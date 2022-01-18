import mappers
from utils import format_hex_data

class memory:
        debug = 0
        
        mapper = ""
        mapper_name = 0
        ROM =           bytearray(b'\0' * 0x10000)
        PRG =           bytearray(b'\0' * 0x10000)
        VRAM =          bytearray(b'\0' * 0x2000)
        palette_VRAM = bytearray(b'\0' *  0x20)
        OAM =           bytearray(b'\0' * 0x100)
        PPUADDR = 0
        OAMADDR = 0
        
        emulator = b''
        ctrl1_status = 0
        ctrl2_status = 0
        
        
        def __init__(self, emulator):
                self.emulator = emulator
                
                try:
                        module = __import__("mappers")
                        class_ = getattr(module, f"mapper{self.emulator.cartridge.mapper}")
                        self.mapper = class_(self.emulator.cartridge)
                        self.mapper_name = self.emulator.cartridge.mapper
                except Exception as e:
                        print(f"Unreconized mapper {self.emulator.cartridge.mapper}")
                        print(e)
                        exit()
                
        def getTile(self, bank, tile):
                if self.debug : print(f"{len(self.cartridge.chr_rom):x} - {tile} - {bank + 16 * tile:x}:{bank + 16 * tile + 16:x}")
                tile =  self.emulator.cartridge.chr_rom[bank + 16 * tile:bank + 16 * tile + 16]
                return tile
                        
        def read_rom(self, address):
                if address > 0x7FFF:
                        return self.mapper.read_rom(address)
                elif address < 0x2000: # RAM mirroring
                        return self.ROM[address % 0x800]
                elif address == 0x2007:
                        return self.read_ppu_memory_at_ppuaddr()
                elif address < 0x4000: # PPU mirroring
                        return self.ROM[0x2000 + (address % 0x8)]
                elif address == 0x4016: # Handling joystick
                        if self.debug : print(f"Joystick 1 read {self.ctrl1_status:b}")
                        value = self.ctrl1_status & 1
                        self.ctrl1_status = self.ctrl1_status >> 1
                        return value
                elif address == 0x4017: # Handling joystick
                        if self.debug : print(f"Joystick 1 read {self.ctrl1_status:b}")
                        value = self.ctrl2_status & 1
                        self.ctrl2_status = self.ctrl2_status >> 1
                        return value
                else:
                        return self.ROM[address]
        
        # NES is Little Endian
        def read_rom_16(self, address):
                if address > 0x7FFF:
                        low = self.mapper.read_rom(address)
                        high = self.mapper.read_rom(address+1)
                        return low + (high <<8)
                else:
                        low = self.ROM[address]
                        high = self.ROM[address+1]
                        return low + (high <<8)
        
        
        def write_rom(self, address, value):
                if address > 0x7FFF:
                        if self.debug : print(f"Illegal write to address 0x{format_hex_data(address)}")
                elif address >= 0x2000 and address < 0x4000:
                        address = 0x2000 + (address % 8)
                        if address == 0x2003:
                                self.OAMADDR = value
                        elif address == 0x2004:
                                self.OAM[self.OAMADDR] = value
                        elif address == 0x2006:
                                self.PPUADDR = ((self.PPUADDR << 8 ) + value ) & 0xffff
                        elif address == 0x2007:
                                self.write_ppu_memory_at_ppuaddr(value)
                        else:
                                self.ROM[address] = value
                        return 0
                elif address == 0x4014 : # OAMDMA
                        value = value << 8
                        self.OAM[self.OAMADDR:] = bytearray(self.ROM[value:value + 0x100])
                        if len(self.OAM) < 256:
                                raise Exception("OAM trop court")
                        return 514
                elif address == 0x4016: # Handling joystick
                        if self.debug : print(f"Joystick write {value:b}")
                        if value & 1 == 0:
                                # store joypad value
                                self.ctrl1_status = self.emulator.ctrl1.status
                                self.ctrl2_status = self.emulator.ctrl2.status
                                
                elif address < 0x2000:
                        self.ROM[address % 0x800] = value
                else:
                        self.ROM[address] = value
                return 0 
                
                
        def read_ppu_memory_at_ppuaddr(self):
                        if self.PPUADDR < 0x2000:
                                return self.cartridge.prg_rom[self.PPUADDR] # CHR_ROM ADDRESS
                        elif self.PPUADDR < 0x3000: # VRAM
                                val =  self.VRAM[self.PPUADDR - 0x2000]
                                self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
                                return val
                        elif self.PPUADDR < 0x3F00: # VRAM mirror
                                val =  self.VRAM[self.PPUADDR - 0X3000]
                                self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
                                return val
                        elif address < 0x4000 : # palette
                                return self.palette_VRAM[self.PPUADDR % 0x20]
                        else:
                                raise Error("Out of PPU memory range")
                
                
        def read_ppu_memory(self, address):
                        if address < 0x2000:
                                return self.emulator.xcartridge.prg_rom[address] # CHR_ROM ADDRESS
                        elif address < 0x3000: # VRAM
                                return self.VRAM[address - 0x2000]
                        elif address < 0x3F00: # VRAM mirror
                                return self.VRAM[address - 0X3000]
                        elif address < 0x4000 : # palette
                                return self.palette_VRAM[self.PPUADDR % 0x20]
                        else:
                                raise Error("Out of PPU memory range")
        
        def write_ppu_memory_at_ppuaddr(self, value):
                        if self.PPUADDR < 0x2000:
                                pass # CHR_ROM ADDRESS
                        elif self.PPUADDR < 0x3000: # VRAM
                                self.VRAM[self.PPUADDR - 0x2000] = value
                                VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
                                self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
                        elif self.PPUADDR < 0x3F00: # VRAM mirror
                                self.VRAM[self.PPUADDR - 0x3000] = value
                                VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
                                self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
                        else: # palette
                                self.palette_VRAM[self.PPUADDR % 0x20] = value
                
        def print_status(self):
                print("Memory status")
                print("OAMADDR\t| PPUADDR")
                print(f"{self.OAMADDR:x}\t| {format_hex_data(self.PPUADDR)}")
                print("")
                print("OAM")
                print(f"{' '.join([f'{i:02x}' for i in self.OAM])}")
                print("Zero Page")
                print(f"{' '.join([f'{i:02x}' for i in self.ROM[:0x100]])}")