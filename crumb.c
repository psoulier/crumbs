#include <stdio.h>
#include "crumb.h"

Crumb_Filters_t         crumb_filters;

Crumb_Header_t* Crumb_firstentry();
Crumb_Header_t* Crumb_nextentry(Crumb_Header_t *entry);

void dump_entry(Crumb_Header_t *entry)
{
    int size = Crumb_EntrySize(entry);
    uint8_t *b = (uint8_t*)entry;

    for (int i = 0; i < size; i++) {
        if ((i % 4) == 0) printf(" ");
        printf("%02x", *b);
        b++;

    }

    printf("\n");
}

void Crumb_Dump(void (*dump)(void*, uint8_t), void *arg) {
    Crumb_Header_t  *entry;
    uint8_t         checksum = 0;
    uint32_t        tag = CRUMB_CRC;
    uint8_t         *b;
    crumbi_t        i;

    b = (uint8_t*)&tag;
    for (i = 0; i < 4; i++) {
        checksum ^= *b;
        dump(arg, *b);
        b++;
    }

    for (entry = Crumb_firstentry(); entry != NULL; entry = Crumb_nextentry(entry)) {
        uint8_t *b = (uint8_t*)entry;
        int     size = Crumb_EntrySize(entry);

        for (i = 0; i < size; i++) {
            checksum ^= *b;
            dump(arg, *b);
            b++;
        }
    }

    dump(arg, 0);
    dump(arg, CRUMB_FILL);
    dump(arg, 0);
    dump(arg, 0);
    dump(arg, checksum);
}


#if __CRUMB_FILTERS_ENABLED
void Crumb_SetFilter(int cat, int ent)
{
    if (cat == CRUMB_FILTER_ALL) {
        size_t  *filt = &__crumb_filters[0][0];
        size_t  i;

        for (i = 0; i < __CRUMB_NUM_CATEGORIES * __CRUMB_NUM_ENTRY_FILTERS; i++) {
            filt[i] = ~0;
        }
    }
    else if (ent == CRUMB_FILTER_ALL) {
        for (i = 0; i < __CRUMB_NUM_ENTRY_FILTERS; i++) {
            __crumb_filters[cat][i] = ~0;
        }
    }
    else {
        __crumb_filters[cat][ent >> 5] |= 1 << (ent & __CRUMB_FILTER_MASK);
    }
}

void Crumb_ClrFilter(int cat, int ent)
{
    if (cat == CRUMB_FILTER_ALL) {
        size_t  *filt = &__crumb_filters[0][0];
        size_t  i;

        for (i = 0; i < __CRUMB_NUM_CATEGORIES * __CRUMB_NUM_ENTRY_FILTERS; i++) {
            filt[i] = 0;
        }
    }
    else if (ent == CRUMB_FILTER_ALL) {
        for (i = 0; i < __CRUMB_NUM_ENTRY_FILTERS; i++) {
            __crumb_filters[cat][i] = 0;
        }
    }
    else {
        __crumb_filters[cat][ent >> 5] &= ~(1 << (ent & __CRUMB_FILTER_MASK));
    }
}
#endif
