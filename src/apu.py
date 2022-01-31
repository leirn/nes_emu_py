'''The emulator APU module'''
import sys
import instances

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    sys.exit()

class Apu:
    '''The emulator APU module class

    Args:
        emulator (nes_emulator): A reference to the emulator used
        to access memory or other components

    Attributes:
        emulator (emulator): A reference to the emulator used to
        access memory or other components
    '''
    def __init__(self):
        pass

    def next(self):
        "Execute next APU cycle"
        pass
