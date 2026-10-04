"""Relocate compiled MaternalBound dialogue into the native text VM format.

Outputs remain development artifacts until opcode/routine and data integration
pass. ROM content is only read locally. Reports contain addresses and counts,
never copied dialogue, graphics, or machine-code payloads.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys

BLOB_BASE = 0x100000
ASM_WORD = re.compile(r"^(?:ADC|AND|ASL|BCC|BCS|BEQ|BIT|BMI|BNE|BPL|BRA|BRL|BVC|BVS|CLC|CLD|CLI|CLV|CMP|COP|CPX|CPY|DEC|DEX|DEY|EOR|INC|INX|INY|JML|JMP|JSL|JSR|LDA|LDX|LDY|LSR|MVN|MVP|NOP|ORA|PEA|PEI|PER|PHA|PHB|PHD|PHK|PHP|PHX|PHY|PLA|PLB|PLD|PLP|PLX|PLY|REP|ROL|ROR|RTI|RTL|RTS|SBC|SEC|SED|SEI|SEP|STA|STP|STX|STY|STZ|TAX|TAY|TCD|TCS|TDC|TRB|TSB|TSC|TSX|TXA|TXS|TXY|TYA|TYX|WAI|WDM|XBA|XCE)(?:_[A-Za-z0-9]+)?\b|^M_[A-Za-z0-9_]+\b")
SOURCE_LABEL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
ORIGINAL_LABEL = re.compile(r"l_0x([0-9a-fA-F]{6})$")


class ConversionError(ValueError):
    pass


def without_comments(text: str) -> str:
    # Leave quoted strings intact; comments sometimes contain example labels.
    token = re.compile(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*')
    return token.sub(lambda m: m[0] if m[0].startswith('"') else '\n' * m[0].count('\n'), text)


def source_labels(path: Path) -> dict[str, str]:
    lines = without_comments(path.read_text(encoding="utf-8", errors="replace")).splitlines()
    result = {}
    for i, line in enumerate(lines):
        match = SOURCE_LABEL.match(line)
        if not match:
            continue
        rest = match[2].strip()
        if not rest or rest == "{":
            for following in lines[i + 1:]:
                if following.strip() and following.strip() not in ("{", "}") and not SOURCE_LABEL.match(following):
                    rest = following.strip()
                    break
        result[match[1]] = "assembly" if ASM_WORD.match(rest) else "raw-data" if re.match(r"^(?:long|short|byte|insertbin|ROMTBL|ROM)\b",rest) else "script"
    return result


@dataclass
class Decoded:
    data: bytearray
    # Pointer fields: (output byte offset, original pointer, purpose)
    pointers: list[tuple[int, int, str]]
    boundaries: dict[int, int]
    opcodes: Counter
    routines: list[tuple[int, int]]


def relocate_bytes(data: bytes, specs: dict, expansions: list[bytes]) -> Decoded:
    """Parse exact instruction widths; malformed/unknown instructions fail closed."""
    out = bytearray()
    pointers = []
    boundaries = {}
    opcodes = Counter()
    routines = []
    pos = 0

    def take(n: int) -> bytes:
        nonlocal pos
        if n < 0 or pos + n > len(data):
            raise ConversionError(f"truncated operand at +0x{pos:X}, need {n} bytes")
        value = data[pos:pos+n]
        pos += n
        return value

    def pointer(purpose: str) -> None:
        raw = take(4)
        pointers.append((len(out), int.from_bytes(raw, "little"), purpose))
        out.extend(raw)

    while pos < len(data):
        boundaries[pos] = len(out)
        byte = take(1)[0]
        if byte >= 0x20:
            out.append(byte)
            continue
        if byte in (0x15, 0x16, 0x17):
            index = (byte - 0x15)*256 + take(1)[0]
            if index >= len(expansions):
                raise ConversionError(f"unknown compressed text index {index}")
            out.extend(expansions[index])
            continue
        key = (byte, take(1)[0]) if byte >= 0x18 else (byte,)
        spec = specs.get(key)
        if spec is None:
            raise ConversionError(f"unknown opcode {' '.join(f'{x:02X}' for x in key)} at +0x{pos-len(key):X}")
        name, args = spec
        opcodes[name] += 1
        out.extend(key)
        for kind in args:
            if kind == "LABEL":
                pointer(name)
            elif kind == "JUMP_TABLE":
                count = take(1)[0]
                out.append(count)
                for _ in range(count):
                    pointer(name)
            elif kind == "STRING":
                while True:
                    char = take(1)[0]
                    out.append(char)
                    if char in (3, 4):
                        # Redux's dual-column menu labels carry a second string
                        # followed by a zero and, for 03, a callback pointer.
                        while True:
                            second = take(1)[0]
                            out.append(second)
                            if second == 0:
                                break
                            if second < 0x20:
                                raise ConversionError("control code inside dual-column menu string")
                        if char == 3:
                            pointer(name)
                        break
                    if char == 1:
                        pointer(name)
                        break
                    if char in (0, 2):
                        break
            else:
                out.extend(take({"U8": 1, "U16": 2, "U24": 3, "U32": 4}[kind]))
        if key == (0x1A, 0x0C):
            routines.append((int.from_bytes(out[-4:-1], "little"), out[-1]))
    boundaries[len(data)] = len(out)
    return Decoded(out, pointers, boundaries, opcodes, routines)


def load_native(native_source: Path):
    sys.path.insert(0, str(native_source.resolve()))
    config = importlib.import_module("ebtools.config")
    opcodes = importlib.import_module("ebtools.text_dsl.opcodes")
    doc = config.load_dump_doc(native_source / "earthbound.yml")
    sizes = {
        "U8": "U8", "ITEM": "U8", "WINDOW": "U8", "PARTY": "U8", "MUSIC": "U8", "SFX": "U8", "STATUS_GROUP": "U8",
        "U16": "U16", "FLAG": "U16", "SPRITE": "U16", "MOVEMENT": "U16", "ENEMY_GROUP": "U16", "U24": "U24", "U32": "U32",
        "LABEL": "LABEL", "JUMP_TABLE": "JUMP_TABLE", "STRING": "STRING",
    }
    specs = {key: (op.yaml_name, tuple(sizes[arg.type.name] for arg in op.args)) for key, op in opcodes.OPCODE_BY_BYTES.items()}
    # Exact Redux encodings documented in window_titles.ccs / cc_asmcall.ccs.
    specs.update({
        (0x18, 0x08): ("redux_menu_in_window_no_cancel", ("U8",)),
        (0x1A, 0x00): ("redux_party_select_no_cancel", ("LABEL", "LABEL", "LABEL", "LABEL", "U8")),
        (0x1A, 0x04): ("redux_menu_no_cancel", ()),
        (0x1A, 0x08): ("redux_menu_keep_options_no_cancel", ()),
        (0x1A, 0x09): ("redux_menu_keep_options", ()),
        (0x1A, 0x0B): ("redux_teleport_menu", ()),
        (0x18, 0x0B): ("redux_title_character", ("U8", "U8", "U8")),
        (0x18, 0x0C): ("redux_title_string", ("U8", "LABEL")),
        (0x18, 0x0D): ("redux_status_window", ("U8", "U8")),
        (0x18, 0x0E): ("redux_title_suffix", ("U8", "U8", "U8", "LABEL")),
        (0x18, 0x0F): ("redux_title_prefix", ("U8", "U8", "U8", "LABEL")),
        (0x1A, 0x0C): ("redux_native_routine", ("U24", "U8")),
        (0x1A, 0x0D): ("redux_custom_fadeout", ("U16", "U16", "U16", "U8")),
        (0x1A, 0x0E): ("redux_custom_fadein", ("U16", "U16", "U16", "U8")),
        (0x1A, 0x0F): ("redux_item_determiner", ("U8",)),
        (0x1A, 0x10): ("redux_item_quantity", ("U8",)),
        (0x1A, 0x11): ("redux_character_in_party", ("U8",)),
        (0x1A, 0x18): ("redux_try_give_money", ("U32",)),
        (0x1A, 0x19): ("redux_can_give_money", ("U32",)),
        (0x1A, 0x1A): ("redux_can_deposit_money", ("U32",)),
        (0x1A, 0x21): ("redux_compare_result_argument", ()),
        # Redux adds a character operand to the original 1C 11 command.
        (0x1C, 0x11): ("redux_zero_width_space", ("U8",)),
        (0x1F, 0x60): ("redux_wait_input_timeout", ("U8",)),
    })
    reverse = {value: key for key, value in doc.textTable.items()}
    expansions = [bytes(reverse[ch] for ch in value) for value in doc.compressedTextStrings]
    return doc, specs, expansions


def convert(bridge: dict, project: Path, rom: bytes, native_source: Path) -> tuple[bytes, dict, dict]:
    expected = bridge["roms"]["compiled"]["sha256"].lower()
    if hashlib.sha256(rom).hexdigest() != expected:
        raise ConversionError("Compiled ROM hash does not match bridge manifest")
    for source in bridge["sourceGraph"]["files"]:
        path = project / source["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != source["sha256"].upper():
            raise ConversionError(f"Source differs from compiled inventory: {source['path']}")
    doc, specs, expansions = load_native(native_source)
    by_module = {}
    for label in bridge["labels"]:
        by_module.setdefault(label["module"], []).append(label)
    decoded_rows = []
    failures = []
    excluded = []
    total_ops = Counter()
    routine_calls = Counter()
    address_map = {}
    blob = bytearray()
    original_aliases = {}
    alias_candidates = {}

    for module in sorted(bridge["modules"], key=lambda m: m["name"]):
        source = module["source"]
        if not source or not module["size"]:
            continue
        # Script-heavy areas only; hardware/engine patch modules are converted separately.
        if Path(source).parts[1] not in ("data", "dialogue", "shops", "debug") and module["name"] not in ("window_titles", "item_determiners", "keyitems"):
            continue
        if module["name"] in ("coffee_tea_sequences","flyover_texts","staff_text"):
            excluded.append({"module":module["name"],"kind":"separate-text-format"})
            continue
        classifications = source_labels(project / source)
        labels = by_module.get(module["name"], [])
        grouped = {}
        for label in labels:
            grouped.setdefault(label["snesAddress"], []).append(label)
        addresses = sorted(grouped)
        for i, start in enumerate(addresses):
            names = [row["name"] for row in grouped[start]]
            end = addresses[i+1] if i+1 < len(addresses) else module["snes_address"]+module["size"]
            if not module["snes_address"] <= start < end <= module["snes_address"] + module["size"]:
                failures.append({"module": module["name"], "labels": names, "address": start, "error": "label outside contiguous compiled module"})
                continue
            kinds = {classifications.get(name, "unclassified") for name in names}
            if "assembly" in kinds or "raw-data" in kinds or kinds == {"unclassified"}:
                excluded.append({"module": module["name"], "labels": names, "address": start, "kind": ",".join(sorted(kinds))})
                continue
            offset = start - 0xC00000
            try:
                decoded = relocate_bytes(rom[offset:offset+end-start], specs, expansions)
            except ConversionError as error:
                failures.append({"module": module["name"], "labels": names, "address": start, "error": str(error)})
                continue
            flat = BLOB_BASE + len(blob)
            address_map[start] = flat
            for original_off, output_off in decoded.boundaries.items():
                if original_off < end-start:
                    address_map[start+original_off] = flat+output_off
            for name in names:
                original_match = ORIGINAL_LABEL.fullmatch(name)
                if original_match:
                    original = int(original_match[1], 16)
                    alias_candidates.setdefault(original, []).append((start,flat))
            decoded_rows.append((module["name"], start, len(blob), decoded))
            blob.extend(decoded.data)
            total_ops.update(decoded.opcodes)
            routine_calls.update(decoded.routines)

    alias_conflicts = []
    for original, candidates in sorted(alias_candidates.items()):
        unique = set(candidates)
        if len(unique) == 1:
            original_aliases[original] = candidates[0][1]
            continue
        off = original-0xC00000
        target = int.from_bytes(rom[off+1:off+5],"little") if 0 <= off < len(rom)-5 and rom[off] in (0x08,0x0A) else None
        matched = [flat for address,flat in unique if address == target]
        if len(matched) == 1:
            original_aliases[original] = matched[0]
        else:
            alias_conflicts.append({"originalAddress":original,"candidates":[{"compiledAddress":address,"nativeAddress":flat} for address,flat in sorted(unique)],"patchedEntryTarget":target})

    unresolved = Counter()
    relocated = 0
    for module, start, output_start, decoded in decoded_rows:
        for offset, target, purpose in decoded.pointers:
            replacement = address_map.get(target, original_aliases.get(target))
            if target == 0:
                continue
            if replacement is None:
                unresolved[(target, purpose)] += 1
                continue
            blob[output_start+offset:output_start+offset+4] = replacement.to_bytes(4,"little")
            relocated += 1

    all_label_names = {}
    for label in bridge["labels"]:
        all_label_names.setdefault(label["snesAddress"], []).append(label["module"]+"."+label["name"])
    routines = [{"address": address, "names": all_label_names.get(address, []), "returnType": ret, "calls": count, "nativeStatus": "unported"} for (address, ret), count in sorted(routine_calls.items())]
    report = {
        "format": "maternalbound-native-dialogue-report-v1",
        "status": "development-only-not-playable",
        "compiledRomSha256": expected.upper(),
        "counts": {"convertedLabelSpans": len(decoded_rows), "convertedBytes": len(blob), "relocatedPointerFields": relocated, "unresolvedPointerFields": sum(unresolved.values()), "failedLabelSpans": len(failures), "excludedAssemblyOrUnclassifiedSpans": len(excluded), "nativeRoutineCalls": sum(routine_calls.values()), "nativeRoutineVariants": len(routines), "ambiguousOriginalAliases": len(alias_conflicts)},
        "nativeCustomHandlers": ["redux_try_give_money", "redux_can_give_money", "redux_can_deposit_money", "redux_character_in_party", "redux_compare_result_argument", "redux_title_string"],
        "remainingCustomCommands": sorted(name for name in total_ops if name.startswith("redux_") and name not in {"redux_try_give_money", "redux_can_give_money", "redux_can_deposit_money", "redux_character_in_party", "redux_compare_result_argument", "redux_title_string", "redux_party_select_no_cancel", "redux_menu_no_cancel", "redux_menu_keep_options_no_cancel", "redux_menu_keep_options", "redux_teleport_menu", "redux_status_window"}),
        "blobSha256": hashlib.sha256(blob).hexdigest().upper(),
        "opcodes": dict(sorted(total_ops.items())),
        "failures": failures,
        "unresolvedTargets": [{"address": target, "names": all_label_names.get(target, []), "purpose": purpose, "references": count} for (target, purpose), count in sorted(unresolved.items())],
        "nativeRoutines": routines,
        "unresolvedOriginalAliases": alias_conflicts,
        "excluded": excluded,
    }
    relocation = {"format": "maternalbound-native-dialogue-relocations-v1", "status": report["status"], "blobSha256": report["blobSha256"], "compiledAddresses": {f"{addr:06X}": dest for addr,dest in sorted(address_map.items())}, "originalAddresses": {f"{addr:06X}": dest for addr,dest in sorted(original_aliases.items())}}
    return bytes(blob), report, relocation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--compiled-rom", required=True, type=Path)
    parser.add_argument("--native-source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    blob, report, relocation = convert(json.loads(args.bridge.read_text()),args.project,args.compiled_rom.read_bytes(),args.native_source)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir / "dialogue.bin").write_bytes(blob)
    (args.output_dir / "dialogue-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    (args.output_dir / "dialogue-relocations.json").write_text(json.dumps(relocation,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"],indent=2))
    print(f"Development output: {args.output_dir}; not yet a playable asset pack")


if __name__ == "__main__":
    main()
