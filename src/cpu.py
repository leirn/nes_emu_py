'''Emulator CPU Modules'''

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

# Addressing modes : http://www.emulator101.com/6502-addressing-modes.html
# Opcodes : http://www.6502.org/tutorials/6502opcodes.html

# https://www.atarimagazines.com/compute/issue53/047_1_All_About_The_Status_Register.php

# https://www.masswerk.at/6502/6502_instruction_set.html

# https://www.gladir.com/CODER/ASM6502/referenceopcode.htm
import sys
from cpu_opcodes import OPCODES
import re
from utils import format_hex_data

class Cpu:

    def __init__(self, emulator):
        self.test_mode = 0
        self.debug = 0
        self.compteur = 0
        self.total_cycles = 0
        self.remaining_cycles = 0
        self.additional_cycle = 0

        self.A = 0
        self.X = 0
        self.Y = 0
        self.PC = 0
        self.SP = 0

        """
        C (carry)
        N (negative)
        Z (zero)
        V (overflow)
        D (decimal)
        """
        self.flagN = 0
        self.flagV = 0
        self.flagB = 0
        self.flagD = 0
        self.flagI = 1
        self.flagZ = 0
        self.flagC = 0
        self.emulator = emulator

    # initialise PC
    def start(self, entry_point = None):
        '''Execute 6502 Start sequence'''

        #Start sequence push stack three time
        self.push(0)
        self.push(0)
        self.push(0)

        if entry_point:
            self.PC = entry_point
        else:
        # Equivalent to JMP ($FFFC)
            self.PC = self.emulator.memory.read_rom_16(0xfffc)
        if self.debug : print(f"Entry point : 0x{format_hex_data(self.PC)}")
        self.total_cycles = 7 # Cout de l'init
        self.remaining_cycles = 7

        return 1

    def nmi(self):
        ''' Raises an NMI interruption'''
        if self.debug : print("NMI interruption detected")
        self.general_interrupt(0xFFFA)

    def irq(self):
        ''' Raises an IRQ interruption'''
        if self.debug : print("IRQ interruption detected")
        self.general_interrupt(0xFFFE)

    def general_interrupt(self, address):
        '''General interruption sequence used for NMI and IRQ

        Interruptions last for 7 CPU cycles
        '''
        self.push(self.PC >> 8)
        self.push(self.PC & 255)
        self.push(self.getP())

        self.flagI = 0

        self.PC = self.emulator.memory.read_rom_16(address)
        self.remaining_cycles = 7 - 1 # do not count current cycle twice
        self.total_cycles += 7

    def next(self):
        ''' Execute the next CPU cycles.

        If There are remaining cycles from previous opcode execution, does noting.
        Otherwise, execute the next opcode

        Raises:
            Exception when opcode is unknown
        '''
        if self.remaining_cycles > 0:
            self.remaining_cycles -= 1
            return

        opcode = self.emulator.memory.read_rom(self.PC)
        try:
            if self.debug > 0:
                self.print_status_summary()

            fn = getattr(self, f"fn_0x{opcode:02x}")
            step, self.remaining_cycles = fn()
            self.remaining_cycles += self.additional_cycle
            self.total_cycles += self.remaining_cycles
            self.remaining_cycles -= 1 # Do not count current cycle twice
            self.additional_cycle = 0
            self.PC += step
            self.compteur += 1
            return
        except KeyError as e:
            print(f"Unknow opcode 0x{opcode:02x} at {' '.join(a+b for a,b in zip(f'{self.PC:x}'[::2], f'{self.PC:x}'[1::2]))}")
            raise e

    def get_cpu_status(self):
        ''' Return a dictionnary containing the current CPU Status. Usefull for debugging'''
        status = dict()
        status["PC"] = self.PC
        status["SP"] = self.SP
        status["A"] = self.A
        status["X"] = self.X
        status["Y"] = self.Y
        status["P"] = self.getP()
        status["CYC"] = self.total_cycles
        status["PPU_LINE"] = self.emulator.ppu.line
        status["PPU_COL"] = self.emulator.ppu.col
        return status

    def getP(self):
        '''Returns the P register which contains the flag status.

        Bit 5 is always set to 1
        '''
        return (self.flagN << 7) | (self.flagV << 6) | (1 << 5) | (self.flagB << 4) | (self.flagD << 3) | (self.flagI << 2) | (self.flagZ << 1) | self.flagC

    def setP(self, p):
        '''Set the P register which contains the flag status.

        When setting the P Register, the break flag is not set.
        '''
        self.flagC = p & 1
        self.flagZ = (p >> 1) & 1
        self.flagI = (p >> 2) & 1
        self.flagD = (p >> 3) & 1
        #self.flagB = (p >> 4) & 1
        self.flagV = (p >> 6) & 1
        self.flagN = (p >> 7) & 1

    def push(self, val):
        '''Push value into stack'''
        self.emulator.memory.write_rom(0x0100 | self.SP, val)
        self.SP = 255 if self.SP == 0 else self.SP - 1

    def pop(self):
        '''Pop value from stack'''
        self.SP = 0 if self.SP == 255 else self.SP + 1
        return self.emulator.memory.read_rom(0x0100 | self.SP)

    def getImmediate(self):
        '''Get 8 bit immediate value on PC + 1'''
        return self.emulator.memory.read_rom(self.PC+1)

    def setZeroPage(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument'''
        self.emulator.memory.write_rom(self.getZeroPageAddress(), val)

    def getZeroPageAddress(self):
        '''Get ZeroPage address to be used for current opcode. Alias to get_immediate'''
        return self.getImmediate()

    def getZeroPageValue(self):
        '''Get val from Zero Page memory. Address is given as opcode 1-byte argument'''
        address= self.getImmediate()
        return self.emulator.memory.read_rom(address)

    def setZeroPageX(self, val):
        self.emulator.memory.write_rom(self.getZeroPageXAddress(), val)

    def getZeroPageXAddress(self):
        return (self.emulator.memory.read_rom(self.PC+1) + self.X) & 255

    def getZeroPageXValue(self):
        address = self.getZeroPageXAddress()
        return self.emulator.memory.read_rom(address)

    def setZeroPageY(self, val):
        self.emulator.memory.write_rom(self.getZeroPageYAddress(), val)

    def getZeroPageYAddress(self):
        return  (self.emulator.memory.read_rom(self.PC+1) + self.Y) & 255

    def getZeroPageYValue(self):
        address = self.getZeroPageYAddress()
        return self.emulator.memory.read_rom(address)

    def setAbsolute(self, val):
        self.emulator.memory.write_rom(self.getAbsoluteAddress(), val)

    def getAbsoluteAddress(self):
        return self.emulator.memory.read_rom_16(self.PC+1)

    def getAbsoluteValue(self):
        address = self.getAbsoluteAddress()
        return self.emulator.memory.read_rom(address)

    def setAbsoluteX(self, val):
        self.emulator.memory.write_rom(self.getAbsoluteXAddress(), val)

    def getAbsoluteXAddress(self):
        address = self.emulator.memory.read_rom_16(self.PC+1)
        target_address = (address + self.X) & 0xFFFF
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getAbsoluteXValue(self):
        address = self.getAbsoluteXAddress()
        return self.emulator.memory.read_rom(address)

    def setAbsoluteY(self, val):
        self.emulator.memory.write_rom(self.getAbsoluteYAddress(), val)

    def getAbsoluteYAddress(self):
        address = self.emulator.memory.read_rom_16(self.PC+1)
        target_address = (address + self.Y) & 0xFFFF
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getAbsoluteYValue(self):
        address = self.getAbsoluteYAddress()
        return self.emulator.memory.read_rom(address)

    def getIndirectXAddress(self):
        address = self.getZeroPageXAddress()
        return self.emulator.memory.read_rom_16_no_crossing_page(address)

    def getIndirectXValue(self):
        address = self.getIndirectXAddress()
        return self.emulator.memory.read_rom(address)

    def setIndirectX(self, val):
        self.emulator.memory.write_rom(self.getIndirectXAddress(), val)

    def getIndirectYAddress(self):
        address = self.getZeroPageAddress()
        target_address = 0xFFFF & (self.emulator.memory.read_rom_16_no_crossing_page(address )+ self.Y)
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getIndirectYValue(self):
        address = self.getIndirectYAddress()
        return self.emulator.memory.read_rom(address)

    def setIndirectY(self, val):
        self.emulator.memory.write_rom(self.getIndirectYAddress(), val)

    def setFlagNZ(self, val):
        '''Sets flags N and Z according to value'''
        self.setFlagN(val)
        self.setFlagZ(val)

    def setFlagN(self, val):
        ''' Set Negative Flag according to value'''
        if val < 0:
            self.flagN = 1
        else:
            self.flagN = val >> 7

    def setFlagZ(self, val):
        ''' Set Zero Flag according to value'''
        self.flagZ = 1 if val == 0 else 0

    def adc(self, val):
        adc = val + self.A + self.flagC
        self.flagC = adc >> 8
        result = 255 & adc

        self.flagV = not not ((self.A ^ result) & (val ^ result) & 0x80)

        self.A = result

        self.setFlagNZ(self.A)

    # ADC #$44
    # Immediate
    def fn_0x69(self) :
        self.adc(self.getImmediate())
        return (2, 2)

    # ADC $44
    # Zero Page
    def fn_0x65(self) :
        self.adc(self.getZeroPageValue())
        return (2, 3)

    # ADC $44, X
    # Zero Page, X
    def fn_0x75(self) :
        self.adc(self.getZeroPageXValue())
        return (2, 4)

    # ADC $4400
    # Absolute
    def fn_0x6d(self) :
        self.adc(self.getAbsoluteValue())
        return (3, 4)

    # ADC $4400, X
    # Absolute, X
    def fn_0x7d(self) :
        self.adc(self.getAbsoluteXValue())
        return (3, 4)

    # ADC $4400, Y
    # Absolute, Y
    def fn_0x79(self) :
        self.adc(self.getAbsoluteYValue())
        return (3, 4)

    # ADC ($44, X)
    # Indirect, X
    def fn_0x61(self) :
        self.adc(self.getIndirectXValue())
        return (2, 6)

    # ADC ($44), Y
    # Indirect, Y
    def fn_0x71(self) :
        self.adc(self.getIndirectYValue())
        return (2, 5)

    # AND #$44
    # Immediate
    def fn_0x29(self) :
        self.A &= self.getImmediate()
        self.setFlagNZ(self.A)
        return (2, 2)

    # AND $44
    # Zero Page
    def fn_0x25(self) :
        self.A &= self.getZeroPageValue()
        self.setFlagNZ(self.A)
        return (2, 3)

    # AND $44, X
    # Zero Page, X
    def fn_0x35(self) :
        self.A &= self.getZeroPageXValue()
        self.setFlagNZ(self.A)
        return (2, 4)

    # AND $4400
    # Absolute
    def fn_0x2d(self) :
        self.A &= self.getAbsoluteValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # AND $4400, X
    # Absolute, X
    def fn_0x3d(self) :
        self.A &= self.getAbsoluteXValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # AND $4400, Y
    # Absolute, Y
    def fn_0x39(self) :
        self.A &= self.getAbsoluteYValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # AND ($44, X)
    # Indirect, X
    def fn_0x21(self) :
        self.A &= self.getIndirectXValue()
        self.setFlagNZ(self.A)
        return (2, 6)

    # AND ($44), Y
    # Indirect, Y
    def fn_0x31(self) :
        self.A &= self.getIndirectYValue()
        self.setFlagNZ(self.A)
        return (2, 5)

    # ASL A
    # Accumulator
    def fn_0x0a(self) :
        self.flagC = self.A >> 7
        self.A = (self.A << 1) & 0b11111111
        self.setFlagNZ(self.A)
        return (1, 2)

    # ASL $44
    # Zero Page
    def fn_0x06(self) :
        value = self.getZeroPageValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setZeroPage(value)
        self.setFlagNZ(value)
        return (2, 5)

    # ASL $44, X
    # Zero Page, X
    def fn_0x16(self) :
        value = self.getZeroPageXValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setZeroPageX(value)
        self.setFlagNZ(value)
        return (2, 6)

    # ASL $4400
    # Absolute
    def fn_0x0e(self) :
        value = self.getAbsoluteValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsolute(value)
        self.setFlagNZ(value)
        return (3, 6)

    # ASL $4400, X
    # Absolute, X
    def fn_0x1e(self) :
        value = self.getAbsoluteXValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsoluteX(value)
        self.setFlagNZ(value)
        return (3, 7)

    # BIT $44
    # Zero Page
    def fn_0x24(self) :
        tocomp = self.getZeroPageValue()
        value = tocomp & self.A
        self.setFlagZ(value)
        self.flagN = (tocomp >> 7) & 1
        self.flagV = (tocomp >> 6) & 1
        return (2, 3)

    # BIT $4400
    # Absolute
    def fn_0x2c(self) :
        tocomp = self.getAbsoluteValue()
        value = tocomp & self.A
        self.setFlagZ(value)
        self.flagN = (tocomp >> 7) & 1
        self.flagV = (tocomp >> 6) & 1
        return (3, 4)

    # BPL
    # Relative
    def fn_0x10(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagN == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle += 1
        return (2, 2)

    # BMI
    # Relative
    def fn_0x30(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagN == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BVC
    # Relative
    def fn_0x50(self) :
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagV == 0:
            self.PC += signed
            self.additional_cycle += 1
        return (2, 2)

    # BVS
    # Relative
    def fn_0x70(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagV == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BCC
    # Relative
    def fn_0x90(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagC == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BCS
    # Relative
    def fn_0xb0(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagC == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BNE
    # Relative
    def fn_0xd0(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagZ == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BEQ
    # Relative
    def fn_0xf0(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.flagZ == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BRK
    # Implied
    # TODO : Should set B flag to 1
    def fn_0x00(self) :
        self.PC += 1
        self.push(self.PC >> 8)
        self.push(self.PC & 255)
        self.push(self.getP())
        self.PC = self.emulator.memory.read_rom_16(0xFFFE)
        return (0, 7)

    def cmp(self, op1, op2) :
        '''General implementation for CMP operation'''
        if op1 > op2:
            if op1-op2 >= 0x80:
                self.flagC = 1
                self.flagN = 1
                self.flagZ = 0
            else:
                self.flagC = 1
                self.flagN = 0
                self.flagZ = 0
        elif op1 == op2:
            self.flagC = 1
            self.flagN = 0
            self.flagZ = 1
        else:
            if op2 - op1 >= 0x80:
                self.flagC = 0
                self.flagN = 0
                self.flagZ = 0
            else:
                self.flagC = 0
                self.flagN = 1
                self.flagZ = 0

    # CMP #$44
    # Immediate
    def fn_0xc9(self) :
        self.cmp(self.A, self.getImmediate())
        return (2, 2)

    # CMP $44
    # Zero Page
    def fn_0xc5(self) :
        self.cmp(self.A, self.getZeroPageValue())
        return (2, 3)

    # CMP $44, X
    # Zero Page, X
    def fn_0xd5(self) :
        self.cmp(self.A, self.getZeroPageXValue())
        return (2, 4)

    # CMP $4400
    # Absolute
    def fn_0xcd(self) :
        self.cmp(self.A, self.getAbsoluteValue())
        return (3, 4)

    # CMP $4400, X
    # Absolute, X
    def fn_0xdd(self) :
        self.cmp(self.A, self.getAbsoluteXValue())
        return (3, 4)

    # CMP $4400, Y
    # Absolute, Y
    def fn_0xd9(self) :
        self.cmp(self.A, self.getAbsoluteYValue())
        return (3, 4)

    # CMP ($44), X
    # Indirect, X
    def fn_0xc1(self) :
        self.cmp(self.A, self.getIndirectXValue())
        return (2, 6)

    # CMP ($44), Y
    # Indirect, Y
    def fn_0xd1(self) :
        self.cmp(self.A, self.getIndirectYValue())
        return (2, 5)

    # CPX #$44
    # Immediate
    def fn_0xe0(self) :
        self.cmp(self.X, self.getImmediate())
        return (2, 2)

    # CPX $44
    # Zero Page
    def fn_0xe4(self) :
        self.cmp(self.X, self.getZeroPageValue())
        return (2, 3)

    # CPX $4400
    # Absolute
    def fn_0xec(self) :
        self.cmp(self.X, self.getAbsoluteValue())
        return (3, 4)

    # CPY #$44
    # Immediate
    def fn_0xc0(self) :
        self.cmp(self.Y, self.getImmediate())
        return (2, 2)

    # CPY $44
    # Zero Page
    def fn_0xc4(self) :
        self.cmp(self.Y, self.getZeroPageValue())
        return (2, 3)

    # CPY $4400
    # Absolute
    def fn_0xcc(self) :
        self.cmp(self.Y, self.getAbsoluteValue())
        return (3, 4)

    # DEC $44
    # Zero Page
    def fn_0xc6(self) :
        value = self.getZeroPageValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPage(value)
        self.setFlagNZ(value)
        return (2, 5)

    # DEC $44, X
    # Zero Page, X
    def fn_0xd6(self) :
        value = self.getZeroPageXValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPageX(value)
        self.setFlagNZ(value)
        return (2, 6)

    # DEC $4400
    # Absolute
    def fn_0xce(self) :
        value = self.getAbsoluteValue()
        value = 255 if value == 0 else value - 1
        self.setAbsolute(value)
        self.setFlagNZ(value)
        return (3, 6)

    # DEC $4400, X
    # Absolute, X
    def fn_0xde(self) :
        value = self.getAbsoluteXValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteX(value)
        self.setFlagNZ(value)
        return (3, 7)

    # DCP $44
    # Zero Page
    def fn_0xc7(self):
        value = self.getZeroPageValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPage(value)
        self.cmp(self.A, value)
        return (2, 5)

    # DCP $44, X
    # Zero Page, X
    def fn_0xd7(self):
        value = self.getZeroPageXValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPageX(value)
        self.cmp(self.A, value)
        return (2, 6)

    # DCP $4400
    # Absolute
    def fn_0xcf(self):
        value = self.getAbsoluteValue()
        value = 255 if value == 0 else value - 1
        self.setAbsolute(value)
        self.cmp(self.A, value)
        return (3, 6)

    # DCP $4400, X
    # Absolute, X
    def fn_0xdf(self):
        value = self.getAbsoluteXValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteX(value)
        self.cmp(self.A, value)
        return (3, 7)

    # DCP $4400, Y
    # Absolute, Y
    def fn_0xdb(self):
        value = self.getAbsoluteYValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteY(value)
        self.cmp(self.A, value)
        return (3, 7)

    # DCP ($44), X
    # Indirect, X
    def fn_0xc3(self):
        value = self.getIndirectXValue()
        value = 255 if value == 0 else value - 1
        self.setIndirectX(value)
        self.cmp(self.A, value)
        return (2, 8)

    # DCP ($44, Y)
    # Indirect, Y
    def fn_0xd3(self):
        value = self.getIndirectYValue()
        value = 255 if value == 0 else value - 1
        self.setIndirectY(value)
        self.cmp(self.A, value)
        return (2, 8)

    # ISC $44
    # Zero Page
    def fn_0xe7(self):
        value = self.getZeroPageValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPage(value)
        self.sbc(value)
        return (2, 5)

    # ISC $44, X
    # Zero Page, X
    def fn_0xf7(self):
        value = self.getZeroPageXValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPageX(value)
        self.sbc(value)
        return (2, 6)

    # ISC $4400
    # Absolute
    def fn_0xef(self):
        value = self.getAbsoluteValue()
        value = 0 if value == 255 else value + 1
        self.setAbsolute(value)
        self.sbc(value)
        return (3, 6)

    # ISC $4400, X
    # Absolute, X
    def fn_0xff(self):
        value = self.getAbsoluteXValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteX(value)
        self.sbc(value)
        return (3, 7)

    # ISC $4400, Y
    # Absolute, Y
    def fn_0xfb(self):
        value = self.getAbsoluteYValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteY(value)
        self.sbc(value)
        return (3, 7)

    # ISC ($44), X
    # Indirect, X
    def fn_0xe3(self):
        value = self.getIndirectXValue()
        value = 0 if value == 255 else value + 1
        self.setIndirectX(value)
        self.sbc(value)
        return (2, 8)

    # ISC ($44, Y)
    # Indirect, Y
    def fn_0xf3(self):
        value = self.getIndirectYValue()
        value = 0 if value == 255 else value + 1
        self.setIndirectY(value)
        self.sbc(value)
        return (2, 4)

    # EOR #$44
    # Immediate
    def fn_0x49(self) :
        self.A ^= self.getImmediate()
        self.setFlagNZ(self.A)
        return (2, 2)

    # EOR $44
    # Zero Page
    def fn_0x45(self) :
        self.A ^= self.getZeroPageValue()
        self.setFlagNZ(self.A)
        return (2, 3)

    # EOR $44, X
    # Zero Page, X
    def fn_0x55(self) :
        self.A ^= self.getZeroPageXValue()
        self.setFlagNZ(self.A)
        return (2, 4)

    # EOR $4400
    # Absolute
    def fn_0x4d(self) :
        self.A ^= self.getAbsoluteValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # EOR $4400, X
    # Absolute, X
    def fn_0x5d(self) :
        self.A ^= self.getAbsoluteXValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # EOR $4400, Y
    # Absolute, Y
    def fn_0x59(self) :
        self.A ^= self.getAbsoluteYValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # EOR ($44, X)
    # Indirect, X
    def fn_0x41(self) :
        self.A ^= self.getIndirectXValue()
        self.setFlagNZ(self.A)
        return (2, 6)

    # EOR ($44), Y
    # Indirect, Y
    def fn_0x51(self) :
        self.A ^= self.getIndirectYValue()
        self.setFlagNZ(self.A)
        return (2, 5)

    # CLC
    # Implied
    def fn_0x18(self) :
        self.flagC = 0
        return (1, 2)

    # SEC
    # Implied
    def fn_0x38(self) :
        self.flagC = 1
        return (1, 2)

    # CLI
    # Implied
    def fn_0x58(self) :
        self.flagI = 0
        return (1, 2)

    # SEI
    # Implied
    def fn_0x78(self) :
        self.flagI = 1
        return (1, 2)

    # CLV
    # Implied
    def fn_0xb8(self) :
        self.flagV = 0
        return (1, 2)

    # CLD
    # Implied
    def fn_0xd8(self) :
        self.flagD = 0
        return (1, 2)

    # SED
    # Implied
    def fn_0xf8(self) :
        self.flagD = 1
        return (1, 2)

    # INC $44
    # Zero Page
    def fn_0xe6(self) :
        value = self.getZeroPageValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPage(value)
        self.setFlagNZ(value)
        return (2, 5)

    # INC $44, X
    # Zero Page, X
    def fn_0xf6(self) :
        value = self.getZeroPageXValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPageX(value)
        self.setFlagNZ(value)
        return (2, 6)

    # INC $4400
    # Absolute
    def fn_0xee(self) :
        value = self.getAbsoluteValue()
        value = 0 if value == 255 else value + 1
        self.setAbsolute(value)
        self.setFlagNZ(value)
        return (3, 6)

    # INC $4400, X
    # Absolute, X
    def fn_0xfe(self) :
        value = self.getAbsoluteXValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteX(value)
        self.setFlagNZ(value)
        return (3, 7)

    # JMP $5597
    # Absolute
    def fn_0x4c(self) :
        self.PC = self.getAbsoluteAddress()
        return (0, 3)

    # JMP ($5597)
    # Indirect
    def fn_0x6c(self) :
        address = self.getAbsoluteAddress()
        if address & 0xFF == 0xFF: # Strange behaviour in nestest.net where direct jump to re-aligned address where address at end of page
            address += 1
            if self.debug :  print(f"JMP address : {address:4x}")
        else:
            address = self.emulator.memory.read_rom_16(address)
        if self.debug : print(f"JMP address : {address:4x}")
        self.PC = address
        return (0, 5)

    # JSR $5597
    # Absolute
    def fn_0x20(self) :
        pc = self.PC + 2
        high = pc >> 8
        low =  pc & 255
        self.push(high) # little endian
        self.push(low)
        self.PC = self.getAbsoluteAddress()
        return (0, 6)

    # LDA #$44
    # Immediate
    def fn_0xa9(self) :
        self.A = self.getImmediate()
        self.setFlagNZ(self.A)
        return (2, 2)

    # LDA $44
    # Zero Page
    def fn_0xa5(self) :
        self.A =self.getZeroPageValue()
        self.setFlagNZ(self.A)
        return (2, 3)

    # LDA $44, X
    # Zero Page, X
    def fn_0xb5(self) :
        self.A = self.getZeroPageXValue()
        self.setFlagNZ(self.A)
        return (2, 4)

    # LDA $4400
    # Absolute
    def fn_0xad(self) :
        self.A = self.getAbsoluteValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # LDA $4400, X
    # Absolute, X
    def fn_0xbd(self) :
        self.A = self.getAbsoluteXValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # LDA $4400, Y
    # Absolute, Y
    def fn_0xb9(self) :
        self.A = self.getAbsoluteYValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # LDA ($44, X)
    # Indirect, X
    def fn_0xa1(self) :
        self.A = self.getIndirectXValue()
        self.setFlagNZ(self.A)
        return (2, 6)

    # LDA ($44), Y
    # Indirect, Y
    def fn_0xb1(self) :
        self.A = self.getIndirectYValue()
        self.setFlagNZ(self.A)
        return (2, 5)

    # LDX #$44
    # Immediate
    def fn_0xa2(self) :
        self.X = self.getImmediate()
        self.setFlagNZ(self.X)
        return (2, 2)

    # LDX $44
    # Zero Page
    def fn_0xa6(self) :
        self.X = self.getZeroPageValue()
        self.setFlagNZ(self.X)
        return (2, 3)

    # LDX $44, Y
    # Zero Page, Y
    def fn_0xb6(self) :
        self.X = self.getZeroPageYValue()
        self.setFlagNZ(self.X)
        return (2, 4)

    # LDX $4400
    # Absolute
    def fn_0xae(self) :
        self.X = self.getAbsoluteValue()
        self.setFlagNZ(self.X)
        return (3, 4)

    # LDX $4400, Y
    # Absolute, Y
    def fn_0xbe(self) :
        self.X = self.getAbsoluteYValue()
        self.setFlagNZ(self.X)
        return (3, 4)

    # LDY #$44
    # Immediate
    def fn_0xa0(self) :
        self.Y = self.getImmediate()
        self.setFlagNZ(self.Y)
        return (2, 2)

    # LDY $44
    # Zero Page
    def fn_0xa4(self) :
        self.Y = self.getZeroPageValue()
        self.setFlagNZ(self.X)
        return (2, 3)

    # LDY $44, X
    # Zero Page, X
    def fn_0xb4(self) :
        self.Y = self.getZeroPageXValue()
        self.setFlagNZ(self.Y)
        return (2, 4)

    # LDY $4400
    # Absolute
    def fn_0xac(self) :
        self.Y =self.getAbsoluteValue()
        self.setFlagNZ(self.Y)
        return (3, 4)

    # LDY $4400, X
    # Absolute, X
    def fn_0xbc(self) :
        self.Y = self.getAbsoluteXValue()
        self.setFlagNZ(self.Y)
        return (3, 4)

    # LSR A
    # Accumulator
    def fn_0x4a(self) :
        self.flagC = self.A & 1
        self.A = self.A >> 1
        self.setFlagNZ(self.A)
        return (1, 2)

    # LSR $44
    # Zero Page
    def fn_0x46(self) :
        value = self.getZeroPageValue()
        self.flagC = value & 1
        value = value >> 1
        self.setZeroPage(value)
        self.setFlagNZ(value)
        return (2, 5)

    # LSR $44, X
    # Zero Page, X
    def fn_0x56(self) :
        value = self.getZeroPageXValue()
        self.flagC = value & 1
        value = value >> 1
        self.setZeroPageX(value)
        self.setFlagNZ(value)
        return (2, 6)

    # LSR $4400
    # Absolute
    def fn_0x4e(self) :
        value = self.getAbsoluteValue()
        self.flagC = value & 1
        value = value >> 1
        self.setAbsolute(value)
        self.setFlagNZ(value)
        return (3, 6)

    # LSR $4400, X
    # Absolute, X
    def fn_0x5e(self) :
        value = self.getAbsoluteXValue()
        self.flagC = value & 1
        value = value >> 1
        self.setAbsoluteX(value)
        self.setFlagNZ(value)
        return (3, 7)

    # NOP
    # Implied
    # Disabling no-self-use pylint control
    # pylint: disable=R0201
    def fn_0xea(self) : return (1, 2)
    def fn_0x1a(self) : return (1, 2)
    def fn_0x3a(self) : return (1, 2)
    def fn_0x5a(self) : return (1, 2)
    def fn_0x7a(self) : return (1, 2)
    def fn_0xda(self) : return (1, 2)
    def fn_0xfa(self) : return (1, 2)
    # DOP
    def fn_0x04(self) : return (2, 3)
    def fn_0x14(self) : return (2, 4)
    def fn_0x34(self) : return (2, 4)
    def fn_0x44(self) : return (2, 3)
    def fn_0x54(self) : return (2, 4)
    def fn_0x64(self) : return (2, 3)
    def fn_0x74(self) : return (2, 4)
    def fn_0x80(self) : return (2, 2)
    def fn_0x82(self) : return (2, 2)
    def fn_0x89(self) : return (2, 2)
    def fn_0xc2(self) : return (2, 2)
    def fn_0xd4(self) : return (2, 4)
    def fn_0xe2(self) : return (2, 2)
    def fn_0xf4(self) : return (2, 4)

    #TOP
    def fn_0x0c(self) : return (3, 4)
    def fn_0x1c(self) : return (3, 4)
    def fn_0x3c(self) : return (3, 4)
    def fn_0x5c(self) : return (3, 4)
    def fn_0x7c(self) : return (3, 4)
    def fn_0xdc(self) : return (3, 4)
    def fn_0xfc(self) : return (3, 4)
    # Restoring no-self-use pylint control
    # pylint: enable=R0201

    # ORA #$44
    # Immediate
    def fn_0x09(self) :
        self.A |= self.getImmediate()
        self.setFlagNZ(self.A)
        return (2, 2)

    # ORA $44
    # Zero Page
    def fn_0x05(self) :
        self.A |= self.getZeroPageValue()
        self.setFlagNZ(self.A)
        return (2, 3)

    # ORA $44, X
    # Zero Page, X
    def fn_0x15(self) :
        self.A |= self.getZeroPageXValue()
        self.setFlagNZ(self.A)
        return (2, 4)

    # ORA $4400
    # Absolute
    def fn_0x0d(self) :
        self.A |= self.getAbsoluteValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # ORA $4400, X
    # Absolute, X
    def fn_0x1d(self) :
        self.A |= self.getAbsoluteXValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # ORA $4400, Y
    # Absolute, Y
    def fn_0x19(self) :
        self.A |= self.getAbsoluteYValue()
        self.setFlagNZ(self.A)
        return (3, 4)

    # ORA ($44, X)
    # Indirect, X
    def fn_0x01(self) :
        self.A |= self.getIndirectXValue()
        self.setFlagNZ(self.A)
        return (2, 6)

    # ORA ($44), Y
    # Indirect, Y
    def fn_0x11(self) :
        self.A |= self.getIndirectYValue()
        self.setFlagNZ(self.A)
        return (2, 5)

    # SLO $44
    # Zero Page
    def fn_0x07(self):
        self.fn_0x06() # ASL
        self.fn_0x05() # ORA
        return (2, 5)

    # SLO $44, X
    # Zero Page, X
    def fn_0x17(self):
        self.fn_0x16() # ASL
        self.fn_0x15() # ORA
        return (2, 6)

    # SLO $4400
    # Absolute
    def fn_0x0f(self):
        self.fn_0x0e() # ASL
        self.fn_0x0d() # ORA
        return (3, 6)

    # SLO $4400, X
    # Absolute, X
    def fn_0x1f(self):
        self.fn_0x1e() # ASL
        self.fn_0x1d() # ORA
        return (3, 7)

    # SLO $4400, Y
    # Absolute, Y
    def fn_0x1b(self):
        value = self.getAbsoluteYValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsoluteY(value)
        self.fn_0x19() # ORA
        return (3, 7)

    # SLO ($44), X
    # Indirect, X
    def fn_0x03(self):
        value = self.getIndirectXValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setIndirectX(value)
        self.fn_0x01() # ORA
        return (2, 8)

    # SLO ($44, Y)
    # Indirect, Y
    def fn_0x13(self):
        value = self.getIndirectYValue()
        self.flagC = value >> 7
        value = (value << 1) & 0b11111111
        self.setIndirectY(value)
        self.fn_0x11() # ORA
        return (2, 8)

    # RLA $44
    # Zero Page
    def fn_0x27(self):
        self.fn_0x26() # ROL
        self.fn_0x25() # AND
        return (2, 5)

    # RLA $44, X
    # Zero Page, X
    def fn_0x37(self):
        self.fn_0x36() # ROL
        self.fn_0x35() # AND
        return (2, 6)

    # RLA $4400
    # Absolute
    def fn_0x2f(self):
        self.fn_0x2e() # ROL
        self.fn_0x2d() # AND
        return (3, 6)

    # RLA $4400, X
    # Absolute, X
    def fn_0x3f(self):
        self.fn_0x3e() # ROL
        self.fn_0x3d() # AND
        return (3, 7)

    # RLA $4400, Y
    # Absolute, Y
    def fn_0x3b(self):
        val = self.getAbsoluteYValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setAbsoluteY(val)
        self.fn_0x39() # AND
        return (3, 7)

    # RLA ($44), X
    # Indirect, X
    def fn_0x23(self):
        val = self.getIndirectXValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setIndirectX(val)
        self.fn_0x21() # AND
        return (2, 8)

    # RLA ($44, Y)
    # Indirect, Y
    def fn_0x33(self):
        val = self.getIndirectYValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setIndirectY(val)
        self.fn_0x31() # AND
        return (2, 8)

    # RRA $44
    # Zero Page
    def fn_0x67(self):
        self.fn_0x66() # ROR
        self.fn_0x65() # ADC
        return (2, 5)

    # RRA $44, X
    # Zero Page, X
    def fn_0x77(self):
        self.fn_0x76() # ROR
        self.fn_0x75() # ADC
        return (2, 6)

    # RRA $4400
    # Absolute
    def fn_0x6f(self):
        self.fn_0x6e() # ROR
        self.fn_0x6d() # ADC
        return (3, 6)

    # RRA $4400, X
    # Absolute, X
    def fn_0x7f(self):
        self.fn_0x7e() # ROR
        self.fn_0x7d() # ADC
        return (3, 7)

    # RRA $4400, Y
    # Absolute, Y
    def fn_0x7b(self):
        val = self.getAbsoluteYValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setAbsoluteY(val)
        self.fn_0x79() # ADC
        return (3, 7)

    # RRA ($44), X
    # Indirect, X
    def fn_0x63(self):
        val = self.getIndirectXValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setIndirectX(val)
        self.fn_0x61() # ADC
        return (2, 8)

    # RRA ($44, Y)
    # Indirect, Y
    def fn_0x73(self):
        val = self.getIndirectYValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setIndirectY(val)
        self.fn_0x71() # ADC
        return (2, 8)

    # SRE $44
    # Zero Page
    def fn_0x47(self):
        self.fn_0x46() # LSR
        self.fn_0x45() # EOR
        return (2, 5)

    # SRE $44, X
    # Zero Page, X
    def fn_0x57(self):
        self.fn_0x56() # LSR
        self.fn_0x55() # EOR
        return (2, 6)

    # SRE $4400
    # Absolute
    def fn_0x4f(self):
        self.fn_0x4e() # LSR
        self.fn_0x4d() # EOR
        return (3, 6)

    # SRE $4400, X
    # Absolute, X
    def fn_0x5f(self):
        self.fn_0x5e() # LSR
        self.fn_0x5d() # EOR
        return (3, 7)

    # SRE $4400, Y
    # Absolute, Y
    def fn_0x5b(self):
        val = self.getAbsoluteYValue()
        self.flagC = val & 1
        val = val >> 1
        self.setAbsoluteY(val)
        self.fn_0x59() # EOR
        return (3, 7)

    # SRE ($44), X
    # Indirect, X
    def fn_0x43(self):
        val = self.getIndirectXValue()
        self.flagC = val & 1
        val = val >> 1
        self.setIndirectX(val)
        self.fn_0x41() # EOR
        return (2, 8)

    # SRE ($44, Y)
    # Indirect, Y
    def fn_0x53(self):
        val = self.getIndirectYValue()
        self.flagC = val & 1
        val = val >> 1
        self.setIndirectY(val)
        self.fn_0x51() # EOR
        return (2, 8)

    # TAX
    # Implied
    def fn_0xaa(self) :
        self.X = self.A
        self.setFlagNZ(self.X)
        return (1, 2)

    # TXA
    # Implied
    def fn_0x8a(self) :
        self.A = self.X
        self.setFlagNZ(self.A)
        return (1, 2)

    # DEX
    # Implied
    def fn_0xca(self) :
        self.X = self.X - 1 if self.X > 0 else 255
        self.setFlagNZ(self.X)
        return (1, 2)

    # INX
    # Implied
    def fn_0xe8(self) :
        self.X = self.X + 1 if self.X < 255 else 0
        self.setFlagNZ(self.X)
        return (1, 2)

    # TAY
    # Implied
    def fn_0xa8(self) :
        self.Y = self.A
        self.setFlagNZ(self.Y)
        return (1, 2)

    # TYA
    # Implied
    def fn_0x98(self) :
        self.A = self.Y
        self.setFlagNZ(self.A)
        return (1, 2)

    # DEY
    # Implied
    def fn_0x88(self) :
        self.Y = self.Y - 1 if self.Y > 0 else 255
        self.setFlagNZ(self.Y)
        return (1, 2)

    # INY
    # Implied
    def fn_0xc8(self) :
        self.Y = self.Y + 1 if self.Y < 255 else 0
        self.setFlagNZ(self.Y)
        return (1, 2)

    # ROL A
    # Accumulator
    def fn_0x2a(self) :
        self.A = (self.A << 1) | (self.flagC)
        self.flagC = self.A >> 8
        self.A &= 255
        self.setFlagNZ(self.A)
        return (1, 2)


    # ROL $44
    # Zero Page
    def fn_0x26(self) :
        val = self.getZeroPageValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setZeroPage(val)
        self.setFlagNZ(val)
        return (2, 5)

    # ROL $44, X
    # Zero Page, X
    def fn_0x36(self) :
        val = self.getZeroPageXValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setZeroPageX(val)
        self.setFlagNZ(val)
        return (2, 6)

    # ROL $4400
    # Absolute
    def fn_0x2e(self) :
        val = self.getAbsoluteValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setAbsolute(val)
        self.setFlagNZ(val)
        return (3, 6)

    # ROL $4400, X
    # Absolute, X
    def fn_0x3e(self) :
        val = self.getAbsoluteXValue()
        val = (val << 1) | (self.flagC)
        self.flagC = val >> 8
        val &= 255
        self.setAbsoluteX(val)
        self.setFlagNZ(val)
        return (3, 7)

    # ROR A
    # Accumulator
    def fn_0x6a(self) :
        carry = self.A & 1
        self.A = (self.A >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setFlagNZ(self.A)
        return (1, 2)

    # ROR $44
    # Zero Page
    def fn_0x66(self) :
        val = self.getZeroPageValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setZeroPage(val)
        self.setFlagNZ(val)
        return (2, 5)

    # ROR $44, X
    # Zero Page, X
    def fn_0x76(self) :
        val = self.getZeroPageXValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setZeroPageX(val)
        self.setFlagNZ(val)
        return (2, 6)

    # ROR $4400
    # Absolute
    def fn_0x6e(self) :
        val = self.getAbsoluteValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setAbsolute(val)
        self.setFlagNZ(val)
        return (3, 6)

    # ROR $4400, X
    # Absolute, X
    def fn_0x7e(self) :
        val = self.getAbsoluteXValue()
        carry = val & 1
        val = (val >> 1) | (self.flagC << 7)
        self.flagC = carry
        self.setAbsoluteX(val)
        self.setFlagNZ(val)
        return (3, 7)

    # RTI
    # Implied
    def fn_0x40(self) :
        self.setP(self.pop())
        low = self.pop()
        high = self.pop()
        self.PC = (high << 8) + low
        return (0, 6)

    # RTS
    # Implied
    def fn_0x60(self) :
        low = self.pop()
        high = self.pop()
        self.PC = (high << 8) + low + 1 # JSR increment only by two, and RTS add the third
        return (0, 6)

    def sbc(self, val):
        self.adc(255-val)

    # sbc #$44
    # Immediate
    def fn_0xe9(self) :
        self.sbc(self.getImmediate())
        return (2, 2)
    # 0xeb alias to 0x e9
    def fn_0xeb(self) :
        return self.fn_0xe9()

    # sbc $44
    # Zero Page
    def fn_0xe5(self) :
        self.sbc(self.getZeroPageValue())
        return (2, 3)

    # sbc $44, X
    # Zero Page, X
    def fn_0xf5(self) :
        self.sbc(self.getZeroPageXValue())
        return (2, 4)

    # sbc $4400
    # Absolute
    def fn_0xed(self) :
        self.sbc(self.getAbsoluteValue())
        return (3, 4)

    # sbc $4400, X
    # Absolute, X
    def fn_0xfd(self) :
        self.sbc(self.getAbsoluteXValue())
        return (3, 4)

    # sbc $4400, Y
    # Absolute, Y
    def fn_0xf9(self) :
        self.sbc(self.getAbsoluteYValue())
        return (3, 4)

    # sbc ($44, X)
    # Indirect, X
    def fn_0xe1(self) :
        self.sbc(self.getIndirectXValue())
        return (2, 6)

    # sbc ($44), Y
    # Indirect, Y
    def fn_0xf1(self) :
        self.sbc(self.getIndirectYValue())
        return (2, 5)

    # STA $44
    # Zero Page
    def fn_0x85(self) :
        address = self.getZeroPageAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (2, 3 + extra_cycles)

    # STA $44, X
    # Zero Page, X
    def fn_0x95(self) :
        address = self.getZeroPageXAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (2, 4 + extra_cycles)

    # STA $4400
    # Absolute
    def fn_0x8d(self) :
        address = self.getAbsoluteAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (3, 4 + extra_cycles)

    # STA $4400, X
    # Absolute, X
    def fn_0x9d(self) :
        address = self.getAbsoluteXAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (3, 5 + extra_cycles)

    # STA $4400, Y
    # Absolute, Y
    def fn_0x99(self) :
        address = self.getAbsoluteYAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (3, 5 + extra_cycles)

    # STA ($44, X)
    # Indirect, X
    def fn_0x81(self) :
        address = self.getIndirectXAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (2, 6 + extra_cycles)

    # STA ($44), Y
    # Indirect, Y
    def fn_0x91(self) :
        address = self.getIndirectYAddress()
        extra_cycles = self.emulator.memory.write_rom(address, self.A)
        return (2, 6 + extra_cycles)

    # TXS
    # Implied
    # Affect no flag
    def fn_0x9a(self) :
        self.SP = self.X
        return (1, 2)

    # TSX
    # Implied
    def fn_0xba(self) :
        self.X = self.SP
        self.setFlagNZ(self.X)
        return (1, 2)

    # PHA
    # Implied
    def fn_0x48(self) :
        self.push(self.A)
        return (1, 3)

    # PLA
    # Implied
    def fn_0x68(self) :
        self.A = self.pop()
        self.setFlagNZ(self.A)
        return (1, 4)

    # PHP
    # Implied
    def fn_0x08(self) :
        # create status byte
        p = self.getP() | (1 << 4)
        self.push(p)
        return (1, 3)

    # PLP
    # Implied
    def fn_0x28(self) :
        p = self.pop()
        self.setP(p)
        return (1, 4)

    # STX $44
    # Zero Page
    def fn_0x86(self) :
        address = self.getZeroPageAddress()
        self.emulator.memory.write_rom(address, self.X)
        return (2, 3)

    # STX $44, Y
    # Zero Page, Y
    def fn_0x96(self) :
        address = self.getZeroPageYAddress()
        self.emulator.memory.write_rom(address, self.X)
        return (2, 4)

    # STX $4400
    # Absolute
    def fn_0x8e(self) :
        address = self.getAbsoluteAddress()
        self.emulator.memory.write_rom(address, self.X)
        return (3, 4)

    # STY $44
    # Zero Page
    def fn_0x84(self) :
        address = self.getZeroPageAddress()
        self.emulator.memory.write_rom(address, self.Y)
        return (2, 3)

    # STY $44, X
    # Zero Page, X
    def fn_0x94(self) :
        address = self.getZeroPageXAddress()
        self.emulator.memory.write_rom(address, self.Y)
        return (2, 4)

    # STY $4400
    # Absolute
    def fn_0x8c(self) :
        address = self.getAbsoluteAddress()
        self.emulator.memory.write_rom(address, self.Y)
        return (3, 4)

    # LAX $44
    # Zero Page
    def fn_0xa7(self) :
        self.A = self.getZeroPageValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (2, 3)

    # LAX $44, Y
    # Zero Page, Y
    def fn_0xb7(self) :
        self.A = self.getZeroPageYValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (2, 4)

    # LAX $4400
    # Absolute
    def fn_0xaf(self) :
        self.A = self.getAbsoluteValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (3, 4)

    # LAX $4400, Y
    # Absolute, Y
    def fn_0xbf(self) :
        self.A = self.getAbsoluteYValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (3, 4)

    # LAX ($44, X)
    # Indirect, X
    def fn_0xa3(self) :
        self.A = self.getIndirectXValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (2, 6)

    # LAX ($44), Y
    # Indirect, Y
    def fn_0xb3(self) :
        self.A = self.getIndirectYValue()
        self.X = self.A
        self.setFlagNZ(self.A)
        return (2, 5)

    #SAX $44
    # Zero Page
    def fn_0x87(self) :
        val = self.A & self.X
        self.setZeroPage(val)
        return (2, 3)

    #SAX $ 44, Y
    # Zero Page, Y
    def fn_0x97(self) :
        val = self.A & self.X
        self.setZeroPageY(val)
        return (2, 4)

    #SAX $4400
    # Absolute
    def fn_0x8f(self) :
        val = self.A & self.X
        self.setAbsolute(val)
        return (3, 4)

    #SAX
    # Indirect, X
    def fn_0x83(self) :
        val = self.A & self.X
        self.setIndirectX(val)
        return (2, 6)


    def print_status(self) :
        '''Print CPU Status'''
        print("CPU")
        print("Registers:")
        print("A\t| X\t| Y\t| SP\t| PC")
        print(f"0x{self.A:02x}\t| 0x{self.X:02x}\t| 0x{self.Y:02x}\t| 0x{self.SP:02x}\t| 0x{format_hex_data(self.PC)}")
        print("")
        print("Flags")
        print("NVxBDIZC")
        print(f"{self.getP():08b}")
        print("")

    def print_status_summary(self) :
        opcode = self.emulator.memory.read_rom(self.PC)
        label = OPCODES[opcode][1]
        l = re.search(r'[0-9]+', label)
        if l:
            if len(l.group(0)) == 2:
                val = self.getImmediate()
                label = label.replace(l.group(0), f"{val:x}")
            else:
                val = self.getAbsoluteAddress()
                label = label.replace(l.group(0), f"{format_hex_data(val)}")
        print(f"Counter : {self.compteur:8}, SP : 0x{self.SP:02x}, PC : {format_hex_data(self.PC)} - fn_0x{opcode:02x} - {label:14}, A = {self.A:2x}, X = {self.X:2x}, Y = {self.Y:2x}, Flags NVxBDIZC : {self.getP():08b}")
