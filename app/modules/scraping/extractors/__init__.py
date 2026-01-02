"""
PDF Extractors Package
"""
from app.modules.scraping.extractors.base import BaseScraper
from app.modules.scraping.extractors.hch import HCHScraper
from app.modules.scraping.extractors.chs import CHSScraper
from app.modules.scraping.extractors.vsc import VSCScraper

__all__ = ['BaseScraper', 'HCHScraper', 'CHSScraper', 'VSCScraper']
