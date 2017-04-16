#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <memory.h>

#include "flashcrumb.h"

#define EXAMPLE_BANK_SIZE       128
#define EXAMPLE_BANK_CNT        9

static uint8_t      banks[EXAMPLE_BANK_SIZE][EXAMPLE_BANK_SIZE];

void do_logging(void);



void dump_buf()
{
    int i = 0;

    while (i < EXAMPLE_BANK_SIZE * EXAMPLE_BANK_CNT) {
        for (int j = 0; j < 16; j++) {
            printf("%02x", ((uint8_t*)banks)[i]);
            i++;

            if ((i % 4) == 0) {
                printf(" ");
            }
        }

        if ((i % 128) == 0) printf("\n");

        printf("\n");
    }
}

void Crumb_erasebank(uint32_t bank)
{
    memset(&banks[bank], (0-1), EXAMPLE_BANK_SIZE);
}


int main()
{
    memset(banks, (0-1), sizeof(banks));

    Crumb_Init(banks, EXAMPLE_BANK_CNT, EXAMPLE_BANK_SIZE);


    do_logging();
    dump_buf();
}
