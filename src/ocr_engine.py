from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
import subprocess
import tempfile
from importlib.util import find_spec
from typing import Callable

import numpy as np

import ocrmypdf
import pikepdf
import pytesseract
import pypdfium2 as pdfium
import cv2
from pypdf import PdfReader


class OCREngineError(Exception):
    """Error controlado del motor OCR."""


@dataclass
class PdfAnalysis:
    path: Path
    pages: int
    size_mb: float
    encrypted: bool
    has_text: bool
    image_count: int
    can_process_ocr: bool
    restriction_message: str | None


@dataclass
class DiagnosticReport:
    tesseract_path: str | None
    ghostscript_path: str | None
    tesseract_version: str | None
    ghostscript_version: str | None
    available_languages: list[str]
    has_spa: bool
    has_eng: bool
    is_ready: bool
    issues: list[str]
    has_fallback_dependencies: bool


def _validate_system_dependencies() -> None:
    if which("tesseract") is None:
        raise OCREngineError(
            "No se encontro Tesseract en PATH. Instala Tesseract OCR y agrega "
            "C:\\Program Files\\Tesseract-OCR al PATH de Windows."
        )

    if which("gswin64c") is None and which("gs") is None:
        raise OCREngineError(
            "No se encontro Ghostscript en PATH. Instala Ghostscript y agrega su carpeta "
            "bin al PATH (por ejemplo C:\\Program Files\\gs\\gs10.xx.x\\bin)."
        )


def _validate_tesseract_only_dependencies() -> None:
    if which("tesseract") is None:
        raise OCREngineError(
            "No se encontro Tesseract en PATH. Instala Tesseract OCR y agrega "
            "C:\\Program Files\\Tesseract-OCR al PATH de Windows."
        )


def _first_line_or_none(text: str) -> str | None:
    stripped = text.strip()
    return stripped.splitlines()[0] if stripped else None


def build_diagnostic_report() -> DiagnosticReport:
    tesseract_path = which("tesseract")
    ghostscript_path = which("gswin64c") or which("gs")

    tesseract_version: str | None = None
    ghostscript_version: str | None = None
    available_languages: list[str] = []
    issues: list[str] = []

    if tesseract_path:
        try:
            completed = subprocess.run(
                ["tesseract", "--version"],
                check=False,
                capture_output=True,
                text=True,
            )
            tesseract_version = _first_line_or_none(completed.stdout or completed.stderr)
        except Exception:
            issues.append("No se pudo obtener la version de Tesseract.")
    else:
        issues.append("Tesseract no esta en PATH.")

    if ghostscript_path:
        gs_cmd = "gswin64c" if which("gswin64c") else "gs"
        try:
            completed = subprocess.run(
                [gs_cmd, "-version"],
                check=False,
                capture_output=True,
                text=True,
            )
            ghostscript_version = _first_line_or_none(completed.stdout or completed.stderr)
        except Exception:
            issues.append("No se pudo obtener la version de Ghostscript.")
    else:
        issues.append("Ghostscript no esta en PATH.")

    if tesseract_path:
        try:
            completed = subprocess.run(
                ["tesseract", "--list-langs"],
                check=False,
                capture_output=True,
                text=True,
            )
            lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            # Formato esperado:
            # List of available languages in "...":
            # eng
            # spa
            available_languages = [line for line in lines if not line.lower().startswith("list of")]
        except Exception:
            issues.append("No se pudo listar los idiomas de Tesseract.")

    has_spa = "spa" in available_languages
    has_eng = "eng" in available_languages

    has_fallback_dependencies = all(
        find_spec(module_name) is not None
        for module_name in ("pypdfium2", "pytesseract", "cv2", "numpy")
    )
    if not has_fallback_dependencies:
        issues.append("Faltan dependencias de fallback por imagen (pypdfium2/pytesseract/opencv/numpy).")

    if tesseract_path and not has_spa:
        issues.append("Falta idioma 'spa' en Tesseract.")
    if tesseract_path and not has_eng:
        issues.append("Falta idioma 'eng' en Tesseract.")

    is_ready = tesseract_path is not None and ghostscript_path is not None and has_spa and has_eng

    return DiagnosticReport(
        tesseract_path=tesseract_path,
        ghostscript_path=ghostscript_path,
        tesseract_version=tesseract_version,
        ghostscript_version=ghostscript_version,
        available_languages=available_languages,
        has_spa=has_spa,
        has_eng=has_eng,
        is_ready=is_ready,
        issues=issues,
        has_fallback_dependencies=has_fallback_dependencies,
    )


