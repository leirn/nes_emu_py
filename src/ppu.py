'''The emulator PPU module'''

import time
import instances
import pygame
import utils

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

PALETTE = [
    (84,  84,  84, 255), 	(0,  30, 116, 255),	(8, 16, 144, 255),	(48, 0, 136, 255), 	(68, 0, 100, 255),  	(92, 0,  48, 255),   	(84, 4, 0, 255),   	(60, 24, 0, 255),   	(32, 42, 0, 255), 	(8, 58, 0, 255),    	(0, 64, 0, 255),    	(0, 60, 0, 255),    	(0, 50, 60, 255),    	(0,   0,   0, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
    (152, 150, 152, 255),   (8,  76, 196, 255),   	(48, 50, 236, 255),   	(92, 30, 228, 255),  	(136, 20, 176, 255), 	(160, 20, 100, 255),  	(152, 34, 32, 255),  	(120, 60, 0, 255),   	(84, 90, 0, 255),   	(40, 114, 0, 255),    	(8, 124, 0, 255),    	(0, 118, 40, 255),    	(0, 102, 120, 255),    	(0,   0,   0, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
    (236, 238, 236, 255),   (76, 154, 236, 255),  	(120, 124, 236, 255),  	(176, 98, 236, 255),  	(228, 84, 236, 255), 	(236, 88, 180, 255),  	(236, 106, 100, 255),  	(212, 136, 32, 255),  	(160, 170, 0, 255),  	(116, 196, 0, 255),   	(76, 208, 32, 255),   	(56, 204, 108, 255),   	(56, 180, 204, 255),   	(60,  60,  60, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
    (236, 238, 236, 255),  	(168, 204, 236, 255),  	(188, 188, 236, 255),  	(212, 178, 236, 255),  	(236, 174, 236, 255),	(236, 174, 212, 255),  	(236, 180, 176, 255),  	(228, 196, 144, 255),  	(204, 210, 120, 255),  	(180, 222, 120, 255),  	(168, 226, 144, 255),  	(152, 226, 180, 255),  	(160, 214, 228, 255),  	(160, 162, 160, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
]

class Ppu:
    '''PPU Component. Handles all PPU Operations'''

    def __init__(self):
        self.pixel_generator = self.PixelGenerator(self)
        instances.debug = 0

        self.register_v = 0 #  Current VRAM address, 15 bits
        self.register_t = 0 #  Temporary VRAM address, 15 bits. Can be thought of as address of top left onscreen tile
        self.register_x = 0 #  File X Scroll, 3 bits
        self.register_w = 0 #  First or second write toggle, 1 bit

        self.primary_oam = bytearray(b'\0' * 0x100)

        self.scale = 2
        self.col = 0
        self.line = 0
        self.cycle = 0
        self.frame_count = 0

        self.current_tile = 0

        self.frame_background = ''
        self.frame_sprite = ''
        self.frame_parity = 0

        self.x_scroll = 0
        self.y_scroll = 0

        self.ppuctrl = 0
        self.ppumask = 0
        self.ppustatus = 0b10100000
        self.oamaddr = 0
        self.ppuscroll = 0
        self.ppuaddr = 0
        self.vram = bytearray(b'\0' * 0x2000)
        self.palette_vram =  bytearray(b'\0' *  0x20)
        #self.set_ppudata(0)

    def read_ppu_memory(self, address):
        '''lecture des addresses PPU Memory map

        0x0000 to 0x2000 - 1 : Pattern table
        0x2000 to 0x3000 - 1 : Nametable
        0x3000 to 0x3eff :  Nametable Mirror
        0x3f00 to 0x3f20 - 1 : Palette ram index
        0x3f20 to 0x3fff = Palette ram mirror
        '''
        if address < 0x2000:
            return instances.cartridge.read_chr_rom(address) # CHR_ROM ADDRESS
        if address < 0x3000: # VRAM
            return self.vram[address - 0x2000]
        if address < 0x3F00: # VRAM mirror
            return self.vram[address - 0X3000]
        if address < 0x4000 : # palette
            if address % 4 == 0:
                palette_address = 0
            else:
                palette_address = address % 0x20
            return self.palette_vram[palette_address]
        raise Exception("Out of PPU memory range")

    def write_ppu_memory(self, address, value):
        '''ecriture des addresses PPU Memory map

        0x0000 to 0x2000 - 1 : Pattern table
        0x2000 to 0x3000 - 1 : Nametable
        0x3000 to 0x3eff :  Nametable Mirror
        0x3f00 to 0x3f20 - 1 : Palette ram index
        0x3f20 to 0x3fff = Palette ram mirror
        '''
        if address < 0x2000:
            instances.cartridge.write_chr_rom(address, value) # CHR_ROM ADDRESS
        elif address < 0x3000: # VRAM
            self.vram[address - 0x2000] = value
        elif address < 0x3F00: # VRAM mirror
            self.vram[address - 0X3000] = value
        elif address < 0x4000 : # palette
            if address % 4 == 0:
                palette_address = 0
            else:
                palette_address = address % 0x20
            self.palette_vram[palette_address] = value
        else:
            raise Exception("Out of PPU memory range")

    def write_0x2000(self, value):
        '''Update PPU internal register when CPU write 0x2000 memory address'''
        self.ppuctrl = value
        self.register_t = (self.register_t & 0b111001111111111) | ((value & 0b11) << 10)

    def write_0x2001(self, value):
        '''Update PPU internal register when CPU write 0x2001 memory address - ppumask'''
        self.ppumask = value

    def read_0x2002(self):
        '''Update PPU internal register when CPU read 0x2002 memory address'''
        self.register_w = 0
        self.ppuaddr = 0
        value = self.ppustatus
        self.ppustatus = value & 0b1111111
        return value

    def write_0x2003(self, value):
        '''Update PPU internal register when CPU write 0x2003 memory address - oamaddr'''
        self.oamaddr = value

    def read_0x2004(self):
        '''Update PPU internal register when CPU write 0x2004 memory address - read OAM at oamaddr'''
        return self.primary_oam[self.oamaddr]

    def write_0x2004(self, value):
        '''Update PPU internal register when CPU write 0x2004 memory address - read OAM at oamaddr'''
        self.primary_oam[self.oamaddr] = value

    def write_0x2005(self, value):
        '''Update PPU internal register when CPU write 0x2005 memory address'''
        self.ppuscroll = ((self.ppuscroll << 8 ) + value ) & 0xffff
        if self.register_w == 0:
            self.register_t = (self.register_t & 0b111111111100000) | ((value) >> 5)
            self.register_x = value & 0b111
            self.register_w = 1
        else:
            self.register_t = (self.register_t & 0b000110000011111) | ((value & 0b11111000) << 2) | ((value & 0b111) << 12)
            self.register_w = 0

    def write_0x2006(self, value):
        self.ppuaddr = ((self.ppuaddr << 8 ) + value ) & 0xffff
        '''Update PPU internal register when CPU write 0x2006 memory address'''
        if self.register_w == 0:
            self.register_t = (self.register_t & 0b000000011111111) | ((value & 0b00111111) << 8)
            self.register_w = 1
        else:
            self.register_t = (self.register_t & 0b111111100000000) | value
            self.register_v = self.register_t
            self.register_w = 0

    def read_0x2007(self):
        '''Read PPU internal register at 0x2007 memory address'''
        self.read_or_write_0x2007()
        return self.read_ppu_memory(self.ppuaddr)

    def write_0x2007(self, value):
        '''Write PPU internal register at 0x2007 memory address'''
        self.read_or_write_0x2007()
        print(f"PPUADDR : {self.ppuaddr:x}")
        self.write_ppu_memory(self.ppuaddr, value)

    def read_or_write_0x2007(self):
        '''Update PPU internal register when CPU read or write 0x2007 memory address'''
        if not self.is_rendering_enabled:
            self.register_v += 1 if (self.ppuctrl >> 2) & 1 == 0 else 0x20
        else:
            self.inc_vert_v()
            self.inc_hor_v()

    def write_oamdma(self, value):
        '''Write OAM with memory from main vram passed in value'''
        self.primary_oam[self.oamaddr:] = value

    def inc_hor_v(self):
        '''Increment Horizontal part of v register

        Implementation base on nevdev PPU_scrolling#Wrapping around
        '''
        if (self.register_v & 0x1F) == 31:
            self.register_v &= 0b111111111100000 # hor_v = 0
            self.register_v ^= 0x400 #switch horizontal nametable
        else:
            self.register_v += 1

    def inc_vert_v(self):
        '''Increment Vertical part of v register

        Implementation base on nevdev PPU_scrolling#Wrapping around
        '''
        if (self.register_v & 0x7000) != 0x7000:
            self.register_v += 0x1000
        else:
            self.register_v &= 0xFFF                # Fine Y = 0
            y = (self.register_v & 0x3e0 ) >> 5     # y = vert_v
            if y == 29:
                y = 0
                self.register_v ^= 0x8000           # switch vertical nametable
            elif y == 31:
                y = 0
            else:
                y += 1
            self.register_v = (self.register_v & 0x3e0) | (y << 5)

    def copy_hor_t_to_hor_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b111101111100000) | (self.register_t & 0b00001000011111)

    def copy_vert_t_to_vert_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b00001000011111) | (self.register_t & 0b111101111100000)

    def is_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.ppumask >> 3) & 1 # TODO : This is not the right implementation

    def is_bg_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.ppumask >> 3) & 1

    def is_sprite_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.ppumask >> 4) & 1

    def next(self):
        '''Next function that implement the almost exact PPU rendering workflow'''

        #TODO : prepare for sprite fetching
        if self.line < 240: # Normal line
            if self.col > 0 and self.col < 257:
                if self.is_bg_rendering_enabled():
                    pixel_color = self.pixel_generator.compute_next_pixel()
                    instances.nes.display.fill(pixel_color, (((self.col - 1) * self.scale, self.line * self.scale), (self.scale,self.scale)))
                self.load_tile_data()

        if self.line < 240 or self.line == 261: # Normal line or prerender liner
            if self.col == 257:
                self.register_v = self.register_t
            if self.col > 320: # Preload data for two first tiles of next scanlines
                self.load_tile_data()

        if (self.col, self.line) == (1, 241):
            pygame.display.flip()
            self.set_vblank()
            if (self.ppuctrl >> 7) & 1:
                instances.nes.raise_nmi()

        if (self.col, self.line) == (1, 261):
            self.clear_vblank()

        if self.line == 261 and self.col > 279 and self.col < 305 :
            self.copy_vert_t_to_vert_v
        #Increment position
        self.col  = (self.col + 1) % 341
        if self.col == 0:
            # End of scan line
            self.line = (self.line + 1) % 262
            # TODO : Implement 0,0 cycle skipped on odd frame

        #if instances.debug == 1:
        #print(f"(Line, col) = ({self.line}, {self.col}), v = {self.register_v:x}, t = {self.register_t:x}")

        return (self.col, self.line) == (0, 0)

    def load_tile_data(self):
        '''8 cycle operation to load next tile data'''

        # TODO : Fetch the actual data
        match self.col % 8:
            case 1: #read NT Byte for N+2 tile
                print(f"rr{self.register_v:x}")
                tile_address = 0x2000 | (self.register_v & 0xfff) # Is it NT or tile address ?
                print(f"aa{tile_address:x}")
                nt_byte = self.read_ppu_memory(tile_address)
                print(f"NT Byte : {nt_byte:x}")
                self.pixel_generator.set_nt_byte(nt_byte)
            case 3: #read AT Byte for N+2 tile
                attribute_address = 0x23c0 | (self.register_v & 0xC00) | ((self.register_v >> 4) & 0x38) | ((self.register_v >> 2) & 0x07)
                at_byte = self.read_ppu_memory(attribute_address)
                print(f"AT Byte : {at_byte:x}")
                self.pixel_generator.set_at_byte(at_byte)
            case 5: #read low BG Tile Byte for N+2 tile
                bg_pattern_tabl_addr = ((self.ppuctrl >> 4) & 1) * 0x1000
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                print(f"aa{bg_pattern_tabl_addr:x}")
                print(f"aa{tile_address:x}")
                print(f"aa{bg_pattern_tabl_addr + 16 * tile_address:x}")
                low_bg_tile_byte = self.read_ppu_memory(bg_pattern_tabl_addr + 16 * tile_address)
                print(f"lb{low_bg_tile_byte:x}")
                self.pixel_generator.set_low_bg_tile_byte(low_bg_tile_byte)
            case 7: #read high BG Tile Byte for N+2 tile
                bg_pattern_tabl_addr = ((self.ppuctrl >> 4) & 1) * 0x1000
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                high_bg_tile_byte = self.read_ppu_memory(bg_pattern_tabl_addr + 16 * tile_address + 8)
                print(f"hb{high_bg_tile_byte:x}")
                self.pixel_generator.set_high_bg_tile_byte(high_bg_tile_byte)
            case 0: #increment tile number and shift pixel generator registers
                self.pixel_generator.shift_registers()
                self.current_tile = (self.current_tile + 1) % 960
                if self.col == 256:
                    self.inc_vert_v()
                else:
                    self.inc_hor_v()

    # https://wiki.nesdev.org/w/index.php?title=PPU_registers
    # https://bugzmanov.github.io/nes_ebook/chapter_6_4.html

    # TODO : Vlbank status should be cleared after reading by CPU
    def set_vblank(self):
        '''Set vblank bit in ppustatus register'''
        self.ppustatus |= 0b10000000

    def clear_vblank(self):
        '''Clear vblank bit in ppustatus register'''
        self.ppustatus &= 0b11111111

    def set_sprite0_hit(self):
        '''Set sprite 0 bit in ppustatus register'''
        self.ppustatus |= 0b01000000

    def clear_sprite0_hit(self):
        '''Clear sprite 0 bit in ppustatus register'''
        self.ppustatus &= 0b10111111

    def dump_chr(self):
        """ Display the tiles in CHR Memory. Useful for debugging."""
        print(len(instances.cartridge.chr_rom)/16)
        x_pos = 2
        y_pos = 2
        for counter in range(len(instances.cartridge.chr_rom)//16):

            tile = self.create_tile(instances.cartridge.get_tile(0, counter))
            tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
            instances.nes.display.blit(tile, (x_pos, y_pos))
            if (x_pos +  10 * self.scale)  > 256 * self.scale:
                x_pos = 2
                y_pos += 10 * self.scale
            else :
                x_pos += 10 * self.scale

        pygame.display.update()
        pygame.display.flip()

    def create_tile(self, array_of_byte, palette_address = -1, is_sprite = 0):
        """ Create a tile pygame surface from tile array of bytes and palette address

        Arguments:
        array_of_byte -- The 8 bytes to make a surface from
        palette_address -- The palette to use, from 0 to 4. -1 is used for default palette
        is_sprite -- Allows to select between background and sprite palettes
        """

        surface = pygame.Surface((8, 8), pygame.SRCALPHA)
        palette = []
        palette.append((0, 0, 0, 0))
        if palette_address == -1:
            palette.append(PALETTE[0x23])
            palette.append(PALETTE[0x27])
            palette.append(PALETTE[0x30])
        else:
            address = 0x3f00 + (0x10 * is_sprite) + (0x4 * palette_address)
            palette.append(PALETTE[self.read_ppu_memory(address + 1)])
            palette.append(PALETTE[self.read_ppu_memory(address + 2)])
            palette.append(PALETTE[self.read_ppu_memory(address + 3)])
        for i in range(8):
            for j in range(8):
                bit1 = (array_of_byte[i] >> (7-j)) & 1
                bit2 = (array_of_byte[8 + i] >> (7-j)) & 1
                color_code = bit1 | (bit2 << 1)
                surface.set_at((j, i), palette[color_code])

        return surface

    def print_status(self):
        """Print the PPU status"""
        print("PPU")
        print("PPUCTRL  | PPUMASK  | PPUSTAT  | PPUADDR  | OAMADDR")
        print(f"{self.ppuctrl:08b} | {self.ppumask:08b} | {self.ppustatus:08b} | {self.ppuaddr:08b} | {self.oamaddr:08b}")
        print("OAM")
        utils.print_memory_page(self.primary_oam, 0)
        print("Palette")
        utils.print_memory_page(self.palette_vram)
        print("")

    class PixelGenerator:
        '''This class implement the PPU pixel path, which generate the current pixel'''
        def __init__(self, ppu):
            self.ppu = ppu
            self.bg_palette_register = []
            self.bg_low_byte_table_register = []
            self.bg_high_byte_table_register = []
            self.bg_attribute_table_register = []
            self.bg_nt_table_register = []

        def compute_next_pixel(self):
            '''Compute the pixel to be displayed in current coordinates'''
            fine_x = instances.ppu.col % 8

            palette = []
            palette.append((0, 0, 0, 0))
            palette.append(PALETTE[0x23])
            palette.append(PALETTE[0x27])
            palette.append(PALETTE[0x30])

            bit1 = (self.bg_low_byte_table_register[0] >> (7-fine_x)) & 1
            bit2 = (self.bg_high_byte_table_register[0] >> (7-fine_x)) & 1
            color_code = bit1 | (bit2 << 1)

            print(f"Low byte : {self.bg_low_byte_table_register[0]:x}, high byte : {self.bg_high_byte_table_register[0]:x}")

            return palette[color_code]

        def multiplexer_decision(self, bg_pixel, sprite_pixel, priority):
            '''Implement PPU Priority Multiplexer decision table'''
            bg_transparent_color = 0
            bg_color = 0
            sprite_color = 0
            if bg_pixel == 0 and sprite_pixel == 0:
                return bg_transparent_color
            if bg_pixel == 0 and sprite_pixel > 0:
                return sprite_color
            if sprite_pixel == 0:
                return bg_color
            if priority == 0:
                return sprite_color
            return bg_color

        def shift_registers(self):
            '''Shift registers every 8 cycles'''
            try:
                self.bg_palette_register.pop(0)
                self.bg_low_byte_table_register.pop(0)
                self.bg_high_byte_table_register.pop(0)
                self.bg_attribute_table_register.pop(0)
                self.bg_nt_table_register.pop(0)
            except:
                pass

        def set_nt_byte(self, nt_byte):
            '''Set nt_byte into registers'''
            self.bg_nt_table_register.append(nt_byte)

        def set_at_byte(self, at_byte):
            '''Set at_byte into registers'''
            self.bg_attribute_table_register.append(at_byte)

        def set_low_bg_tile_byte(self, low_bg_tile_byte):
            '''Set low_bg_tile_byte into registers'''
            self.bg_low_byte_table_register.append(low_bg_tile_byte)

        def set_high_bg_tile_byte(self, high_bg_tile_byte):
            '''Set high_bg_tile_byte into registers'''
            self.bg_high_byte_table_register.append(high_bg_tile_byte)