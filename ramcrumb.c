#include <stdbool.h>
#include <stdint.h>

#include "crumb.h"

static uint8_t      *crumbbuf;
static uint32_t     bufsize;
static uintptr_t    tail;
static uintptr_t    head;
static bool         wrapped;


void Crumb_Init(void *buf, size_t size)
{
    head = 0;
    tail = 0;
    wrapped = false;
    crumbbuf = (uint8_t*)buf;
    bufsize = size;
}

void Crumb_Reset()
{
    head = 0;
    tail = 0;
    wrapped = false;
}


void* Crumb_GetEntry(size_t size)
{
    Crumb_Header_t  *entry;

    if (tail + size >= bufsize) {
        if (tail < bufsize) {
            entry = (Crumb_Header_t*)&crumbbuf[tail];
            entry->catid = CRUMB_FILL;
            Crumb_SetEntrySize(entry, bufsize - tail);
        }

        wrapped = true;
        head = 0;
        tail = 0;
    }

    if (wrapped) {
        do {
            entry = (Crumb_Header_t*)&crumbbuf[head];
            head += Crumb_EntrySize(entry);
        } while (head < tail + size);
    }

    entry = (Crumb_Header_t*)&crumbbuf[tail];
    tail += size;

    return entry;
}


Crumb_Header_t* Crumb_firstentry()
{
    if (head == tail && !wrapped) {
        return NULL;
    }
    else {
        return (Crumb_Header_t*)&crumbbuf[head];
    }
}

Crumb_Header_t* Crumb_nextentry(Crumb_Header_t *entry)
{
    uint8_t *next = (uint8_t*)entry;

    next += Crumb_EntrySize(entry);

    if (next == &crumbbuf[bufsize]) {
        next = crumbbuf;
    }

    entry = (Crumb_Header_t*)next;

    if (next == &crumbbuf[tail]) {
        next = NULL;
    }
    else if (entry->catid == CRUMB_FILL) {
        next = crumbbuf;

        if (next == &crumbbuf[tail]) {
            next = NULL;
        }
    }

    return (Crumb_Header_t*)next;
}


