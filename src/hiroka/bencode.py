COLON = ord(":")
DICTIONARY = ord("d")
END = ord("e")
INTEGER = ord("i")
LIST = ord("l")
MINUS = ord("-")
NINE = ord("9")
ZERO = ord("0")


class DecodeError(Exception):
    pass


class Decode:
    def __init__(self, data):
        self._data = data
        self._offset = 0

    def decode(self):
        byte = self._data[self._offset]

        if ZERO <= byte <= NINE:
            return self._decode_string()
        elif byte == INTEGER:
            return self._decode_integer()
        elif byte == LIST:
            return self._decode_list()
        elif byte == DICTIONARY:
            return self._decode_dictionary()
        else:
            raise DecodeError(f"Unexpected byte {bytes([byte])}")

    def _parse_integer(self):
        sign = 1

        if self._data[self._offset] == MINUS:
            sign = -1
            self._offset += 1

        first = self._offset
        first_non_zero = None
        integer = 0

        while (byte := self._data[self._offset]) not in [COLON, END]:
            n = byte - ZERO

            if n < 0 or n > 9:
                raise DecodeError("Invalid integer: not in base 10")
            elif n > 0 and first_non_zero is None:
                first_non_zero = self._offset

            integer = integer * 10 + n
            self._offset += 1

        if first_non_zero is None:
            first_non_zero = self._offset

        if first_non_zero - first > 1:
            raise DecodeError("Invalid integer: leading zeros")

        if integer == 0 and sign == -1:
            raise DecodeError("Invalid integer: negative zero")

        return sign * integer

    def _next(self, expected):
        byte = self._data[self._offset]

        if byte != expected:
            raise DecodeError(f"Expected {expected}, found {bytes([byte])}")

        self._offset += 1

    def _decode_string(self):
        length = self._parse_integer()
        self._next(COLON)
        string = self._data[self._offset : self._offset + length]
        self._offset += length

        return string

    def _decode_integer(self):
        self._next(INTEGER)
        integer = self._parse_integer()
        self._next(END)

        return integer

    def _decode_list(self):
        self._next(LIST)
        list = []

        while self._data[self._offset] != END:
            list.append(self.decode())

        self._next(END)

        return list

    def _decode_dictionary(self):
        self._next(DICTIONARY)
        dictionary = {}
        keys = []

        while self._data[self._offset] != END:
            encoded_key = self._decode_string()

            if keys and keys[-1] > encoded_key:
                raise DecodeError("Invalid dictionary: keys not sorted")

            keys.append(encoded_key)
            key = encoded_key.decode()
            value = self.decode()
            dictionary[key] = value

        self._next(END)

        return dictionary


class EncodeError(Exception):
    pass


class Encode:
    def __init__(self):
        self._data = bytearray()

    def encode(self, value):
        if isinstance(value, bytes):
            self._encode_string(value)
        elif isinstance(value, int):
            self._encode_integer(value)
        elif isinstance(value, list):
            self._encode_list(value)
        elif isinstance(value, dict):
            self._encode_dictionary(value)
        else:
            raise EncodeError("Unsupported type")

        return bytes(self._data)

    def _encode_string(self, string):
        self._data += str(len(string)).encode() + b":" + string

    def _encode_integer(self, integer):
        self._data += b"i" + str(integer).encode() + b"e"

    def _encode_list(self, list):
        self._data += b"l"

        for value in list:
            self.encode(value)

        self._data += b"e"

    def _encode_dictionary(self, dictionary):
        self._data += b"d"

        for key in sorted(map(lambda key: key.encode(), dictionary)):
            self._encode_string(key)
            self.encode(dictionary[key.decode()])

        self._data += b"e"


def decode(data):
    return Decode(data).decode()


def encode(value):
    return Encode().encode(value)
