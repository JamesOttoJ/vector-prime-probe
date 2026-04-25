// GROUND TRUTH: PRIME-PROBE (Targeting L1D Set)
// - Scenario A: PRIME -> PROBE
// - Scenario B: PRIME -> VICTIM -> PROBE
// Prints average cycles for both scenarios and the delta.

#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <x86intrin.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sched.h>
#include <time.h>

#include <immintrin.h>
#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
/********************/

// ------------ constants ------------
#define PAGE_SIZE            4096
#define CACHE_LINE_SIZE        64
#define L1D_ASSOCIATIVITY       8   
#define L1D_SETS               64   
#define TARGET_SET              5   
#define NUM_PAGES            2048   
#define NUM_TRIALS           1000   
#define VICTIM_ROUNDS        1000
#define RESULTS_FOLDER "Prime-Probe_results"

// M1. Targeted Cache Set Mapping
static inline int get_cache_set_index(uintptr_t addr) {
    return (addr >> 6) & (L1D_SETS - 1);
}
static inline void serialize_full(void) { _mm_mfence(); _mm_lfence(); }

// M7. Probe and High-Resolution Timing
static inline uint64_t probe_chase(uint8_t **set, FILE *timing_file) {
    __attribute__((aligned(64))) uint64_t offsets_array[L1D_ASSOCIATIVITY];
    volatile __m512i dst;
    __m512i offsets_vector;
    uint64_t base_addr = (uint64_t) set[0];

    // Translate the list of addresses to a list of offsets
    for (int i = 0; i < L1D_ASSOCIATIVITY; i++) {
        offsets_array[i] = (uint64_t) set[i] - base_addr;
    }
    offsets_vector = _mm512_load_epi64(&offsets_array);

    //_mm_lfence();
    //uint64_t t0 = __rdtsc();
    //_mm_lfence();
    // for (int k = 0; k < L1D_ASSOCIATIVITY; k++) {
    //     p = *(volatile uint8_t **)p; // dependent, volatile loads
    // }
    //dst = (volatile __m512i) _mm512_i64gather_epi64(offsets_vector, base_addr, 1);
    //_mm_lfence();
    //uint64_t t1 = __rdtsc();
    //_mm_lfence();
    // asm volatile ("" :: "r"(p) : "memory"); // keep live
    
    uint64_t t0, t1;

    asm volatile (
        "kxnorw %%k1, %%k1, %%k1\n\t" // Set mask k1 to all 1s
        //"mfence\n\t"
        //"lfence\n\t"
        "rdtsc\n\t"
        //"lfence\n\t"
        "shl $32, %%rdx\n\t"
        "or %%rdx, %%rax\n\t"
        "vpgatherqq (%[base],%[offsets],1), %%zmm1%{%%k1%}\n\t"
        "mov %%rax, %[t0]\n\t"
        //"mfence\n\t"
        //"lfence\n\t"
        "rdtsc\n\t"
        //"lfence\n\t"
        "shl $32, %%rdx\n\t"
        "or %%rdx, %%rax\n\t"
        "mov %%rax, %[t1]\n\t"
        : [t0] "=r" (t0),
          [t1] "=r" (t1)
        : [base] "r" (base_addr),
          [offsets] "v" (offsets_vector)
        : "rax", "rdx", "k1", "memory"
    );
    
    // Return -1 if scheduling propblems between reads caused an outlier
    if (t1 - t0 > 1000 || t1 - t0 < 0) {
        return -1;
    }

    if (timing_file != NULL) fprintf(timing_file, "%ld ", t0);

    return t1 - t0;
}

static inline void shuffle_indices(int *a, int n) {
    for (int i = n - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        int t = a[i]; a[i] = a[j]; a[j] = t;
    }
}

// M3. Pointer-Chase Linked List Setup
static void build_linked_list(uint8_t **set, int *perm) {
    for (int i = 0; i < L1D_ASSOCIATIVITY; i++) {
        uint8_t *cur = set[perm[i]];
        uint8_t *nxt = set[perm[(i + 1) % L1D_ASSOCIATIVITY]];
        *(uint8_t**)cur = nxt; // pointer at bytes [0..7] of the line
    }
}

