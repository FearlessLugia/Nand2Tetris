import os
import sys
import re
from enum import Enum


# fileName.jack -> fileName.xml
# folderName -> One .xml file for every .jack file, stored in that folder
# Drives the process
class JackAnalyzer:
    def __init__(self, path):
        self.compilation_engine = CompilationEngine(path)


class TokenType(Enum):
    NONE = 0
    KEYWORD = 'keyword'
    SYMBOL = 'symbol'
    INTEGER_CONSTANT = 'integerConstant'
    STRING_CONSTANT = 'stringConstant'
    IDENTIFIER = 'identifier'


class KeyWord(Enum):
    NONE = 0
    CLASS = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    INT = 5
    BOOLEAN = 6
    CHAR = 7
    VOID = 8
    VAR = 9
    STATIC = 10
    FIELD = 11
    LET = 12
    DO = 13
    IF = 14
    ELSE = 15
    WHILE = 16
    RETURN = 17
    TRUE = 18
    FALSE = 19
    NULL = 20
    THIS = 21


# Handles the input
class JackTokenizer:
    # Opens the input .jack file/stream and gets ready to tokenize it
    def __init__(self, path):
        with open(path, 'r', encoding="utf-8") as file:
            text = file.read()

        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        text = re.sub(r'//.*', '', text)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        self.full_text = '\n'.join(lines)

        token_spec = [
            (TokenType.KEYWORD, r'\b(class|constructor|function|method|field|static|var|int|char|boolean|void|'
                                r'true|false|null|this|let|do|if|else|while|return)\b'),
            (TokenType.SYMBOL, r'[{}()\[\].,;+\-*/&|<>=~]'),
            (TokenType.INTEGER_CONSTANT, r'(\d+)'),
            (TokenType.STRING_CONSTANT, r'(".*")'),
            (TokenType.IDENTIFIER, r'[a-zA-Z_]\w*'),
        ]

        token_regex = '|'.join(f'(?P<{t.name}>{pattern})' for t, pattern in token_spec)
        self.r = re.compile(token_regex)

        self.tokens = list(self.r.finditer(self.full_text))
        # for i, tok in enumerate(self.tokens):
        #     print(f"Token {i}: {tok.group()}  -> {tok.lastgroup}")

        self.token_index = -1
        self.current_token = None

    # Are there more tokens in the input?
    def has_more_tokens(self) -> bool:
        # print('here', self.token_index, self.tokens)
        return self.token_index < len(self.tokens) - 1

    # Gets the next token from the input, and makes it the current token
    # This method should be called only if hasMoreTokens is true
    # Initially, there is no current token
    def advance(self):
        self.token_index += 1
        self.current_token = self.tokens[self.token_index]

    # Returns the type of the current token, as a constant
    def token_type(self):
        return TokenType[self.current_token.lastgroup]

    # Returns the keyword which is the current token, as a constant
    # This method should be called only if tokenType is KEYWORD
    def key_word(self):
        return self.current_token.group()

    # Returns the character which is the current token
    # Should be called only if tokenType is SYMBOL
    def symbol(self):
        dictionary = {'<': '&lt;', '>': '&gt;', '"': '&quot;', "&": "&amp;"}
        if self.current_token.group() in dictionary:
            return dictionary[self.current_token.group()]
        return self.current_token.group()

    # Returns the string which is the current token
    # Should be called only if tokenType is IDENTIFIER
    def identifier(self):
        return self.current_token.group()

    # Returns the integer value of the current token
    # Should be called only if tokenType is INT_CONST
    def int_val(self):
        return int(self.current_token.group())

    # Returns the string value of the current token, without the opening and closing double quotes
    # Should be called only if tokenType is STRING_CONST
    def string_val(self):
        return self.current_token.group()[1:-1]


