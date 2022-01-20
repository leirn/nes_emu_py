# http://users.telenet.be/kim1-6502/6502/proman.html#92

import cpu
import memory
import apu
import ppu
import inputs
import cartridge
import pygame
import traceback
from pygame.locals import *
import time
import cpu_opcodes
import re

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
    test_file = 0
    
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
        

    def start(self, entry_point = None):
        self.cpu.start(entry_point)
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
                                #is_frame |= self.ppu.next()
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
                                if event.key == K_UP: 		self.ctrl1.setUp()
                                elif event.key == K_DOWN: 	self.ctrl1.setDown()
                                elif event.key == K_LEFT: 	self.ctrl1.setLeft()
                                elif event.key == K_RIGHT: 	self.ctrl1.setRight()
                                elif event.key == K_RETURN: 	self.ctrl1.setStart()
                                elif event.key == K_ESCAPE: 	self.ctrl1.setSelect()
                                elif event.key == K_LCTRL: 	self.ctrl1.setA()
                                elif event.key == K_LALT: 	self.ctrl1.setB()
                                elif event.key == K_q: 		continuer = 0
                                elif event.key == K_p: 		self.togglePause()
                                elif event.key == K_s: 		
                                        self.print_status()
                                
                        elif event.type == KEYUP:
                                if event.key == K_UP: 		self.ctrl1.clearUp()
                                elif event.key == K_DOWN: 	self.ctrl1.clearDown()
                                elif event.key == K_LEFT:	self.ctrl1.clearLeft()
                                elif event.key == K_RIGHT: 	self.ctrl1.clearRight()
                                elif event.key == K_RETURN:     self.ctrl1.clearStart()
                                elif event.key == K_ESCAPE:     self.ctrl1.clearSelect()
                                elif event.key == K_LCTRL: 	self.ctrl1.clearA()
                                elif event.key == K_LALT: 	self.ctrl1.clearB()
                                
        
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
        
    def setTestMode(self, file_name):
        self.cpu.test_mode = 1
        self.test_file = file_name
        
    prev_opcode = -1
    def check_test(self, cpu_status):
        
        opcode = self.memory.read_rom(cpu_status["PC"])
        opcode_info = cpu_opcodes.opcodes[opcode]
        
        opcode_arg_1 = '  '
        opcode_arg_2 = '  '
        if cpu_opcodes.opcodes[opcode][2] > 1:
            opcode_arg_1 = f"{self.memory.read_rom(cpu_status['PC']+1):02x}"
        if cpu_opcodes.opcodes[opcode][2] > 2:
            opcode_arg_2 = f"{self.memory.read_rom(cpu_status['PC']+2):02x}"
        
        print(f"{cpu_status['PC']:x}  {opcode:02x} {opcode_arg_1} {opcode_arg_2}  {cpu_opcodes.opcodes[opcode][1]:30}  A:{cpu_status['A']:02x} X:{cpu_status['X']:02x} Y:{cpu_status['Y']:02x} P:{cpu_status['P']:02x} SP:{cpu_status['SP']:02x} PPU:{self.ppu.line}, {self.ppu.col} CYC:{cpu_status['CYC']}".upper())
    
        reference = self.test_file.readline()
        print(reference)
        self.memory.print_memory_page(self.memory.ROM, 0x0)
        print("")
        self.memory.print_memory_page(self.memory.ROM, 0x6)
        
        
        
        ref_status = dict()
        ref_status['PC'] = int(reference[0:4], 16)
        
        m = re.findall(r'A:(?P<A>[0-9A-Fa-f]{2}) X:(?P<X>[0-9A-Fa-f]{2}) Y:(?P<Y>[0-9A-Fa-f]{2}) P:(?P<P>[0-9A-Fa-f]{2}) SP:(?P<SP>[0-9A-Fa-f]{2})', reference)
        ref_status['A']  = int(m[0][0], 16)
        ref_status['X']  = int(m[0][1], 16)
        ref_status['Y']  = int(m[0][2], 16)
        ref_status['P']  = int(m[0][3], 16)
        ref_status['SP'] = int(m[0][4], 16)
        
        if ref_status['PC'] != cpu_status['PC'] or ref_status['A'] != cpu_status['A'] or ref_status['X'] != cpu_status['X']  or ref_status['Y'] != cpu_status['Y']  or ref_status['P'] != cpu_status['P']  or ref_status['SP'] != cpu_status['SP']: #  or ref_status['SP'] != cpu_status['SP']:
                raise Exception("ERROR !! ERROR !! ERROR !!")
        self.prev_opcode = opcode
        print("")
        
        pass