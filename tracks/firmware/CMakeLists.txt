cmake_minimum_required(VERSION 3.12)
# Initialize the Pico SDK from installed location
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
project(tracks_firmware C CXX ASM)
pico_sdk_init()

add_executable(tracks_firmware main.c)
target_link_libraries(tracks_firmware pico_stdlib hardware_pwm hardware_uart)
pico_add_extra_outputs(tracks_firmware)
