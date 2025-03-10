#include "pico/stdlib.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "hardware/pwm.h"
#include "pico/time.h"

static int clamp_speed(int speed) {
    if (speed < 0) return 0;
    if (speed > 1000) return 1000;
    return speed;
}

static void init_track(uint vcc_pin, uint dir_pin, uint pwm_pin, uint *slice, uint *channel, int duty) {
    gpio_init(vcc_pin);
    gpio_set_dir(vcc_pin, GPIO_OUT);
    gpio_init(dir_pin);
    gpio_set_dir(dir_pin, GPIO_OUT);
    gpio_set_function(pwm_pin, GPIO_FUNC_PWM);
    *slice = pwm_gpio_to_slice_num(pwm_pin);
    *channel = pwm_gpio_to_channel(pwm_pin);
    pwm_set_wrap(*slice, 1000);
    pwm_set_chan_level(*slice, *channel, duty);
    pwm_set_enabled(*slice, true);
}

static void process_command(const char* cmd, absolute_time_t *last_heartbeat, uint slice_left, uint chan_left, uint slice_right, uint chan_right, uint left_dir_pin, uint right_dir_pin) {
    printf("cmd: %s\n", cmd);
    if (strcmp(cmd, "heartbeat") == 0) {
        *last_heartbeat = get_absolute_time();
    } else if (strncmp(cmd, "move ", 5) == 0) {
        float linear = 0.0f, angular = 0.0f;
        if (sscanf(cmd + 5, "%f %f", &linear, &angular) == 2) {
            int left_val = (int)((linear - angular) * 10);
            int right_val = (int)((linear + angular) * 10);
            if (left_val < 0) {
                gpio_put(left_dir_pin, 0);
                left_val = clamp_speed(-left_val);
            } else {
                gpio_put(left_dir_pin, 1);
                left_val = clamp_speed(left_val);
            }
            if (right_val < 0) {
                gpio_put(right_dir_pin, 0);
                right_val = clamp_speed(-right_val);
            } else {
                gpio_put(right_dir_pin, 1);
                right_val = clamp_speed(right_val);
            }
            printf("left_speed: %i\n", left_val);
            printf("right_speed: %i\n", right_val);
            pwm_set_chan_level(slice_left, chan_left, left_val);
            pwm_set_chan_level(slice_right, chan_right, right_val);
        }
    }
}

int main() {
    stdio_init_all();
    // The UART baud rate is set by the Pico SDK defaults (typically 115200)
    // and configured via pico_enable_stdio_uart() in CMakeLists.txt.
    uint slice_num_left, chan_left;
    uint slice_num_right, chan_right;

    init_track(2, 4, 3, &slice_num_left, &chan_left, 0);
    init_track(6, 8, 7, &slice_num_right, &chan_right, 0);

    // Set VCC and forward direction for both tracks
    gpio_put(2, 1);         // Enable left VCC
    gpio_put(4, 1);         // Set left direction forward
    gpio_put(6, 1);         // Enable right VCC
    gpio_put(8, 1);         // Set right direction forward

    // Heartbeat monitoring loop: if no "heartbeat" command received within 3s, stop all motors.
    absolute_time_t last_heartbeat = get_absolute_time();
    bool warned = false;
    char buf[64] = {0};
    int buf_index = 0;
    while (true) {
        int c = getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT) {
            char ch = (char)c;
            if (ch == '\n' || ch == '\r') {
                buf[buf_index] = '\0';
                if (strcmp(buf, "heartbeat") == 0) {
                    warned = false;
                }
                process_command(buf, &last_heartbeat, slice_num_left, chan_left, slice_num_right, chan_right, 4, 8);
                buf_index = 0;
            } else {
                if (buf_index < 63) {
                    buf[buf_index++] = ch;
                }
            }
        }
        if (absolute_time_diff_us(last_heartbeat, get_absolute_time()) > 3000000) {
            if (!warned) {
                printf("heartbeat missing, stopping motors\n");
                warned = true;
            }
            pwm_set_chan_level(slice_num_right, chan_right, 0);
            pwm_set_chan_level(slice_num_left, chan_left, 0);
        }
    }

    // pwm_set_chan_level(slice_num_right, chan_right, 1000);
    // pwm_set_chan_level(slice_num_left, chan_left, 1000);
}
