#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include "crumb.h"

static crumbseq_t   sequence = 0;
static crumbtime_t  timestamp = 0;

crumbseq_t Crumb_Sequence() {
    return sequence++;
}

crumbtime_t Crumb_Timestamp() {
    return timestamp++;
}

void example_dump_bytes(void *arg, uint8_t b)
{
    FILE    *file = (FILE*)arg;

    fwrite(&b, 1, 1, file);

}

void do_logging(void)
{
    uint32_t    i,
                bytes = 1,
                off = 0;
    FILE        *file;


    Crumb_State_PwrRst(CRUMB_STATE_PWRRST_POWER_ON);

    for (i = 1; i <= 10; i++) {
        Crumb_IO_Read(1, bytes, off);
        Crumb_IO_Write(2, bytes, off);
        bytes += 1;
        off += 10;
    }

    Crumb_State_PwrRst(CRUMB_STATE_PWRRST_SLEEP);
    Crumb_State_PwrRst(CRUMB_STATE_PWRRST_WAKE);

    for (; i <= 20; i++) {
        Crumb_IO_Read(1, bytes, off);
        Crumb_IO_Write(2, bytes, off);
        bytes += 1;
        off += 10;
    }

    Crumb_State_PwrRst(CRUMB_STATE_PWRRST_POWER_OFF);


    file = fopen("example_crumbs.bin", "wb");
    if (file == NULL) {
        printf("Failed to open file.\n");
    }
    else {
        Crumb_Dump(example_dump_bytes, file);
        fclose(file);
    }
}