# Handles the parsing
class CompilationEngine:
    # Creates a new compilation engine with the given input and output
    # The next routine called (by the JackAnalyzer module) must be compileClass
    def __init__(self, path):
        self.file = None
        res = []

        self.jump_count = -1
        self.call_count = {}

        # print('  input_path', path)

        if os.path.isfile(path):
            file_name = path.split('.')[-2] + '.xml'

            parser = JackTokenizer(path)
            self.parser = parser
            short_name = os.path.basename(path).replace('.xml', '')
            self.set_file_name(short_name)

            res.extend([f'<tokens>'])
            while parser.has_more_tokens():
                parser.advance()
                self.current_token = parser.current_token

                token_type = self.parser.token_type()
                # print(f"Token {self.parser.token_index}: {self.current_token.group()} -> {token_type}")

                if token_type == TokenType.KEYWORD:
                    res.extend([f'<{token_type.value}> {self.parser.key_word()} </{token_type.value}>'])
                    # res.extend(self.compile_class())
                elif token_type == TokenType.SYMBOL:
                    res.extend([f'<{token_type.value}> {self.parser.symbol()} </{token_type.value}>'])
                    # res.extend(self.compile_class_var_dec())
                elif token_type == TokenType.INTEGER_CONSTANT:
                    res.extend([f'<{token_type.value}> {self.parser.int_val()} </{token_type.value}>'])
                    # res.extend(self.compile_parameter_list())
                elif token_type == TokenType.STRING_CONSTANT:
                    res.extend([f'<{token_type.value}> {self.parser.string_val()} </{token_type.value}>'])
                    # res.extend(self.compile_subroutine_body())
                elif token_type == TokenType.IDENTIFIER:
                    res.extend([f'<{token_type.value}> {self.parser.identifier()} </{token_type.value}>'])
                    # res.extend(self.compile_var_dec())

            res.extend([f'</tokens>'])


        else:
            file_name = os.path.join(path, path.split('/')[-1] + '.jack')

            vm_files = [f for f in os.listdir(path) if f.endswith('.xml')]
            # print('vm_files', vm_files)

            res.extend(self.compile_subroutine())

            for file in vm_files:
                full_path = os.path.join(path, file)
                parser = JackTokenizer(full_path)
                self.parser = parser
                short_name = file.replace('.vm', '')
                self.set_file_name(short_name)

                while parser.has_more_tokens():
                    parser.advance()
                    self.current_token = parser.current_token

                    if self.parser.key_word() == TokenType.C_ARITHMETIC:
                        res.extend(self.compile_class())
                    elif self.parser.key_word() == TokenType.C_PUSH or self.parser.key_word() == TokenType.C_POP:
                        res.extend(self.compile_class_var_dec())
                    elif self.parser.key_word() == TokenType.C_LABEL:
                        res.extend(self.compile_parameter_list())
                    elif self.parser.key_word() == TokenType.C_GOTO:
                        res.extend(self.compile_subroutine_body())
                    elif self.parser.key_word() == TokenType.C_IF:
                        res.extend(self.compile_var_dec())
                    elif self.parser.key_word() == TokenType.C_FUNCTION:
                        res.extend(self.compile_statements())
                    elif self.parser.key_word() == TokenType.C_RETURN:
                        res.extend(self.compile_if())
                    elif self.parser.key_word() == TokenType.C_CALL:
                        res.extend(self.compile_let())

        # print('  output_file_name', file_name)
        # print('  self.file', self.file)

        # print('res', res)

        with open(file_name, 'w', encoding="utf-8") as file:
            for line in res:
                file.write(line + '\n')

    def process(self, str):
        if self.current_token == str:
            print_xml_token(str)
        else:
            print("syntax error")
        self.current_token = tokenizer.advance()

    # Compiles a complete class
    def compile_class(self):
        arg = self.parser.symbol()

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

    # Compiles a static variable declaration or a field declaration
    def compile_class_var_dec(self):
        segment = self.parser.symbol()
        i = self.parser.identifier()
        self.ram_map = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS', 'that': 'THAT'}

        if self.parser.key_word() == TokenType.C_PUSH:
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
                    f'@{self.file}.{i}', 'D=M',
                    '@SP', 'A=M', 'M=D',
                    '@SP', 'M=M+1']  # // SP++

            if segment == 'pointer':
                this_that = 'THIS' if i == '0' else 'THAT'
                return [
                    f'// {self.parser.current_line}',
                    f'@{this_that}', 'D=M',  # // D=i
                    '@SP', 'A=M', 'M=D',  # // RAM[SP]=D
                    '@SP', 'M=M+1']  # // SP++

        if self.parser.key_word() == TokenType.C_POP:
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

    # Compiles a complete method, function, or constructor
    def compile_subroutine(self):
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

    # Compiles a (possibly empty) parameter list
    # Does not handle the enclosing parentheses tokens ( and )
    def compile_parameter_list(self):
        arg = self.parser.symbol()
        return [f'// {self.parser.current_line}',
                f'({arg})']

    # Compiles a subroutine’s body
    def compile_subroutine_body(self):
        arg = self.parser.symbol()
        return [f'// {self.parser.current_line}',
                f'@{arg}',
                '0;JMP']

    # Compiles a var declaration
    def compile_var_dec(self):
        arg = self.parser.symbol()
        return [f'// {self.parser.current_line}',
                '@SP', 'M=M-1', 'A=M', 'D=M',
                f'@{arg}',
                'D;JNE']

    # Compiles a sequence of statements
    # Does not handle the enclosing curly bracket tokens { and }
    def compile_statements(self):
        function_name = self.parser.symbol()
        n_vars = int(self.parser.identifier())

        res = [f'// {self.parser.current_line}',
               # f'({self.file}.{function_name})']  # (Foo.bar)
               f'({function_name})']  # (Foo.bar)

        for i in range(n_vars):  # nVars = number of local variables
            res.extend(['@SP', 'A=M', 'M=0',
                        '@SP', 'M=M+1'])  # initializes the local variables to 0

        return res

    # Compiles a let statement
    def compile_let(self):
        # function_name = f'{self.file}.{self.parser.arg1()}'
        function_name = f'{self.parser.symbol()}'
        # print('call_function_name', function_name)
        n_vars = self.parser.identifier()

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

    # Compiles an if statement, possibly with a trailing else clause
    def compile_if(self):
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

    # Compiles a while statement
    def compile_while(self):
        pass

    # Compiles a do statement
    def compile_do(self):
        pass

    # Compiles a return statement
    def compile_return(self):
        pass

    # Compiles an expression
    def compile_expression(self):
        pass

    # Compiles a term
    # If the current token is an identifier, the routine must resolve it into a variable, an array entry, or a subroutine call
    # A single lookahead token, which may be [, (, or ., suffices to distinguish between the possibilities
    # Any other token is not part of this term and should not be advanced over
    def compile_term(self):
        pass

    # Compiles a (possibly empty) comma-separated list of expressions
    # Returns the number of expressions in the list
    def compile_expression_list(self):
        pass


if __name__ == '__main__':
    files = ['ArrayTest/Main0.jack', 'ExpressionLessSquare', 'Square']
    jack_analyzer = JackAnalyzer(files[0])
    parser = jack_analyzer.compilation_engine.parser

    # args = sys.argv
    # if len(args) < 1:
    #     print('Need file name')
    #
    # vm_translator = VMTranslator(args[1])
