import json
import sys
import operator
import re
import binascii
import argparse
import struct




H_FILE = """
/* This is an auto-generated file, do not modify
 */
#ifndef __CRUMBSAUTO_H__
#define __CRUMBSAUTO_H__

%s

#endif
"""

HEADER_STRUCT = """
typedef struct {
    uint8_t         size;
    uint8_t         catid;
    uint8_t         entryid;
    uint8_t         rsvd;
} Crumb_Header_t;
"""

CRUMB_ENUM = """
typedef enum {
%s
} %s;
"""

CRUMB_FUNC = """
static inline void %s(%s) {
    if (Crumb_Filter(0x%x, 0x%x)) {
        %s      *entry;

        entry = (%s*)Crumb_GetEntry(%d);
%s
    }
}
"""


# Could optimize code size (possibly) by detecting log structures that are
# structurally equivalent and just defining one func and use macros for the
# others.
#
CATEGORYID_STR = 'catid'
ENTRYID_STR = 'entryid'
SEQUENCE_STR = 'sequence'
TIMESTAMP_STR = 'timestamp'
SIZE_STR = 'size'


BUILTIN_CTYPES = {8:'uint8_t', 16:'uint16_t', 32:'uint32_t', 64:'uint64_t',
                 -8:'int8_t', -16:'int16_t', -32:'int32_t', -64:'int64_t',
                 .32:'float', .64:'double'}

SIZEOF_CTYPES = {'uint8_t':1, 'int8_t':1, 'uint16_t':2, 'int16_t':2, 
                 'uint32_t':4, 'int32_t':4, 'uint64_t':8, 'int64_t':8,
                 'float':4, 'double':8}

C2PACKFMT = {'uint8_t':'B', 'uint16_t':'H', 'uint32_t':'I', 'uint64_t':'Q', 
             'int8_t':'b', 'int16_t':'h', 'int32_t':'i', 'int64_t':'q', 
             'float':'f', 'double':'d'}

CVAR_REGEX = re.compile("^[^\d\W]\w*\Z")

WORDSIZE = None
TIMESCALE = 1.0
TIMESTAMP = None
SEQUENCE = None
HDRPACKFMT = None;
BOF = None
HEADER_SIZE = 3
NUM_CATEGORIES = 0
MAX_ENTPERCAT = 0

class CrumbError(Exception):

    def __init__(self, msg):
        self.msg = msg

def pack_fields(struct):
    return sorted(struct.items(), key=operator.itemgetter(1), reverse=True)

def isvalidcvar(c):
    return len(CVAR_REGEX.findall(c)) == 1


def getctype(c):
    """Determine C/C++ type for a given field.
    Currently, only built-in types and enumerated values are supported.  Integer values
    are specified using the required number of bits and a signed value is prefixed by a
    minus sign.  Bits are used in the event that I _could_ compact an entry that had a 
    bunch of small entries, but that's a lot of work for maybe not so much value.

    Enumerated values are just a string of space separated strings that are valid C/C++
    symbols.
    """
    if isinstance(c, int):
        if c in BUILTIN_CTYPES:
            return BUILTIN_CTYPES[c]
        else:
            raise CrumbError('Invalid payload field size "%d"; must be the size of a built-in C integer type' % c)
    elif isinstance(c, float):
        if c in BUILTIN_CTYPES:
            return BUILTIN_CTYPES[c]
        else:
            raise CrumbError('Invalid float size "%s" in payload, must be 32.0 or 64.0' % c)
    else:
        enums = c.split(' ')
        for e in enums:
            if not isvalidcvar(e):
                raise CrumbError('"%s" is not a valid C/C++ symbol name.' % e)

        # Assuming no one will create an entry with more than 64k hand-made names.
        # Really, 256 is a bit ridiculous, but hey,who knows.
        if len(enums) <= 256:
            return 'uint8_t'
        elif len(enums) <= 64*1024:
            return 'uint16_t'
        else:
            raise CrumbError("Too many enums!!! Something went seriously wrong.")

