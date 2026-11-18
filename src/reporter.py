"""
Reporter module for JPEG XL batch conversion.
Calculates space savings, summary metrics, and exports reports to HTML, Markdown, and CSV.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from src.engine import ConversionResult


def format_bytes(size: int | float) -> str:
    """Format bytes into a human-readable string (e.g. 1.25 MB)."""
    if size < 0:
        return f"-{format_bytes(-size)}"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.2f} TB"


class ConversionReport:
    def __init__(self, results: List[ConversionResult], source_dir: Path | str):
        self.results = results
        self.source_dir = Path(source_dir)
        self.timestamp = datetime.now()
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> Dict[str, Any]:
        total_files = len(self.results)
        successful = [r for r in self.results if r.status == "success"]
        skipped = [r for r in self.results if r.status == "skipped"]
        errors = [r for r in self.results if r.status == "error"]

        total_orig_bytes = sum(r.original_size for r in successful)
        total_conv_bytes = sum(r.converted_size for r in successful)
        total_saved_bytes = total_orig_bytes - total_conv_bytes
        saved_pct = (
            (total_saved_bytes / total_orig_bytes * 100) if total_orig_bytes > 0 else 0.0
        )
        total_time_ms = sum(r.duration_ms for r in self.results)

        return {
            "total_files": total_files,
            "success_count": len(successful),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "total_original_bytes": total_orig_bytes,
            "total_converted_bytes": total_conv_bytes,
            "total_saved_bytes": total_saved_bytes,
            "saved_percentage": saved_pct,
            "total_duration_sec": total_time_ms / 1000.0,
        }

    def generate_text_summary(self) -> str:
        m = self.metrics
        lines = [
            "==================================================",
            "         RELATÓRIO DE CONVERSÃO JPEG XL          ",
            "==================================================",
            f"Diretório de Origem: {self.source_dir}",
            f"Data e Hora:        {self.timestamp.strftime('%d/%m/%Y %H:%M:%S')}",
            f"Total de Imagens:   {m['total_files']}",
            f"  - Convertidas:    {m['success_count']}",
            f"  - Ignoradas:      {m['skipped_count']}",
            f"  - Com Erro:       {m['error_count']}",
            "--------------------------------------------------",
            f"Tamanho Original:   {format_bytes(m['total_original_bytes'])}",
            f"Tamanho em JXL:     {format_bytes(m['total_converted_bytes'])}",
            f"Espaço Economizado: {format_bytes(m['total_saved_bytes'])} ({m['saved_percentage']:.2f}%)",
            f"Tempo Total:        {m['total_duration_sec']:.2f} segundos",
            "==================================================",
        ]
        return "\n".join(lines)

    def export_csv(self, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Arquivo Original",
                "Arquivo JXL",
                "Status",
                "Tamanho Original (Bytes)",
                "Tamanho Original",
                "Tamanho JXL (Bytes)",
                "Tamanho JXL",
                "Economia (Bytes)",
                "Economia (%)",
                "Tempo (ms)",
                "Mensagem/Erro",
            ])
            for r in self.results:
                writer.writerow([
                    str(r.input_path),
                    str(r.output_path) if r.output_path else "",
                    r.status,
                    r.original_size,
                    format_bytes(r.original_size),
                    r.converted_size,
                    format_bytes(r.converted_size),
                    r.saved_bytes,
                    f"{r.saved_percentage:.2f}%",
                    f"{r.duration_ms:.1f}",
                    r.error_message or "",
                ])
        return output_path

    def export_html(self, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m = self.metrics

        rows_html = []
        for r in self.results:
            status_badge = (
                '<span class="badge success">Sucesso</span>'
                if r.status == "success"
                else (
                    '<span class="badge skipped">Ignorado</span>'
                    if r.status == "skipped"
                    else '<span class="badge error">Erro</span>'
                )
            )
            pct_class = "saved-positive" if r.saved_percentage > 0 else "saved-neutral"
            rows_html.append(f"""
            <tr>
                <td title="{r.input_path}">{r.input_path.name}</td>
                <td>{status_badge}</td>
                <td>{format_bytes(r.original_size)}</td>
                <td>{format_bytes(r.converted_size)}</td>
                <td class="{pct_class}">{format_bytes(r.saved_bytes)} ({r.saved_percentage:.1f}%)</td>
                <td>{r.duration_ms:.0f} ms</td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Conversão JPEG XL</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --accent: #818cf8;
            --success: #34d399;
            --warning: #fbbf24;
            --danger: #f87171;
            --border: #334155;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 2rem; }}
        h1 {{ font-size: 2rem; font-weight: 700; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }}
        .meta {{ color: var(--text-muted); margin-top: 0.5rem; font-size: 0.95rem; }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .card-title {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
        .card-value {{ font-size: 1.8rem; font-weight: 700; margin-top: 0.25rem; color: var(--text); }}
        .card-value.highlight {{ color: var(--success); }}
        .progress-bar-container {{
            background: var(--surface);
            border-radius: 9999px;
            height: 12px;
            overflow: hidden;
            margin: 1.5rem 0;
            border: 1px solid var(--border);
        }}
        .progress-bar-fill {{
            background: linear-gradient(90deg, var(--primary), var(--success));
            height: 100%;
            width: {min(max(m['saved_percentage'], 0), 100):.1f}%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        th, td {{ padding: 0.85rem 1rem; text-align: left; font-size: 0.9rem; }}
        th {{ background: #162032; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--border); }}
        tr:not(:last-child) td {{ border-bottom: 1px solid var(--border); }}
        tr:hover td {{ background: var(--surface-hover); }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge.success {{ background: rgba(52, 211, 153, 0.15); color: var(--success); }}
        .badge.skipped {{ background: rgba(251, 191, 36, 0.15); color: var(--warning); }}
        .badge.error {{ background: rgba(248, 113, 113, 0.15); color: var(--danger); }}
        .saved-positive {{ color: var(--success); font-weight: 600; }}
        .saved-neutral {{ color: var(--text-muted); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Relatório de Otimização JPEG XL</h1>
            <div class="meta">
                <span>Pasta: <strong>{self.source_dir}</strong></span> •
                <span>Data: <strong>{self.timestamp.strftime('%d/%m/%Y às %H:%M:%S')}</strong></span>
            </div>
        </header>

        <div class="cards">
            <div class="card">
                <div class="card-title">Espaço Economizado</div>
                <div class="card-value highlight">{format_bytes(m['total_saved_bytes'])}</div>
            </div>
            <div class="card">
                <div class="card-title">Redução Média</div>
                <div class="card-value highlight">{m['saved_percentage']:.1f}%</div>
            </div>
            <div class="card">
                <div class="card-title">Tamanho Original</div>
                <div class="card-value">{format_bytes(m['total_original_bytes'])}</div>
            </div>
            <div class="card">
                <div class="card-title">Tamanho em JXL</div>
                <div class="card-value">{format_bytes(m['total_converted_bytes'])}</div>
            </div>
            <div class="card">
                <div class="card-title">Imagens Processadas</div>
                <div class="card-value">{m['success_count']} / {m['total_files']}</div>
            </div>
            <div class="card">
                <div class="card-title">Tempo Total</div>
                <div class="card-value">{m['total_duration_sec']:.1f}s</div>
            </div>
        </div>

        <div class="progress-bar-container" title="Redução de {m['saved_percentage']:.1f}%">
            <div class="progress-bar-fill"></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Arquivo</th>
                    <th>Status</th>
                    <th>Original</th>
                    <th>JXL</th>
                    <th>Economia</th>
                    <th>Tempo</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path
