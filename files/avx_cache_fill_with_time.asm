; nasm -f elf64 avx_cache_fill_with_time.asm
; gcc -no-pie -o avx_cache_fill_with_time avx_cache_fill_with_time.o
SECTION .data
align   64
array_vindex    dq  0x0, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7000
fmt             dd  '%d %ld', 10, 0
nl              dd  10
out_file        dd  'intel_avx512_out.txt', 0
mod             dd  'w', 0
run_num         dd  1000000

SECTION .text
default rel
extern printf, malloc, sync, fopen, fclose, fprintf
global getTimings
;global main

main:
    jmp getTimings

; rbp-8h: i
; rbp-10h: time
; rbp-18h: mask
; rbp-20h: out FILE
getTimings:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 0x20
    
    ; Open file
    mov rdi, out_file
    mov rsi, mod
    xor rax, rax
    call fopen
    mov [rbp-20h], rax

    mov     qword [rbp-8h], 0                    ; Initialize loop
    vmovdqu64 zmm6, [array_vindex]  ; Put array into vector format
    mov rdi, 10000h
    push    rbp
    call malloc
    pop rbp
    mov r8, rax             ; Put chunk of memory into r8
    kxnorw k1, k1, k1    
    jmp     loop_cond
loop_main:
    lfence
    rdtsc                   ; Start timer
    shl rdx, 32
    or  rdx, rax
    mov [rbp-10h], rdx
    lfence
    vpgatherqq  zmm7 {k1}, [r8 + zmm6*1]  ; Access 8 pages
    lfence
    rdtsc                   ; Stop timer    
    shl rdx, 32
    or  rdx, rax
    lfence    
    sub rdx, [rbp-10h]

    ; Save space by only writing anomalies
    cmp rdx, 212
    jle inc

    ; rdx is already holding the time difference
    mov	rsi, qword [rbp-8h]
    mov	rdi, fmt
    mov	rax, 0

    mov rcx, rdx ; Timing arg
    mov rdi, [rbp-20h] ; FILE arg
    mov rsi, fmt ; Format arg
    mov rdx, [rbp-8h]
    xor rax, rax
    call fprintf wrt ..plt

    mov rdi, [rbp-20h] ; FILE arg
    mov rsi, nl
    xor rax, rax
    call fprintf wrt ..plt

inc:    
    add qword [rbp-8h], 1

loop_cond:
    mov rax, [run_num]
    cmp qword [rbp-8h], rax
    jle loop_main
    
exit:
    mov rdi, [rbp-20h]
    xor rax, rax
    call fclose

    mov     rbx, 0
    mov     rax, 1
    int     80h
    mov     rsp, rbp
    pop     rbp
    ret
    
