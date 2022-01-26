'''Emulator CPU Modules'''
from singleton_decorator import singleton

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
import instances
from utils import format_hex_data

class Cpu:

    def __init__(self):
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
        self.negative = 0
        self.overflow = 0
        self.flagB = 0
        self.decimal = 0
        self.interrupt = 1
        self.zero = 0
        self.carry = 0

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
            self.PC = instances.memory.read_rom_16(0xfffc)
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

        self.interrupt = 0

        self.PC = instances.memory.read_rom_16(address)
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

        opcode = instances.memory.read_rom(self.PC)
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
        status["PPU_LINE"] = instances.ppu.line
        status["PPU_COL"] = instances.ppu.col
        return status

    def getP(self):
        '''Returns the P register which contains the flag status.

        Bit 5 is always set to 1
        '''
        return (self.negative << 7) | (self.overflow << 6) | (1 << 5) | (self.flagB << 4) | (self.decimal << 3) | (self.interrupt << 2) | (self.zero << 1) | self.carry

    def setP(self, p):
        '''Set the P register which contains the flag status.

        When setting the P Register, the break flag is not set.
        '''
        self.carry = p & 1
        self.zero = (p >> 1) & 1
        self.interrupt = (p >> 2) & 1
        self.decimal = (p >> 3) & 1
        #self.flagB = (p >> 4) & 1
        self.overflow = (p >> 6) & 1
        self.negative = (p >> 7) & 1

    def push(self, val):
        '''Push value into stack'''
        instances.memory.write_rom(0x0100 | self.SP, val)
        self.SP = 255 if self.SP == 0 else self.SP - 1

    def pop(self):
        '''Pop value from stack'''
        self.SP = 0 if self.SP == 255 else self.SP + 1
        return instances.memory.read_rom(0x0100 | self.SP)

    def getImmediate(self):
        '''Get 8 bit immediate value on PC + 1'''
        return instances.memory.read_rom(self.PC+1)

    def setZeroPage(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument'''
        instances.memory.write_rom(self.getZeroPageAddress(), val)

    def getZeroPageAddress(self):
        '''Get ZeroPage address to be used for current opcode. Alias to get_immediate'''
        return self.getImmediate()

    def getZeroPageValue(self):
        '''Get val from Zero Page memory. Address is given as opcode 1-byte argument'''
        address= self.getImmediate()
        return instances.memory.read_rom(address)

    def setZeroPageX(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument and X register'''
        instances.memory.write_rom(self.getZeroPageXAddress(), val)

    def getZeroPageXAddress(self):
        '''Get ZeroPage address to be used for current opcode and X register'''
        return (instances.memory.read_rom(self.PC+1) + self.X) & 255

    def getZeroPageXValue(self):
        '''Get value at ZeroPage address to be used for current opcode and X register'''
        address = self.getZeroPageXAddress()
        return instances.memory.read_rom(address)

    def setZeroPageY(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument and Y register'''
        instances.memory.write_rom(self.getZeroPageYAddress(), val)

    def getZeroPageYAddress(self):
        '''Get ZeroPage address to be used for current opcode and Y register'''
        return  (instances.memory.read_rom(self.PC+1) + self.Y) & 255

    def getZeroPageYValue(self):
        '''Get value at ZeroPage address to be used for current opcode and Y register'''
        address = self.getZeroPageYAddress()
        return instances.memory.read_rom(address)

    def setAbsolute(self, val):
        '''Write val into memory. Address is given as opcode 2-byte argument'''
        instances.memory.write_rom(self.getAbsoluteAddress(), val)

    def getAbsoluteAddress(self):
        '''Get address given as opcode 2-byte argument'''
        return instances.memory.read_rom_16(self.PC+1)

    def getAbsoluteValue(self):
        '''Get val from memory. Address is given as opcode 2-byte argument'''
        address = self.getAbsoluteAddress()
        return instances.memory.read_rom(address)

    def setAbsoluteX(self, val):
        '''Write val into memory. Address is given as opcode 2-byte argument and X register'''
        instances.memory.write_rom(self.getAbsoluteXAddress(), val)

    def getAbsoluteXAddress(self):
        '''Get address given as opcode 2-byte argument and X register'''
        address = instances.memory.read_rom_16(self.PC+1)
        target_address = (address + self.X) & 0xFFFF
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getAbsoluteXValue(self):
        '''Get val from memory. Address is given as opcode 2-byte argument and X register'''
        address = self.getAbsoluteXAddress()
        return instances.memory.read_rom(address)

    def setAbsoluteY(self, val):
        '''Write val into memory. Address is given as opcode 2-byte argument and Y register'''
        instances.memory.write_rom(self.getAbsoluteYAddress(), val)

    def getAbsoluteYAddress(self):
        '''Get address given as opcode 2-byte argument and Y register'''
        address = instances.memory.read_rom_16(self.PC+1)
        target_address = (address + self.Y) & 0xFFFF
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getAbsoluteYValue(self):
        '''Get val from memory. Address is given as opcode 2-byte argument and Y register'''
        address = self.getAbsoluteYAddress()
        return instances.memory.read_rom(address)

    def getIndirectXAddress(self):
        address = self.getZeroPageXAddress()
        return instances.memory.read_rom_16_no_crossing_page(address)

    def getIndirectXValue(self):
        address = self.getIndirectXAddress()
        return instances.memory.read_rom(address)

    def setIndirectX(self, val):
        instances.memory.write_rom(self.getIndirectXAddress(), val)

    def getIndirectYAddress(self):
        address = self.getZeroPageAddress()
        target_address = 0xFFFF & (instances.memory.read_rom_16_no_crossing_page(address )+ self.Y)
        if  address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def getIndirectYValue(self):
        address = self.getIndirectYAddress()
        return instances.memory.read_rom(address)

    def setIndirectY(self, val):
        instances.memory.write_rom(self.getIndirectYAddress(), val)

    def set_flags_nz(self, val):
        '''Sets flags N and Z according to value'''
        self.setnegative(val)
        self.setzero(val)

    def setnegative(self, val):
        ''' Set Negative Flag according to value'''
        if val < 0:
            self.negative = 1
        else:
            self.negative = val >> 7

    def setzero(self, val):
        ''' Set Zero Flag according to value'''
        self.zero = 1 if val == 0 else 0

    def adc(self, val):
        '''Perform ADC operation for val'''
        adc = val + self.A + self.carry
        self.carry = adc >> 8
        result = 255 & adc

        self.overflow = not not ((self.A ^ result) & (val ^ result) & 0x80)

        self.A = result

        self.set_flags_nz(self.A)

    def fn_0x69(self) :
        '''Function call for ADC #$xx. Immediate'''
        self.adc(self.getImmediate())
        return (2, 2)

    def fn_0x65(self) :
        '''Function call for ADC $xx. Zero Page'''
        self.adc(self.getZeroPageValue())
        return (2, 3)

    def fn_0x75(self) :
        '''Function call for ADC $xx, X. Zero Page, X'''
        self.adc(self.getZeroPageXValue())
        return (2, 4)

    def fn_0x6d(self) :
        '''Function call for ADC $xxxx. Absolute'''
        self.adc(self.getAbsoluteValue())
        return (3, 4)

    def fn_0x7d(self) :
        '''Function call for ADC $xxxx, X. Absolute, X'''
        self.adc(self.getAbsoluteXValue())
        return (3, 4)

    def fn_0x79(self) :
        '''Function call for ADC $xxxx, Y. Absolute, Y'''
        self.adc(self.getAbsoluteYValue())
        return (3, 4)

    def fn_0x61(self) :
        '''Function call for ADC ($xx, X). Indirect, X'''
        self.adc(self.getIndirectXValue())
        return (2, 6)

    def fn_0x71(self) :
        '''Function call for ADC ($xx), Y. Indirect, Y'''
        self.adc(self.getIndirectYValue())
        return (2, 5)

    def fn_0x29(self) :
        '''Function call for AND #$xx. Immediate'''
        self.A &= self.getImmediate()
        self.set_flags_nz(self.A)
        return (2, 2)

    def fn_0x25(self) :
        '''Function call for AND $xx. Zero Page'''
        self.A &= self.getZeroPageValue()
        self.set_flags_nz(self.A)
        return (2, 3)

    def fn_0x35(self) :
        '''Function call for AND $xx, X. Zero Page, X'''
        self.A &= self.getZeroPageXValue()
        self.set_flags_nz(self.A)
        return (2, 4)

    def fn_0x2d(self) :
        '''Function call for AND $xxxx. Absolute'''
        self.A &= self.getAbsoluteValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x3d(self) :
        '''Function call for AND $xxxx, X. Absolute, X'''
        self.A &= self.getAbsoluteXValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x39(self) :
        '''Function call for AND $xxxx, Y. Absolute, Y'''
        self.A &= self.getAbsoluteYValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x21(self) :
        '''Function call for AND ($xx, X). Indirect, X'''
        self.A &= self.getIndirectXValue()
        self.set_flags_nz(self.A)
        return (2, 6)

    def fn_0x31(self) :
        '''Function call for AND ($xx), Y. Indirect, Y'''
        self.A &= self.getIndirectYValue()
        self.set_flags_nz(self.A)
        return (2, 5)

    def fn_0x0a(self) :
        '''Function call for ASL. Accumulator'''
        self.carry = self.A >> 7
        self.A = (self.A << 1) & 0b11111111
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0x06(self) :
        '''Function call for ASL $xx. Zero Page'''
        value = self.getZeroPageValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setZeroPage(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0x16(self) :
        '''Function call for ASL $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setZeroPageX(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0x0e(self) :
        '''Function call for ASL $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0x1e(self) :
        '''Function call for ASL $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsoluteX(value)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0x24(self) :
        '''Function call for BIT $xx. Zero Page'''
        tocomp = self.getZeroPageValue()
        value = tocomp & self.A
        self.setzero(value)
        self.negative = (tocomp >> 7) & 1
        self.overflow = (tocomp >> 6) & 1
        return (2, 3)

    def fn_0x2c(self) :
        '''Function call for BIT $xxxx. Absolute'''
        tocomp = self.getAbsoluteValue()
        value = tocomp & self.A
        self.setzero(value)
        self.negative = (tocomp >> 7) & 1
        self.overflow = (tocomp >> 6) & 1
        return (3, 4)

    def fn_0x10(self) :
        '''Function call for BPL #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.negative == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle += 1
        return (2, 2)

    def fn_0x30(self) :
        '''Function call for BMI #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.negative == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BVC
    # Relative
    def fn_0x50(self) :
        '''Function call for BVC #$xx. Relative'''
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.overflow == 0:
            self.PC += signed
            self.additional_cycle += 1
        return (2, 2)

    def fn_0x70(self) :
        '''Function call for BVS #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.overflow == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0x90(self) :
        '''Function call for BCC #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.carry == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0xb0(self) :
        '''Function call for BCS #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.carry == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

        '''Function call for BNE #$xx. Relative'''
    def fn_0xd0(self) :
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.zero == 0:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0xf0(self) :
        '''Function call for BEQ #$xx. Relative'''
        old_pc = self.PC + 2
        unsigned = self.getImmediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.zero == 1:
            self.PC += signed
            self.additional_cycle += 1
            if self.PC & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0x00(self) :
        '''Function call for BRK. Implied
        TODO ! Should set Break flag to 1
        '''
        self.PC += 1
        self.push(self.PC >> 8)
        self.push(self.PC & 255)
        self.push(self.getP())
        self.PC = instances.memory.read_rom_16(0xFFFE)
        return (0, 7)

    def cmp(self, op1, op2) :
        '''General implementation for CMP operation

        Args:
            op1 -- First operand
            op2 -- First operand
        '''
        if op1 > op2:
            if op1-op2 >= 0x80:
                self.carry = 1
                self.negative = 1
                self.zero = 0
            else:
                self.carry = 1
                self.negative = 0
                self.zero = 0
        elif op1 == op2:
            self.carry = 1
            self.negative = 0
            self.zero = 1
        else:
            if op2 - op1 >= 0x80:
                self.carry = 0
                self.negative = 0
                self.zero = 0
            else:
                self.carry = 0
                self.negative = 1
                self.zero = 0

    def fn_0xc9(self) :
        '''Function call for CMP #$xx. Immediate'''
        self.cmp(self.A, self.getImmediate())
        return (2, 2)

    def fn_0xc5(self) :
        '''Function call for CMP $xx. Zero Page'''
        self.cmp(self.A, self.getZeroPageValue())
        return (2, 3)

    def fn_0xd5(self) :
        '''Function call for CMP $xx, X. Zero Page, X'''
        self.cmp(self.A, self.getZeroPageXValue())
        return (2, 4)

    def fn_0xcd(self) :
        '''Function call for CMP $xxxx. Absolute'''
        self.cmp(self.A, self.getAbsoluteValue())
        return (3, 4)

    def fn_0xdd(self) :
        '''Function call for CMP $xxxx, X. Absolute, X'''
        self.cmp(self.A, self.getAbsoluteXValue())
        return (3, 4)

    def fn_0xd9(self) :
        '''Function call for CMP $xxxx, Y. Absolute, Y'''
        self.cmp(self.A, self.getAbsoluteYValue())
        return (3, 4)

    def fn_0xc1(self) :
        '''Function call for CMP ($xx, X). Indirect, X'''
        self.cmp(self.A, self.getIndirectXValue())
        return (2, 6)

    def fn_0xd1(self) :
        '''Function call for CMP ($xx), Y. Indirect, Y'''
        self.cmp(self.A, self.getIndirectYValue())
        return (2, 5)

    def fn_0xe0(self) :
        '''Function call for CPX #$xx. Immediate'''
        self.cmp(self.X, self.getImmediate())
        return (2, 2)

    def fn_0xe4(self) :
        '''Function call for CPX $xx. Zero Page'''
        self.cmp(self.X, self.getZeroPageValue())
        return (2, 3)

    def fn_0xec(self) :
        '''Function call for CPX $xxxx. Absolute'''
        self.cmp(self.X, self.getAbsoluteValue())
        return (3, 4)

    def fn_0xc0(self) :
        '''Function call for CPY #$xx. Immediate'''
        self.cmp(self.Y, self.getImmediate())
        return (2, 2)

    def fn_0xc4(self) :
        '''Function call for CPY $xx. Zero Page'''
        self.cmp(self.Y, self.getZeroPageValue())
        return (2, 3)

    def fn_0xcc(self) :
        '''Function call for CPY $xxxx. Absolute'''
        self.cmp(self.Y, self.getAbsoluteValue())
        return (3, 4)

    def fn_0xc6(self) :
        '''Function call for DEC $xx. Zero Page'''
        value = self.getZeroPageValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPage(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0xd6(self) :
        '''Function call for DEC $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPageX(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0xce(self) :
        '''Function call for DEC $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        value = 255 if value == 0 else value - 1
        self.setAbsolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0xde(self) :
        '''Function call for CPY $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteX(value)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0xc7(self):
        '''Function call for DCP $xx. Zero Page'''
        value = self.getZeroPageValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPage(value)
        self.cmp(self.A, value)
        return (2, 5)

    def fn_0xd7(self):
        '''Function call for DCP $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        value = 255 if value == 0 else value - 1
        self.setZeroPageX(value)
        self.cmp(self.A, value)
        return (2, 6)

    def fn_0xcf(self):
        '''Function call for DCP $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        value = 255 if value == 0 else value - 1
        self.setAbsolute(value)
        self.cmp(self.A, value)
        return (3, 6)

    def fn_0xdf(self):
        '''Function call for DCP $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteX(value)
        self.cmp(self.A, value)
        return (3, 7)

    def fn_0xdb(self):
        '''Function call for CPY $xxxx, Y. Absolute, Y'''
        value = self.getAbsoluteYValue()
        value = 255 if value == 0 else value - 1
        self.setAbsoluteY(value)
        self.cmp(self.A, value)
        return (3, 7)

    def fn_0xc3(self):
        '''Function call for DCP ($xx, X). Indirect, X'''
        value = self.getIndirectXValue()
        value = 255 if value == 0 else value - 1
        self.setIndirectX(value)
        self.cmp(self.A, value)
        return (2, 8)

    def fn_0xd3(self):
        '''Function call for DCP ($xx), Y. Indirect, Y'''
        value = self.getIndirectYValue()
        value = 255 if value == 0 else value - 1
        self.setIndirectY(value)
        self.cmp(self.A, value)
        return (2, 8)

    def fn_0xe7(self):
        '''Function call for ISC $xx. Zero Page'''
        value = self.getZeroPageValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPage(value)
        self.sbc(value)
        return (2, 5)

    def fn_0xf7(self):
        '''Function call for ESC $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPageX(value)
        self.sbc(value)
        return (2, 6)

    def fn_0xef(self):
        '''Function call for ISC $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        value = 0 if value == 255 else value + 1
        self.setAbsolute(value)
        self.sbc(value)
        return (3, 6)

    def fn_0xff(self):
        '''Function call for ISC $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteX(value)
        self.sbc(value)
        return (3, 7)

    def fn_0xfb(self):
        '''Function call for ISC $xxxx, Y. Absolute, Y'''
        value = self.getAbsoluteYValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteY(value)
        self.sbc(value)
        return (3, 7)

    def fn_0xe3(self):
        '''Function call for ISC ($xx), X. Indirect, X'''
        value = self.getIndirectXValue()
        value = 0 if value == 255 else value + 1
        self.setIndirectX(value)
        self.sbc(value)
        return (2, 8)

    def fn_0xf3(self):
        '''Function call for ISC ($xx, Y). Indirect, Y'''
        value = self.getIndirectYValue()
        value = 0 if value == 255 else value + 1
        self.setIndirectY(value)
        self.sbc(value)
        return (2, 4)

    def fn_0x49(self) :
        '''Function call for EOR #$xx. Immediate'''
        self.A ^= self.getImmediate()
        self.set_flags_nz(self.A)
        return (2, 2)

    def fn_0x45(self) :
        '''Function call for EOR $xx. Zero Page'''
        self.A ^= self.getZeroPageValue()
        self.set_flags_nz(self.A)
        return (2, 3)

    def fn_0x55(self) :
        '''Function call for EOR $xx, X. Zero Page, X'''
        self.A ^= self.getZeroPageXValue()
        self.set_flags_nz(self.A)
        return (2, 4)

    def fn_0x4d(self) :
        '''Function call for EOR $xxxx. Absolute'''
        self.A ^= self.getAbsoluteValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x5d(self) :
        '''Function call for EOR $xxxx, X. Absolute, X'''
        self.A ^= self.getAbsoluteXValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x59(self) :
        '''Function call for EOR $xxxx, Y. Absolute, Y'''
        self.A ^= self.getAbsoluteYValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x41(self) :
        '''Function call for EOR ($xx, X). Indirect, X'''
        self.A ^= self.getIndirectXValue()
        self.set_flags_nz(self.A)
        return (2, 6)

    def fn_0x51(self) :
        '''Function call for EOR ($xx), Y. Indirect, Y'''
        self.A ^= self.getIndirectYValue()
        self.set_flags_nz(self.A)
        return (2, 5)

    def fn_0x18(self) :
        '''Function call for CLC. Implied

        Clear carry flag
        '''
        self.carry = 0
        return (1, 2)

    def fn_0x38(self) :
        '''Function call for SEC. Implied

        Set carry flag
        '''
        self.carry = 1
        return (1, 2)

    def fn_0x58(self) :
        '''Function call for CLI. Implied

        Clear interrupt flag
        '''
        self.interrupt = 0
        return (1, 2)

    def fn_0x78(self) :
        '''Function call for SEI. Implied

        Set interrupt flag
        '''
        self.interrupt = 1
        return (1, 2)

    def fn_0xb8(self) :
        '''Function call for CLV. Implied

        Clear overflow flag
        '''
        self.overflow = 0
        return (1, 2)

    def fn_0xd8(self) :
        '''Function call for CLD. Implied

        Clear decimal flag
        '''
        self.decimal = 0
        return (1, 2)

    def fn_0xf8(self) :
        '''Function call for SED. Implied

        Set decimal flag
        '''
        self.decimal = 1
        return (1, 2)

    def fn_0xe6(self) :
        '''Function call for INC $xx. Zero Page'''
        value = self.getZeroPageValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPage(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0xf6(self) :
        '''Function call for INC $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        value = 0 if value == 255 else value + 1
        self.setZeroPageX(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0xee(self) :
        '''Function call for INC $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        value = 0 if value == 255 else value + 1
        self.setAbsolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0xfe(self) :
        '''Function call for INC $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        value = 0 if value == 255 else value + 1
        self.setAbsoluteX(value)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0x4c(self) :
        '''Function call for JMP $xxxx. Absolute'''
        self.PC = self.getAbsoluteAddress()
        return (0, 3)

    def fn_0x6c(self) :
        '''Function call for JMP ($xxxx). Indirect'''
        address = self.getAbsoluteAddress()
        if address & 0xFF == 0xFF: # Strange behaviour in nestest.nes where direct jump to re-aligned address where address at end of page
            address += 1
            if self.debug :  print(f"JMP address : {address:4x}")
        else:
            address = instances.memory.read_rom_16(address)
        if self.debug : print(f"JMP address : {address:4x}")
        self.PC = address
        return (0, 5)

    def fn_0x20(self) :
        '''Function call for JSR $xxxx. Absolute'''
        pc = self.PC + 2
        high = pc >> 8
        low =  pc & 255
        self.push(high) # little endian
        self.push(low)
        self.PC = self.getAbsoluteAddress()
        return (0, 6)

    def fn_0xa9(self) :
        '''Function call for LDA #$xx. Immediate'''
        self.A = self.getImmediate()
        self.set_flags_nz(self.A)
        return (2, 2)

    def fn_0xa5(self) :
        '''Function call for LDA $xx. Zero Page'''
        self.A =self.getZeroPageValue()
        self.set_flags_nz(self.A)
        return (2, 3)

    def fn_0xb5(self) :
        '''Function call for LDA $xx, X. Zero Page, X'''
        self.A = self.getZeroPageXValue()
        self.set_flags_nz(self.A)
        return (2, 4)

    def fn_0xad(self) :
        '''Function call for LDA $xxxx. Absolute'''
        self.A = self.getAbsoluteValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0xbd(self) :
        '''Function call for LDA $xxxx, X. Absolute, X'''
        self.A = self.getAbsoluteXValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0xb9(self) :
        '''Function call for LDA $xxxx, Y. Absolute, Y'''
        self.A = self.getAbsoluteYValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0xa1(self) :
        '''Function call for LDA ($xx, X). Indirect, X'''
        self.A = self.getIndirectXValue()
        self.set_flags_nz(self.A)
        return (2, 6)

    def fn_0xb1(self) :
        '''Function call for EOR ($xx), Y. Indirect, Y'''
        self.A = self.getIndirectYValue()
        self.set_flags_nz(self.A)
        return (2, 5)

    def fn_0xa2(self) :
        '''Function call for LDX #$xx. Immediate'''
        self.X = self.getImmediate()
        self.set_flags_nz(self.X)
        return (2, 2)

    def fn_0xa6(self) :
        '''Function call for LDX $xx. Zero Page'''
        self.X = self.getZeroPageValue()
        self.set_flags_nz(self.X)
        return (2, 3)

    def fn_0xb6(self) :
        '''Function call for LDX $xx, Y. Zero Page, Y'''
        self.X = self.getZeroPageYValue()
        self.set_flags_nz(self.X)
        return (2, 4)

    def fn_0xae(self) :
        '''Function call for LDX $xxxx. Absolute'''
        self.X = self.getAbsoluteValue()
        self.set_flags_nz(self.X)
        return (3, 4)

    def fn_0xbe(self) :
        '''Function call for LDX $xxxx, Y. Absolute, Y'''
        self.X = self.getAbsoluteYValue()
        self.set_flags_nz(self.X)
        return (3, 4)

    def fn_0xa0(self) :
        '''Function call for LDY #$xx. Immediate'''
        self.Y = self.getImmediate()
        self.set_flags_nz(self.Y)
        return (2, 2)

    def fn_0xa4(self) :
        '''Function call for LDY $xx. Zero Page'''
        self.Y = self.getZeroPageValue()
        self.set_flags_nz(self.X)
        return (2, 3)

    def fn_0xb4(self) :
        '''Function call for LDY $xx, X. Zero Page, X'''
        self.Y = self.getZeroPageXValue()
        self.set_flags_nz(self.Y)
        return (2, 4)

    def fn_0xac(self) :
        '''Function call for LDY $xxxx. Absolute'''
        self.Y =self.getAbsoluteValue()
        self.set_flags_nz(self.Y)
        return (3, 4)

    def fn_0xbc(self) :
        '''Function call for LDY $xxxx, X. Absolute, X'''
        self.Y = self.getAbsoluteXValue()
        self.set_flags_nz(self.Y)
        return (3, 4)

    def fn_0x4a(self) :
        '''Function call for LSR. Accumulator'''
        self.carry = self.A & 1
        self.A = self.A >> 1
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0x46(self) :
        '''Function call for LSR $xx. Zero Page'''
        value = self.getZeroPageValue()
        self.carry = value & 1
        value = value >> 1
        self.setZeroPage(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0x56(self) :
        '''Function call for LSR $xx, X. Zero Page, X'''
        value = self.getZeroPageXValue()
        self.carry = value & 1
        value = value >> 1
        self.setZeroPageX(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0x4e(self) :
        '''Function call for LSR $xxxx. Absolute'''
        value = self.getAbsoluteValue()
        self.carry = value & 1
        value = value >> 1
        self.setAbsolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0x5e(self) :
        '''Function call for LSR $xxxx, X. Absolute, X'''
        value = self.getAbsoluteXValue()
        self.carry = value & 1
        value = value >> 1
        self.setAbsoluteX(value)
        self.set_flags_nz(value)
        return (3, 7)

    # Disabling no-self-use pylint control
    # pylint: disable=R0201
    def fn_0xea(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0x1a(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0x3a(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0x5a(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0x7a(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0xda(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)
    def fn_0xfa(self) :
        '''Function call for NOP. Implied'''
        return (1, 2)

    def fn_0x04(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 3)
    def fn_0x14(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)
    def fn_0x34(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)
    def fn_0x44(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 3)
    def fn_0x54(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)
    def fn_0x64(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 3)
    def fn_0x74(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)
    def fn_0x80(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 2)
    def fn_0x82(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 2)
    def fn_0x89(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 2)
    def fn_0xc2(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 2)
    def fn_0xd4(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)
    def fn_0xe2(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 2)
    def fn_0xf4(self) :
        '''Function call for DOP. Implied

        Equivalent to NOP NOP (2-byte NOP)
        '''
        return (2, 4)

    def fn_0x0c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0x1c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0x3c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0x5c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0x7c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0xdc(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    def fn_0xfc(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        return (3, 4)
    # Restoring no-self-use pylint control
    # pylint: enable=R0201

    def fn_0x09(self) :
        '''Function call for ORA #$xx. Immediate'''
        self.A |= self.getImmediate()
        self.set_flags_nz(self.A)
        return (2, 2)

    def fn_0x05(self) :
        '''Function call for ORA $xx. Zero Page'''
        self.A |= self.getZeroPageValue()
        self.set_flags_nz(self.A)
        return (2, 3)

    def fn_0x15(self) :
        '''Function call for ORA $xx, X. Zero Page, X'''
        self.A |= self.getZeroPageXValue()
        self.set_flags_nz(self.A)
        return (2, 4)

    def fn_0x0d(self) :
        '''Function call for ORA $xxxx. Absolute'''
        self.A |= self.getAbsoluteValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x1d(self) :
        '''Function call for ORA $xxxx, X. Absolute, X'''
        self.A |= self.getAbsoluteXValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x19(self) :
        '''Function call for ORA $xxxx, Y. Absolute, Y'''
        self.A |= self.getAbsoluteYValue()
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0x01(self) :
        '''Function call for ORA ($xx, X). Indirect, X'''
        self.A |= self.getIndirectXValue()
        self.set_flags_nz(self.A)
        return (2, 6)

    def fn_0x11(self) :
        '''Function call for ORA ($xx), Y. Indirect, Y'''
        self.A |= self.getIndirectYValue()
        self.set_flags_nz(self.A)
        return (2, 5)

    def fn_0x07(self):
        '''Function call for SLO $xx. Zero Page

        Equivalent to:
            ASL
            ORA
        '''
        self.fn_0x06() # ASL
        self.fn_0x05() # ORA
        return (2, 5)

    def fn_0x17(self):
        '''Function call for SLO $xx, X. Zero Page, X

        Equivalent to:
            ASL
            ORA
        '''
        self.fn_0x16() # ASL
        self.fn_0x15() # ORA
        return (2, 6)

    def fn_0x0f(self):
        '''Function call for SLO $xxxx. Absolute

        Equivalent to:
            ASL
            ORA
        '''
        self.fn_0x0e() # ASL
        self.fn_0x0d() # ORA
        return (3, 6)

    def fn_0x1f(self):
        '''Function call for SLO $xxxx, X. Absolute, X

        Equivalent to:
            ASL
            ORA
        '''
        self.fn_0x1e() # ASL
        self.fn_0x1d() # ORA
        return (3, 7)

    def fn_0x1b(self):
        '''Function call for SLO $xxxx, Y. Absolute, Y

        Equivalent to:
            ASL
            ORA
        '''
        value = self.getAbsoluteYValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setAbsoluteY(value)
        self.fn_0x19() # ORA
        return (3, 7)

    def fn_0x03(self):
        '''Function call for SLO ($xx, X). Indirect, X

        Equivalent to:
            ASL
            ORA
        '''
        value = self.getIndirectXValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setIndirectX(value)
        self.fn_0x01() # ORA
        return (2, 8)

    def fn_0x13(self):
        '''Function call for SLO ($xx), Y. Indirect, Y

        Equivalent to:
            ASL
            ORA
        '''
        value = self.getIndirectYValue()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.setIndirectY(value)
        self.fn_0x11() # ORA
        return (2, 8)

    def fn_0x27(self):
        '''Function call for RLA $xx. Zero Page

        Equivalent to:
            ROL
            AND
        '''
        self.fn_0x26() # ROL
        self.fn_0x25() # AND
        return (2, 5)

    def fn_0x37(self):
        '''Function call for RLA $xx, X. Zero Page, X

        Equivalent to:
            ROL
            AND
        '''
        self.fn_0x36() # ROL
        self.fn_0x35() # AND
        return (2, 6)

    def fn_0x2f(self):
        '''Function call for RLA $xxxx. Absolute

        Equivalent to:
            ROL
            AND
        '''
        self.fn_0x2e() # ROL
        self.fn_0x2d() # AND
        return (3, 6)

    def fn_0x3f(self):
        '''Function call for RLA $xxxx, X. Absolute, X

        Equivalent to:
            ROL
            AND
        '''
        self.fn_0x3e() # ROL
        self.fn_0x3d() # AND
        return (3, 7)

    def fn_0x3b(self):
        '''Function call for RLA $xxxx, Y. Absolute, Y

        Equivalent to:
            ROL
            AND
        '''
        val = self.getAbsoluteYValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setAbsoluteY(val)
        self.fn_0x39() # AND
        return (3, 7)

    def fn_0x23(self):
        '''Function call for RLA ($xx, X). Indirect, X

        Equivalent to:
            ROL
            AND
        '''
        val = self.getIndirectXValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setIndirectX(val)
        self.fn_0x21() # AND
        return (2, 8)

    def fn_0x33(self):
        '''Function call for RLA ($xx), Y. Indirect, Y

        Equivalent to:
            ROL
            AND
        '''
        val = self.getIndirectYValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setIndirectY(val)
        self.fn_0x31() # AND
        return (2, 8)

    def fn_0x67(self):
        '''Function call for RRA $xx. Zero Page

        Equivalent to:
            ROR
            ADC
        '''
        self.fn_0x66() # ROR
        self.fn_0x65() # ADC
        return (2, 5)

    def fn_0x77(self):
        '''Function call for RRA $xx, X. Zero Page, X

        Equivalent to:
            ROR
            ADC
        '''
        self.fn_0x76() # ROR
        self.fn_0x75() # ADC
        return (2, 6)

    def fn_0x6f(self):
        '''Function call for RRA $xxxx. Absolute

        Equivalent to:
            ROR
            ADC
        '''
        self.fn_0x6e() # ROR
        self.fn_0x6d() # ADC
        return (3, 6)

    def fn_0x7f(self):
        '''Function call for RRA $xxxx, X. Absolute, X

        Equivalent to:
            ROR
            ADC
        '''
        self.fn_0x7e() # ROR
        self.fn_0x7d() # ADC
        return (3, 7)

    def fn_0x7b(self):
        '''Function call for RRA $xxxx, Y. Absolute, Y

        Equivalent to:
            ROR
            ADC
        '''
        val = self.getAbsoluteYValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setAbsoluteY(val)
        self.fn_0x79() # ADC
        return (3, 7)

    def fn_0x63(self):
        '''Function call for RRA ($xx, X). Indirect, X

        Equivalent to:
            ROR
            ADC
        '''
        val = self.getIndirectXValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setIndirectX(val)
        self.fn_0x61() # ADC
        return (2, 8)

    # RRA ($44, Y)
    # Indirect, Y
    def fn_0x73(self):
        '''Function call for RRA ($xx), Y. Indirect, Y

        Equivalent to:
            ROR
            ADC
        '''
        val = self.getIndirectYValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setIndirectY(val)
        self.fn_0x71() # ADC
        return (2, 8)

    def fn_0x47(self):
        '''Function call for SRE $xx. Zero Page

        Equivalent to:
            LSR
            EOR
        '''
        self.fn_0x46() # LSR
        self.fn_0x45() # EOR
        return (2, 5)

    def fn_0x57(self):
        '''Function call for SRE $xx, X. Zero Page, X

        Equivalent to:
            LSR
            EOR
        '''
        self.fn_0x56() # LSR
        self.fn_0x55() # EOR
        return (2, 6)

    def fn_0x4f(self):
        '''Function call for SRE $xxxx. Absolute

        Equivalent to:
            LSR
            EOR
        '''
        self.fn_0x4e() # LSR
        self.fn_0x4d() # EOR
        return (3, 6)

    def fn_0x5f(self):
        '''Function call for SRE $xxxx, X. Absolute, X

        Equivalent to:
            LSR
            EOR
        '''
        self.fn_0x5e() # LSR
        self.fn_0x5d() # EOR
        return (3, 7)

    def fn_0x5b(self):
        '''Function call for SRE $xxxx, Y. Absolute, Y

        Equivalent to:
            LSR
            EOR
        '''
        val = self.getAbsoluteYValue()
        self.carry = val & 1
        val = val >> 1
        self.setAbsoluteY(val)
        self.fn_0x59() # EOR
        return (3, 7)

    def fn_0x43(self):
        '''Function call for SRE ($xx, X). Indirect, X

        Equivalent to:
            LSR
            EOR
        '''
        val = self.getIndirectXValue()
        self.carry = val & 1
        val = val >> 1
        self.setIndirectX(val)
        self.fn_0x41() # EOR
        return (2, 8)

    def fn_0x53(self):
        '''Function call for SRE ($xx), Y. Indirect, Y

        Equivalent to:
            LSR
            EOR
        '''
        val = self.getIndirectYValue()
        self.carry = val & 1
        val = val >> 1
        self.setIndirectY(val)
        self.fn_0x51() # EOR
        return (2, 8)

    def fn_0xaa(self) :
        '''Function call for TAX. Implied'''
        self.X = self.A
        self.set_flags_nz(self.X)
        return (1, 2)

    def fn_0x8a(self) :
        '''Function call for TXA. Implied'''
        self.A = self.X
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0xca(self) :
        '''Function call for DEX. Implied'''
        self.X = self.X - 1 if self.X > 0 else 255
        self.set_flags_nz(self.X)
        return (1, 2)

    def fn_0xe8(self) :
        '''Function call for INX. Implied'''
        self.X = self.X + 1 if self.X < 255 else 0
        self.set_flags_nz(self.X)
        return (1, 2)

    def fn_0xa8(self) :
        '''Function call for TAY. Implied'''
        self.Y = self.A
        self.set_flags_nz(self.Y)
        return (1, 2)

    def fn_0x98(self) :
        '''Function call for TYA. Implied'''
        self.A = self.Y
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0x88(self) :
        '''Function call for DEY. Implied'''
        self.Y = self.Y - 1 if self.Y > 0 else 255
        self.set_flags_nz(self.Y)
        return (1, 2)

    def fn_0xc8(self) :
        '''Function call for INY. Implied'''
        self.Y = self.Y + 1 if self.Y < 255 else 0
        self.set_flags_nz(self.Y)
        return (1, 2)

    def fn_0x2a(self) :
        '''Function call for ROL A. Accumulator'''
        self.A = (self.A << 1) | (self.carry)
        self.carry = self.A >> 8
        self.A &= 255
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0x26(self) :
        '''Function call for ROL $xx. Zero Page'''
        val = self.getZeroPageValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setZeroPage(val)
        self.set_flags_nz(val)
        return (2, 5)

    def fn_0x36(self) :
        '''Function call for ROL $xx, X. Zero Page, X'''
        val = self.getZeroPageXValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setZeroPageX(val)
        self.set_flags_nz(val)
        return (2, 6)

    def fn_0x2e(self) :
        '''Function call for ROL $xxxx. Absolute'''
        val = self.getAbsoluteValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setAbsolute(val)
        self.set_flags_nz(val)
        return (3, 6)

    def fn_0x3e(self) :
        '''Function call for ROL $xxxx, X. Absolute, X'''
        val = self.getAbsoluteXValue()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.setAbsoluteX(val)
        self.set_flags_nz(val)
        return (3, 7)

    def fn_0x6a(self) :
        '''Function call for ROR A. Accumulator'''
        carry = self.A & 1
        self.A = (self.A >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_flags_nz(self.A)
        return (1, 2)

    def fn_0x66(self) :
        '''Function call for ROR $xx. Zero Page'''
        val = self.getZeroPageValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setZeroPage(val)
        self.set_flags_nz(val)
        return (2, 5)

    def fn_0x76(self) :
        '''Function call for ROR $xx, X. Zero Page, X'''
        val = self.getZeroPageXValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setZeroPageX(val)
        self.set_flags_nz(val)
        return (2, 6)

    def fn_0x6e(self) :
        '''Function call for ROR $xxxx. Absolute'''
        val = self.getAbsoluteValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setAbsolute(val)
        self.set_flags_nz(val)
        return (3, 6)

    def fn_0x7e(self) :
        '''Function call for ROR$xxxx, X. Absolute, X'''
        val = self.getAbsoluteXValue()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.setAbsoluteX(val)
        self.set_flags_nz(val)
        return (3, 7)

    def fn_0x40(self) :
        '''Function call for RTI. Implied'''
        self.setP(self.pop())
        low = self.pop()
        high = self.pop()
        self.PC = (high << 8) + low
        return (0, 6)

    def fn_0x60(self) :
        '''Function call for RTS. Implied'''
        low = self.pop()
        high = self.pop()
        self.PC = (high << 8) + low + 1 # JSR increment only by two, and RTS add the third
        return (0, 6)

    def sbc(self, val):
        '''General implementation for sbc operation

        SBC is the same as ADC with two's complement on second operand
        '''
        self.adc(255-val)

    def fn_0xe9(self) :
        '''Function call for SBC #$xx. Immediate'''
        self.sbc(self.getImmediate())
        return (2, 2)
    # 0xeb alias to 0x e9
    def fn_0xeb(self) :
        '''Function call for SBC #$xx. Immediate

        0xeb alias to 0xe9
        '''
        return self.fn_0xe9()

    def fn_0xe5(self) :
        '''Function call for SBC $xx. Zero Page'''
        self.sbc(self.getZeroPageValue())
        return (2, 3)

    def fn_0xf5(self) :
        '''Function call for SBC $xx, X. Zero Page, X'''
        self.sbc(self.getZeroPageXValue())
        return (2, 4)

    def fn_0xed(self) :
        '''Function call for SBC $xxxx. Absolute'''
        self.sbc(self.getAbsoluteValue())
        return (3, 4)

    def fn_0xfd(self) :
        '''Function call for SBC $xxxx, X. Absolute, X'''
        self.sbc(self.getAbsoluteXValue())
        return (3, 4)

    def fn_0xf9(self) :
        '''Function call for SBC $xxxx, Y. Absolute, Y'''
        self.sbc(self.getAbsoluteYValue())
        return (3, 4)

    def fn_0xe1(self) :
        '''Function call for SBC ($xx, X). Indirect, X'''
        self.sbc(self.getIndirectXValue())
        return (2, 6)

    def fn_0xf1(self) :
        '''Function call for SBC ($xx), Y. Indirect, Y'''
        self.sbc(self.getIndirectYValue())
        return (2, 5)

    def fn_0x85(self) :
        '''Function call for STA $xx. Zero Page'''
        address = self.getZeroPageAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (2, 3 + extra_cycles)

    def fn_0x95(self) :
        '''Function call for STA $xx, X. Zero Page, X'''
        address = self.getZeroPageXAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (2, 4 + extra_cycles)

    def fn_0x8d(self) :
        '''Function call for STA $xxxx. Absolute'''
        address = self.getAbsoluteAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (3, 4 + extra_cycles)

    def fn_0x9d(self) :
        '''Function call for STA $xxxx, X. Absolute, X'''
        address = self.getAbsoluteXAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (3, 5 + extra_cycles)

    def fn_0x99(self) :
        '''Function call for STA $xxxx, Y. Absolute, Y'''
        address = self.getAbsoluteYAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (3, 5 + extra_cycles)

    def fn_0x81(self) :
        '''Function call for STA ($xx, X). Indirect, X'''
        address = self.getIndirectXAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (2, 6 + extra_cycles)

    def fn_0x91(self) :
        '''Function call for STA ($xx), Y. Indirect, Y'''
        address = self.getIndirectYAddress()
        extra_cycles = instances.memory.write_rom(address, self.A)
        return (2, 6 + extra_cycles)

    def fn_0x9a(self) :
        '''Function call for TXS. Implied'''
        self.SP = self.X
        return (1, 2)

    def fn_0xba(self) :
        '''Function call for TSX. Implied'''
        self.X = self.SP
        self.set_flags_nz(self.X)
        return (1, 2)

    def fn_0x48(self) :
        '''Function call for RHA. Implied'''
        self.push(self.A)
        return (1, 3)

    def fn_0x68(self) :
        '''Function call for PLA. Implied'''
        self.A = self.pop()
        self.set_flags_nz(self.A)
        return (1, 4)

    def fn_0x08(self) :
        '''Function call for PHP. Implied'''
        # create status byte
        p = self.getP() | (1 << 4)
        self.push(p)
        return (1, 3)

    def fn_0x28(self) :
        '''Function call for PLP. Implied'''
        p = self.pop()
        self.setP(p)
        return (1, 4)

    def fn_0x86(self) :
        '''Function call for STX $xx. Zero Page'''
        address = self.getZeroPageAddress()
        instances.memory.write_rom(address, self.X)
        return (2, 3)

    def fn_0x96(self) :
        '''Function call for STX $xx, Y. Zero Page, Y'''
        address = self.getZeroPageYAddress()
        instances.memory.write_rom(address, self.X)
        return (2, 4)

    def fn_0x8e(self) :
        '''Function call for STX $xxxx. Absolute'''
        address = self.getAbsoluteAddress()
        instances.memory.write_rom(address, self.X)
        return (3, 4)

    def fn_0x84(self) :
        '''Function call for STY $xx. Zero Page'''
        address = self.getZeroPageAddress()
        instances.memory.write_rom(address, self.Y)
        return (2, 3)

    def fn_0x94(self) :
        '''Function call for STY $xx, X. Zero Page, X'''
        address = self.getZeroPageXAddress()
        instances.memory.write_rom(address, self.Y)
        return (2, 4)

    def fn_0x8c(self) :
        '''Function call for STY $xxxx. Absolute'''
        address = self.getAbsoluteAddress()
        instances.memory.write_rom(address, self.Y)
        return (3, 4)

    def fn_0xa7(self) :
        '''Function call for LAX $xx. Zero Page'''
        self.A = self.getZeroPageValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (2, 3)

    def fn_0xb7(self) :
        '''Function call for LAX $xx, Y. Zero Page, Y'''
        self.A = self.getZeroPageYValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (2, 4)

    def fn_0xaf(self) :
        '''Function call for LAX $xxxx. Absolute'''
        self.A = self.getAbsoluteValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0xbf(self) :
        '''Function call for LAX $xxxx, Y. Absolute, Y'''
        self.A = self.getAbsoluteYValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (3, 4)

    def fn_0xa3(self) :
        '''Function call for LAX ($xx, X). Indirect, X'''
        self.A = self.getIndirectXValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (2, 6)

    def fn_0xb3(self) :
        '''Function call for LAX ($xx), Y. Indirect, Y'''
        self.A = self.getIndirectYValue()
        self.X = self.A
        self.set_flags_nz(self.A)
        return (2, 5)

    def fn_0x87(self) :
        '''Function call for SAX $xx. Zero Page'''
        val = self.A & self.X
        self.setZeroPage(val)
        return (2, 3)

    def fn_0x97(self) :
        '''Function call for SAX $xx, Y. Zero Page, Y'''
        val = self.A & self.X
        self.setZeroPageY(val)
        return (2, 4)

    def fn_0x8f(self) :
        '''Function call for SAX $xxxx. Absolute'''
        val = self.A & self.X
        self.setAbsolute(val)
        return (3, 4)

    def fn_0x83(self) :
        '''Function call for SAX ($xx, X). Indirect, X'''
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
        '''Debug print of status'''
        opcode = instances.memory.read_rom(self.PC)
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
