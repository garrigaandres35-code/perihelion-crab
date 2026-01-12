# Protocolo para Agentes de Desarrollo (Antigravity) 🤖

Este documento proporciona contexto crítico para que los agentes de IA y desarrolladores colaboren eficazmente en el proyecto `perihelion-crab`.

## 📌 Visión General
`perihelion-crab` es una plataforma de análisis predictivo deportivo (foco inicial: hípica) que utiliza técnicas de scraping avanzadas y modelos de Machine Learning.

## 🏗️ Arquitectura para Agentes
Al trabajar en este repositorio, sigue estas directrices:

### 1. Sistema de Scraping
- **Web**: Localizado en `app/modules/scraping/`.
  - **Programas**: Usa `Playwright` estándar.
  - **Resultados**: Usa `ResultsDetailScraper` (`app/modules/scraping/results_detail_scraper.py`).
    - **Navegación Robusta**: Utiliza iteración por `<select>` (Dropdown) en lugar de botones.
    - **Manejo de Prompts**: Detecta y clickea automáticamente botones de confirmación ("Si").
    - **Estandarización de 12 Columnas**: Implementa un sistema de mapeo por **heurística de contenido** para soportar tablas de HCH (20 cols) y estándar (11-12 cols) uniformemente.
- **PDF**: Localizado en `app/modules/scraping/pdf_scraper.py`.
  - **Enfoque Híbrido**: Usa `PyMuPDF` (`fitz`) para escaneo rápido de cabeceras (Fecha/Reunión) y `LlamaExtract` para extracción profunda.
  - **Gestión de Volantes**: Sistema de carga manual de PDFs desde interfaz web.
    - **Upload desde Cliente**: Modal de edición permite cargar PDFs desde explorador de archivos.
    - **Organización**: PDFs se guardan en `data/pdf_scraping/pdfs/{recinto}/` con nombre original.
    - **Validaciones**: Tipo PDF, tamaño máximo 10MB, nombre sanitizado.
    - **Indicador Visual**: Icono verde en tabla de competencias cuando hay PDF asociado.
- **Persistencia**: Los datos se guardan en `data/web_scraping/resultados_detalle/` como JSON estructurado.
- **Verificación de Estado**: El flag 'R' (Resultados) en la UI solo se activa si existe el archivo en la subcarpeta `resultados_detalle`.
- **Regularización de Datos**: Scripts automatizados para vincular competencias con PDFs mediante análisis de JSONs (`phase1`, `phase2`, `phase3`).

### 2. Interfaz de Usuario (UI)
- **Batch Scraping**: La UI permite procesamiento secuencial de lotes filtrados mediante el botón "Procesar Filtrados".
- **Filtros Dinámicos**: Implementa filtrado por estado (P/R/V) y recinto con persistencia en `localStorage`.
- **Gestión de PDFs**: 
  - **Carga Manual**: Modal de edición de competencias permite subir PDFs de volantes.
  - **Indicador de Estado**: Icono verde junto al nombre cuando hay PDF asociado.
  - **Actualización Automática**: Tabla se refresca después de operaciones de scraping.
- **Estilo**: Vanilla CSS con estética "Dark Mode Premium". No romper el layout de glassmorphism.

### 3. Base de Datos
- Usa SQLAlchemy. Los modelos están en `app/models/`.
- Siempre verifica si una entidad ya existe antes de crear un duplicado (ej. `Venues` por nombre/slug).
- **Campo `pdf_volante_path`**: Almacena ruta relativa al PDF del volante (`data\pdf_scraping\pdfs\{recinto}\{archivo}.pdf`).

## 🛠️ Flujo de Trabajo del Agente
1. **Planificación**: Siempre genera un `implementation_plan.md` antes de cambios estructurales.
2. **Tareas**: Mantener el archivo `task.md` actualizado para visibilidad del usuario.
3. **Verificación**: Ejecutar `pytest` tras modificar módulos de negocio.

## 📡 Historial de Conversación Crítico
- Se han corregido errores de codificación UTF-8 en versiones previas.
- El sistema de menús es dinámico y se carga desde `config/menu_config.json`.

---
*Este documento es dinámico y debe ser actualizado por los agentes cuando se realicen cambios de arquitectura significativos.*