// M5. Prime Function
static inline void prime_chase(uint8_t **set) {
    // volatile uint8_t *p = set[0];
    // for (int k = 0; k < L1D_ASSOCIATIVITY; k++) {
    //     p = *(volatile uint8_t **)p; // dependent, volatile loads
    // }
    // asm volatile ("" :: "r"(p) : "memory");
    __attribute__((aligned(64))) uint64_t offsets_array[L1D_ASSOCIATIVITY];
    volatile __m512i dst;
    __m512i offsets_vector;
    uint64_t base_addr = (uint64_t) set[0];

    // Translate the list of addresses to a list of offsets
    for (int i = 0; i < L1D_ASSOCIATIVITY; i++) {
        offsets_array[i] = (uint64_t) set[i] - base_addr;
    }
    offsets_vector = _mm512_load_epi64(&offsets_array);

    dst = (volatile __m512i) _mm512_i64gather_epi64(offsets_vector, base_addr, 1);
}

// M6. Victim Function
/* Accessing one cache line */
static void victim_function(uint8_t **victim, int *indices) {
    // Touch only the first cache line in the victim set, away from [0..7] pointer area
    for (int r = 0; r < VICTIM_ROUNDS; r++) {
        uint8_t *a = victim[0] + 8; // Only victim[0], offset +8
        a[0] ^= (uint8_t)r;         // write to allocate in L1D
        (void)*(volatile uint8_t*)a;
    }
}

// M2. Eviction and Victim Set Construction (Verification)
uint64_t get_physical_addr(uint8_t *virt_addr) {
    uint64_t virt_pfn = (uintptr_t)virt_addr / PAGE_SIZE;
    uint64_t offset = virt_pfn * sizeof(uint64_t);

    int fd = open("/proc/self/pagemap", O_RDONLY);
    if (fd < 0) return 0;

    uint64_t entry;
    if (lseek(fd, offset, SEEK_SET) == (off_t)-1 ||
        read(fd, &entry, sizeof(entry)) != sizeof(entry)) {
        close(fd);
        return 0;
    }
    close(fd);

    // Check if page is present
    if (!(entry & (1ULL << 63))) return 0;

    uint64_t phys_pfn = entry & ((1ULL << 55) - 1);
    return (phys_pfn * PAGE_SIZE) + ((uintptr_t)virt_addr % PAGE_SIZE);
}

void print_set_mapping(const char *label, uint8_t **set, int n) {
    printf("%s mapping (virtual -> physical -> set):\n", label);
    for (int i = 0; i < n; i++) {
        uintptr_t vaddr = (uintptr_t)set[i];
        uint64_t  paddr = get_physical_addr(set[i]);
        int set_idx = get_cache_set_index(vaddr);
        printf("  %s[%d]: %p -> phys 0x%lx -> set %d\n", label, i, (void*)vaddr, paddr, set_idx);
    }
}
/***********************************************************************************/

