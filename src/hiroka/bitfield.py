from math import ceil


class Bitfield:
    def __init__(self, value):
        if isinstance(value, bytes):
            self.data = bytearray(value)
        elif isinstance(value, int):
            self.data = bytearray(ceil(value / 8))
        else:
            raise TypeError("'value' must be a bytes or int object")

    def __contains__(self, piece_index):
        return self.data[piece_index // 8] & 0b1000_0000 >> piece_index % 8 > 0

    def add(self, piece_index):
        self.data[piece_index // 8] |= 0b1000_0000 >> piece_index % 8

    def remove(self, piece_index):
        self.data[piece_index // 8] &= ~(0b1000_0000 >> piece_index % 8)