def getcsizeof(c):
    return SIZEOF_CTYPES[ getctype(c) ]

def gen_struct_(name, fields):
    STRUCT = 'typedef struct {\n%s} %s;\n\n'

    cfields = ''

    for f in fields:
        cfields += '    %s %s;\n' % (getctype(f[1]), f[0])

    return STRUCT % (cfields, name)

F_NAME=0
F_RAW=1
F_CTYPE=2
F_POS=3
class Entry:

    def __init__(self, cat, entry, entryid):
        """Processes an entry field from the crumb definition.  Necessary data
        is stored in the object rather than keeping the JSON object around.
        """

        self.cat = cat
        self.id = entryid
        self.packedfields = []
        self.padding = 0
        self.footerpadding = 0


        self._extractfields(entry)

        self.name = entry['name']
        self.packfmt = HDRPACKFMT + 'B' * self.padding
        self.size = HEADER_SIZE + self.padding
        
        for f in self.packedfields:
            self.size += SIZEOF_CTYPES[f[F_CTYPE]]

        for f in self.packedfields:
            self.packfmt += C2PACKFMT[f[F_CTYPE]]

        # Need to account for unused bytes that result from the WORDSIZE alignment.
        # The packing format needs this to ensure that it advances through the 
        # binary data correctly.
        if (self.size % WORDSIZE) != 0:
            self.footerpadding = int(WORDSIZE - (self.size % WORDSIZE))
            self.packfmt += 'B' * self.footerpadding

            self.size += self.footerpadding

        self.format = entry['format']

    def _extractfields(self, entry):
        fields = entry['payload']

        if TIMESTAMP != None:
            fields['timestamp'] = TIMESTAMP

        if SEQUENCE != None:
            fields['sequence'] = SEQUENCE

        sizeoffields = {}
        for f in fields:
            sizeoffields[f] = getcsizeof(fields[f])

        sizeoffields = sorted(sizeoffields.items(), key=operator.itemgetter(1), reverse=True)

        self.padding = int(WORDSIZE - (HEADER_SIZE % WORDSIZE))
        top = []
        bottom = []
        for f in sizeoffields:
            if f[1] <= self.padding:
                top.append((f[0], f[1]))
                self.padding -= f[1]
            else:
                bottom.append((f[0], f[1]))

        packedstruct = top + bottom
        packoff = HEADER_SIZE + self.padding


        # This is the important part.  All the data about a field is gathered here.  The "packedfields"
        # object is a list of fields in the order they occur in physical memory.  Each entry is a tuple
        # of data about the field defined as (symbolic names for these are defined before the "Entry"
        # object):
        # 0: name of field (the C structure field name)
        # 1: The raw "type" as it occurs in the crumb definition file.
        # 2: The C type of the field.
        # 3: The position of this field in the tuple returned by struct.unpack
        self.fieldbyname = {}
        i = 0
        for f in packedstruct:
            self.packedfields.append((f[0], fields[f[0]], getctype(fields[f[0]]), i+packoff))
            self.fieldbyname[f[0]] = self.packedfields[-1]
            i += 1


    def gen_struct(self):
        STRUCT = 'typedef struct {\n%s%s} %s_t;\n'


        header = ''
        header += '    uint8_t size;\n'
        header += '    uint8_t catid;\n'
        header += '    uint8_t entryid;\n'
        if self.padding > 0:
            header += '    uint8_t hdrpadding[%d];\n' % self.padding

        cfields = ''
        for f in self.packedfields:
            cfields += '    %s %s;\n' % (f[F_CTYPE], f[F_NAME])

        if self.footerpadding > 0:
            cfields += '    uint8_t footerpadding[%d];\n' % self.footerpadding

        structname = 'Crumb_%s_%s' % (self.cat['name'], self.name)

        structure = STRUCT % (header, cfields, structname)
        #structure += 'CRUMB_STATIC_ASSERT(sizeof(%s_t) == %d, %ssize_alignment_error);\n' % (structname, self.size, structname)

        return structure

    def gen_func(self):
        fname = 'Crumb_%s_%s' % (self.cat['name'], self.name)
        ct = 'Crumb_%s_%s_t' % (self.cat['name'], self.name)

        enums = ''
        first_loop = True
        args = ''
        assign = ''

        assign += '        entry->%s = %d;\n' % (CATEGORYID_STR, self.cat['id'])
        assign += '        entry->%s = %d;\n' % (ENTRYID_STR, self.id)
        assign += '        entry->%s = %s;\n' % (SIZE_STR, int(self.size / WORDSIZE) - 1)

        for f in self.packedfields:
            # Need to take care when generating the commas in the C argument list.  This
            # just ensures there's no trailing comma after the last parameter in the function
            # definition.  Since the timestamp and sequence don't get passed into the logging
            # function, skip over this for those fields.
            if f[F_NAME] != 'sequence' and f[F_NAME] != 'timestamp':
                if first_loop:
                    first_loop = False
                else:
                    args += ', '

            # Parameters are either built-in C types or an enum for a log entry with named
            # values.
            if f[F_RAW] in BUILTIN_CTYPES:
                if f[F_NAME] != 'sequence' and f[F_NAME] != 'timestamp':
                    args += '%s %s' % (f[F_CTYPE], f[F_NAME])
            else:
                enum = 'Crumb_%s_%s_enum' % (self.cat['name'], self.name)
                args += '%s %s' % (enum, f[F_NAME])

                # Build the list of fields for the C enum.
                for e in f[F_RAW].split(' '):
                    enums += ('    Crumb_%s_%s_%s,\n' % (self.cat['name'], self.name, e)).upper()

            # Assign each field in the crumb entry with the appropriate parameter.  Need to check
            # if the field is timestamp or sequence and use the appropriate function that's defined
            # by the actual C implementation (e.g., ramcrumb.c).
            if f[F_NAME] == 'timestamp':
                assign += '        entry->%s = %s;\n' % (f[F_NAME], 'Crumb_Timestamp()')
            elif f[F_NAME] == 'sequence':
                assign += '        entry->%s = %s;\n' % (f[F_NAME], 'Crumb_Sequence()')
            else:
                assign += '        entry->%s = %s;\n' % (f[F_NAME], f[F_NAME])

        f = ''

        # If an enum was necessary, create the enum typedef.
        if len(enums) > 0:
            f += CRUMB_ENUM % (enums, 'Crumb_%s_%s_enum' % (self.cat['name'], self.name))

        # Build the logging function.
        f += (CRUMB_FUNC % (fname, args, self.cat['id'], self.id, ct, ct, self.size, assign))

        return f

    def getdata(self, name, bindata):
        """Return the actual data from a crumb file for the entry based on the structure
        field name.
        """
        return bindata[self.fieldbyname[name][F_POS]]

    def process(self, bindata):
        """Given the binary data for an entry, generate its formatted string representation
        and return the string to caller.  The format string for the entry in the crumb
        definition file will have "%{name}" sections.  This function replaces it with the
        data from the field with the same name.  The formatting options are the same as those
        in python.  If the formatting option is omitted, a default in (%d) is used or the
        enumeration name if the field was specified as a list of named values.
        """


        data = struct.unpack(self.packfmt, bindata)

        output = ''

        if 'timestamp' in self.fieldbyname:
            output += '[%012f] ' % (self.getdata('timestamp', data) * TIMESCALE)

        output += '%s-%s: ' % (self.cat['name'], self.name)

        # This is basically a highly-simplified "printf" that lives within the restrictions
        # of the allowable types of a crumb file (i.e., built-in C types or an enumerated
        # field.
        i = 0
        while i < len(self.format):
            c = self.format[i]

            if c == '%':
                v = c
                i += 1
                c = self.format[i]
                while c != '{':
                    v += c
                    i += 1
                    c = self.format[i]

                name = ''
                i += 1
                c = self.format[i]
                while c != '}':
                    name += c
                    i += 1
                    c = self.format[i]

                i += 1

                f = self.fieldbyname[name]

                # Default formatting...
                if v == '%':
                    # Need to check if this is a numeric or enumerated type...
                    if f[F_RAW] in BUILTIN_CTYPES:
                        output += '%d' % data[f[F_POS]]
                    else:
                        output += '%s' % f[F_RAW].split(' ')[data[f[F_POS]]]
                else:
                    output += v % data[f[F_POS]]

            else:
                output += c
                i += 1

        return output
  


