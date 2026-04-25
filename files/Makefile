all: avx_cache_fill_with_time Prime-Probe vpgather_test ping_memory

# Need to remove main from timing file symbols before compiling
ping_memory: avx_cache_fill_with_time
	nasm -f elf64 avx_cache_fill_with_time.asm
	gcc -no-pie -pthread ping_memory.c avx_cache_fill_with_time.o -o ping_memory

avx_cache_fill_with_time_avx2:
	nasm -f elf64 avx_cache_fill_with_time_avx2.asm
#	gcc -no-pie -o avx_cache_fill_with_time_avx2 avx_cache_fill_with_time_avx2.o

avx_cache_fill_with_time:
	nasm -f elf64 avx_cache_fill_with_time.asm
	#gcc -no-pie -o avx_cache_fill_with_time avx_cache_fill_with_time.o

Prime-Probe:
	gcc -mavx2 -mavx512f -o Prime-Probe Prime-Probe.c

vpgather_test:
	nasm -f elf64 vpgather_test.asm
	gcc -no-pie -o vpgather_test vpgather_test.o


clean:
	rm -f *.o
	rm -f avx_cache_fill_with_time_avx2
	rm -f avx_cache_fill_with_time
	rm -f Prime-Probe
	rm -f vpgather_test
	rm -f ping_memory
	rm -f Prime-Probe_results/*

.PHONY: all
.PHONY: clean
