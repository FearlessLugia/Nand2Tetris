// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
// The algorithm is based on repetitive addition.

//// Replace this comment with your code.
@sum
M=0    // sum=0

@0
D=M    // D=R0
@SUM
D;JEQ  // if R0==0 goto SUM

@1
D=M
@SUM
D;JEQ  // if R1==0 goto SUM

(LOOP)
@0
D=M    // D=R0
@sum
M=D+M  // sum=D+sum

@1
M=M-1  // R1=R1-1
D=M    // D=R1
@LOOP
D;JGT  // if R1>0 goto LOOP

(SUM)
@sum
D=M    // D=sum
@2
M=D    // R2=D

(END)
@END
0;JMP  // Infinite loop