HDR_FILL=0xfe
HDR_SIZE=0
HDR_CAT=1
HDR_ENT=2

def check_crumb_def(crumbdef):
    """Do some sanity checking on the crumb definition file.  This is not
    at all comprehensive, but will catch a lot of common errors.  Unfortunately,
    errors that aren't caught will probably cause some really odd behavior.
    """

    if 'wordsize' not in crumbdef:
        raise CrumbError('Definition of word size for target platform required ("wordsize":bits).')

    if 'byteorder' not in crumbdef:
        raise CrumbError('Byte order must be specified (add "byteorder:big|little|netword").')

    cats = []
    for c in crumbdef['categories']:
        if 'name' not in c:
            raise CrumbError('Category requires a name field.')

        if c['name'] in cats:
            raise CrumbError('Category "%s" previously defined.' % c['name'])

        cats.append(c['name'])

    if 'filters' in crumbdef:
        if not isinstance(crumbdef['filters'], bool):
            raise CrumbError('The "filters" field must be true or false.')

CDEFINES = ''
def load_crumb_def(crumbdef, crc):
    global WORDSIZE
    global TIMESCALE
    global TIMESTAMP
    global SEQUENCE
    global HDRPACKFMT
    global BOF
    global NUM_CATEGORIES
    global MAX_ENTPERCAT
    global CDEFINES


    WORDSIZE = crumbdef['wordsize'] / 8

    if crumbdef['byteorder'].lower() == 'big':
        HDRPACKFMT = '>BBB'
        BOF = '>'
    elif crumbdef['byteorder'].lower() == 'little':
        HDRPACKFMT = '<BBB'
        BOF = '<'
    elif crumbdef['byteorder'].lower() == 'network':
        HDRPACKFMT = '!BBB'
        BOF = '!'
    else:
        raise CrumbError('Invalid byte order "%s"; must be big|little|netword.' % crumbdef['byteorder'])


    if 'timescale' in crumbdef:
        TIMESCALE = crumbdef['timescale']

    if 'timestamp' in crumbdef:
        TIMESTAMP = crumbdef['timestamp']

    if 'sequence' in crumbdef:
        SEQUENCE = crumbdef['sequence']


    entpercat = []
    entries = {}
    catid = 0
    for c in crumbdef['categories']:
        c['id'] = catid

        CDEFINES += '#define CRUMB_CAT_%s   %d\n' % (c['name'].upper(), catid)

        NUM_CATEGORIES += 1

        entpercat.append(0)
        entryid = 0
        for e in c['entries']:
            CDEFINES += '#define CRUMB_ENTRY_%s   %d\n' % (e['name'].upper(), entryid)
            entpercat[catid] += 1
            entries[ catid << 16 | entryid ] = Entry(c, e, entryid)
            entryid += 1
    
        catid += 1

    for c in entpercat:
        if c > MAX_ENTPERCAT:
            MAX_ENTPERCAT = c


    return entries

