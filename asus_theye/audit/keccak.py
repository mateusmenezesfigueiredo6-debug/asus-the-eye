"""Small dependency-free Keccak-256 implementation for Ethereum-compatible Merkle trees."""

from __future__ import annotations

_RC = (0x1,0x8082,0x800000000000808A,0x8000000080008000,0x808B,0x80000001,
       0x8000000080008081,0x8000000000008009,0x8A,0x88,0x80008009,0x8000000A,
       0x8000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
       0x8000000000008002,0x8000000000000080,0x800A,0x800000008000000A,
       0x8000000080008081,0x8000000000008080,0x80000001,0x8000000080008008)
_ROT = ((0,36,3,41,18),(1,44,10,45,2),(62,6,43,15,61),(28,55,25,21,56),(27,20,39,8,14))
_MASK = (1 << 64) - 1


def _rol(value: int, count: int) -> int:
    return value if count == 0 else ((value << count) | (value >> (64 - count))) & _MASK


def _permutation(state: list[int]) -> None:
    for rc in _RC:
        c = [state[x] ^ state[x+5] ^ state[x+10] ^ state[x+15] ^ state[x+20] for x in range(5)]
        d = [c[(x-1)%5] ^ _rol(c[(x+1)%5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5): state[x+5*y] ^= d[x]
        b = [0] * 25
        for x in range(5):
            for y in range(5): b[y + 5*((2*x+3*y)%5)] = _rol(state[x+5*y], _ROT[x][y])
        for x in range(5):
            for y in range(5): state[x+5*y] = b[x+5*y] ^ ((~b[(x+1)%5+5*y]) & b[(x+2)%5+5*y])
        state[0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate = 136
    padded = bytearray(data)
    padded.append(0x01)  # Keccak domain suffix, deliberately not SHA3's 0x06.
    padded.extend(b"\0" * ((rate - len(padded) % rate - 1) % rate))
    padded.append(0x80)
    state = [0] * 25
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset+rate]
        for index in range(rate // 8):
            state[index] ^= int.from_bytes(block[index*8:index*8+8], "little")
        _permutation(state)
    return b"".join(word.to_bytes(8, "little") for word in state)[:32]
