'''The emulator PPU module'''
import sys
import time
import pygame
import instances
import utils

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

PALETTE = [
    (84,  84,  84), 	(0,  30, 116),	(8, 16, 144),	(48, 0, 136), 	(68, 0, 100),  	(92, 0,  48),   	(84, 4, 0),   	(60, 24, 0),   	(32, 42, 0), 	(8, 58, 0),    	(0, 64, 0),    	(0, 60, 0),    	(0, 50, 60),    	(0,   0,   0),	(0,   0,   0),	(0,   0,   0),
    (152, 150, 152),   (8,  76, 196),   	(48, 50, 236),   	(92, 30, 228),  	(136, 20, 176), 	(160, 20, 100),  	(152, 34, 32),  	(120, 60, 0),   	(84, 90, 0),   	(40, 114, 0),    	(8, 124, 0),    	(0, 118, 40),    	(0, 102, 120),    	(0,   0,   0),	(0,   0,   0),	(0,   0,   0),
    (236, 238, 236),   (76, 154, 236),  	(120, 124, 236),  	(176, 98, 236),  	(228, 84, 236), 	(236, 88, 180),  	(236, 106, 100),  	(212, 136, 32),  	(160, 170, 0),  	(116, 196, 0),   	(76, 208, 32),   	(56, 204, 108),   	(56, 180, 204),   	(60,  60,  60),	(0,   0,   0),	(0,   0,   0),
    (236, 238, 236),  	(168, 204, 236),  	(188, 188, 236),  	(212, 178, 236),  	(236, 174, 236),	(236, 174, 212),  	(236, 180, 176),  	(228, 196, 144),  	(204, 210, 120),  	(180, 222, 120),  	(168, 226, 144),  	(152, 226, 180),  	(160, 214, 228),  	(160, 162, 160),	(0,   0,   0),	(0,   0,   0),
]

