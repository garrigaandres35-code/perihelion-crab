# Data Sports Lab

📊 **Un espacio para aficionados a la ciencia de datos en el mundo de las competencias deportivas online**

## 🎯 Características

- **Sistema de Scraping Modular**: Extracción de datos desde web y PDFs
- **Arquitectura Escalable**: Diseñada para múltiples deportes (comenzando con hípica)
- **UI Moderna y Premium**: Interfaz dark mode con glassmorphism y animaciones suaves
- **Menú Dinámico**: Sistema de navegación configurable mediante JSON
- **API RESTful**: Endpoints para integración con otros sistemas
- **Base de Datos SQLite**: Almacenamiento eficiente para desarrollo/testing

## 📁 Estructura del Proyecto

```
perihelion-crab/
├── app/
│   ├── routes/          # Blueprints de Flask
│   ├── modules/         # Módulos de negocio (scraping, análisis, modelos)
│   ├── utils/           # Utilidades (menú, database)
│   ├── static/          # CSS, JS, imágenes
│   └── templates/       # Templates HTML
├── config/              # Configuraciones JSON
├── data/                # Base de datos y datos scrapeados
└── tests/               # Tests unitarios
```

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
cd perihelion-crab
```

### 2. Crear entorno virtual

```bash
python -m venv venv
```

### 3. Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

## ▶️ Ejecución

### Modo Desarrollo

```bash
python run.py
```

La aplicación estará disponible en: `http://localhost:5000`

### Variables de Entorno

Edita el archivo `.env` para configurar:

```env
FLASK_DEBUG=True
FLASK_PORT=5000
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///data/database.db
```

## 📊 Módulos

### 1. Scraping

- **Web Scraping**: Extracción de datos de sitios web de hipódromos
- **PDF Scraping**: Procesamiento de volantes PDF (HCH, CHS, VSC)

**Ubicación**: `app/modules/scraping/`

**Integración**: Copia tu código existente a:
- `web_scraper.py` - Para scraping web
- `pdf_scraper.py` - Para procesamiento de PDFs

### 2. Análisis

Módulo para análisis de datos históricos e identificación de patrones.

**Ubicación**: `app/modules/analysis/`

### 3. Modelos Predictivos

Framework para entrenamiento y ejecución de modelos de Machine Learning.

**Ubicación**: `app/modules/models/`

## 🎨 Características de UI

- ✨ **Dark Mode Premium**: Paleta de colores moderna
- 🌈 **Glassmorphism**: Efectos de vidrio esmerilado
- 🎭 **Animaciones Suaves**: Transiciones y micro-interacciones
- 📱 **Responsive**: Diseño adaptable a todos los dispositivos
- 🎯 **Iconos Feather**: Sistema de iconos moderno

## 🔧 Configuración del Menú

El menú se configura mediante `config/menu_config.json`:

```json
{
  "menu_items": [
    {
      "id": "admin",
      "label": "Administración",
      "icon": "settings",
      "submenu": [...]
    }
  ]
}
```

## 🗄️ Base de Datos

### Modelos Principales

- **Sport**: Tipos de deportes/competencias
- **Venue**: Hipódromos/Lugares
- **Event**: Eventos/Reuniones
- **Race**: Carreras
- **Participant**: Competidores
- **ScrapingLog**: Registro de scraping
- **Configuration**: Configuraciones del sistema

### Inicialización

La base de datos se inicializa automáticamente al primer arranque con:
- Deporte: Hípica
- Hipódromos: HCH, CHS, VSC
- Configuraciones por defecto

## 🔌 API Endpoints

### Venues
```
GET /api/venues
```

### Events
```
GET /api/events?venue=HCH&date=2024-12-09
```

### Races
```
GET /api/races/<event_id>
```

### Participants
```
GET /api/participants/<race_id>
```

### Statistics
```
GET /api/stats
```

## 🧪 Testing

```bash
python -m pytest tests/
```

## 📝 Próximos Pasos

1. **Integrar tus proyectos de scraping existentes**
   - Copiar código a `app/modules/scraping/`
   - Actualizar rutas en `app/routes/scraping.py`

2. **Desarrollar módulo de análisis**
   - Implementar análisis estadístico
   - Generar visualizaciones

3. **Implementar modelos predictivos**
   - Entrenar modelos ML
   - Crear sistema de predicciones

4. **Expandir a otros deportes**
   - Agregar nuevos sports en la BD
   - Adaptar scrapers

## 🛠️ Tecnologías

- **Backend**: Flask 3.0, SQLAlchemy
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript
- **Base de Datos**: SQLite
- **Scraping**: Playwright, PyMuPDF, BeautifulSoup4, Llama-Parse
- **Análisis**: Pandas, NumPy

## 📄 Licencia

Proyecto de desarrollo para análisis predictivo deportivo.

## 👨‍💻 Desarrollo

Desarrollado como plataforma modular y escalable para predicción deportiva, comenzando con hípica chilena (HCH, CHS, VSC).

---

**¿Necesitas ayuda?** Revisa la documentación en `/admin` o contacta al equipo de desarrollo.
