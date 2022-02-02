'''Emulator CPU Modules'''
import sys
import re
import instances
from utils import format_hex_data
from cpu_opcodes import OPCODES

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

# Addressing modes : http://www.emulator101.com/6502-addressing-modes.html
# Opcodes : http://www.6502.org/tutorials/6502opcodes.html

# https://www.atarimagazines.com/compute/issue53/047_1_All_About_The_Status_Register.php

# https://www.masswerk.at/6502/6502_instruction_set.html

# https://www.gladir.com/CODER/ASM6502/referenceopcode.htm

class Cpu:
    '''CPU component'''
    def __init__(self):
        self.test_mode = 0
        instances.debug = 0
        self.compteur = 0
        self.total_cycles = 0
        self.remaining_cycles = 0
        self.additional_cycle = 0

        self.accumulator = 0
        self.x_register = 0
        self.y_register = 0
        self.program_counter = 0
        self.stack_pointer = 0

        """
        C (carry)
        N (negative)
        Z (zero)
        V (overflow)
        D (decimal)
        """
        self.negative = 0
        self.overflow = 0
        self.break_flag = 0
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
            self.program_counter = entry_point
        else:
        # Equivalent to JMP ($FFFC)
            self.program_counter = instances.memory.read_rom_16(0xfffc)
        if instances.debug : print(f"Entry point : 0x{format_hex_data(self.program_counter)}")
        self.total_cycles = 7 # Cout de match'init
        self.remaining_cycles = 7 - 1 # On évite de compter deux fois le cycle en cours

        return 1

    def nmi(self):
        ''' Raises an NMI interruption'''
        if instances.debug : print("NMI interruption detected")
        self.general_interrupt(0xFFFA)

    def irq(self):
        ''' Raises an IRQ interruption'''
        if instances.debug : print("IRQ interruption detected")
        self.general_interrupt(0xFFFE)

    def general_interrupt(self, address):
        '''General interruption sequence used for NMI and IRQ

        Interruptions last for 7 CPU cycles
        '''
        self.push(self.program_counter >> 8)
        self.push(self.program_counter & 255)
        self.push(self.get_status_register())

        self.interrupt = 0

        self.program_counter = instances.memory.read_rom_16(address)
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

        opcode = instances.memory.read_rom(self.program_counter)
        try:
            if instances.debug > 0:
                self.print_status_summary()

            cpu_instruction = getattr(self, f"fn_0x{opcode:02x}")
            step, self.remaining_cycles = cpu_instruction()
            self.remaining_cycles += self.additional_cycle
            self.total_cycles += self.remaining_cycles
            self.remaining_cycles -= 1 # Do not count current cycle twice
            self.additional_cycle = 0
            self.program_counter += step
            self.compteur += 1
            return
        except KeyError as exception:
            raise Exception(f"Unknow opcode 0x{opcode:02x} at {' '.join(a+b for a,b in zip(f'{self.program_counter:x}'[::2], f'{self.program_counter:x}'[1::2]))}") from exception

    def get_cpu_status(self):
        ''' Return a dictionnary containing the current CPU Status. Usefull for debugging'''
        status = dict()
        status["PC"] = self.program_counter
        status["SP"] = self.stack_pointer
        status["A"] = self.accumulator
        status["X"] = self.x_register
        status["Y"] = self.y_register
        status["P"] = self.get_status_register()
        status["CYC"] = self.total_cycles
        status["PPU_LINE"] = instances.ppu.line
        status["PPU_COL"] = instances.ppu.col
        return status

    def get_status_register(self):
        '''Returns the P register which contains the flag status.

        Bit 5 is always set to 1
        '''
        return (self.negative << 7) | (self.overflow << 6) | (1 << 5) | (self.break_flag << 4) | (self.decimal << 3) | (self.interrupt << 2) | (self.zero << 1) | self.carry

    def set_status_register(self, status_register):
        '''Set the P register which contains the flag status.

        When setting the P Register, the break flag is not set.
        '''
        self.carry = status_register & 1
        self.zero = (status_register >> 1) & 1
        self.interrupt = (status_register >> 2) & 1
        self.decimal = (status_register >> 3) & 1
        #self.flagB = (status_register >> 4) & 1
        self.overflow = (status_register >> 6) & 1
        self.negative = (status_register >> 7) & 1

    def push(self, val):
        '''Push value into stack'''
        instances.memory.write_rom(0x0100 | self.stack_pointer, val)
        self.stack_pointer = 255 if self.stack_pointer == 0 else self.stack_pointer - 1

    def pop(self):
        '''Pop value from stack'''
        self.stack_pointer = 0 if self.stack_pointer == 255 else self.stack_pointer + 1
        return instances.memory.read_rom(0x0100 | self.stack_pointer)

    def get_immediate(self):
        '''Get 8 bit immediate value on PC + 1'''
        return instances.memory.read_rom(self.program_counter+1)

    def set_zero_page(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument'''
        instances.memory.write_rom(self.get_zero_page_address(), val)

    def get_zero_page_address(self):
        '''Get ZeroPage address to be used for current opcode. Alias to get_immediate'''
        return self.get_immediate()

    def get_zero_page_value(self):
        '''Get val from Zero Page memory. Address is given as opcode 1-byte argument'''
        address= self.get_immediate()
        return instances.memory.read_rom(address)

    def set_zero_page_x(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument and X register'''
        instances.memory.write_rom(self.get_zero_page_x_address(), val)

    def get_zero_page_x_address(self):
        '''Get ZeroPage address to be used for current opcode and X register'''
        return (instances.memory.read_rom(self.program_counter+1) + self.x_register) & 255

    def get_zero_page_x_value(self):
        '''Get value at ZeroPage address to be used for current opcode and X register'''
        address = self.get_zero_page_x_address()
        return instances.memory.read_rom(address)

    def set_zero_page_y(self, val):
        '''Write val into Zero Page memory. Address is given as opcode 1-byte argument and Y register'''
        instances.memory.write_rom(self.get_zero_page_y_address(), val)

    def get_zero_page_y_address(self):
        '''Get ZeroPage address to be used for current opcode and Y register'''
        return  (instances.memory.read_rom(self.program_counter+1) + self.y_register) & 255

    def get_zero_page_y_value(self):
        '''Get value at ZeroPage address to be used for current opcode and Y register'''
        address = self.get_zero_page_y_address()
        return instances.memory.read_rom(address)

    def set_absolute(self, val):
        '''Write val into memory. Address is given as opcode 2-byte argument'''
        instances.memory.write_rom(self.get_absolute_address(), val)

    def get_absolute_address(self):
        '''Get address given as opcode 2-byte argument'''
        return instances.memory.read_rom_16(self.program_counter+1)

    def get_absolute_value(self):
        '''Get val from memory. Address is given as opcode 2-byte argument'''
        address = self.get_absolute_address()
        return instances.memory.read_rom(address)

    def set_absolute_x(self, val, is_additionnal = True):
        '''Write val into memory. Address is given as opcode 2-byte argument and X register'''
        instances.memory.write_rom(self.get_absolute_x_address(is_additionnal), val)

    def get_absolute_x_address(self, is_additionnal = True):
        '''Get address given as opcode 2-byte argument and X register'''
        address = instances.memory.read_rom_16(self.program_counter+1)
        target_address = (address + self.x_register) & 0xFFFF
        if  is_additionnal and address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def get_absolute_x_value(self, is_additionnal = True):
        '''Get val from memory. Address is given as opcode 2-byte argument and X register'''
        address = self.get_absolute_x_address(is_additionnal)
        return instances.memory.read_rom(address)

    def set_absolute_y(self, val, is_additionnal = True):
        '''Write val into memory. Address is given as opcode 2-byte argument and Y register'''
        instances.memory.write_rom(self.get_absolute_y_address(is_additionnal), val)

    def get_absolute_y_address(self, is_additionnal = True):
        '''Get address given as opcode 2-byte argument and Y register'''
        address = instances.memory.read_rom_16(self.program_counter+1)
        target_address = (address + self.y_register) & 0xFFFF
        if is_additionnal and address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def get_absolute_y_value(self, is_additionnal = True):
        '''Get val from memory. Address is given as opcode 2-byte argument and Y register'''
        address = self.get_absolute_y_address(is_additionnal)
        return instances.memory.read_rom(address)

    def get_indirect_x_address(self):
        '''Get indirect address given as opcode 2-byte argument and X register'''
        address = self.get_zero_page_x_address()
        return instances.memory.read_rom_16_no_crossing_page(address)

    def get_indirect_x_value(self):
        '''Get val from memory. Indirect address is given as opcode 2-byte argument and X register'''
        address = self.get_indirect_x_address()
        return instances.memory.read_rom(address)

    def set_indirect_x(self, val):
        '''Write val into memory. Indirect address is given as opcode 2-byte argument and X register'''
        instances.memory.write_rom(self.get_indirect_x_address(), val)

    def get_indirect_y_address(self, is_additionnal = True):
        '''Get indirect address given as opcode 2-byte argument and Y register'''
        address = self.get_zero_page_address()
        address = instances.memory.read_rom_16_no_crossing_page(address )
        target_address = 0xFFFF & (address + self.y_register)
        if is_additionnal and address & 0xFF00 != target_address & 0xFF00:
            self.additional_cycle += 1
        return target_address

    def get_indirect_y_value(self, is_additionnal = True):
        '''Get val from memory. Indirect address is given as opcode 2-byte argument and Y register'''
        address = self.get_indirect_y_address(is_additionnal)
        return instances.memory.read_rom(address)

    def set_indirect_y(self, val, is_additionnal = True):
        '''Write val into memory. Indirect address is given as opcode 2-byte argument and Y register'''
        instances.memory.write_rom(self.get_indirect_y_address(is_additionnal), val)

    def set_flags_nz(self, val):
        '''Sets flags N and Z according to value'''
        self.set_negative(val)
        self.set_zero(val)

    def set_negative(self, val):
        ''' Set Negative Flag according to value'''
        if val < 0:
            self.negative = 1
        else:
            self.negative = val >> 7

    def set_zero(self, val):
        ''' Set Zero Flag according to value'''
        self.zero = 1 if val == 0 else 0

    def adc(self, val):
        '''Perform ADC operation for val'''
        adc = val + self.accumulator + self.carry
        self.carry = adc >> 8
        result = 255 & adc

        self.overflow = not not ((self.accumulator ^ result) & (val ^ result) & 0x80)

        self.accumulator = result

        self.set_flags_nz(self.accumulator)

    def fn_0x69(self) :
        '''Function call for ADC #$xx. Immediate'''
        self.adc(self.get_immediate())
        return (2, 2)

    def fn_0x65(self) :
        '''Function call for ADC $xx. Zero Page'''
        self.adc(self.get_zero_page_value())
        return (2, 3)

    def fn_0x75(self) :
        '''Function call for ADC $xx, X. Zero Page, X'''
        self.adc(self.get_zero_page_x_value())
        return (2, 4)

    def fn_0x6d(self) :
        '''Function call for ADC $xxxx. Absolute'''
        self.adc(self.get_absolute_value())
        return (3, 4)

    def fn_0x7d(self, is_additionnal = True) :
        '''Function call for ADC $xxxx, X. Absolute, X'''
        self.adc(self.get_absolute_x_value(is_additionnal))
        return (3, 4)

    def fn_0x79(self, is_additionnal  = True) :
        '''Function call for ADC $xxxx, Y. Absolute, Y'''
        self.adc(self.get_absolute_y_value(is_additionnal))
        return (3, 4)

    def fn_0x61(self) :
        '''Function call for ADC ($xx, X). Indirect, X'''
        self.adc(self.get_indirect_x_value())
        return (2, 6)

    def fn_0x71(self, is_additionnal = True) :
        '''Function call for ADC ($xx), Y. Indirect, Y'''
        self.adc(self.get_indirect_y_value(is_additionnal))
        return (2, 5)

    def fn_0x29(self) :
        '''Function call for AND #$xx. Immediate'''
        self.accumulator &= self.get_immediate()
        self.set_flags_nz(self.accumulator)
        return (2, 2)

    def fn_0x25(self) :
        '''Function call for AND $xx. Zero Page'''
        self.accumulator &= self.get_zero_page_value()
        self.set_flags_nz(self.accumulator)
        return (2, 3)

    def fn_0x35(self) :
        '''Function call for AND $xx, X. Zero Page, X'''
        self.accumulator &= self.get_zero_page_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 4)

    def fn_0x2d(self) :
        '''Function call for AND $xxxx. Absolute'''
        self.accumulator &= self.get_absolute_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x3d(self, is_additionnal = True) :
        '''Function call for AND $xxxx, X. Absolute, X'''
        self.accumulator &= self.get_absolute_x_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x39(self, is_additionnal = True) :
        '''Function call for AND $xxxx, Y. Absolute, Y'''
        self.accumulator &= self.get_absolute_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x21(self) :
        '''Function call for AND ($xx, X). Indirect, X'''
        self.accumulator &= self.get_indirect_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 6)

    def fn_0x31(self, is_additionnal = True) :
        '''Function call for AND ($xx), Y. Indirect, Y'''
        self.accumulator &= self.get_indirect_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (2, 5)

    def fn_0x0a(self) :
        '''Function call for ASL. Accumulator'''
        self.carry = self.accumulator >> 7
        self.accumulator = (self.accumulator << 1) & 0b11111111
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0x06(self) :
        '''Function call for ASL $xx. Zero Page'''
        value = self.get_zero_page_value()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_zero_page(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0x16(self) :
        '''Function call for ASL $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_zero_page_x(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0x0e(self) :
        '''Function call for ASL $xxxx. Absolute'''
        value = self.get_absolute_value()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_absolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0x1e(self, is_additionnal = True) :
        '''Function call for ASL $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value(is_additionnal)
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_absolute_x(value, is_additionnal)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0x24(self) :
        '''Function call for BIT $xx. Zero Page'''
        tocomp = self.get_zero_page_value()
        value = tocomp & self.accumulator
        self.set_zero(value)
        self.negative = (tocomp >> 7) & 1
        self.overflow = (tocomp >> 6) & 1
        return (2, 3)

    def fn_0x2c(self) :
        '''Function call for BIT $xxxx. Absolute'''
        tocomp = self.get_absolute_value()
        value = tocomp & self.accumulator
        self.set_zero(value)
        self.negative = (tocomp >> 7) & 1
        self.overflow = (tocomp >> 6) & 1
        return (3, 4)

    def fn_0x10(self) :
        '''Function call for BPL #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.negative == 0:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle += 1
        return (2, 2)

    def fn_0x30(self) :
        '''Function call for BMI #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.negative == 1:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    # BVC
    # Relative
    def fn_0x50(self) :
        '''Function call for BVC #$xx. Relative'''
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.overflow == 0:
            self.program_counter += signed
            self.additional_cycle += 1
        return (2, 2)

    def fn_0x70(self) :
        '''Function call for BVS #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.overflow == 1:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0x90(self) :
        '''Function call for BCC #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.carry == 0:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0xb0(self) :
        '''Function call for BCS #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.carry == 1:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0xd0(self) :
        '''Function call for BNE #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.zero == 0:
            self.program_counter += signed
            self.additional_cycle += 1
            if self.program_counter & 0xFF00 != old_pc & 0xFF00:
                self.additional_cycle = 1
        return (2, 2)

    def fn_0xf0(self) :
        '''Function call for BEQ #$xx. Relative'''
        old_pc = self.program_counter + 2
        unsigned = self.get_immediate()
        signed = unsigned - 256 if unsigned > 127 else unsigned
        if self.zero == 1:
            self.program_counter += signed
            self.additional_cycle += 1
            if (self.program_counter + 2) & 0xFF00 != old_pc & 0xFF00: # PC+2 to take into account current instruction size
                self.additional_cycle += 1
        return (2, 2)

    def fn_0x00(self) :
        '''Function call for BRK. Implied
        TODO ! Should set Break flag to 1
        '''
        self.program_counter += 1
        self.push(self.program_counter >> 8)
        self.push(self.program_counter & 255)
        self.push(self.get_status_register())
        self.program_counter = instances.memory.read_rom_16(0xFFFE)
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
        self.cmp(self.accumulator, self.get_immediate())
        return (2, 2)

    def fn_0xc5(self) :
        '''Function call for CMP $xx. Zero Page'''
        self.cmp(self.accumulator, self.get_zero_page_value())
        return (2, 3)

    def fn_0xd5(self) :
        '''Function call for CMP $xx, X. Zero Page, X'''
        self.cmp(self.accumulator, self.get_zero_page_x_value())
        return (2, 4)

    def fn_0xcd(self) :
        '''Function call for CMP $xxxx. Absolute'''
        self.cmp(self.accumulator, self.get_absolute_value())
        return (3, 4)

    def fn_0xdd(self) :
        '''Function call for CMP $xxxx, X. Absolute, X'''
        self.cmp(self.accumulator, self.get_absolute_x_value())
        return (3, 4)

    def fn_0xd9(self) :
        '''Function call for CMP $xxxx, Y. Absolute, Y'''
        self.cmp(self.accumulator, self.get_absolute_y_value())
        return (3, 4)

    def fn_0xc1(self) :
        '''Function call for CMP ($xx, X). Indirect, X'''
        self.cmp(self.accumulator, self.get_indirect_x_value())
        return (2, 6)

    def fn_0xd1(self) :
        '''Function call for CMP ($xx), Y. Indirect, Y'''
        self.cmp(self.accumulator, self.get_indirect_y_value())
        return (2, 5)

    def fn_0xe0(self) :
        '''Function call for CPX #$xx. Immediate'''
        self.cmp(self.x_register, self.get_immediate())
        return (2, 2)

    def fn_0xe4(self) :
        '''Function call for CPX $xx. Zero Page'''
        self.cmp(self.x_register, self.get_zero_page_value())
        return (2, 3)

    def fn_0xec(self) :
        '''Function call for CPX $xxxx. Absolute'''
        self.cmp(self.x_register, self.get_absolute_value())
        return (3, 4)

    def fn_0xc0(self) :
        '''Function call for CPY #$xx. Immediate'''
        self.cmp(self.y_register, self.get_immediate())
        return (2, 2)

    def fn_0xc4(self) :
        '''Function call for CPY $xx. Zero Page'''
        self.cmp(self.y_register, self.get_zero_page_value())
        return (2, 3)

    def fn_0xcc(self) :
        '''Function call for CPY $xxxx. Absolute'''
        self.cmp(self.y_register, self.get_absolute_value())
        return (3, 4)

    def fn_0xc6(self) :
        '''Function call for DEC $xx. Zero Page'''
        value = self.get_zero_page_value()
        value = 255 if value == 0 else value - 1
        self.set_zero_page(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0xd6(self) :
        '''Function call for DEC $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        value = 255 if value == 0 else value - 1
        self.set_zero_page_x(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0xce(self) :
        '''Function call for DEC $xxxx. Absolute'''
        value = self.get_absolute_value()
        value = 255 if value == 0 else value - 1
        self.set_absolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0xde(self) :
        '''Function call for CPY $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value()
        value = 255 if value == 0 else value - 1
        self.set_absolute_x(value)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0xc7(self):
        '''Function call for DCP $xx. Zero Page'''
        value = self.get_zero_page_value()
        value = 255 if value == 0 else value - 1
        self.set_zero_page(value)
        self.cmp(self.accumulator, value)
        return (2, 5)

    def fn_0xd7(self):
        '''Function call for DCP $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        value = 255 if value == 0 else value - 1
        self.set_zero_page_x(value)
        self.cmp(self.accumulator, value)
        return (2, 6)

    def fn_0xcf(self):
        '''Function call for DCP $xxxx. Absolute'''
        value = self.get_absolute_value()
        value = 255 if value == 0 else value - 1
        self.set_absolute(value)
        self.cmp(self.accumulator, value)
        return (3, 6)

    def fn_0xdf(self):
        '''Function call for DCP $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value(False)
        value = 255 if value == 0 else value - 1
        self.set_absolute_x(value, False)
        self.cmp(self.accumulator, value)
        return (3, 7)

    def fn_0xdb(self):
        '''Function call for CPY $xxxx, Y. Absolute, Y'''
        value = self.get_absolute_y_value(False)
        value = 255 if value == 0 else value - 1
        self.set_absolute_y(value, False)
        self.cmp(self.accumulator, value)
        return (3, 7)

    def fn_0xc3(self):
        '''Function call for DCP ($xx, X). Indirect, X'''
        value = self.get_indirect_x_value()
        value = 255 if value == 0 else value - 1
        self.set_indirect_x(value)
        self.cmp(self.accumulator, value)
        return (2, 8)

    def fn_0xd3(self):
        '''Function call for DCP ($xx), Y. Indirect, Y'''
        value = self.get_indirect_y_value(False)
        value = 255 if value == 0 else value - 1
        self.set_indirect_y(value, False)
        self.cmp(self.accumulator, value)
        return (2, 8)

    def fn_0xe7(self):
        '''Function call for ISC $xx. Zero Page'''
        value = self.get_zero_page_value()
        value = 0 if value == 255 else value + 1
        self.set_zero_page(value)
        self.sbc(value)
        return (2, 5)

    def fn_0xf7(self):
        '''Function call for ESC $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        value = 0 if value == 255 else value + 1
        self.set_zero_page_x(value)
        self.sbc(value)
        return (2, 6)

    def fn_0xef(self):
        '''Function call for ISC $xxxx. Absolute'''
        value = self.get_absolute_value()
        value = 0 if value == 255 else value + 1
        self.set_absolute(value)
        self.sbc(value)
        return (3, 6)

    def fn_0xff(self):
        '''Function call for ISC $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value(False)
        value = 0 if value == 255 else value + 1
        self.set_absolute_x(value, False)
        self.sbc(value)
        return (3, 7)

    def fn_0xfb(self):
        '''Function call for ISC $xxxx, Y. Absolute, Y'''
        value = self.get_absolute_y_value(False)
        value = 0 if value == 255 else value + 1
        self.set_absolute_y(value, False)
        self.sbc(value)
        return (3, 7)

    def fn_0xe3(self):
        '''Function call for ISC ($xx), X. Indirect, X'''
        value = self.get_indirect_x_value()
        value = 0 if value == 255 else value + 1
        self.set_indirect_x(value)
        self.sbc(value)
        return (2, 8)

    def fn_0xf3(self):
        '''Function call for ISC ($xx, Y). Indirect, Y'''
        value = self.get_indirect_y_value()
        value = 0 if value == 255 else value + 1
        self.set_indirect_y(value)
        self.sbc(value)
        return (2, 6)

    def fn_0x49(self) :
        '''Function call for EOR #$xx. Immediate'''
        self.accumulator ^= self.get_immediate()
        self.set_flags_nz(self.accumulator)
        return (2, 2)

    def fn_0x45(self) :
        '''Function call for EOR $xx. Zero Page'''
        self.accumulator ^= self.get_zero_page_value()
        self.set_flags_nz(self.accumulator)
        return (2, 3)

    def fn_0x55(self) :
        '''Function call for EOR $xx, X. Zero Page, X'''
        self.accumulator ^= self.get_zero_page_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 4)

    def fn_0x4d(self) :
        '''Function call for EOR $xxxx. Absolute'''
        self.accumulator ^= self.get_absolute_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x5d(self, is_additionnal = True) :
        '''Function call for EOR $xxxx, X. Absolute, X'''
        self.accumulator ^= self.get_absolute_x_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x59(self, is_additionnal = True) :
        '''Function call for EOR $xxxx, Y. Absolute, Y'''
        self.accumulator ^= self.get_absolute_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x41(self) :
        '''Function call for EOR ($xx, X). Indirect, X'''
        self.accumulator ^= self.get_indirect_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 6)

    def fn_0x51(self, is_additionnal = True) :
        '''Function call for EOR ($xx), Y. Indirect, Y'''
        self.accumulator ^= self.get_indirect_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
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
        value = self.get_zero_page_value()
        value = 0 if value == 255 else value + 1
        self.set_zero_page(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0xf6(self) :
        '''Function call for INC $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        value = 0 if value == 255 else value + 1
        self.set_zero_page_x(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0xee(self) :
        '''Function call for INC $xxxx. Absolute'''
        value = self.get_absolute_value()
        value = 0 if value == 255 else value + 1
        self.set_absolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0xfe(self) :
        '''Function call for INC $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value()
        value = 0 if value == 255 else value + 1
        self.set_absolute_x(value)
        self.set_flags_nz(value)
        return (3, 7)

    def fn_0x4c(self) :
        '''Function call for JMP $xxxx. Absolute'''
        self.program_counter = self.get_absolute_address()
        return (0, 3)

    def fn_0x6c(self) :
        '''Function call for JMP ($xxxx). Indirect'''
        address = self.get_absolute_address()
        if address & 0xFF == 0xFF: # Strange behaviour in nestest.nes where direct jump to re-aligned address where address at end of page
            address += 1
            if instances.debug :  print(f"JMP address : {address:4x}")
        else:
            address = instances.memory.read_rom_16(address)
        if instances.debug : print(f"JMP address : {address:4x}")
        self.program_counter = address
        return (0, 5)

    def fn_0x20(self) :
        '''Function call for JSR $xxxx. Absolute'''
        program_counter = self.program_counter + 2
        high = program_counter >> 8
        low =  program_counter & 255
        self.push(high) # little endian
        self.push(low)
        self.program_counter = self.get_absolute_address()
        return (0, 6)

    def fn_0xa9(self) :
        '''Function call for LDA #$xx. Immediate'''
        self.accumulator = self.get_immediate()
        self.set_flags_nz(self.accumulator)
        return (2, 2)

    def fn_0xa5(self) :
        '''Function call for LDA $xx. Zero Page'''
        self.accumulator =self.get_zero_page_value()
        self.set_flags_nz(self.accumulator)
        return (2, 3)

    def fn_0xb5(self) :
        '''Function call for LDA $xx, X. Zero Page, X'''
        self.accumulator = self.get_zero_page_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 4)

    def fn_0xad(self) :
        '''Function call for LDA $xxxx. Absolute'''
        self.accumulator = self.get_absolute_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0xbd(self) :
        '''Function call for LDA $xxxx, X. Absolute, X'''
        self.accumulator = self.get_absolute_x_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0xb9(self) :
        '''Function call for LDA $xxxx, Y. Absolute, Y'''
        self.accumulator = self.get_absolute_y_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0xa1(self) :
        '''Function call for LDA ($xx, X). Indirect, X'''
        self.accumulator = self.get_indirect_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 6)

    def fn_0xb1(self) :
        '''Function call for EOR ($xx), Y. Indirect, Y'''
        self.accumulator = self.get_indirect_y_value()
        self.set_flags_nz(self.accumulator)
        return (2, 5)

    def fn_0xa2(self) :
        '''Function call for LDX #$xx. Immediate'''
        self.x_register = self.get_immediate()
        self.set_flags_nz(self.x_register)
        return (2, 2)

    def fn_0xa6(self) :
        '''Function call for LDX $xx. Zero Page'''
        self.x_register = self.get_zero_page_value()
        self.set_flags_nz(self.x_register)
        return (2, 3)

    def fn_0xb6(self) :
        '''Function call for LDX $xx, Y. Zero Page, Y'''
        self.x_register = self.get_zero_page_y_value()
        self.set_flags_nz(self.x_register)
        return (2, 4)

    def fn_0xae(self) :
        '''Function call for LDX $xxxx. Absolute'''
        self.x_register = self.get_absolute_value()
        self.set_flags_nz(self.x_register)
        return (3, 4)

    def fn_0xbe(self) :
        '''Function call for LDX $xxxx, Y. Absolute, Y'''
        self.x_register = self.get_absolute_y_value()
        self.set_flags_nz(self.x_register)
        return (3, 4)

    def fn_0xa0(self) :
        '''Function call for LDY #$xx. Immediate'''
        self.y_register = self.get_immediate()
        self.set_flags_nz(self.y_register)
        return (2, 2)

    def fn_0xa4(self) :
        '''Function call for LDY $xx. Zero Page'''
        self.y_register = self.get_zero_page_value()
        self.set_flags_nz(self.x_register)
        return (2, 3)

    def fn_0xb4(self) :
        '''Function call for LDY $xx, X. Zero Page, X'''
        self.y_register = self.get_zero_page_x_value()
        self.set_flags_nz(self.y_register)
        return (2, 4)

    def fn_0xac(self) :
        '''Function call for LDY $xxxx. Absolute'''
        self.y_register =self.get_absolute_value()
        self.set_flags_nz(self.y_register)
        return (3, 4)

    def fn_0xbc(self) :
        '''Function call for LDY $xxxx, X. Absolute, X'''
        self.y_register = self.get_absolute_x_value()
        self.set_flags_nz(self.y_register)
        return (3, 4)

    def fn_0x4a(self) :
        '''Function call for LSR. Accumulator'''
        self.carry = self.accumulator & 1
        self.accumulator = self.accumulator >> 1
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0x46(self) :
        '''Function call for LSR $xx. Zero Page'''
        value = self.get_zero_page_value()
        self.carry = value & 1
        value = value >> 1
        self.set_zero_page(value)
        self.set_flags_nz(value)
        return (2, 5)

    def fn_0x56(self) :
        '''Function call for LSR $xx, X. Zero Page, X'''
        value = self.get_zero_page_x_value()
        self.carry = value & 1
        value = value >> 1
        self.set_zero_page_x(value)
        self.set_flags_nz(value)
        return (2, 6)

    def fn_0x4e(self) :
        '''Function call for LSR $xxxx. Absolute'''
        value = self.get_absolute_value()
        self.carry = value & 1
        value = value >> 1
        self.set_absolute(value)
        self.set_flags_nz(value)
        return (3, 6)

    def fn_0x5e(self, is_additionnal  = True) :
        '''Function call for LSR $xxxx, X. Absolute, X'''
        value = self.get_absolute_x_value(is_additionnal)
        self.carry = value & 1
        value = value >> 1
        self.set_absolute_x(value, is_additionnal)
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
        self.get_absolute_x_value() # Need extra cycle

        return (3, 4)
    def fn_0x3c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        self.get_absolute_x_value() # Need extra cycle
        return (3, 4)
    def fn_0x5c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        self.get_absolute_x_value() # Need extra cycle
        return (3, 4)
    def fn_0x7c(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        self.get_absolute_x_value() # Need extra cycle
        return (3, 4)
    def fn_0xdc(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        self.get_absolute_x_value() # Need extra cycle
        return (3, 4)
    def fn_0xfc(self) :
        '''Function call for TOP. Implied

        Equivalent to NOP NOP NOP (3-byte NOP)
        '''
        self.get_absolute_x_value() # Need extra cycle
        return (3, 4)
    # Restoring no-self-use pylint control
    # pylint: enable=R0201

    def fn_0x09(self) :
        '''Function call for ORA #$xx. Immediate'''
        self.accumulator |= self.get_immediate()
        self.set_flags_nz(self.accumulator)
        return (2, 2)

    def fn_0x05(self) :
        '''Function call for ORA $xx. Zero Page'''
        self.accumulator |= self.get_zero_page_value()
        self.set_flags_nz(self.accumulator)
        return (2, 3)

    def fn_0x15(self) :
        '''Function call for ORA $xx, X. Zero Page, X'''
        self.accumulator |= self.get_zero_page_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 4)

    def fn_0x0d(self) :
        '''Function call for ORA $xxxx. Absolute'''
        self.accumulator |= self.get_absolute_value()
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x1d(self, is_additionnal = True) :
        '''Function call for ORA $xxxx, X. Absolute, X'''
        self.accumulator |= self.get_absolute_x_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x19(self, is_additionnal = True) :
        '''Function call for ORA $xxxx, Y. Absolute, Y'''
        self.accumulator |= self.get_absolute_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0x01(self) :
        '''Function call for ORA ($xx, X). Indirect, X'''
        self.accumulator |= self.get_indirect_x_value()
        self.set_flags_nz(self.accumulator)
        return (2, 6)

    def fn_0x11(self, is_additionnal = True) :
        '''Function call for ORA ($xx), Y. Indirect, Y'''
        self.accumulator |= self.get_indirect_y_value(is_additionnal)
        self.set_flags_nz(self.accumulator)
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
        self.fn_0x1e(False) # ASL
        self.fn_0x1d(False) # ORA
        return (3, 7)

    def fn_0x1b(self):
        '''Function call for SLO $xxxx, Y. Absolute, Y

        Equivalent to:
            ASL
            ORA
        '''
        value = self.get_absolute_y_value(False)
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_absolute_y(value, False)
        self.fn_0x19(False) # ORA
        return (3, 7)

    def fn_0x03(self):
        '''Function call for SLO ($xx, X). Indirect, X

        Equivalent to:
            ASL
            ORA
        '''
        value = self.get_indirect_x_value()
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_indirect_x(value)
        self.fn_0x01() # ORA
        return (2, 8)

    def fn_0x13(self):
        '''Function call for SLO ($xx), Y. Indirect, Y

        Equivalent to:
            ASL
            ORA
        '''
        value = self.get_indirect_y_value(False)
        self.carry = value >> 7
        value = (value << 1) & 0b11111111
        self.set_indirect_y(value, False)
        self.fn_0x11(False) # ORA
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
        self.fn_0x3e(False) # ROL
        self.fn_0x3d(False) # AND
        return (3, 7)

    def fn_0x3b(self):
        '''Function call for RLA $xxxx, Y. Absolute, Y

        Equivalent to:
            ROL
            AND
        '''
        val = self.get_absolute_y_value(False)
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_absolute_y(val, False)
        self.fn_0x39(False) # AND
        return (3, 7)

    def fn_0x23(self):
        '''Function call for RLA ($xx, X). Indirect, X

        Equivalent to:
            ROL
            AND
        '''
        val = self.get_indirect_x_value()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_indirect_x(val)
        self.fn_0x21() # AND
        return (2, 8)

    def fn_0x33(self):
        '''Function call for RLA ($xx), Y. Indirect, Y

        Equivalent to:
            ROL
            AND
        '''
        val = self.get_indirect_y_value(False)
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_indirect_y(val, False)
        self.fn_0x31(False) # AND
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
        self.fn_0x7e(False) # ROR
        self.fn_0x7d(False) # ADC
        return (3, 7)

    def fn_0x7b(self):
        '''Function call for RRA $xxxx, Y. Absolute, Y

        Equivalent to:
            ROR
            ADC
        '''
        val = self.get_absolute_y_value(False)
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_absolute_y(val, False)
        self.fn_0x79(False) # ADC
        return (3, 7)

    def fn_0x63(self):
        '''Function call for RRA ($xx, X). Indirect, X

        Equivalent to:
            ROR
            ADC
        '''
        val = self.get_indirect_x_value()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_indirect_x(val)
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
        val = self.get_indirect_y_value(False)
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_indirect_y(val, False)
        self.fn_0x71(False) # ADC
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
        self.fn_0x5e(False) # LSR
        self.fn_0x5d(False) # EOR
        return (3, 7)

    def fn_0x5b(self):
        '''Function call for SRE $xxxx, Y. Absolute, Y

        Equivalent to:
            LSR
            EOR
        '''
        val = self.get_absolute_y_value(False)
        self.carry = val & 1
        val = val >> 1
        self.set_absolute_y(val, False)
        self.fn_0x59(False) # EOR
        return (3, 7)

    def fn_0x43(self):
        '''Function call for SRE ($xx, X). Indirect, X

        Equivalent to:
            LSR
            EOR
        '''
        val = self.get_indirect_x_value()
        self.carry = val & 1
        val = val >> 1
        self.set_indirect_x(val)
        self.fn_0x41() # EOR
        return (2, 8)

    def fn_0x53(self):
        '''Function call for SRE ($xx), Y. Indirect, Y

        Equivalent to:
            LSR
            EOR
        '''
        val = self.get_indirect_y_value(False)
        self.carry = val & 1
        val = val >> 1
        self.set_indirect_y(val, False)
        self.fn_0x51(False) # EOR
        return (2, 8)

    def fn_0xaa(self) :
        '''Function call for TAX. Implied'''
        self.x_register = self.accumulator
        self.set_flags_nz(self.x_register)
        return (1, 2)

    def fn_0x8a(self) :
        '''Function call for TXA. Implied'''
        self.accumulator = self.x_register
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0xca(self) :
        '''Function call for DEX. Implied'''
        self.x_register = self.x_register - 1 if self.x_register > 0 else 255
        self.set_flags_nz(self.x_register)
        return (1, 2)

    def fn_0xe8(self) :
        '''Function call for INX. Implied'''
        self.x_register = self.x_register + 1 if self.x_register < 255 else 0
        self.set_flags_nz(self.x_register)
        return (1, 2)

    def fn_0xa8(self) :
        '''Function call for TAY. Implied'''
        self.y_register = self.accumulator
        self.set_flags_nz(self.y_register)
        return (1, 2)

    def fn_0x98(self) :
        '''Function call for TYA. Implied'''
        self.accumulator = self.y_register
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0x88(self) :
        '''Function call for DEY. Implied'''
        self.y_register = self.y_register - 1 if self.y_register > 0 else 255
        self.set_flags_nz(self.y_register)
        return (1, 2)

    def fn_0xc8(self) :
        '''Function call for INY. Implied'''
        self.y_register = self.y_register + 1 if self.y_register < 255 else 0
        self.set_flags_nz(self.y_register)
        return (1, 2)

    def fn_0x2a(self) :
        '''Function call for ROL A. Accumulator'''
        self.accumulator = (self.accumulator << 1) | (self.carry)
        self.carry = self.accumulator >> 8
        self.accumulator &= 255
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0x26(self) :
        '''Function call for ROL $xx. Zero Page'''
        val = self.get_zero_page_value()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_zero_page(val)
        self.set_flags_nz(val)
        return (2, 5)

    def fn_0x36(self) :
        '''Function call for ROL $xx, X. Zero Page, X'''
        val = self.get_zero_page_x_value()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_zero_page_x(val)
        self.set_flags_nz(val)
        return (2, 6)

    def fn_0x2e(self) :
        '''Function call for ROL $xxxx. Absolute'''
        val = self.get_absolute_value()
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_absolute(val)
        self.set_flags_nz(val)
        return (3, 6)

    def fn_0x3e(self, is_additionnal = True) :
        '''Function call for ROL $xxxx, X. Absolute, X'''
        val = self.get_absolute_x_value(is_additionnal)
        val = (val << 1) | (self.carry)
        self.carry = val >> 8
        val &= 255
        self.set_absolute_x(val, is_additionnal)
        self.set_flags_nz(val)
        return (3, 7)

    def fn_0x6a(self) :
        '''Function call for ROR A. Accumulator'''
        carry = self.accumulator & 1
        self.accumulator = (self.accumulator >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_flags_nz(self.accumulator)
        return (1, 2)

    def fn_0x66(self) :
        '''Function call for ROR $xx. Zero Page'''
        val = self.get_zero_page_value()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_zero_page(val)
        self.set_flags_nz(val)
        return (2, 5)

    def fn_0x76(self) :
        '''Function call for ROR $xx, X. Zero Page, X'''
        val = self.get_zero_page_x_value()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_zero_page_x(val)
        self.set_flags_nz(val)
        return (2, 6)

    def fn_0x6e(self) :
        '''Function call for ROR $xxxx. Absolute'''
        val = self.get_absolute_value()
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_absolute(val)
        self.set_flags_nz(val)
        return (3, 6)

    def fn_0x7e(self, is_additionnal = True) :
        '''Function call for ROR$xxxx, X. Absolute, X'''
        val = self.get_absolute_x_value(is_additionnal)
        carry = val & 1
        val = (val >> 1) | (self.carry << 7)
        self.carry = carry
        self.set_absolute_x(val, is_additionnal)
        self.set_flags_nz(val)
        return (3, 7)

    def fn_0x40(self) :
        '''Function call for RTI. Implied'''
        self.set_status_register(self.pop())
        low = self.pop()
        high = self.pop()
        self.program_counter = (high << 8) + low
        return (0, 6)

    def fn_0x60(self) :
        '''Function call for RTS. Implied'''
        low = self.pop()
        high = self.pop()
        self.program_counter = (high << 8) + low + 1 # JSR increment only by two, and RTS add the third
        return (0, 6)

    def sbc(self, val):
        '''General implementation for sbc operation

        SBC is the same as ADC with two's complement on second operand
        '''
        self.adc(255-val)

    def fn_0xe9(self) :
        '''Function call for SBC #$xx. Immediate'''
        self.sbc(self.get_immediate())
        return (2, 2)
    # 0xeb alias to 0x e9
    def fn_0xeb(self) :
        '''Function call for SBC #$xx. Immediate

        0xeb alias to 0xe9
        '''
        return self.fn_0xe9()

    def fn_0xe5(self) :
        '''Function call for SBC $xx. Zero Page'''
        self.sbc(self.get_zero_page_value())
        return (2, 3)

    def fn_0xf5(self) :
        '''Function call for SBC $xx, X. Zero Page, X'''
        self.sbc(self.get_zero_page_x_value())
        return (2, 4)

    def fn_0xed(self) :
        '''Function call for SBC $xxxx. Absolute'''
        self.sbc(self.get_absolute_value())
        return (3, 4)

    def fn_0xfd(self) :
        '''Function call for SBC $xxxx, X. Absolute, X'''
        self.sbc(self.get_absolute_x_value())
        return (3, 4)

    def fn_0xf9(self) :
        '''Function call for SBC $xxxx, Y. Absolute, Y'''
        self.sbc(self.get_absolute_y_value())
        return (3, 4)

    def fn_0xe1(self) :
        '''Function call for SBC ($xx, X). Indirect, X'''
        self.sbc(self.get_indirect_x_value())
        return (2, 6)

    def fn_0xf1(self) :
        '''Function call for SBC ($xx), Y. Indirect, Y'''
        self.sbc(self.get_indirect_y_value())
        return (2, 5)

    def fn_0x85(self) :
        '''Function call for STA $xx. Zero Page'''
        address = self.get_zero_page_address()
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (2, 3 + extra_cycles)

    def fn_0x95(self) :
        '''Function call for STA $xx, X. Zero Page, X'''
        address = self.get_zero_page_x_address()
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (2, 4 + extra_cycles)

    def fn_0x8d(self) :
        '''Function call for STA $xxxx. Absolute'''
        address = self.get_absolute_address()
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (3, 4 + extra_cycles)

    def fn_0x9d(self) :
        '''Function call for STA $xxxx, X. Absolute, X'''
        address = self.get_absolute_x_address(False) # No additionnal cycles on STA
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (3, 5 + extra_cycles)

    def fn_0x99(self) :
        '''Function call for STA $xxxx, Y. Absolute, Y'''
        address = self.get_absolute_y_address(False) # No additionnal cycles on STA
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (3, 5 + extra_cycles)

    def fn_0x81(self) :
        '''Function call for STA ($xx, X). Indirect, X'''
        address = self.get_indirect_x_address()
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (2, 6 + extra_cycles)

    def fn_0x91(self) :
        '''Function call for STA ($xx), Y. Indirect, Y'''
        address = self.get_indirect_y_address(False) # No additionnal cycles on STA
        extra_cycles = instances.memory.write_rom(address, self.accumulator)
        return (2, 6 + extra_cycles)

    def fn_0x9a(self) :
        '''Function call for TXS. Implied'''
        self.stack_pointer = self.x_register
        return (1, 2)

    def fn_0xba(self) :
        '''Function call for TSX. Implied'''
        self.x_register = self.stack_pointer
        self.set_flags_nz(self.x_register)
        return (1, 2)

    def fn_0x48(self) :
        '''Function call for RHA. Implied'''
        self.push(self.accumulator)
        return (1, 3)

    def fn_0x68(self) :
        '''Function call for PLA. Implied'''
        self.accumulator = self.pop()
        self.set_flags_nz(self.accumulator)
        return (1, 4)

    def fn_0x08(self) :
        '''Function call for PHP. Implied'''
        # create status byte
        status_register = self.get_status_register() | (1 << 4)
        self.push(status_register)
        return (1, 3)

    def fn_0x28(self) :
        '''Function call for PLP. Implied'''
        status_register = self.pop()
        self.set_status_register(status_register)
        return (1, 4)

    def fn_0x86(self) :
        '''Function call for STX $xx. Zero Page'''
        address = self.get_zero_page_address()
        instances.memory.write_rom(address, self.x_register)
        return (2, 3)

    def fn_0x96(self) :
        '''Function call for STX $xx, Y. Zero Page, Y'''
        address = self.get_zero_page_y_address()
        instances.memory.write_rom(address, self.x_register)
        return (2, 4)

    def fn_0x8e(self) :
        '''Function call for STX $xxxx. Absolute'''
        address = self.get_absolute_address()
        instances.memory.write_rom(address, self.x_register)
        return (3, 4)

    def fn_0x84(self) :
        '''Function call for STY $xx. Zero Page'''
        address = self.get_zero_page_address()
        instances.memory.write_rom(address, self.y_register)
        return (2, 3)

    def fn_0x94(self) :
        '''Function call for STY $xx, X. Zero Page, X'''
        address = self.get_zero_page_x_address()
        instances.memory.write_rom(address, self.y_register)
        return (2, 4)

    def fn_0x8c(self) :
        '''Function call for STY $xxxx. Absolute'''
        address = self.get_absolute_address()
        instances.memory.write_rom(address, self.y_register)
        return (3, 4)

    def fn_0xa7(self) :
        '''Function call for LAX $xx. Zero Page'''
        self.accumulator = self.get_zero_page_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (2, 3)

    def fn_0xb7(self) :
        '''Function call for LAX $xx, Y. Zero Page, Y'''
        self.accumulator = self.get_zero_page_y_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (2, 4)

    def fn_0xaf(self) :
        '''Function call for LAX $xxxx. Absolute'''
        self.accumulator = self.get_absolute_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0xbf(self) :
        '''Function call for LAX $xxxx, Y. Absolute, Y'''
        self.accumulator = self.get_absolute_y_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (3, 4)

    def fn_0xa3(self) :
        '''Function call for LAX ($xx, X). Indirect, X'''
        self.accumulator = self.get_indirect_x_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (2, 6)

    def fn_0xb3(self) :
        '''Function call for LAX ($xx), Y. Indirect, Y'''
        self.accumulator = self.get_indirect_y_value()
        self.x_register = self.accumulator
        self.set_flags_nz(self.accumulator)
        return (2, 5)

    def fn_0x87(self) :
        '''Function call for SAX $xx. Zero Page'''
        val = self.accumulator & self.x_register
        self.set_zero_page(val)
        return (2, 3)

    def fn_0x97(self) :
        '''Function call for SAX $xx, Y. Zero Page, Y'''
        val = self.accumulator & self.x_register
        self.set_zero_page_y(val)
        return (2, 4)

    def fn_0x8f(self) :
        '''Function call for SAX $xxxx. Absolute'''
        val = self.accumulator & self.x_register
        self.set_absolute(val)
        return (3, 4)

    def fn_0x83(self) :
        '''Function call for SAX ($xx, X). Indirect, X'''
        val = self.accumulator & self.x_register
        self.set_indirect_x(val)
        return (2, 6)


    def print_status(self) :
        '''Print CPU Status'''
        print("CPU")
        print("Registers:")
        print("A\t| X\t| Y\t| SP\t| PC")
        print(f"0x{self.accumulator:02x}\t| 0x{self.x_register:02x}\t| 0x{self.y_register:02x}\t| 0x{self.stack_pointer:02x}\t| 0x{format_hex_data(self.program_counter)}")
        print("")
        print("Flags")
        print("NVxBDIZC")
        print(f"{self.get_status_register():08b}")
        print("")

    def print_status_summary(self) :
        '''Debug print of status'''
        opcode = instances.memory.read_rom(self.program_counter)
        label = OPCODES[opcode][1]
        match = re.search(r'[0-9]+', label)
        if match:
            if len(match.group(0)) == 2:
                val = self.get_immediate()
                label = label.replace(match.group(0), f"{val:x}")
            else:
                val = self.get_absolute_address()
                label = label.replace(match.group(0), f"{format_hex_data(val)}")
        print(f"Counter : {self.compteur:8}, SP : 0x{self.stack_pointer:02x}, PC : {format_hex_data(self.program_counter)} - fn_0x{opcode:02x} - {label:14}, A = {self.accumulator:2x}, X = {self.x_register:2x}, Y = {self.y_register:2x}, Flags NVxBDIZC : {self.get_status_register():08b}")
