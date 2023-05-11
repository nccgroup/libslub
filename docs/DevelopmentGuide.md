<!-- vim-markdown-toc GFM -->

* [Design](#design)
* [Glossary](#glossary)
    * [Details](#details)
* [Python requirements](#python-requirements)
    * [Python namespaces limitation](#python-namespaces-limitation)
    * [Do not use `from XXX import YYY`](#do-not-use-from-xxx-import-yyy)
* [SLUB internals](#slub-internals)
    * [kernel source code](#kernel-source-code)

<!-- vim-markdown-toc -->

# Design

The code was rewritten from [SlabDbg](https://github.com/NeatMonster/slabdbg) by NeatMonster and taking into account the [x64 port](https://github.com/Kyle-Kyle/slabdbg/) from Kyle-Kyle.

Lots of design decisions were taken from [libptmalloc](https://github.com/nccgroup/libptmalloc).

# Glossary

* A "slab" is the generic term to refer to one of the following:
    * the "main slab" associated with a CPU core
    * a "partial slab" associated with a CPU core or node
    * a "full slab" associated with the node
* A "memory page" is backed by the `struct page`
* A "slab" is composed of one or several pages (`struct page`)
* Each "page" (`struct page`) has a corresponding memory region associated with it for allocation
* When we say some allocations happens on a given "slab", we actually mean they happen in its memory region backed by one or several of its `struct page`

## Details

Some terms can be very confusing when talking about things related to slab, SLAB, Slab, page, etc. so we try to define a way to talk about things and will try to name variables and functions in libslub the same way we talk about them here.

The "slab" can refer to many things:

* It is common to talk about the "Slab" allocator as the high level Linux kernel allocator interface that can be implemented by the "SLOB", "SLAB" or "SLUB" implementation. 
    * "SLOB" is optimized for memory space but is slow, so is generally used in embedded systems.
    * "SLAB" is optimized for speed but takes a lot of memory space due to the way it tracks things. 
    * "SLUB" is the default Linux kernel allocator nowadays and tried to solve "SLAB" problems by reducing how things are tracked in the kernel.
* It is common to say that kernel allocations happen on a given "slab cache". This means they are allocated on the "kmalloc-1k", "kmalloc-64", "TCPv6", etc. (as shown by `cat /proc/slabinfo`). However, we also generally say that a "slab cache" contains several "slabs" associated with various CPU cores. Generally what we mean by that is that the "slab cache" (`struct kmem_cache`) has associated "slab cache per cpu core" (`struct kmem_cache_cpu`), and each of these "slab cache per cpu core" has a "main slab" (aka "current slab") it uses for allocating new objects. And the "slab cache per cpu core" also has "partial slab(s)" that are not currently used for new allocations but could be used if the "main slab" becomes full and no objects can be allocated from it.
* There is also the concept of "full slabs" which are slabs that contains allocated objects entirely. These are not associated with any CPU but they can become associated with a given CPU once one object from them is freed (so they are not full slabs anymore)
* A "slab" as defined above is composed of one or many memory pages (`struct page`). Indeed since a page is 4096 bytes, for instance if the object size used for a slab is more than that (e.g. 5000 bytes), several contigous memory pages will be required to allocate one single object. Consequently, in the Linux kernel, when talking about a slab, you may think of it as a linked list of `struct page` where the first one contains the interesting info about the slab such as the total number of objects, the number of inuse objects, etc.

A "node" can refer to a "CPU" or "multiple CPUs". But generally all the CPU cores are given each of them a `struct kmem_cache_cpu`.

# Python requirements

libslub only supports Python >= 3.7. This is for commodity reasons, as detailed below and in the following [post](https://stackoverflow.com/questions/62524794/python-submodule-importing-correctly-in-python-3-7-but-not-3-6).

## Python namespaces limitation

One quirk of Python namespaces and tools like gdb which allows importing Python files is that it won't reload files that have been already imported, except if you especially request it. So let's consider a scenario where you source `A.py` which imports `B.py` (using `import B` or `from B import *`), it will import `B`. Now you modify `B.py` and re-source `A.py` in your debugger to test your changes. Unfortunately the changes made to `B.py` won't be taken into account. The only solution will be to reload gdb entirely before reloading `A.py`.

To work around that limitation, we use `importlib.reload()` in the dev branch for all the imported modules. This slows down significantly reloading libslub but it is still faster than reloading gdb :)

## Do not use `from XXX import YYY`

When modifying libslub's source code, it is handy to be able to re-import libslub in gdb without having to restart gdb itself.

We need to use `importlib.reload()` for all imported sub modules, hence we never use `from XXX import YYY` but instead always use `import XXX` so we can then use `importlib.reload(XXX)`.

# SLUB internals

* https://lwn.net/Articles/229984/ and https://lwn.net/Articles/229096/
* https://www.youtube.com/watch?v=pFi-JKgoX-I 
    * from 28 min
    * but doesn't mention per cpu partial lists
* https://events.static.linuxfound.org/images/stories/pdf/klf2012_kim.pdf
* https://ruffell.nz/programming/writeups/2019/02/15/looking-at-kmalloc-and-the-slub-memory-allocator.html
* https://duasynt.com/blog/linux-kernel-heap-feng-shui-2022
* https://hammertux.github.io/slab-allocator (recommended)
* https://sam4k.com/linternals-memory-allocators-part-1/

## kernel source code

* SLUB_DEBUG: https://elixir.bootlin.com/linux/v5.15/source/init/Kconfig#L1869
* SLUB_DEBUG_ON: https://elixir.bootlin.com/linux/v5.15/source/lib/Kconfig.debug#L674
* slab_caches (global): https://elixir.bootlin.com/linux/v5.15/source/mm/slab.h#L72
* struct kmem_cache_cpu: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L48
* struct page: https://elixir.bootlin.com/linux/v5.15/source/include/linux/mm_types.h#L70
* struct kmem_cache_node: https://elixir.bootlin.com/linux/v5.15/source/mm/slab.h#L533
* struct kmem_cache_order_objects: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L83