FILTER_STRUCT = """
typedef struct {
    uint32_t    filters%s;
} Crumb_Filters_t;

extern Crumb_Filters_t __crumb_filters;
"""

def generate_filters(crumbdef, entries):
    if 'filters' not in crumbdef or crumbdef['filters'] == False:
        filter_struct = FILTER_STRUCT % ''
    else:
        catelms = NUM_CATEGORIES / WORDSIZE
        if (NUM_CATEGORIES % WORDSIZE) != 0:
            catelms += 1

        entelms = MAX_ENTPERCAT / WORDSIZE
        if (MAX_ENTPERCAT % WORDSIZE) != 0:
            entelms += 1

        filter_struct = FILTER_STRUCT % ('[%d][%d]' % (catelms, entelms))
        filter_struct += '#define __CRUMB_FILTERS_ENABLED\n'

    return filter_struct

def makeheaderfile(crumbdef, entries, crc, outh):

    crumbi_t = getctype(crumbdef['wordsize'])

    h = ''


    h += 'typedef %s crumbi_t;\n' % crumbi_t
    h += 'static const uint32_t CRUMB_CRC = 0x%08x;\n' % crc
    h += 'static const size_t CRUMB_SCALE = %d;\n' % WORDSIZE
    h += '\n'

    if 'sequence' in crumbdef:
        crumbseq_t = getctype(crumbdef['sequence'])
        h += 'typedef %s crumbseq_t;\n' % crumbseq_t
        h += 'crumbseq_t Crumb_Sequence();\n'

    if 'timestamp' in crumbdef:
        crumbtime_t = getctype(crumbdef['timestamp'])
        h += 'typedef %s crumbtime_t;\n' % crumbtime_t
        h += 'crumbtime_t Crumb_Timestamp();\n'

    h += 'void* Crumb_GetEntry(size_t size);\n'

    h += HEADER_STRUCT


    maxsize = 0
    for e in entries:
        maxsize = max(maxsize, entries[e].size)

        h += entries[e].gen_struct() + '\n'


    for e in entries:
        h += entries[e].gen_func() + '\n'

    h += '#define CRUMB_MAX_ENTRY_SIZE          %d\n' % maxsize
    h += CDEFINES

    h += generate_filters(crumbdef, entries)

    outh.write(H_FILE % h)

