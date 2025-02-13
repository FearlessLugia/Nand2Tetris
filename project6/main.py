from enum import Enum


# prog.asm -> prog.hack
class HackAssembler:
    def __init__(self, files):
        self.symbol_table = None
        self.parser = None
        self.code = Code()

        self.res = []

        self.files = files
        self.file_num = -1
        self.current_file = self.files[0]

    # Opens the input file (prog.asm) and gets ready to process it
    # Constructs a symbol table, and adds to it all the predefined symbols
    def initialize(self):
        with open(self.current_file + '.asm', 'r', encoding="utf-8") as file:
            lines_temp = file.readlines()

        lines = []
        for line in lines_temp:
            if not line.strip().startswith('//') and line.strip():
                lines.append(line.strip())
        print(lines, len(lines))

        self.parser = Parser(lines)
        self.symbol_table = SymbolTable()

    # Reads the program lines, one by one, focusing only on (label) declarations.
    # Adds the found labels to the symbol table
    def first_pass(self):
        line_num_to_reduce = 0

        while self.parser.has_more_lines():
            self.parser.advance()

            # print(line, self.parser.instruction_type(), self.parser.symbol())
            if self.parser.instruction_type() == InstructionType.L_INSTRUCTION:
                symbol = self.parser.symbol()
                # print('s,num', symbol, self.parser.line_num)
                if not symbol.isdigit():
                    self.symbol_table.add_entry(symbol, self.parser.line_num - line_num_to_reduce)
                    line_num_to_reduce += 1

        print('    symbol_table', self.symbol_table.symbol_table)

    # While there are more lines to process:
    #   Gets the next instruction, and parses it
    #   If the instruction is @ symbol
    #     If symbol is not in the symbol table, adds it to the table
    #     Translates the symbol into its binary value
    #   If the instruction is dest =comp ; jump
    #     Translates each of the three fields into its binary value
    #   Assembles the binary values into a string of sixteen 0’s and 1’s
    #   Writes the string to the output file.
    def second_pass(self):
        self.parser.line_num = -1
        while self.parser.has_more_lines():
            self.parser.advance()
            self.code.current_string = self.parser.current_line

            if self.parser.instruction_type() == InstructionType.C_INSTRUCTION:
                dest = self.parser.dest()
                comp = self.parser.comp()
                jump = self.parser.jump()
                res = '111' + self.code.comp(comp) + self.code.dest(dest) + self.code.jump(jump)
                print('  res', self.parser.current_line, res)
                self.res.append(res)

            elif self.parser.instruction_type() == InstructionType.A_INSTRUCTION:
                symbol = self.parser.symbol()
                print('symbol', symbol)
                if symbol.isdigit():
                    res = str(bin(int(symbol))[2:]).rjust(16, '0')
                    self.res.append(res)
                else:
                    if self.symbol_table.contains(symbol):
                        address = self.symbol_table.get_address(symbol)
                        res = str(bin(address)[2:]).rjust(16, '0')
                        print('  res', res)
                        self.res.append(res)
                    else:
                        self.symbol_table.current_num += 1
                        self.symbol_table.add_entry(symbol, self.symbol_table.current_num)

            # print(self.res)
        print('    symbol_table', self.symbol_table.symbol_table)

        with open(self.current_file + '.hack', 'w', encoding="utf-8") as file:
            for line in self.res:
                file.write(line + '\n')

    def advance(self):
        self.file_num += 1
        if self.file_num < len(self.files):
            self.current_file = self.files[self.file_num]
        else:
            self.current_file = None


class InstructionType(Enum):
    NONE = 0
    A_INSTRUCTION = 1
    C_INSTRUCTION = 2
    L_INSTRUCTION = 4


class Parser:
    def __init__(self, lines):
        # self.current_line = 'D=D+1;JLE'
        # self.current_line = 'M=-1'
        self.current_line = ''
        self.line_num = -1
        self.lines = lines
        self.lines_num = len(lines)

    def has_more_lines(self):
        # print('has_more_lines', self.line_num, '<', self.lines_num - 1, self.line_num < self.lines_num - 1)
        return self.line_num < self.lines_num - 1

    def advance(self):
        self.line_num += 1
        self.current_line = self.lines[self.line_num]

    def instruction_type(self):
        if self.current_line.startswith('@'):
            return InstructionType.A_INSTRUCTION
        if self.current_line.startswith('('):
            return InstructionType.L_INSTRUCTION
        return InstructionType.C_INSTRUCTION

    def symbol(self):
        if self.instruction_type() == InstructionType.A_INSTRUCTION:
            return self.current_line[1:]
        if self.instruction_type() == InstructionType.L_INSTRUCTION:
            return self.current_line[1:-1]
        return None

    def dest(self):
        if self.instruction_type() != InstructionType.C_INSTRUCTION:
            return None
        return self.current_line.split('=')[0]

    def comp(self):
        # print('self.current_line.split()', self.current_line.split('='))
        split = self.current_line.split('=')
        if len(split) > 1:
            return split[1].split(';')[0]
        return self.current_line.split(';')[0]

    def jump(self):
        split = self.current_line.split(';')
        return split[1] if len(split) > 1 else None


class Code:
    def __init__(self):
        self.current_string = ''
        self.__comp_table = {'0': '0101010', '1': '0111111', '-1': '0111010', 'D': '0001100', 'A': '0110000',
                             'M': '1110000', '!D': '0001100', '!A': '0110001', '!M': '1110001', '-D': '0001111',
                             '-A': '0110011', '-M': '1110001', 'D+1': '0011111', 'A+1': '0110111', 'M+1': '1110111',
                             'D-1': '0001110', 'A-1': '0110010', 'M-1': '1110010', 'D+A': '0000010', 'D+M': '1000010',
                             'D-A': '0010011', 'D-M': '1010011', 'A-D': '0000111', 'M-D': '1000111', 'D&A': '0000000',
                             'D&M': '1000000', 'D|A': '0010101', 'D|M': '1010101'}
        self.__dest_table = {'null': '000', 'M': '001', 'D': '010', 'DM': '011', 'MD': '011', 'A': '100', 'AM': '101',
                             'AD': '110', 'ADM': '111'}
        self.__jump_table = {'null': '000', 'JGT': '001', 'JEQ': '010', 'JGE': '011', 'JLT': '100', 'JNE': '101',
                             'JLE': '110', 'JMP': '111'}

    def dest(self, string):
        return self.__dest_table[string] if string in self.__dest_table else self.__dest_table['null']

    def comp(self, string):
        return self.__comp_table[string] if string in self.__comp_table else self.__comp_table['null']

    def jump(self, string):
        return self.__jump_table[string] if string in self.__jump_table else self.__jump_table['null']


class SymbolTable:
    def __init__(self):
        self.symbol_table = ({f'R{i}': i for i in range(16)} |
                             {'SCREEN': 16384, 'KBD': 24576, 'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4})
        self.current_num = 15

    def add_entry(self, symbol, address):
        if not self.contains(symbol):
            self.symbol_table[symbol] = address

    def contains(self, symbol):
        return symbol in self.symbol_table

    def get_address(self, symbol):
        return self.symbol_table[symbol]


if __name__ == '__main__':
    files = ['Add', 'MaxL', 'Max', 'RectL', 'Rect', 'PongL', 'Pong']

    assembler = HackAssembler(files)

    while assembler.current_file:
        assembler.initialize()
        assembler.first_pass()
        assembler.second_pass()

        assembler.advance()
