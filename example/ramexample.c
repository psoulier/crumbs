#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>

#include "ramcrumb.h"

#define EXAMPLE_BUFFER_SIZE     128
static uint8_t      buffer[EXAMPLE_BUFFER_SIZE];
static crumbseq_t   sequence = 0;
static crumbtime_t  timestamp = 0;


void do_logging(void);


void dump_buf()
{
    int i = 0;

    while (i < EXAMPLE_BUFFER_SIZE) {
        for (int j = 0; j < 16; j++) {
            printf("%02x", buffer[i]);
            i++;

            if ((i % 4) == 0) {
                printf(" ");
            }
        }

        printf("\n");
    }
}

int main()
{
    Crumb_Init(buffer, EXAMPLE_BUFFER_SIZE);

    do_logging();
}
