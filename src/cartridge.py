'''Cartridge module'''
import sys
import instances

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

# https://formats.kaitai.io/ines/

class Cartridge:
    def __init__(self):
        # HEADER
        self.title = b''
        self.header = b''
        self.magic = b''
        self.prg_rom_size = 0
        self.chr_rom_size = 0
        self.prg_ram_size = 0
        self.f6 = b''
        self.f7 = b''
        self.f9 = b''
        self.f10 = b''
        self.mapper = 0
        self.mapper_id = 0

        #TRAINER
        self.is_trainer = False
        self.trainer = b''

        #PRG_ROM
        self.prg_rom = b''

        #CHR_ROM
        self.chr_rom = b''

        #PLAY_CHOISE_10
        self.is_playchoice = False
        self.playchoice = b''

        #TITLE
        self.header = b''

    def read_prg_rom(self, address):
        '''Read ROM from cartridge. Task will be delegated to mapper'''
        return self.mapper.read_prg_rom(address)

    def read_chr_rom(self, address):
        '''Read ROM from cartridge. Task will be delegated to mapper'''
        return self.mapper.read_chr_rom(address)

    def read_ram(self, address):
        '''Read ROM from cartridge. Task will be delegated to mapper'''
        return self.mapper.read_ram(address)

    def write_ram(self, address, value):
        '''Read ROM from cartridge. Task will be delegated to mapper'''
        self.mapper.write_ram(address, value)

    def get_tile(self, bank, tile):
        '''Get Tile data from CHR Rom'''
        if instances.debug : print(f"{len(self.chr_rom):x} - {tile} - {bank + 16 * tile:x}:{bank + 16 * tile + 16:x}")
        tile =  self.chr_rom[bank + 16 * tile:bank + 16 * tile + 16]
        return tile

    def parse_rom(self, cartridge_filename):
        '''Parse rom file and load into memory'''
        stream = open(cartridge_filename, 'rb')

        self.header = stream.read(16)
        self.parse_header()

        if self.is_trainer:
            self.trainer = stream.read(512)

        self.prg_rom = bytearray(stream.read(self.prg_rom_size))

        self.chr_rom = bytearray(stream.read(self.chr_rom_size))
        if self.is_playchoice:
            self.playchoice = stream.read(8224)
        self.title = stream.read()

        stream.close()

        try:
            module = __import__("mappers")
            class_ = getattr(module, f"Mapper{self.mapper_id}")
            self.mapper = class_()
        except Exception as exception:
            raise Exception(f"Unreconized mapper {self.mapper_id}") from exception

    def parse_header(self):
        '''Parse the rom header'''
        h = self.header
        self.magic = h[0:4]
        print(h[5])
        self.prg_rom_size = h[4] * 16 * 1024
        self.chr_rom_size = h[5] * 8 * 1024
        self.f6 = h[6]
        self.is_trainer = self.f6 & 0x1000
        self.f7= h[7]
        self.is_playchoice = self.f6 & 0x100
        self.prg_ram_size= h[8] * 8 * 1024
        self.f9= h[9]
        self.f10= h[10]

        self.mapper_id = (self.f7 & 0x11110000) + ((self.f6 & 0x11110000) >> 4)

    def print_status(self):
        """Print the Cartridge status"""
        print(self.title)
        print(self.header)
        print(self.magic)
        print(f"Trainer present : {self.is_trainer}")
        print(f"PRG_ROM Size : {self.prg_rom_size//1024} kB")
        print(f"CHR_ROM Size : {self.chr_rom_size//1024} kB")
        print(f"PRG_RAM Size : {self.prg_ram_size//1024} kB")
        print(f"Mapper : {self.mapper}")
        print(f"Entry point : {self.prg_rom[0x7ffc:0x7ffc+2]}")
