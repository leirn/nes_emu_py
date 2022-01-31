'''Debugging tools'''
from doctest import debug_script
import pygame
import instances
from ppu import PALETTE

ERROR = 1
WARN = 2
DEBUG = 4

def log(class_name, level, message):
    '''Print a log message depending on given parameters'''
    if instances.debug :
        print(message)

def dump_chr():
    """ Display the tiles in CHR Memory. Useful for debugging."""
    scale = instances.ppu.scale
    print(len(instances.cartridge.chr_rom)/16)
    x_pos = 2
    y_pos = 2
    for counter in range(len(instances.cartridge.chr_rom)//16):

        tile = create_tile(instances.cartridge.get_tile(0, counter))
        tile = pygame.transform.scale(tile, (int(8 * scale), int(8 * scale)))
        instances.nes.display.blit(tile, (x_pos, y_pos))
        if (x_pos +  10 * scale)  > 256 * scale:
            x_pos = 2
            y_pos += 10 * scale
        else :
            x_pos += 10 * scale

    pygame.display.update()
    pygame.display.flip()

def create_tile(array_of_byte):
    """ Create a tile pygame surface from tile array of bytes and palette address

    Arguments:
    array_of_byte -- The 8 bytes to make a surface from
    palette_address -- The palette to use, from 0 to 4. -1 is used for default palette
    is_sprite -- Allows to select between background and sprite palettes
    """

    surface = pygame.Surface((8, 8), pygame.SRCALPHA)
    palette = []
    palette.append((0, 0, 0, 0))
    palette.append(PALETTE[0x23])
    palette.append(PALETTE[0x27])
    palette.append(PALETTE[0x30])

    for i in range(8):
        for j in range(8):
            bit1 = (array_of_byte[i] >> (7-j)) & 1
            bit2 = (array_of_byte[8 + i] >> (7-j)) & 1
            color_code = bit1 | (bit2 << 1)
            surface.set_at((j, i), palette[color_code])

    return surface

