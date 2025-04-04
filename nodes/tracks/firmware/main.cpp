#include "pico/stdlib.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "hardware/pwm.h"
#include "pico/time.h"

// GPIO Pin definitions (adjust if different)
#define LEFT_VCC_PIN  2
#define LEFT_DIR_PIN  4
#define LEFT_PWM_PIN  3
#define RIGHT_VCC_PIN 6
#define RIGHT_DIR_PIN 8
#define RIGHT_PWM_PIN 7

#define PWM_WRAP_VALUE 1000 // Max PWM duty cycle value
#define HEARTBEAT_TIMEOUT_US 3000000 // 3 seconds

// Clamp speed to the allowed PWM range (0 to PWM_WRAP_VALUE)
static int clamp_pwm_duty(int duty) {
    if (duty < 0) return 0;
    if (duty > PWM_WRAP_VALUE) return PWM_WRAP_VALUE;
    return duty;
}

// Initialize GPIO and PWM for one track
static void init_track(uint vcc_pin, uint dir_pin, uint pwm_pin, uint *slice, uint *channel, int initial_duty) {
    // VCC Enable Pin
    gpio_init(vcc_pin);
    gpio_set_dir(vcc_pin, GPIO_OUT);
    gpio_put(vcc_pin, 1); // Enable motor driver VCC

    // Direction Pin
    gpio_init(dir_pin);
    gpio_set_dir(dir_pin, GPIO_OUT);
    // Initial direction doesn't strictly matter here as it's set per command

    // PWM Pin
    gpio_set_function(pwm_pin, GPIO_FUNC_PWM);
    *slice = pwm_gpio_to_slice_num(pwm_pin);
    *channel = pwm_gpio_to_channel(pwm_pin);
    pwm_set_wrap(*slice, PWM_WRAP_VALUE); // Set PWM frequency wrap value
    pwm_set_chan_level(*slice, *channel, initial_duty); // Set initial duty cycle
    pwm_set_enabled(*slice, true); // Enable PWM slice
}

// Process incoming serial commands
static void process_command(const char* cmd, absolute_time_t *last_heartbeat,
                             uint slice_left, uint chan_left, uint slice_right, uint chan_right,
                             uint left_dir_pin, uint right_dir_pin) {

    printf("cmd: %s\n", cmd); // Log received command

    if (strcmp(cmd, "heartbeat") == 0) {
        *last_heartbeat = get_absolute_time();
    } else if (strncmp(cmd, "move ", 5) == 0) {
        *last_heartbeat = get_absolute_time(); // Treat move command as heartbeat too

        float linear = 0.0f, angular = 0.0f;
        if (sscanf(cmd + 5, "%f %f", &linear, &angular) == 2) {

            // --- Standard Differential Drive Mixing ---
            // Note: Python script sends -100 to 100. Firmware multiplies by 10.
            // Resulting range for left_mix/right_mix is approx -2000 to 2000.
            float left_mix = (linear - angular);
            float right_mix = (linear + angular);

            // --- Determine Direction and PWM Duty Cycle ---
            // Based on observation: positive calculated value means BACKWARD motion.
            // Therefore, negative calculated value means FORWARD motion.

            int left_pwm_duty;
            int right_pwm_duty;

            // Left Motor
            if (left_mix < 0) { // Negative mix value means FORWARD
                gpio_put(left_dir_pin, 1); // Assuming GPIO HIGH = Forward (adjust if needed)
                left_pwm_duty = clamp_pwm_duty((int)(-left_mix * 10)); // Make value positive for PWM, scale, clamp
            } else { // Positive or zero mix value means BACKWARD (or Stop)
                gpio_put(left_dir_pin, 0); // Assuming GPIO LOW = Backward (adjust if needed)
                left_pwm_duty = clamp_pwm_duty((int)(left_mix * 10)); // Value is already positive, scale, clamp
            }

            // Right Motor
            if (right_mix < 0) { // Negative mix value means FORWARD
                gpio_put(right_dir_pin, 1); // Assuming GPIO HIGH = Forward (adjust if needed)
                right_pwm_duty = clamp_pwm_duty((int)(-right_mix * 10)); // Make value positive for PWM, scale, clamp
            } else { // Positive or zero mix value means BACKWARD (or Stop)
                gpio_put(right_dir_pin, 0); // Assuming GPIO LOW = Backward (adjust if needed)
                right_pwm_duty = clamp_pwm_duty((int)(right_mix * 10)); // Value is already positive, scale, clamp
            }

            // Log the *final* PWM values being set
            printf("left_pwm: %d\n", left_pwm_duty);
            printf("right_pwm: %d\n", right_pwm_duty);

            // Set PWM levels
            pwm_set_chan_level(slice_left, chan_left, left_pwm_duty);
            pwm_set_chan_level(slice_right, chan_right, right_pwm_duty);

        } else {
            printf("Error parsing move command: %s\n", cmd);
        }
    } else {
        printf("Unknown command: %s\n", cmd);
    }
}

int main() {
    stdio_init_all();
    // UART setup is assumed to be handled by stdio_init_all and CMakeLists

    uint slice_num_left, chan_left;
    uint slice_num_right, chan_right;

    // Initialize tracks - VCC is enabled inside init_track now
    init_track(LEFT_VCC_PIN, LEFT_DIR_PIN, LEFT_PWM_PIN, &slice_num_left, &chan_left, 0);
    init_track(RIGHT_VCC_PIN, RIGHT_DIR_PIN, RIGHT_PWM_PIN, &slice_num_right, &chan_right, 0);

    printf("Track Controller Initialized. Waiting for commands...\n");

    absolute_time_t last_heartbeat = get_absolute_time();
    bool heartbeat_warned = false;
    char serial_cmd_buf[64] = {0};
    int buf_index = 0;

    while (true) {
        int c = getchar_timeout_us(0); // Non-blocking read
        if (c != PICO_ERROR_TIMEOUT) {
            char ch = (char)c;
            // Handle line endings and buffer filling
            if (ch == '\n' || ch == '\r') {
                if (buf_index > 0) { // Process only if buffer not empty
                    serial_cmd_buf[buf_index] = '\0'; // Null-terminate
                    process_command(serial_cmd_buf, &last_heartbeat, slice_num_left, chan_left, slice_num_right, chan_right, LEFT_DIR_PIN, RIGHT_DIR_PIN);
                    buf_index = 0; // Reset buffer index
                    heartbeat_warned = false; // Reset warning on any valid command processed
                }
            } else if (buf_index < (sizeof(serial_cmd_buf) - 1)) {
                serial_cmd_buf[buf_index++] = ch; // Add character to buffer
            } else {
                // Buffer overflow, discard and reset
                printf("WARN: Serial command buffer overflow!\n");
                buf_index = 0;
            }
        }

        // Heartbeat Check
        if (absolute_time_diff_us(last_heartbeat, get_absolute_time()) > HEARTBEAT_TIMEOUT_US) {
            if (!heartbeat_warned) {
                printf("WARN: Heartbeat missing, stopping motors!\n");
                // Stop motors by setting PWM duty cycle to 0
                pwm_set_chan_level(slice_num_left, chan_left, 0);
                pwm_set_chan_level(slice_num_right, chan_right, 0);
                heartbeat_warned = true;
            }
        }
    } // end while(true)

    return 0; // Should not be reached
}