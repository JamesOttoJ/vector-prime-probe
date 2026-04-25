; nasm -f elf64 vpgather_test.asm
; gcc -no-pie -o vpgather_test vpgather_test.o
SECTION .data
align   32
array_vindex    dd  0x00000001, 0x00000002, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000
fmt             dd  '%x', 10, 0
nl              dd  10
out_file        dd  'vpgather_test_out.txt', 0
mod             dd  'w', 0

SECTION .text
default rel
extern printf, malloc, sync, fopen, fclose, fprintf
global main

; rbp-8h: i
; rbp-10h: time
; rbp-18h: mask
; rbp-20h: out FILE
main:
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
    vmovdqu32 zmm6, [array_vindex]  ; Put array into vector format
    mov rdi, 10000h ; 32 4KB pages (0x800 * 0x20, 0b1000 0000 0000 * 0b10 0000)
    push    rbp
    call malloc
    pop rbp
    mov r10, rax             ; Put chunk of memory into r8
    ; fill memory
    mov byte [r10], 0
    mov byte [r10+1], 1
    mov byte [r10+2], 2
    mov byte [r10+3], 3
    mov byte [r10+4], 4
    mov byte [r10+5], 5
    mov byte [r10+6], 6
    mov byte [r10+7], 7
    mov byte [r10+8], 8
    ; Result memory
    mov rdi, 200h ; 512 bytes
    push    rbp
    call malloc
    pop rbp
    mov r11, rax
    ; Set-up mask
    mov eax, 0x03
    kmovw k1, eax    
    vpgatherdd  zmm7 {k1}, [r10 + zmm6*8] ; Access either 1 or 8

    ; Get number gathered
    vmovdqa32   [r11] {k1}, zmm7

    mov rdi, [rbp-20h] ; FILE arg
    mov rsi, fmt ; Format arg
    mov rdx, [r11]
    xor rax, rax
    call fprintf wrt ..plt

    mov rdi, [rbp-20h] ; FILE arg
    mov rsi, nl
    xor rax, rax
    call fprintf wrt ..plt
    add qword [rbp-8h], 1
;    push rbp    
;    call sync
;    pop rbp    

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
    
