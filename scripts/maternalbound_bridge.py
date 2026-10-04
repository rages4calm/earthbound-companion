"""Build an auditable bridge manifest for a native MaternalBound Redux port.

This tool consumes CoilSnake's CCScript compilation summary and the ROM used as
the compile base.  It does not claim that 65816 routines are natively ported.
It gives the C port a deterministic inventory of every relocated module and
label, plus byte-level evidence for the compiled output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


MODULE_ROW = re.compile(r"^(?P<name>.+?)\s+\$(?P<address>[0-9a-fA-F]+)\s+(?P<size>\d+)\s+bytes$")
LABEL_HEADER = re.compile(r"^Labels in module (?P<name>.+)$")
LABEL_ROW = re.compile(r"^(?P<name>.+?)\s+\$(?P<address>[0-9a-fA-F]+)$")
IMPORT_ROW = re.compile(r'^\s*import\s+"(?P<path>[^"]+)"', re.MULTILINE)


@dataclass(frozen=True)
class Module:
    name: str
    snes_address: int
    rom_offset: int
    size: int
    source: str | None
    changed_bytes: int
    compiled_sha256: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def snes_to_rom(address: int) -> int:
    return address - 0xC00000 if address >= 0xC00000 else address


def parse_summary(text: str) -> tuple[list[tuple[str, int, int]], dict[str, list[tuple[str, int]]]]:
    modules: list[tuple[str, int, int]] = []
    labels: dict[str, list[tuple[str, int]]] = {}
    in_module_table = False
    current_labels: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line == "Module information":
            in_module_table = True
            current_labels = None
            continue

        header = LABEL_HEADER.match(line)
        if header:
            in_module_table = False
            current_labels = header.group("name").strip()
            labels.setdefault(current_labels, [])
            continue

        if in_module_table:
            match = MODULE_ROW.match(line)
            if match:
                modules.append(
                    (
                        match.group("name").strip(),
                        int(match.group("address"), 16),
                        int(match.group("size")),
                    )
                )
            continue

        if current_labels:
            match = LABEL_ROW.match(line)
            if match:
                labels[current_labels].append(
                    (match.group("name").strip(), int(match.group("address"), 16))
                )

    if not modules:
        raise ValueError("No CCScript modules found in summary")
    return modules, labels


def index_sources(project: Path) -> tuple[dict[str, str], dict[str, object]]:
    ccscript = project / "ccscript"
    main = ccscript / "main.ccs"
    if not main.is_file():
        return {}, {"files": [], "imports": [], "unresolvedImports": [], "duplicateModuleNames": {}}

    sources: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}
    imports: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    files: list[dict[str, object]] = []
    root = ccscript.resolve()
    pending = [main.resolve()]
    visited: set[Path] = set()

    while pending:
        source = pending.pop()
        if source in visited:
            continue
        visited.add(source)
        try:
            relative = source.relative_to(project.resolve()).as_posix()
        except ValueError:
            continue
        data = source.read_bytes()
        category_parts = Path(relative).parts
        category = category_parts[1] if len(category_parts) > 2 else "root"
        files.append({"path": relative, "sha256": sha256(data), "size": len(data), "category": category})
        stem = source.stem
        if stem in sources and sources[stem] != relative:
            duplicates.setdefault(stem, [sources[stem]]).append(relative)
        else:
            sources[stem] = relative

        text = data.decode("utf-8", errors="replace")
        for match in IMPORT_ROW.finditer(text):
            requested = match.group("path")
            target = (source.parent / requested).resolve()
            try:
                target_relative = target.relative_to(root)
            except ValueError:
                unresolved.append({"source": relative, "requested": requested, "reason": "outside-ccscript-root"})
                continue
            if not target.is_file():
                unresolved.append({"source": relative, "requested": requested, "reason": "missing"})
                continue
            target_project_path = (Path("ccscript") / target_relative).as_posix()
            imports.append({"source": relative, "target": target_project_path})
            if target not in visited:
                pending.append(target)

    files.sort(key=lambda row: str(row["path"]).lower())
    imports.sort(key=lambda row: (row["source"].lower(), row["target"].lower()))
    unresolved.sort(key=lambda row: (row["source"].lower(), row["requested"].lower()))
    category_counts: dict[str, int] = {}
    for row in files:
        category = str(row["category"])
        category_counts[category] = category_counts.get(category, 0) + 1
    return sources, {
        "entrypoint": "ccscript/main.ccs",
        "files": files,
        "imports": imports,
        "unresolvedImports": unresolved,
        "duplicateModuleNames": dict(sorted(duplicates.items())),
        "categoryCounts": dict(sorted(category_counts.items())),
    }


def git_revision(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def count_diff_ranges(base: bytes, output: bytes) -> tuple[int, int]:
    changed_bytes = 0
    ranges = 0
    active = False
    for index in range(max(len(base), len(output))):
        changed = index >= len(base) or index >= len(output) or base[index] != output[index]
        if changed:
            changed_bytes += 1
            if not active:
                ranges += 1
                active = True
        else:
            active = False
    return changed_bytes, ranges


def build_manifest(summary: Path, project: Path, base_rom: Path, output_rom: Path) -> dict[str, object]:
    base = base_rom.read_bytes()
    output = output_rom.read_bytes()
    parsed_modules, labels = parse_summary(summary.read_text(encoding="utf-8", errors="replace"))
    sources, source_graph = index_sources(project)

    modules: list[Module] = []
    for name, address, size in parsed_modules:
        offset = snes_to_rom(address)
        end = offset + size
        if size and end > len(output):
            raise ValueError(f"Module {name} exceeds output ROM: 0x{offset:X}+{size}")
        compiled = output[offset:end] if size else b""
        baseline = base[offset:end]
        changed = sum(a != b for a, b in zip(compiled, baseline)) + max(0, len(compiled) - len(baseline))
        modules.append(
            Module(
                name=name,
                snes_address=address,
                rom_offset=offset,
                size=size,
                source=sources.get(name),
                changed_bytes=changed,
                compiled_sha256=sha256(compiled),
            )
        )

    label_rows = [
        {"module": module, "name": name, "snesAddress": address, "romOffset": snes_to_rom(address)}
        for module in sorted(labels)
        for name, address in labels[module]
    ]
    changed_bytes, changed_ranges = count_diff_ranges(base, output)
    source_root = project.parent
    return {
        "format": "earthbound-companion-maternalbound-bridge-v1",
        "status": "inventory-only-native-port-incomplete",
        "source": {
            "project": project.as_posix(),
            "revision": git_revision(source_root),
            "summarySha256": sha256(summary.read_bytes()),
        },
        "roms": {
            "base": {"size": len(base), "sha256": sha256(base)},
            "compiled": {"size": len(output), "sha256": sha256(output)},
            "changedBytes": changed_bytes,
            "contiguousChangedRanges": changed_ranges,
        },
        "counts": {
            "modules": len(modules),
            "nonemptyModules": sum(module.size > 0 for module in modules),
            "labels": len(label_rows),
            "modulesWithMappedSource": sum(module.source is not None for module in modules),
            "reachableSourceFiles": len(source_graph["files"]),
            "sourceImports": len(source_graph["imports"]),
            "unresolvedSourceImports": len(source_graph["unresolvedImports"]),
        },
        "sourceGraph": source_graph,
        "modules": [asdict(module) for module in modules],
        "labels": label_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--base-rom", required=True, type=Path)
    parser.add_argument("--compiled-rom", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = build_manifest(args.summary, args.project, args.base_rom, args.compiled_rom)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    counts = manifest["counts"]
    print(
        f"Wrote {args.output}: {counts['modules']} modules, "
        f"{counts['labels']} labels, {counts['modulesWithMappedSource']} mapped sources"
    )


if __name__ == "__main__":
    main()
