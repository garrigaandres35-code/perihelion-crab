"""
Base Scraper
Abstract base class for PDF extractors
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.modules.scraping.pdf_models import Meeting


class BaseScraper(ABC):
    """Abstract base class for PDF scrapers"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.text_content = ""
        
    @abstractmethod
    def extract_meeting(self) -> Meeting:
        """
        Extract meeting data from PDF
        Must be implemented by subclasses
        
        Returns:
            Meeting: Extracted meeting data
        """
        pass
    
    def save_json(self, output_path: str, meeting: Optional[Meeting] = None) -> str:
        """
        Save meeting data to JSON file
        
        Args:
            output_path: Path for output JSON file
            meeting: Meeting data (if None, extracts first)
            
        Returns:
            str: Path to saved JSON file
        """
        if meeting is None:
            meeting = self.extract_meeting()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(meeting.to_dict(), f, ensure_ascii=False, indent=2)
        
        return str(output_path)
    
    def get_output_filename(self, meeting: Meeting) -> str:
        """
        Generate standard output filename
        
        Args:
            meeting: Extracted meeting data
            
        Returns:
            str: Filename in format volante_{nro_reunion}_{fecha}.json
        """
        return f"volante_{meeting.nro_reunion}_{meeting.fecha}.json"
