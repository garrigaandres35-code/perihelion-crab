"""
Scraping Modules Package
"""
from app.modules.scraping.web_scraper import ElTurfScraper, WebScraper
from app.modules.scraping.pdf_scraper import PDFScraperManager, PDFScraper
from app.modules.scraping.scraping_config import ScrapingConfig

__all__ = [
    'ElTurfScraper', 
    'WebScraper', 
    'PDFScraperManager', 
    'PDFScraper',
    'ScrapingConfig'
]
