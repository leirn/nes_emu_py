'''Emulator inputs classes'''

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

class NesController:
    status = 0

    def __init__(self):
        pass

    def setA(self):
        self.status |= 1

    def clearA(self):
        self.status &= 0b11111110

    def setB(self):
        self.status |= 0b10

    def clearB(self):
        self.status &= 0b11111101

    def setSelect(self):
        self.status |= 0b100

    def clearSelect(self):
        self.status &= 0b11111011

    def setStart(self):
        self.status |= 0b1000

    def clearStart(self):
        self.status &= 0b11110111

    def setUp(self):
        self.status |= 0b10000

    def clearUp(self):
        self.status &= 0b11101111

    def setDown(self):
        self.status |= 0b100000

    def clearDown(self):
        self.status &= 0b11011111

    def setLeft(self):
        self.status |= 0b1000000

    def clearLeft(self):
        self.status &= 0b10111111

    def setRight(self):
        self.status |= 0b10000000

    def clearRight(self):
        self.status &= 0b01111111