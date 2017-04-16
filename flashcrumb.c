#include "flashcrumb.h"

typedef struct {
    uint8_t             *banks;
    size_t              banksize;
    size_t              bankcnt;
    size_t              next;
    size_t              crntbank;
} Crumb_t;

static Crumb_t          crumbs;


void Crumb_erasebank(uintptr_t bank);

static inline Crumb_Header_t* Crumb_entryat(size_t pos)
{
    return (Crumb_Header_t*)(&crumbs.banks[crumbs.crntbank * crumbs.banksize] + pos);
}

void Crumb_Init(void *banks, size_t bankcnt, size_t banksize)
{
    bool    startfound = false;

    crumbs.banks = banks;
    crumbs.banksize = banksize;
    crumbs.bankcnt = bankcnt;
    crumbs.crntbank = 0;
    crumbs.next = 0;


    while (!startfound && crumbs.crntbank < crumbs.bankcnt) {
        size_t  *bwd = (size_t*)&crumbs.banks[crumbs.crntbank+1];
        size_t  i;

        for (i = 0; i < CRUMB_MAX_ENTRY_SIZE/sizeof(size_t); i++) {
            bwd--;

            if (*bwd != CRUMB_EMPTYWD) {
                startfound = true;
                break ;
            }
        }

        crumbs.crntbank += 1;
    }

    if (startfound) {
        Crumb_Header_t  *entry;
        size_t          off = 0;

        // The current bank is ahead by 1 from the prior while loop.
        crumbs.crntbank -= 1;

        entry = (Crumb_Header_t*)&crumbs.banks[crumbs.banksize * crumbs.crntbank];

        while ((entry->catid & CRUMB_EMPTY) != CRUMB_EMPTY) {
            off += Crumb_EntrySize(entry);
            entry = Crumb_entryat(off);
        }
    }
    else {
        crumbs.next = 0;
        crumbs.crntbank = 0;
    }
}

void Crumb_Reset()
{
    size_t  b;

    for (b = 0; b < crumbs.bankcnt; b++) {
        Crumb_erasebank(b);
    }

    crumbs.crntbank = 0;
    crumbs.next = 0;
}

size_t Crumb_prevbank()
{
    if (crumbs.crntbank == 0) {
        return crumbs.bankcnt - 1;
    }
    else {
        return crumbs.crntbank + 1;
    }
}

size_t Crumb_nextbank()
{
    if (crumbs.crntbank == crumbs.bankcnt - 1) {
        return 0;
    }
    else {
        return crumbs.crntbank + 1;
    }
}

void* Crumb_GetEntry(size_t size)
{
    Crumb_Header_t  *entry;

    entry = Crumb_entryat(crumbs.next);

    if (crumbs.next + size >= crumbs.banksize) {
        // need to adjust crumbs.next to point at the beginning of the next bank and
        // partway into the current entry.  The entry will be split across contiguous banks

        crumbs.crntbank = Crumb_nextbank();
        crumbs.next += size;

        if (crumbs.next < crumbs.banksize && crumbs.crntbank == 0) {
            entry->catid = CRUMB_FILL;

            Crumb_SetEntrySize(entry, crumbs.banksize - crumbs.next);
            crumbs.next = 0;
            entry = Crumb_entryat(crumbs.next);
        }
        else {
            crumbs.next -= crumbs.banksize;
        }

        /* This needs occur _after_ the possible fill occurs.  For an implementation that
         * may flush the oldest buffer to some kind of storage, the fill needs to be in
         * there before it's written out.
         */
        Crumb_erasebank(crumbs.crntbank);
    }

    else {
        crumbs.next += size;
    }

    return entry;
}

Crumb_Header_t* Crumb_firstentry()
{
    Crumb_Header_t  *entry;

    entry = (Crumb_Header_t*)&crumbs.banks[Crumb_nextbank() * crumbs.banksize];

    if (entry->catid == CRUMB_EMPTY) {
        entry = (Crumb_Header_t*)crumbs.banks;
    }
    else {
        entry = (Crumb_Header_t*)&crumbs.banks[Crumb_nextbank() * crumbs.banksize];
    }

    return entry;
}

Crumb_Header_t* Crumb_nextentry(Crumb_Header_t *entry)
{
    uint8_t *next = (uint8_t*)entry;

    next += Crumb_EntrySize(entry);

    entry = (Crumb_Header_t*)next;

    if (next == (uint8_t*)Crumb_entryat(crumbs.next)) {
        return NULL;
    }
    else if (entry->catid == CRUMB_FILL) {
        next += Crumb_EntrySize(entry);

        if (next == &crumbs.banks[crumbs.banksize * crumbs.bankcnt]) {
            next = crumbs.banks;
        }

        if (next == (uint8_t*)Crumb_entryat(crumbs.next)) {
            return NULL;
        }
    }

    return (Crumb_Header_t*)next;
}
