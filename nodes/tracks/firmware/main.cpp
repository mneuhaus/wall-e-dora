#include "pico/stdlib.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "hardware/pwm.h"
#include "pico/time.h"

static int clamp_speed(int speed) {
    if (speed < 0) return 0;
    if (speed > 100) return 100;
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
    pwm_set_wrap(*slice, 100);
    pwm_set_chan_level(*slice, *channel, duty);
    pwm_set_enabled(*slice, true);
}

static void process_command(const char* cmd, absolute_time_t *last_heartbeat, uint slice_left, uint chan_left, uint slice_right, uint chan_right) {
    if (strcmp(cmd, "heartbeat") == 0) {
        *last_heartbeat = get_absolute_time();
    } else if (strncmp(cmd, "left ", 5) == 0) {
        int speed = clamp_speed(atoi(cmd + 5));
        pwm_set_chan_level(slice_left, chan_left, speed);
    } else if (strncmp(cmd, "right ", 6) == 0) {
        int speed = clamp_speed(atoi(cmd + 6));
        pwm_set_chan_level(slice_right, chan_right, speed);
    }
}

int main() {
    stdio_init_all();

    uint slice_num_left, chan_left;
    uint slice_num_right, chan_right;

    init_track(2, 4, 3, &slice_num_left, &chan_left, 10);
    init_track(6, 8, 7, &slice_num_right, &chan_right, 10);

    // Set VCC and forward direction for both tracks
    gpio_put(2, 1);         // Enable left VCC
    gpio_put(4, 1);         // Set left direction forward
    gpio_put(6, 1);         // Enable right VCC
    gpio_put(8, 1);         // Set right direction forward

    // Heartbeat monitoring loop: if no "heartbeat" command received within 3s, stop all motors.
    absolute_time_t last_heartbeat = get_absolute_time();
    char buf[64] = {0};
    int buf_index = 0;
    while (true) {
        int c = getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT) {
            char ch = (char)c;
            if (ch == '\n' || ch == '\r') {
                buf[buf_index] = '\0';
                process_command(buf, &last_heartbeat, slice_num_left, chan_left, slice_num_right, chan_right);
                buf_index = 0;
            } else {
                if (buf_index < 63) {
                    buf[buf_index++] = ch;
                }
            }
        }
        if (absolute_time_diff_us(last_heartbeat, get_absolute_time()) > 3000000) {
            break;
        }
        sleep_ms(100);
    }

    // Stop the motors
    pwm_set_enabled(slice_num_left, false);
    pwm_set_enabled(slice_num_right, false);
    gpio_put(2, 0);         // Disable left VCC
    gpio_put(6, 0);         // Disable right VCC

    return 0;
}
