'''Emulator inputs classes'''

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

class NesController:
    '''Class to handle Input controllers

    Var:
        Status is a one byte status of the controller
    '''
    def __init__(self):
        self.status = 0

    def set_a(self):
        '''Set when A button is press'''
        self.status |= 1

    def clear_a(self):
        '''Clear when A button is released'''
        self.status &= 0b11111110

    def set_b(self):
        '''Set when B button is press'''
        self.status |= 0b10

    def clear_b(self):
        '''Clear when B button is released'''
        self.status &= 0b11111101

    def set_select(self):
        '''Set when Select button is press'''
        self.status |= 0b100

    def clear_select(self):
        '''Clear when Select button is released'''
        self.status &= 0b11111011

    def set_start(self):
        '''Set when Start button is press'''
        self.status |= 0b1000

    def clear_start(self):
        '''Clear when Start button is released'''
        self.status &= 0b11110111

    def set_up(self):
        '''Set when Up button is press'''
        self.status |= 0b10000

    def clear_up(self):
        '''Clear when Up button is released'''
        self.status &= 0b11101111

    def set_down(self):
        '''Set when Down button is press'''
        self.status |= 0b100000

    def clear_down(self):
        '''Clear when Down button is released'''
        self.status &= 0b11011111

    def set_left(self):
        '''Set when Left button is press'''
        self.status |= 0b1000000

    def clear_left(self):
        '''Clear when Left button is released'''
        self.status &= 0b10111111

    def set_right(self):
        '''Set when Right button is press'''
        self.status |= 0b10000000

    def clear_right(self):
        '''Clear when Right button is released'''
        self.status &= 0b01111111
