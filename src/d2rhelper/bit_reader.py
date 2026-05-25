from __future__ import annotations


class BitReader:
    _MASK_64 = (1 << 64) - 1
    _HUFFMAN_DICTIONARY = {
        "11110": "a",
        "0101": "b",
        "01000": "c",
        "110001": "d",
        "110000": "e",
        "010011": "f",
        "11010": "g",
        "00011": "h",
        "1111110": "i",
        "000101110": "j",
        "010010": "k",
        "11101": "l",
        "01101": "m",
        "001101": "n",
        "1111111": "o",
        "11011001": "q",
        "11001": "p",
        "11100": "r",
        "0010": "s",
        "01100": "t",
        "00001": "u",
        "1101110": "v",
        "00000": "w",
        "00111": "x",
        "0001010": "y",
        "11011000": "z",
        "10": " ",
        "11111011": "0",
        "1111100": "1",
        "001100": "2",
        "1101101": "3",
        "11111010": "4",
        "00010110": "5",
        "1101111": "6",
        "01111": "7",
        "000100": "8",
        "01110": "9",
    }

    def __init__(self, data: bytes):
        self._data = data
        self._position_in_bits = 0

    @property
    def position_in_bits(self) -> int:
        return self._position_in_bits

    def set_position_in_bits(self, position_in_bits: int) -> None:
        if position_in_bits < 0:
            position_in_bits = 0
        self._position_in_bits = position_in_bits

    @property
    def length_in_bits(self) -> int:
        return len(self._data) * 8

    def get_current_byte(self) -> int:
        index = self._position_in_bits // 8
        if index >= len(self._data):
            return 0
        return self._data[index]

    def revert(self, amount: int) -> None:
        self._position_in_bits -= amount

    def skip(self, bits: int) -> None:
        self._position_in_bits += bits

    def move_to_next_byte_boundary(self) -> None:
        self._position_in_bits = (self._position_in_bits + 7) & (~7)

    def bits_to_next_boundary(self) -> int:
        return ((self._position_in_bits + 7) & ~7) - self._position_in_bits

    def peek_next_byte(self) -> int:
        peek_index = (self._position_in_bits // 8) + (
            0 if self.bits_to_next_boundary() == 0 else 1
        )
        if peek_index + 1 >= len(self._data):
            return -1
        return self._data[peek_index]

    def peek_next_bytes(self, bits: int) -> int:
        return self._unflip(self._read(min(bits, 64), update_position=False), bits)

    def read_char(self, bits: int) -> str:
        return chr(self._unflip(self._read(bits, update_position=True), bits))

    def read_byte(self, bits: int) -> int:
        value = self._unflip(self._read(bits, update_position=True), bits)
        return value if value < 128 else value - 256

    def read_short(self, bits: int) -> int:
        return self._unflip(self._read(bits, update_position=True), bits)

    def read_int(self, bits: int = 32) -> int:
        return self._unflip(self._read(bits, update_position=True), bits)

    def read_flipped_int(self, bits: int) -> int:
        return self._read(bits, update_position=True)

    def read_huffman_encoded_string(self) -> str:
        reader = ""
        out = ""
        while True:
            reader += str(self._read(1, update_position=True))
            char = self._HUFFMAN_DICTIONARY.get(reader)
            if char is not None:
                if char == " ":
                    return out
                out += char
                reader = ""
            if len(reader) > 100 or len(out) > 100:
                raise ValueError("Huffman decoding failed, string too long")

    def _read(self, bits: int, update_position: bool) -> int:
        position_in_bytes = self._position_in_bits // 8
        bits_in_last_byte = self._position_in_bits % 8

        result = 0
        for i in range(8):
            result <<= 8
            if position_in_bytes + i < len(self._data):
                read_byte = self._data[position_in_bytes + i]
                result += self._flip_byte(read_byte) & 0xFF
            result &= self._MASK_64

        result <<= bits_in_last_byte
        result &= self._MASK_64
        result >>= 64 - bits

        if update_position:
            self._position_in_bits += bits
        return result

    @staticmethod
    def _flip_byte(b: int) -> int:
        ret = 0
        for i in range(8):
            bit = (b >> i) & 0x01
            ret = (ret << 1) + bit
        return ret

    @staticmethod
    def _unflip(value: int, bits: int) -> int:
        ret = 0
        for i in range(bits):
            bit = (value >> i) & 0x01
            ret = (ret << 1) + bit
        return ret
