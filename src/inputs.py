import memory


class NESController:
	
	status = 0
	memoryAddress = 0x4016
	
	def __init__(self, memory, memoryAddress):
		self.memoryAddress = memoryAddress
		self.memory = memory
		
	def updateMemory(self):
		self.memory.write_rom(self.memoryAddress, self.status)
		
	def setA(self):
		self.status |= 1
		self.updateMemory()
		
	def clearA(self):
		self.status &= 0b11111110
		self.updateMemory()
		
	def setB(self):
		self.status |= 0b10
		self.updateMemory()
		
	def clearB(self):
		self.status &= 0b11111101
		self.updateMemory()
		
	def setSelect(self):
		self.status |= 0b100
		self.updateMemory()
		
	def clearSelect(self):
		self.status &= 0b11111011
		self.updateMemory()
		
	def setStart(self):
		self.status |= 0b1000
		self.updateMemory()
		
	def clearStart(self):
		self.status &= 0b11110111
		self.updateMemory()
		
	def setUp(self):
		self.status |= 0b1000
		self.updateMemory()
		
	def clearUp(self):
		self.status &= 0b11101111
		
	def setDown(self):
		self.status |= 0b10000
		self.updateMemory()
		
	def clearDown(self):
		self.status &= 0b11011111
		self.updateMemory()
		
	def setLeft(self):
		self.status |= 0b100000
		self.updateMemory()
		
	def clearLeft(self):
		self.status &= 0b10111111
		self.updateMemory()
		
	def setRight(self):
		self.status |= 0b1000000
		self.updateMemory()
		
	def clearRight(self):
		self.status &= 0b01111111
		self.updateMemory()
		
class NESController1(NESController):
		def __init__(self, memory):
			super().__init__(memory, 0x4016)
		
class NESController2(NESController):
		def __init__(self, memory):
			super().__init__(memory, 0x4017)
		