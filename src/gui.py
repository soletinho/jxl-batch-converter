"""
Graphical User Interface for JXL Batch Converter.
Built with Tkinter and ttk with modern dark-accent styling and background threading.
"""

import os
import sys
import webbrowser
import threading
from pathlib import Path
from typing import Optional, List
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.downloader import ensure_cjxl, is_cjxl_available
from src.scanner import scan_images
from src.engine import JXLEngine, ConversionConfig, ConversionResult
from src.reporter import ConversionReport, format_bytes


class JXLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JXL Batch Converter - Otimizador JPEG XL")
        self.geometry("920x680")
        self.minsize(800, 580)

        # State
        self.engine: Optional[JXLEngine] = None
        self.is_converting = False
        self.cancel_requested = False
        self.conversion_thread: Optional[threading.Thread] = None
        self.latest_report: Optional[ConversionReport] = None
        self.results_history: List[ConversionResult] = []

        self._setup_styles()
        self._build_ui()
        self._init_engine_async()

    def _setup_styles(self):
        style = ttk.Style(self)
        # Use clam or vista theme as base
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Custom colors
        bg_dark = "#1e293b"
        accent_blue = "#0284c7"
        text_white = "#f8fafc"

        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=accent_blue)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#64748b")
        style.configure("Section.TLabelframe", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=accent_blue, foreground="white")
        style.map("Primary.TButton", background=[("active", "#0369a1")])
        style.configure("CardTitle.TLabel", font=("Segoe UI", 8), foreground="#64748b")
        style.configure("CardValue.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0f172a")

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header_frame, text="⚡ JXL Batch Converter", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header_frame,
            text="Converta imagens JPG, PNG, GIF e WebP para JPEG XL com máxima compressão e fidelidade.",
            style="SubHeader.TLabel"
        ).pack(anchor=tk.W)

        # Folder Selection Section
        folder_frame = ttk.LabelFrame(main_frame, text="1. Seleção de Pastas", style="Section.TLabelframe")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        # Source folder
        src_row = ttk.Frame(folder_frame)
        src_row.pack(fill=tk.X, pady=2)
        ttk.Label(src_row, text="Pasta de Origem:", width=18).pack(side=tk.LEFT)
        self.src_var = tk.StringVar()
        self.src_entry = ttk.Entry(src_row, textvariable=self.src_var)
        self.src_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(src_row, text="Procurar...", command=self._browse_source).pack(side=tk.LEFT)

        # Destination folder
        dest_row = ttk.Frame(folder_frame)
        dest_row.pack(fill=tk.X, pady=2)
        self.custom_dest_var = tk.BooleanVar(value=False)
        dest_check = ttk.Checkbutton(
            dest_row,
            text="Pasta de Destino Separada:",
            variable=self.custom_dest_var,
            command=self._toggle_destination,
            width=25
        )
        dest_check.pack(side=tk.LEFT)
        self.dest_var = tk.StringVar()
        self.dest_entry = ttk.Entry(dest_row, textvariable=self.dest_var, state=tk.DISABLED)
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.dest_btn = ttk.Button(dest_row, text="Procurar...", command=self._browse_dest, state=tk.DISABLED)
        self.dest_btn.pack(side=tk.LEFT)

        # Options row (Recursive & Skip existing)
        opts_row = ttk.Frame(folder_frame)
        opts_row.pack(fill=tk.X, pady=(5, 0))
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_row, text="Incluir subpastas (recursivo)", variable=self.recursive_var).pack(side=tk.LEFT, padx=(0, 15))
        self.skip_existing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_row, text="Ignorar imagens que já possuem .jxl", variable=self.skip_existing_var).pack(side=tk.LEFT)

        # Conversion Settings Section
        settings_frame = ttk.LabelFrame(main_frame, text="2. Configurações de Qualidade e Conversão", style="Section.TLabelframe")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        mode_row = ttk.Frame(settings_frame)
        mode_row.pack(fill=tk.X, pady=2)
        self.mode_var = tk.StringVar(value="lossless")
        ttk.Radiobutton(
            mode_row,
            text="Sem Perdas (Lossless / Reversível) - Recomendado para JPG/PNG",
            variable=self.mode_var,
            value="lossless",
            command=self._toggle_quality_slider
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Radiobutton(
            mode_row,
            text="Qualidade Personalizada (Com perdas / Maior compressão)",
            variable=self.mode_var,
            value="custom",
            command=self._toggle_quality_slider
        ).pack(side=tk.LEFT)

        # Quality slider row
        self.slider_frame = ttk.Frame(settings_frame)
        self.slider_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.slider_frame, text="Qualidade:").pack(side=tk.LEFT, padx=(0, 5))
        self.quality_var = tk.IntVar(value=90)
        self.quality_slider = ttk.Scale(
            self.slider_frame,
            from_=60,
            to=98,
            variable=self.quality_var,
            orient=tk.HORIZONTAL,
            command=self._on_quality_changed
        )
        self.quality_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.quality_label = ttk.Label(self.slider_frame, text="90 (Visualmente sem perdas)", width=28)
        self.quality_label.pack(side=tk.LEFT)
        self._toggle_quality_slider()  # Initialize enabled/disabled state

        # Originals Handling row
        orig_row = ttk.Frame(settings_frame)
        orig_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(orig_row, text="Arquivos originais:").pack(side=tk.LEFT, padx=(0, 10))
        self.orig_action_var = tk.StringVar(value="keep")
        ttk.Radiobutton(orig_row, text="Manter intactos (Seguro)", variable=self.orig_action_var, value="keep").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(orig_row, text="Excluir originais após conversão com sucesso", variable=self.orig_action_var, value="delete").pack(side=tk.LEFT)

        # Action & Progress Section
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(action_frame, text="▶ Iniciar Conversão", style="Primary.TButton", command=self._start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_btn = ttk.Button(action_frame, text="⏹ Cancelar", command=self._cancel_conversion, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.status_var = tk.StringVar(value="Aguardando seleção de pasta...")
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var, font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Metrics Cards Bar
        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill=tk.X, pady=(0, 10))

        self.card_saved_var = tk.StringVar(value="0.00 MB")
        self.card_pct_var = tk.StringVar(value="0.0%")
        self.card_processed_var = tk.StringVar(value="0 / 0")

        self._create_card(cards_frame, "ESPAÇO ECONOMIZADO", self.card_saved_var, side=tk.LEFT)
        self._create_card(cards_frame, "REDUÇÃO MÉDIA", self.card_pct_var, side=tk.LEFT)
        self._create_card(cards_frame, "PROGRESSO", self.card_processed_var, side=tk.LEFT)

        # Report Buttons on the right of cards
        btn_box = ttk.Frame(cards_frame)
        btn_box.pack(side=tk.RIGHT, fill=tk.Y)
        self.html_btn = ttk.Button(btn_box, text="🌐 Abrir Relatório HTML", command=self._open_html_report, state=tk.DISABLED)
        self.html_btn.pack(side=tk.RIGHT, padx=5)
        self.csv_btn = ttk.Button(btn_box, text="📊 Exportar CSV", command=self._export_csv_report, state=tk.DISABLED)
        self.csv_btn.pack(side=tk.RIGHT, padx=5)

        # Results Table
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("file", "status", "orig_size", "jxl_size", "saved", "time")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("file", text="Arquivo")
        self.tree.heading("status", text="Status")
        self.tree.heading("orig_size", text="Tamanho Original")
        self.tree.heading("jxl_size", text="Tamanho JXL")
        self.tree.heading("saved", text="Economia")
        self.tree.heading("time", text="Tempo")

        self.tree.column("file", width=340)
        self.tree.column("status", width=90, anchor=tk.CENTER)
        self.tree.column("orig_size", width=120, anchor=tk.E)
        self.tree.column("jxl_size", width=120, anchor=tk.E)
        self.tree.column("saved", width=130, anchor=tk.E)
        self.tree.column("time", width=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_card(self, parent, title: str, text_var: tk.StringVar, side):
        frame = ttk.Frame(parent, relief=tk.RIDGE, padding=(12, 6))
        frame.pack(side=side, padx=(0, 10))
        ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(frame, textvariable=text_var, style="CardValue.TLabel").pack(anchor=tk.W)

    def _init_engine_async(self):
        def worker():
            try:
                self.status_var.set("Verificando binários do JPEG XL (cjxl)...")
                path = ensure_cjxl(
                    progress_callback=lambda c, t, msg: self.status_var.set(msg)
                )
                self.engine = JXLEngine(path)
                self.status_var.set("Pronto. Selecione a pasta de imagens para iniciar.")
            except Exception as exc:
                self.status_var.set(f"Erro ao inicializar cjxl: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Selecione a pasta com imagens para converter")
        if folder:
            self.src_var.set(folder)
            self._preview_candidates(folder)

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Selecione a pasta de destino dos arquivos JXL")
        if folder:
            self.dest_var.set(folder)

    def _toggle_destination(self):
        if self.custom_dest_var.get():
            self.dest_entry.configure(state=tk.NORMAL)
            self.dest_btn.configure(state=tk.NORMAL)
        else:
            self.dest_entry.configure(state=tk.DISABLED)
            self.dest_btn.configure(state=tk.DISABLED)

    def _toggle_quality_slider(self):
        is_custom = self.mode_var.get() == "custom"
        state = tk.NORMAL if is_custom else tk.DISABLED
        self.quality_slider.configure(state=state)
        if not is_custom:
            self.quality_label.configure(text="Matematicamente sem perdas (100% fiel)")
        else:
            self._on_quality_changed(self.quality_var.get())

    def _on_quality_changed(self, value):
        val = int(float(value))
        if val >= 95:
            desc = f"{val} (Ultra alta fidelidade)"
        elif val >= 85:
            desc = f"{val} (Visualmente sem perdas)"
        else:
            desc = f"{val} (Alta compressão)"
        self.quality_label.configure(text=desc)

    def _preview_candidates(self, folder: str):
        def worker():
            self.status_var.set("Examinando arquivos na pasta...")
            candidates = scan_images(
                Path(folder),
                recursive=self.recursive_var.get(),
                skip_existing_jxl=self.skip_existing_jxl_var.get()
            )
            count = len(candidates)
            self.status_var.set(f"Encontradas {count} imagens prontas para conversão.")
            self.card_processed_var.set(f"0 / {count}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_conversion(self):
        src_path = self.src_var.get().strip()
        if not src_path or not Path(src_path).is_dir():
            messagebox.showwarning("Aviso", "Por favor, selecione uma pasta de origem válida.")
            return

        if not self.engine:
            messagebox.showerror("Erro", "O motor cjxl ainda não está pronto. Aguarde alguns instantes.")
            return

        dest_dir = None
        if self.custom_dest_var.get():
            dest_str = self.dest_var.get().strip()
            if not dest_str:
                messagebox.showwarning("Aviso", "Por favor, defina a pasta de destino ou desmarque a opção.")
                return
            dest_dir = Path(dest_str)

        config = ConversionConfig(
            quality_mode=self.mode_var.get(),
            quality=self.quality_var.get(),
            effort=7,
            destination_dir=dest_dir,
            keep_original=(self.orig_action_var.get() == "keep"),
            delete_original=(self.orig_action_var.get() == "delete")
        )

        if config.delete_original:
            confirm = messagebox.askyesno(
                "Atenção - Exclusão de Originais",
                "Você selecionou a opção de EXCLUIR os arquivos originais após a conversão.\n\n"
                "Tem certeza de que deseja continuar?",
                icon=messagebox.WARNING
            )
            if not confirm:
                return

        # Clear UI table & stats
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.results_history.clear()
        self.card_saved_var.set("0.00 MB")
        self.card_pct_var.set("0.0%")
        self.html_btn.configure(state=tk.DISABLED)
        self.csv_btn.configure(state=tk.DISABLED)

        self.is_converting = True
        self.cancel_requested = False
        self.start_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)

        def worker():
            source_root = Path(src_path)
            self.status_var.set("Buscando imagens...")
            files = scan_images(
                source_root,
                recursive=self.recursive_var.get(),
                skip_existing_jxl=self.skip_existing_var.get(),
                destination_dir=dest_dir
            )

            total = len(files)
            if total == 0:
                self.status_var.set("Nenhuma imagem para converter encontrada.")
                self._conversion_finished([])
                return

            self.progress_bar["maximum"] = total
            self.progress_bar["value"] = 0

            def on_progress(idx: int, tot: int, res: ConversionResult):
                self.results_history.append(res)
                # Dispatch update to main UI thread
                self.after(0, self._update_row, idx, tot, res)

            def cancel_check():
                return self.cancel_requested

            results = self.engine.batch_convert(
                files=files,
                source_root=source_root,
                config=config,
                progress_callback=on_progress,
                cancel_check=cancel_check
            )

            self.after(0, self._conversion_finished, results)

        self.conversion_thread = threading.Thread(target=worker, daemon=True)
        self.conversion_thread.start()

    def _update_row(self, index: int, total: int, res: ConversionResult):
        self.progress_bar["value"] = index
        self.card_processed_var.set(f"{index} / {total}")
        self.status_var.set(f"Convertendo [{index}/{total}]: {res.input_path.name}")

        status_text = "Sucesso" if res.status == "success" else ("Ignorado" if res.status == "skipped" else "Erro")
        saved_text = f"{format_bytes(res.saved_bytes)} ({res.saved_percentage:.1f}%)" if res.status == "success" else "-"
        orig_str = format_bytes(res.original_size)
        conv_str = format_bytes(res.converted_size) if res.converted_size > 0 else "-"
        time_str = f"{res.duration_ms:.0f} ms"

        item_id = self.tree.insert(
            "",
            tk.END,
            values=(res.input_path.name, status_text, orig_str, conv_str, saved_text, time_str)
        )
        self.tree.see(item_id)

        # Update running stats
        successful = [r for r in self.results_history if r.status == "success"]
        tot_orig = sum(r.original_size for r in successful)
        tot_conv = sum(r.converted_size for r in successful)
        tot_saved = tot_orig - tot_conv
        pct = (tot_saved / tot_orig * 100) if tot_orig > 0 else 0.0

        self.card_saved_var.set(format_bytes(tot_saved))
        self.card_pct_var.set(f"{pct:.1f}%")

    def _cancel_conversion(self):
        if self.is_converting:
            self.cancel_requested = True
            self.status_var.set("Cancelando... Aguardando conversão atual terminar.")
            self.cancel_btn.configure(state=tk.DISABLED)

    def _conversion_finished(self, results: List[ConversionResult]):
        self.is_converting = False
        self.start_btn.configure(state=tk.NORMAL)
        self.cancel_btn.configure(state=tk.DISABLED)

        if not results and not self.results_history:
            return

        all_results = self.results_history
        src_path = self.src_var.get()
        report = ConversionReport(all_results, src_path)
        self.latest_report = report

        # Enable export buttons
        self.html_btn.configure(state=tk.NORMAL)
        self.csv_btn.configure(state=tk.NORMAL)

        m = report.metrics
        status_msg = (
            f"Concluído! {m['success_count']} convertidas, {m['skipped_count']} ignoradas, "
            f"{m['error_count']} erros. Economizados: {format_bytes(m['total_saved_bytes'])} ({m['saved_percentage']:.1f}%)"
        )
        self.status_var.set(status_msg)

        messagebox.showinfo(
            "Conversão Concluída",
            f"Processamento finalizado com sucesso!\n\n"
            f"• Imagens convertidas: {m['success_count']}\n"
            f"• Espaço economizado: {format_bytes(m['total_saved_bytes'])} ({m['saved_percentage']:.1f}%)\n"
            f"• Tempo total: {m['total_duration_sec']:.1f} segundos\n\n"
            "Você pode exportar o relatório detalhado em HTML ou CSV."
        )

    def _open_html_report(self):
        if not self.latest_report:
            return
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        html_file = reports_dir / f"relatorio_{self.latest_report.timestamp.strftime('%Y%m%d_%H%M%S')}.html"
        self.latest_report.export_html(html_file)
        webbrowser.open(str(html_file.resolve()))

    def _export_csv_report(self):
        if not self.latest_report:
            return
        dest = filedialog.asksaveasfilename(
            title="Salvar Relatório CSV",
            defaultextension=".csv",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos os Arquivos", "*.*")]
        )
        if dest:
            self.latest_report.export_csv(Path(dest))
            messagebox.showinfo("Exportado", f"Relatório salvo em:\n{dest}")


def launch_gui():
    app = JXLApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
