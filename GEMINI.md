# PERIHELION-CRAB (GEMINI CONTEXT)

## 📌 Project Overview
**Perihelion-Crab** is a data science platform for horse racing analysis (Data Sports Lab). It focuses on Chilean racetracks (HCH, CHS, VSC) and features a hybrid scraping system (Web + PDF) to feed a predictive model.

**Tech Stack:**
- **Backend:** Python 3.10+, Flask 3.0, SQLAlchemy.
- **Database:** SQLite (`data/database.db`).
- **Scraping:**
  - **Web:** Playwright + Requests (`elturf.com`). New `ResultsDetailScraper` for deep results extraction.
  - **PDF:** PyMuPDF (Header Scan) + LlamaExtract (Deep Extraction).
- **Frontend:** HTML5/CSS3 (Vanilla), Glassmorphism UI.

## 📂 Key Directory Structure
```
D:/Proyectos/perihelion-crab/
├── app/
│   ├── modules/
│   │   ├── scraping/
│   │   │   ├── web_scraper.py         # Main entry, calls ResultsDetailScraper
│   │   │   ├── results_detail_scraper.py # Dropdown navigation & 12-col heuristic extraction
│   │   │   ├── pdf_scraper.py         # LlamaIndex logic for PDF processing
│   │   │   └── utils.py               # Status check logic (P/R/V)
│   ├── models.py                # SQLAlchemy DB Models
│   ├── routes/                  # Flask Blueprints
│   └── templates/               # HTML Templates (Batch Scraping UI)
├── data/                        # Data Storage
│   ├── web_scraping/            
│   │   └── resultados_detalle/  # Detailed results JSONs (Source for 'R')
│   └── pdf_scraping/            # PDFs and extracted JSONs
├── config/                      # Configuration files (menu_config.json)
├── run.py                       # Application Entry Point
└── requirements.txt             # Project Dependencies
```

## 🚀 Running the Project
1. **Activate Virtual Environment:**
   `venv/Scripts/activate`
2. **Run Server:**
   `python run.py`
   - Access at: `http://localhost:8080`

## 🧠 Core Concepts

### 1. Scraping Status (P/R/V)
The system tracks the state of each race meeting using three indicators:
- **P (Programas):** Datos de la reunión.
- **R (Resultados):** Valida **Resultados Detallados** en `data/web_scraping/resultados_detalle/`. Los resultados simples heredados son ignorados.
- **V (Volantes):** Extracción de PDF mediante IA (LlamaExtract).

### 2. Data Flow
1. **Scrape:**
   - **Results:** `ResultsDetailScraper` usa navegación por dropdown para robustez y un sistema de **heurística de contenido** para estandarizar 12 columnas (manejando las 20 de HCH).
   - **Batching:** La UI envía peticiones secuenciales para procesar múltiples eventos filtrados automáticamente.
2. **Ingest:** Data is processed and loaded into SQLite via `app/models.py`.
3. **Analyze:** Historical data is used to train models.

### 3. PDF Processing Strategy
- **Scan:** `fitz` (PyMuPDF) quickly reads the header for Date/Meeting#.
- **Extract:** If date matches, `LlamaExtract` envía el PDF a LlamaCloud.
- **Fallback:** Regex fallback available.

## ⚠️ Critical Constraints & Agents Protocol
- **Tools:** Use `mcp-exec` with `rust-mcp-filesystem` tools.
- **Conventions:** Follow `AGENTS.md` protocols.
- **Testing:** Run `python -m pytest tests/` before major PRs.
- **Logs:** Check `logs/app.log` for scraping errors (especialmente warnings de "No se encontró la tabla").
