def format_hex_data(val):
	return ' '.join(a+b for a,b in zip(f'{val:x}'[::2], f'{val:x}'[1::2]))