'''Store some functions for all kind of conversions
'''

def bytes2decimal(bytes, endian='little'):
    '''Converts a bytes object to a decimal number

    Args:
        bytes (bytes): A bytes type object, e.g. b'\x11'
        endian (str): One of 'little' or 'big'

    Returns:
        int: A decimal number
    '''
    decimal = int.from_bytes(bytes, byteorder=endian)
    return decimal