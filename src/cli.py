"""
Command Line Interface (CLI) for JXL Batch Converter.
"""

import sys
import argparse
from pathlib import Path
from src.downloader import ensure_cjxl
from src.scanner import scan_images
from src.engine import JXLEngine, ConversionConfig, ConversionResult
from src.reporter import ConversionReport, format_bytes


def run_cli(args_list=None):
    parser = argparse.ArgumentParser(
        prog="jxl-batch-converter",
        description="Otimizador e Conversor de Imagens em Lote para JPEG XL (.jxl)"
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Pasta de entrada contendo as imagens para converter."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Pasta de destino (opcional). Se omitida, os arquivos .jxl serão salvos na mesma pasta."
    )
    parser.add_argument(
        "-q", "--quality",
        type=str,
        default="lossless",
        help="Modo de qualidade: 'lossless' (padrão) ou um número de 1 a 100."
    )
    parser.add_argument(
        "-e", "--effort",
        type=int,
        default=7,
        help="Nível de esforço do encoder (1 a 10, padrão: 7)."
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Não verificar subpastas (apenas arquivos na raiz da pasta de entrada)."
    )
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="Excluir arquivos originais após conversão bem-sucedida (ATENÇÃO: irreversível)."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescrever arquivos .jxl se já existirem."
    )
    parser.add_argument(
        "--report-html",
        type=str,
        default=None,
        help="Caminho para salvar o relatório detalhado em HTML."
    )
    parser.add_argument(
        "--report-csv",
        type=str,
        default=None,
        help="Caminho para salvar o relatório em CSV."
    )

    args = parser.parse_args(args_list)

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"Erro: A pasta de entrada '{input_dir}' não existe.", file=sys.stderr)
        sys.exit(1)

    dest_dir = Path(args.output) if args.output else None

    # Parse quality
    quality_str = str(args.quality).strip().lower()
    if quality_str == "lossless":
        quality_mode = "lossless"
        quality_val = 90
    else:
        try:
            quality_val = int(quality_str)
            if not (1 <= quality_val <= 100):
                raise ValueError()
            quality_mode = "custom"
        except ValueError:
            print("Erro: --quality deve ser 'lossless' ou um número entre 1 e 100.", file=sys.stderr)
            sys.exit(1)

    config = ConversionConfig(
        quality_mode=quality_mode,
        quality=quality_val,
        effort=args.effort,
        destination_dir=dest_dir,
        keep_original=not args.delete_originals,
        delete_original=args.delete_originals,
        overwrite=args.overwrite
    )

    print("Verificando motor cjxl...")
    cjxl_bin = ensure_cjxl()
    engine = JXLEngine(cjxl_bin)

    print(f"Escaneando imagens em: {input_dir}...")
    files = scan_images(
        input_dir,
        recursive=not args.no_recursive,
        skip_existing_jxl=not args.overwrite,
        destination_dir=dest_dir
    )

    total_files = len(files)
    if total_files == 0:
        print("Nenhuma imagem para converter encontrada.")
        return

    print(f"Encontradas {total_files} imagens. Iniciando conversão...\n")

    def progress_callback(idx: int, tot: int, res: ConversionResult):
        status_sym = "✓" if res.status == "success" else ("-" if res.status == "skipped" else "✗")
        saved_str = f"(-{res.saved_percentage:.1f}%)" if res.status == "success" else ""
        print(f"[{idx}/{tot}] {status_sym} {res.input_path.name} -> {format_bytes(res.converted_size)} {saved_str}")

    results = engine.batch_convert(
        files=files,
        source_root=input_dir,
        config=config,
        progress_callback=progress_callback
    )

    report = ConversionReport(results, input_dir)
    print("\n" + report.generate_text_summary())

    if args.report_html:
        html_out = report.export_html(Path(args.report_html))
        print(f"\nRelatório HTML salvo em: {html_out}")

    if args.report_csv:
        csv_out = report.export_csv(Path(args.report_csv))
        print(f"Relatório CSV salvo em: {csv_out}")


if __name__ == "__main__":
    run_cli()
