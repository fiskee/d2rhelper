from d2rhelper.bit_reader import BitReader


def test_bit_reader_read_and_revert() -> None:
    br = BitReader(bytes([0b10101010, 0b01010101]))

    first = br.read_int(4)
    second = br.read_int(4)
    br.revert(4)
    second_again = br.read_int(4)

    assert first == 10
    assert second == 10
    assert second_again == second


def test_bit_reader_boundary_and_peek() -> None:
    br = BitReader(bytes([0x10, 0x20, 0x30]))
    assert br.bits_to_next_boundary() == 0
    br.skip(3)
    assert br.bits_to_next_boundary() == 5
    assert br.peek_next_byte() == 0x20
    br.move_to_next_byte_boundary()
    assert br.position_in_bits == 8
