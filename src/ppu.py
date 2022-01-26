'''The emulator PPU module'''

import time
import pygame

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

    def __init__(self, emulator):
        self.pixel_generator = self.PixelGenerator(self)
        self.debug = 0

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
        self.emulator = emulator

        self.setPPUCTRL(0)
        self.setPPUMASK(0)
        self.setPPUSTATUS(0b10100000)
        self.setPPU_OAMADDR(0)
        self.setPPUSCROLL(0)
        self.setPPUADDR(0)
        self.setPPUDATA(0)

    def bg_quarter(self, bank):
        bg_pattern_tabl_addr = ((self.getPPUCTRL() >> 4) & 1) * 0x1000
        map_address = bg_pattern_tabl_addr + 0x2000 + 0x400 * bank
        attribute_table = map_address + 0x3C0
        quarter = pygame.Surface((256, 240), pygame.SRCALPHA, 32) # Le background

        for j in range(30):
            for i in range(32):
                tile_index = i + (32 * j)
                attribute_address = ((tile_index % 64) // 4) % 8 + (tile_index // 128) * 8
                attribute = self.emulator.memory.read_ppu_memory(attribute_table + attribute_address)

                shift = (i % 4)//2 + (((j % 4)//2 ) << 1)
                color_palette = (attribute >> (shift * 2)) & 0b11

                #read background info in VRAM
                bgtile_index = self.emulator.memory.read_ppu_memory(map_address  + tile_index)
                #if self.debug : print (f"Tile ID : {tile_index} - Tile content : {bgtile_index:x}")
                tile_data = self.emulator.memory.getTile(bg_pattern_tabl_addr, bgtile_index)
                tile = self.create_tile(tile_data, color_palette, 0)
                quarter.blit(tile, (i * 8, j * 8))

        return quarter

    def next(self):
        '''Next function that implement the almost exact PPU rendering workflow'''

        #TODO : prepare for sprite fetching
        if self.line < 240: # Normal line
            if self.col > 0 and self.col < 257:
                pixel_color = self.pixel_generator.compute_next_pixel()
                self.emulator.display.fill(pixel_color, (((self.col - 1) * self.scale, self.line * self.scale), (self.scale,self.scale)))
                self.load_tile_data()

        if self.line < 240 or self.line == 261: # Normal line or prerender liner
            if self.col > 320: # Preload data for two first tiles of next scanlines
                self.load_tile_data()

        if (self.col, self.line) == (241, 1):
            pygame.display.flip()
            self.set_vblank()

        if (self.col, self.line) == (261, 1):
            self.clear_vblank()

        #Increment position
        self.col  = (self.col + 1) % 341
        if self.col == 0:
            # End of scan line
            self.line = (self.line + 1) % 262
            # TODO : Implement 0,0 cycle skipped on odd frame

        return (self.col, self.line) == (0, 0)

    def load_tile_data(self):
        '''8 cycle operation to load next tile data'''

        # TODO : Fetch the actual data
        match self.col % 8:
            case 1: #read NT Byte for N+2 tile
                nt_byte = 0
                self.pixel_generator.set_nt_byte(nt_byte)
            case 3: #read AT Byte for N+2 tile
                at_byte = 0
                self.pixel_generator.set_at_byte(at_byte)
            case 5: #read low BG Tile Byte for N+2 tile
                low_bg_tile_byte = 0
                self.pixel_generator.set_low_bg_tile_byte(low_bg_tile_byte)
            case 7: #read high BG Tile Byte for N+2 tile
                high_bg_tile_byte = 0
                self.pixel_generator.set_high_bg_tile_byte(high_bg_tile_byte)
            case 8: #increment tile number and shift pixel generator registers
                self.pixel_generator.shift_registers()
                self.current_tile = (self.current_tile + 1) % 960
                pass

    # https://wiki.nesdev.org/w/index.php?title=PPU_registers
    # https://bugzmanov.github.io/nes_ebook/chapter_6_4.html
    def old_next(self):
        '''Execute the next PPU Cycle in a non precise manner'''

        PPUCTRL = self.getPPUCTRL()
        PPUMASK = self.getPPUMASK()
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
                    sprite = self.emulator.memory.OAM[i * 4:i * 4 + 4]
                    s_y = sprite[0]
                    s_x = sprite[3]
                    s_tileId = sprite[1]
                    s_param = sprite[2]
                    s_is_foreground = (s_param >> 5) & 1 # 0 is front, 1 is back
                    s_palette = s_param & 0b11

                    sprite_tile = self.emulator.memory.getTile(sprite_pattern_table_address, s_tileId)
                    tile = self.create_tile(sprite_tile, s_palette, 1)
                    tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))

                    tile = pygame.transform.flip(tile, (s_param >> 7) & 1, (s_param >> 6) & 1)

                    if self.debug : print(f"Tile {i} : {s_tileId} - {s_x} - {s_y}")
                    self.frame_sprite[s_is_foreground].blit(tile, (s_x * self.scale, (s_y - 1) * self.scale))

                    if i == 0: #chek for Sprint 0 Hit

                        pass

            # Update screen
            self.set_vblank()
            self.emulator.display.fill(PALETTE[self.emulator.memory.read_ppu_memory(0x3f00)]) # Couleur de fond transparene du backgroundaddress = 0x3f00 + (0x10 * is_sprite) + (0x4 * palette_address)
            x = self.x_scroll % 256
            y = self.y_scroll % 240
            pygame.draw.rect(self.frame_background, (255, 0, 0), pygame.Rect(x - 1, y - 1, x + 257, y + 241), 2)

            # To scale
            self.frame_sprite[0]  = pygame.transform.scale(self.frame_sprite[0],  (int(self.scale * 256), int(self.scale * 240)))
            self.frame_sprite[1]  = pygame.transform.scale(self.frame_sprite[1],  (int(self.scale * 256), int(self.scale * 240)))
            self.frame_background = pygame.transform.scale(self.frame_background, (int(self.scale * 256 * 2), int(self.scale * 240 * 2)))
            #Blit
            self.emulator.display.blit(self.frame_sprite[1], (x, y))
            self.emulator.display.blit(self.frame_background, (0, 0))
            self.emulator.display.blit(self.frame_sprite[0], (x, y))
            pygame.display.flip()

            #time.sleep(2)

            if (PPUCTRL >> 7) & 1:
                self.emulator.raise_nmi()
        elif (self.line, self.col) == (261, 3):
            self.clear_vblank()
            self.clear_sprite0_hit()

        elif (self.line, self.col) == (261, 280):
            PPUCTRL = self.getPPUCTRL()

            self.x_scroll = self.getPPUSCROLL() >> 8 + (256 * (PPUCTRL & 0b1))
            self.y_scroll = (self.getPPUSCROLL() & 0xff) + (240 * ((PPUCTRL >> 1 ) & 0b1))


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
        val = self.getPPUSTATUS()
        val |= 0b10000000
        self.setPPUSTATUS(val)
        pass

    def clear_vblank(self):
        val = self.getPPUSTATUS()
        val &= 0b11111111
        self.setPPUSTATUS(val)
        pass
    def set_sprite0_hit(self):
        val = self.getPPUSTATUS()
        val |= 0b01000000
        self.setPPUSTATUS(val)
        pass

    def clear_sprite0_hit(self):
        val = self.getPPUSTATUS()
        val &= 0b10111111
        self.setPPUSTATUS(val)
        pass

    def setPPUCTRL(self, val):
        """Set the PPUCTRL Register"""
        self.emulator.memory.write_rom(0x2000, val)

    def getPPUCTRL(self):
        """Returns the PPUCTRL Register"""
        return self.emulator.memory.read_rom(0x2000)

    def setPPUMASK(self, val):
        """Set the PPUMASK Register"""
        self.emulator.memory.write_rom(0x2001, val)

    def getPPUMASK(self):
        """Returns the PPUMASK Register"""
        return self.emulator.memory.read_rom(0x2001)

    def setPPUSTATUS(self, val):
        """Set the PPUUSTATUS Register"""
        self.emulator.memory.write_rom(0x2002, val)

    def getPPUSTATUS(self):
        """Returns the PPUUSTATUS Register"""
        return self.emulator.memory.read_rom(0x2002)

    def setPPU_OAMADDR(self, val):
        """Set the OAMADDR Register"""
        self.emulator.memory.write_rom(0x2003, val)

    def getPPU_OAMADDR(self):
        """Returns the OAMADDR Register"""
        return self.emulator.memory.read_rom(0x2003)

    def setPPU_OAMDATA(self, val):
        """Set the OAMDATA Register"""
        self.emulator.memory.write_rom(0x2004, val)

    def getPPU_OAMDATA(self):
        """Returns the OAMDATA Register"""
        return self.emulator.memory.read_rom(0x2004)

    def setPPUSCROLL(self, val):
        """Set the SCROLL Register"""
        self.emulator.memory.PPUSCROLL

    def getPPUSCROLL(self):
        """Returns the SCROLL Register"""
        return self.emulator.memory.PPUSCROLL

    def setPPUADDR(self, val):
        """Set the PPUADDR Register"""
        self.emulator.memory.write_rom(0x2006, val)

    def getPPUADDR(self):
        """Returns the PPUADDR Register"""
        return self.emulator.memory.read_rom(0x2006)

    def setPPUDATA(self, val):
        """Set the PPUDATA Register"""
        self.emulator.memory.write_rom(0x2007, val)

    def getPPUDATA(self):
        """Returns the PPUDATA Register"""
        return self.emulator.memory.read_rom(0x2007)

    def dump_chr(self):
        """ Display the tiles in CHR Memory. Useful for debugging."""
        print(len(self.emulator.cartridge.chr_rom)/16)
        c = 0
        x = 2
        y = 2
        for c in range(len(self.emulator.cartridge.chr_rom)//16):

            tile = self.create_tile(self.emulator.memory.getTile(0, c))
            tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
            self.emulator.display.blit(tile, (x, y))
            if (x +  10 * self.scale)  > 256 * self.scale:
                x = 2
                y += 10 * self.scale
            else :
                x += 10 * self.scale

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
            palette.append(PALETTE[self.emulator.memory.read_ppu_memory(address + 1)])
            palette.append(PALETTE[self.emulator.memory.read_ppu_memory(address + 2)])
            palette.append(PALETTE[self.emulator.memory.read_ppu_memory(address + 3)])
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
        print(f"{self.getPPUCTRL():08b} | {self.getPPUMASK():08b} | {self.getPPUSTATUS():08b}")
        print("")

    class PixelGenerator:
        '''This class implement the PPU pixel path, which generate the current pixel'''
        def __init__(self, ppu):
            self.ppu = ppu
            self.bg_palette_register = 0
            self.current_pattern_table_register = 0
            self.next_pattern_table_register = 0

        def compute_next_pixel(self):
            '''Compute the pixel to be displayed in current coordinates'''
            return (0, 255, 0, 255)

        def multiplexer_decision(self, bg_pixel, sprite_pixel, priority):
            '''Implement PPU Priority Multiplexer decision table'''
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
            pass

        def set_nt_byte(self, nt_byte):
            '''Set nt_byte into registers'''
            pass

        def set_at_byte(self, at_byte):
            '''Set at_byte into registers'''
            pass

        def set_low_bg_tile_byte(self, low_bg_tile_byte):
            '''Set low_bg_tile_byte into registers'''
            pass

        def set_high_bg_tile_byte(self, high_bg_tile_byte):
            '''Set high_bg_tile_byte into registers'''
            pass