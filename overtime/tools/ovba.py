"""MS-OVBA (2.4.1) Compression/Decompression algorithm.

Reference: [MS-OVBA] 2.4.1 "Compression and Decompression".
Used to store VBA module source inside a vbaProject.bin.
"""

SIGNATURE = 0x01
CHUNK_DECOMPRESSED_MAX = 4096


def _bit_count(difference: int) -> int:
    """BitCount = Max(4, Ceiling(Log2(difference)))  -- [MS-OVBA] 2.4.1.3.19.1"""
    if difference <= 0:
        return 4
    return max(4, (difference - 1).bit_length())


def _limits(difference: int):
    bc = _bit_count(difference)
    length_mask = 0xFFFF >> bc
    offset_mask = (~length_mask) & 0xFFFF
    max_length = length_mask + 3
    max_offset = 1 << bc
    return bc, length_mask, offset_mask, max_length, max_offset


def _compress_chunk(data: bytes) -> bytes:
    """Compress one DecompressedChunk (<= 4096 bytes) into a token stream."""
    out = bytearray()
    flag_pos = 0
    flags = 0
    ntok = 0
    out.append(0)  # placeholder FlagByte

    # hash chains over 3-byte sequences, for match finding
    chains = {}
    n = len(data)
    i = 0
    while i < n:
        if ntok == 8:
            out[flag_pos] = flags
            flags = 0
            ntok = 0
            flag_pos = len(out)
            out.append(0)

        best_len = 0
        best_off = 0
        if i > 0 and n - i >= 3:
            bc, length_mask, offset_mask, max_length, max_offset = _limits(i)
            key = data[i:i + 3]
            lo = i - max_offset
            if lo < 0:
                lo = 0
            cand = chains.get(key)
            if cand:
                tries = 0
                for j in reversed(cand):
                    if j < lo:
                        break
                    tries += 1
                    if tries > 48:
                        break
                    ln = 0
                    limit = min(max_length, n - i)
                    while ln < limit and data[j + ln] == data[i + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len = ln
                        best_off = i - j
                        if ln == limit:
                            break

        if best_len >= 3:
            bc, length_mask, offset_mask, max_length, max_offset = _limits(i)
            token = ((best_off - 1) << (16 - bc)) | (best_len - 3)
            out.append(token & 0xFF)
            out.append((token >> 8) & 0xFF)
            flags |= (1 << ntok)
            for k in range(i, i + best_len):
                if k + 3 <= n:
                    chains.setdefault(data[k:k + 3], []).append(k)
            i += best_len
        else:
            out.append(data[i])
            if i + 3 <= n:
                chains.setdefault(data[i:i + 3], []).append(i)
            i += 1
        ntok += 1

    out[flag_pos] = flags
    return bytes(out)


def _emit_chunk(out: bytearray, raw: bytes) -> None:
    """Append one chunk covering exactly `raw`, splitting if it cannot fit."""
    body = _compress_chunk(raw)
    if len(body) <= 4096:
        header = 0xB000 | ((len(body) + 2 - 3) & 0x0FFF)
        out.append(header & 0xFF)
        out.append((header >> 8) & 0xFF)
        out += body
        return
    if len(raw) == CHUNK_DECOMPRESSED_MAX:
        # a full, incompressible chunk is stored raw -- exactly 4096 bytes,
        # so nothing is added or lost on decompression
        header = 0x3000 | ((CHUNK_DECOMPRESSED_MAX + 2 - 3) & 0x0FFF)
        out.append(header & 0xFF)
        out.append((header >> 8) & 0xFF)
        out += raw
        return
    # a short chunk that will not fit compressed: split rather than pad,
    # because padding a raw chunk would append stray bytes to the output
    half = len(raw) // 2
    _emit_chunk(out, raw[:half])
    _emit_chunk(out, raw[half:])


def compress(data: bytes) -> bytes:
    """Build a CompressedContainer from raw bytes."""
    out = bytearray([SIGNATURE])
    for off in range(0, len(data), CHUNK_DECOMPRESSED_MAX):
        _emit_chunk(out, data[off:off + CHUNK_DECOMPRESSED_MAX])
    return bytes(out)


def decompress(container: bytes) -> bytes:
    """Spec-faithful decompressor, used to verify compress()."""
    if not container or container[0] != SIGNATURE:
        raise ValueError("bad CompressedContainer signature")
    pos = 1
    out = bytearray()
    while pos + 2 <= len(container):
        header = container[pos] | (container[pos + 1] << 8)
        pos += 2
        size = (header & 0x0FFF) + 3
        sig = (header >> 12) & 0x07
        flag = (header >> 15) & 0x01
        if sig != 0b011:
            raise ValueError("bad CompressedChunkSignature")
        end = pos + size - 2
        if flag == 0:
            out += container[pos:end]
            pos = end
            continue
        chunk_start = len(out)
        while pos < end:
            flags = container[pos]
            pos += 1
            for b in range(8):
                if pos >= end:
                    break
                if flags & (1 << b):
                    token = container[pos] | (container[pos + 1] << 8)
                    pos += 2
                    bc, length_mask, offset_mask, _m, _o = _limits(len(out) - chunk_start)
                    offset = ((token & offset_mask) >> (16 - bc)) + 1
                    length = (token & length_mask) + 3
                    src = len(out) - offset
                    if src < 0:
                        raise ValueError("copy token offset out of range")
                    for k in range(length):
                        out.append(out[src + k])
                else:
                    out.append(container[pos])
                    pos += 1
    return bytes(out)
