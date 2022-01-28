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

NMI = 0b10
FRAME_COMPLETED = 0b1

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
        self.debug = 0

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

        self.set_ppuctrl(0)
        self.set_ppumask(0)
        self.set_ppustatus(0b10100000)
        self.set_ppu_oamaddr(0)
        self.set_ppuscroll(0)
        self.set_ppuaddr(0)
        #self.set_ppudata(0)

    def write_0x2000(self, val):
        '''Update PPU internal register when CPU write 0x2000 memory address'''
        self.register_t = (self.register_t & 0b111001111111111) | ((val & 0b11) << 10)

    def read_0x2002(self):
        '''Update PPU internal register when CPU read 0x2002 memory address'''
        self.register_w = 0

    def write_0x2005(self, val):
        '''Update PPU internal register when CPU write 0x2005 memory address'''
        if self.register_w == 0:
            self.register_t = (self.register_t & 0b111111111100000) | ((val) >> 5)
            self.register_x = val & 0b111
            self.register_w = 1
        else:
            self.register_t = (self.register_t & 0b000110000011111) | ((val & 0b11111000) << 2) | ((val & 0b111) << 12)
            self.register_w = 0

    def write_0x2006(self, val):
        '''Update PPU internal register when CPU write 0x2006 memory address'''
        if self.register_w == 0:
            self.register_t = (self.register_t & 0b000000011111111) | ((val & 0b00111111) << 8)
            self.register_w = 1
        else:
            self.register_t = (self.register_t & 0b111111100000000) | val
            self.register_v = self.register_t
            self.register_w = 0

    def read_or_write_0x2007(self):
        '''Update PPU internal register when CPU read or write 0x2007 memory address'''
        if not self.is_rendering_enabled:
            self.register_v += 1 if (self.get_ppuctrl() >> 2) & 1 == 0 else 0x20
        else:
            self.inc_vert_v()
            self.inc_hor_v()

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
        vert_v = 0b11111
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

    def inc_hor_t(self):
        '''Increment Horizontal part of t register

        TODO : confirms function is used somwhere
        '''
        hor_t = 0b11111
        self.register_t &= 0b111111111100000
        hor_t = (hor_t + 1) & 0b11111
        self.register_t |= hor_t

    def inc_vert_t(self):
        '''Increment Vertical part of t register

        TODO : confirms function is used somwhere
        '''
        vert_t = 0b11111
        self.register_t &= 0b111110000011111
        vert_t = (vert_t + 1) & 0b11111
        self.register_t |= vert_t

    def copy_hor_t_to_hor_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b111101111100000) | (self.register_t & 0b00001000011111)

    def copy_vert_t_to_vert_v(self):
        '''Copy hor part of t to v'''
        self.register_v = (self.register_v & 0b00001000011111) | (self.register_t & 0b111101111100000)

    def is_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.get_ppumask() >> 3) & 1 # TODO : This is not the right implementation

    def is_bg_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.get_ppumask() >> 3) & 1

    def is_sprite_rendering_enabled(self):
        '''Return 1 is rendering is enabled, 0 otherwise'''
        return (self.get_ppumask() >> 4) & 1

    def bg_quarter(self, bank):
        '''Generate background for full bg bank

        Used by old PPU Architecture. DEPRECATED
        '''
        bg_pattern_tabl_addr = ((self.get_ppuctrl() >> 4) & 1) * 0x1000
        map_address = bg_pattern_tabl_addr + 0x2000 + 0x400 * bank
        attribute_table = map_address + 0x3C0
        quarter = pygame.Surface((256, 240), pygame.SRCALPHA, 32) # Le background

        for j in range(30):
            for i in range(32):
                tile_index = i + (32 * j)
                attribute_address = ((tile_index % 64) // 4) % 8 + (tile_index // 128) * 8
                attribute = instances.memory.read_ppu_memory(attribute_table + attribute_address)

                shift = (i % 4)//2 + (((j % 4)//2 ) << 1)
                color_palette = (attribute >> (shift * 2)) & 0b11

                #read background info in VRAM
                bgtile_index = instances.memory.read_ppu_memory(map_address  + tile_index)
                #if self.debug : print (f"Tile ID : {tile_index} - Tile content : {bgtile_index:x}")
                tile_data = instances.memory.get_tile(bg_pattern_tabl_addr, bgtile_index)
                tile = self.create_tile(tile_data, color_palette, 0)
                quarter.blit(tile, (i * 8, j * 8))

        return quarter

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
            if (self.get_ppuctrl() >> 7) & 1:
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

        #if self.debug == 1:
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
                nt_byte = instances.memory.read_ppu_memory(tile_address)
                print(f"NT Byte : {nt_byte:x}")
                self.pixel_generator.set_nt_byte(nt_byte)
            case 3: #read AT Byte for N+2 tile
                attribute_address = 0x23c0 | (self.register_v & 0xC00) | ((self.register_v >> 4) & 0x38) | ((self.register_v >> 2) & 0x07)
                at_byte = instances.memory.read_ppu_memory(attribute_address)
                print(f"AT Byte : {at_byte:x}")
                self.pixel_generator.set_at_byte(at_byte)
            case 5: #read low BG Tile Byte for N+2 tile
                bg_pattern_tabl_addr = ((self.get_ppuctrl() >> 4) & 1) * 0x1000
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                print(f"aa{bg_pattern_tabl_addr:x}")
                print(f"aa{tile_address:x}")
                print(f"aa{bg_pattern_tabl_addr + 16 * tile_address:x}")
                low_bg_tile_byte = instances.memory.read_ppu_memory(bg_pattern_tabl_addr + 16 * tile_address)
                print(f"lb{low_bg_tile_byte:x}")
                self.pixel_generator.set_low_bg_tile_byte(low_bg_tile_byte)
            case 7: #read high BG Tile Byte for N+2 tile
                bg_pattern_tabl_addr = ((self.get_ppuctrl() >> 4) & 1) * 0x1000
                tile_address = self.pixel_generator.bg_nt_table_register[-1]
                high_bg_tile_byte = instances.memory.read_ppu_memory(bg_pattern_tabl_addr + 16 * tile_address + 8)
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
    def old_next(self):
        '''Execute the next PPU Cycle in a non precise manner

        Will soon be DEPRECATED
        '''

        PPUCTRL = self.get_ppuctrl()
        PPUMASK = self.get_ppumask()
        if self.line == 0 and self.col == 0:
            self.frame_sprite = []
            self.frame_background = pygame.Surface((256 * 2, 240 * 2), pygame.SRCALPHA, 32) # Le background
            self.frame_sprite.append(pygame.Surface(((256, 240)), pygame.SRCALPHA, 32)) # Les sprites derrire le bg
            self.frame_sprite.append(pygame.Surface(((256, 240)), pygame.SRCALPHA, 32)) # Les sprites devant le bg

            if (PPUMASK >>3) & 1 and self.col == 0 and self.line == 0 :	# Update pixel
                flipping = PPUCTRL & 0b11
                mirrors = {
                    0: (0, 1, 2, 3),
                    1: (2, 3, 0, 1),
                    2: (2, 3, 0, 1),
                    3: (3, 2, 1, 0),
                    }
                quarter = self.bg_quarter(mirrors[flipping][0])
                self.frame_background.blit(quarter, (0, 0))
                quarter = self.bg_quarter(mirrors[flipping][1])
                self.frame_background.blit(quarter, (256, 0))
                quarter = self.bg_quarter(mirrors[flipping][2])
                self.frame_background.blit(quarter, (0, 240))
                quarter = self.bg_quarter(mirrors[flipping][3])
                self.frame_background.blit(quarter, (256, 240))

        self.col  = (self.col + 1) % 340

        if (self.line, self.col) == (241, 3):

            if (PPUCTRL >> 5) & 1:
                raise Exception("8x16 tiles are not supported yet")

            if (PPUMASK >>4) & 1  :  # Doit on afficher les sprites
                # Display sprites
                print("Entering display sprinte loop")
                sprite_pattern_table_address = ((PPUCTRL >> 3) & 1) * 0x1000
                for i in range(64):
                    sprite = self.primary_oam[i * 4:i * 4 + 4]
                    s_y = sprite[0]
                    s_x = sprite[3]
                    s_tileId = sprite[1]
                    s_param = sprite[2]
                    s_is_foreground = (s_param >> 5) & 1 # 0 is front, 1 is back
                    s_palette = s_param & 0b11

                    sprite_tile = instances.memory.get_tile(sprite_pattern_table_address, s_tileId)
                    tile = self.create_tile(sprite_tile, s_palette, 1)
                    tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))

                    tile = pygame.transform.flip(tile, (s_param >> 7) & 1, (s_param >> 6) & 1)

                    if self.debug : print(f"Tile {i} : {s_tileId} - {s_x} - {s_y}")
                    self.frame_sprite[s_is_foreground].blit(tile, (s_x * self.scale, (s_y - 1) * self.scale))

                    if i == 0: #chek for Sprint 0 Hit

                        pass

            # Update screen
            self.set_vblank()
            instances.nes.display.fill(PALETTE[instances.memory.read_ppu_memory(0x3f00)]) # Couleur de fond transparene du backgroundaddress = 0x3f00 + (0x10 * is_sprite) + (0x4 * palette_address)
            x = self.x_scroll % 256
            y = self.y_scroll % 240
            pygame.draw.rect(self.frame_background, (255, 0, 0), pygame.Rect(x - 1, y - 1, x + 257, y + 241), 2)

            # To scale
            self.frame_sprite[0]  = pygame.transform.scale(self.frame_sprite[0],  (int(self.scale * 256), int(self.scale * 240)))
            self.frame_sprite[1]  = pygame.transform.scale(self.frame_sprite[1],  (int(self.scale * 256), int(self.scale * 240)))
            self.frame_background = pygame.transform.scale(self.frame_background, (int(self.scale * 256 * 2), int(self.scale * 240 * 2)))
            #Blit
            instances.nes.display.blit(self.frame_sprite[1], (x, y))
            instances.nes.display.blit(self.frame_background, (0, 0))
            instances.nes.display.blit(self.frame_sprite[0], (x, y))
            pygame.display.flip()

            #time.sleep(2)

            if (PPUCTRL >> 7) & 1:
                instances.nes.raise_nmi()
        elif (self.line, self.col) == (261, 3):
            self.clear_vblank()
            self.clear_sprite0_hit()

        elif (self.line, self.col) == (261, 280):
            PPUCTRL = self.get_ppuctrl()

            self.x_scroll = self.get_ppuscroll() >> 8 + (256 * (PPUCTRL & 0b1))
            self.y_scroll = (self.get_ppuscroll() & 0xff) + (240 * ((PPUCTRL >> 1 ) & 0b1))


        if self.col == 0:
            # End of scan line --> Sprite evaluation
            self.line = (self.line + 1)


            # End of frame
            if self.line == 262:
                self.line = 0
                self.frame_parity = 1 - self.frame_parity
                self.frame_count += 1
                return FRAME_COMPLETED
        return 0

    # TODO : Vlbank status should be cleared after reading by CPU
    def set_vblank(self):
        val = self.get_ppustatus()
        val |= 0b10000000
        self.set_ppustatus(val)

    def clear_vblank(self):
        val = self.get_ppustatus()
        val &= 0b11111111
        self.set_ppustatus(val)

    def set_sprite0_hit(self):
        val = self.get_ppustatus()
        val |= 0b01000000
        self.set_ppustatus(val)

    def clear_sprite0_hit(self):
        val = self.get_ppustatus()
        val &= 0b10111111
        self.set_ppustatus(val)

    def set_ppuctrl(self, val):
        """Set the PPUCTRL Register"""
        instances.memory.PPUCTRL = val

    def get_ppuctrl(self):
        """Returns the PPUCTRL Register"""
        return instances.memory.PPUCTRL

    def set_ppumask(self, val):
        """Set the PPUMASK Register"""
        instances.memory.write_rom(0x2001, val)

    def get_ppumask(self):
        """Returns the PPUMASK Register"""
        return instances.memory.read_rom(0x2001)

    def set_ppustatus(self, val):
        """Set the PPUSTATUS Register"""
        instances.memory.PPUSTATUS = val

    def get_ppustatus(self):
        """Returns the PPUSTATUS Register"""
        return instances.memory.PPUSTATUS

    def set_ppu_oamaddr(self, val):
        """Set the OAMADDR Register"""
        instances.memory.write_rom(0x2003, val)

    def get_ppu_oamaddr(self):
        """Returns the OAMADDR Register"""
        return instances.memory.read_rom(0x2003)

    def set_ppu_oamdata(self, val):
        """Set the OAMDATA Register"""
        instances.memory.write_rom(0x2004, val)

    def get_ppu_oamdata(self):
        """Returns the OAMDATA Register"""
        return instances.memory.read_rom(0x2004)

    def set_ppuscroll(self, val):
        """Set the SCROLL Register"""
        instances.memory.PPUSCROLL = val

    def get_ppuscroll(self):
        """Returns the SCROLL Register"""
        return instances.memory.PPUSCROLL

    def set_ppuaddr(self, val):
        """Set the PPUADDR Register"""
        instances.memory.PPUADDR = val

    def get_ppuaddr(self):
        """Returns the PPUADDR Register"""
        return instances.memory.PPUADDR

    def set_ppudata(self, val):
        """Set the PPUDATA Register"""
        instances.memory.write_rom(0x2007, val)

    def get_ppudata(self):
        """Returns the PPUDATA Register"""
        return instances.memory.read_rom(0x2007)

    def dump_chr(self):
        """ Display the tiles in CHR Memory. Useful for debugging."""
        print(len(instances.cartridge.chr_rom)/16)
        c = 0
        x = 2
        y = 2
        for c in range(len(instances.cartridge.chr_rom)//16):

            tile = self.create_tile(instances.memory.get_tile(0, c))
            tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
            instances.nes.display.blit(tile, (x, y))
            if (x +  10 * self.scale)  > 256 * self.scale:
                x = 2
                y += 10 * self.scale
            else :
                x += 10 * self.scale

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
            palette.append(PALETTE[instances.memory.read_ppu_memory(address + 1)])
            palette.append(PALETTE[instances.memory.read_ppu_memory(address + 2)])
            palette.append(PALETTE[instances.memory.read_ppu_memory(address + 3)])
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
        print("PPUCTRL  | PPUMASK  | PPUSTAT")
        print(f"{self.get_ppuctrl():08b} | {self.get_ppumask():08b} | {self.get_ppustatus():08b}")
        print("OAM")
        #utils.print_memory_page(self.primary_oam, 0)
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