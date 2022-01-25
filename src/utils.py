'''Some utility functions'''

# Preventing direct execution
if __name__ == '__main__':
    import sys
    print("This module cannot be executed. Please use main.py")
    sys.exit()


def format_hex_data(val):
    """Format hex data with spaces every two hexadecimal characters

    Arguments
    val -- array of bytes to convert

    Returns
    Formated strings
    """
    return ' '.join(a+b for a,b in zip(f'{val:x}'[::2], f'{val:x}'[1::2]))
