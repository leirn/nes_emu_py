'''Singleton holders for main componentes.

This helps avoid circular module dependancies issues
'''

# Disabling invalid-name pylint control since it interprets variables as constants
# pylint: disable=C0103
# Disabling global-variable-undefined pylint control since pylint handles badly this specific 'singleton" architecture
# pylint: disable=W0601
def init():
    '''Trick to define global variable without circular dependancy issues'''
    global ppu, cpu, memory, cartridge, apu, nes, debug
    ppu = 0
    cpu = 0
    memory = 0
    cartridge = 0
    apu = 0
    nes = 0
    debug = 1