class Ppu:
    '''PPU Component. Handles all PPU Operations'''

    def __init__(self):
        self.pixel_generator = self.PixelGenerator(self)
        instances.debug = 0

        self.register_v = 0 #  Current VRAM address, 15 bits
        self.register_t = 0 #  Temporary VRAM address, 15 bits. Can be thought of as address of top left onscreen tile
        self.register_x = 0 #  Fine X Scroll, 3 bits
        self.register_w = 0 #  First or second write toggle, 1 bit

        self.primary_oam = bytearray(b'\0' * 0x100)
        self.secondary_oam = bytearray(b'\0' * 0x40)
        self.sprite_count = 0
        self.sprite_fetcher_count = 0
        self.secondary_oam_pointer = 0

        self.scale = 2
        self.col = 0
        self.line = 0
        self.cycle = 0
        self.frame_count = 0

        self.frame_background = ''
        self.frame_sprite = ''
        self.frame_parity = 1
        self.is_first_sprite_0 = 0

        self.x_scroll = 0
        self.y_scroll = 0

        self.ppuctrl = 0
        self.ppumask = 0
        self.ppustatus = 0b10100000
        self.oamaddr = 0
        self.ppuscroll = 0
        self.ppuaddr = 0
        self.ppudata = 0
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
        '''Update PPU internal register when CPU write 0x2006 memory address'''
        self.ppuaddr = ((self.ppuaddr << 8 ) + value ) & 0xffff
        if self.register_w == 0:
            self.register_t = (self.register_t & 0b000000011111111) | ((value & 0b00111111) << 8)
            self.register_w = 1
        else:
            self.register_t = (self.register_t & 0b111111100000000) | value
            self.register_v = self.register_t
            self.register_w = 0

    def read_0x2007(self):
        '''Read PPU internal register at 0x2007 memory address'''
        if self.ppuaddr % 0x4000 < 0x3f00: # Delayed buffering requiring dummy read
            value = self.ppudata
            self.ppudata = self.read_ppu_memory(self.ppuaddr % 0x4000) # Address above 0x3fff are mirrored down
        else :
            self.ppudata = self.read_ppu_memory(self.ppuaddr % 0x4000) # Address above 0x3fff are mirrored down
            value = self.ppudata

        self.read_or_write_0x2007()
        self.ppuaddr += 1 if (self.ppuctrl >> 2) & 1 == 0 else 0x20
        return value

    def write_0x2007(self, value):
        '''Write PPU internal register at 0x2007 memory address'''
        self.write_ppu_memory(self.ppuaddr % 0x4000, value) # Address above 0x3fff are mirrored down
        self.read_or_write_0x2007()
        self.ppuaddr += 1 if (self.ppuctrl >> 2) & 1 == 0 else 0x20

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
            self.register_v &= 0b111111111100000    # hor_v = 0
            self.register_v ^= 0x400                #switch horizontal nametable
        else:
            self.register_v += 1

    def inc_vert_v(self):
        '''Increment Vertical part of v register

        Implementation base on nevdev PPU_scrolling#Wrapping around
        '''
        if (self.register_v & 0x7000) != 0x7000:
            self.register_v += 0x1000
        else:
            self.register_v &= 0xfff                # Fine Y = 0
            coarse_y = (self.register_v & 0x3e0 ) >> 5     # coarse_y = vert_v
            if coarse_y == 29:
                coarse_y = 0
                self.register_v ^= 0x800            # switch vertical nametable
            elif coarse_y == 31:
                coarse_y = 0
            else:
                coarse_y += 1
            self.register_v = (self.register_v & 0b111110000011111) | (coarse_y << 5)

    def copy_hor_t_to_hor_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b111101111100000) | (self.register_t & 0b000010000011111)

    def copy_vert_t_to_vert_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b000010000011111) | (self.register_t & 0b111101111100000)

    def is_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return self.is_bg_rendering_enabled() and self.is_sprite_rendering_enabled()

    def is_bg_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.ppumask >> 3) & 1

    def is_sprite_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.ppumask >> 4) & 1

    def next(self):
        '''Next function that implement the almost exact PPU rendering workflow'''

        #Pixel rendering
        if self.line < 240 or self.line == 261: # Normal line
            if self.col > 0 and self.col < 257:
                if self.line < 240 and self.is_bg_rendering_enabled():
                    pixel_color = self.pixel_generator.compute_next_pixel()
                    instances.nes.display.fill(pixel_color, (((self.col - 1) * self.scale, self.line * self.scale), (self.scale,self.scale)))

            # Nothing happens during Vblank
            self.next_background_evaluation()
            self.next_sprite_evaluation()

        if (self.col, self.line) == (1, 241):
            pygame.display.flip()
            self.set_vblank()
            if (self.ppuctrl >> 7) & 1:
                instances.nes.raise_nmi()

        if (self.col, self.line) == (1, 261):
            self.clear_vblank()
            self.clear_sprite0_hit()
            self.is_first_sprite_0 = 0
            self.clear_sprite_overflow()
        #Increment position
        self.col  = (self.col + 1) % 341
        if self.col == 0:
            # End of scan line
            self.line = (self.line + 1) % 262
            if self.line == 0:
                if self.frame_parity > 0 :
                    self.col = 1
                self.frame_parity = 1 - self.frame_parity

        return (self.col, self.line) == (0, 0)

    def next_background_evaluation(self):
        '''Next pixel evaluation and '''
        if self.line < 240 or self.line == 261: # Normal line
            if self.col > 0 and self.col < 257:
                self.load_tile_data()
            if self.col == 257:
                self.copy_hor_t_to_hor_v()
            if self.col > 320 and self.col < 337:
                self.load_tile_data()

        if self.is_rendering_enabled() and self.line == 261 and self.col > 279 and self.col < 305 :
            self.copy_vert_t_to_vert_v()

    def load_tile_data(self):
        '''8 cycle operation to load next tile data'''

        match self.col % 8:
            case 1: #read NT Byte for N+2 tile
                tile_address = 0x2000 | (self.register_v & 0xfff) # Is it NT or tile address ?
                nt_byte = self.read_ppu_memory(tile_address)
                self.pixel_generator.set_nt_byte(nt_byte)
            case 3: #read AT Byte for N+2 tile
                attribute_address = 0x23c0 | (self.register_v & 0xC00) | ((self.register_v >> 4) & 0x38) | ((self.register_v >> 2) & 0x07)
                at_byte = self.read_ppu_memory(attribute_address)
                self.pixel_generator.set_at_byte(at_byte)
            case 5: #read low BG Tile Byte for N+2 tile
                chr_bank = ((self.ppuctrl >> 4) & 1) * 0x1000
                fine_y = self.register_v >> 12
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                low_bg_tile_byte = self.read_ppu_memory(chr_bank + 16 * tile_address + fine_y)
                self.pixel_generator.set_low_bg_tile_byte(low_bg_tile_byte)
            case 7: #read high BG Tile Byte for N+2 tile
                chr_bank = ((self.ppuctrl >> 4) & 1) * 0x1000
                fine_y = self.register_v >> 12
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                high_bg_tile_byte = self.read_ppu_memory(chr_bank + 16 * tile_address + 8 + fine_y)
                self.pixel_generator.set_high_bg_tile_byte(high_bg_tile_byte)
            case 0: #increment tile number and shift pixel generator registers
                self.pixel_generator.shift_registers()
                if self.col == 256:
                    self.inc_vert_v()
                else:
                    self.inc_hor_v()

    def next_sprite_evaluation(self):
        '''Handle the sprite evaluation process'''
        if self.col > 0 and self.col < 65:
            '''During those cycles, Secondary OAM is clear on byte after another'''
            self.secondary_oam[self.col - 1] = 0xff
        if self.col == 64:
            self.sprite_count = 0
            self.secondary_oam_pointer = 0

        if self.secondary_oam_pointer > 7:
            self.set_sprite_overflow()
            return # Maximum 8 sprites found per frame

        if self.col > 64 and self.col < 256 and self.sprite_count < 64:
            '''During those cycles, sprites are actually evaluated'''
            #Fetch next sprite first byte (y coordinate)
            sprite_y_coordinate = self.primary_oam[4 * self.sprite_count]
            self.secondary_oam[self.secondary_oam_pointer * 4] = sprite_y_coordinate
            if self.line in range(sprite_y_coordinate, sprite_y_coordinate + 8):
                # Le sprite traverse la scanline, on le copy dans  le secondary oam
                self.secondary_oam[self.secondary_oam_pointer * 4 + 1] = self.primary_oam[4 * self.sprite_count + 1]
                self.secondary_oam[self.secondary_oam_pointer * 4 + 2] = self.primary_oam[4 * self.sprite_count + 2]
                self.secondary_oam[self.secondary_oam_pointer * 4 + 3] = self.primary_oam[4 * self.sprite_count + 3]
                self.secondary_oam_pointer += 1
            self.sprite_count += 1

        if self.col == 256:
            self.sprite_fetcher_count = 0
            self.pixel_generator.clear_sprite_registers()

        if self.sprite_fetcher_count < self.secondary_oam_pointer and self.col > 256 and self.col < 321:
            '''During those cycles sprites are actually fetched for rendering in the next line'''
            match self.col % 8:
                case 7: # Fetch sprite low and high byte at the same time on 7 instead of spreading over 8 cycles
                    y_coordinate    = self.secondary_oam[self.sprite_fetcher_count * 4 + 0]
                    tile_address    = self.secondary_oam[self.sprite_fetcher_count * 4 + 1]
                    attribute       = self.secondary_oam[self.sprite_fetcher_count * 4 + 2]
                    x_coordinate    = self.secondary_oam[self.sprite_fetcher_count * 4 + 3]

                    fine_y = self.line - y_coordinate

                    # Flipping
                    flip_horizontally = (attribute >> 6) & 1
                    flip_vertically = (attribute >> 7) & 1

                    flipping_offset = 0
                    if flip_vertically > 0:
                        flipping_offset = 8
                    if flip_horizontally > 0:
                        fine_y = 7 - fine_y

                    chr_bank = ((self.ppuctrl >> 3) & 1) * 0x1000
                    low_sprite_tile_byte = self.read_ppu_memory(chr_bank + 16 * tile_address + fine_y + flipping_offset)

                    self.pixel_generator.sprite_attribute_table_register.append(attribute)
                    self.pixel_generator.sprite_x_coordinate_table_register.append(x_coordinate)
                    self.pixel_generator.sprite_low_byte_table_register.append(low_sprite_tile_byte)

                    flipping_offset = 8
                    if flip_vertically > 0:
                        flipping_offset = 0

                    high_sprite_tile_byte = self.read_ppu_memory(chr_bank + 16 * tile_address + fine_y + flipping_offset)
                    self.pixel_generator.sprite_high_byte_table_register.append(high_sprite_tile_byte)

                    self.sprite_fetcher_count += 1


    # https://wiki.nesdev.org/w/index.php?title=PPU_registers
    # https://bugzmanov.github.io/nes_ebook/chapter_6_4.html

    # TODO : Vlbank status should be cleared after reading by CPU
    def set_vblank(self):
        '''Set vblank bit in ppustatus register'''
        self.ppustatus |= 0b10000000

    def clear_vblank(self):
        '''Clear vblank bit in ppustatus register'''
        self.ppustatus &= 0b01111111

    def set_sprite0_hit(self):
        '''Set sprite 0 bit in ppustatus register'''
        self.ppustatus |= 0b01000000

    def clear_sprite0_hit(self):
        '''Clear sprite 0 bit in ppustatus register'''
        self.ppustatus &= 0b10111111

    def set_sprite_overflow(self):
        '''Set sprite overflow bit in ppustatus register'''
        self.ppustatus |= 0b00100000

    def clear_sprite_overflow(self):
        '''Clear sprite overflow bit in ppustatus register'''
        self.ppustatus &= 0b11011111

    def print_status(self):
        """Print the PPU status"""
        print("PPU")
        print(f"Line, col : {self.line}, {self.col}")
        print(" Register T         | Register V")
        print(f" {self.register_t:015b}    | {self.register_v:015b}")
        print("PPUCTRL  | PPUMASK  | PPUSTAT  | PPUADDR  | OAMADDR")
        print(f"{self.ppuctrl:08b} | {self.ppumask:08b} | {self.ppustatus:08b} | {self.ppuaddr:04x}     | {self.oamaddr:02x}")
        print("OAM")
        utils.print_memory_page(self.primary_oam, 0)
        print("Secondary OAM")
        utils.print_memory_page(self.secondary_oam, 0)
        print("Palette")
        utils.print_memory_page(self.palette_vram)
        for i in range(6):
            print(f"VRAM Page {i}")
            utils.print_memory_page(self.vram, i, 0x2000)
        print("")
        self.pixel_generator.print_status()

    class PixelGenerator:
        '''This class implement the PPU pixel path, which generate the current pixel'''
        def __init__(self, ppu):
            self.ppu = ppu
            # Start with two empty tiles
            self.bg_palette_register = [0, 0]
            self.bg_low_byte_table_register = [0, 0]
            self.bg_high_byte_table_register = [0, 0]
            self.bg_attribute_table_register = [0, 0]
            self.bg_nt_table_register = [0, 0]

            self.sprite_low_byte_table_register = []
            self.sprite_high_byte_table_register = []
            self.sprite_attribute_table_register = []
            self.sprite_x_coordinate_table_register = []

        def compute_next_pixel(self):
            '''Compute the pixel to be displayed in current coordinates'''

            bg_color_code, bg_color_palette = self.compute_bg_pixel()
            sprite_color_code, sprite_color_palette, priority = self.compute_sprite_pixel()

            return self.multiplexer_decision(bg_color_code, bg_color_palette, sprite_color_code, sprite_color_palette, priority)

        def compute_bg_pixel(self):
            '''Compute the elements for the bg pixel'''
            fine_x = (instances.ppu.col - 1) % 8 + instances.ppu.register_x # Pixel 0 is outputed at col == 1
            register_level = 0
            if fine_x > 7:
                register_level += 1
                fine_x -= 8

            bit1 = (self.bg_low_byte_table_register[register_level] >> (7-fine_x)) & 1
            bit2 = (self.bg_high_byte_table_register[register_level] >> (7-fine_x)) & 1
            bg_color_code = bit1 | (bit2 << 1)

            attribute = self.bg_attribute_table_register[register_level]

            #la position réelle x et y dépendent du coin en haut à gauche défini par register_t + fine x ou y  + la position réelle sur l'écran
            shift_x = (instances.ppu.register_t & 0x1f) + (instances.ppu.col - 1) + instances.ppu.register_x
            shift_y = ((instances.ppu.register_t & 0x3e0) >> 5) + instances.ppu.line + ((instances.ppu.register_t & 0x7000) >> 12)

            # Compute which zone to select in the attribute byte
            shift = ((1 if shift_x % 32 > 15 else 0) + (2 if shift_y % 32 > 15 else 0)) * 2
            bg_color_palette = (attribute >> shift) & 0b11
            return bg_color_code, bg_color_palette

        def compute_sprite_pixel(self):
            '''Compute the elements for the sprite pixel if there is one at that position'''
            for i in range(len(self.sprite_x_coordinate_table_register)):
                sprite_x = self.sprite_x_coordinate_table_register[i]
                # TODO : instances.ppu.col must only wrok where no scrolling, use register_v instead ?
                if instances.ppu.col >= sprite_x and instances.ppu.col < sprite_x + 8:
                    x_offset = instances.ppu.col %8
                    bit1 = (self.sprite_low_byte_table_register[i] >> (7-x_offset)) & 1
                    bit2 = (self.sprite_high_byte_table_register[i] >> (7-x_offset)) & 1
                    sprite_color_code = bit1 | (bit2 << 1)

                    attribute = self.sprite_attribute_table_register[i]
                    priority = (attribute >> 5) & 0x1
                    sprite_color_palette = attribute & 0b11

                    return sprite_color_code, sprite_color_palette, priority
            return 0, 0, 1 # Means no sprite, transparente color

        def multiplexer_decision(self, bg_color_code, bg_color_palette, sprite_color_code, sprite_color_palette, priority):
            '''Implement PPU Priority Multiplexer decision table'''
            bg_palette_address = bg_color_palette << 2
            sprite_palette_address = sprite_color_palette << 2

            if bg_color_code == 0 and sprite_color_code == 0:
                return PALETTE[instances.ppu.palette_vram[0]] # Palette BG Color
            if bg_color_code == 0 and sprite_color_code > 0:
                return PALETTE[instances.ppu.palette_vram[0x10 + sprite_palette_address + sprite_color_code]] # Sprite color > 0
            if sprite_color_code == 0:
                return PALETTE[instances.ppu.palette_vram[bg_palette_address + bg_color_code]] # bg color
            if priority == 0:
                return PALETTE[instances.ppu.palette_vram[0x10 + sprite_palette_address + sprite_color_code]]
            return PALETTE[instances.ppu.palette_vram[bg_palette_address + bg_color_code]] # bg color

        def shift_registers(self):
            '''Shift registers every 8 cycles'''
            #time.sleep(5)
            #try:
            #self.bg_palette_register.pop(0)
            self.bg_low_byte_table_register.pop(0)
            self.bg_high_byte_table_register.pop(0)
            self.bg_attribute_table_register.pop(0)
            self.bg_nt_table_register.pop(0)
            #except:
            #    pass

        def clear_sprite_registers(self):
            '''Reset the sprite registers'''
            self.sprite_low_byte_table_register = []
            self.sprite_high_byte_table_register = []
            self.sprite_attribute_table_register = []
            self.sprite_x_coordinate_table_register = []

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

        def print_status(self):
            '''Print Pixel Generator current status'''


    def xor_primary_oam(self):
        xor = 0
        for i in self.primary_oam:
            xor ^= i
        return xor

    def xor_secondary_oam(self):
        xor = 0
        for i in self.secondary_oam:
            xor ^= i
        return xor

    def print_oam(self):
        print("Primary OAM")
        utils.print_memory_page(self.primary_oam, 0)
        print("Secondary OAM")
        utils.print_memory_page(self.secondary_oam, 0)
