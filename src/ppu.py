import pygame
import time

NMI = 0b10
FRAME_COMPLETED = 0b1

class ppu:
        debug = 0
    
        emulator = ""
        scale = 2
        line = 0
        col = 0
        cycle = 0
        frame_count = 0
        
        cached_frame = ''
        frameParity = 0
        
        palette = [
                        (84,  84,  84, 255), 	(0,  30, 116, 255),	(8, 16, 144, 255),	(48, 0, 136, 255), 	(68, 0, 100, 255),  	(92, 0,  48, 255),   	(84, 4, 0, 255),   	(60, 24, 0, 255),   	(32, 42, 0, 255), 	(8, 58, 0, 255),    	(0, 64, 0, 255),    	(0, 60, 0, 255),    	(0, 50, 60, 255),    	(0,   0,   0, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
                        (152, 150, 152, 255),   (8,  76, 196, 255),   	(48, 50, 236, 255),   	(92, 30, 228, 255),  	(136, 20, 176, 255), 	(160, 20, 100, 255),  	(152, 34, 32, 255),  	(120, 60, 0, 255),   	(84, 90, 0, 255),   	(40, 114, 0, 255),    	(8, 124, 0, 255),    	(0, 118, 40, 255),    	(0, 102, 120, 255),    	(0,   0,   0, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
                        (236, 238, 236, 255),   (76, 154, 236, 255),  	(120, 124, 236, 255),  	(176, 98, 236, 255),  	(228, 84, 236, 255), 	(236, 88, 180, 255),  	(236, 106, 100, 255),  	(212, 136, 32, 255),  	(160, 170, 0, 255),  	(116, 196, 0, 255),   	(76, 208, 32, 255),   	(56, 204, 108, 255),   	(56, 180, 204, 255),   	(60,  60,  60, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
                        (236, 238, 236, 255),  	(168, 204, 236, 255),  	(188, 188, 236, 255),  	(212, 178, 236, 255),  	(236, 174, 236, 255),	(236, 174, 212, 255),  	(236, 180, 176, 255),  	(228, 196, 144, 255),  	(204, 210, 120, 255),  	(180, 222, 120, 255),  	(168, 226, 144, 255),  	(152, 226, 180, 255),  	(160, 214, 228, 255),  	(160, 162, 160, 255),	(0,   0,   0, 255),	(0,   0,   0, 255),
                ]
        
        def __init__(self, emulator):
                self.emulator = emulator	
                
                self.setPPUCTRL(0)
                self.setPPUMASK(0)
                self.setPPUSTATUS(0b10100000)
                self.setPPU_OAMADDR(0)
                self.setPPUSCROLL(0)
                self.setPPUADDR(0)
                self.setPPUDATA(0)
                
                self.col = 0
                self.line = 0
        
        # https://wiki.nesdev.org/w/index.php?title=PPU_registers
        # https://bugzmanov.github.io/nes_ebook/chapter_6_4.html
        def next(self):
                if self.line == 0 and self.col == 0:
                        self.frame_sprite = []
                        self.frame_background = pygame.Surface((256, 240), pygame.SRCALPHA, 32) # Le background
                        #self.frame_background = self.frame_background.convert_alpha()
                        self.frame_sprite.append(pygame.Surface(((256, 240)), pygame.SRCALPHA, 32)) # Les sprites derri�re le bg
                        #self.frame_sprite[0] = self.frame_sprite[0].convert_alpha()
                        self.frame_sprite.append(pygame.Surface(((256, 240)), pygame.SRCALPHA, 32)) # Les sprites devant le bg
                        #self.frame_sprite[1] = self.frame_sprite[1].convert_alpha()
                
                PPUCTRL = self.getPPUCTRL()
                PPUMASK = self.getPPUMASK()
                # Current nametable
                nametable = PPUCTRL & 0b11
                nametableAddress = {0 : 0x2000, 1 : 0x2400, 2 : 0x2800, 3 : 0x2C00}[nametable]
                backgroundPatternTableAddress = ((PPUCTRL >> 4) & 1) * 0x1000

                attribute_table = nametableAddress + 0x3C0

                # update background
                if (PPUMASK >>3) & 1 and self.line < 240 and self.col < 256 and self.col % 8 == 0 and self.line % 8 == 0 :	# Update pixel
                        
                        tileIndex = self.col // 8 + (32 * self.line // 8)

                        attribute_address = (self.line // 0x20) * 0x8 + (self.col // 0x20) # Attribut pour un bloc de 32x32
                        attribute =  self.emulator.memory.read_ppu_memory(attribute_table + attribute_address)

                        shift = (((self.col % 0x20) // 16) % 2) + ((((self.line % 0x20) // 16) % 2) << 1) # Une couleur par bloc de 16*16
                        color_palette = (attribute >> (shift * 2)) & 0b11
                                
                        #read background info in VRAM
                        bgTileIndex = self.emulator.memory.read_ppu_memory(nametableAddress + backgroundPatternTableAddress + tileIndex) 
                        if self.debug : print (f"Tile ID : {tileIndex} - Tile content : {bgTileIndex:x}")
                        
                        tileData = self.emulator.memory.getTile(backgroundPatternTableAddress, bgTileIndex)
                        tile = self.createTile(tileData, color_palette, 0)
                        #tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                        self.frame_background.blit(tile, (self.col, self.line))

                        print(f"Tile {tileIndex} : x : {self.col}, y : {self.line}, Color zone : {shift}, Palette : {color_palette}, attribute_adr = {attribute_address}, attribute = {attribute:08b}")

                
                self.col  = (self.col + 1) % 340
                                                
                if (self.line, self.col) == (241, 3):

                        if (PPUCTRL >> 5) & 1:
                            raise Exception("8x16 tiles are not supported yet")
                            
                        if (PPUMASK >>4) & 1  :  # Doit on afficher les sprites
                            # Display sprites
                            for i in range(64):
                                    sprite = self.emulator.memory.OAM[self.emulator.memory.OAMADDR + i * 4:self.emulator.memory.OAMADDR + i * 4 + 4]
                                    s_y = sprite[0]
                                    s_x = sprite[3]
                                    s_tileId = sprite[1]
                                    s_param = sprite[2]
                                    s_is_foreground = (s_param >> 5) & 1
                                    s_palette = s_param  & 3
                                    
                                    sprite_tile = self.emulator.memory.getTile(backgroundPatternTableAddress, s_tileId)
                                    tile = self.createTile(sprite_tile, s_palette, 1)
                                    tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                                    
                                    tile = pygame.transform.flip(tile, (s_param >> 7) & 1, (s_param >> 6) & 1)
                                    
                                    if self.debug : print(f"Tile {i} : {s_tileId} - {s_x} - {s_y}")
                                    self.frame_sprite[s_is_foreground].blit(tile, (s_x * self.scale, (s_y - 1) * self.scale))
                        
                                    if i == 0: #chek for Sprint 0 Hit
                                        
                                        pass

                        # Update screen
                        self.setVBlank()
                        self.emulator.display.fill((0, 0, 0))
                        # To scale
                        self.frame_sprite[0]  = pygame.transform.scale(self.frame_sprite[0], (int(self.scale * 256), int(self.scale * 240)))
                        self.frame_sprite[1]  = pygame.transform.scale(self.frame_sprite[1], (int(self.scale * 256), int(self.scale * 240)))
                        self.frame_background = pygame.transform.scale(self.frame_background, (int(self.scale * 256), int(self.scale * 240)))
                        #Blit
                        self.emulator.display.blit(self.frame_sprite[0], (0, 0))
                        self.emulator.display.blit(self.frame_background, (0, 0))
                        self.emulator.display.blit(self.frame_sprite[1], (0, 0))
                        pygame.display.flip()
                        
                        #time.sleep(2)
                        
                        if (PPUCTRL >> 7) & 1:
                                self.emulator.raise_nmi()
                elif (self.line, self.col) == (261, 3): 
                        self.clearVBlank()
                        self.clearSprite0Hit()
                
                
                if self.col == 0:
                        # End of scan line --> Sprite evaluation
                        self.line = (self.line + 1) 
                        
        
                        # End of frame
                        if self.line == 262:
                                self.line = 0
                                self.frameParity = 1 - self.frameParity
                                self.frame_count += 1
                                return FRAME_COMPLETED
                return 0

        # TODO : Vlbank status should be cleared after reading by CPU
        def setVBlank(self):
                val = self.getPPUSTATUS()
                val |= 0b10000000
                self.setPPUSTATUS(val)
                pass
                
        def clearVBlank(self):
                val = self.getPPUSTATUS()
                val &= 0b11111111
                self.setPPUSTATUS(val)
                pass
        def setSprite0Hit(self):
                val = self.getPPUSTATUS()
                val |= 0b01000000
                self.setPPUSTATUS(val)
                pass
                
        def clearSprite0Hit(self):
                val = self.getPPUSTATUS()
                val &= 0b10111111
                self.setPPUSTATUS(val)
                pass
        
        def setPPUCTRL(self, val):
                self.emulator.memory.write_rom(0x2000, val)

        def getPPUCTRL(self):
                return self.emulator.memory.read_rom(0x2000)
        
        def setPPUMASK(self, val):
                self.emulator.memory.write_rom(0x2001, val)

        def getPPUMASK(self):
                return self.emulator.memory.read_rom(0x2001)
        
        def setPPUSTATUS(self, val):
                self.emulator.memory.write_rom(0x2002, val)

        def getPPUSTATUS(self):
                return self.emulator.memory.read_rom(0x2002)
        
        def setPPU_OAMADDR(self, val):
                self.emulator.memory.write_rom(0x2003, val)

        def getPPU_OAMADDR(self):
                return self.emulator.memory.read_rom(0x2003)
        
        def setPPU_OAMDATA(self, val):
                self.emulator.memory.write_rom(0x2004, val)

        def getPPU_OAMDATA(self):
                return self.emulator.memory.read_rom(0x2004)
        
        def setPPUSCROLL(self, val):
                self.emulator.memory.write_rom(0x2005, val)

        def getPPUSCROLL(self):
                return self.emulator.memory.read_rom(0x2005)
        
        def setPPUADDR(self, val):
                self.emulator.memory.write_rom(0x2006, val)

        def getPPUADDR(self):
                return self.emulator.memory.read_rom(0x2006)
        
        def setPPUDATA(self, val):
                self.emulator.memory.write_rom(0x2007, val)

        def getPPUDATA(self):
                return self.emulator.memory.read_rom(0x2007)
                
        def dump_chr(self):
                print(len(self.emulator.cartridge.chr_rom)/16)
                c = 0
                x = 2
                y = 2
                for c in range(len(self.emulator.cartridge.chr_rom)//16):
                
                        tile = self.createTile(self.emulator.memory.getTile(0, c))
                        tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                        self.emulator.display.blit(tile, (x, y))
                        if (x +  10 * self.scale)  > 256 * self.scale:
                                x = 2
                                y += 10 * self.scale
                        else :
                                x += 10 * self.scale
                
        def createTile(self, array_of_byte, palette_address = -1, is_sprite = 0):
                surface = pygame.Surface((8, 8), pygame.SRCALPHA)

                palette = []
                if palette_address == -1:
                        palette.append((0, 0, 0, 0))
                        palette.append(self.palette[0x23])
                        palette.append(self.palette[0x27])
                        palette.append(self.palette[0x30])
                else:
                        address = 0x3f00 + (0x10 * is_sprite) + (0x4 * palette_address)
                        if is_sprite == 0: palette.append((0, 0, 0, 0))
                        else : 
                                palette.append(self.palette[self.emulator.memory.read_ppu_memory(address)])
                        palette.append(self.palette[self.emulator.memory.read_ppu_memory(address + 1)])
                        palette.append(self.palette[self.emulator.memory.read_ppu_memory(address + 2)])
                        palette.append(self.palette[self.emulator.memory.read_ppu_memory(address + 3)])
                for i in range(8):
                        for j in range(8):
                                bit1 = (array_of_byte[i] >> (7-j)) & 1
                                bit2 = (array_of_byte[8 + i] >> (7-j)) & 1
                                color_code = bit1 | (bit2 << 1)
                                surface.set_at((j, i), palette[color_code])
                                
                return surface
        
        def print_status(self):
                print("PPU")
                print("PPUCTRL  | PPUMASK  | PPUSTAT")
                print(f"{self.getPPUCTRL():08b} | {self.getPPUMASK():08b} | {self.getPPUSTATUS():08b}")
                print("")
                pass