int prime_probe_for_set(int set_number, FILE *summary_file, int run_number) {

    // M2. Eviction and Victim Set Construction
    // Allocate a pool to find lines that map to set_number
    size_t pool_sz = NUM_PAGES * PAGE_SIZE;
    uint8_t *pool = mmap(NULL, pool_sz, PROT_READ | PROT_WRITE,
                         MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (pool == MAP_FAILED) { perror("mmap"); return 1; }

    uint8_t *eviction_set[L1D_ASSOCIATIVITY];
    uint8_t *victim_set[L1D_ASSOCIATIVITY];
    int ec = 0, vc = 0;

    pid_t pid;
    int status;
    struct timespec victimWaitInterval = {0, 10000};
    struct timespec probeWaitInterval = {0, 1};

    FILE *timing_file;
    char timing_file_name[64];
    snprintf(timing_file_name, sizeof(timing_file_name), "%s/Prime-Probe_timings%d-%d.txt", RESULTS_FOLDER, run_number, set_number);

    timing_file = fopen(timing_file_name, "w");

    if (timing_file == NULL) {
        printf("Error opening file %s\n", timing_file_name);
        exit(1);
    }

    for (int page = 0; page < NUM_PAGES; page++) {
        uint8_t *base = pool + page * PAGE_SIZE;
        for (int off = 0; off < PAGE_SIZE; off += CACHE_LINE_SIZE) {
            uint8_t *addr = base + off;
            if (get_cache_set_index((uintptr_t)addr) == set_number) {
                if (ec < L1D_ASSOCIATIVITY)      eviction_set[ec++] = addr;
                else if (vc < L1D_ASSOCIATIVITY) victim_set[vc++]   = addr;
            }
            if (ec >= L1D_ASSOCIATIVITY && vc >= L1D_ASSOCIATIVITY) break;
        }
        if (ec >= L1D_ASSOCIATIVITY && vc >= L1D_ASSOCIATIVITY) break;
    }
    if (ec < L1D_ASSOCIATIVITY || vc < L1D_ASSOCIATIVITY) {
        // fprintf(stderr, "Failed to gather 8+8 lines for set %d\n", set_number);
        return 1;
    }

    // M10. Output and Result Reporting (Mapping Verification)
    // printf("###########  Before Page Fault:\n");
    // print_set_mapping("eviction_set", eviction_set, L1D_ASSOCIATIVITY);
    // print_set_mapping("victim_set", victim_set, L1D_ASSOCIATIVITY);

    /**********************************************************************************/

    // M4. Page Faulting and Memory Initialization
    // Fault-in pages WITHOUT clobbering the pointer area [0..7]
    for (int i = 0; i < L1D_ASSOCIATIVITY; i++) {
        uint8_t *e = eviction_set[i] + 8;
        uint8_t *v = victim_set[i]   + 8;
        e[0] ^= 1; v[0] ^= (uint8_t)(rand() & 0xFF);
        (void)*(volatile uint8_t*)e;
        (void)*(volatile uint8_t*)v;
    }

    // M10. Output and Result Reporting (Mapping Verification)
    // printf("############ After page fault:\n");
    // print_set_mapping("eviction_set", eviction_set, L1D_ASSOCIATIVITY);
    // print_set_mapping("victim_set", victim_set, L1D_ASSOCIATIVITY);

    /**********************************************************************************/

    // M3. Pointer-Chase Linked List Setup
    // Build random pointer-chase rings (attacker & victim)
    int perm[L1D_ASSOCIATIVITY]; 
    for (int i = 0; i < L1D_ASSOCIATIVITY; i++) 
        perm[i] = i;

    // shuffle_indices(perm, L1D_ASSOCIATIVITY);
    // build_linked_list(eviction_set, perm);
    // shuffle_indices(perm, L1D_ASSOCIATIVITY);
    // build_linked_list(victim_set, perm);

    // ---- Two scenarios averaged over NUM_TRIALS ----
    // M8. Scenario Sequencing and Averaging
    uint64_t t1_total = 0, t2_total = 0;
    int idx[L1D_ASSOCIATIVITY]; 
    for (int i=0;i<L1D_ASSOCIATIVITY;i++) 
        idx[i]=i;

    uint64_t t1;
    uint64_t t2;

    // Warm up to align better with parallel timings
    // serialize_full();
    // prime_chase(eviction_set);
    // serialize_full();
    // probe_chase(eviction_set, NULL);
    // serialize_full();
    // prime_chase(eviction_set);
    // serialize_full();
    // probe_chase(eviction_set, NULL);
    // serialize_full();

    for (int trial = 0; trial < NUM_TRIALS; trial++) {
        // Scenario A: PRIME -> PROBE
        // M5. Prime Function
        prime_chase(eviction_set);
        serialize_full();
        // M7. Probe and High-Resolution Timing
        t1 = probe_chase(eviction_set, NULL);
        t1_total += t1;

        // Scenario B: PRIME -> VICTIM -> PROBE (Traditional)
        // M5. Prime Function
        //pid = fork();

        //cpu_set_t cpuset;

        //CPU_ZERO(&cpuset);
        //CPU_SET(37, &cpuset);

        //sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);

        //prime_chase(eviction_set);
        //serialize_full();
        
        //if (pid == 0) { // Child process
        //    // execlp("phoronix-test-suite", "phoronix-test-suite", "batch-run", "pts/sample-pass-fail", NULL);
        //    //execlp("pwd", "pwd", NULL);
        //    //for (int i = 0; i < 100; i++) {
        //    //    nanosleep(&victimWaitInterval, NULL);
        //    //    victim_function(victim_set, idx);
        //    //}
        //    _exit(0);
        //    perror("execlp failed");
        //    exit(EXIT_FAILURE);
        //} else if (pid > 0) { // Parent process
        //} else { // Forking failed
        //    perror("fork failed");
        //    return EXIT_FAILURE;
        //}
        
        //wait(&status);
        //while (!WIFEXITED(status)) {
        //    wait(&status);
        //}

        //serialize_full();
        //prime_chase(eviction_set);
        //serialize_full();
        //victim_function(victim_set, idx);
        //serialize_full();
        //t2 = probe_chase(eviction_set, timing_file);
        //if (t2 < 0) break; // Outlier detected, off time
        //t2_total += t2;
        //fprintf(timing_file, "%ld\n", t2);
        //serialize_full();
    }
    uint64_t avg_A = t1_total / NUM_TRIALS;
    
    // Parallel
    pid = fork();

    cpu_set_t cpuset;

    CPU_ZERO(&cpuset);
    CPU_SET(37, &cpuset);

    sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);

    if (pid == 0) { // Child process
        // execlp("phoronix-test-suite", "phoronix-test-suite", "batch-run", "pts/sample-pass-fail", NULL);
        //execlp("pwd", "pwd", NULL);
        //
        // Victim function (ping)
        //for (int i = 0; i < 10; i++) {
        //    nanosleep(&victimWaitInterval, NULL);
        //    victim_function(victim_set, idx);
        //}
        //
        // Required for none and victim function
        _exit(0);
        perror("execlp failed");
        exit(EXIT_FAILURE);
    } else if (pid > 0) { // Parent process
        for (int trial = 0; trial < NUM_TRIALS; trial++) {
            serialize_full();
            t2 = probe_chase(eviction_set, timing_file);
            if (t2 < 0) break; // Outlier detected, off time
            t2_total += t2;
            fprintf(timing_file, "%ld\n", t2);
            nanosleep(&probeWaitInterval, NULL); // Window
        }
    } else { // Forking failed
        perror("fork failed");
        return EXIT_FAILURE;
    }
    status;
    wait(&status);
    while (!WIFEXITED(status)) {
        wait(&status);
    }


    // M9. Delta Calculation and Cache Contention Detection
    uint64_t avg_B = t2_total / NUM_TRIALS;

    // M10. Output and Result Reporting
    fprintf(summary_file, "Run Number = %d\n", run_number);
    fprintf(summary_file, "Target_Set = %d\n", set_number);
    fprintf(summary_file, "Trials     = %d\n", NUM_TRIALS);
    fprintf(summary_file, "\nA) PRIME -> PROBE              : %lu cycles (avg)\n", avg_A);
    fprintf(summary_file, "B) PRIME -> VICTIM -> PROBE    : %lu cycles (avg)\n", avg_B);
    fprintf(summary_file, "Delta (B - A)                  : %ld cycles\n", (long)(avg_B - avg_A));
    fprintf(summary_file, "--------------------\n\n");

    munmap(pool, pool_sz);
    fclose(timing_file);
    return 0;
}

int main(void) {
    FILE *summary_file;
    char *summary_file_name = RESULTS_FOLDER "/Prime-Probe_summary.txt";

    summary_file = fopen(summary_file_name, "w");
    if (summary_file == NULL) {
        printf("Error opening file %s\n", summary_file_name);
        exit(1);
    }

    // Find static similarities in one set
    //for (int i = 0; i < 100; i++) {
    //    prime_probe_for_set(23, summary_file, i);
    //}
    
    // int set_list[L1D_SETS] = {33, 2, 52, 29, 26, 61, 46, 53, 49, 41, 23, 22, 45, 0, 43, 47, 19, 16, 54, 56, 48, 27, 4, 1, 21, 38, 32, 24, 39, 10, 42, 13, 17, 44, 6, 8, 12, 37, 15, 55, 5, 60, 62, 63, 58, 30, 3, 36, 11, 59, 25, 51, 31, 50, 20, 34, 9, 14, 7, 57, 35, 40, 18, 28};
    
    for (int i = 0; i < L1D_SETS; i++) {
        for (int j = 0; j < 10; j++) {
            // printf("%d %d\n", i, j);
            prime_probe_for_set(i, summary_file, j);
         }
    }
    fclose(summary_file);
}
