"""Export the original Companion artwork as a multi-resolution Windows ICO."""
from pathlib import Path
import argparse
from PIL import Image

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)

def build(source: Path, destination: Path) -> None:
    with Image.open(source) as artwork:
        if artwork.width != artwork.height or artwork.mode != 'RGBA':
            raise ValueError('Use square RGBA artwork with a transparent background.')
        alpha = artwork.getchannel('A')
        if alpha.getextrema() != (0, 255):
            raise ValueError('The artwork must retain actual transparency.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        artwork.save(destination, format='ICO', sizes=[(size, size) for size in SIZES])
    with Image.open(destination) as icon:
        if icon.ico.sizes() != {(size, size) for size in SIZES}:
            raise ValueError('The ICO is missing a requested Windows size.')

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=root/'Companion/Assets/earthbound-companion.png')
    parser.add_argument('--destination', type=Path, default=root/'Companion/Assets/earthbound-companion.ico')
    arguments = parser.parse_args()
    build(arguments.source, arguments.destination)
    print(f'Wrote {arguments.destination}: {", ".join(str(size) for size in SIZES)} px.')
