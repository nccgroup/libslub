# /usr/lib/debug/boot/vmlinux-5.15.0-27-generic
file vmlinux-5.15.0-27-generic
source /home/user/target2204_5.15.0-27/vmlinuz-5.15.0-27-generic-gdb.py 
directory /home/user/target2204_5.15.0-27/jammy/
set substitute-path /build/linux-HMZHpV/linux-5.15.0/ /home/user/target2204_5.15.0-27/jammy

set disassembly-flavor intel

# disable having to press space to page down debugger output
set height 0
set width 0
set pagination off

# allows showing structures with indentation enabled when using "p"
set print pretty on

target remote 192.168.28.1:42040

# this avoids having to manually set the addresses of the kernel modules using "add-symbol-file"
lx-symbols

source libslub.py

set logging file gdb.log
set logging overwrite on
set logging on

########### cgroup ###########

# cgroup_init_fs_context() -> after "ctx = kzalloc()" returns
# process="test1"
break kernel/cgroup/cgroup.c:2185
commands
    silent
    #printf "cgroup = 0x%lx (alloc) (process=%s)\n", ctx, $lx_current()->comm
    sbmeta add ctx tag "CGROUP.M" --append
    sbslabdb add kmalloc-96 ctx
    sbcache -n kmalloc-96 --show-region -H ctx --highlight-only --object-only --object-info --hide-title
    continue
end

# cgroup_fs_context_free -> before kfree(ctx)
# process="test1"
# this points way before the kfree(ctx) which would still work but anyway
#break kernel/cgroup/cgroup.c:2144
#b* cgroup_fs_context_free+84
#commands
#    silent
#    #printf "cgroup = 0x%lx (before free) (process=%s)\n", ctx, $lx_current()->comm
#    sbcache -n kmalloc-96 --show-region -H ctx --highlight-only --object-only --object-info --hide-title
#    continue
#end

# cgroup_fs_context_free -> after kfree(ctx)
# this is pointing to the following function so not working
#break cgroup.c:2145
# process="test1"
b* cgroup_fs_context_free+89
commands
    silent
    #printf "cgroup = 0x%lx (freed) (process=%s)\n", ctx, $lx_current()->comm
    sbmeta add ctx tag "CGROUP.F" --append
    sbslabdb add kmalloc-96 ctx
    sbcache -n kmalloc-96 --show-region -H ctx --highlight-only --object-only --object-info --hide-title
    continue
end

########### tty ###########

# alloc_tty_struct() -> after kzalloc()
# process="test2"
break tty_io.c:3123
commands
    silent
    #printf "tty = 0x%lx (alloc) (process=%s)\n", tty, $lx_current()->comm
    sbmeta add tty tag "TTY.M" --append
    sbslabdb add kmalloc-1k tty
    sbcache -n kmalloc-1k --show-region -H tty --highlight-only --object-only --object-info --hide-title
    continue
end

# free_tty_struct() -> before kfree(tty)
# process="kworker/0:2"
# this points to wrong place
#break tty_io.c:169
# see above why we hardcode the offset (also ya, note the name mismatch but breakpoint works)
#b* release_one_tty+223
#commands
#    silent
#    #printf "tty = 0x%lx (before free) (process=%s)\n", tty, $lx_current()->comm
#    sbcache -n kmalloc-1k --show-region -H tty --highlight-only --object-only --object-info --hide-title
#    continue
#end

# free_tty_struct() -> after kfree(tty)
# process="kworker/0:2"
# see above why we hardcode the offset (also ya, note the name mismatch but breakpoint works)
b* release_one_tty+228
commands
    silent
    #printf "tty = 0x%lx (freed) (process=%s)\n", tty, $lx_current()->comm
    sbmeta add tty tag "TTY.F" --append
    sbslabdb del kmalloc-1k tty
    sbcache -n kmalloc-1k --show-region -H tty --highlight-only --object-only --object-info --hide-title
    continue
end

continue