#ifndef __CRUMB_H__
#define __CRUMB_H__

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#define CRUMB_EMPTY         0xff
#define CRUMB_FILL          0xfe
#define CRUMB_FILTERWORDS   4

/* Static asserts used to detect inconsistent size/alignment issues in generated code
 * code and compiled code.
 * This code was lifted from http://www.pixelbeat.org/programming/gcc/static_assert.html
 * but renamed to avoid namespace issues.
 */
#define CRUMB_ASSERT_CONCAT_(__a, __b) __a##__b
#define CRUMB_ASSERT_CONCAT(__a, __b) CRUMB_ASSERT_CONCAT_(__a, __b)
/* These can't be used after statements in c89. */
#ifdef __COUNTER__
  #define CRUMB_STATIC_ASSERT(__e,__m) \
    ;enum { CRUMB_ASSERT_CONCAT(static_assert_, __COUNTER__) = 1/(int)(!!(__e)) }
#else
  /* This can't be used twice on the same line so ensure if using in headers
   * that the headers are not included twice (by wrapping in #ifndef...#endif)
   * Note it doesn't cause an issue when used on same line of separate modules
   * compiled with gcc -combine -fwhole-program.  */
  #define CRUMB_STATIC_ASSERT(__e,__m) \
    ;enum { CRUMB_ASSERT_CONCAT(assert_line_, __LINE__) = 1/(int)(!!(__e)) }
#endif


#include "crumbauto.h"

static inline crumbi_t Crumb_EntrySize(Crumb_Header_t *entry) {
    return (entry->size + 1) * CRUMB_SCALE;
}

static inline void Crumb_SetEntrySize(Crumb_Header_t *entry, uintptr_t size)
{
    entry->size = (size / CRUMB_SCALE) - 1;
}

void Crumb_Dump(void (*dump)(void*, uint8_t), void *arg);

#define CRUMB_FILTER_ALL        -1
#define __CRUMB_FILTER_SHIFT    5
#define __CRUMB_FILTER_MASK     0x1f

#ifdef __CRUMB_FILTERS_ENABLED

static inline bool Crumb_Filter(int cat, int ent)
{
    return crumb_filters[cat][ent >> __CRUMB_FILTER_SHIFT] & (1 << (ent & __CRUMB_FILTER_MASK)) != 0;
}

void Crumb_SetFilter(int cat, int ent);
void Crumb_ClrFilter(int cat, int ent);

#else

#define Crumb_ClrFilter(__cat, __ent)
#define Crumb_SetFilter(___cat, __ent)
#define Crumb_Filter(__cat, __ent)  true

#endif

#endif

