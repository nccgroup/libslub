<!-- vim-markdown-toc GFM -->

* [Usage](#usage)
    * [libslub commands](#libslub-commands)
    * [Commands' usage](#commands-usage)
* [Common usage and example](#common-usage-and-example)
    * [sblist](#sblist)
    * [sbcache](#sbcache)
    * [sbobject](#sbobject)
    * [sbmeta](#sbmeta)
    * [sbslabdb](#sbslabdb)
* [Cache](#cache)
* [Comparison with other tools](#comparison-with-other-tools)
    * [SlabDbg](#slabdbg)

<!-- vim-markdown-toc -->

# Usage

## libslub commands

The `sbhelp` command lists all the commands provided by libslub:

```
(gdb) sbhelp
sbhelp              List all libslub commands
sbcache             Print the metadata and contents of one or all slab cache(s)
sbobject            Print the metadata and contents of one or more objects/chunks
sblist              Show information about all the slab caches on the system
sbmeta              Handle metadata associated with object/chunk addresses
sbslabdb            Handle saving slab addresses associated with object/chunk addresses
sbcrosscache        Identify adjacent memory regions from two different slabs
Note: Use a command name with -h to get additional help
Note: Modify libslub.cfg if you want to enable or disable sbbreak/sbtrace/sbwatch commands (may crash GDB due to broken finish)
```

## Commands' usage

Each command has detailed usage that you can print using `-h`:

```
(gdb) sbcache -h
usage:  [-c COUNT] [--cpu CPU] [--main-slab] [--partial-slab] [--node-slab] [--full-slab] [--show-freelist]
        [--show-lockless-freelist] [--show-region] [--hide-title] [--object-only] [-n NAME] [-v] [-h] [-x] [-X HEXDUMP_UNIT]
        [-m MAXBYTES] [-N] [-p PRINT_OFFSET] [-M METADATA] [-I HIGHLIGHT_TYPES] [-H HIGHLIGHT_ADDRESSES] [-G HIGHLIGHT_METADATA]
        [--highlight-only] [--use-cache] [-s SEARCH_VALUE] [-S SEARCH_TYPE] [--match-only] [--skip-header] [--depth SEARCH_DEPTH]
        [--cmds COMMANDS] [--object-info] [-o]

Print the metadata and contents of one or all slab cache(s)

If you don't specify any slab cache name, it will print all of them but it will take some time to parse structures in memory

optional arguments:
  -c COUNT, --count COUNT
                        Number of chunks to print linearly in each slab or in each freelist
  --cpu CPU             Show CPU specified only, instead of all slabs (Ignore node's partial slabs and full slabs)
  --main-slab           Show main slabs for CPUs only, instead of all slabs (Ignore CPU partial slabs, node's partial slabs and full slabs)
  --partial-slab        Show partial slabs for CPUs only, instead of all slabs (Ignore CPU main slabs, node's partial slabs and full slabs)
  --node-slab           Show partial slabs for nodes only, instead of all slabs (Ignore CPU main/partial slabs and node's full slabs)
  --full-slab           Show full slabs only, instead of all slabs (Ignore CPU main and partial slabs, node's partial slabs)
  --show-freelist       Show the freelists for each slab (not shown by default)
  --show-lockless-freelist
                        Show the freelist associated to a CPU for the main slab (not shown by default)
  --show-region         Show the objects in the memory region for each slab (not shown by default)
  --hide-title          Hide the "region:" or "freelist:" titles (shown by default) when showing regions or freelists
  --object-only         Do not show structures' fields and show objects only (still requires --show-freelist and/or --show-region)
  -n NAME               The slab cache name (e.g. kmalloc-64). Use "sblist" to get them all

generic optional arguments:
  -v, --verbose         Use verbose output (multiple for more verbosity)
  -h, --help            Show this help
  -x, --hexdump         Hexdump the object/chunk contents
  -X HEXDUMP_UNIT       Specify hexdump unit (1, 2, 4, 8 or dps) when using -x (default: 1)
  -m MAXBYTES, --maxbytes MAXBYTES
                        Max bytes to dump with -x
  -N                    Do not output the trailing newline (summary representation)
  -p PRINT_OFFSET       Print data inside at given offset (summary representation)
  -M METADATA, --metadata METADATA
                        Comma separated list of metadata to print (previously stored with the 'sbmeta' command)
  -I HIGHLIGHT_TYPES, --highlight-types HIGHLIGHT_TYPES
                        Comma separated list of chunk types (M, F) for objects/chunks we want to highlight in the output
  -H HIGHLIGHT_ADDRESSES, --highlight-addresses HIGHLIGHT_ADDRESSES
                        Comma separated list of addresses for objects/chunks we want to highlight in the output
  -G HIGHLIGHT_METADATA, --highlight-metadata HIGHLIGHT_METADATA
                        Comma separated list of metadata (previously stored with the 'sbmeta' command)
                        for objects/chunks we want to highlight in the output
  --highlight-only      Only show the highlighted objects/chunks (instead of just '*' them)
  --use-cache           Do not fetch any internal slab data if you know they haven't changed since
                        last time they were cached
  -s SEARCH_VALUE, --search SEARCH_VALUE
                        Search a value and show match/no match
  -S SEARCH_TYPE, --search-type SEARCH_TYPE
                        Specify search type (string, byte, word, dword or qword) when using -s (default: string)
  --match-only          Only show the matched chunks (instead of just show match/no match)
  --skip-header         Don't include chunk header contents in search results
  --depth SEARCH_DEPTH  How far into each chunk to search, starting from chunk header address
  --cmds COMMANDS       Semi-colon separated list of debugger commands to be executed for each chunk that is displayed
                        ('@' is replaced by the chunk address)
  --object-info         Show object info such as its slab/cpu/node/etc. (summary representation)
  -o, --address-offset  Print offsets from the first printed chunk instead of addresses
```

# Common usage and example

## sblist

To show all the slab caches:

```
(gdb) sblist
name                    objs inuse slabs size obj_size objs_per_slab pages_per_slab
AF_VSOCK                  12     2     1 1280     1248            12              4
ext4_groupinfo_4k          0     0     0  192      192            21              1
fsverity_info              0     0     0  256      256            16              1
fscrypt_info               0     0     0  136      136            30              1
MPTCPv6                    0     0     0 2048     2016            16              8
ip6-frags                  0     0     0  184      184            22              1
PINGv6                     0     0     0 1216     1200            13              4
RAWv6                     13     6     1 1216     1200            13              4
UDPv6                     12     2     1 1344     1344            12              4
tw_sock_TCPv6              0     0     0  248      240            16              1
request_sock_TCPv6         0     0     0  304      296            13              1
TCPv6                     13     1     1 2432     2392            13              8
[...]

name: slab cache name used for display
objs: total number of chunks in that slab cache
inuse: number of allocated chunks in that slab cache
slabs: number of slabs allocated for that slab cache
size: chunk size (with metadata)
obj_size: object size (without metadata)
objs_per_slab: number of objects per slab
pages_per_slab: number of pages per slab
```

To show only the default `kmalloc-XX` slab caches:

```
(gdb) sblist -k
name                    objs inuse slabs size obj_size objs_per_slab pages_per_slab
kmalloc-8k                12     9     3 8192     8192             4              8
kmalloc-4k                24    19     3 4096     4096             8              8
kmalloc-2k               128    86     8 2048     2048            16              8
kmalloc-1k               272   236    17 1024     1024            16              4
kmalloc-512              672   510    42  512      512            16              2
kmalloc-256              128   102     8  256      256            16              1
kmalloc-192              693   508    33  192      192            21              1
kmalloc-128               32     5     1  128      128            32              1
kmalloc-96               924   773    22   96       96            42              1
kmalloc-64              1664  1520    26   64       64            64              1
kmalloc-32              4352  3263    34   32       32           128              1
kmalloc-16              3328  2966    13   16       16           256              1
kmalloc-8               2560  2367     5    8        8           512              1
```

To show  all the slab caches matching a certain pattern:

```
(gdb) sblist -p file
name                    objs inuse slabs size obj_size objs_per_slab pages_per_slab
ecryptfs_file_cache        0     0     0   16       16           256              1
file_lock_cache           18     9     1  216      216            18              1
file_lock_ctx             73    25     1   56       56            73              1
seq_file                  34    18     1  120      120            34              1
lsm_file_cache          4420  3999    26   24       24           170              1
files_cache               92    70     4  704      704            23              4
trace_event_file         782   656    17   88       88            46              1
```

## sbcache

To print the main slab information for the `kmalloc-1k` slab cache:

```
(gdb) sbcache -n kmalloc-1k --main-slab
struct kmem_cache @ 0xffff888100041b00 {
  name        = kmalloc-1k
  flags       = __CMPXCHG_DOUBLE
  offset      = 0x200
  size        = 1024 (0x400)
  object_size = 1024 (0x400)
  struct kmem_cache_cpu @ 0xffff888139e36160 (cpu 0) {
    freelist = 0xffff88801ae1c000 (5 elements)
    page     = struct page @ 0xffffea00006b8700 {
      objects  = 16
      inuse    = 16 (real = 11)
      frozen   = 1
      freelist = 0x0 (0 elements)
      region   @ 0xffff88801ae1c000-0xffff88801ae20000 (16 elements)
  struct kmem_cache_cpu @ 0xffff888139e76160 (cpu 1) {
    freelist = 0xffff88800e148c00 (2 elements)
    page     = struct page @ 0xffffea0000385200 {
      objects  = 16
      inuse    = 16 (real = 14)
      frozen   = 1
      freelist = 0x0 (0 elements)
      region   @ 0xffff88800e148000-0xffff88800e14c000 (16 elements)
```

To print the objects on the main slab for the `kmalloc-1k` slab cache and only for the first CPU (index 0):

```
(gdb) sbcache -n kmalloc-1k --main-slab  --cpu 0 --show-region
struct kmem_cache @ 0xffff888100041b00 {
  name        = kmalloc-1k
  flags       = __CMPXCHG_DOUBLE
  offset      = 0x200
  size        = 1024 (0x400)
  object_size = 1024 (0x400)
  struct kmem_cache_cpu @ 0xffff888139e36160 (cpu 0) {
    freelist = 0xffff88801ae1c000 (5 elements)
    page     = struct page @ 0xffffea00006b8700 {
      objects  = 16
      inuse    = 16 (real = 11)
      frozen   = 1
      freelist = 0x0 (0 elements)
      region   @ 0xffff88801ae1c000-0xffff88801ae20000 (16 elements)
        0xffff88801ae1c000 F (region start)
        0xffff88801ae1c400 M
        0xffff88801ae1c800 F
        0xffff88801ae1cc00 M
        0xffff88801ae1d000 M
        0xffff88801ae1d400 M
        0xffff88801ae1d800 F
        0xffff88801ae1dc00 M
        0xffff88801ae1e000 M
        0xffff88801ae1e400 M
        0xffff88801ae1e800 F
        0xffff88801ae1ec00 M
        0xffff88801ae1f000 M
        0xffff88801ae1f400 M
        0xffff88801ae1f800 M
        0xffff88801ae1fc00 F (region end)
```

To print the objects on the lockless freelist associated with the main slab for the `kmalloc-1k` slab cache and only for the first CPU (index 0):

```
(gdb) sbcache -n kmalloc-1k --main-slab --cpu 0 --show-lockless-freelist
struct kmem_cache @ 0xffff888100041b00 {
  name        = kmalloc-1k
  flags       = __CMPXCHG_DOUBLE
  offset      = 0x200
  size        = 1024 (0x400)
  object_size = 1024 (0x400)
  struct kmem_cache_cpu @ 0xffff888139e36160 (cpu 0) {
    freelist = 0xffff88801ae1c000 (5 elements)
      0xffff88801ae1c000 F [1]
      0xffff88801ae1e800 F [2]
      0xffff88801ae1c800 F [3]
      0xffff88801ae1fc00 F [4]
      0xffff88801ae1d800 F [5]
    page     = struct page @ 0xffffea00006b8700 {
      objects  = 16
      inuse    = 16 (real = 11)
      frozen   = 1
      freelist = 0x0 (0 elements)
      region   @ 0xffff88801ae1c000-0xffff88801ae20000 (16 elements)
```

And to show a short version with only the object allocations:

```
(gdb) sbcache -n kmalloc-1k --main-slab --cpu 0 --show-lockless-freelist --object-only
    lockless freelist:
      0xffff88801ae1c000 F [1]
      0xffff88801ae1e800 F [2]
      0xffff88801ae1c800 F [3]
      0xffff88801ae1fc00 F [4]
      0xffff88801ae1d800 F [5]
```

To print the objects on the partial slabs for the `kmalloc-1k` slab cache and only for the first CPU (index 0):

```
(gdb) sbcache -n kmalloc-1k --partial-slab --cpu 0
struct kmem_cache @ 0xffff888100041b00 {
  name        = kmalloc-1k
  flags       = __CMPXCHG_DOUBLE
  offset      = 0x200
  size        = 1024 (0x400)
  object_size = 1024 (0x400)
  struct kmem_cache_cpu @ 0xffff888139e36160 (cpu 0) {
    partial  = struct page @ 0xffffea0004359400 (1/2) {
      objects  = 16
      inuse    = 14
      frozen   = 1
      freelist = 0xffff88810d651400 (2 elements)
      region   @ 0xffff88810d650000-0xffff88810d654000 (16 elements)
    partial  = struct page @ 0xffffea0004345200 (2/2) {
      objects  = 16
      inuse    = 15
      frozen   = 1
      freelist = 0xffff88810d14bc00 (1 elements)
      region   @ 0xffff88810d148000-0xffff88810d14c000 (16 elements)
```

To print a short version of the freelists associated with the partial slabs for the `kmalloc-1k` slab cache and only for the first CPU (index 0):

```
(gdb) sbcache -n kmalloc-1k --partial-slab --cpu 0 --show-freelist --object-only
    regular freelist:
        0xffff88810d651400 F [1]
        0xffff88810d650c00 F [2]
    regular freelist:
        0xffff88810d14bc00 F [1]
```

## sbobject

To check if an address is a valid object address:

```
(gdb) sbobject 0xffff88801ae1c000
Fetching all slab caches, this will take a while... (use -n to specify a slab cache)
Fetched in 45s
0xffff88801ae1c000 F (region start)
```

To check if an address is a valid object address, in a specific slab cache:

```
(gdb) sbobject -n kmalloc-1k 0xffff88801ae1c000
0xffff88801ae1c000 F (region start)
```

To show 4 objects adjacent to a specific address:

```
(gdb) sbobject -n kmalloc-1k 0xffff88801ae1c000 -c 4
0xffff88801ae1c000 F (region start)
0xffff88801ae1c400 M
0xffff88801ae1c800 F
0xffff88801ae1cc00 M
```

NOTE: `F` is for freed object and `M` for allocated (malloc-ed) object.

To show all objects adjacent to a specific address until we reach the end of the slab:

```
(gdb) sbobject -n kmalloc-1k 0xffff88801ae1c000 -c unlimited
0xffff88801ae1c000 F (region start)
0xffff88801ae1c400 M
0xffff88801ae1c800 F
0xffff88801ae1cc00 M
0xffff88801ae1d000 M
0xffff88801ae1d400 M
0xffff88801ae1d800 F
0xffff88801ae1dc00 M
0xffff88801ae1e000 M
0xffff88801ae1e400 M
0xffff88801ae1e800 F
0xffff88801ae1ec00 M
0xffff88801ae1f000 M
0xffff88801ae1f400 M
0xffff88801ae1f800 M
0xffff88801ae1fc00 F (region end)
Stopping due to end of memory region
```

To show the content of objects as hexdumps, and limited to the first 16 bytes:

```
(gdb) sbobject -n kmalloc-1k 0xffff88801ae1c000 -c 4 -x -m 0x10
0xffff88801ae1c000 F (region start)
0x400 bytes of object data:
0xffff88801ae1c000:  AD DE AD DE 00 00 00 00  00 00 00 00 00 00 00 00  ................
--
0xffff88801ae1c400 M
0x400 bytes of object data:
0xffff88801ae1c400:  00 B8 A4 13 81 88 FF FF  01 00 00 00 00 00 00 00  ................
--
0xffff88801ae1c800 F
0x400 bytes of object data:
0xffff88801ae1c800:  AD DE AD DE 00 00 00 00  00 00 00 00 00 00 00 00  ................
--
0xffff88801ae1cc00 M
0x400 bytes of object data:
0xffff88801ae1cc00:  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
```

To show 4 objects adjacent to a specific address and highlighting a specific address:

```
(gdb) sbobject -n kmalloc-1k 0xffff88801ae1c000 -c 4 -H 0xffff88801ae1c400
0xffff88801ae1c000 F (region start)
* 0xffff88801ae1c400 M
0xffff88801ae1c800 F
0xffff88801ae1cc00 M
```

## sbmeta

To find some `struct* tty_struct` allocated/free objects:

```
(gdb) sbcache -n kmalloc-1k -M tag --show-region --cmds "p ((struct tty_struct*)@)->ops" -N
...
    partial  = struct page @ 0xffffea00003f1d00 (14/14) {
      objects  = 16
      inuse    = 12
      frozen   = 0
      freelist = 0xffff88800fc77400 (4 elements)
      region   @ 0xffff88800fc74000-0xffff88800fc78000 (16 elements)
        0xffff88800fc74000 M (region start)        $968 = (const struct tty_operations *) 0xffff88800fc74010
        0xffff88800fc74400 M        $969 = (const struct tty_operations *) 0xffff88800fc74410
        0xffff88800fc74800 M        $970 = (const struct tty_operations *) 0x0 <fixed_percpu_data>
        0xffff88800fc74c00 M        $971 = (const struct tty_operations *) 0x0 <fixed_percpu_data>
        0xffff88800fc75000 M        $972 = (const struct tty_operations *) 0x2 <fixed_percpu_data+2>
        0xffff88800fc75400 M        $973 = (const struct tty_operations *) 0xffff88800fc75410
        0xffff88800fc75800 F        $974 = (const struct tty_operations *) 0xffffffff822be1a0 <pty_unix98_ops>
        0xffff88800fc75c00 M        $975 = (const struct tty_operations *) 0x2 <fixed_percpu_data+2>
        0xffff88800fc76000 F        $976 = (const struct tty_operations *) 0xffffffff822be1a0 <pty_unix98_ops>
        0xffff88800fc76400 M        $977 = (const struct tty_operations *) 0x0 <fixed_percpu_data>
        0xffff88800fc76800 M        $978 = (const struct tty_operations *) 0xffff88800fc76810
        0xffff88800fc76c00 M        $979 = (const struct tty_operations *) 0x2 <fixed_percpu_data+2>
        0xffff88800fc77000 M        $980 = (const struct tty_operations *) 0xffff88800fc77010
        0xffff88800fc77400 F        $981 = (const struct tty_operations *) 0xffffffff822be2c0 <ptm_unix98_ops>
        0xffff88800fc77800 M        $982 = (const struct tty_operations *) 0x2 <fixed_percpu_data+2>
        0xffff88800fc77c00 F (region end)        $983 = (const struct tty_operations *) 0xffffffff822be2c0 <ptm_unix98_ops>
```

To tag a specific object addresses:

```
(gdb) sbmeta add 0xffff88800fc75800 tag TTY
(gdb) sbmeta add 0xffff88800fc76000 tag TTY
(gdb) sbmeta add 0xffff88800fc77400 tag TTY
```

To show the content of chunks in a slab, with their associated tag previously set:

```
(gdb) sbcache -n kmalloc-1k -M tag --show-region
...
    partial  = struct page @ 0xffffea00003f1d00 (14/14) {
      objects  = 16
      inuse    = 12
      frozen   = 0
      freelist = 0xffff88800fc77400 (4 elements)
      region   @ 0xffff88800fc74000-0xffff88800fc78000 (16 elements)
        0xffff88800fc74000 M (region start)
        0xffff88800fc74400 M
        0xffff88800fc74800 M
        0xffff88800fc74c00 M
        0xffff88800fc75000 M
        0xffff88800fc75400 M
        0xffff88800fc75800 F | TTY |
        0xffff88800fc75c00 M
        0xffff88800fc76000 F | TTY |
        0xffff88800fc76400 M
        0xffff88800fc76800 M
        0xffff88800fc76c00 M
        0xffff88800fc77000 M
        0xffff88800fc77400 F | TTY |
        0xffff88800fc77800 M
        0xffff88800fc77c00 F (region end)
```

Also supported by the `sbobject` command:

```
(gdb) sbobject -n kmalloc-1k 0xffff88800fc75800 -M tag -c unlimited
0xffff88800fc75800 F | TTY |
0xffff88800fc75c00 M
0xffff88800fc76000 F | TTY |
0xffff88800fc76400 M
0xffff88800fc76800 M
0xffff88800fc76c00 M
0xffff88800fc77000 M
0xffff88800fc77400 F | TTY |
0xffff88800fc77800 M
0xffff88800fc77c00 F (region end)
Stopping due to end of memory region
```

## sbslabdb

Because the full slabs are not saved by the SLUB allocator, by default, libslub won't be able to show the contents of full slabs.

However, we support helpers to track the full slabs using 2 methods:

1) Breakpoints in SLUB functions to track when new slabs are allocated/destroyed
2) The `sbslabdb` command to log objects addresses and their associated slab

With (1), it is automatically done for all slab caches, and is theoretically the best approach but gdb sometimes crashes when a breakpoint hits too many times. With (2), we restrict saving slabs addresses for the objects we are interested in.

For instance, checking [libslub.gdb](../test/libslub.gdb), you'll see we ask libslub to save slabs for specific object addresses:

```
sbslabdb add kmalloc-1k <addr>
```

Combining that with `sbmeta` command to save the types of allocations:

```
sbmeta add <addr> tag "TTY.M" --append
```

Then we can show the contents of the full slabs:

```
(gdb) sbcache -n kmalloc-1k --full-slab --show-region -M tag
...
    full     = struct page @ 0xffffea00006b7900 (18/20) {
      objects  = 16
      inuse    = 16
      frozen   = 0
      freelist = 0x0 (0 elements)
      region   @ 0xffff88801ade4000-0xffff88801ade8000 (16 elements)
        0xffff88801ade4000 M (region start)
        0xffff88801ade4400 M
        0xffff88801ade4800 M
        0xffff88801ade4c00 M
        0xffff88801ade5000 M
        0xffff88801ade5400 M
        0xffff88801ade5800 M
        0xffff88801ade5c00 M | TTY.M |
        0xffff88801ade6000 M
        0xffff88801ade6400 M
        0xffff88801ade6800 M
        0xffff88801ade6c00 M
        0xffff88801ade7000 M
        0xffff88801ade7400 M
        0xffff88801ade7800 M
        0xffff88801ade7c00 M (region end)
    full     = struct page @ 0xffffea00006b6600 (19/20) {
      objects  = 16
      inuse    = 16
      frozen   = 0
      freelist = 0x0 (0 elements)
      region   @ 0xffff88801ad98000-0xffff88801ad9c000 (16 elements)
        0xffff88801ad98000 M | TTY.M | (region start)
        0xffff88801ad98400 M | TTY.M |
        0xffff88801ad98800 M | TTY.M |
        0xffff88801ad98c00 M | TTY.M |
        0xffff88801ad99000 M | TTY.M |
        0xffff88801ad99400 M | TTY.M |
        0xffff88801ad99800 M | TTY.M |
        0xffff88801ad99c00 M | TTY.M |
        0xffff88801ad9a000 M | TTY.M |
        0xffff88801ad9a400 M | TTY.M |
        0xffff88801ad9a800 M | TTY.M |
        0xffff88801ad9ac00 M | TTY.M |
        0xffff88801ad9b000 M | TTY.M |
        0xffff88801ad9b400 M | TTY.M |
        0xffff88801ad9b800 M | TTY.M |
        0xffff88801ad9bc00 M | TTY.M | (region end)
```

# Cache

In order to speed up the execution of commands, libslub caches the SLUB structures as well as the addresses of the objects when you execute certain commands.

```
(gdb) sbobject 0xffff888003e50400
Fetching all slab caches, this will take a while... (use -n to specify a slab cache)
Fetched in 45s
0xffff888003e50400 M
```

That being said, by default, it won't use the cache, to avoid any misleading info:

```
(gdb) sbobject 0xffff888003e50400
Fetching all slab caches, this will take a while... (use -n to specify a slab cache)
Fetched in 45s
0xffff888003e50400 M
```

If you want to use the cache, when you know nothing has changed since the last cached information (e.g. while stopped in the same breakpoint), you can use the following:

```
(gdb) sbobject 0xffff888003e50400 --use-cache
0xffff888003e50400 M
```

# Comparison with other tools

## SlabDbg


libslub is heavily based on other tools like
[SlabDbg](https://github.com/Kyle-Kyle/slabdbg/) even though a lot has been
changed or added.

The following table shows differences:

| SlabDbg          | libslub      | Note |
|------------------|------------------|------|
| slab list | sblist | sblist support filtering/showing only interesting slab caches |
| slab info | sbcache | sbcache supports lots of features to show what we are interested in. sbcache shows the actual structures name matching source code. |
| slab print | N/A | Not supported yet but adding a sbslab command should be easy to add (due to libslub design) |
| slab trace | sbtrace | |
| slab break | sbbreak | |
| slab watch | sbwatch | |
| N/A | sbobject | |
| N/A | sbmeta   | |
| N/A | sbslabdb | |
