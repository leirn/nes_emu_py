import mappers


class memory:
	mapper = ""
	mapper_name = 0
	ROM = bytearray(b'0' * 0x10000)
	PRG = bytearray(b'0' * 0x10000)
	VRAM = bytearray(b'0' * 0x2000)
	OAM = bytearray(b'0' * 256)
	PPUADDR = 0
	OAMADDR = 0
	
	cartridge = b''
	
	
	def __init__(self, cartridge):
		self.cartridge = cartridge
		
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
			return self.VRAM[self.PPUADDR]
		elif address < 0x4000: # PPU mirroring
			return self.ROM[0x2000 + (address % 0x8)]
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
			print(f"Illegal write to address 0x{' '.join(a+b for a,b in zip(f'{address:x}'[::2], f'{address:x}'[1::2]))}")
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
				self.write_ppu_memory(value)
			else:
				self.ROM[address] = value
			return 0
		elif address == 0x4014 : # OAMDMA
			address = address << 8
			self.OAM = self.ROM[address:address+0xff]
			return 514
		elif address < 0x2000:
			self.ROM[address % 0x800] = value
		else:
			self.ROM[address] = value
		return 0 
		
		
	def read_ppu_memory(self, address):
			if self.PPUADDR < 0x2000:
				return self.cartridge.prg_rom[address] # CHR_ROM ADDRESS
			elif self.PPUADDR < 0x3000: # VRAM
				return self.VRAM[address - 0x2000]
			elif self.PPUADDR < 0x3F00: # VRAM mirror
				self.VRAM[address - 0X1000]
			else: # palette
				self.VRAM[0x3F00 + (address % 0x20)]
	
	def write_ppu_memory(self, value):
			print(f"{self.PPUADDR:x}")
			if self.PPUADDR < 0x2000:
				pass # CHR_ROM ADDRESS
			elif self.PPUADDR < 0x3000: # VRAM
				self.VRAM[self.PPUADDR - 0x2000] = value
				VRAM_increment = (self.read_rom(0x2000) >> 2) & 1
				self.PPUADDR += 1 if VRAM_increment == 0 else 0x20
			elif self.PPUADDR < 0x3F00: # VRAM mirror
				self.VRAM[self.PPUADDR - 0X1000] = value
			else: # palette
				self.VRAM[0x3F00 + (self.PPUADDR % 0x20)] = value