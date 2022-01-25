'''Cartridge module'''

# Preventing direct execution
if __name__ == '__main__':
    print("This module cannot be executed. Please use main.py")
    exit()


# https://formats.kaitai.io/ines/

class cartridge:
    # HEADER
    title = b''
    header = b''
    magic = b''
    prg_rom_size = 0
    chr_rom_size = 0
    prg_ram_size = 0
    f6 = b''
    f7 = b''
    f9 = b''
    f10 = b''
    mapper = 0
    
    #TRAINER
    is_trainer = False
    trainer = b''
    
    #PRG_ROM
    prg_rom = b''
    
    #CHR_ROM
    chr_rom = b''
    
    #PLAY_CHOISE_10
    is_playchoice = False
    playchoice = b''
    
    #TITLE
    header = b''

    def parse_rom(self, stream):
        self.header = stream.read(16)
        self.parse_header()
        
        if self.is_trainer:
            self.trainer = stream.read(512)
            
        self.prg_rom = bytearray(stream.read(self.prg_rom_size))
        
        self.chr_rom = bytearray(stream.read(self.chr_rom_size))
        if self.is_playchoice:
            self.playchoice = stream.read(8224)
        self.title = stream.read()
        
    def parse_header(self):
        h = self.header
        self.magic = h[0:4]
        print(h[5])
        self.prg_rom_size = h[4] * 16 * 1024
        self.chr_rom_size = h[5] * 8 * 1024
        self.f6 = h[6]
        self.is_trainer = self.f6 & 0x1000
        self.f7= h[7]
        self.is_playchoice = self.f6 & 0x100
        self.prg_ram_size= h[8] * 8 * 1024
        self.f9= h[9]
        self.f10= h[10]
        
        self.mapper = (self.f7 & 0x11110000) + ((self.f6 & 0x11110000) >> 4)

    def disas(self):
        global opcodes
        pc = int.from_bytes(self.prg_rom[0x7ffc:0x7ffc+2], "big")
        print("DISASSEMBLY")
        for i in range(1000):
            try:
                print(f"0x{pc:x} : 0x{self.prg_rom[pc]:x} : {opcodes[self.prg_rom[pc]]}")
                pc += opcodes[self.prg_rom[pc]][2]
            except Exception as e:
                print(f"Opcode not found : 0x{self.prg_rom[pc]:x}")
                break
            
        

    def print(self):
        print(self.title)
        print(self.header)
        print(self.magic)
        print(f"Trainer present : {self.is_trainer}")
        print(f"PRG_ROM Size : {self.prg_rom_size//1024} kB")
        print(f"CHR_ROM Size : {self.chr_rom_size//1024} kB")
        print(f"PRG_RAM Size : {self.prg_ram_size//1024} kB")
        print(f"Mapper : {self.mapper}")
        print(f"Entry point : {self.prg_rom[0x7ffc:0x7ffc+2]}")
