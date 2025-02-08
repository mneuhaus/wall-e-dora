#include "pico/stdlib.h"
#include <stdio.h>
#include "hardware/pwm.h"

int main() {
    stdio_init_all();

    // Initialize left track pins
    gpio_init(2);           // Left VCC
    gpio_set_dir(2, GPIO_OUT);
    gpio_init(4);           // Left DIR
    gpio_set_dir(4, GPIO_OUT);
    gpio_set_function(3, GPIO_FUNC_PWM);  // Left PWM

    // Initialize right track pins
    gpio_init(6);           // Right VCC
    gpio_set_dir(6, GPIO_OUT);
    gpio_init(8);           // Right DIR
    gpio_set_dir(8, GPIO_OUT);
    gpio_set_function(7, GPIO_FUNC_PWM);  // Right PWM

    // Set VCC and forward direction
    gpio_put(2, 1);         // Enable left VCC
    gpio_put(4, 1);         // Set left direction forward
    gpio_put(6, 1);         // Enable right VCC
    gpio_put(8, 1);         // Set right direction forward

    // Setup PWM for left track (GPIO3): 10% duty cycle
    uint slice_num_left = pwm_gpio_to_slice_num(3);
    uint chan_left = pwm_gpio_to_channel(3);
    pwm_set_wrap(slice_num_left, 100);
    pwm_set_chan_level(slice_num_left, chan_left, 10);
    pwm_set_enabled(slice_num_left, true);

    // Setup PWM for right track (GPIO7): 10% duty cycle
    uint slice_num_right = pwm_gpio_to_slice_num(7);
    uint chan_right = pwm_gpio_to_channel(7);
    pwm_set_wrap(slice_num_right, 100);
    pwm_set_chan_level(slice_num_right, chan_right, 10);
    pwm_set_enabled(slice_num_right, true);

    // Run the turn for 5 seconds
    sleep_ms(5000);

    // Stop the motors
    pwm_set_enabled(slice_num_left, false);
    pwm_set_enabled(slice_num_right, false);
    gpio_put(2, 0);         // Disable left VCC
    gpio_put(6, 0);         // Disable right VCC

    return 0;
}
