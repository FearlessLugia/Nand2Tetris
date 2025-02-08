// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Fill.asm

// Runs an infinite loop that listens to the keyboard input. 
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel. When no key is pressed, 
// the screen should be cleared.

//// Replace this comment with your code.


(LOOP)
@KBD
D=M
@WHITE
D;JEQ // if no key is pressed, goto white
@BLACK
D;JNE // if any key is pressed, goto black

(WHITE)
@i
M=0

(WHITELOOP)
// if i==8192, goto LOOP
@i
D=M
@8192
D=D-A
@LOOP
D;JEQ

// RAM[screen+i] = 0
@SCREEN
D=A
@i
A=M
A=D+A
M=0
@i
M=M+1
@WHITELOOP
0;JMP


(BLACK)
@i
M=0

(BLACKLOOP)
// if i==8192, goto LOOP
@i
D=M
@8192
D=D-A
@LOOP
D;JEQ

// RAM[screen+i] = -1
@SCREEN
D=A
@i
A=M
A=D+A
M=-1
@i
M=M+1
@BLACKLOOP
0;JMP
