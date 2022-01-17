# Addressing modes : http://www.emulator101.com/6502-addressing-modes.html
# Opcodes : http://www.6502.org/tutorials/6502opcodes.html

# https://www.atarimagazines.com/compute/issue53/047_1_All_About_The_Status_Register.php

# https://www.masswerk.at/6502/6502_instruction_set.html

# https://www.gladir.com/CODER/ASM6502/referenceopcode.htm
import sys
import cpu_opcodes
import re
from utils import format_hex_data

class cpu:
        debug = 0
        compteur = 0
        remaining_cycles = 0
        
        memory = ""
        A = 0
        X = 0
        Y = 0
        PC = 0
        SP = 0
        
        """
        C (carry)
        N (negative)
        Z (zero)
        V (overflow)
        D (decimal)
        """
        flagN = 0
        flagV = 0
        flagB = 0
        flagD = 0
        flagI = 0
        flagZ = 0
        flagC = 0
        
        def __init__(self, memory):
                self.memory = memory
        
        # initialise PC
        def start(self):
                # Equivalent to JMP ($FFFC)
                self.PC = self.memory.read_rom_16(0xfffc)
                if self.debug : print(f"Entry point : 0x{format_hex_data(self.PC)}")
                
                return 1
        
        def nmi(self):
                # Execute an NMI
                if self.debug : print("NMI interruption detected")
                self.general_interrupt(0xFFFA)
                
        def irq(self):
                if self.debug : print("IRQ interruption detected")
                self.general_interrupt(0xFFFE)
                
        def general_interrupt(self, address):
                
                self.push(self.PC >> 8)
                self.push(self.PC & 255)
                self.push(self.getP())
                
                self.flagI = 0
                
                self.PC = self.memory.read_rom_16(address)
                self.remaining_cycles = 7
        
        # next : execute the next opcode.
        # return the number of cycles used to execute
        def next(self):
                
                if self.PC < 0x8000:
                        if self.debug : print(f"PC out of PRG ROM : {self.PC:x}")
                        exit()
                
                if self.remaining_cycles > 0:
                        self.remaining_cycles -= 1
                        return
                
                opcode = self.memory.read_rom(self.PC)
                try:
                        if self.debug:
                                label = cpu_opcodes.opcodes[opcode][1]
                                l = re.search(r'[0-9]+', label)
                                if l:
                                        if len(l.group(0)) == 2:
                                                val = self.getImmediate()
                                                label = label.replace(l.group(0), f"{val:x}") 
                                        else:
                                                val = self.getAbsoluteAddress()
                                                label = label.replace(l.group(0), f"{format_hex_data(val)}")
                                if self.debug : print(f"Counter : {self.compteur:8}, SP : 0x{self.SP:02x}, PC : {format_hex_data(self.PC)} - fn_0x{opcode:02x} - {label:14}, A = {self.A:2x}, X = {self.X:2x}, Y = {self.Y:2x}")
                        
                        fn = getattr(self, f"fn_0x{opcode:02x}")
                        step, self.remaining_cycles = fn()
                        self.PC += step
                        self.compteur += 1
                        return
                except KeyError as e:
                        print(f"Unknow opcode 0x{opcode:02x} at {' '.join(a+b for a,b in zip(f'{self.PC:x}'[::2], f'{self.PC:x}'[1::2]))}")
                        raise e
                

        def getP(self):
                return (self.flagN << 7) | (self.flagV << 6) | (self.flagB << 4) | (self.flagD << 3) | (self.flagI << 2) | (self.flagZ << 1) | self.flagC

        def setP(self, p):
                self.flagC = p & 1
                self.flagZ = (p >> 1) & 1
                self.flagI = (p >> 2) & 1
                self.flagD = (p >> 3) & 1
                self.flagB = (p >> 4) & 1
                self.flagV = (p >> 6) & 1
                self.flagN = (p >> 7) & 1

        def push(self, val):
                self.memory.write_rom(0x0100 | self.SP, val)
                self.SP = 255 if self.SP == 0 else self.SP - 1
                
        def pop(self):
                self.SP = 0 if self.SP == 255 else self.SP + 1
                return self.memory.read_rom(0x0100 | self.SP)

        # Get 8 bit immediate value on PC + 1
        def getImmediate(self):
                return self.memory.read_rom(self.PC+1)

        def setZeroPage(self, val):
                self.memory.write_rom(self.getZeroPageAddress(), val)

        # Alias to getImmediate
        def getZeroPageAddress(self):
                return self.getImmediate()

        # Get 8 bit zeropage value on 8 bit (PC + 1)
        def getZeroPageValue(self):
                address= self.getImmediate()
                return self.memory.read_rom(address)
        
        def setZeroPageX(self, val):
                self.memory.write_rom(self.getZeroPageXAddress(), val)
                
        def getZeroPageXAddress(self):
                return  (self.memory.read_rom(self.PC+1) + self.X) & 255
                
        def getZeroPageXValue(self):
                address = self.getZeroPageXAddress()
                return self.memory.read_rom(address)
                
        def getZeroPageYAddress(self):
                return  (self.memory.read_rom(self.PC+1) + self.Y) & 255
                
        def getZeroPageYValue(self):
                address = self.getZeroPageYAddress()
                return self.memory.read_rom(address)
        
        def setAbsolute(self, val):
                self.memory.write_rom(self.getAbsoluteAddress(), val)
                
        def getAbsoluteAddress(self):
                return self.memory.read_rom_16(self.PC+1)
                
        def getAbsoluteValue(self):
                address = self.getAbsoluteAddress()
                return self.memory.read_rom(address)
        
        def setAbsoluteX(self, val):
                self.memory.write_rom(self.getAbsoluteXAddress(), val)
                
        def getAbsoluteXAddress(self):
                return self.memory.read_rom_16(self.PC+1) + self.X
                
        def getAbsoluteXValue(self):
                address = self.getAbsoluteXAddress()
                return self.memory.read_rom(address)
                
        def getAbsoluteYAddress(self):
                return self.memory.read_rom_16(self.PC+1) + self.Y
                
        def getAbsoluteYValue(self):
                address = self.getAbsoluteYAddress()
                return self.memory.read_rom(address)

        def getIndirectXAddress(self):
                address = (self.memory.read_rom(self.PC+1) + self.X) & 255
                return self.memory.read_rom_16(address)

        def getIndirectXValue(self):
                address = self.getIndirectXAddress()
                return self.memory.read_rom(address)

        def getIndirectYAddress(self):
                address = self.memory.read_rom(self.PC+1)
                return self.memory.read_rom_16(address + self.Y)

        def getIndirectYValue(self):
                address = self.getIndirectYAddress()
                return self.memory.read_rom(address)
        
        def setFlagNZ(self, val):
                self.setFlagN(val)
                self.setFlagZ(val)
        
        def setFlagN(self, val):
                self.flagN = val >> 7

        def setFlagZ(self, val):
                self.flagZ = 1 if val == 0 else 0

        def ADC(self, input):
                adc = input + self.A + self.flagC
                self.flagC = adc >> 8
                result = 255 & adc
                
                self.flagV = not not ((self.A ^ result) & (input ^ result) & 0x80)
                
                self.A = result
                
                self.setFlagNZ(self.A)

        # ADC #$44
        # Immediate
        def fn_0x69(self) :
                self.ADC(self.getImmediate())
                return (2, 2)

        # ADC $44
        # Zero Page
        def fn_0x65(self) :
                self.ADC(self.getZeroPageValue())
                return (2, 3)

        # ADC $44, X
        # Zero Page, X
        def fn_0x75(self) :
                self.ADC(self.getZeroPageXValue())
                return (2, 4)

        # ADC $4400
        # Absolute
        def fn_0x6d(self) :
                self.ADC(self.getAbsoluteValue())
                return (3, 4)

        # ADC $4400, X
        # Absolute, X
        def fn_0x7d(self) :
                self.ADC(self.getAbsoluteXValue())
                return (3, 4)

        # ADC $4400, Y
        # Absolute, Y
        def fn_0x79(self) :
                self.ADC(self.getAbsoluteYValue())
                return (3, 4)

        # ADC ($44, X)
        # Indirect, X
        def fn_0x61(self) :
                self.ADC(self.getIndirectXValue())
                return (2, 6)

        # ADC ($44), Y
        # Indirect, Y
        def fn_0x71(self) :
                self.ADC(self.getIndirectYValue())
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
                self.A = (self.A < 1) & 0b11111111
                self.setFlagNZ(self.A)
                return (1, 2)

        # ASL $44
        # Zero Page
        def fn_0x06(self) :
                value = self.getZeroPageValue()
                self.flagC = value >> 7
                self.A = (self.A < 1) & 0b11111111
                self.setFlagNZ(self.A)
                return (2, 5)

        # ASL $44, X
        # Zero Page, X
        def fn_0x16(self) :
                value = self.getZeroPageXValue()
                self.flagC = value >> 7
                self.A = (self.A < 1) & 0b11111111
                self.setFlagNZ(self.A)
                return (2, 6)

        # ASL $4400
        # Absolute
        def fn_0x0e(self) :
                value = self.getAbsoluteValue()
                self.flagC = value >> 7
                self.A = (self.A < 1) & 0b11111111
                self.setFlagNZ(self.A)
                return (3, 6)

        # ASL $4400, X
        # Absolute, X
        def fn_0x1e(self) :
                value = self.getAbsoluteXValue()
                self.flagC = value >> 7
                self.A = (self.A << 1) & 0b11111111
                self.setFlagNZ(self.A)
                return (3, 7)

        # BIT $44
        # Zero Page
        def fn_0x24(self) :
                tocomp = self.getZeroPageValue()
                value = tocomp | self.A
                self.setFlagZ(value)
                self.flagN = (tocomp >> 7) & 1
                self.flagV = (tocomp >> 6) & 1
                return (2, 3)

        # BIT $4400
        # Absolute
        def fn_0x2c(self) :
                tocomp = self.getAbsoluteValue()
                value = tocomp | self.A
                self.setFlagZ(value)
                self.flagN = (tocomp >> 7) & 1
                self.flagV = (tocomp >> 6) & 1
                return (3, 4)

        # BPL
        # Relative
        def fn_0x10(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagN == 0:
                        self.PC += signed
                return (2, 2)

        # BMI
        # Relative
        def fn_0x30(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagN == 1:
                        self.PC += signed
                return (2, 2)

        # BVC
        # Relative
        def fn_0x50(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagV == 0:
                        self.PC += signed
                return (2, 2)

        # BVS
        # Relative
        def fn_0x70(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagV == 1:
                        self.PC += signed
                return (2, 2)

        # BCC
        # Relative
        def fn_0x90(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagC == 0:
                        self.PC += signed
                return (2, 2)

        # BCS
        # Relative
        def fn_0xb0(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagC == 1:
                        self.PC += signed
                return (2, 2)

        # BNE
        # Relative
        def fn_0xd0(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagZ == 0:
                        self.PC += signed
                return (2, 2)

        # BEQ
        # Relative
        def fn_0xf0(self) :
                unsigned = self.getImmediate()
                signed = unsigned - 256 if unsigned > 127 else unsigned
                if self.flagZ == 1:
                        self.PC += signed
                return (2, 2)

        # BRK
        # Implied
        def fn_0x00(self) :
                self.PC += 1
                self.push(self.PC >> 8)
                self.push(self.PC & 255)
                self.push(self.getP())
                self.PC = self.memory.read_rom_16(0xFFFE)
                return (0, 7)

        # CMP #$44
        # Immediate
        def fn_0xc9(self) :
                val = self.getImmediate() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 2)

        # CMP $44
        # Zero Page
        def fn_0xc5(self) :
                val = self.getZeroPageValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 3)

        # CMP $44, X
        # Zero Page, X
        def fn_0xd5(self) :
                val = self.getZeroPageXValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 4)

        # CMP $4400
        # Absolute
        def fn_0xcd(self) :
                val = self.getAbsoluteValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (3, 4)

        # CMP $4400, X
        # Absolute, X
        def fn_0xdd(self) :
                val = self.getAbsoluteXValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (3, 4)

        # CMP $4400, Y
        # Absolute, Y
        def fn_0xd9(self) :
                val = self.getAbsoluteYValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (3, 4)

        # CMP ($44), Y
        # Indirect, Y
        def fn_0xc1(self) :
                val = self.getIndirectYValue() - self.A
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 5)

        # CPX #$44
        # Immediate
        def fn_0xe0(self) :
                val = self.getImmediate() - self.X
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 2)

        # CPX $44
        # Zero Page
        def fn_0xe4(self) :
                val = self.getZeroPageValue() - self.X
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 3)

        # CPX $4400
        # Absolute
        def fn_0xec(self) :
                val = self.getAbsoluteValue() - self.X
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (3, 4)

        # CPY #$44
        # Immediate
        def fn_0xc0(self) :
                val = self.getImmediate() - self.Y
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 2)

        # CPY $44
        # Zero Page
        def fn_0xc4(self) :
                val = self.getZeroPageValue() - self.Y
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
                return (2, 3)

        # CPY $4400
        # Absolute
        def fn_0xcc(self) :
                val = self.getAbsoluteValue() - self.Y
                if val > 0:
                        self.flagC = 1
                else:  
                        self.flagC = 0
                self.setFlagNZ(val)
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
                self.PC = self.memory.read_rom_16(address)
                return (0, 5)

        # JSR $5597
        # Absolute
        def fn_0x20(self) :
                pc = self.PC + 3
                high = pc >> 8
                low =  pc & 255
                self.push(high)
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
                self.A = self.A > 1
                self.setFlagNZ(self.A)
                return (1, 2)

        # LSR $44
        # Zero Page
        def fn_0x46(self) :
                value = self.getZeroPageValue()
                self.flagC = value & 1
                self.A = value > 1
                self.setFlagNZ(self.A)
                return (2, 5)

        # LSR $44, X
        # Zero Page, X
        def fn_0x56(self) :
                value = self.getZeroPageXValue()
                self.flagC = value & 1
                self.A = value > 1
                self.setFlagNZ(self.A)
                return (2, 6)

        # LSR $4400
        # Absolute
        def fn_0x4e(self) :
                value = self.getAbsoluteValue()
                self.flagC = value & 1
                self.A = value > 1
                self.setFlagNZ(self.A)
                return (3, 6)

        # LSR $4400, X
        # Absolute, X
        def fn_0x5e(self) :
                value = self.getAbsoluteXValue()
                self.flagC = value & 1
                self.A = value > 1
                self.setFlagNZ(self.A)
                return (3, 7)

        # NOP
        # Implied
        def fn_0xea(self) :
                print("NOP")
                return (1, 2)

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
                self.A = (self.A << 1) & (self.flagC)
                self.flagC = self.A >> 8
                self.A &= 255
                self.setFlagNZ(self.A)
                return (1, 2)

        # ROL $44
        # Zero Page
        def fn_0x26(self) :
                val = self.getZeroPageValue()
                self.A = (val << 1) & (self.flagC)
                self.flagC = self.A >> 8
                self.A &= 255
                self.setFlagNZ(self.A)
                return (2, 5)

        # ROL $44, X
        # Zero Page, X
        def fn_0x36(self) :
                val = self.getZeroPageXValue()
                self.A = (val << 1) & (self.flagC)
                self.flagC = self.A >> 8
                self.A &= 255
                self.setFlagNZ(self.A)
                return (2, 6)

        # ROL $4400
        # Absolute
        def fn_0x2e(self) :
                val = self.getAbsoluteValue()
                self.A = (val << 1) & (self.flagC)
                self.flagC = self.A >> 8
                self.A &= 255
                self.setFlagNZ(self.A)
                return (3, 6)

        # ROL $4400, X
        # Absolute, X
        def fn_0x3e(self) :
                val = self.getAbsoluteXValue()
                self.A = (val << 1) & (self.flagC)
                self.flagC = self.A >> 8
                self.A &= 255
                self.setFlagNZ(self.A)
                print("ROL $4400, X")
                return (3, 7)

        # ROR A
        # Accumulator
        def fn_0x6a(self) :
                carry = self.A & 1
                self.A = (self.A >> 1) & (self.flagC << 7)
                self.flagC = carry
                self.setFlagNZ(self.A)
                return (1, 2)

        # ROR $44
        # Zero Page
        def fn_0x66(self) :
                val = self.getZeroPageValue()
                carry = val & 1
                self.A = (val >> 1) & (self.flagC << 7)
                self.flagC = carry
                self.setFlagNZ(self.A)
                return (2, 5)

        # ROR $44, X
        # Zero Page, X
        def fn_0x76(self) :
                val = self.getZeroPageXValue()
                carry = val & 1
                self.A = (val >> 1) & (self.flagC << 7)
                self.flagC = carry
                self.setFlagNZ(self.A)
                return (2, 6)

        # ROR $4400
        # Absolute
        def fn_0x6e(self) :
                val = self.getAbsoluteValue()
                carry = val & 1
                self.A = (val >> 1) & (self.flagC << 7)
                self.flagC = carry
                self.setFlagNZ(self.A)
                return (3, 6)

        # ROR $4400, X
        # Absolute, X
        def fn_0x7e(self) :
                val = self.getAbsoluteXValue()
                carry = val & 1
                self.A = (val >> 1) & (self.flagC << 7)
                self.flagC = carry
                self.setFlagNZ(self.A)
                return (3, 7)

        # RTI
        # Implied
        def fn_0x40(self) :
                self.setP(self.pop())
                low = self.pop()
                high = self.pop()
                self.PC = (high << 8) + low
                #TO BE IMPLEMENTED
                print("RTI")
                return (0, 6)

        # RTS
        # Implied
        def fn_0x60(self) :
                low = self.pop()
                high = self.pop()
                self.PC = (high << 8) + low
                return (0, 6)

        def SBC(self, input):
                input ^= 255
                c = 1 - self.flagC
                sum = input + self.A + c
                self.flagC = sum >> 8
                result = 255 & sum
                
                self.flagV = not not ((self.A ^ result) & (input ^ result) & 0x80)
                
                self.A = result
                
                self.setFlagNZ(self.A)

        # SBC #$44
        # Immediate
        def fn_0xe9(self) :
                self.SBC(self.getImmediate())
                return (2, 2)

        # SBC $44
        # Zero Page
        def fn_0xe5(self) :
                self.SBC(self.getZeroPageValue())
                return (2, 3)

        # SBC $44, X
        # Zero Page, X
        def fn_0xf5(self) :
                self.SBC(self.getZeroPageXValue())
                return (2, 4)

        # SBC $4400
        # Absolute
        def fn_0xed(self) :
                self.SBC(self.getAbsoluteValue())
                return (3, 4)

        # SBC $4400, X
        # Absolute, X
        def fn_0xfd(self) :
                self.SBC(self.getAbsoluteXValue())
                return (3, 4)

        # SBC $4400, Y
        # Absolute, Y
        def fn_0xf9(self) :
                self.SBC(self.getAbsoluteYValue())
                return (3, 4)

        # SBC ($44, X)
        # Indirect, X
        def fn_0xe1(self) :
                self.SBC(self.getIndirectValue())
                return (2, 6)

        # SBC ($44), Y
        # Indirect, Y
        def fn_0xf1(self) :
                self.SBC(self.getIndirectYValue())
                return (2, 5)

        # STA $44
        # Zero Page
        def fn_0x85(self) :
                address = self.getZeroPageAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (2, 3 + extra_cycles)

        # STA $44, X
        # Zero Page, X
        def fn_0x95(self) :
                address = self.getZeroPageXAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (2, 4 + extra_cycles)

        # STA $4400
        # Absolute
        def fn_0x8d(self) :
                address = self.getAbsoluteAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (3, 4 + extra_cycles)

        # STA $4400, X
        # Absolute, X
        def fn_0x9d(self) :
                address = self.getAbsoluteXAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (3, 5 + extra_cycles)

        # STA $4400, Y
        # Absolute, Y
        def fn_0x99(self) :
                address = self.getAbsoluteYAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (3, 5 + extra_cycles)

        # STA ($44, X)
        # Indirect, X
        def fn_0x81(self) :
                address = self.getIndirectXAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
                return (2, 6 + extra_cycles)

        # STA ($44), Y
        # Indirect, Y
        def fn_0x91(self) :
                address = self.getIndirectYAddress()
                extra_cycles = self.memory.write_rom(address, self.A)
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
                return (1, 4)

        # PHP
        # Implied
        def fn_0x08(self) :
                # create status byte
                self.push(self.getP())
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
                self.memory.write_rom(address, self.X)
                return (2, 3)

        # STX $44, Y
        # Zero Page, Y
        def fn_0x96(self) :
                address = self.getZeroPageYAddress()
                self.memory.write_rom(address, self.X)
                return (2, 4)

        # STX $4400
        # Absolute
        def fn_0x8e(self) :
                address = self.getAbsoluteAddress()
                self.memory.write_rom(address, self.X)
                return (3, 4)

        # STY $44
        # Zero Page
        def fn_0x84(self) :
                address = self.getZeroPageAddress()
                self.memory.write_rom(address, self.Y)
                return (2, 3)

        # STY $44, X
        # Zero Page, X
        def fn_0x94(self) :
                address = self.getZeroPageXAddress()
                self.memory.write_rom(address, self.Y)
                return (2, 4)

        # STY $4400
        # Absolute
        def fn_0x8c(self) :
                address = self.getAbsoluteAddress()
                self.memory.write_rom(address, self.Y)
                return (3, 4)
                
        def print_status(self) :
                print("CPU")
                print("Registers:")
                print("A\t| X\t| Y\t| SP\t| PC")
                print(f"0x{self.A:x}\t| 0x{self.X:x}\t| 0x{self.Y:x}\t| 0x{self.SP:x}\t| 0x{format_hex_data(self.PC)}")
                print("")
                print("Flags")
                print("NVxBDIZC")
                print(f"{self.getP():08b}")
                print("")
                
                
 