def _detect_text(pdf_path: Path, pages_to_check: int = 5) -> bool:
    """Devuelve True si detecta texto extraible en alguna pagina."""
    reader = PdfReader(str(pdf_path))
    total = min(len(reader.pages), pages_to_check)
    for index in range(total):
        text = (reader.pages[index].extract_text() or "").strip()
        if text:
            return True
    return False


def _count_images_by_occurrence(pdf: pikepdf.Pdf) -> int:
    image_count = 0
    for page in pdf.pages:
        try:
            resources = page.obj.get("/Resources", None)
            if resources is None:
                continue
            xobjects = resources.get("/XObject", None)
            if xobjects is None:
                continue
            for _, xobj in xobjects.items():
                if xobj.get("/Subtype", None) == "/Image":
                    image_count += 1
        except Exception:
            # Si una pagina tiene estructura no estandar, seguimos con el resto.
            continue
    return image_count


def analyze_pdf(input_path: str | Path) -> PdfAnalysis:
    pdf_path = Path(input_path).resolve()
    if not pdf_path.exists():
        raise OCREngineError("El archivo PDF no existe.")

    if pdf_path.suffix.lower() != ".pdf":
        raise OCREngineError("El archivo seleccionado no es un PDF.")

    can_process_ocr = True
    restriction_message: str | None = None

    try:
        with pikepdf.open(str(pdf_path)) as pdf:
            pages = len(pdf.pages)
            encrypted = pdf.is_encrypted
            image_count = _count_images_by_occurrence(pdf)
            if encrypted:
                can_process_ocr = False
                restriction_message = (
                    "El PDF esta cifrado/protegido. Quita la proteccion o usa una copia sin restricciones."
                )
    except pikepdf.PasswordError as exc:
        raise OCREngineError("El PDF esta protegido con contrasena.") from exc
    except pikepdf.PdfError as exc:
        raise OCREngineError("No se pudo leer el PDF. Puede estar corrupto.") from exc

    try:
        has_text = _detect_text(pdf_path)
    except Exception:
        # Si falla la extraccion de texto, continuamos marcando como sin texto.
        has_text = False

    size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2)
    return PdfAnalysis(
        path=pdf_path,
        pages=pages,
        size_mb=size_mb,
        encrypted=encrypted,
        has_text=has_text,
        image_count=image_count,
        can_process_ocr=can_process_ocr,
        restriction_message=restriction_message,
    )


def get_output_path(input_path: str | Path) -> Path:
    pdf_path = Path(input_path).resolve()
    candidate = pdf_path.with_name(f"{pdf_path.stem}_ocr.pdf")
    counter = 1
    while candidate.exists():
        candidate = pdf_path.with_name(f"{pdf_path.stem}_ocr_{counter}.pdf")
        counter += 1
    return candidate


def _has_required_langs(languages: str) -> bool:
    try:
        completed = subprocess.run(
            ["tesseract", "--list-langs"],
            check=False,
            capture_output=True,
            text=True,
        )
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        available_languages = {line for line in lines if not line.lower().startswith("list of")}
    except Exception:
        return False

    requested = {lang.strip() for lang in languages.split("+") if lang.strip()}
    return requested.issubset(available_languages)


def _preprocess_page_image(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=12)
    # Umbral adaptativo para mejorar texto sobre fondos variables.
    return cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )


def _run_ocr_image_fallback(
    input_path: Path,
    output_path: Path,
    languages: str,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    _validate_tesseract_only_dependencies()
    if not _has_required_langs(languages):
        raise OCREngineError(
            f"Faltan datos de idioma en Tesseract para: {languages}. Instala los archivos .traineddata requeridos."
        )

    pdf_doc = pdfium.PdfDocument(str(input_path))
    if len(pdf_doc) == 0:
        raise OCREngineError("El PDF no contiene paginas para procesar.")

    with tempfile.TemporaryDirectory(prefix="ocr_fallback_") as temp_dir:
        temp_path = Path(temp_dir)
        page_pdf_paths: list[Path] = []

        for index in range(len(pdf_doc)):
            page = pdf_doc[index]
            rendered = page.render(scale=300 / 72)
            pil_image = rendered.to_pil()
            image_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            preprocessed = _preprocess_page_image(image_bgr)

            page_pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                preprocessed,
                extension="pdf",
                lang=languages,
                config="--psm 6",
            )
            page_pdf_path = temp_path / f"page_{index + 1}.pdf"
            page_pdf_path.write_bytes(page_pdf_bytes)
            page_pdf_paths.append(page_pdf_path)
            if progress_callback:
                percent = int(((index + 1) / len(pdf_doc)) * 100)
                progress_callback(max(1, min(percent, 100)))

        with pikepdf.new() as merged:
            for page_pdf_path in page_pdf_paths:
                with pikepdf.open(str(page_pdf_path)) as partial:
                    merged.pages.extend(partial.pages)
            merged.save(str(output_path))

    return output_path


def _run_ocr_primary(
    input_path: Path,
    output_path: Path,
    languages: str,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    _validate_system_dependencies()
    if progress_callback:
        progress_callback(10)
    ocrmypdf.ocr(
        input_file=str(input_path),
        output_file=str(output_path),
        language=languages,
        deskew=True,
        skip_text=True,
        progress_bar=False,
        # Modo compatibilidad para Ghostscript 10.6.x:
        # evita optimizaciones/recompresiones agresivas de imagen.
        optimize=0,
        output_type="pdf",
    )
    if progress_callback:
        progress_callback(100)
    return output_path


def run_ocr(
    input_path: str | Path,
    output_path: str | Path,
    languages: str,
    mode: str = "auto",
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    in_path = Path(input_path).resolve()
    out_path = Path(output_path).resolve()
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"auto", "principal", "fallback"}:
        raise OCREngineError("Modo OCR invalido. Usa: auto, principal o fallback.")

    primary_error: Exception | None = None
    if normalized_mode in {"auto", "principal"}:
        try:
            return _run_ocr_primary(in_path, out_path, languages, progress_callback=progress_callback)
        except ocrmypdf.exceptions.MissingDependencyError as exc:
            details = str(exc).lower()
            if normalized_mode == "principal":
                if "tesseract" in details:
                    raise OCREngineError(
                        "No se encontro Tesseract. Instala Tesseract OCR y agrega su carpeta al PATH de Windows "
                        "(por ejemplo C:\\Program Files\\Tesseract-OCR), luego reinicia la aplicacion."
                    ) from exc
                if "ghostscript" in details or "gswin64c" in details:
                    raise OCREngineError(
                        "No se encontro Ghostscript. Instala Ghostscript y agrega su carpeta bin al PATH de Windows."
                    ) from exc
                raise OCREngineError(f"Falta una dependencia del sistema. Detalle: {exc}") from exc
            primary_error = exc
        except ocrmypdf.exceptions.EncryptedPdfError as exc:
            raise OCREngineError("El PDF esta cifrado y no puede procesarse.") from exc
        except ocrmypdf.exceptions.PriorOcrFoundError as exc:
            raise OCREngineError("El PDF ya tiene OCR y se omitio el proceso.") from exc
        except Exception as exc:
            if normalized_mode == "principal":
                raise OCREngineError(f"Error durante OCR principal: {exc}") from exc
            primary_error = exc

    try:
        if progress_callback and normalized_mode == "auto":
            progress_callback(5)
        return _run_ocr_image_fallback(
            in_path,
            out_path,
            languages,
            progress_callback=progress_callback,
        )
    except Exception as fallback_error:
        if primary_error is not None:
            raise OCREngineError(
                "Fallo OCR principal y tambien el fallback por imagen. "
                f"Principal: {primary_error}. Fallback: {fallback_error}"
            ) from fallback_error
        raise OCREngineError(f"Error durante OCR fallback por imagen: {fallback_error}") from fallback_error
