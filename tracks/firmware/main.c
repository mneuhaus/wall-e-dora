#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/uart.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define RIGHT_VCC_PIN 2
#define RIGHT_PWM_PIN 3
#define RIGHT_DIR_PIN 4

#define LEFT_VCC_PIN 6
#define LEFT_PWM_PIN 7
#define LEFT_DIR_PIN 8

typedef struct {
    float Kp;
    float Ki;
    float Kd;
    float prev_error;
    float integral;
} PID;

float pid_update(PID *pid, float setpoint, float measurement, float dt) {
    float error = setpoint - measurement;
    pid->integral += error * dt;
    float derivative = (error - pid->prev_error) / dt;
    float output = pid->Kp * error + pid->Ki * pid->integral + pid->Kd * derivative;
    pid->prev_error = error;
    return output;
}

PID pid_right = { .Kp = 1.0f, .Ki = 0.0f, .Kd = 0.0f, .prev_error = 0.0f, .integral = 0.0f };
PID pid_left  = { .Kp = 1.0f, .Ki = 0.0f, .Kd = 0.0f, .prev_error = 0.0f, .integral = 0.0f };

void setup_gpio() {
    // Setup Right Motor pins
    gpio_init(RIGHT_VCC_PIN);
    gpio_set_dir(RIGHT_VCC_PIN, GPIO_OUT);
    gpio_put(RIGHT_VCC_PIN, 1); // Enable motor driver if needed

    gpio_init(RIGHT_DIR_PIN);
    gpio_set_dir(RIGHT_DIR_PIN, GPIO_OUT);
    // Setup right PWM pin
    gpio_set_function(RIGHT_PWM_PIN, GPIO_FUNC_PWM);
    
    // Setup Left Motor pins
    gpio_init(LEFT_VCC_PIN);
    gpio_set_dir(LEFT_VCC_PIN, GPIO_OUT);
    gpio_put(LEFT_VCC_PIN, 1); // Enable motor driver if needed

    gpio_init(LEFT_DIR_PIN);
    gpio_set_dir(LEFT_DIR_PIN, GPIO_OUT);
    // Setup left PWM pin
    gpio_set_function(LEFT_PWM_PIN, GPIO_FUNC_PWM);
}

int main() {
    stdio_init_all();
    setup_gpio();

    // Setup PWM slices and channels for right and left motors
    uint slice_right = pwm_gpio_to_slice_num(RIGHT_PWM_PIN);
    uint slice_left = pwm_gpio_to_slice_num(LEFT_PWM_PIN);
    pwm_set_wrap(slice_right, 1000);
    pwm_set_wrap(slice_left, 1000);
    pwm_set_enabled(slice_right, true);
    pwm_set_enabled(slice_left, true);

    const float dt = 0.01f; // loop time in seconds
    char buffer[64];

    while (true) {
        if (fgets(buffer, sizeof(buffer), stdin)) {
            // Expect command in the ros2 Twist message format:
            // "linear: x: <lin>, y: <val>, z: <val> angular: x: <val>, y: <val>, z: <ang>"
            float lin = 0.0f, ang = 0.0f;
            if (sscanf(buffer, "linear: x: %f, y: %*f, z: %*f angular: x: %*f, y: %*f, z: %f", &lin, &ang) == 2) {
                float setpoint_right = lin + ang;
                float setpoint_left  = lin - ang;
                // In absence of sensor feedback, we assume measurement is zero.
                float output_right = pid_update(&pid_right, setpoint_right, 0.0f, dt);
                float output_left  = pid_update(&pid_left, setpoint_left,  0.0f, dt);
                
                // Determine the direction based on the sign of the output
                uint pwm_right = (uint)(output_right < 0 ? -output_right : output_right);
                uint pwm_left  = (uint)(output_left  < 0 ? -output_left : output_left);
                
                gpio_put(RIGHT_DIR_PIN, output_right < 0 ? 1 : 0);
                gpio_put(LEFT_DIR_PIN,  output_left  < 0 ? 1 : 0);

                // Clamp PWM values to the wrap limit
                if (pwm_right > 1000) pwm_right = 1000;
                if (pwm_left > 1000) pwm_left = 1000;

                pwm_set_gpio_level(RIGHT_PWM_PIN, pwm_right);
                pwm_set_gpio_level(LEFT_PWM_PIN, pwm_left);

                printf("Right PWM: %d, Left PWM: %d\n", pwm_right, pwm_left);
            }
        }
        busy_wait_us_32((uint32_t)(dt * 1000000));
    }
    return 0;
}
