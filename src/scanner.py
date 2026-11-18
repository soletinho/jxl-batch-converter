"""
Image Scanner module.
Discovers convertible image files in directories.
"""

from pathlib import Path
from typing import List, Set, Generator

SUPPORTED_EXTENSIONS: Set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def is_supported_image(file_path: Path) -> bool:
    """Check if the given file has a supported image extension."""
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def scan_images(
    directory: Path,
    recursive: bool = True,
    skip_existing_jxl: bool = True,
    destination_dir: Path | None = None
) -> List[Path]:
    """
    Scan directory for images to convert.

    :param directory: Root directory to scan.
    :param recursive: If True, search subdirectories.
    :param skip_existing_jxl: If True, do not include images that already have a corresponding .jxl.
    :param destination_dir: If specified, check existing .jxl in destination instead of same dir.
    :return: Sorted list of Path objects for discovered images.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    pattern = "**/*" if recursive else "*"
    candidates: List[Path] = []

    for item in directory.glob(pattern):
        if not item.is_file():
            continue
        if not is_supported_image(item):
            continue

        if skip_existing_jxl:
            if destination_dir:
                rel = item.relative_to(directory)
                target_jxl = destination_dir / rel.with_suffix(".jxl")
            else:
                target_jxl = item.with_suffix(".jxl")

            if target_jxl.exists() and target_jxl.stat().st_size > 0:
                continue

        candidates.append(item)

    return sorted(candidates)
