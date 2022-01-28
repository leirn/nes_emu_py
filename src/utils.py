'''Some utility functions'''

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()

def format_hex_data(val):
    """Format hex data with spaces every two hexadecimal characters

    Args:
        val -- array of bytes to convert

    Returns:
        Formated strings
    """
    return ' '.join(a+b for a,b in zip(f'{val:x}'[::2], f'{val:x}'[1::2]))

def print_memory_page(page, high = 0) :
    '''Function to pretty print a memory page'''
    for i in range(0, min(256, len(page)), 32):
        print(f"{(high << 8) + i:04x}:{(high << 8) + i + 31 :04x}    {' '.join([f'{i:02x}' for i in page[(high << 8) + i:(high << 8) + i + 32]])}")
    pass
