"""
PDF Scraper Module
Manager for PDF extraction using LlamaExtract API (LlamaIndex Cloud)
"""
import os
import json
import logging
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from llama_cloud_services import LlamaExtract
from llama_cloud import ExtractConfig

from app.modules.scraping.scraping_config import ScrapingConfig
from app.modules.scraping.pdf_models import Meeting, Race

logger = logging.getLogger(__name__)

# Schema for LlamaExtract
DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
        "reunion": {"type": "integer", "description": "Número de reunión extraído del encabezado (precedido por 'Reunión N°' o 'REUNIÓN N°')"},
        "carreras": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer"},
                    "opcion": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 4,
                        "maxItems": 4
                    },
                    "numero_competidores": {"type": "integer"}
                },
                "required": ["numero", "opcion", "numero_competidores"]
            }
        }
    },
    "required": ["fecha", "reunion", "carreras"],
    "additionalProperties": False
}

# Extraction Configuration
EXTRACT_CONFIG = {
    "priority": None,
    "extraction_target": "PER_DOC",
    "extraction_mode": "PREMIUM",
    "parse_model": "gemini-2.5-pro",
    "extract_model": "openai-gpt-5-mini",
    "multimodal_fast_mode": True,
    "system_prompt": None,
    "use_reasoning": False,
    "cite_sources": False,
    "citation_bbox": False,
    "confidence_scores": False,
    "chunk_mode": "PAGE",
    "high_resolution_mode": False,
    "invalidate_cache": False,
    "num_pages_context": None,
    "page_range": None
}

# Specific prompts for each racetrack to improve extraction speed and accuracy
TRACK_PROMPTS = {
    'hch': "Estás procesando el 'Volante' de Hipódromo Chile (HCH). "
           "El número de REUNIÓN se encuentra después de 'REUNION N°'. "
           "Las carreras muestran la hora aprox, distancia y un código en paréntesis. "
           "La tabla de participantes incluye columnas de PESO, JINETE-PREPARADOR y STUD. "
           "Extrae con precisión la 'serie' y el 'indice' si es HANDICAP.",
    'chs': "Estás procesando el programa de Club Hípico de Santiago (CHS). "
           "La fecha suele estar en formato 'DÍA DD MES AAAA' (ej: VIERNES 21 NOVIEMBRE 2025). "
           "La DISTANCIA está en la segunda línea de cada bloque de carrera junto con el número de carrera. "
           "Los participantes tienen el formato 'Nro Nombre - Sire Peso'. "
           "El Jinete y Preparador están separados por un guión en una línea inferior.",
    'vsc': "Estás procesando el programa de Valparaíso Sporting Club (VSC). "
           "El formato es similar a HCH. Busca 'Valparaíso Sporting' para confirmar el recinto. "
           "Extrae todas las carreras y participantes asegurando que el 'codigo' sea el número entre paréntesis."
}