def process(entries, crc, fin, force):
    bindata = fin.read()
    if crc != struct.unpack(BOF + 'I', bindata[:4])[0]:
        warnmsg = """WARNING: Crumb definition file does not match the one used 
to produce the binary crumb data.  Use the 'force' option to make try and 
process the data.
"""

        print(warnmsg);
        if not force:
            sys.exit(0)

    off = 4
    while True:
        hdr = struct.unpack(HDRPACKFMT, bindata[off:off+HEADER_SIZE])
        if hdr[HDR_CAT] == HDR_FILL:
            break

        e = entries[(hdr[HDR_CAT] << 16) | hdr[HDR_ENT]]
        end = off + (hdr[HDR_SIZE]+1) * 4
        print(e.process(bindata[off:end]))

        off += (hdr[HDR_SIZE]+1) * 4;



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("crumbfile", type=str, 
                        help='Path to Crumb definition file')
    parser.add_argument('-g', "--generate", action='store_true',
                        help='Generate C header file.')
    parser.add_argument('-p', '--process', type=str,
                        help='Process binary Crumb trace file')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Ignore different versions of crumb definition and trace data.')
    args = parser.parse_args()

    try:
        with open(args.crumbfile) as data_file:
            crc32 =  binascii.crc32(open(args.crumbfile,'rb').read()) & 0xFFFFFFFF;
            data = json.load(data_file)

            if 'crumbs' not in data:
                raise CrumbError('Crumb definition file doesn\'t have a "crumbs" section.')

            check_crumb_def(data['crumbs'])
            entries = load_crumb_def(data['crumbs'], crc32)

            if args.generate:
                with open('crumbauto.h', 'w') as fout:
                    makeheaderfile(data['crumbs'], entries, crc32, fout)

            if args.process != None:
                with open(args.process, 'rb') as fin:
                    process(entries, crc32, fin, args.force)


    except CrumbError as crerr:
        print('Error: %s\n' % crerr.msg)
    except IOError as ioerr:
        print(str(ioerr))


