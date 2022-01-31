'''Cartridge mappers' implementations'''
import sys
import instances

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

# Disabling no-self-use pylint control
# pylint: disable=R0201
class Mapper0:
    '''Class to handle mapper type 0'''

    def __init__(self):
        # If mapper = 0 and only 16kB of data, bank loaded twice
        if instances.cartridge.prg_rom_size == 16 * 1024:
            instances.cartridge.prg_rom.extend(instances.cartridge.prg_rom)

        if instances.cartridge.prg_rom_size == 0x1000:
            instances.cartridge.chr_rom.extend(instances.cartridge.chr_rom)

    def read_prg_rom(self, address):
        '''Read PRG ROM from cartridge'''
        return instances.cartridge.prg_rom[address]

    def write_prg_rom(self, address, value):
        '''Write PRG ROM from cartridge. Not implemented in mapper 0'''
        raise Exception("Mapper 0 doesn't allow to write on PRG ROM")

    def read_chr_rom(self, address):
        '''Read ROM from cartridge.'''
        return instances.cartridge.chr_rom[address]

    def write_chr_rom(self, address, value):
        '''Write CHR ROM from cartridge. Not implemented in mapper 0'''
        raise Exception("Mapper 0 doesn't allow to write on CHR ROM")

    def read_ram(self, address):
        '''Read ROM from cartridge. Task will be delegate to mapper'''
        return instances.cartridge.chr_rom[address]

    def write_ram(self, address, value):
        '''Read ROM from cartridge. Task will be delegate to mapper'''
        instances.cartridge.chr_rom[address] = value


class Mapper1:
    '''Class to handle mapper type 1'''
    cartridge = 0

    def __init__(self, cartridge):
        instances.cartridge = cartridge
