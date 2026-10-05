"""Copy player documentation, keeping links valid outside the source checkout."""
from pathlib import Path
import argparse
import re
from urllib.parse import quote, urlsplit

DOCUMENTS = {
    name: name for name in (
        "README.md", "RANDOMIZER.md", "CREDITS.md", "LEGAL.md",
        "MATERNALBOUND-NATIVE.md", "UPSTREAM.md", "LICENSE.md", "RESEARCH.md"
    )
}
DOCUMENTS["distribution/PACKAGE-NOTES.md"] = "PACKAGE-NOTES.md"
REPOSITORY = "https://github.com/rages4calm/earthbound-companion"

def prepare(source: Path, destination: Path) -> list[Path]:
    source, destination = source.resolve(), destination.resolve()
    if source == destination:
        raise ValueError("Use a separate package destination.")
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for original, filename in DOCUMENTS.items():
        path = source / original
        contents = path.read_text(encoding="utf-8-sig")
        def target(value: str, image: bool = False) -> str:
            parsed = urlsplit(value)
            if not value or value.startswith("#") or parsed.scheme or parsed.netloc:
                return value
            resolved = (path.parent / parsed.path).resolve()
            if not resolved.is_relative_to(source) or not resolved.exists():
                raise ValueError(f"Missing or external local link in {original}: {value}")
            relative = resolved.relative_to(source).as_posix()
            if relative in DOCUMENTS and not image:
                result = DOCUMENTS[relative]
            else:
                category = "raw/refs/heads/main" if image else "tree/main" if resolved.is_dir() else "blob/main"
                result = f"{REPOSITORY}/{category}/{quote(relative, safe='/')}"
            if parsed.query:
                result += "?" + parsed.query
            if parsed.fragment:
                result += "#" + parsed.fragment
            return result
        contents = re.sub(r'(!?)\[([^\]]*)\]\(([^\s)]+)\)',
                          lambda m: f"{m[1]}[{m[2]}]({target(m[3], bool(m[1]))})", contents)
        contents = re.sub(r'\b(src|href)="([^"]+)"',
                          lambda m: f'{m[1]}="{target(m[2], m[1] == "src")}"', contents)
        output = destination / filename
        output.write_text(contents, encoding="utf-8", newline="\n")
        copied.append(output)
    return copied

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    arguments = parser.parse_args()
    print(f"Prepared {len(prepare(arguments.source, arguments.destination))} documentation files.")
