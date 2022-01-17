import pygame
from pygame.locals import *
from inputs import NESController1, NESController2
import traceback

import argparse
from cpu import cpu 
import ppu 
from memory import memory 
from cartridge import cartridge
import time

import cpu_opcodes

def print_status():
        cpu.print_status()
        ppu.print_status()
        memory.print_status()

parser = argparse.ArgumentParser("Parser")
parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'))

args = parser.parse_args()


pygame.init()
scale = 2
display = pygame.display.set_mode( (int(256 * scale), int(240 * scale)))

the_cartridge = cartridge()
the_cartridge.parse_rom(args.infile)
the_cartridge.print()


MEM = memory(the_cartridge)
CPU = cpu(MEM)
PPU = ppu.ppu(MEM, display)
CTRL1 = NESController1(MEM)

CPU.start()
FRAME_SIZE = 20 #cycles
cycles_left = FRAME_SIZE


continuer = 1
pause = 0

PPU.dump_chr()
pygame.display.update()
pygame.display.flip()
        
start_frame_time = time.time_ns()

FRAME_LENGHT_NS = 1/60 * 1000000000
frame_count = 0

# Useful to handle NMI interruption
is_nmi = False

while continuer:
        # Handle FRAME_SIZE cycles frames
        # 29780.5 CPU cycles per frame
        # NTSC : 60Hz
        # 
        if cycles_left < 0:
                cycles_left = FRAME_SIZE
        if not pause:
                #Check for NMI
                if is_nmi:
                        is_nmi = False
                        CPU.nmi()
                #Check for IRQ
                try:
                        #Execute next CPU instruction
                        CPU.next()
                        # 3 PPU dots per CPU cycles
                        is_frame = 0
                        is_frame |= PPU.next()
                        is_frame |= PPU.next()
                        is_frame |= PPU.next()
                except Exception as e:
                        print(e)	
                        CPU.print_status()
                        PPU.print_status()
                        MEM.print_status()
                        print(traceback.format_exc())
                        exit()
                if is_frame & ppu.FRAME_COMPLETED > 0:
                        current_time =  time.time_ns()
                        time_left = FRAME_LENGHT_NS - (current_time - start_frame_time)
                        if time_left > 0:
                                print(f"Frame {frame_count} finished, sleeep time : {time_left/1000000} ms")
                                frame_count += 1
                                time.sleep(time_left/1000000000)
                                start_frame_time = time.time_ns()
                elif is_frame & ppu.NMI > 0:
                        is_nmi = True
                
                #time.sleep(0.0001)
        
        # http://www.pygame.org/docs/ref/key.html
        for event in pygame.event.get():
                if event.type == QUIT:
                        continuer = 0
                elif event.type == KEYDOWN:
                        if event.key == K_UP: 			CTRL1.setUp()
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
                        if event.key == K_UP: 			CTRL1.clearUp()
                        elif event.key == K_DOWN: 	CTRL1.clearDown()
                        elif event.key == K_LEFT:		CTRL1.clearLeft()
                        elif event.key == K_RIGHT: 	CTRL1.clearRight()
                        elif event.key == K_RETURN: CTRL1.clearStart()
                        elif event.key == K_ESCAPE: CTRL1.clearSelect()
                        elif event.key == K_LCTRL: 	CTRL1.clearA()
                        elif event.key == K_LALT: 	CTRL1.clearB()
                        

        