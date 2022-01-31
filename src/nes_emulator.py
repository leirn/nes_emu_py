'''The emulator main engine'''

# http://users.telenet.be/kim1-6502/6502/proman.html#92
import sys
import time
import traceback
import re
import pygame
import instances
import inputs
import utils
from cpu_opcodes import OPCODES

class NesEmulator:
    '''Main class handling the whole emulator execution

    Arg:
        cartridge_stream - Cartridge stream to be read in order to load the cartridge
    '''

    def __init__(self):
        self.is_nmi = 0
        self.is_irq = 0
        self.pause = 0
        self.test_file = 0
        self.test_mode = 0

        pygame.init()
        self.scale = 2

        self.display = pygame.display.set_mode( (int(256 * self.scale), int(240 * self.scale)))
        self.display.fill((0, 0, 0))

        self.ctrl1 = inputs.NesController()
        self.ctrl2 = inputs.NesController()

        self.clock = pygame.time.Clock()

        self.apu_toggler = 0

        pygame.display.update()
        pygame.display.flip()


    def start(self, entry_point = None):
        '''Starts the Emulator execution'''
        instances.cpu.start(entry_point)
        instances.ppu.next()
        instances.ppu.next()
        instances.ppu.next()
        continuer = 1
        frame_count = 0

        while continuer:
            if not self.pause:
                #Check for NMI
                if self.is_nmi:
                    self.is_nmi = False
                    instances.cpu.nmi()
                if not instances.cpu.interrupt and self.is_irq: # Interrupt flag is ON
                    instances.cpu.irq()
                #Check for IRQ
                try:
                    #Execute next CPU instruction
                    instances.cpu.next()
                    # Execute next APU instruction
                    if self.apu_toggler : instances.apu.next()
                    self.apu_toggler = 1 - self.apu_toggler
                    # 3 PPU dots per CPU cycles
                    is_frame = 0
                    is_frame |= instances.ppu.next()
                    is_frame |= instances.ppu.next()
                    is_frame |= instances.ppu.next()
                except Exception as exception:
                    print(exception)
                    self.print_status()
                    print(traceback.format_exc())
                    sys.exit()

                if self.test_mode == 1 and instances.cpu.remaining_cycles == 0: self.check_test(instances.cpu.get_cpu_status())

                if is_frame :
                    frame_count += 1
                    self.clock.tick(60)
                    print(f"FPS = {self.clock.get_fps()}")

                #time.sleep(0.01)

            # http://www.pygame.org/docs/ref/key.html
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    continuer = 0
                elif event.type == pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_UP: 		self.ctrl1.set_up()
                        case pygame.K_DOWN: 	self.ctrl1.set_down()
                        case pygame.K_LEFT: 	self.ctrl1.set_left()
                        case pygame.K_RIGHT: 	self.ctrl1.set_right()
                        case pygame.K_RETURN:   self.ctrl1.set_start()
                        case pygame.K_ESCAPE:   self.ctrl1.set_select()
                        case pygame.K_LCTRL: 	self.ctrl1.set_a()
                        case pygame.K_LALT: 	self.ctrl1.set_b()
                        case pygame.K_q: 		continuer = 0
                        case pygame.K_p: 		self.toggle_pause()
                        case pygame.K_s:        self.print_status()

                elif event.type == pygame.KEYUP:
                    match event.key:
                        case pygame.K_UP: 		self.ctrl1.clear_up()
                        case pygame.K_DOWN: 	self.ctrl1.clear_down()
                        case pygame.K_LEFT:	    self.ctrl1.clear_left()
                        case pygame.K_RIGHT: 	self.ctrl1.clear_right()
                        case pygame.K_RETURN:   self.ctrl1.clear_start()
                        case pygame.K_ESCAPE:   self.ctrl1.clear_select()
                        case pygame.K_LCTRL: 	self.ctrl1.clear_a()
                        case pygame.K_LALT: 	self.ctrl1.clear_b()

    def reset(self):
        '''Reset the emulator

        TODO : Implement the functionnality
        '''

    def resize(self):
        '''Resize the diplay

        TODO : Implement the functionnality
        '''

    def print_status(self):
        '''Display Emulator status'''
        instances.cpu.print_status()
        instances.ppu.print_status()
        instances.memory.print_status()
        instances.cartridge.print_status()

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
        instances.cpu.test_mode = 1
        self.test_file = file_name


    def check_test(self, cpu_status):
        ''' Performs test execution against reference execution log to find descrepancies'''
        opcode = instances.memory.read_rom(cpu_status["PC"])

        opcode_arg_1 = '  '
        opcode_arg_2 = '  '
        if OPCODES[opcode][2] > 1:
            opcode_arg_1 = f"{instances.memory.read_rom(cpu_status['PC']+1):02x}"
        if OPCODES[opcode][2] > 2:
            opcode_arg_2 = f"{instances.memory.read_rom(cpu_status['PC']+2):02x}"

        print(f"{cpu_status['PC']:x}  {opcode:02x} {opcode_arg_1} {opcode_arg_2}  {OPCODES[opcode][1]:30}  A:{cpu_status['A']:02x} X:{cpu_status['X']:02x} Y:{cpu_status['Y']:02x} P:{cpu_status['P']:02x} SP:{cpu_status['SP']:02x} PPU:{instances.ppu.line}, {instances.ppu.col} CYC:{cpu_status['CYC']}".upper())

        reference = self.test_file.readline()

        if reference == "":
            print("Test file completed")
            sys.exit()

        print(reference)
        utils.print_memory_page(instances.memory.ROM, 0x0)
        utils.print_memory_page(instances.memory.ROM, 0x6)

        ref_status = dict()
        ref_status['PC'] = int(reference[0:4], 16)

        match = re.findall(r'A:(?P<A>[0-9A-Fa-f]{2}) X:(?P<X>[0-9A-Fa-f]{2}) Y:(?P<Y>[0-9A-Fa-f]{2}) P:(?P<P>[0-9A-Fa-f]{2}) SP:(?P<SP>[0-9A-Fa-f]{2})', reference)
        ref_status['A']  = int(match[0][0], 16)
        ref_status['X']  = int(match[0][1], 16)
        ref_status['Y']  = int(match[0][2], 16)
        ref_status['P']  = int(match[0][3], 16)
        ref_status['SP'] = int(match[0][4], 16)
        match = re.findall(r'CYC:(?P<A>[0-9A-Fa-f]+)', reference)
        ref_status['CYC']  = int(match[0])
        match = re.findall(r'PPU:[ ]*([0-9]+),[ ]*([0-9]+)', reference)
        ref_status['PPU_LINE']  = int(match[0][0])
        ref_status['PPU_COL']  = int(match[0][1])

        for i in ["PC", "A", "X", "Y", "P", "SP"]: # On hold : CYC, PPU_LINE, PPU_COL
            if ref_status[i] != cpu_status[i] :
                raise Exception(f"{i} Error : {cpu_status[i]} instead of {ref_status[i]}")
        print("")