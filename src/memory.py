import mappers
from utils import format_hex_data

class memory:
        mapper = ""
        mapper_name = 0
        ROM =           bytearray(b'\0' * 0x10000)
        PRG =           bytearray(b'\0' * 0x10000)
        VRAM =          bytearray(b'\0' * 0x2000)
        palette_VRAM = bytearray(b'\0' *  0x20)
        OAM =           bytearray(b'\0' * 0xFF)
        PPUADDR = 0
        OAMADDR = 0
        
        cartridge = b''
        
        ctrl1 = 0
        ctrl1_status = 0
        ctrl2 = 0
        ctrl2_status = 0
        
        
        def __init__(self, cartridge, ctrl1, ctrl2):
                self.cartridge = cartridge
                self.ctrl1 = ctrl1
                self.ctrl2 = ctrl2
                
                try:
                        module = __import__("mappers")
                        class_ = getattr(module, f"mapper{cartridge.mapper}")
                        self.mapper = class_(cartridge)
                        self.mapper_name = cartridge.mapper
                except Exception as e:
                        print(f"Unreconized mapper {cartridge.mapper}")
                        print(e)
                        exit()
                
        def getTile(self, bank, tile):
                print(f"{len(self.cartridge.chr_rom):x} - {tile} - {bank + 16 * tile:x}:{bank + 16 * tile + 16:x}")
                tile =  self.cartridge.chr_rom[bank + 16 * tile:bank + 16 * tile + 16]
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
                        value = self.ctrl1_status & 1
                        self.ctrl1_status = self.ctrl1_status >> 1
                        return value
                elif address == 0x4017: # Handling joystick
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
                        print(f"Illegal write to address 0x{format_hex_data(address)}")
                elif address >= 0x2000 and address < 0x4000:
                        address = 0x2000 + (address % 8)
                        if address == 0x2003:
                                self.OAMADDR = value
                        elif address == 0x2004:
                                self.OAM[self.OAMADDR] = value
                        elif address == 0x2006:
                                self.PPUADDR = ((self.PPUADDR << 8 ) + value ) & 0xffff
                        elif address == 0x2007:
                                print(f"0x{self.PPUADDR:x}")
                                self.write_ppu_memory_at_ppuaddr(value)
                        else:
                                self.ROM[address] = value
                        return 0
                elif address == 0x4014 : # OAMDMA
                        address = address << 8
                        self.OAM = bytearray(self.ROM[value << 8 :(value << 8) + 0x100])
                        return 514
                elif address == 0x4016: # Handling joystick
                        if value & 1 == 0:
                                # store joypad value
                                self.ctrl1_status = self.ctrl1.status
                                self.ctrl1_status = self.ctrl2.status
                elif address < 0x2000:
                        self.ROM[address % 0x800] = value
                else:
                        self.ROM[address] = value
                return 0 
                
                
        def read_ppu_memory_at_ppuaddr(self):
                        if self.PPUADDR < 0x2000:
                                return self.cartridge.prg_rom[self.PPUADDR] # CHR_ROM ADDRESS
                        elif self.PPUADDR < 0x3000: # VRAM
                                return self.VRAM[self.PPUADDR - 0x2000]
                        elif self.PPUADDR < 0x3F00: # VRAM mirror
                                return self.VRAM[self.PPUADDR - 0X3000]
                        elif address < 0x4000 : # palette
                                return self.palette_VRAM[self.PPUADDR % 0x20]
                        else:
                                raise Error("Out of PPU memory range")
                
                
        def read_ppu_memory(self, address):
                        if address < 0x2000:
                                return self.cartridge.prg_rom[address] # CHR_ROM ADDRESS
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
                                self.VRAM[self.PPUADDR - 0X3000] = value # - 0x1000 due to mirror + -0x2000 to reach start of VRAM
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