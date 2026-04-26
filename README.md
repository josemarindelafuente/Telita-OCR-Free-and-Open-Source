# TELITA OCR

**TELITA OCR** es una aplicacion de escritorio para Windows que convierte archivos PDF en PDFs buscables, usando OCR y una interfaz grafica con Tkinter.

Esta app esta pensada para documentos escaneados, PDFs con texto rasterizado como imagen y casos donde se necesita un flujo simple pero robusto.

## Que hace TELITA OCR

- Carga un PDF desde la interfaz.
- Analiza el archivo antes de ejecutar OCR.
- Detecta:
  - cantidad de paginas,
  - tamano del archivo,
  - si contiene texto extraible,
  - cantidad de imagenes encontradas (por ocurrencia),
  - si esta cifrado o con restriccion que bloquee el proceso.
- Permite elegir idioma OCR:
  - `Espanol`
  - `Ingles`
  - `Espanol + Ingles`
- Permite elegir motor OCR:
  - `Automatico (recomendado)`
  - `Rapido (OCRmyPDF)`
  - `Compatibilidad imagenes`
- Muestra progreso del OCR en porcentaje.
- Incluye menu superior `Ayuda` con guia integrada de configuracion y uso.
- Guarda la salida en la misma carpeta del archivo original.

## Nombre del archivo de salida

- Si el archivo de entrada es `documento.pdf`, la salida sera `documento_ocr.pdf`.
- Si `documento_ocr.pdf` ya existe, la app genera:
  - `documento_ocr_1.pdf`
  - `documento_ocr_2.pdf`
  - etc.

## Modos OCR explicados

### 1) Automatico (recomendado)

Primero intenta con `OCRmyPDF` (rapido y manteniendo bien la estructura original).
Si falla, cambia automaticamente al modo de compatibilidad por imagen.

### 2) Rapido (OCRmyPDF)

Usa solo `OCRmyPDF`.
Es el modo mas directo cuando el entorno esta bien configurado y el PDF no tiene dificultades especiales.

### 3) Compatibilidad imagenes

Renderiza cada pagina como imagen, aplica preprocesado y luego OCR por pagina.
Es util para PDFs "anti-OCR", escaneos degradados o documentos con texto incrustado en imagen.

## Requisitos obligatorios

- Windows 10/11
- Python 3.9 o superior
- [Tesseract OCR (UB Mannheim)](https://github.com/UB-Mannheim/tesseract/wiki)
- [Ghostscript (`gswin64c`)](https://ghostscript.com/releases/gsdnld.html)

Ademas, los idiomas de Tesseract que esta app usa por defecto:

- `spa` (espanol)
- `eng` (ingles)

## Instalacion de dependencias del sistema

### 1) Instalar Tesseract OCR

Descarga e instala desde:
[https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

Ruta habitual:
`C:\Program Files\Tesseract-OCR`

### 2) Instalar Ghostscript

Descarga e instala desde:
[https://ghostscript.com/releases/gsdnld.html](https://ghostscript.com/releases/gsdnld.html)

Ruta habitual (ejemplo):
`C:\Program Files\gs\gs10.xx.x\bin`

### 3) Agregar al PATH de Windows

Debes agregar al `PATH`:

- Carpeta de Tesseract (donde esta `tesseract.exe`)
- Carpeta `bin` de Ghostscript (donde esta `gswin64c.exe`)

### 4) Verificar instalacion

En una nueva terminal de PowerShell:

```powershell
tesseract --version
gswin64c -version
tesseract --list-langs
```

Si alguno falla, TELITA OCR no podra procesar correctamente.

## Instalacion del proyecto (Python)

Desde PowerShell, en la carpeta del proyecto:

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar TELITA OCR

Opcion 1:

```powershell
.\venv\Scripts\activate
python main.py
```

Opcion 2:

- Ejecutar `run.bat` con doble clic.

## Uso de la aplicacion paso a paso

1. Haz clic en `Seleccionar PDF`.
2. Revisa el bloque `Analisis del archivo`.
3. Verifica especialmente:
   - `Contiene texto`
   - `Imagenes encontradas`
   - `Cifrado`
   - `Restricciones`
4. Elige idioma OCR.
5. Elige modo OCR.
6. (Opcional) pulsa `Modo diagnostico`.
7. Haz clic en `Generar PDF con OCR`.
8. Sigue el porcentaje de avance.
9. Al finalizar, abre la carpeta con `Abrir carpeta`.

## Ayuda integrada en la app

TELITA OCR incluye un menu superior:

- `Ayuda > Ver ayuda`: abre una ventana con guia completa de configuracion, modos OCR, diagnostico y errores comunes.
- `Ayuda > Acerca de`: muestra informacion general de la aplicacion.

## Modo diagnostico

El boton `Modo diagnostico` muestra:

- si Tesseract esta en PATH,
- si Ghostscript esta en PATH,
- versiones detectadas,
- idiomas disponibles (`spa`, `eng`),
- estado de dependencias del fallback por imagen.

Esto ayuda a resolver errores antes de lanzar OCR.

## Estructura del proyecto

```text
.
├── assets/
│   └── telita-ocr.png
├── main.py
├── requirements.txt
├── README.md
├── run.bat
├── venv/
└── src/
    ├── __init__.py
    ├── app.py
    └── ocr_engine.py
```

## Detalles tecnicos relevantes

- La interfaz corre con Tkinter.
- El OCR se ejecuta en un hilo para no congelar la ventana.
- El progreso de OCR se muestra en porcentaje.
- En modo `Compatibilidad imagenes` el progreso se calcula por paginas procesadas.
- En modo `Rapido`, el progreso se reporta por hitos del proceso.
- El analisis cuenta imagenes por ocurrencia en paginas (no unicas globales).

## Problemas comunes

- **No se encontro Tesseract en PATH**
  - Verifica instalacion y ruta en variables de entorno.

- **No se encontro Ghostscript en PATH**
  - Verifica `gswin64c.exe` y carpeta `bin` en PATH.

- **Please install the appropriate language data**
  - Faltan archivos de idioma (`spa.traineddata`/`eng.traineddata`) en `tessdata`.

- **PDF protegido o cifrado**
  - La app bloquea OCR si detecta restricciones incompatibles.

- **No se genera archivo de salida**
  - Revisa permisos de escritura en la carpeta del PDF original.

## Licencia y uso

Este proyecto usa librerias de terceros (por ejemplo `ocrmypdf`, `tesseract`, `ghostscript`) con sus propias licencias. Revisa sus terminos si vas a distribuir TELITA OCR comercialmente.
