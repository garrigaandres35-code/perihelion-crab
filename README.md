# Data Sports Lab (Perihelion-Crab)

📊 **Un espacio para aficionados a la ciencia de datos en el mundo de las competencias deportivas online**

## 🎯 Características

- **Sistema de Scraping Modular**: Extracción de datos desde web y PDFs.
- **Navegación Robusta**: `ResultsDetailScraper` con manejo automático de prompts ("Si"), esperas inteligentes y selección por dropdown.
- **Batch Scraping UI**: Capacidad de procesar lotes de carreras filtradas secuencialmente desde la interfaz de administración.
- **Estandarización de Datos**: Sistema heurístico para uniformar resultados de diferentes hipódromos (HCH 20 cols vs Estándar 12 cols).
- **Gestión de PDFs de Volantes**: 
  - Carga manual desde explorador de archivos del cliente.
  - Organización automática por recinto.
  - Indicador visual en tabla de competencias.
  - Scripts de regularización automática para vincular PDFs existentes.
- **Filtros Dinámicos con Persistencia**: Filtrado por recinto y estado con almacenamiento en `localStorage`.
- **UI Moderna y Premium**: Interfaz dark mode con glassmorphism y micro-animaciones.
- **Menú Dinámico**: Sistema configurable mediante JSON.
- **Base de Datos SQLite**: Almacenamiento eficiente con SQLAlchemy.

## 📁 Estructura del Proyecto

```
perihelion-crab/
├── app/
│   ├── routes/          # Blueprints de Flask
│   ├── modules/         # Módulos de negocio (scraping, análisis, modelos)
│   ├── static/          # CSS, JS, imágenes
│   └── templates/       # Templates HTML (UI de Batch Scraping)
├── data/                # Base de datos y datos scrapeados
│   ├── web_scraping/
│   │   └── resultados_detalle/  # JSONs de resultados avanzados
│   └── pdf_scraping/
│       ├── pdfs/        # PDFs de volantes organizados por recinto
│       └── json/        # Metadata extraída de PDFs
├── config/              # Configuraciones JSON
└── tests/               # Tests unitarios
```

## 🚀 Instalación y Ejecución

1. **Entorno**: `python -m venv venv` y `venv\Scripts\activate`.
2. **Dependencias**: `pip install -r requirements.txt`.
3. **Arranque**: `python run.py`.
4. **Acceso**: `http://localhost:8080`.

## 📊 Módulos de Scraping

- **Web (Programas)**: Playwright estándar.
- **Web (Resultados)**: `ResultsDetailScraper` con navegación por dropdown y detección de prompts.
- **PDF**: Procesamiento IA (LlamaExtract) con fallback de Regex.

## 🎨 Características de UI (Admin)

- **Indicadores P/R/V**:
  - **P**: Programas (Web List).
  - **R**: Resultados Detallados (Carpeta `resultados_detalle`).
  - **V**: Volantes (Extracción PDF AI).
- **Gestión de Competencias**:
  - Nombre auto-generado en formato `{RECINTO}-{YYYY}_{MM}_{DD}`.
  - Campos obligatorios: Recinto y Fecha.
  - Carga de PDF de volante desde modal de edición.
  - Icono verde indica PDF asociado.
- **Batch Processing**: El botón "Procesar Filtrados" en la sección de Scraping permite ejecutar la cola de forma automática y secuencial.
- **Filtros Persistentes**: Filtrado dinámico por recinto y estado con persistencia en `localStorage`.

## 🧪 Testing

```bash
python -m pytest tests/
```

---
**Desarrollado para análisis predictivo deportivo, comenzando con hípica chilena (HCH, CHS, VSC).**
