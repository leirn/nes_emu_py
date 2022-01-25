'''The emulator main engine'''

# http://users.telenet.be/kim1-6502/6502/proman.html#92

import time
import traceback
import re
import pygame
from pygame.locals import *
import cpu
import memory
import apu
import ppu
import inputs
import cartridge
from cpu_opcodes import OPCODES

class NesEmulator:
    '''Main class handling the whole emulator execution

    Arg:
        cartridge_stream - Cartridge stream to be read in order to load the cartridge
    '''

    def __init__(self, cartridge_stream):
        self.is_nmi = 0
        self.is_irq = 0
        self.pause = 0
        self.test_file = 0
        self.test_mode = 0

        pygame.init()
        self.scale = 2

        self.cartridge = cartridge.Cartridge()
        self.cartridge.parse_rom(cartridge_stream)

        self.display = pygame.display.set_mode( (int(256 * self.scale * 2), int(240 * self.scale * 2)))
        self.display.fill((0, 0, 0))

        self.ctrl1 = inputs.NesController()
        self.ctrl2 = inputs.NesController()
        self.memory = memory.Memory(self)
        self.cpu = cpu.Cpu(self)
        self.ppu = ppu.Ppu(self)
        self.apu = apu.Apu(self)

        self.clock = pygame.time.Clock()

        self.ppu.dump_chr()
        pygame.display.update()
        pygame.display.flip()


    def start(self, entry_point = None):
        '''Starts the Emulator execution'''
        self.cpu.start(entry_point)
        self.ppu.next()
        self.ppu.next()
        self.ppu.next()
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

                if self.test_mode == 1 and self.cpu.remaining_cycles == 0: self.check_test(self.cpu.get_cpu_status())

                if is_frame & ppu.FRAME_COMPLETED > 0:
                    frame_count += 1
                    self.clock.tick(60)
                    print(f"FPS = {self.clock.get_fps()}")

                #time.sleep(0.01)

            # http://www.pygame.org/docs/ref/key.html
            for event in pygame.event.get():
                if event.type == QUIT:
                    continuer = 0
                elif event.type == KEYDOWN:
                    if event.key == K_UP: 		self.ctrl1.set_up()
                    elif event.key == K_DOWN: 	self.ctrl1.set_down()
                    elif event.key == K_LEFT: 	self.ctrl1.set_left()
                    elif event.key == K_RIGHT: 	self.ctrl1.set_right()
                    elif event.key == K_RETURN: self.ctrl1.set_start()
                    elif event.key == K_ESCAPE: self.ctrl1.set_select()
                    elif event.key == K_LCTRL: 	self.ctrl1.set_a()
                    elif event.key == K_LALT: 	self.ctrl1.set_b()
                    elif event.key == K_q: 		continuer = 0
                    elif event.key == K_p: 		self.toggle_pause()
                    elif event.key == K_s:      self.print_status()

                elif event.type == KEYUP:
                    if event.key == K_UP: 		self.ctrl1.clear_up()
                    elif event.key == K_DOWN: 	self.ctrl1.clear_down()
                    elif event.key == K_LEFT:	self.ctrl1.clear_left()
                    elif event.key == K_RIGHT: 	self.ctrl1.clear_right()
                    elif event.key == K_RETURN: self.ctrl1.clear_start()
                    elif event.key == K_ESCAPE: self.ctrl1.clear_select()
                    elif event.key == K_LCTRL: 	self.ctrl1.clear_a()
                    elif event.key == K_LALT: 	self.ctrl1.clear_b()

    def reset(self):
        '''Reset the emulator

        TODO : Implement the functionnality
        '''
        pass

    def resize(self):
        '''Resize the diplay

        TODO : Implement the functionnality
        '''
        pass

    def print_status(self):
        '''Display Emulator status'''
        self.cpu.print_status()
        self.ppu.print_status()
        self.memory.print_status()
        self.cartidge.print_status()

    def toggle_pause(self):
        '''Toggle pause on the emulator execution'''
        self.pause = 1 - self.pause

    def raise_nmi(self):
        '''Raises an NMI interrup'''
        self.is_nmi = 1

    def raise_irq(self):
        '''Raises an IRQ interrup'''
        self.is_irq = 1

    def set_test_mode(self, file_name):
        '''Activate test mode and set the execution reference file'''
        self.test_mode = 1
        self.cpu.test_mode = 1
        self.test_file = file_name


    def check_test(self, cpu_status):
        ''' Performs test execution against reference execution log to find descrepancies'''
        opcode = self.memory.read_rom(cpu_status["PC"])

        opcode_arg_1 = '  '
        opcode_arg_2 = '  '
        if OPCODES[opcode][2] > 1:
            opcode_arg_1 = f"{self.memory.read_rom(cpu_status['PC']+1):02x}"
        if OPCODES[opcode][2] > 2:
            opcode_arg_2 = f"{self.memory.read_rom(cpu_status['PC']+2):02x}"

        print(f"{cpu_status['PC']:x}  {opcode:02x} {opcode_arg_1} {opcode_arg_2}  {OPCODES[opcode][1]:30}  A:{cpu_status['A']:02x} X:{cpu_status['X']:02x} Y:{cpu_status['Y']:02x} P:{cpu_status['P']:02x} SP:{cpu_status['SP']:02x} PPU:{self.ppu.line}, {self.ppu.col} CYC:{cpu_status['CYC']}".upper())

        reference = self.test_file.readline()

        if reference == "":
            print("Test file completed")
            exit()

        print(reference)
        self.memory.print_memory_page(self.memory.ROM, 0x0)
        self.memory.print_memory_page(self.memory.ROM, 0x6)

        ref_status = dict()
        ref_status['PC'] = int(reference[0:4], 16)

        m = re.findall(r'A:(?P<A>[0-9A-Fa-f]{2}) X:(?P<X>[0-9A-Fa-f]{2}) Y:(?P<Y>[0-9A-Fa-f]{2}) P:(?P<P>[0-9A-Fa-f]{2}) SP:(?P<SP>[0-9A-Fa-f]{2})', reference)
        ref_status['A']  = int(m[0][0], 16)
        ref_status['X']  = int(m[0][1], 16)
        ref_status['Y']  = int(m[0][2], 16)
        ref_status['P']  = int(m[0][3], 16)
        ref_status['SP'] = int(m[0][4], 16)
        m = re.findall(r'CYC:(?P<A>[0-9A-Fa-f]+)', reference)
        ref_status['CYC']  = int(m[0])
        m = re.findall(r'PPU:[ ]*([0-9]+),[ ]*([0-9]+)', reference)
        ref_status['PPU_LINE']  = int(m[0][0])
        ref_status['PPU_COL']  = int(m[0][1])

        for i in ["PC", "A", "X", "Y", "P", "SP"]: # On hold : CYC, PPU_LINE, PPU_COL
            if ref_status[i] != cpu_status[i] :
                raise Exception(f"{i} Error : {cpu_status[i]} instead of {ref_status[i]}")

        self.prev_opcode = opcode
        print("")