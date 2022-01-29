'''Memory manager and routing module'''
import sys
import instances

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

from cartridge import Cartridge
from ppu import Ppu
import mappers
import utils


class Memory:
    '''Handles all memory operations and serves as bus between components'''

    def __init__(self):
        instances.debug = 0

        self.internal_ram =  bytearray(b'\0' * 0x800)

        self.ctrl1_status = 0
        self.ctrl2_status = 0

    def read_rom(self, address):
        '''Lecture de la mémoire, à restucturer comme suit:
            0x0000 to 0x1fff : internal ram
            0x2000 to 0x3fff : PPU registers
            0x4000 to 0x4017 : APU and I/O registers
            0x4018 to 0x401f : APU and I/O funcitonality normally disabled
            0x4020 to 0x5fff : Cartridge space but for what ??
            0x6000 to 0x7fff : Cartridge ram
            0x8000 to 0xffff : Cartridge prg_rom
        '''
        if address < 0x2000:
            return self.internal_ram[address % 0x800]
        elif address < 0x3fff:
            address = 0x2000 + (address % 8)
            #Plug into new PPU architecture
            if address == 0x2000:
                '''Write only'''
            elif address == 0x2001:
                '''Write only'''
            elif address == 0x2002:
                return instances.ppu.read_0x2002()
            elif address == 0x2003:
                '''Write only'''
            elif address == 0x2004:
                instances.ppu.read_0x2004()
            elif address == 0x2005:
                '''Write only'''
            elif address == 0x2006:
                '''Write only'''
            elif address == 0x2007:
                return instances.ppu.read_0x2007()
            # Endof plug
        elif address < 0x4018:
            if address == 0x4016: # Handling joystick
                if instances.debug : print(f"Joystick 1 read {self.ctrl1_status:b}")
                value = self.ctrl1_status & 1
                self.ctrl1_status = self.ctrl1_status >> 1
                return value
            elif address == 0x4017: # Handling joystick
                if instances.debug : print(f"Joystick 2 read {self.ctrl2_status:b}")
                value = self.ctrl2_status & 1
                self.ctrl2_status = self.ctrl2_status >> 1
                return value
        elif address < 0x4020:
            '''Normally disabled'''
        elif address < 0x6000:
            '''Cartrige sapce, but what ?'''
        elif address < 0x6000:
            return instances.cartridge.read_ram(address - 0x6000)
        else:
            return instances.cartridge.read_prg_rom(address - 0x8000)

    # NES is Little Endian
    def read_rom_16_no_crossing_page(self, address):
        '''Read 16 bits values forbidding crossing pages'''
        high_address = (address & 0xFF00) +((address + 1) & 0xFF)
        if instances.debug : print(f"High address : {high_address:04x}, Low address : {address:04x}")
        if address > 0x7FFF:
            low = instances.cartridge.read_prg_rom(address - 0x8000)
            high = instances.cartridge.read_prg_rom(high_address - 0x8000) # So that reading never cross pages
            return low + (high <<8)
        else:
            low = self.internal_ram[address]
            high = self.internal_ram[high_address] # So that reading never cross pages
            return low + (high <<8)

    def read_rom_16(self, address):
        '''Read 16 bits values allowing crossing pages'''
        if address > 0x7FFF:
            low = instances.cartridge.mapper.read_prg_rom(address - 0x8000)
            high = instances.cartridge.mapper.read_prg_rom(address + 1 - 0x8000)
            return low + (high <<8)
        else:
            low = self.internal_ram[address]
            high = self.internal_ram[address + 1] # So that reading never cross pages
            return low + (high <<8)


    def write_rom(self, address, value):
        '''Lecture de la mémoire, à restucturer comme suit:
            0x0000 to 0x1fff : internal ram
            0x2000 to 0x3fff : PPU registers
            0x4000 to 0x4017 : APU and I/O registers
            0x4018 to 0x401f : APU and I/O funcitonality normally disabled
            0x4020 to 0x5fff : Cartridge space but for what ??
            0x6000 to 0x7fff : Cartridge ram
            0x8000 to 0xffff : Cartridge prg_rom
        '''
        if address < 0x2000:
            self.internal_ram[address % 0x800] = value
        elif address < 0x3fff:
            address = 0x2000 + (address % 8)
            if address == 0x2000:
                instances.ppu.write_0x2000(value)
            elif address == 0x2001:
                instances.ppu.write_0x2001(value)
            elif address == 0x2002:
                '''Read only'''
            elif address == 0x2003:
                instances.ppu.write_0x2003(value)
            elif address == 0x2004:
                instances.ppu.write_0x2004(value)
            elif address == 0x2005:
                instances.ppu.write_0x2005(value)
            elif address == 0x2006:
                instances.ppu.write_0x2006(value)
            elif address == 0x2007:
                instances.ppu.write_0x2007(value)
            # Endof plug

        elif address < 0x4018:
            if address == 0x4014 : # OAMDMA
                value = value << 8
                instances.ppu.write_oamdma(bytearray(self.internal_ram[value:value + 0x100]))
                return 514
            elif address == 0x4016: # Handling joystick
                if instances.debug : print(f"Joystick write {value:b}")
                if value & 1 == 0:
                    if instances.debug : print(f"Saved {instances.nes.ctrl1.status:b}")
                    # store joypad value
                    self.ctrl1_status = instances.nes.ctrl1.status
                    self.ctrl2_status = instances.nes.ctrl2.status
        elif address < 0x4020:
            '''Normally disabled'''
        elif address < 0x6000:
            '''Cartridge space, but what ??'''
        elif address < 0x8000:
            instances.cartridge.write_ram(address - 0x6000, value)
        else:
            instances.cartridge.write_prg_rom(address - 0x8000, value)
        return 0
    '''
    def read_ppu_memory_at_ppuaddr(self):
        if self.PPUADDR < 0x2000:
            return self.PRG[self.PPUADDR] # CHR_ROM ADDRESS
        elif self.PPUADDR < 0x3000: # VRAM
            val =  self.VRAM[self.PPUADDR - 0x2000]
            self.PPUADDR += 1 if (self.PPUCTRL >> 2) & 1 == 0 else 0x20
            return val
        elif self.PPUADDR < 0x3F00: # VRAM mirror
            val =  self.VRAM[self.PPUADDR - 0X3000]
            self.PPUADDR += 1 if (self.PPUCTRL >> 2) & 1 == 0 else 0x20
            return val
        elif self.PPUADDR < 0x4000 : # palette
            if self.PPUADDR % 4 == 0:
                address = 0
            else:
                address = self.PPUADDR % 0x20
            return self.palette_VRAM[address]
        else:
            raise Exception("Out of PPU memory range")
    ''
    def read_ppu_memory(self, address):
        if address < 0x2000:
            return self.PRG[address] # CHR_ROM ADDRESS
        elif address < 0x3000: # VRAM
            return self.VRAM[address - 0x2000]
        elif address < 0x3F00: # VRAM mirror
            return self.VRAM[address - 0X3000]
        elif address < 0x4000 : # palette
            if address % 4 == 0:
                palette_address = 0
            else:
                palette_address = address % 0x20
            return self.palette_VRAM[palette_address]
        else:
            raise Exception("Out of PPU memory range")
    '' OBSOLETE
    def write_ppu_memory_at_ppuaddr(self, value):
        if self.PPUADDR < 0x2000:
            pass # CHR_ROM ADDRESS
        elif self.PPUADDR < 0x3000: # VRAM
            self.VRAM[self.PPUADDR - 0x2000] = value
            VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
            self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
        elif self.PPUADDR < 0x3F00: # VRAM mirror
            self.VRAM[self.PPUADDR - 0x3000] = value
            VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
            self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
        elif self.PPUADDR < 0x4000: # palette
            if self.PPUADDR % 4 == 0:
                address = 0
            else:
                address = self.PPUADDR % 0x20
            self.palette_VRAM[address] = value
            VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
            self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
    '''
    def print_status(self):
        '''Print the status of Memory component'''
        print("Memory status")
        print("Zero Page")
        utils.print_memory_page(self.internal_ram, 0x0)
        print("Stack")
        utils.print_memory_page(self.internal_ram, 0x1)
        print("Page 2")
        utils.print_memory_page(self.internal_ram, 0x2)
        print("Page 3")
        utils.print_memory_page(self.internal_ram, 0x3)