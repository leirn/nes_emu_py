

opcodes = {
	#HEX, 	MODE, 			SYNTAX, 		LEN,		TIME, 	PAGE_CROSS
	#ADC
	0x69 :	["Immediate", 		"ADC #$44", 	2, 		2, 		0	],
	0x65 :	["Zero Page", 		"ADC $44", 		2, 		3,		0	],
	0x75 :	["Zero Page, X", 	"ADC $44, X", 	2, 		4, 		0	],
	0x6d :	["Absolute", 		"ADC $4400", 	3, 		4, 		0	],
	0x7d :	["Absolute, X", 		"ADC $4400, X", 	3, 		4, 		1	],
	0x79 :	["Absolute, Y", 		"ADC $4400, Y", 	3, 		4, 		1	],
	0x61 :	["Indirect, X", 		"ADC ($44, X)", 	2, 		6, 		0	],
	0x71 :	["Indirect, Y", 		"ADC ($44), Y", 	2, 		5, 		1	],
	
	#AND
	0x29 :	["Immediate", 		"AND #$44", 	2, 		2, 		0	],
	0x25 :	["Zero Page", 		"AND $44", 		2, 		3,		0	],
	0x35 :	["Zero Page, X", 	"AND $44, X", 	2, 		4, 		0	],
	0x2d :	["Absolute", 		"AND $4400", 	3, 		4, 		0	],
	0x3d :	["Absolute, X", 		"AND $4400, X", 	3, 		4, 		1	],
	0x39 :	["Absolute, Y", 		"AND $4400, Y", 	3, 		4, 		1	],
	0x21 :	["Indirect, X", 		"AND ($44, X)", 	2, 		6, 		0	],
	0x31 :	["Indirect, Y", 		"AND ($44), Y", 	2, 		5, 		1	],
	
	#ASL
	0x0a:	["Accumulator",		"ASL A",		1,		2,		0	],
	0x06:	["Zero Page",		"ASL $44",		2,		5,		0	],
	0x16:	["Zero Page, X",		"ASL $44, X",	2,		6,		0	],
	0x0e:	["Absolute",		"ASL $4400",	3,		6,		0	],
	0x1e:	["Absolute, X",		"ASL $4400, X",	3,		7,		0	],
	
	#BIT
	0x24:	["Zero Page",		"BIT $44",		2,		3,		0	],
	0x2c:	["Absolute",		"BIT $4400",	3,		4,		0	],
	
	#BRANCH # Cycle count impact depending or branching actually done
	0x10:	["Relative",		"BPL #$44",		2,		2,		0	],
	0x30:	["Relative",		"BMI #$44",		2,		2,		0	],
	0x50:	["Relative",		"BVC #$44",		2,		2,		0	],
	0x70:	["Relative",		"BVS #$44",		2,		2,		0	],
	0x90:	["Relative",		"BCC #$44",		2,		2,		0	],
	0xb0:	["Relative",		"BCS #$44",		2,		2,		0	],
	0xd0:	["Relative",		"BNE #$44",		2,		2,		0	],
	0xf0:		["Relative",		"BEQ #$44",		2,		2,		0	],
	
	#BREAK
	0x00:	["Implied",		"BRK",		1,		7,		0	],
	
	#CMP
	0xc9 :	["Immediate", 		"CMP #$44", 	2, 		2, 		0	],
	0xc5 :	["Zero Page", 		"CMP $44", 		2, 		3,		0	],
	0xd5 :	["Zero Page, X", 	"CMP $44, X", 	2, 		4, 		0	],
	0xcd :	["Absolute", 		"CMP $4400", 	3, 		4, 		0	],
	0xdd :	["Absolute, X", 		"CMP $4400, X", 	3, 		4, 		1	],
	0xd9 :	["Absolute, Y", 		"CMP $4400, Y", 	3, 		4, 		1	],
	0xc1 :	["Indirect, X", 		"CMP ($44, X)", 	2, 		6, 		0	],
	0xc1 :	["Indirect, Y", 		"CMP ($44), Y", 	2, 		5, 		1	],
	
	#CPX
	0xe0 :	["Immediate", 		"CPX #$44", 	2, 		2, 		0	],
	0xe4 :	["Zero Page", 		"CPX $44", 		2, 		3,		0	],
	0xec :	["Absolute", 		"CPX $4400", 	3, 		4, 		0	],
	
	#CPY
	0xc0 :	["Immediate", 		"CPY #$44", 	2, 		2, 		0	],
	0xc4 :	["Zero Page", 		"CPY $44", 		2, 		3,		0	],
	0xcc :	["Absolute", 		"CPY $4400", 	3, 		4, 		0	],
	
	#DEC
	0xc6 :	["Zero Page", 		"DEC $44", 		2, 		5, 		0	],
	0xd6 :	["Zero Page, X",	"DEC $44, X", 	2, 		6, 		0	],
	0xce :	["Absolute", 		"DEC $4400", 	3, 		6, 		0	],
	0xde :	["Absolute, X", 		"DEC $4400, X", 	3, 		7, 		0	],
	
	#EOR
	0x49 :	["Immediate", 		"EOR #$44", 	2, 		2, 		0	],
	0x45 :	["Zero Page", 		"EOR $44", 		2, 		3,		0	],
	0x55 :	["Zero Page, X", 	"EOR $44, X", 	2, 		4, 		0	],
	0x4d :	["Absolute", 		"EOR $4400", 	3, 		4, 		0	],
	0x5d :	["Absolute, X", 		"EOR $4400, X", 	3, 		4, 		1	],
	0x59 :	["Absolute, Y", 		"EOR $4400, Y", 	3, 		4, 		1	],
	0x41 :	["Indirect, X", 		"EOR ($44, X)", 	2, 		6, 		0	],
	0x51 :	["Indirect, Y", 		"EOR ($44), Y", 	2, 		5, 		1	],
	
	#Flags
	0x18:	["Implied",		"CLC",		1,		2,		0	],
	0x38:	["Implied",		"SEC",		1,		2,		0	],
	0x58:	["Implied",		"CLI",		1,		2,		0	],
	0x78:	["Implied",		"SEI",		1,		2,		0	],
	0xb8:	["Implied",		"CLV",		1,		2,		0	],
	0xd8:	["Implied",		"CLD",		1,		2,		0	],
	0xf8:		["Implied",		"SED",		1,		2,		0	],
	
	#INC
	0xe6 :	["Zero Page", 		"DEC $44", 		2, 		5, 		0	],
	0xf6 :	["Zero Page, X",		"DEC $44, X", 	2, 		6, 		0	],
	0xee :	["Absolute", 		"DEC $4400", 	3, 		6, 		0	],
	0xfe :	["Absolute, X", 		"DEC $4400, X", 	3, 		7, 		0	],
	
	#JMP
	0x4c :	["Absolute", 		"JMP $5597",	3, 		3, 		0	],
	0x6c :	["Indirect",		"JMP ($5597)", 	3, 		5, 		0	],
	
	#JSR
	0x20 :	["Absolute", 		"JSR $5597",	3, 		6, 		0	],
	
	#LDA
	0xa9 :	["Immediate", 		"LDA #$44", 	2, 		2, 		0	],
	0xa5 :	["Zero Page", 		"LDA $44", 		2, 		3,		0	],
	0xb5 :	["Zero Page, X", 	"LDA $44, X", 	2, 		4, 		0	],
	0xad :	["Absolute", 		"LDA $4400", 	3, 		4, 		0	],
	0xbd :	["Absolute, X", 		"LDA $4400, X", 	3, 		4, 		1	],
	0xb9 :	["Absolute, Y", 		"LDA $4400, Y", 	3, 		4, 		1	],
	0xa1 :	["Indirect, X", 		"LDA ($44, X)", 	2, 		6, 		0	],
	0xb1 :	["Indirect, Y", 		"LDA ($44), Y", 	2, 		5, 		1	],
	
	#LDX
	0xa2:	["Immediate",		"LDX #$44",	2,		2,		0	],
	0xa6:	["Zero Page",		"LDX $44",		2,		3,		0	],
	0xb6:	["Zero Page, Y",		"LDX $44, Y",	2,		4,		0	],
	0xae:	["Absolute",		"LDX $4400",	3,		4,		0	],
	0xbe:	["Absolute, Y",		"LDX $4400, Y",	3,		4,		1	],
	
	#LDY
	0xa0:	["Immediate",		"LDY #$44",	2,		2,		0	],
	0xa4:	["Zero Page",		"LDY $44",		2,		3,		0	],
	0xb4:	["Zero Page, X",		"LDY $44, X",	2,		4,		0	],
	0xac:	["Absolute",		"LDY $4400",	3,		4,		0	],
	0xbc:	["Absolute, X",		"LDY $4400, X",	3,		4,		1	],
	
	#LSR
	0x4a:	["Accumulator",		"LSR A",		1,		2,		0	],
	0x46:	["Zero Page",		"LSR $44",		2,		5,		0	],
	0x56:	["Zero Page, X",		"LSR $44, X",	2,		6,		0	],
	0x4e:	["Absolute",		"LSR $4400",	3,		6,		0	],
	0x5e:	["Absolute, X",		"LSR $4400, X",	3,		7,		0	],
	
	#NOP
	0xea:	["Implied",		"NOP",		1,		2,		0	],
	
	#ORA
	0x09 :	["Immediate", 		"ORA #$44", 	2, 		2, 		0	],
	0x05 :	["Zero Page", 		"ORA $44", 		2, 		3,		0	],
	0x15 :	["Zero Page, X", 	"ORA $44, X", 	2, 		4, 		0	],
	0x0d :	["Absolute", 		"ORA $4400", 	3, 		4, 		0	],
	0x1d :	["Absolute, X", 		"ORA $4400, X", 	3, 		4, 		1	],
	0x19 :	["Absolute, Y", 		"ORA $4400, Y", 	3, 		4, 		1	],
	0x01 :	["Indirect, X", 		"ORA ($44, X)", 	2, 		6, 		0	],
	0x11 :	["Indirect, Y", 		"ORA ($44), Y", 	2, 		5, 		1	],
	
	#Registers
	0xaa:	["Implied",		"TAX",		1,		2,		0	],
	0x8a:	["Implied",		"TXA",		1,		2,		0	],
	0xca:	["Implied",		"DEX",		1,		2,		0	],
	0xe8:	["Implied",		"INX",		1,		2,		0	],
	0xa8:	["Implied",		"TAY",		1,		2,		0	],
	0x98:	["Implied",		"TYA",		1,		2,		0	],
	0x88:	["Implied",		"DEY",		1,		2,		0	],
	0xc8:	["Implied",		"INY",		1,		2,		0	],
	
	#ROL
	0x2a:	["Accumulator",		"ROL A",		1,		2,		0	],
	0x26:	["Zero Page",		"ROL $44",		2,		5,		0	],
	0x36:	["Zero Page, X",		"ROL $44, X",	2,		6,		0	],
	0x2e:	["Absolute",		"ROL $4400",	3,		6,		0	],
	0x3e:	["Absolute, X",		"ROL $4400, X",	3,		7,		0	],
	
	#ROR
	0x6a:	["Accumulator",		"ROR A",		1,		2,		0	],
	0x66:	["Zero Page",		"ROR $44",		2,		5,		0	],
	0x76:	["Zero Page, X",		"ROR $44, X",	2,		6,		0	],
	0x6e:	["Absolute",		"ROR $4400",	3,		6,		0	],
	0x7e:	["Absolute, X",		"ROR $4400, X",	3,		7,		0	],
	
	#RTI
	0x40:	["Implied",		"RTI",		1,		6,		0	],
	
	#RTS
	0x60:	["Implied",		"RTS",		1,		6,		0	],
	
	#SBC
	0xe9 :	["Immediate", 		"SBC #$44", 	2, 		2, 		0	],
	0xe5 :	["Zero Page", 		"SBC $44", 		2, 		3,		0	],
	0xf5 :	["Zero Page, X", 	"SBC $44, X", 	2, 		4, 		0	],
	0xed :	["Absolute", 		"SBC $4400", 	3, 		4, 		0	],
	0xfd :	["Absolute, X", 		"SBC $4400, X", 	3, 		4, 		1	],
	0xf9 :	["Absolute, Y", 		"SBC $4400, Y", 	3, 		4, 		1	],
	0xe1 :	["Indirect, X", 		"SBC ($44, X)", 	2, 		6, 		0	],
	0xf1 :	["Indirect, Y", 		"SBC ($44), Y", 	2, 		5, 		1	],
	
	#STA
	0x85 :	["Zero Page", 		"STA $44", 		2, 		3,		0	],
	0x95 :	["Zero Page, X", 	"STA $44, X", 	2, 		4, 		0	],
	0x8d :	["Absolute", 		"STA $4400", 	3, 		4, 		0	],
	0x9d :	["Absolute, X", 		"STA $4400, X", 	3, 		5, 		0	],
	0x99 :	["Absolute, Y", 		"STA $4400, Y", 	3, 		5, 		0	],
	0x81 :	["Indirect, X", 		"STA ($44, X)", 	2, 		6, 		0	],
	0x91 :	["Indirect, Y", 		"STA ($44), Y", 	2, 		6, 		0	],
	
	#Stack
	0x9a:	["Implied",		"TXS",		1,		2,		0	],
	0xba:	["Implied",		"TSX",		1,		2,		0	],
	0x48:	["Implied",		"PHA",		1,		3,		0	],
	0x68:	["Implied",		"PLA",		1,		4,		0	],
	0x08:	["Implied",		"PHP",		1,		3,		0	],
	0x28:	["Implied",		"PLP",		1,		4,		0	],
	
	#STX
	0x86 :	["Zero Page", 		"STX $44", 		2, 		3,		0	],
	0x96 :	["Zero Page, Y", 	"STX $44, Y", 	2, 		4, 		0	],
	0x8e :	["Absolute", 		"STX $4400", 	3, 		4, 		0	],
	
	#STY
	0x84 :	["Zero Page", 		"STY $44", 		2, 		3,		0	],
	0x94 :	["Zero Page, X", 	"STY $44, X", 	2, 		4, 		0	],
	0x8c :	["Absolute", 		"STY $4400", 	3, 		4, 		0	],
	}
