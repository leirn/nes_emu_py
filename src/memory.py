'''Memory manager and routing module'''
import sys
import instances
import mappers
import utils

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

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
        if address < 0x3fff:
            address = 0x2000 + (address % 8)
            match address:
                #case 0x2000: Write only
                #case 0x2001: Write only
                case 0x2002: return instances.ppu.read_0x2002()
                #case 0x2003: Write only
                case 0x2004: return instances.ppu.read_0x2004()
                #case 0x2005: Write only
                #case 0x2006: Write only
                case 0x2007: return instances.ppu.read_0x2007()
        if address < 0x4018:
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
        #if address < 0x4020:
        #    '''Normally disabled'''
        #if address < 0x6000:
        #    '''Cartrige sapce, but what ?'''
        if address < 0x6000:
            return instances.cartridge.read_ram(address - 0x6000)
        return instances.cartridge.read_prg_rom(address - 0x8000)

    # NES is Little Endian
    def read_rom_16_no_crossing_page(self, address):
        '''Read 16 bits values forbidding crossing pages'''
        high_address = (address & 0xFF00) +((address + 1) & 0xFF)
        if instances.debug : print(f"High address : {high_address:04x}, Low address : {address:04x}")
        high, low = 0, 0
        if address > 0x7FFF:
            low = instances.cartridge.read_prg_rom(address - 0x8000)
            high = instances.cartridge.read_prg_rom(high_address - 0x8000) # So that reading never cross pages

        else:
            low = self.internal_ram[address]
            high = self.internal_ram[high_address] # So that reading never cross pages
        return low + (high <<8)

    def read_rom_16(self, address):
        '''Read 16 bits values allowing crossing pages'''
        high, low = 0, 0
        if address > 0x7FFF:
            low = instances.cartridge.mapper.read_prg_rom(address - 0x8000)
            high = instances.cartridge.mapper.read_prg_rom(address + 1 - 0x8000)
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
            match address:
                case 0x2000: instances.ppu.write_0x2000(value)
                case 0x2001: instances.ppu.write_0x2001(value)
                #case' 0x2002: Read only
                case 0x2003: instances.ppu.write_0x2003(value)
                case 0x2004: instances.ppu.write_0x2004(value)
                case 0x2005: instances.ppu.write_0x2005(value)
                case 0x2006: instances.ppu.write_0x2006(value)
                case 0x2007: instances.ppu.write_0x2007(value)

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