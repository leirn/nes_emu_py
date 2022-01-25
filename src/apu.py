'''The emulator APU module'''

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    exit()

class apu:
    '''The emulator APU module class

    Args:
        emulator (nes_emulator): A reference to the emulator used to access memory or other components

    Attributes:
        emulator (emulator): A reference to the emulator used to access memory or other components
    '''
    def __init__(self, parent):
        self.emulator = emulator
