'''Memory manager and routing module'''
import instances

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

from cartridge import Cartridge
from ppu import Ppu
import mappers
import utils


class Memory:
    '''Handles all memory operations and serves as bus between components'''

    def __init__(self):
        self.debug = 0

        self.ROM =           bytearray(b'\0' * 0x10000)
        self.PRG =           bytearray(b'\0' * 0x10000)
        self.VRAM =          bytearray(b'\0' * 0x2000)
        self.palette_VRAM =  bytearray(b'\0' *  0x20)
        self.PPUCTRL = 0
        self.PPUSTATUS = 0
        self.PPUADDR = 0
        self.PPUSCROLL = 0
        self.OAMADDR = 0

        self.ctrl1_status = 0
        self.ctrl2_status = 0

    def get_tile(self, bank, tile):
        if self.debug : print(f"{len(instances.cartridge.chr_rom):x} - {tile} - {bank + 16 * tile:x}:{bank + 16 * tile + 16:x}")
        tile =  instances.cartridge.chr_rom[bank + 16 * tile:bank + 16 * tile + 16]
        return tile

    def read_rom(self, address):

        if address > 0x7FFF:
            return instances.cartridge.mapper.read_rom(address)
        elif address < 0x2000: # RAM mirroring
                return self.ROM[address % 0x800]
        elif address >= 0x2000 and address < 0x3f00:
            address = 0x2000 + (address % 8)
            #Plug into new PPU architecture
            if address == 0x2002:
                instances.ppu.read_0x2002()
            elif address == 0x2007:
                instances.ppu.read_or_write_0x2007()
            # Endof plug

            if address == 0x2000: # PPUCTRL
                return self.PPUCTRL
            elif address == 0x2002: # PPUSTATUS
                # Reset PPUADDR and PPUSCROLL
                #self.PPUSCROLL = 0 # Scrolling doesn't work if uncommented
                self.PPUADDR = 0
                value = self.PPUSTATUS
                self.PPUSTATUS = value & 0b1111111
                return value
            elif address == 0x2007:
                return self.read_ppu_memory_at_ppuaddr()
            else:
                return self.ROM[address]
        elif address >= 0x3f00 and address < 0x4000:
            if address % 4 == 0:
                address = 0
            else:
                address = address % 0x20
            return self.palette_VRAM[address]
        elif address < 0x4000: # PPU mirroring
            return self.ROM[0x2000 + (address % 0x8)]
        elif address == 0x4016: # Handling joystick
            if self.debug : print(f"Joystick 1 read {self.ctrl1_status:b}")
            value = self.ctrl1_status & 1
            self.ctrl1_status = self.ctrl1_status >> 1
            return value
        elif address == 0x4017: # Handling joystick
            if self.debug : print(f"Joystick 1 read {self.ctrl1_status:b}")
            value = self.ctrl2_status & 1
            self.ctrl2_status = self.ctrl2_status >> 1
            return value
        else:
            return self.ROM[address]

    # NES is Little Endian
    def read_rom_16_no_crossing_page(self, address):
        high_address = (address & 0xFF00) +((address + 1) & 0xFF)
        if self.debug : print(f"High address : {high_address:04x}, Low address : {address:04x}")
        if address > 0x7FFF:
            low = instances.cartridge.mapper.read_rom(address)
            high = instances.cartridge.mapper.read_rom(high_address) # So that reading never cross pages
            return low + (high <<8)
        else:
            low = self.ROM[address]
            high = self.ROM[high_address] # So that reading never cross pages
            return low + (high <<8)

    def read_rom_16(self, address):
        if address > 0x7FFF:
            low = instances.cartridge.mapper.read_rom(address)
            high = instances.cartridge.mapper.read_rom(address + 1) # So that reading never cross pages
            return low + (high <<8)
        else:
            low = self.ROM[address]
            high = self.ROM[address + 1] # So that reading never cross pages
            return low + (high <<8)


    def write_rom(self, address, value):
        if address > 0x7FFF:
            if self.debug : print(f"Illegal write to address 0x{format_hex_data(address)}")
        elif address >= 0x2000 and address < 0x3f00:
            address = 0x2000 + (address % 8)
            #Plug into new PPU architecture
            if address == 0x2000:
                instances.ppu.write_0x2000(value)
            elif address == 0x2005:
                instances.ppu.write_0x2005(value)
            elif address == 0x2006:
                instances.ppu.write_0x2006(value)
            elif address == 0x2007:
                instances.ppu.read_or_write_0x2007()
            # Endof plug
            if address == 0x2000:
                self.PPUCTRL = value
            elif address == 0x2002:
                print(f"Write PPUSTATUS to val {value}")
                self.PPUSTATUS = value
            elif address == 0x2003:
                self.OAMADDR = value
            elif address == 0x2004:
                instances.ppu.primary_oam[self.OAMADDR] = value
            elif address == 0x2005:
                self.PPUSCROLL = ((self.PPUSCROLL << 8 ) + value ) & 0xffff
            elif address == 0x2006:
                self.PPUADDR = ((self.PPUADDR << 8 ) + value ) & 0xffff
            elif address == 0x2007:
                self.write_ppu_memory_at_ppuaddr(value)
            else:
                self.ROM[address] = value
            return 0
        elif address >= 0x3f00 and address < 0x4000:
            if address % 4 == 0:
                address = 0
            else:
                address = address % 0x20
            self.palette_VRAM[address] = value
            return 0
        elif address == 0x4014 : # OAMDMA
            value = value << 8
            instances.ppu.primary_oam[self.OAMADDR:] = bytearray(self.ROM[value:value + 0x100])
            if len(instances.ppu.primary_oam) < 256:
                raise Exception("OAM trop court")
            return 514
        elif address == 0x4016: # Handling joystick
            if self.debug : print(f"Joystick write {value:b}")
            if value & 1 == 0:
                if self.debug : print(f"Saved {instances.nes.ctrl1.status:b}")
                # store joypad value
                self.ctrl1_status = instances.nes.ctrl1.status
                self.ctrl2_status = instances.nes.ctrl2.status

        elif address < 0x2000:
            self.ROM[address % 0x800] = value
        else:
            self.ROM[address] = value
        return 0


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

    def print_status(self):
        '''Print the status of Memory component'''
        print("Memory status")
        print("OAMADDR\t| PPUADDR")
        print(f"{self.OAMADDR:04x}\t| {self.PPUADDR:04x}")
        print("")
        print("Zero Page")
        utils.print_memory_page(self.ROM, 0x0)
        print("Stack")
        utils.print_memory_page(self.ROM, 0x1)
        print("Page 2")
        utils.print_memory_page(self.ROM, 0x2)
        print("Page 3")
        utils.print_memory_page(self.ROM, 0x3)
        print("Palette")
        utils.print_memory_page(self.palette_VRAM)