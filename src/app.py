from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from shutil import which
from tkinter import filedialog, messagebox, scrolledtext, ttk

import sv_ttk

from src.ocr_engine import (
    OCREngineError,
    PdfAnalysis,
    analyze_pdf,
    build_diagnostic_report,
    get_output_path,
    run_ocr,
)


LANG_OPTIONS = {
    "Espanol": "spa",
    "Ingles": "eng",
    "Espanol + Ingles": "spa+eng",
}

ENGINE_OPTIONS = {
    "Automatico (recomendado)": "auto",
    "Rapido (OCRmyPDF)": "principal",
    "Compatibilidad imagenes": "fallback",
}

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUBTITLE = ("Segoe UI", 10)
FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_LOG = ("Consolas", 9)

HELP_TEXT = """TELITA OCR - Ayuda de configuracion y uso

1) Requisitos obligatorios
- Windows 10/11
- Python 3.9+
- Tesseract OCR instalado y en PATH
- Ghostscript (gswin64c) instalado y en PATH

2) Configuracion recomendada
- Instala Tesseract desde UB Mannheim.
- Instala Ghostscript desde su sitio oficial.
- Verifica en terminal:
  tesseract --version
  gswin64c -version
  tesseract --list-langs

3) Idioma OCR
- Espanol: usa 'spa'
- Ingles: usa 'eng'
- Espanol + Ingles: usa ambos modelos

4) Modos OCR
- Automatico: intenta OCRmyPDF y, si falla, usa compatibilidad por imagen.
- Rapido (OCRmyPDF): usa solo el motor principal.
- Compatibilidad imagenes: OCR por pagina con preprocesado para PDFs dificiles.

5) Analisis del archivo
Antes de procesar, la app muestra:
- Paginas
- Tamano
- Contiene texto
- Imagenes encontradas (por ocurrencia)
- Cifrado/restricciones

6) Diagnostico
Usa 'Modo diagnostico' para revisar:
- rutas detectadas de Tesseract y Ghostscript
- idiomas instalados
- dependencias de fallback por imagen

7) Errores comunes
- 'No se encontro Tesseract': agregar ruta de Tesseract al PATH.
- 'No se encontro Ghostscript': agregar carpeta bin de Ghostscript al PATH.
- 'Please install appropriate language data': faltan spa/eng en tessdata.
- PDF protegido/cifrado: no se procesa OCR hasta quitar restricciones.

8) Salida de archivo
Se guarda en la misma carpeta del PDF original:
- archivo.pdf -> archivo_ocr.pdf
- Si ya existe, se usan sufijos _ocr_1, _ocr_2, etc.
"""


class OCRApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Telita OCR - Aplicacion de escritorio para OCR de PDFs")
        self.root.geometry("1150x860")
        self.root.minsize(1040, 720)

        sv_ttk.set_theme("light")

        self.selected_pdf: Path | None = None
        self.output_pdf: Path | None = None
        self.analysis: PdfAnalysis | None = None

        self.language_var = tk.StringVar(value="Espanol + Ingles")
        self.engine_var = tk.StringVar(value="Automatico (recomendado)")
        self.file_var = tk.StringVar(value="Ningun archivo seleccionado")
        self.status_var = tk.StringVar(value="Listo para comenzar.")
        self.progress_percent_var = tk.StringVar(value="0%")

        self.var_a_archivo = tk.StringVar(value="—")
        self.var_a_paginas = tk.StringVar(value="—")
        self.var_a_tamano = tk.StringVar(value="—")
        self.var_a_texto = tk.StringVar(value="—")
        self.var_a_imagenes = tk.StringVar(value="—")
        self.var_a_cifrado = tk.StringVar(value="—")
        self.var_a_restricciones = tk.StringVar(value="—")
        self.var_a_salida = tk.StringVar(value="—")

        self.logo_image: tk.PhotoImage | None = self._load_logo_image()
        self._dependency_notice_shown = False
        self._container: ttk.Frame | None = None
        self._analysis_value_labels: list[ttk.Label] = []

        self._build_menu()
        self._build_ui()
        self.root.after(0, self._maximize_main_window)
        self.root.after(150, self._show_missing_dependencies_notice)

    def _maximize_main_window(self) -> None:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Ver ayuda", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de", command=self.show_about)
        menu_bar.add_cascade(label="Ayuda", menu=help_menu)
        self.root.config(menu=menu_bar)

    def _show_missing_dependencies_notice(self) -> None:
        if self._dependency_notice_shown:
            return

        missing_items: list[str] = []
        if which("tesseract") is None:
            missing_items.append("Tesseract-OCR")
        if which("gswin64c") is None and which("gs") is None:
            missing_items.append("Ghostscript")

        if not missing_items:
            return

        self._dependency_notice_shown = True
        dependencies = ", ".join(missing_items)
        messagebox.showwarning(
            "Dependencias obligatorias faltantes",
            "TELITA OCR requiere dependencias del sistema para funcionar.\n\n"
            f"Faltan: {dependencies}\n\n"
            "Instala estas herramientas y agrega sus rutas al PATH de Windows:\n"
            "- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "- Ghostscript: https://ghostscript.com/releases/gsdnld.html\n\n"
            "Luego reinicia la aplicacion.",
        )

    def _load_logo_image(self) -> tk.PhotoImage | None:
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "telita-ocr.png"
        if not logo_path.exists():
            return None
        try:
            image = tk.PhotoImage(file=str(logo_path))
            scale = max(1, image.width() // 180)
            if scale > 1:
                image = image.subsample(scale, scale)
            return image
        except tk.TclError:
            return None

    def _sync_theme_button_text(self) -> None:
        if sv_ttk.get_theme() == "dark":
            self.theme_button.config(text="Tema: Oscuro")
        else:
            self.theme_button.config(text="Tema: Claro")

    def _toggle_theme(self) -> None:
        sv_ttk.toggle_theme()
        self._sync_theme_button_text()
        self._apply_log_widget_theme(self.log_text)

    def _on_container_configure(self, event: tk.Event) -> None:
        if self._container is None or event.widget is not self._container:
            return
        inner = max(220, int(event.width) - 220)
        for lbl in self._analysis_value_labels:
            lbl.configure(wraplength=inner)

    def _apply_log_widget_theme(self, widget: tk.Text) -> None:
        if sv_ttk.get_theme() == "dark":
            widget.config(
                bg="#1e1e1e",
                fg="#d4d4d4",
                insertbackground="#d4d4d4",
                highlightthickness=0,
            )
        else:
            widget.config(
                bg="#ffffff",
                fg="#1a1a1a",
                insertbackground="#1a1a1a",
                highlightthickness=0,
            )

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=(20, 18))
        self._container = container
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(7, weight=1)
        container.bind("<Configure>", self._on_container_configure, add="+")

        # --- Fila 0: cabecera ---
        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)

        logo_frame = ttk.Frame(header)
        logo_frame.grid(row=0, column=0, sticky="nw", padx=(0, 12))
        if self.logo_image:
            ttk.Label(logo_frame, image=self.logo_image).pack(anchor=tk.NW)

        title_box = ttk.Frame(header)
        title_box.grid(row=0, column=1, sticky="w")
        ttk.Label(title_box, text="Telita OCR", font=FONT_TITLE).pack(anchor=tk.W)
        ttk.Label(
            title_box,
            text="Convierte PDFs a documentos buscables con OCR.",
            font=FONT_SUBTITLE,
        ).pack(anchor=tk.W, pady=(2, 0))

        self.theme_button = ttk.Button(header, text="", width=16, command=self._toggle_theme)
        self.theme_button.grid(row=0, column=2, sticky="ne", padx=(12, 0))
        self._sync_theme_button_text()

        # --- Fila 1: Archivo ---
        card_file = ttk.LabelFrame(container, text=" Archivo ", padding=(14, 12))
        card_file.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        card_file.grid_columnconfigure(1, weight=1)

        ttk.Button(card_file, text="Seleccionar PDF", command=self.select_pdf).grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        ttk.Label(card_file, textvariable=self.file_var, font=FONT_UI).grid(
            row=0, column=1, sticky="w"
        )

        # --- Fila 2: Configuracion ---
        card_settings = ttk.LabelFrame(container, text=" Configuracion ", padding=(14, 12))
        card_settings.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        card_settings.grid_columnconfigure(1, weight=1)
        card_settings.grid_columnconfigure(3, weight=1)

        ttk.Label(card_settings, text="Idioma OCR", font=FONT_UI_BOLD).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.language_combo = ttk.Combobox(
            card_settings,
            state="readonly",
            textvariable=self.language_var,
            values=list(LANG_OPTIONS.keys()),
            width=22,
        )
        self.language_combo.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        ttk.Label(card_settings, text="Modo OCR", font=FONT_UI_BOLD).grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        self.engine_combo = ttk.Combobox(
            card_settings,
            state="readonly",
            textvariable=self.engine_var,
            values=list(ENGINE_OPTIONS.keys()),
            width=28,
        )
        self.engine_combo.grid(row=0, column=3, sticky="ew")

        # --- Fila 3: Acciones ---
        card_actions = ttk.LabelFrame(container, text=" Acciones ", padding=(14, 12))
        card_actions.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        card_actions.grid_columnconfigure(0, weight=1)
        card_actions.grid_columnconfigure(1, weight=1)
        card_actions.grid_columnconfigure(2, weight=1)

        self.process_button = ttk.Button(
            card_actions,
            text="Generar PDF con OCR",
            command=self.start_ocr,
            state=tk.DISABLED,
        )
        self.process_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.diagnostic_button = ttk.Button(
            card_actions,
            text="Modo diagnostico",
            command=self.show_diagnostics,
        )
        self.diagnostic_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.open_folder_button = ttk.Button(
            card_actions,
            text="Abrir carpeta de salida",
            command=self.open_output_folder,
            state=tk.DISABLED,
        )
        self.open_folder_button.grid(row=0, column=2, sticky="ew")

        # --- Fila 4: Analisis ---
        card_analysis = ttk.LabelFrame(container, text=" Analisis del archivo ", padding=(14, 12))
        card_analysis.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        card_analysis.grid_columnconfigure(1, weight=1)

        analysis_rows: list[tuple[str, tk.StringVar]] = [
            ("Archivo", self.var_a_archivo),
            ("Paginas", self.var_a_paginas),
            ("Tamano", self.var_a_tamano),
            ("Contiene texto", self.var_a_texto),
            ("Imagenes encontradas", self.var_a_imagenes),
            ("Cifrado", self.var_a_cifrado),
            ("Restricciones", self.var_a_restricciones),
            ("Salida prevista", self.var_a_salida),
        ]
        self._analysis_value_labels.clear()
        for i, (label, var) in enumerate(analysis_rows):
            ttk.Label(card_analysis, text=f"{label}:", font=FONT_UI_BOLD).grid(
                row=i, column=0, sticky="nw", padx=(0, 10), pady=3
            )
            val_lbl = ttk.Label(card_analysis, textvariable=var, font=FONT_UI, wraplength=720)
            val_lbl.grid(row=i, column=1, sticky="w", pady=3)
            self._analysis_value_labels.append(val_lbl)

        # --- Fila 5: Progreso ---
        progress_wrap = ttk.Frame(container)
        progress_wrap.grid(row=5, column=0, sticky="ew", pady=(0, 6))
        progress_wrap.grid_columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(progress_wrap, mode="determinate", maximum=100, value=0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        ttk.Label(progress_wrap, textvariable=self.progress_percent_var, font=FONT_UI_BOLD, width=5).grid(
            row=0, column=1, sticky="e"
        )

        # --- Fila 6: Estado ---
        ttk.Label(container, textvariable=self.status_var, font=FONT_UI).grid(
            row=6, column=0, sticky="w", pady=(0, 10)
        )

        # --- Fila 7: Registro (expande) ---
        logs_frame = ttk.LabelFrame(container, text=" Registro ", padding=(14, 12))
        logs_frame.grid(row=7, column=0, sticky="nsew", pady=(0, 0))
        logs_frame.grid_rowconfigure(0, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(logs_frame, height=11, wrap=tk.WORD, relief=tk.FLAT, font=FONT_LOG)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self._apply_log_widget_theme(self.log_text)

        self.log("Aplicacion iniciada.")
        self.root.after_idle(self._sync_analysis_wraplength)

    def _sync_analysis_wraplength(self) -> None:
        if self._container is None:
            return
        try:
            w = self._container.winfo_width()
        except tk.TclError:
            return
        inner = max(220, w - 220)
        for lbl in self._analysis_value_labels:
            lbl.configure(wraplength=inner)

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def _reset_analysis_display(self) -> None:
        self.var_a_archivo.set("—")
        self.var_a_paginas.set("—")
        self.var_a_tamano.set("—")
        self.var_a_texto.set("—")
        self.var_a_imagenes.set("—")
        self.var_a_cifrado.set("—")
        self.var_a_restricciones.set("—")
        self.var_a_salida.set("—")

    def select_pdf(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo PDF",
            filetypes=[("PDF", "*.pdf")],
        )
        if not file_path:
            return

        self.selected_pdf = Path(file_path)
        self.output_pdf = get_output_path(self.selected_pdf)
        self.file_var.set(self.selected_pdf.name)
        self.open_folder_button.config(state=tk.DISABLED)
        self._analyze_selected_pdf()

    def _analyze_selected_pdf(self) -> None:
        if not self.selected_pdf:
            return
        try:
            self.analysis = analyze_pdf(self.selected_pdf)
            text_status = "Si" if self.analysis.has_text else "No"
            encrypted_status = "Si" if self.analysis.encrypted else "No"
            restriction_status = (
                self.analysis.restriction_message
                if self.analysis.restriction_message
                else "Ninguna"
            )

            self.var_a_archivo.set(self.analysis.path.name)
            self.var_a_paginas.set(str(self.analysis.pages))
            self.var_a_tamano.set(f"{self.analysis.size_mb} MB")
            self.var_a_texto.set(text_status)
            self.var_a_imagenes.set(str(self.analysis.image_count))
            self.var_a_cifrado.set(encrypted_status)
            self.var_a_restricciones.set(restriction_status)
            self.var_a_salida.set(self.output_pdf.name if self.output_pdf else "—")

            self.status_var.set("Analisis completado.")
            if self.analysis.can_process_ocr:
                self.process_button.config(state=tk.NORMAL)
            else:
                self.process_button.config(state=tk.DISABLED)
                self.status_var.set("El PDF tiene restricciones. No se puede ejecutar OCR.")
                self.log(
                    "OCR bloqueado por restricciones del PDF: "
                    f"{self.analysis.restriction_message}"
                )
            self.log(f"Analisis completado para: {self.selected_pdf}")
        except OCREngineError as exc:
            self.analysis = None
            self.process_button.config(state=tk.DISABLED)
            self._reset_analysis_display()
            self.var_a_archivo.set("Error al analizar")
            self.status_var.set("No se pudo analizar el PDF.")
            messagebox.showerror("Error de analisis", str(exc))
            self.log(f"Error de analisis: {exc}")

    def start_ocr(self) -> None:
        if not self.selected_pdf or not self.output_pdf:
            messagebox.showwarning("Archivo faltante", "Selecciona un archivo PDF primero.")
            return

        if self.analysis and not self.analysis.can_process_ocr:
            reason = self.analysis.restriction_message or "El PDF tiene restricciones."
            messagebox.showwarning("OCR bloqueado", reason)
            self.log(f"OCR bloqueado: {reason}")
            return

        self.process_button.config(state=tk.DISABLED)
        self.open_folder_button.config(state=tk.DISABLED)
        self.progress.config(value=0)
        self.progress_percent_var.set("0%")
        self.status_var.set("Procesando OCR... 0%")
        self.log("Iniciando OCR...")

        threading.Thread(target=self._run_ocr_worker, daemon=True).start()

    def _run_ocr_worker(self) -> None:
        assert self.selected_pdf is not None
        assert self.output_pdf is not None

        selected_lang = LANG_OPTIONS[self.language_var.get()]
        selected_engine = ENGINE_OPTIONS[self.engine_var.get()]

        def on_progress(percent: int) -> None:
            self.root.after(0, lambda p=percent: self._update_progress(p))

        try:
            output = run_ocr(
                self.selected_pdf,
                self.output_pdf,
                selected_lang,
                mode=selected_engine,
                progress_callback=on_progress,
            )
            self.root.after(0, lambda output_path=output: self._on_ocr_success(output_path))
        except OCREngineError as exc:
            error_message = str(exc)
            self.root.after(0, lambda message=error_message: self._on_ocr_error(message))

    def _update_progress(self, percent: int) -> None:
        bounded = max(0, min(100, int(percent)))
        self.progress.config(value=bounded)
        self.progress_percent_var.set(f"{bounded}%")
        self.status_var.set(f"Procesando OCR... {bounded}%")

    def _on_ocr_success(self, output: Path) -> None:
        self.progress.config(value=100)
        self.progress_percent_var.set("100%")
        self.status_var.set("OCR finalizado correctamente.")
        self.process_button.config(state=tk.NORMAL)
        self.open_folder_button.config(state=tk.NORMAL)
        self.log(f"OCR completado. Archivo generado: {output}")
        messagebox.showinfo("Proceso completado", f"Archivo generado:\n{output}")

    def _on_ocr_error(self, error_message: str) -> None:
        self.progress.config(value=0)
        self.progress_percent_var.set("0%")
        self.status_var.set("Error durante el OCR.")
        self.process_button.config(state=tk.NORMAL)
        self.log(f"Error OCR: {error_message}")
        messagebox.showerror("Error OCR", error_message)

    def show_help(self) -> None:
        help_window = tk.Toplevel(self.root)
        help_window.title("TELITA OCR - Ayuda")
        help_window.geometry("760x560")
        help_window.minsize(680, 500)
        help_window.transient(self.root)
        help_window.grab_set()
        sv_ttk.set_theme(sv_ttk.get_theme())

        frame = ttk.Frame(help_window, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="Guia de configuracion y uso", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        help_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=FONT_UI, height=22)
        help_box.grid(row=1, column=0, sticky="nsew")
        self._apply_log_widget_theme(help_box)
        help_box.insert(tk.END, HELP_TEXT)
        help_box.config(state=tk.DISABLED)

        button_row = ttk.Frame(frame)
        button_row.grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Button(button_row, text="Cerrar", command=help_window.destroy).pack(side=tk.RIGHT)

    def show_about(self) -> None:
        messagebox.showinfo(
            "Acerca de TELITA OCR",
            "TELITA OCR\nVersion: 1.0\nAplicacion de escritorio para OCR de archivos PDF.",
        )

    def show_diagnostics(self) -> None:
        report = build_diagnostic_report()
        ready = "Si" if report.is_ready else "No"
        spa_status = "Si" if report.has_spa else "No"
        eng_status = "Si" if report.has_eng else "No"
        fallback_status = "Si" if report.has_fallback_dependencies else "No"
        langs = ", ".join(report.available_languages) if report.available_languages else "-"
        issues = "\n".join(f"- {item}" for item in report.issues) if report.issues else "- Ninguna"

        message = (
            "Diagnostico del sistema OCR\n\n"
            f"Listo para OCR: {ready}\n"
            f"Tesseract PATH: {report.tesseract_path or 'No encontrado'}\n"
            f"Tesseract version: {report.tesseract_version or 'No disponible'}\n"
            f"Ghostscript PATH: {report.ghostscript_path or 'No encontrado'}\n"
            f"Ghostscript version: {report.ghostscript_version or 'No disponible'}\n"
            f"Idioma spa instalado: {spa_status}\n"
            f"Idioma eng instalado: {eng_status}\n"
            f"Dependencias fallback instaladas: {fallback_status}\n"
            f"Idiomas detectados: {langs}\n\n"
            "Problemas encontrados:\n"
            f"{issues}"
        )

        self.log(f"Diagnostico ejecutado. Listo para OCR: {ready}")
        if report.issues:
            self.status_var.set("Diagnostico: se encontraron problemas.")
            messagebox.showwarning("Modo diagnostico", message)
        else:
            self.status_var.set("Diagnostico: sistema listo para OCR.")
            messagebox.showinfo("Modo diagnostico", message)

    def open_output_folder(self) -> None:
        if not self.output_pdf:
            return
        folder = self.output_pdf.parent
        os.startfile(folder)  # type: ignore[attr-defined]
