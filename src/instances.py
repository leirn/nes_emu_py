def init():
    '''Trick to define global variable without circular dependancy issues'''
    global ppu, cpu, memory, cartridge, apu, nes, debug
    ppu = 0
    cpu = 0
    memory = 0
    cartridge = 0
    apu = 0
    nes = 0
    debug = 0
