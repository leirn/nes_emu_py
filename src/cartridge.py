'''Cartridge module'''
import instances

# Preventing direct execution
if __name__ == '__main__':
    import sys
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

    def parse_rom(self, cartridge_filename):
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

        try:
            module = __import__("mappers")
            class_ = getattr(module, f"Mapper{self.mapper_id}")
            self.mapper = class_()
        except Exception as e:
            raise Exception(f"Unreconized mapper {self.mapper_id}")

        stream.close()

    def parse_header(self):
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
