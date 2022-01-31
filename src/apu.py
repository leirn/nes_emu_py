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
        self.registers = {
            # Default values that silences all channels at start
            0x4000 : 0x30,
            0x4001 : 0x08,
            0x4002 : 0x00,
            0x4003 : 0x00,
            0x4004 : 0x30,
            0x4005 : 0x08,
            0x4006 : 0x00,
            0x4007 : 0x00,
            0x4008 : 0x30,
            0x4009 : 0x08,
            0x400a : 0x00,
            0x400b : 0x00,
            0x400c : 0x30,
            0x400d : 0x08,
            0x400e : 0x00,
            0x400f : 0x00,
            0x4010 : 0x30,
            0x4011 : 0x08,
            0x4012 : 0x00,
            0x4013 : 0x00,
            0x4015 : 0x0f,
            0x4017 : 0x40,
        }

    def next(self):
        '''Execute next APU cycle'''
        pass

    def read_register(self, register):
        '''Read the register given as argument

        Args:
            Register address

        Returns:
            The value of the register
        '''
        return self.registers[register]

    def write_register(self, register, value):
        '''Write value in the given register

        Args:
            register -- the register address
            value  -- the value to set in the register
        '''
        self.registers[register] = value
