"""
Downloader module for libjxl tools (cjxl and djxl).
Automatically manages and downloads precompiled static binaries for Windows x64.
"""

import os
import sys
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Callable

LIBJXL_VERSION = "v0.13.0"
LIBJXL_WIN_X64_ZIP = (
    f"https://github.com/libjxl/libjxl/releases/download/{LIBJXL_VERSION}/jxl-x64-windows-static.zip"
)
LIBJXL_WIN_X64_7Z = (
    f"https://github.com/libjxl/libjxl/releases/download/{LIBJXL_VERSION}/jxl-x64-windows-static.7z"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = PROJECT_ROOT / "bin"


def get_binary_path(binary_name: str = "cjxl") -> Optional[Path]:
    """
    Search for binary in local bin directory first, then system PATH.
    """
    ext = ".exe" if sys.platform.startswith("win") else ""
    full_name = f"{binary_name}{ext}"

    # 1. Check local bin/ folder
    local_bin = BIN_DIR / full_name
    if local_bin.is_file() and os.access(local_bin, os.X_OK):
        return local_bin

    # 2. Check system PATH
    system_path = shutil.which(full_name)
    if system_path:
        return Path(system_path)

    return None


def is_cjxl_available() -> bool:
    """Return True if cjxl executable is found."""
    return get_binary_path("cjxl") is not None


def download_libjxl_windows(
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Path:
    """
    Download and extract cjxl.exe and djxl.exe into the bin/ folder.
    """
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    seven_zip = shutil.which("7z") or shutil.which("7za")

    # If 7z is installed, prefer the smaller .7z file (8MB vs 40MB)
    if seven_zip:
        download_url = LIBJXL_WIN_X64_7Z
        target_archive = BIN_DIR / "jxl-windows-static.7z"
    else:
        download_url = LIBJXL_WIN_X64_ZIP
        target_archive = BIN_DIR / "jxl-windows-static.zip"

    def report_hook(block_num: int, block_size: int, total_size: int):
        downloaded = block_num * block_size
        if progress_callback:
            progress_callback(
                min(downloaded, total_size),
                total_size,
                f"Baixando ferramentas JPEG XL ({LIBJXL_VERSION})..."
            )

    try:
        if progress_callback:
            progress_callback(0, 0, f"Iniciando download do libjxl ({LIBJXL_VERSION})...")

        urllib.request.urlretrieve(
            download_url,
            str(target_archive),
            reporthook=report_hook if progress_callback else None
        )

        if progress_callback:
            progress_callback(100, 100, "Extraindo executáveis...")

        extracted = False

        # Try 7z / NanaZip if available
        if seven_zip:
            res = subprocess.run(
                [seven_zip, "e", str(target_archive), f"-o{BIN_DIR}", "cjxl.exe", "djxl.exe", "-r", "-y"],
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                extracted = True

        # Fallback to tar if still not extracted
        if not extracted and shutil.which("tar"):
            try:
                subprocess.run(
                    ["tar", "-xf", str(target_archive), "-C", str(BIN_DIR)],
                    check=True,
                    capture_output=True
                )
                # Look for extracted cjxl.exe recursively and move to bin/
                for found in BIN_DIR.glob("**/cjxl.exe"):
                    if found != BIN_DIR / "cjxl.exe":
                        shutil.move(str(found), str(BIN_DIR / "cjxl.exe"))
                for found in BIN_DIR.glob("**/djxl.exe"):
                    if found != BIN_DIR / "djxl.exe":
                        shutil.move(str(found), str(BIN_DIR / "djxl.exe"))
                extracted = True
            except Exception:
                pass

        if target_archive.exists():
            target_archive.unlink()

        cjxl_path = BIN_DIR / "cjxl.exe"
        if not cjxl_path.exists():
            raise FileNotFoundError("Não foi possível extrair cjxl.exe. Verifique se o 7-Zip ou tar está instalado.")

        if progress_callback:
            progress_callback(100, 100, "Ferramentas JPEG XL instaladas com sucesso!")

        return cjxl_path

    except Exception as exc:
        if target_archive.exists():
            try:
                target_archive.unlink()
            except OSError:
                pass
        raise RuntimeError(f"Falha ao obter libjxl: {exc}") from exc


def ensure_cjxl(progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Path:
    """
    Ensure cjxl binary is available. Downloads automatically on Windows x64 if missing.
    """
    existing = get_binary_path("cjxl")
    if existing:
        return existing

    if sys.platform.startswith("win") and platform.machine().lower() in ("amd64", "x86_64"):
        return download_libjxl_windows(progress_callback)

    raise FileNotFoundError(
        "O executável 'cjxl' não foi encontrado no sistema ou em bin/. "
        "Adicione cjxl ao PATH ou à pasta bin/."
    )
