
import traceback

import argparse
import nes_emulator
import time

import cpu_opcodes

parser = argparse.ArgumentParser("Parser")
parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'))

args = parser.parse_args()

emulator = nes_emulator.nes_emulator(args.infile)

emulator.start()