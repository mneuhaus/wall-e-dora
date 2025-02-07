#include "pico/stdlib.h"
#include <stdio.h>

int main() {
    stdio_init_all();
    gpio_init(25);
    gpio_set_dir(25, GPIO_OUT);
    while (true) {
        printf("hello world\n");
        gpio_put(25, 1);
        sleep_ms(250);
        gpio_put(25, 0);
        sleep_ms(750);
    }
    return 0;
}
