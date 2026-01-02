# 🚀 Perihelion-Crab - Guía de Configuración

## Requisitos Previos
- Python 3.10+
- Git
- Visual Studio Code con extensión Antigravity (opcional)

---

## 📥 Instalación en Nuevo Computador

### 1. Clonar el repositorio
```bash
git clone https://github.com/garrigaandres35-code/perihelion-crab.git
cd perihelion-crab
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Instalar Playwright (para web scraping)
```bash
playwright install chromium
```

### 5. Crear archivo `.env`
Crear archivo `.env` en la raíz del proyecto (NO se sincroniza por seguridad):

```env
# Credenciales ElTurf
ELTURF_USER=tu_usuario_elturf
ELTURF_PASSWORD=tu_password_elturf

# LlamaCloud API (para PDF scraping)
LLAMA_CLOUD_API_KEY=tu_api_key_llama

# Flask
SECRET_KEY=una_clave_secreta_segura
FLASK_DEBUG=True
```

### 6. Crear estructura de datos
```bash
# Windows PowerShell
mkdir -Force data/web_scraping/resultados_detalle
mkdir -Force data/web_scraping/programas
mkdir -Force data/pdf_scraping
mkdir -Force logs

# Linux/Mac
mkdir -p data/web_scraping/resultados_detalle
mkdir -p data/web_scraping/programas
mkdir -p data/pdf_scraping
mkdir -p logs
```

### 7. Ejecutar la aplicación
```bash
python run.py
```
Acceder a: **http://localhost:8080**

---

## 👥 Flujo de Trabajo en Equipo

### Antes de empezar a trabajar
```bash
git pull origin master
```

### Comandos Git básicos
| Acción | Comando |
|--------|---------|
| Ver estado | `git status` |
| Agregar cambios | `git add .` |
| Hacer commit | `git commit -m "Descripción del cambio"` |
| Subir cambios | `git push origin master` |
| Actualizar local | `git pull origin master` |

### Resolver conflictos
Si hay conflictos al hacer pull:
1. Git marcará los archivos en conflicto
2. Editar manualmente los archivos
3. `git add .` para marcar como resueltos
4. `git commit -m "Merge: resolver conflictos"`

---

## ⚠️ Archivos NO sincronizados (en .gitignore)

| Archivo/Carpeta | Razón |
|-----------------|-------|
| `.env` | Credenciales sensibles |
| `data/` | Datos de scraping (muy pesados) |
| `logs/` | Logs de la aplicación |
| `venv/` | Entorno virtual |
| `*.db` | Base de datos local |

---

## 🔧 Troubleshooting

### Error: "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### Error: "Playwright not installed"
```bash
playwright install chromium
```

### Error de permisos en Windows
Ejecutar PowerShell como Administrador.

---

## 📁 Estructura del Proyecto
```
perihelion-crab/
├── app/
│   ├── modules/
│   │   ├── scraping/      # Web + PDF scrapers
│   │   ├── analysis/      # Análisis de datos
│   │   └── models/        # ML models
│   ├── routes/            # Flask blueprints
│   └── templates/         # HTML templates
├── config/                # Configuración
├── data/                  # Datos (ignorado)
├── logs/                  # Logs (ignorado)
└── run.py                 # Entry point
```
