; nasm -f elf64 avx_cache_fill_with_time_avx2.asm
; gcc -no-pie -o avx_cache_fill_with_time_avx2 avx_cache_fill_with_time_avx2.o
SECTION .data
align   32
array_vindex    dd  0x00000200, 0x00000400, 0x00000600, 0x00000800, 0x00000a00, 0x00000c00, 0x00000e00, 0x000001000
fmt             dd  '%d %ld', 10, 0
nl              dd  10
out_file        dd  'intel_avx2_out.txt', 0
mod             dd  'w', 0

SECTION .text
default rel
extern printf, malloc, fflush, fopen, fclose, fprintf
global getTimings
; global main

; main:
;     jmp getTimings

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
    vmovdqu ymm6, [array_vindex]  ; Put array into vector format
    mov rdi, 10000h
    push    rbp
    call malloc
    pop rbp
    mov r8, rax             ; Put chunk of memory into r8
    mov dword [rbp-18h], 0xffffffff
    vpbroadcastd    ymm7, dword [rsp+12h]
    jmp     loop_cond

loop_main:
    mfence
    rdtsc                   ; Start timer
    shl rdx, 32
    or  rdx, rax
    mov [rbp-10h], rdx
    vpgatherdd  ymm8, [r8 + ymm6*8], ymm7  ; Access 8 pages
    rdtsc                   ; Stop timer
    shl rdx, 32
    or  rdx, rax
    sub rdx, [rbp-10h]

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
    add qword [rbp-8h], 1
    
loop_cond:
    cmp qword [rbp-8h], 100
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
    
