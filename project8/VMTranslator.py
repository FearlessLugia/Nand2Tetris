import sys
from enum import Enum


# fileName.vm -> fileName.asm
# Drives the process
class VMTranslator:
    def __init__(self, file):
        self.parser = Parser(file)
        self.code_writer = CodeWriter(self.parser, file)


class CommandType(Enum):
    NONE = 0
    C_ARITHMETIC = 1
    C_PUSH = 2
    C_POP = 3
    C_LABEL = 4
    C_GOTO = 5
    C_IF = 6
    C_FUNCTION = 7
    C_RETURN = 8
    C_CALL = 9


# Parses each VM command into its lexical elements
class Parser:
    # Opens the input file/stream, and gets ready to parse it
    def __init__(self, current_file):
        self.current_line = ''
        self.line_num = -1

        with open(current_file + '.vm', 'r', encoding="utf-8") as file:
            lines_temp = file.readlines()

        lines = []
        for line in lines_temp:
            if not line.strip().startswith('//') and line.strip():
                lines.append(line.strip())
        # print(lines, len(lines))

        self.lines = lines
        self.lines_num = len(lines)

    def has_more_lines(self) -> bool:
        return self.line_num < self.lines_num - 1

    def advance(self):
        self.line_num += 1
        self.current_line = self.lines[self.line_num]

    # Returns a constant representing the type of the current command
    # If the current command is an arithmetic-logical command, returns C_ARITHMETIC
    def command_type(self):
        if self.current_line.startswith('push '):
            return CommandType.C_PUSH
        if self.current_line.startswith('pop '):
            return CommandType.C_POP
        if self.current_line.startswith('label '):
            return CommandType.C_LABEL
        if self.current_line.startswith('goto '):
            return CommandType.C_GOTO
        if self.current_line.startswith('if-goto '):
            return CommandType.C_IF
        if self.current_line.startswith('call '):
            return CommandType.C_CALL
        if self.current_line.startswith('function '):
            return CommandType.C_FUNCTION
        if self.current_line.startswith('return '):
            return CommandType.C_RETURN
        return CommandType.C_ARITHMETIC

    # Returns the first argument of the current command
    # In the case of C_ARITHMETIC, the command itself (add, sub, etc.) is returned
    # Should not be called if the current command is C_RETURN
    def arg1(self):
        if self.command_type() == CommandType.C_ARITHMETIC:
            return self.current_line.split()[0]
        return self.current_line.split()[1]

    # Returns the second argument of the current command
    # Should be called only if the current command is C_PUSH, C_POP, C_FUNCTION, or C_CALL
    def arg2(self):
        return self.current_line.split()[2]


