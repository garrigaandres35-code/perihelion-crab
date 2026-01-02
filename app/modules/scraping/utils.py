import os
from pathlib import Path
import glob
from app.modules.scraping.scraping_config import ScrapingConfig

def check_scraping_status(competition):
    """
    Check availability of Programas, Resultados, and Volantes for a competition.
    Returns a dict with 'P', 'R', 'V' booleans.
    """
    status = {'P': False, 'R': False, 'V': False}
    
    if not competition.event_date:
        return status
        
    date_str = competition.event_date.strftime('%Y-%m-%d')
    date_fmt_2 = competition.event_date.strftime('%d-%m-%Y')
    
    # P: Programas
    prog_pattern = Path(ScrapingConfig.PATH_WEB_SCRAPING) / 'programas' / f"programas_*_{date_str}.json"
    status['P'] = bool(glob.glob(str(prog_pattern)))
    
    # R: Resultados (Updated to check for Detailed Results)
    # Checks for files in 'resultados_detalle' folder with pattern resultados_detalle_{HIP}_{DATE}.json
    res_pattern = Path(ScrapingConfig.PATH_WEB_SCRAPING) / 'resultados_detalle' / f"resultados_detalle_*_{date_str}.json"
    status['R'] = bool(glob.glob(str(res_pattern)))
    
    # V: Volantes
    if competition.venue and competition.venue.abbreviation:
        track = competition.venue.abbreviation.lower()
        json_dir = Path(ScrapingConfig.PATH_PDF_SCRAPING) / 'json' / track
        
        if json_dir.exists():
            # Optimize for HCH: Check filename pattern first
            if track == 'hch':
                if list(json_dir.glob(f"volante_*_{date_str}.json")):
                    status['V'] = True
            
            # Standard check (content-based) if not found by filename
            if not status['V']:
                for json_file in json_dir.glob('*.json'):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            content = f.read(1000) # Read header
                            if f'"fecha": "{date_str}"' in content or f'"fecha": "{date_fmt_2}"' in content:
                                status['V'] = True
                                break
                    except:
                        continue
                    
    return status
