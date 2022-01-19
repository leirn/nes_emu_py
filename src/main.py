__description__ = 'YaNESEmu'
__author__ = 'Laurent Vromman'
__version__ = '0.0.0'
__date__ = '2022/01/19'

import sys
import optparse
import nes_emulator

import cpu_opcodes

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
emulator = nes_emulator.nes_emulator(open(args[0], 'rb'))

if options.test_file:
    emulator.setTestMode(open(options.test_file, 'r'))
    emulator.start(0xC000)
else:
    emulator.start()