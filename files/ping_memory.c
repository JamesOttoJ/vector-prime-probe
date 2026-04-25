#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <sched.h>
#include <errno.h>
#include <time.h>

extern void *getTimings();


#define handle_error_en(en, msg) \
  do {                           \
    errno = en;                   \
    perror(msg);                 \
    exit(EXIT_FAILURE);           \
  } while (0)

int main (void) {
    int s, j;
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    cpu_set_t cpuset;
    pthread_t timingThread;
    void *ret;
    struct timespec waitInterval = {0, 100000}; // Wait 1 ns

    CPU_ZERO(&cpuset);
    CPU_SET(50, &cpuset);

    sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);

    pthread_attr_setaffinity_np(&attr, sizeof(cpu_set_t), &cpuset);

    printf ("Getting memory\n");
    if (pthread_create(&timingThread, &attr, &getTimings, NULL) != 0) {
	    printf("Error opening thread\n");
        exit(1);
    }

    char memory[10];
    for(int i = 0; i < 10; i++) {
        memory[i] = 'a';
        nanosleep(&waitInterval, NULL);
    }

//    s = pthread_getaffinity_np(timingThread, sizeof(cpu_set_t), &cpuset);
//    if (s != 0)
//        handle_error_en(s, "pthread_getaffinity_np");
//
//    printf("Current thread affinity:\n");
//    for (j = 0; j < CPU_SETSIZE; j++)
//        if (CPU_ISSET(j, &cpuset))
//            printf("CPU %d\n", j);

    if (pthread_join(timingThread, &ret) != 0) {
        perror("pthread_join() error");
        exit(3);
    }
    printf("Chars %s\n", memory);
    exit(0);
}
