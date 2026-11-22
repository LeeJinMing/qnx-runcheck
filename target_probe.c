#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <sys/utsname.h>
#include <time.h>

int main(void)
{
    struct utsname platform;
    struct timespec monotonic;
    if (uname(&platform) != 0 || clock_gettime(CLOCK_MONOTONIC, &monotonic) != 0) {
        perror("target probe");
        return 1;
    }
    printf("Target: %s %s %s\n", platform.sysname, platform.release, platform.machine);
    printf("Monotonic clock: %lld.%09ld s\n", (long long)monotonic.tv_sec, monotonic.tv_nsec);
    return 0;
}
