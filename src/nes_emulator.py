import cpu
import memory
import apu
import ppu
import inputs
import cartridge
import pygame
import traceback
from pygame.locals import *

class nes_emulator:
    apu = 0
    cpu = 0
    ppu = 0
    memory = 0
    ctrl1 = 0
    ctrl2 = 0
    is_nmi = 0
    is_irq = 0
    cartridge  = 0
    scale = 0
    pause = 0
    clock = 0
    
    def __init__(self, cartridge_stream):
        pygame.init()
        self.scale = 2
        
        self.cartridge = cartridge.cartridge()
        self.cartridge.parse_rom(cartridge_stream)
        
        self.display = pygame.display.set_mode( (int(256 * self.scale), int(240 * self.scale)))
        
        self.ctrl1 = inputs.nes_controller()
        self.ctrl2 = inputs.nes_controller()
        self.memory = memory.memory(self)
        self.cpu = cpu.cpu(self)
        self.ppu = ppu.ppu(self)
        self.apu = apu.apu(self)
        
        self.clock = pygame.time.Clock()
        
        self.ppu.dump_chr()
        pygame.display.update()
        pygame.display.flip()
        

    def start(self):
        self.cpu.start()
        continuer = 1
        frame_count = 0

        while continuer:
                if not self.pause:
                        #Check for NMI
                        if self.is_nmi:
                                self.is_nmi = False
                                self.cpu.nmi()
                        if not self.cpu.flagI and self.is_irq: # Interrupt flag is ON
                                self.cpu.irq()
                        #Check for IRQ
                        try:
                                #Execute next CPU instruction
                                self.cpu.next()
                                # 3 PPU dots per CPU cycles
                                is_frame = 0
                                is_frame |= self.ppu.next()
                                is_frame |= self.ppu.next()
                                is_frame |= self.ppu.next()
                        except Exception as e:
                                print(e)	
                                self.print_status()
                                print(traceback.format_exc())
                                exit()
                        if is_frame & ppu.FRAME_COMPLETED > 0:
                                frame_count += 1
                                self.clock.tick(60)
                                print(f"FPS = {self.clock.get_fps()}")
                        
                        #time.sleep(0.0001)
                
                # http://www.pygame.org/docs/ref/key.html
                for event in pygame.event.get():
                        if event.type == QUIT:
                                continuer = 0
                        elif event.type == KEYDOWN:
                                if event.key == K_UP: 		CTRL1.setUp()
                                elif event.key == K_DOWN: 	CTRL1.setDown()
                                elif event.key == K_LEFT: 	CTRL1.setLeft()
                                elif event.key == K_RIGHT: 	CTRL1.setRight()
                                elif event.key == K_RETURN: 	CTRL1.setStart()
                                elif event.key == K_ESCAPE: 	CTRL1.setSelect()
                                elif event.key == K_LCTRL: 	CTRL1.setA()
                                elif event.key == K_LALT: 	CTRL1.setB()
                                elif event.key == K_q: 		continuer = 0
                                elif event.key == K_p: 		pause = 1 - pause
                                elif event.key == K_s: 		
                                        CPU.print_status()
                                        PPU.print_status()
                                        MEM.print_status()
                                
                        elif event.type == KEYUP:
                                if event.key == K_UP: 		CTRL1.clearUp()
                                elif event.key == K_DOWN: 	CTRL1.clearDown()
                                elif event.key == K_LEFT:	CTRL1.clearLeft()
                                elif event.key == K_RIGHT: 	CTRL1.clearRight()
                                elif event.key == K_RETURN:     CTRL1.clearStart()
                                elif event.key == K_ESCAPE:     CTRL1.clearSelect()
                                elif event.key == K_LCTRL: 	CTRL1.clearA()
                                elif event.key == K_LALT: 	CTRL1.clearB()
                                
        
    def reset(self):
        pass
        
    def resize(self):
        pass

    def print_status(self):
            self.cpu.print_status()
            self.ppu.print_status()
            self.memory.print_status()
            
    def togglePause(self):
        self.pause = 1 - self.pause
        
    def raise_nmi(self):
        self.is_nmi = 1
        
    def raise_irq(self):
        self.is_irq = 1