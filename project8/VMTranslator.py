import os
import sys
from enum import Enum

from torch.cuda.tunable import set_filename


# fileName.vm -> fileName.asm
# Drives the process
class VMTranslator:
    def __init__(self, path):
        self.code_writer = CodeWriter(path)


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
    def __init__(self, path):
        self.current_line = ''
        self.line_num = -1
        self.lines = []

        with open(path, 'r', encoding="utf-8") as file:
            lines_temp = file.readlines()

        for line in lines_temp:
            if not line.strip().startswith('//') and line.strip():
                self.lines.append(line.strip())

        # print('lines', self.lines, len(self.lines))

        self.lines_num = len(self.lines)

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
        if self.current_line.startswith('return'):
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
    def __init__(self, path):
        self.file = None
        res = []

        self.jump_count = -1
        self.call_count = {}

        print('  input_path', path)
        # if '.vm' in path:
        #     file_name = path.split('.')[-2] + '.asm'
        #     self.file = path.split('/')[-2]
        #
        #     parser = Parser(path)
        #     self.parser = parser
        # else:
        #     file_name = os.path.join(path, path.split('/')[-1] + '.asm')
        #     self.file = path.split('/')[-1]
        #
        #     res.extend(self.write_init())

        if os.path.isfile(path):
            file_name = path.split('.')[-2] + '.asm'

            parser = Parser(path)
            self.parser = parser
            short_name = os.path.basename(path).replace('.vm', '')
            self.set_file_name(short_name)

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


        else:
            file_name = os.path.join(path, path.split('/')[-1] + '.asm')

            vm_files = [f for f in os.listdir(path) if f.endswith('.vm')]
            print('vm_files', vm_files)

            res.extend(self.write_init())

            for file in vm_files:
                full_path = os.path.join(path, file)
                parser = Parser(full_path)
                self.parser = parser
                short_name = file.replace('.vm', '')
                self.set_file_name(short_name)

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

        print('  output_file_name', file_name)
        print('  self.file', self.file)

        # parser.line_num = -1
        #
        # while parser.has_more_lines():
        #     parser.advance()
        #     self.current_string = parser.current_line
        #
        #     if self.parser.command_type() == CommandType.C_ARITHMETIC:
        #         res.extend(self.write_arithmetic())
        #     elif self.parser.command_type() == CommandType.C_PUSH or self.parser.command_type() == CommandType.C_POP:
        #         res.extend(self.write_push_pop())
        #     elif self.parser.command_type() == CommandType.C_LABEL:
        #         res.extend(self.write_label())
        #     elif self.parser.command_type() == CommandType.C_GOTO:
        #         res.extend(self.write_goto())
        #     elif self.parser.command_type() == CommandType.C_IF:
        #         res.extend(self.write_if())
        #     elif self.parser.command_type() == CommandType.C_FUNCTION:
        #         res.extend(self.write_function())
        #     elif self.parser.command_type() == CommandType.C_RETURN:
        #         res.extend(self.write_return())
        #     elif self.parser.command_type() == CommandType.C_CALL:
        #         res.extend(self.write_call())

        # print('res', res)

        with open(file_name, 'w', encoding="utf-8") as file:
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
                    '@SP', 'A=M', 'M=D',  # //RAM[SP] = RAM[addr]
                    '@SP', 'M=M+1']  # // SP++

            if segment == 'static':
                return [
                    f'// {self.parser.current_line}',
                    f'@{self.file}.{i}', 'D=M',  # // D=RAM[segment+i]
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
                    '@R13', 'M=D',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',
                    '@R13', 'A=M', 'M=D']

            if segment == 'static':
                return [
                    f'// {self.parser.current_line}',
                    '@SP', 'AM=M-1', 'D=M',
                    f'@{self.file}.{i}', 'M=D']

            if segment == 'pointer':
                this_that = 'THIS' if i == '0' else 'THAT'
                return [
                    f'// {self.parser.current_line}',
                    '@SP', 'M=M-1',  # // SP--
                    'A=M', 'D=M',  # D=RAM[SP]
                    f'@{this_that}', 'M=D']  # // THIS/THAT=RAM[SP]

    # Informs that the translation of a new VM file has started (called by the VMTranslator)
    def set_file_name(self, string):
        self.file = string

    def write_init(self):
        return [
            # SP = 256
            '@256', 'D=A',
            '@SP', 'M=D',

            # Call Sys.init
            '// Call Sys.init',
            # push returnAddrLabel
            '@Sys.init$ret.0', 'D=A',
            '@SP', 'A=M', 'M=D',
            '@SP', 'M=M+1',

            # push LCL
            '@LCL', 'D=M',
            '@SP', 'A=M', 'M=D',
            '@SP', 'M=M+1',
            # push ARG
            '@ARG', 'D=M',
            '@SP', 'A=M', 'M=D',
            '@SP', 'M=M+1',
            # push THIS
            '@THIS', 'D=M',
            '@SP', 'A=M', 'M=D',
            '@SP', 'M=M+1',
            # push THAT
            '@THAT', 'D=M',
            '@SP', 'A=M', 'M=D',
            '@SP', 'M=M+1',

            # ARG = SP - 5
            '@SP', 'D=M',
            '@5', 'D=D-A',
            '@ARG', 'M=D',

            # LCL = SP
            '@SP', 'D=M',
            '@LCL', 'M=D',

            # goto Sys.init
            '@Sys.init', '0;JMP',

            # (returnAddrLabel)
            '(Sys.init$ret.0)']

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
        function_name = self.parser.arg1()
        n_vars = int(self.parser.arg2())

        res = [f'// {self.parser.current_line}',
               # f'({self.file}.{function_name})']  # (Foo.bar)
               f'({function_name})']  # (Foo.bar)

        for i in range(n_vars):  # nVars = number of local variables
            res.extend(['@SP', 'A=M', 'M=0',
                        '@SP', 'M=M+1'])  # initializes the local variables to 0

        return res

    # Writes assembly code that effects the call command
    def write_call(self):
        # function_name = f'{self.file}.{self.parser.arg1()}'
        function_name = f'{self.parser.arg1()}'
        print('call_function_name', function_name)
        n_vars = self.parser.arg2()

        if function_name not in self.call_count:
            self.call_count[function_name] = 0
        self.call_count[function_name] += 1

        function_name_ret = f'{function_name}$ret.{self.call_count[function_name]}'

        return [f'// {self.parser.current_line}',

                # push returnAddrLabel
                f'@{function_name_ret}', 'D=A',
                '@SP', 'A=M', 'M=D',
                '@SP', 'M=M+1',

                # push LCL
                '@LCL', 'D=M',
                '@SP', 'A=M', 'M=D',
                '@SP', 'M=M+1',
                # push ARG
                '@ARG', 'D=M',
                '@SP', 'A=M', 'M=D',
                '@SP', 'M=M+1',
                # push THIS
                '@THIS', 'D=M',
                '@SP', 'A=M', 'M=D',
                '@SP', 'M=M+1',
                # push THAT
                '@THAT', 'D=M',
                '@SP', 'A=M', 'M=D',
                '@SP', 'M=M+1',

                # ARG = SP - 5 - nArgs
                '@SP', 'D=M',
                '@5', 'D=D-A',
                f'@{n_vars}', 'D=D-A',
                '@ARG', 'M=D',

                # LCL = SP
                '@SP', 'D=M',
                '@LCL', 'M=D',

                # goto functionName
                f'@{function_name}', '0;JMP',

                # (returnAddrLabel)
                f'({function_name_ret})']

    # Writes assembly code that effects the return command
    def write_return(self):
        return [f'// {self.parser.current_line}',

                # endFrame = LCL
                '@LCL', 'D=M',
                '@R13', 'M=D',

                # retAddr = *(endFrame - 5)
                '@5', 'A=D-A', 'D=M',
                '@R14', 'M=D',

                # *ARG = pop()
                '@SP', 'AM=M-1', 'D=M',
                '@ARG', 'A=M', 'M=D',

                # SP = ARG + 1
                '@ARG', 'D=M+1',
                '@SP', 'M=D',

                # THAT = *(endFrame - 1)
                '@R13', 'AM=M-1', 'D=M',
                '@THAT', 'M=D',
                # THIS = *(endFrame - 2)
                '@R13', 'AM=M-1', 'D=M',
                '@THIS', 'M=D',
                # ARG = *(endFrame - 3)
                '@R13', 'AM=M-1', 'D=M',
                '@ARG', 'M=D',
                # LCL = *(endFrame - 4)
                '@R13', 'AM=M-1', 'D=M',
                '@LCL', 'M=D',

                # goto retAddr
                '@R14', 'A=M', '0;JMP']


if __name__ == '__main__':
    # files = ['ProgramFlow/BasicLoop/BasicLoop.vm', 'ProgramFlow/FibonacciSeries/FibonacciSeries.vm',
    #          'FunctionCalls/SimpleFunction/SimpleFunction.vm', 'FunctionCalls/NestedCall',
    #          'FunctionCalls/FibonacciElement', 'FunctionCalls/StaticsTest']
    # vm_translator = VMTranslator(files[5])

    args = sys.argv
    if len(args) < 1:
        print('Need file name')

    vm_translator = VMTranslator(args[1])
