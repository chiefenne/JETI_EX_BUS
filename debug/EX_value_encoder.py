
import struct
from binascii import hexlify


def EncodeValue(value, dataType, precision):
    '''Encode telemetry value.'''

    # format for pack
    fmt = {0: '<B', 1: '<H', 4: '<I', 5: '<I', 8: '<L', 9: '<L'}

    # number of bytes needed to encode the value
    bytes_for_datatype = {0: 1, 1: 2, 4: 3, 5: 3, 8: 4, 9: 4}

    # get the bit for the sign
    sign = 0x01 if value < 0 else 0x00

    # number of bytes needed to encode the value
    num_bytes = bytes_for_datatype[dataType]

    # scale value based on precision and round it
    value_scaled = int(abs(value) * 10**precision + 0.5)

    # combine sign, precision and scaled value
    value_ex = ((sign << (num_bytes * 8 - 1)) |
               (precision << (num_bytes * 8 - 3)) |
                value_scaled)

    # return the encoded value as bytes in little endian format
    return struct.pack(fmt[dataType], value_ex), value_ex, sign, precision, value_scaled, num_bytes

if __name__ == '__main__':

    # test values
    value = 0.3249817
    dataType = 1
    precision = 1
    expected = hexlify(b'\xE8\x23')

    # Encode the value
    encoded_value, value_ex, sign, precision, value_scaled, num_bytes = EncodeValue(value, dataType, precision)

    print('value: {}'.format(value))
    print('value_scaled: {}'.format(value_scaled))
    print('value_ex: {}'.format(value_ex))
    print('sign: {}'.format(sign))
    print('precision: {}'.format(precision))
    print('num_bytes: {}'.format(num_bytes))
    print('encoded_value: {}'.format(encoded_value))
    print('Encoded hex: {}'.format(hexlify(encoded_value)))
    print('Expected: {}'.format(expected))
