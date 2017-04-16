cmake_minimum_required(VERSION 3.5.2 FATAL_ERROR)

project(Crumb)


set(RAMCRUMB_SRC "ramcrumb.c" "crumb.c" "example/ramexample.c" "example/trcexample.c" "crumb.h")

set(FLASHCRUMB_SRC "flashcrumb.c" "crumb.c" "example/flashexample.c" "example/trcexample.c" "crumb.h")


include_directories(${CMAKE_SOURCE_DIR})

# Add test executable target
add_executable(ramcrumb ${RAMCRUMB_SRC})
add_executable(flashcrumb ${FLASHCRUMB_SRC})


