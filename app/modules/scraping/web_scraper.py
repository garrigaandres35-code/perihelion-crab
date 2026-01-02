"""
Web Scraper Module
ElTurf scraper using Playwright for authentication and API consumption
"""
import os
import sys
import json
import time
import logging
import requests
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.modules.scraping.scraping_config import ScrapingConfig

logger = logging.getLogger(__name__)


class ElTurfScraper:
    """
    Web scraper for elturf.com using Playwright for authentication
    and requests for API consumption
    """
    
    def __init__(self, fecha: str = None, hipodromo: str = None):
        """
        Initialize ElTurf Scraper
        
        Args:
            fecha: Date in YYYY-MM-DD format
            hipodromo: Track code (HCH, CHS, VSC)
        """
        self.base_url = ScrapingConfig.ELTURF_BASE_URL
        self.login_url = ScrapingConfig.ELTURF_LOGIN_URL
        self.username = ScrapingConfig.ELTURF_USUARIO
        self.password = ScrapingConfig.ELTURF_CLAVE
        
        self.fecha_reunion = fecha or ScrapingConfig.DIA_REUNION or datetime.now().strftime('%Y-%m-%d')
        self.hipodromo = hipodromo or ScrapingConfig.HIPODROMO or 'HCH'
        self.hipodromo_nombre = ScrapingConfig.get_hipodromo_set_value(self.hipodromo)
        self.hipodromo_codigo = self.hipodromo.lower()
        
        self.base_path = ScrapingConfig.PATH_WEB_SCRAPING
        self.cookies_file = ScrapingConfig.COOKIES_PATH
        
        self.headless = True  # Run in background by default
        self._cookies = None
        
    def has_credentials(self) -> bool:
        """Check if credentials are configured"""
        return bool(self.username and self.password)
    
    def login_and_get_cookies(self) -> Optional[Dict[str, str]]:
        """
        Perform login using Playwright and capture session cookies
        
        Returns:
            dict: Cookies dictionary or None if login failed
        """
        if not self.has_credentials():
            logger.error("Credentials not configured. Set ELTURF_USUARIO and ELTURF_CLAVE in .env")
            return None
        
        logger.info("Starting browser for authentication...")
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return None
        
        with sync_playwright() as p:
            # Launch browser with anti-bot options
            browser = p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            try:
                # 1. Go to Home
                logger.info("Navigating to Home...")
                page.goto(self.base_url, timeout=60000, wait_until='domcontentloaded')
                
                # 2. Go to Login
                logger.info("Looking for Login link...")
                
                try:
                    login_locator = page.locator('a', has_text=re.compile(r'Login|Ingresar', re.IGNORECASE)).first
                    login_locator.wait_for(state='visible', timeout=10000)
                    login_locator.scroll_into_view_if_needed()
                    login_locator.click()
                except Exception as e:
                    logger.warning(f"Could not click Login link: {e}")
                    logger.info("Attempting direct navigation to /login...")
                    page.goto(f"{self.base_url}/login")
                
                # 3. Fill login form
                logger.info("Entering credentials...")
                page.wait_for_selector('#form_contacto_usuario', state='visible')
                
                page.fill('#form_contacto_usuario', self.username)
                page.fill('#form_contacto_passwd2', self.password)
                
                page.click('#Elturf_Send_Form_Login2')
                
                # 4. Wait for authentication
                logger.info("Waiting for authentication...")
                
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                
                # 5. Capture cookies
                cookies = context.cookies()
                cookies_dict = {c['name']: c['value'] for c in cookies}
                
                if 'PHPSESSID' in cookies_dict:
                    logger.info("Login successful! Cookies captured.")
                    
                    # Save cookies
                    Path(self.cookies_file).parent.mkdir(parents=True, exist_ok=True)
                    with open(self.cookies_file, 'w') as f:
                        json.dump(cookies_dict, f, indent=2)
                    logger.info(f"Cookies saved to {self.cookies_file}")
                    
                    self._cookies = cookies_dict
                    return cookies_dict
                else:
                    logger.error("Session cookies not found. Login may have failed.")
                    return None
                    
            except Exception as e:
                logger.error(f"Error during login: {e}")
                return None
            finally:
                browser.close()
    
    def load_cached_cookies(self) -> Optional[Dict[str, str]]:
        """Load cookies from cache file if exists"""
        if Path(self.cookies_file).exists():
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    if 'PHPSESSID' in cookies:
                        self._cookies = cookies
                        return cookies
            except Exception:
                pass
        return None
    
    def get_cookies(self, force_login: bool = False) -> Optional[Dict[str, str]]:
        """Get cookies, attempting cached first unless force_login"""
        if not force_login and self._cookies:
            return self._cookies
        
        if not force_login:
            cookies = self.load_cached_cookies()
            if cookies:
                logger.info("Using cached cookies")
                return cookies
        
        return self.login_and_get_cookies()
    
    def _make_request(self, url: str, cookies: Dict[str, str], headers: Dict[str, str] = None) -> Tuple[requests.Response, Dict[str, str]]:
        """
        Make HTTP request with auto-retry on 401 Unauthorized
        Returns: (Response object, Updated cookies dict)
        """
        try:
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp, cookies
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("401 Unauthorized. Session expired. Relogging...")
                new_cookies = self.login_and_get_cookies()
                if new_cookies:
                    logger.info("Retrying request with new cookies...")
                    self._cookies = new_cookies
                    resp = requests.get(url, cookies=new_cookies, headers=headers, timeout=15)
                    resp.raise_for_status()
                    return resp, new_cookies
            raise e

    def _match_hipodromo(self, reunion: Dict) -> bool:
        """Check if reunion matches configured hipódromo"""
        nombre = (reunion.get('nombre_hipodromo') or '').strip().lower()
        abreviatura = (reunion.get('abreviatura_hipodromo') or '').strip().lower()
        
        if self.hipodromo_nombre and nombre == self.hipodromo_nombre:
            return True
        if self.hipodromo_codigo and abreviatura == self.hipodromo_codigo:
            return True
        return not self.hipodromo_nombre and not self.hipodromo_codigo
    
    def scrape_programas(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Scrape programs (programas) for configured date and hipódromo
        """
        cookies = cookies or self.get_cookies()
        if not cookies:
            return {'success': False, 'error': 'No session cookies available'}
        
        logger.info(f"Getting PROGRAMS for {self.fecha_reunion}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://elturf.com/'
        }
        
        try:
            url_prog = f"{self.base_url}/api/elturfhome/programas/reuniones/fecha/{self.fecha_reunion}"
            # Use _make_request to handle potential 401s
            resp, cookies = self._make_request(url_prog, cookies, headers)
            
            data_prog = resp.json()
            
            # Create directory
            programas_dir = Path(self.base_path) / "programas"
            programas_dir.mkdir(parents=True, exist_ok=True)
            
            reuniones = data_prog.get('reuniones', [])
            reuniones_filtradas = [r for r in reuniones if self._match_hipodromo(r)]
            
            if not reuniones_filtradas:
                return {
                    'success': False,
                    'error': 'No meetings found matching the configured hipódromo'
                }
            
            reunion = reuniones_filtradas[0]
            id_reunion = reunion.get('id_reunion')
            fecha_reunion = reunion.get('fecha_reunion')
            
            if not id_reunion or not fecha_reunion:
                return {'success': False, 'error': 'Meeting without ID or date'}
            
            # Save main program
            file_prog = programas_dir / f"programas_{id_reunion}_{self.fecha_reunion}.json"
            with open(file_prog, 'w', encoding='utf-8') as f:
                json.dump(reunion, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved program: {file_prog}")
            
            # Save race details
            detalles_dir = programas_dir / "detalles"
            detalles_dir.mkdir(parents=True, exist_ok=True)
            
            carreras = reunion.get('carreras', [])
            logger.info(f"Getting details for {len(carreras)} races...")
            
            races_saved = 0
            for i, carrera in enumerate(carreras, 1):
                id_carrera = carrera.get('id_carrera')
                if not id_carrera:
                    continue
                    
                try:
                    url_detalle = f"{self.base_url}/api/elturf/programa/{id_carrera}"
                    # Reuse updated cookies
                    resp_det, cookies = self._make_request(url_detalle, cookies, headers)
                    
                    detalle = resp_det.json()
                    
                    file_det = detalles_dir / f"carrera_{id_carrera}_{self.fecha_reunion}.json"
                    with open(file_det, 'w', encoding='utf-8') as f:
                        json.dump({"programa": carrera, "detalle": detalle}, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"[{i}/{len(carreras)}] Saved detail: {file_det}")
                    races_saved += 1
                except Exception as e:
                    logger.warning(f"[{i}/{len(carreras)}] Error getting race {id_carrera}: {e}")
            
            return {
                'success': True,
                'id_reunion': id_reunion,
                'fecha': fecha_reunion,
                'hipodromo': reunion.get('nombre_hipodromo'),
                'races_count': len(carreras),
                'races_saved': races_saved,
                'program_file': str(file_prog),
                'message': f"Program saved with {races_saved} race details"
            }
            
        except Exception as e:
            logger.error(f"Error getting programs: {e}")
            return {'success': False, 'error': str(e)}
    
    def scrape_resultados(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Scrape detailed results (Resultados Detalle) using the new scraper.
        Replaces the old legacy scraping process.
        """
        try:
            from app.modules.scraping.results_detail_scraper import ResultsDetailScraper
            
            logger.info(f"Starting Detailed Results Scraping for {self.hipodromo} on {self.fecha_reunion}...")
            
            # Instantiate the verified Detailed Scraper
            # Note: We rely on the scraper's own authentication/navigation rather than passing cookies 
            # because the new scraper manages its own browser context and sophisticated navigation navigation.
            detail_scraper = ResultsDetailScraper(fecha=self.fecha_reunion, hipodromo=self.hipodromo)
            
            # Execute scraping
            scrape_result = detail_scraper.scrape()
            
            if scrape_result.get('success'):
                # Data is already saved by detail_scraper.scrape()
                logger.info(f"Detailed Results Scraping Finished Successfully: {scrape_result.get('file')}")
                return {
                    'success': True,
                    'id_reunion': 'N/A', 
                    'fecha': self.fecha_reunion,
                    'hipodromo': self.hipodromo_nombre,
                    'races_count': scrape_result.get('count', 0),
                    'results_file': scrape_result.get('file'),
                    'message': f"Detailed results saved for {scrape_result.get('count', 0)} races"
                }
            else:
                return {
                    'success': False, 
                    'error': scrape_result.get('error', 'No races extracted or scrape failed')
                }
            
        except Exception as e:
            logger.error(f"Error getting detailed results: {e}")
            return {'success': False, 'error': str(e)}


# Backward compatibility alias
WebScraper = ElTurfScraper