class PDFScraperManager:
    """
    PDF scraper manager using LlamaExtract API
    Supports HCH, CHS, and VSC hipódromos
    """
    
    TRACK_MAP = {
        'hch': {'pdf_dir': 'pdfs/hch', 'json_dir': 'json/hch'},
        'chs': {'pdf_dir': 'pdfs/chs', 'json_dir': 'json/chs'},
        'vsc': {'pdf_dir': 'pdfs/vsc', 'json_dir': 'json/vsc'}
    }

    # Regex for Header Scanning (HCH specific mainly, but generic enough)
    WEEKDAYS = r"(Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado|Domingo)"
    R_DATE_HEADER = re.compile(rf"{WEEKDAYS}\s+\d{{1,2}}\s+de\s+\w+\s+de\s+\d{{4}}", re.IGNORECASE)
    R_REUNION_HEADER = re.compile(r"REUNION\s*N[ºo]\s*(\d+)", re.IGNORECASE)
    
    def __init__(self, track: str = None):
        """Initialize PDF Scraper Manager"""
        self.track = (track or ScrapingConfig.HIPODROMO).lower()
        self.base_path = ScrapingConfig.PATH_PDF_SCRAPING
        self.cache_dir = Path(self.base_path) / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LlamaExtract (uses LLAMA_CLOUD_API_KEY from environment)
        try:
            self.extractor = LlamaExtract()
        except Exception as e:
            logger.error(f"Failed to initialize LlamaExtract: {e}")
            self.extractor = None

    def _convert_date_to_iso(self, date_text: str) -> str:
        """Converts date text to YYYY-MM-DD format"""
        if not date_text:
            return "0000-00-00"
            
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_text):
            return date_text
        
        months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', date_text.lower())
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))
            month = months.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
        
        return date_text

    def _scan_pdf_header(self, pdf_path: str) -> Dict[str, Any]:
        """
        Scans the first page of the PDF to extract Date and Meeting Number using Regex.
        This allows for content-based matching and fallback values.
        """
        try:
            doc = fitz.open(pdf_path)
            # Read only the first page, typically enough for header
            if len(doc) > 0:
                text = doc[0].get_text("text")
            else:
                text = ""
            doc.close()

            # Search for Date
            date_match = self.R_DATE_HEADER.search(text)
            date_iso = None
            if date_match:
                date_iso = self._convert_date_to_iso(date_match.group(0))

            # Search for Reunion
            reunion_match = self.R_REUNION_HEADER.search(text)
            reunion = None
            if reunion_match:
                reunion = int(reunion_match.group(1))

            return {
                "fecha": date_iso,
                "reunion": reunion
            }
        except Exception as e:
            logger.error(f"Error scanning PDF header for {pdf_path}: {e}")
            return {"fecha": None, "reunion": None}
            
    def process_pdf(self, pdf_path: str, track: str = None, target_date: str = None) -> Dict[str, Any]:
        """Process a single PDF file using LlamaExtract"""
        track = (track or self.track).lower()
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return {'success': False, 'error': f"PDF not found: {pdf_path}"}
        
        if not self.extractor:
            return {'success': False, 'error': "LlamaExtract not initialized. Check LLAMA_CLOUD_API_KEY."}

        logger.info(f"Processing PDF with LlamaExtract: {pdf_path}")

        # 1. SCAN HEADER FIRST (Content-Based Check)
        scanned_header = self._scan_pdf_header(str(pdf_path))
        scanned_date = scanned_header.get('fecha')
        
        # 2. Content Matching (if target_date provided)
        if target_date:
            if scanned_date and scanned_date != target_date:
                return {
                    'success': False, # It's not a failure, just a skip. But we return False to filtering logic.
                    'skipped': True,
                    'message': f"Skipped: Date mismatch. PDF date {scanned_date} != Target {target_date}"
                }
            logger.info(f"Date match confirmed: {scanned_date}")
        
        try:
            # Check if JSON already exists before processing
            json_dir = Path(self.base_path) / self.TRACK_MAP[track]['json_dir']
            
            # Determine output filename logic
            output_filename = f"{pdf_path.stem}.json" # Default
            existing_path = None
            
            if track == 'hch':
                # For HCH, check if any file matches volante_{stem}_*.json
                # This covers cases where we already processed it with a date
                pattern = f"volante_{pdf_path.stem}_*.json"
                existing_files = list(json_dir.glob(pattern))
                if existing_files:
                    existing_path = existing_files[0]
            else:
                # Standard check
                potential_path = json_dir / output_filename
                if potential_path.exists():
                    existing_path = potential_path
            
            if existing_path and existing_path.exists():
                logger.info(f"[SKIP] {pdf_path.name} - JSON already exists at {existing_path.name}")
                # Load existing data to return it
                with open(existing_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                return {
                    'success': True,
                    'pdf_path': str(pdf_path),
                    'json_path': str(existing_path),
                    'meeting': existing_data,
                    'races_count': len(existing_data.get('carreras', [])),
                    'message': f"Skipped: {pdf_path.name} already processed as {existing_path.name}"
                }

            # Prepare configuration with track-specific prompt
            extract_params = EXTRACT_CONFIG.copy()
            if track in TRACK_PROMPTS:
                extract_params["system_prompt"] = TRACK_PROMPTS[track]
            
            config = ExtractConfig(**extract_params)
            logger.info(f"Extracting data from {pdf_path.name} (Track: {track.upper()}) using Premium mode...")
            result = self.extractor.extract(DATA_SCHEMA, config, str(pdf_path))
            data = result.data
            
            # Post-processing and Validation
            data['recinto'] = track.upper()
            data['fecha'] = self._convert_date_to_iso(data.get('fecha'))
            
            if not data.get('reunion'):
                # FALLBACK: Use scanned reunion if API returned 0 or null
                if scanned_header.get('reunion'):
                    logger.info(f"Using fallback reunion from scan: {scanned_header['reunion']}")
                    data['reunion'] = scanned_header['reunion']
                else:
                    data['reunion'] = 0
            
            logger.info(f"Successfully extracted data from {pdf_path.name}. Reunión N° {data['reunion']}, Fecha: {data['fecha']}")
            
            # Validate races
            if 'carreras' in data:
                for carrera in data['carreras']:
                    if not carrera.get('opcion') or len(carrera.get('opcion', [])) != 4:
                        carrera['opcion'] = [0, 0, 0, 0]
            
            # Create Meeting object for validation
            meeting = Meeting(**data)
            
            # Save to JSON
            json_dir = Path(self.base_path) / self.TRACK_MAP[track]['json_dir']
            json_dir.mkdir(parents=True, exist_ok=True)
            
            # Construct final filename based on track
            if track == 'hch':
                # Format: volante_[ID]_[DATE].json
                # ID = pdf_path.stem
                # DATE = data['fecha']
                output_filename = f"volante_{pdf_path.stem}_{data['fecha']}.json"
            else:
                output_filename = f"{pdf_path.stem}.json"
                
            output_path = json_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(meeting.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved JSON: {output_path}")
            
            return {
                'success': True,
                'pdf_path': str(pdf_path),
                'json_path': str(output_path),
                'meeting': meeting.to_dict(),
                'races_count': len(meeting.carreras),
                'message': f"Extracted {len(meeting.carreras)} races from {pdf_path.name}"
            }
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return {
                'success': False,
                'pdf_path': str(pdf_path),
                'error': str(e),
                'message': f"Failed to process {pdf_path.name}"
            }
    
    def process_directory(self, directory: str = None, track: str = None, target_date: str = None) -> Dict[str, Any]:
        """Process all PDFs in a track's directory"""
        track = (track or self.track).lower()
        
        if directory:
            pdf_dir = Path(directory)
        else:
            pdf_dir = Path(self.base_path) / self.TRACK_MAP[track]['pdf_dir']
        
        if not pdf_dir.exists():
            pdf_dir.mkdir(parents=True, exist_ok=True)
            return {'success': True, 'processed': 0, 'failed': 0, 'results': [], 'message': f"No PDFs found in {pdf_dir}"}
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            return {'success': True, 'processed': 0, 'failed': 0, 'results': [], 'message': f"No PDF files found in {pdf_dir}"}
        
        # Calculate summary before starting
        json_dir = Path(self.base_path) / self.TRACK_MAP[track]['json_dir']
        
        def is_processed(pdf_path):
            if track == 'hch':
                # Check for volante_{stem}_*.json
                return bool(list(json_dir.glob(f"volante_{pdf_path.stem}_*.json")))
            else:
                return (json_dir / f"{pdf_path.stem}.json").exists()

        already_processed = [f for f in pdf_files if is_processed(f)]
        to_process = [f for f in pdf_files if not is_processed(f)]
        
        logger.info(f"--- Batch Processing Summary ({track.upper()}) ---")
        logger.info(f"Total PDFs found: {len(pdf_files)}")
        logger.info(f"Already processed (will skip): {len(already_processed)}")
        logger.info(f"New PDFs to process: {len(to_process)}")
        logger.info(f"---------------------------------------------")
        
        if not to_process:
            logger.info("Nothing to process.")
            return {
                'success': True, 
                'processed': 0, 
                'failed': 0, 
                'results': [], 
                'message': f"All PDFs in {track.upper()} are already processed."
            }

        results = []
        processed = 0
        failed = 0
        
        for pdf_file in pdf_files:
            # The individual process_pdf now handles the skip check and logging
            result = self.process_pdf(str(pdf_file), track, target_date=target_date)
            
            if result.get('skipped'):
                continue

            results.append(result)
            
            if result['success']:
                processed += 1
                logger.info(f"[OK] Finished processing {pdf_file.name}")
            else:
                failed += 1
                logger.error(f"[FAILED] Error in {pdf_file.name}: {result.get('error')}")
        
        return {
            'success': failed == 0,
            'processed': processed,
            'failed': failed,
            'total': len(pdf_files),
            'results': results,
            'message': f"Processed {processed}/{len(pdf_files)} PDFs successfully"
        }
    
    def list_pdfs(self, track: str = None) -> List[Dict[str, str]]:
        """List available PDFs for a track"""
        track = (track or self.track).lower()
        pdf_dir = Path(self.base_path) / self.TRACK_MAP[track]['pdf_dir']
        
        if not pdf_dir.exists():
            return []
        
        pdfs = []
        for pdf_file in pdf_dir.glob("*.pdf"):
            pdfs.append({
                'name': pdf_file.name,
                'path': str(pdf_file),
                'size': pdf_file.stat().st_size
            })
        
        return pdfs
    
    def list_json_files(self, track: str = None) -> List[Dict[str, str]]:
        """List generated JSON files for a track"""
        track = (track or self.track).lower()
        json_dir = Path(self.base_path) / self.TRACK_MAP[track]['json_dir']
        
        if not json_dir.exists():
            return []
        
        jsons = []
        for json_file in json_dir.glob("*.json"):
            jsons.append({
                'name': json_file.name,
                'path': str(json_file),
                'size': json_file.stat().st_size
            })
        
        return jsons


# Backward compatibility alias
PDFScraper = PDFScraperManager
