from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from shutil import which
from tkinter import filedialog, messagebox, scrolledtext, ttk

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
        self.root.geometry("900x680")
        self.root.minsize(820, 620)

        self.selected_pdf: Path | None = None
        self.output_pdf: Path | None = None
        self.analysis: PdfAnalysis | None = None

        self.language_var = tk.StringVar(value="Espanol + Ingles")
        self.engine_var = tk.StringVar(value="Automatico (recomendado)")
        self.file_var = tk.StringVar(value="Ningun archivo seleccionado")
        self.status_var = tk.StringVar(value="Listo para comenzar.")
        self.info_var = tk.StringVar(value="Selecciona un archivo PDF para analizarlo.")
        self.logo_image: tk.PhotoImage | None = self._load_logo_image()
        self._dependency_notice_shown = False

        self._build_menu()
        self._build_ui()
        self.root.after(150, self._show_missing_dependencies_notice)

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
            # Ajuste automatico para no dominar la interfaz.
            scale = max(1, image.width() // 180)
            if scale > 1:
                image = image.subsample(scale, scale)
            return image
        except tk.TclError:
            return None

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 14))

        if self.logo_image:
            ttk.Label(header, image=self.logo_image).pack(side=tk.LEFT, padx=(0, 12))

        title_box = ttk.Frame(header)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(
            title_box,
            text="Telita OCR",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            title_box,
            text="Convierte PDFs a documentos buscables con OCR.",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(2, 0))

        top_row = ttk.LabelFrame(container, text="Archivo", padding=10)
        top_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(top_row, text="Seleccionar PDF", command=self.select_pdf).pack(side=tk.LEFT)
        ttk.Label(top_row, textvariable=self.file_var).pack(side=tk.LEFT, padx=10)

        settings = ttk.LabelFrame(container, text="Configuracion", padding=10)
        settings.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(settings, text="Idioma OCR:").pack(side=tk.LEFT)
        self.language_combo = ttk.Combobox(
            settings,
            state="readonly",
            textvariable=self.language_var,
            values=list(LANG_OPTIONS.keys()),
            width=20,
        )
        self.language_combo.pack(side=tk.LEFT, padx=10)

        ttk.Label(settings, text="Modo:").pack(side=tk.LEFT)
        self.engine_combo = ttk.Combobox(
            settings,
            state="readonly",
            textvariable=self.engine_var,
            values=list(ENGINE_OPTIONS.keys()),
            width=26,
        )
        self.engine_combo.pack(side=tk.LEFT, padx=10)

        self.process_button = ttk.Button(
            settings,
            text="Generar PDF con OCR",
            command=self.start_ocr,
            state=tk.DISABLED,
        )
        self.process_button.pack(side=tk.LEFT, padx=10)

        self.diagnostic_button = ttk.Button(
            settings,
            text="Modo diagnostico",
            command=self.show_diagnostics,
        )
        self.diagnostic_button.pack(side=tk.LEFT, padx=10)

        self.open_folder_button = ttk.Button(
            settings,
            text="Abrir carpeta",
            command=self.open_output_folder,
            state=tk.DISABLED,
        )
        self.open_folder_button.pack(side=tk.LEFT)

        info = ttk.LabelFrame(container, text="Analisis del archivo", padding=12)
        info.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(info, textvariable=self.info_var, justify=tk.LEFT).pack(anchor=tk.W)

        progress_row = ttk.Frame(container)
        progress_row.pack(fill=tk.X, pady=(0, 10))
        self.progress = ttk.Progressbar(progress_row, mode="determinate", maximum=100, value=0)
        self.progress.pack(fill=tk.X)

        ttk.Label(container, textvariable=self.status_var).pack(anchor=tk.W, pady=(0, 8))

        logs_frame = ttk.LabelFrame(container, text="Registro", padding=10)
        logs_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(logs_frame, height=10, wrap=tk.WORD, relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("Aplicacion iniciada.")

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

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
            self.info_var.set(
                "\n".join(
                    [
                        f"Archivo: {self.analysis.path.name}",
                        f"Paginas: {self.analysis.pages}",
                        f"Tamano: {self.analysis.size_mb} MB",
                        f"Contiene texto: {text_status}",
                        f"Imagenes encontradas: {self.analysis.image_count}",
                        f"Cifrado: {encrypted_status}",
                        f"Restricciones: {restriction_status}",
                        f"Salida: {self.output_pdf.name if self.output_pdf else '-'}",
                    ]
                )
            )
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
            self.info_var.set("No se pudo analizar el PDF.")
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
        self.status_var.set(f"Procesando OCR... {bounded}%")

    def _on_ocr_success(self, output: Path) -> None:
        self.progress.config(value=100)
        self.status_var.set("OCR finalizado correctamente.")
        self.process_button.config(state=tk.NORMAL)
        self.open_folder_button.config(state=tk.NORMAL)
        self.log(f"OCR completado. Archivo generado: {output}")
        messagebox.showinfo("Proceso completado", f"Archivo generado:\n{output}")

    def _on_ocr_error(self, error_message: str) -> None:
        self.progress.config(value=0)
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

        frame = ttk.Frame(help_window, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Guia de configuracion y uso", font=("Segoe UI", 12, "bold")).pack(
            anchor=tk.W, pady=(0, 8)
        )

        help_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Segoe UI", 10), height=22)
        help_box.pack(fill=tk.BOTH, expand=True)
        help_box.insert(tk.END, HELP_TEXT)
        help_box.config(state=tk.DISABLED)

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(10, 0))
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