# Writes the assembly code that implements the parsed command
class CodeWriter:
    # Opens an output file / stream and gets ready to write into it
    def __init__(self, parser, current_file):
        res = []
        self.file = current_file.split('/')[-1]
        self.parser = parser
        self.jump_count = -1
        self.static_count = 15

        parser.line_num = -1
        while parser.has_more_lines():
            parser.advance()
            self.current_string = parser.current_line

            if self.parser.command_type() == CommandType.C_ARITHMETIC:
                res.extend(self.write_arithmetic())
            elif self.parser.command_type() == CommandType.C_PUSH or self.parser.command_type() == CommandType.C_POP:
                res.extend(self.write_push_pop())
            elif self.parser.command_type() == CommandType.C_LABEL:
                res.extend(self.write_label())
            elif self.parser.command_type() == CommandType.C_GOTO:
                res.extend(self.write_goto())
            elif self.parser.command_type() == CommandType.C_IF:
                res.extend(self.write_if())
            elif self.parser.command_type() == CommandType.C_FUNCTION:
                res.extend(self.write_function())
            elif self.parser.command_type() == CommandType.C_RETURN:
                res.extend(self.write_return())
            elif self.parser.command_type() == CommandType.C_CALL:
                res.extend(self.write_call())

        # print('res', res)

        with open(current_file + '.asm', 'w', encoding="utf-8") as file:
            for line in res:
                file.write(line + '\n')

    # Writes to the output file the assembly code that implements the given arithmetic-logical command
    def write_arithmetic(self):
        arg = self.parser.arg1()

        arithmetic_map = {'add': 'D+M', 'sub': 'M-D', 'and': 'D&M', 'or': 'D|M'}
        if arg in arithmetic_map:
            return [f'// {self.parser.current_line}',
                    '@SP', 'M=M-1', 'A=M', 'D=M',
                    '@SP', 'M=M-1', 'A=M',
                    f'M={arithmetic_map[arg]}',
                    '@SP', 'M=M+1']

        arithmetic_map = {'neg': '-', 'not': '!'}
        if arg in arithmetic_map:
            return [f'// {self.parser.current_line}',
                    '@SP', 'A=M-1',
                    f'M={arithmetic_map[arg]}M']

        arithmetic_map = {'eq': 'JEQ', 'gt': 'JGT', 'lt': 'JLT'}
        if arg in arithmetic_map:
            self.jump_count += 1
            return [f'// {self.parser.current_line}',
                    '@SP', 'M=M-1', 'A=M', 'D=M',
                    '@SP', 'M=M-1', 'A=M', 'D=M-D',
                    f'@LABEL{self.jump_count}', f'D;{arithmetic_map[arg]}',
                    '@SP', 'A=M', 'M=0',
                    f'@LABEL{self.jump_count}END', '0;JMP',
                    f'(LABEL{self.jump_count})',
                    '@SP', 'A=M', 'M=-1',
                    f'(LABEL{self.jump_count}END)',
                    '@SP', 'M=M+1']

    # Writes to the output file the assembly code that implements the given push or pop command
    def write_push_pop(self):
        segment = self.parser.arg1()
        i = self.parser.arg2()
        self.ram_map = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS', 'that': 'THAT'}

        if self.parser.command_type() == CommandType.C_PUSH:
            if segment == 'constant':
                return [
                    f'// {self.parser.current_line}',
                    f'@{i}', 'D=A',  # // D=i
                    '@SP', 'A=M', 'M=D',  # // RAM[SP]=D
                    '@SP', 'M=M+1']  # // SP++

            if segment in self.ram_map:
                return [
                    f'// {self.parser.current_line}',
                    f'@{i}', 'D=A',  # // D=i
                    f'@{self.ram_map[segment]}', 'A=M', 'A=D+A', 'D=M',  # // D=RAM[segment+i]
                    '@SP', 'A=M', 'M=D',  # //RAM[SP] = RAM[addr]
                    '@SP', 'M=M+1']  # // SP++

            if segment == 'temp':
                return [
                    f'// {self.parser.current_line}',
                    f'@{5 + int(i)}', 'D=A',  # // D=i
                    '@5', 'A=M', 'A=D+A', 'D=M',  # // D=RAM[segment+i]
                    '@SP', 'A=M', 'M=D',  # //RAM[SP] = RAM[addr]
                    '@SP', 'M=M+1']  # // SP++

            if segment == 'static':
                self.jump_count += 1
                return [
                    f'// {self.parser.current_line}',
                    f'@{i}', 'D=A',  # // D=i
                    f'@{self.file + str(self.static_count)}', 'A=M', 'A=D+A', 'D=M',  # // D=RAM[segment+i]
                    '@SP', 'A=M', 'M=D',  # //RAM[SP] = RAM[addr]
                    '@SP', 'M=M+1']  # // SP++

            if segment == 'pointer':
                this_that = 'THIS' if i == '0' else 'THAT'
                return [
                    f'// {self.parser.current_line}',
                    f'@{this_that}', 'D=M',  # // D=i
                    '@SP', 'A=M', 'M=D',  # // RAM[SP]=D
                    '@SP', 'M=M+1']  # // SP++

        if self.parser.command_type() == CommandType.C_POP:
            if segment in self.ram_map:
                return [
                    f'// {self.parser.current_line}',
                    f'@{i}', 'D=A',  # // D=i
                    f'@{self.ram_map[segment]}', 'A=M', 'D=D+A',  # // D=RAM[segment+i]
                    '@R13', 'M=D',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',
                    '@R13', 'A=M', 'M=D']

            if segment == 'temp':
                return [
                    f'// {self.parser.current_line}',
                    f'@{5 + int(i)}', 'D=A',  # // D=i
                    '@5', 'A=M', 'D=D+A',  # // D=RAM[segment+i]
                    '@R13', 'M=D',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',
                    '@R13', 'A=M', 'M=D']

            if segment == 'static':
                self.jump_count += 1
                return [
                    f'// {self.parser.current_line}',
                    f'@{i}', 'D=A',  # // D=i
                    f'@{self.file + str(self.static_count)}', 'A=M', 'D=D+A',  # // D=RAM[segment+i]
                    '@R13', 'M=D',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',
                    '@R13', 'A=M', 'M=D']

            if segment == 'pointer':
                this_that = 'THIS' if i == '0' else 'THAT'
                return [
                    f'// {self.parser.current_line}',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',  # D=RAM[SP]
                    f'@{this_that}', 'M=D']  # // THIS/THAT=RAM[SP]

    # Informs that the translation of a new VM file has started (called by the VMTranslator)
    def set_file_name(self):
        pass

    def write_init(self):
        pass

    # Writes assembly code that effects the label command
    def write_label(self):
        arg = self.parser.arg1()
        return [f'// {self.parser.current_line}',
                f'({arg})']

    # Writes assembly code that effects the goto command
    def write_goto(self):
        arg = self.parser.arg1()
        return [f'// {self.parser.current_line}',
                f'@{arg}',
                '0;JMP']

    # Writes assembly code that effects the if-goto command
    def write_if(self):
        arg = self.parser.arg1()
        return [f'// {self.parser.current_line}',
                '@SP', 'M=M-1', 'A=M', 'D=M',
                f'@{arg}',
                'D;JNE']

    # Writes assembly code that effects the function command
    def write_function(self):
        pass

    # Writes assembly code that effects the call command
    def write_call(self):
        pass

    # Writes assembly code that effects the return command
    def write_return(self):
        pass


if __name__ == '__main__':
    files = ['ProgramFlow/BasicLoop/BasicLoop', 'ProgramFlow/FibonacciSeries/FibonacciSeries',
             'FunctionCalls/SimpleFunction/SimpleFunction', 'FunctionCalls/NestedCall/NestedCall',
             'FunctionCalls/FibonacciElement/FibonacciElement', 'FunctionCalls/StaticsTest/StaticsTest']
    vm_translator = VMTranslator(files[1])

    # args = sys.argv
    # if len(args) < 1:
    #     print('Need file name with .vm')
    #
    # file_name = args[1].split('.vm')[0]
    # vm_translator = VMTranslator(file_name)
