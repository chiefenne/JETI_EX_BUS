'''Collection of utility functions for all kind of conversions
'''

def bytes2decimal(bytes, endian='little'):
    '''Converts a byte string to a decimal number

    Args:
        bytes (bytes): A bytes type object, e.g. b'\x11'
        endian (str, optional): Little or big endian byte order. Defaults to 'little'.

    Returns:
        int: A decimal number
    '''
    decimal = int.from_bytes(bytes, byteorder=endian)
    return decimal

def decimal2bytes(decimal, endian='little'):
    '''Convert decimal to bytes object

    Args:
        decimal (int): An integer number (max. 16 bit = 0-65535)
        endian (str, optional): Little or big endian byte order. Defaults to 'little'.
    '''
    bytestring = decimal.to_bytes(2, endian)
    return bytestring

