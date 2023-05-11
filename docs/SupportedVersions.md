<!-- vim-markdown-toc GFM -->

* [gdb/Python versions](#gdbpython-versions)
* [Linux/SLUB versions](#linuxslub-versions)

<!-- vim-markdown-toc -->

# gdb/Python versions

libslub currently works with any gdb version that supports Python >= 3.7, see [DevelopmentGuide.md](DevelopmentGuide.md) for more information.

# Linux/SLUB versions

The goal of libslub is to support all SLUB and Linux versions.

That being said, it has only been tested extensively on a limited number of versions. If you encounter an error when using it, please create an issue or do a pull request.

We have used it extensively on the following versions:

| Linux distribution | Kernel version | Notes |
| -- | -- | -- |
| Ubuntu x64 | 5.15.0-27 | N/A |

The above list will be updated once we test more versions. Feel free to report
any additional working version so we add it to the list.