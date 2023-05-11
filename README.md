# libslub

libslub is a python library to examine the SLUB managements structures and object allocations (the Linux kernel heap implementation). It is currently designed for use with GDB but could easily be adapted to work with other debuggers.

It helps understanding SLUB internals and developing Linux kernel exploits.

## Installation

You need any gdb with Python >= 3.7.

Install the Python packages requirements:

```
# pip3 install -r requirements.txt
```

Then using the following command should be enough to get you started.

```
(gdb) source libslub.py
```

It is possible to modify libslub and reload it in your debugger as described in the [Development Guide](docs/DevelopmentGuide.md).

# Usage

Please refer to the [User Guide](docs/UserGuide.md).

# Supported versions

Please refer to the [Supported Versions](docs/SupportedVersions.md).

# Development

Please refer to the [Development Guide](docs/DevelopmentGuide.md).
