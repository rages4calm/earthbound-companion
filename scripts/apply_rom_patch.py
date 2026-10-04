"""Apply BPS or IPS ROM patches without an external patcher.

BPS input is fully checksum verified by :mod:`apply_bps`. IPS has no embedded
source checksum, so callers must validate the source ROM separately.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from apply_bps import apply as apply_bps


def apply_ips(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH"):
        raise ValueError("Not an IPS patch")

    target = bytearray(source)
    cursor = 5
    while True:
        if cursor + 3 > len(patch):
            raise ValueError("Truncated IPS record header")
        if patch[cursor : cursor + 3] == b"EOF":
            cursor += 3
            break

        offset = int.from_bytes(patch[cursor : cursor + 3], "big")
        cursor += 3
        if cursor + 2 > len(patch):
            raise ValueError("Truncated IPS record size")
        size = int.from_bytes(patch[cursor : cursor + 2], "big")
        cursor += 2

        if size:
            end = cursor + size
            if end > len(patch):
                raise ValueError("Truncated IPS literal record")
            payload = patch[cursor:end]
            cursor = end
        else:
            if cursor + 3 > len(patch):
                raise ValueError("Truncated IPS RLE record")
            rle_size = int.from_bytes(patch[cursor : cursor + 2], "big")
            value = patch[cursor + 2]
            cursor += 3
            payload = bytes([value]) * rle_size

        required = offset + len(payload)
        if required > len(target):
            target.extend(b"\x00" * (required - len(target)))
        target[offset:required] = payload

    remaining = len(patch) - cursor
    if remaining == 3:
        truncate_size = int.from_bytes(patch[cursor : cursor + 3], "big")
        del target[truncate_size:]
    elif remaining:
        raise ValueError(f"Unexpected {remaining} trailing IPS bytes")
    return bytes(target)


def apply(source: bytes, patch: bytes) -> tuple[bytes, str]:
    if patch.startswith(b"BPS1"):
        return apply_bps(source, patch), "BPS (checksums verified)"
    if patch.startswith(b"PATCH"):
        return apply_ips(source, patch), "IPS"
    raise ValueError("Unsupported patch format; expected BPS1 or PATCH header")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("patch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result, format_name = apply(args.source.read_bytes(), args.patch.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Applied {format_name}; wrote {len(result)} bytes to {args.output}")


if __name__ == "__main__":
    main()
