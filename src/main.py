''' Main program entry module'''

__description__ = 'YaNESEmu'
__author__ = 'Laurent Vromman'
__version__ = '0.0.0'
__date__ = '2022/01/19'

import sys
import optparse
from nes_emulator import NesEmulator
from ppu import Ppu
from cpu import Cpu
from apu import Apu
from memory import Memory
from cartridge import Cartridge
import instances
import debug

arguments = sys.argv[1:]

oParser = optparse.OptionParser(usage='usage: %prog [options] Rom_filename\n' + __description__, version='%prog ' + __version__)
oParser.add_option('-t', '--test_log', type="str", default=None, help='Activate test mode and set est log file', action="store", dest="test_file")

(options, args) = oParser.parse_args(arguments)

'''
parser = argparse.ArgumentParser("Parser")
parser.add_argument('infile', type=argparse.FileType('rb'), help="Rom file")
parser.add_argument('-t test_file', type=argparse.FileType('r'), required = False, help="Test log file. This option activates the test mode")
# Add force entry point and test mode

args = parser.parse_args()
'''

instances.init()
instances.memory = Memory()
instances.ppu = Ppu()
instances.cpu = Cpu()
instances.apu = Apu()
instances.cartridge = Cartridge()
instances.nes = NesEmulator()
instances.cartridge.parse_rom(args[0])

debug.dump_chr()

if options.test_file:
    instances.nes.set_test_mode(open(options.test_file, 'r'))
    instances.nes.start(0xC000)
else:
    instances.nes.start()
