'''Cartridge mappers' implementations'''

import instances

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

class Mapper0:
    '''Class to handle mapper type 0'''

    def __init__(self):
        # If mapper = 0 and only 16kB of data, bank loaded twice
        if instances.cartridge.prg_rom_size == 16 * 1024:
            instances.cartridge.prg_rom.extend(instances.cartridge.prg_rom)

        if instances.cartridge.prg_rom_size == 0x1000:
            instances.cartridge.chr_rom.extend(instances.cartridge.chr_rom)

    def read_rom(self, address):
        '''Read ROM from cartridge'''
        return instances.cartridge.prg_rom[address-0X8000]


class Mapper1:
    '''Class to handle mapper type 1'''
    cartridge = 0

    def __init__(self, cartridge):
        instances.cartridge = cartridge
