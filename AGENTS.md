# Protocolo para Agentes de Desarrollo (Antigravity) 🤖

Este documento proporciona contexto crítico para que los agentes de IA y desarrolladores colaboren eficazmente en el proyecto `perihelion-crab`.

## 📌 Visión General
`perihelion-crab` es una plataforma de análisis predictivo deportivo (foco inicial: hípica) que utiliza técnicas de scraping avanzadas y modelos de Machine Learning.

## 🏗️ Arquitectura para Agentes
Al trabajar en este repositorio, sigue estas directrices:

### 1. Sistema de Scraping
- **Web**: Localizado en `app/modules/scraping/web/`. Usa `Playwright`. Preferir selectores robustos.
- **PDF**: Localizado en `app/modules/scraping/pdf_scraper.py`.
  - **Enfoque Híbrido**: Usa `PyMuPDF` (`fitz`) para escaneo rápido de cabeceras (Fecha/Reunión) y `LlamaExtract` (LlamaIndex Cloud) para extracción profunda estructurada.
  - **Matching por Contenido**: Se valida la fecha dentro del PDF antes de enviarlo a procesar, evitando dependencia de nombres de archivo.
  - **Fallback**: Se usan datos extraídos por Regex (Scanner) si el modelo falla en campos críticos como `nro_reunion`.
- **Persistencia**: Los datos deben pasar por validadores de `Pydantic` (`pdf_models.py`) antes de guardarse en SQLite.
- **Verificación de Estado**: El estado del scraping (P/R/V) se determina mediante la existencia de archivos JSON en el sistema de archivos (`check_scraping_status` en `app/modules/scraping/utils.py`), no solo por la BD.

### 2. Interfaz de Usuario (UI)
- **Estilo**: Vanilla CSS. Mantener estética "Dark Mode Premium" con glassmorphism.
- **Componentes**: Reutilizar clases de `static/css/main.css`. No introducir frameworks de CSS adicionales sin permiso.

### 3. Base de Datos
- Usa SQLAlchemy. Los modelos están en `app/models/`.
- Siempre verifica si una entidad ya existe antes de crear un duplicado (ej. `Venues` por nombre/slug).

## 🛠️ Flujo de Trabajo del Agente
1. **Planificación**: Siempre genera un `implementation_plan.md` antes de cambios estructurales.
2. **Tareas**: Mantener el archivo `task.md` actualizado para visibilidad del usuario.
3. **Verificación**: Ejecutar `pytest` tras modificar módulos de negocio.

## 📡 Historial de Conversación Crítico
- Se han corregido errores de codificación UTF-8 en versiones previas.
- El sistema de menús es dinámico y se carga desde `config/menu_config.json`.

---
*Este documento es dinámico y debe ser actualizado por los agentes cuando se realicen cambios de arquitectura significativos.*
