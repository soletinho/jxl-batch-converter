"""
Conversion Engine for JPEG XL.
Wraps cjxl executable calls, handles conversions, options, and returns detailed metrics.
"""

import time
import subprocess
import shutil
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, List

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from src.downloader import ensure_cjxl


@dataclass
class ConversionConfig:
    quality_mode: str = "lossless"  # "lossless" or "custom"
    quality: int = 90               # 1-100 when quality_mode == "custom"
    effort: int = 7                 # 1-10 (default 7)
    destination_dir: Optional[Path] = None  # None = same directory as source
    keep_original: bool = True
    delete_original: bool = False
    backup_dir: Optional[Path] = None
    overwrite: bool = False


@dataclass
class ConversionResult:
    input_path: Path
    output_path: Optional[Path]
    original_size: int = 0
    converted_size: int = 0
    saved_bytes: int = 0
    saved_percentage: float = 0.0
    status: str = "pending"  # "success", "skipped", "error"
    error_message: Optional[str] = None
    duration_ms: float = 0.0


class JXLEngine:
    def __init__(self, cjxl_path: Optional[Path] = None):
        self.cjxl_path = cjxl_path or ensure_cjxl()

    def build_command(self, input_file: Path, output_file: Path, config: ConversionConfig) -> List[str]:
        """
        Build command arguments for cjxl.
        Format: cjxl INPUT OUTPUT [options]
        """
        suffix = input_file.suffix.lower()
        needs_stream = suffix in (".webp", ".bmp", ".tif", ".tiff")
        input_target = "-" if needs_stream else str(input_file)

        cmd = [str(self.cjxl_path), input_target, str(output_file), "--quiet"]

        # Effort
        cmd.extend(["-e", str(config.effort)])

        if config.quality_mode == "lossless":
            if suffix in (".jpg", ".jpeg"):
                # Default for jpeg is lossless transcode (-d 0.0)
                cmd.extend(["-d", "0.0"])
            else:
                # Lossless for PNG, GIF, WebP, BMP
                cmd.extend(["-d", "0.0"])
        else:
            # Custom quality (1-100)
            cmd.extend(["-q", str(config.quality)])

        return cmd

    def convert_file(
        self,
        input_file: Path,
        source_root: Path,
        config: ConversionConfig
    ) -> ConversionResult:
        """
        Convert a single image to .jxl.
        """
        input_file = Path(input_file)
        if not input_file.exists():
            return ConversionResult(
                input_path=input_file,
                output_path=None,
                status="error",
                error_message="Arquivo original não encontrado."
            )

        original_size = input_file.stat().st_size

        # Determine target output path
        if config.destination_dir:
            try:
                rel = input_file.relative_to(source_root)
            except ValueError:
                rel = Path(input_file.name)
            output_file = Path(config.destination_dir) / rel.with_suffix(".jxl")
        else:
            output_file = input_file.with_suffix(".jxl")

        # Create parent directories if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if output already exists
        if output_file.exists() and not config.overwrite:
            conv_size = output_file.stat().st_size
            saved = original_size - conv_size
            pct = (saved / original_size * 100) if original_size > 0 else 0.0
            return ConversionResult(
                input_path=input_file,
                output_path=output_file,
                original_size=original_size,
                converted_size=conv_size,
                saved_bytes=saved,
                saved_percentage=pct,
                status="skipped",
                error_message="Arquivo .jxl já existente."
            )

        cmd = self.build_command(input_file, output_file, config)

        # Check if streaming through stdin is needed (e.g. for WebP, BMP, TIFF)
        stdin_data = None
        suffix = input_file.suffix.lower()
        if suffix in (".webp", ".bmp", ".tif", ".tiff"):
            if not HAS_PILLOW:
                return ConversionResult(
                    input_path=input_file,
                    output_path=None,
                    original_size=original_size,
                    status="error",
                    error_message="O formato WebP/BMP requer a biblioteca Pillow instalada (pip install pillow)."
                )
            try:
                buf = io.BytesIO()
                with Image.open(input_file) as im:
                    im.save(buf, format="PNG")
                stdin_data = buf.getvalue()
            except Exception as exc:
                return ConversionResult(
                    input_path=input_file,
                    output_path=None,
                    original_size=original_size,
                    status="error",
                    error_message=f"Falha ao decodificar imagem: {exc}"
                )

        start_time = time.perf_counter()
        try:
            # On Windows, prevent console window popup when launched from GUI
            creationflags = 0
            import sys
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                creationflags=creationflags
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if proc.returncode != 0:
                stderr_str = proc.stderr.decode("utf-8", errors="replace").strip() if proc.stderr else ""
                err_msg = stderr_str or f"Código de saída: {proc.returncode}"
                return ConversionResult(
                    input_path=input_file,
                    output_path=None,
                    original_size=original_size,
                    status="error",
                    error_message=err_msg,
                    duration_ms=elapsed_ms
                )

            if not output_file.exists() or output_file.stat().st_size == 0:
                return ConversionResult(
                    input_path=input_file,
                    output_path=None,
                    original_size=original_size,
                    status="error",
                    error_message="Arquivo de saída não gerado ou vazio.",
                    duration_ms=elapsed_ms
                )

            converted_size = output_file.stat().st_size
            saved = original_size - converted_size
            pct = (saved / original_size * 100) if original_size > 0 else 0.0

            # Handle original file actions (backup or delete)
            if config.backup_dir:
                try:
                    rel_backup = input_file.relative_to(source_root)
                except ValueError:
                    rel_backup = Path(input_file.name)
                backup_target = Path(config.backup_dir) / rel_backup
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(input_file), str(backup_target))
            elif config.delete_original:
                input_file.unlink()

            return ConversionResult(
                input_path=input_file,
                output_path=output_file,
                original_size=original_size,
                converted_size=converted_size,
                saved_bytes=saved,
                saved_percentage=pct,
                status="success",
                duration_ms=elapsed_ms
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ConversionResult(
                input_path=input_file,
                output_path=None,
                original_size=original_size,
                status="error",
                error_message=str(exc),
                duration_ms=elapsed_ms
            )

    def batch_convert(
        self,
        files: List[Path],
        source_root: Path,
        config: ConversionConfig,
        progress_callback: Optional[Callable[[int, int, ConversionResult], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> List[ConversionResult]:
        """
        Process a list of files sequentially or report progress.
        """
        results: List[ConversionResult] = []
        total = len(files)

        for index, file_path in enumerate(files, start=1):
            if cancel_check and cancel_check():
                break

            result = self.convert_file(file_path, source_root, config)
            results.append(result)

            if progress_callback:
                progress_callback(index, total, result)

        return results
