import pygame
import numpy as np
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
        
        cached_frame = ''
        frameParity = 0
        
        palette = [
                        [84,  84,  84], 	[0,  30, 116],		[8, 16, 144],		[48, 0, 136], 		[68, 0, 100],  		[92, 0,  48],   	[84, 4, 0],   		[60, 24, 0],   		[32, 42, 0], 		[8, 58, 0],    		[0, 64, 0],    		[0, 60, 0],    		[0, 50, 60],    	[0,   0,   0],		[0,   0,   0],		[0,   0,   0],
                        [152, 150, 152],   	[8,  76, 196],   	[48, 50, 236],   	[92, 30, 228],  	[136, 20, 176], 	[160, 20, 100],  	[152, 34, 32],  	[120, 60, 0],   	[84, 90, 0],   		[40, 114, 0],    	[8, 124, 0],    	[0, 118, 40],    	[0, 102, 120],    	[0,   0,   0],		[0,   0,   0],		[0,   0,   0],
                        [236, 238, 236],    [76, 154, 236],  	[120, 124, 236],  	[176, 98, 236],  	[228, 84, 236], 	[236, 88, 180],  	[236, 106, 100],  	[212, 136, 32],  	[160, 170, 0],  	[116, 196, 0],   	[76, 208, 32],   	[56, 204, 108],   	[56, 180, 204],   	[60,  60,  60],		[0,   0,   0],		[0,   0,   0],
                        [236, 238, 236],  	[168, 204, 236],  	[188, 188, 236],  	[212, 178, 236],  	[236, 174, 236],	[236, 174, 212],  	[236, 180, 176],  	[228, 196, 144],  	[204, 210, 120],  	[180, 222, 120],  	[168, 226, 144],  	[152, 226, 180],  	[160, 214, 228],  	[160, 162, 160],	[0,   0,   0],		[0,   0,   0],
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
                        self.cached_frame = pygame.Surface((int(self.scale * 256), int(self.scale * 240))) # il faudrait recréer une nouvelle frame en cache
                        # Parcourir les 
                
                PPUCTRL = self.getPPUCTRL()
                PPUMASK = self.getPPUMASK()
                # Current nametable
                nametable = PPUCTRL & 0b11
                nametableAddress = {0 : 0x2000, 1 : 0x2400, 2 : 0x2800, 3 : 0x2C00}[nametable]
                backgroundPatternTableAddress = ((PPUCTRL >> 4) & 1) * 0x1000
                # update background
                if (PPUMASK >>3) & 1 and self.line < 240 and self.col < 256 and self.col % 8 == 0 and self.line % 8 == 0 :	# Update pixel
                        
                        
                        tileIndex = self.col // 8 + (32 * self.line // 8)
                                
                        #read background info in VRAM
                        bgTileIndex = self.emulator.memory.read_ppu_memory(0x2000 + backgroundPatternTableAddress + tileIndex) # 0x2000 to aligne with VRAM start
                        if self.debug : print (f"Tile ID : {tileIndex} - Tile content : {bgTileIndex:x}")
                        
                        tileData = self.emulator.memory.getTile(backgroundPatternTableAddress, bgTileIndex)
                        tile = self.createTile(tileData)
                        tile = pygame.surfarray.make_surface(tile)
                        tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                        self.cached_frame.blit(tile, (self.col * self.scale, self.line * self.scale))
                
                self.col  = (self.col + 1) % 340
                                                
                if (self.line, self.col) == (241, 3):

                        if (PPUCTRL >> 5) & 1:
                            raise Exception("8x16 tiles are not supported yet")
                            
                        if (PPUMASK >>4) & 1  :  # Doit on afficher les sprites
                            # Display sprites
                            for i in range(64):
                                    sprite = self.emulator.memory.OAM[self.memory.OAMADDR + i * 4:self.memory.OAMADDR + i * 4 + 4]
                                    s_y = sprite[0]
                                    s_x = sprite[3]
                                    s_tileId = sprite[1]
                                    s_param = sprite[2]
                                    
                                    sprite_tile = self.emulator.memory.getTile(backgroundPatternTableAddress, s_tileId)
                                    tile = self.createTile(sprite_tile)
                                    tile = pygame.surfarray.make_surface(tile)
                                    tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                                    
                                    tile = pygame.transform.flip(tile, (s_param >> 7) & 1, (s_param >> 6) & 1)
                                    
                                    if self.debug : print(f"Tile {i} : {s_tileId} - {s_x} - {s_y}")
                                    self.cached_frame.blit(tile, (s_x * self.scale, (s_y - 1) * self.scale))
                        
                        # Update screen
                        self.setVBlank()
                        '''
                        tile = pygame.surfarray.make_surface(self.cachedFrame)
                        tile = pygame.transform.scale(tile, (int(256 * self.scale), int(240 * self.scale)))
                        self.display.blit(tile, (0, 0))
                        '''
                        self.display.blit(self.cached_frame, (0, 0))
                        pygame.display.update()
                        pygame.display.flip()
                        
                        time.sleep(2)
                        
                        if (PPUCTRL >> 7) & 1:
                                self.emulator.raise_nmi()
                        return 0
                elif (self.line, self.col) == (261, 3): 
                        self.clearVBlank()
                
                
                if self.col == 0:
                        # End of scan line --> Sprite evaluation
                        self.line = (self.line + 1) 
                        
        
                # End of frame
                if self.line == 262:
                        self.line = 0
                        self.frameParity = 1 - self.frameParity
                        return FRAME_COMPLETED
                return 0

        def setVBlank(self):
                # TODO : To be implemented to update PPUCTRL
                pass
                
        def clearVBlank(self):
                # TODO : To be implemented to update PPUCTRL
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
                print(len(self.emulator.memory.cartridge.chr_rom)/16)
                
                ar = self.createTile(self.emulator.memory.cartridge.chr_rom[:16])
                tile = pygame.surfarray.make_surface(ar)
                
                c = 0
                x = 2
                y = 2
                for c in range(len(self.emulator.memory.cartridge.chr_rom)//16):
                
                        ar = self.createTile(self.memory.getTile(0, c))
                        tile = pygame.surfarray.make_surface(ar)
                        tile = pygame.transform.scale(tile, (int(8 * self.scale), int(8 * self.scale)))
                        self.emulator.display.blit(tile, (x, y))
                        x += 10 * self.scale
                        if x > 256 * self.scale:
                                x = 1
                                y += 10 * self.scale

                
        def createTile(self, array_of_byte):
                a = [[0,   0,   0]] * 8
                a = [a] * 8
                a = np.array([[(0, 0, 0) for x in range(8)] for y in range(8)])
                for i in range(8):
                        for j in range(8):
                                bit1 = (array_of_byte[i] >> (7-j)) & 1
                                bit2 = (array_of_byte[8 + i] >> (7-j)) & 1
                                
                                color_code = bit1 | (bit2 << 1)
                                if color_code == 0:
                                        a[j][i] = self.palette[1]
                                elif color_code == 1:
                                        a[j][i] = self.palette[0x23]
                                elif color_code == 2:
                                        a[j][i] = self.palette[0x27]
                                elif color_code == 3:
                                        a[j][i] = self.palette[0x30]
                                
                return a
        
        def print_status(self):
                print("PPU")
                print("PPUCTRL  | PPUMASK  | PPUSTAT")
                print(f"{self.getPPUCTRL():b} | {self.getPPUMASK():b} | {self.getPPUSTATUS():b}")
                print("")
                pass