"""
Scraping Configuration
Centralized configuration for Web and PDF scraping modules
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ScrapingConfig:
    """Centralized scraping configuration"""
    
    # ElTurf credentials
    ELTURF_USUARIO = os.getenv('ELTURF_USUARIO', '')
    ELTURF_CLAVE = os.getenv('ELTURF_CLAVE', '')
    ELTURF_BASE_URL = os.getenv('ELTURF_BASE_URL', 'https://elturf.com')
    ELTURF_LOGIN_URL = os.getenv('ELTURF_LOGIN_URL', 'https://elturf.com/login')
    
    # API Endpoints
    API_PROGRAMAS = f"{ELTURF_BASE_URL}/api/elturfhome/programas/reuniones/fecha"
    API_RESULTADOS = f"{ELTURF_BASE_URL}/api/elturfhome/resultados/reuniones/fecha"
    API_DETALLE_CARRERA = f"{ELTURF_BASE_URL}/api/elturf/programa"
    
    # Shared parameters
    DIA_REUNION = os.getenv('SCRAPING_DIA_REUNION', '')
    HIPODROMO = os.getenv('SCRAPING_HIPODROMO', 'HCH')
    
    # Storage paths
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    PATH_WEB_SCRAPING = Path(os.getenv('PATH_WEB_SCRAPING', './data/web_scraping'))
    PATH_PDF_SCRAPING = Path(os.getenv('PATH_PDF_SCRAPING', './data/pdf_scraping'))
    COOKIES_PATH = Path(os.getenv('COOKIES_PATH', './data/web_scraping/cookies_sesion.json'))
    
    # Hipódromo mapping
    HIPODROMOS = {
        'HCH': {
            'name': 'Hipódromo Chile',
            'set_value': 'Hipódromo Chile',
            'get_value': 'HCH'
        },
        'CHS': {
            'name': 'Club Hípico de Santiago',
            'set_value': 'Club Hípico de Santiago',
            'get_value': 'CHS'
        },
        'VSC': {
            'name': 'Valparaíso Sporting',
            'set_value': 'Valparaíso Sporting',
            'get_value': 'VSC'
        }
    }
    
    @classmethod
    def get_hipodromo_name(cls, code: str) -> str:
        """Get full name for hipódromo code"""
        return cls.HIPODROMOS.get(code, {}).get('name', code)
    
    @classmethod
    def get_hipodromo_set_value(cls, code: str) -> str:
        """Get SET value for hipódromo (used in API filters)"""
        return cls.HIPODROMOS.get(code, {}).get('set_value', code)
    
    @classmethod
    def update_config(cls, fecha: str = None, hipodromo: str = None):
        """Update configuration values"""
        if fecha:
            cls.DIA_REUNION = fecha
            os.environ['SCRAPING_DIA_REUNION'] = fecha
        if hipodromo:
            cls.HIPODROMO = hipodromo
            os.environ['SCRAPING_HIPODROMO'] = hipodromo
    
    @classmethod
    def has_credentials(cls) -> bool:
        """Check if ElTurf credentials are configured"""
        return bool(cls.ELTURF_USUARIO and cls.ELTURF_CLAVE)
