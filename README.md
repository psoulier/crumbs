# Crumbs

Crumbs is a lightweight tracing facility intended for embedded systems.

Each entry has a minimum size of 4 bytes + WORDSIZE.  While compact, this still
won't be suitable for extremely constrained systems.  Realistically, the Crumb
trace buffer would probably need to be at least 1KB to be useful (64 entries if
each entry is 16 bytes).



## TODO:
* Validate crumb definition file (a.k.a. error checking)
    - Make sure all fields that get used as C symbols are valid       
    - Make sure all required fields exist
* Implement time scaling.
* Filters
    - Need three types: entry/category, category, and global.
    - Created at generation time.
    - Global filter required to shut it off when not initialized.
* Make crumbs a class - useful if someone wanted to use it as a library for some
kind of interactive debug tool or something.
* Get base types figured out (crumbi_t?)
* Crumb_erasebank needs a parameter to indicate of most recent buffer needs to
be flushed.
* Debug bank find first
* Initial state zero-init, 0xff.... init?
* Try and think of a way to verify the word size from JSON file matches the
actual C code.

## Other Ideas
* Buffered flash crumb.  If flash is not accessible by memory read/write, traces
could be buffered in RAM and the written out once full.  This is a use case that
fits systems that load application from flash over a serial bus into RAM but do
not access flash through memory rd/wr.  This could probably fit in with the
existing design with a little tweaking.
* Triggers - may be nice to stop not overwrite trace after a specific event(s)
occurs.
