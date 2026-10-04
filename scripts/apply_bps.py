"""Apply a BPS patch with source, target, and patch CRC verification."""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def number(data: bytes, cursor: int) -> tuple[int, int]:
    value = 0
    shift = 1
    while True:
        if cursor >= len(data):
            raise ValueError("Truncated BPS variable-length integer")
        byte = data[cursor]
        cursor += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, cursor
        shift <<= 7
        value += shift


def apply(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"BPS1") or len(patch) < 16:
        raise ValueError("Not a complete BPS patch")
    if zlib.crc32(patch[:-4]) != struct.unpack_from("<I", patch, len(patch) - 4)[0]:
        raise ValueError("BPS patch checksum mismatch")
    if zlib.crc32(source) != struct.unpack_from("<I", patch, len(patch) - 12)[0]:
        raise ValueError("The source ROM does not match this BPS patch")

    cursor = 4
    source_size, cursor = number(patch, cursor)
    target_size, cursor = number(patch, cursor)
    metadata_size, cursor = number(patch, cursor)
    if source_size != len(source):
        raise ValueError(f"BPS expects {source_size} source bytes, got {len(source)}")
    cursor += metadata_size
    if cursor > len(patch) - 12:
        raise ValueError("Truncated BPS metadata")

    target = bytearray()
    source_relative = 0
    target_relative = 0
    while len(target) < target_size:
        action, cursor = number(patch, cursor)
        mode = action & 3
        length = (action >> 2) + 1
        if mode == 0:  # SourceRead
            start = len(target)
            target.extend(source[start : start + length])
        elif mode == 1:  # TargetRead
            target.extend(patch[cursor : cursor + length])
            cursor += length
        else:
            encoded, cursor = number(patch, cursor)
            delta = encoded >> 1
            if mode == 2:  # SourceCopy
                source_relative += -delta if encoded & 1 else delta
                if source_relative < 0 or source_relative + length > len(source):
                    raise ValueError("BPS source-copy range is invalid")
                target.extend(source[source_relative : source_relative + length])
                source_relative += length
            else:  # TargetCopy; bytewise copy deliberately supports overlap.
                target_relative += -delta if encoded & 1 else delta
                if target_relative < 0 or target_relative >= len(target):
                    raise ValueError("BPS target-copy range is invalid")
                for _ in range(length):
                    target.append(target[target_relative])
                    target_relative += 1
        if len(target) > target_size:
            raise ValueError("BPS action exceeded the declared target size")

    expected_target = struct.unpack_from("<I", patch, len(patch) - 8)[0]
    if zlib.crc32(target) != expected_target:
        raise ValueError("Patched ROM checksum mismatch")
    return bytes(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("patch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = apply(args.source.read_bytes(), args.patch.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Wrote {len(result)} verified bytes to {args.output}")


if __name__ == "__main__":
    main()
