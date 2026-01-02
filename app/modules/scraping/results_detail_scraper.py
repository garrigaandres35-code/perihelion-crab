import logging
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.modules.scraping.scraping_config import ScrapingConfig
from app.modules.scraping.web_scraper import ElTurfScraper  # Reusing Login logic

logger = logging.getLogger(__name__)

class ResultsDetailScraper(ElTurfScraper):
    """
    Scraper para 'Resultados Detalle' que navega vía UI y extrae información 
    directamente del HTML de todos los participantes de cada carrera.
    """

    def __init__(self, fecha: str = None, hipodromo: str = None):
        super().__init__(fecha, hipodromo)
        # self.fecha_reunion and self.hipodromo are set in super().__init__

    def scrape(self) -> Dict[str, Any]:
        """
        Ejecuta el proceso de scraping de detalle via UI.
        """
        logger.info(f"Iniciando Scraping Resultados Detalle para {self.hipodromo} - {self.fecha_reunion}")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # 1. Launch Browser
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(
                    viewport={'width': 1366, 'height': 768},
                     user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()

                # 3. Autenticación (Login si es necesario en la misma ventana)
                if not self.ensure_authenticated(page):
                     return {'success': False, 'error': "Fallo en la autenticación UI"}

                # 4. Navigate to Meeting
                if not self.navigate_to_meeting(page):
                     return {'success': False, 'error': "No se pudo navegar a la reunión o no se encontraron resultados"}

                # 4. Extraction of all races
                resultados = self.extract_all_races(page)
                
                if resultados and resultados['carreras']:
                    file_path = self.save_results(resultados)
                    return {
                        'success': True, 
                        'count': len(resultados['carreras']), 
                        'file': file_path,
                        'data': resultados
                    }
                else:
                    return {'success': False, 'error': "No se pudieron extraer los resultados de las carreras"}

        except Exception as e:
            logger.error(f"Error en scraping detalle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    def ensure_authenticated(self, page) -> bool:
        """
        Verifica si está logueado, de lo contrario realiza el login en la misma página.
        """
        try:
            # Primero intentar cargar cookies del caché si existen
            cookies = self.load_cached_cookies()
            if cookies:
                try:
                    formatted_cookies = []
                    for k, v in cookies.items():
                        formatted_cookies.append({
                            'name': k, 'value': v, 'url': self.base_url
                        })
                    page.context.add_cookies(formatted_cookies)
                    logger.info("Cookies de caché inyectadas.")
                except Exception as ce:
                    logger.warning(f"No se pudieron inyectar cookies de caché: {ce}")

            # Navegar a home para verificar login
            logger.info(f"Navegando a {self.base_url} para verificar estado de sesión...")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    page.goto(self.base_url, timeout=90000, wait_until='domcontentloaded')
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Timeout cargando home (intento {attempt+1}/{max_retries}). Reintentando...")
                        time.sleep(5)
                    else:
                        raise e
            time.sleep(2)
            
            # Verificar si ya está logueado usando múltiples indicadores
            def check_session():
                return (
                    page.locator('a[data-target="#modal_cerrar_session"]').count() > 0 or
                    page.locator('a[href="perfil"]').count() > 0 or
                    page.locator('a:has-text("RP")').count() > 0 or
                    page.locator('a:has-text("Salir")').count() > 0
                )

            is_logged_in = check_session()
            
            if not is_logged_in:
                logger.info("Estado: NO LOGUEADO (UI). Iniciando automatización de credenciales...")
                
                # Ir a login explícitamente
                logger.info(f"Navegando a {self.base_url}/login")
                page.goto(f"{self.base_url}/login", timeout=60000, wait_until='networkidle')
                page.bring_to_front() # Para que el usuario lo vea
                
                # Esperar campos con más paciencia
                logger.info("Esperando campos de login (#form_contacto_usuario)...")
                page.wait_for_selector('#form_contacto_usuario', state='visible', timeout=20000)
                time.sleep(1) # Pausa breve para que el usuario vea la página
                
                # Llenar credenciales con simulación de teclado
                logger.info(f"Ingresando credenciales para: {self.username}")
                page.locator('#form_contacto_usuario').click()
                page.keyboard.press('Control+A')
                page.keyboard.press('Backspace')
                page.type('#form_contacto_usuario', self.username, delay=100)
                
                page.locator('#form_contacto_passwd2').click()
                page.keyboard.press('Control+A')
                page.keyboard.press('Backspace')
                page.type('#form_contacto_passwd2', self.password, delay=100)
                
                # Click en Entrar
                logger.info("Enviando formulario (Login)...")
                page.click('#Elturf_Send_Form_Login2')
                
                # Esperar un tiempo prudente para la redirección
                logger.info("Esperando respuesta del servidor...")
                time.sleep(6) 
                
                if check_session():
                    logger.info("✓ Login exitoso detectado mediante indicadores UI.")
                    # Asegurar estabilidad de la sesión
                    time.sleep(10)
                    # Guardar nuevas cookies 
                    new_cookies = page.context.cookies()
                    cookies_dict = {c['name']: c['value'] for c in new_cookies}
                    if 'PHPSESSID' in cookies_dict:
                        self.save_cookies_locally(cookies_dict)
                    return True
                else:
                    logger.error("No se detectó el inicio de sesión tras el envío de credenciales.")
                    page.screenshot(path=str(Path(self.base_path) / "debug_login_failed.png"))
                    return False
            
            logger.info("✓ Ya se encuentra autenticado.")
            return True

        except Exception as e:
            logger.error(f"Error crítico en ensure_authenticated: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def save_cookies_locally(self, cookies_dict):
        try:
            Path(self.cookies_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies_dict, f, indent=2)
        except:
            pass

    def navigate_to_meeting(self, page) -> bool:
        """
        Navega a la página de Resultados y selecciona fecha/hipódromo via UI.
        """
        try:
            # Ir a pagina de Resultados directamente
            url_res = f"{ScrapingConfig.ELTURF_BASE_URL}/carreras-ultimos-resultados"
            logger.info(f"Navegando a {url_res}...")
            
            # Intentar navegar con un timeout más largo y manejando errores
            try:
                page.goto(url_res, timeout=90000, wait_until='networkidle')
            except Exception as e:
                logger.warning(f"Error en goto inicial: {e}. Reintentando con domcontentloaded...")
                page.goto(url_res, timeout=60000, wait_until='domcontentloaded')
            
            # Debug: URL actual y contenido
            logger.info(f"URL actual: {page.url}")
            if "login" in page.url:
                logger.warning("Redirigido a login. Las cookies no funcionaron o expiraron.")
                # Aquí podriamos llamar a un login manual vía UI si fuera necesario

            # Parsear fecha objetivo
            target_date = datetime.strptime(self.fecha_reunion, '%Y-%m-%d')
            target_dia = str(target_date.day)
            target_mes = str(target_date.month)
            target_ano = str(target_date.year)
            # --- ZONA DE CALENDARIO AVANZADO ---
            # SE ENVÍA DIRECTO AL CALENDARIO AVANZADO para asegurar Año/Mes correctos.
            logger.info(f"Iniciando navegación por Calendario Avanzado para {self.fecha_reunion}...")
            
            try:
                # A. Abrir el calendario
                logger.info("Buscando trigger del calendario (.vdp-datepicker input)...")
                cal_trigger = page.locator('.vdp-datepicker input, .fa-calendar-alt').first
                if cal_trigger.count() > 0:
                    logger.info("Trigger encontrado. Intentando abrir widget...")
                    try:
                        cal_trigger.click(force=True)
                    except Exception as e:
                        logger.warning(f"Click estándar falló ({e}), intentando vía JS...")
                        page.evaluate("document.querySelector('.vdp-datepicker input').click()")
                        
                    time.sleep(1) # Esperar animación de apertura
                else:
                    logger.error("ELEMENTO CALENDARIO NO ENCONTRADO (selector .vdp-datepicker input)")
                    page.screenshot(path="debug_no_calendar_trigger.png")
                    raise Exception("Elemento calendario no encontrado")
                    
                # B. Navegación Jerárquica: AÑO -> MES -> DÍA
                # Implementamos un bucle de "Ascenso" para encontrar el Año deseado.
                
                found_year = False
                for _ in range(3): # Max 3 intentos de subir nivel
                    # 1. ¿Está visible el año objetivo?
                    year_cell = page.locator(f'.vdp-datepicker__calendar .cell.year:visible').filter(has_text=re.compile(fr'^\s*{target_ano}\s*$')).first
                    if year_cell.count() > 0:
                        logger.info(f"Año {target_ano} visible. Seleccionando...")
                        year_cell.click(force=True)
                        found_year = True
                        time.sleep(0.5)
                        break
                    
                    # 2. Si no, ¿está visible el header para subir?
                    header_up = page.locator('.vdp-datepicker__calendar header span.up:visible').first
                    if header_up.count() > 0:
                        # Chequear si el header mismo dice el año (ej: "2025") -> estamos en meses
                        # Si dice "Dic 2025" -> estamos en días
                        logger.info(f"Subiendo nivel de calendario (Header: {header_up.inner_text()})...")
                        header_up.click(force=True)
                        time.sleep(0.5)
                    else:
                        logger.warning("Header calendar no visible, no se puede subir nivel.")
                        break
                
                if not found_year:
                    logger.warning(f"No se pudo clickear explícitamente el año {target_ano}. Intentando seguir con Mes...")

                # C. Seleccionar MES
                # Aumentamos espera tras selección de año
                time.sleep(1.0)
                
                meses_map = {
                    '1': 'Ene', '2': 'Feb', '3': 'Mar', '4': 'Abr', '5': 'May', '6': 'Jun',
                    '7': 'Jul', '8': 'Ago', '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
                }
                mes_key = str(int(target_mes))
                mes_abbr = meses_map.get(mes_key, str(target_mes))
                
                # Regex flexible: "Dic", "Diciembre", "Dec", "December"
                # Se construye dinámicamente para incluir el abbr y posibles variantes comunes si es necesario
                # Simplemente usamos startswith para cubrir "Dic" y "Diciembre"
                pattern_mes = re.compile(fr'^\s*{mes_abbr}.*', re.IGNORECASE)
                
                month_cell = page.locator(f'.vdp-datepicker__calendar .cell.month:visible').filter(has_text=pattern_mes).first
                
                if month_cell.count() > 0:
                    logger.info(f"Seleccionando Mes {mes_abbr} (match)...")
                    month_cell.click(force=True)
                    time.sleep(1.0)
                else:
                    logger.warning(f"Mes {mes_abbr} no visible por texto. Intentando fallback por índice...")
                    # Fallback: intentar por índice numérico (0-11)
                    try:
                        idx = int(target_mes) - 1
                        month_by_idx = page.locator(f'.vdp-datepicker__calendar .cell.month:visible').nth(idx)
                        if month_by_idx.count() > 0:
                            logger.info(f"Seleccionando Mes por índice {idx}...")
                            month_by_idx.click(force=True)
                            time.sleep(1.0)
                    except:
                        pass

                # D. Seleccionar DÍA
                # Regex simple para número exacto
                pattern_dia = re.compile(fr'^\s*{target_dia}\s*$', re.IGNORECASE)
                day_cell = page.locator(f'.vdp-datepicker__calendar .cell.day:not(.blank):not(.muted):visible').filter(has_text=pattern_dia).first
                
                if day_cell.count() > 0:
                    logger.info(f"Seleccionando Día {target_dia}...")
                    day_cell.click(force=True)
                    time.sleep(4) # Esperar carga de hipódromos crítica
                else:
                    logger.error(f"No se encontró el día {target_dia} (visible) en el calendario.")
                    
            except Exception as e_cal:
                logger.error(f"Fallo en navegación de calendario avanzado: {e_cal}")

            # 3. Esperar y Seleccionar HIPÓDROMO (Dinámico tras fecha)
            try:
                # Esperar a que el select se popule (o aparezca)
                logger.info("Esperando carga de lista de hipódromos...")
                hipodromo_select = page.locator('select.form-control').filter(has_text=re.compile(r"Seleccione|Hipódromo|Valparaíso|Club", re.IGNORECASE)).first
                if not hipodromo_select.is_visible(timeout=5000):
                    logger.info("Dropdown de hipódromos no detectado inmediatamente, esperando un poco más...")
                    time.sleep(2)

                if hipodromo_select.count() > 0:
                    # wait for options - Aumentado por reporte de latencia (~3s)
                    time.sleep(5)
                    
                    # DEBUG: Listar opciones encontradas
                    try:
                        options_texts = hipodromo_select.evaluate("select => Array.from(select.options).map(o => o.text)")
                        logger.info(f"Opciones de hipódromo detectadas en el dropdown: {options_texts}")
                    except Exception as e_opt:
                        logger.warning(f"No se pudieron listar las opciones: {e_opt}")
                    
                    # Intentar seleccionar inteligentemente con JS para manejar variantes de texto
                    try:
                        hipodromo_select.evaluate(r"""(select, target) => {
                            const options = Array.from(select.options);
                            // 1. Intentar MATCH EXACTO (Case Sensitive) - Prioridad Usuario
                            let found = options.find(opt => opt.text.trim() === target);
                            
                            if (!found) {
                                // 2. Fallback: Normalización y mapeo (si el exacto falla)
                                let clean_target = target.toLowerCase();
                                
                                if (clean_target.includes('vsc')) clean_target = 'valparaiso';
                                if (clean_target.includes('chs')) clean_target = 'club hípico';
                                if (clean_target.includes('hch') || clean_target.includes('hipodromo') || clean_target.includes('chile')) clean_target = 'hipódromo chile';
                                
                                found = options.find(opt => {
                                    let txt = opt.text.trim().toLowerCase();
                                    return txt.includes(clean_target);
                                });
                            }
                            
                            if (found) {
                                select.value = found.value;
                                select.dispatchEvent(new Event('change'));
                            }
                        }""", self.hipodromo_nombre.lower())
                    except Exception as e_js:
                        logger.warning(f"Error seleccionando hipódromo dinámico: {e_js}")
                    
                    # Ensure selection with Playwright standard method if possible, in case JS didn't fully work or as backup
                    try:
                        hipodromo_select.select_option(label=re.compile(self.hipodromo_nombre, re.IGNORECASE))
                    except:
                        pass
                else:
                    logger.warning(f"Hipódromo '{self.hipodromo_nombre}' no hallado en dropdown (Selector no visible).")

            except Exception as e_hip:
                logger.warning(f"Error seleccionando hipódromo dinámico: {e_hip}")

            # Botón buscar (fallback)
            btn_buscar = page.locator('button:has-text("Actualizar"), input[value="Consultar"]').first
            if btn_buscar.is_visible():
                btn_buscar.click()
            
            # Esperar que la página cargue los resultados (manejar el "Cargando...")
            logger.info("Esperando que finalice la carga de resultados...")
            time.sleep(2)
            try:
                loading = page.locator('text=/Cargando/')
                if loading.count() > 0:
                    loading.wait_for(state='hidden', timeout=30000)
            except:
                pass
            
            page.wait_for_load_state('networkidle', timeout=15000)
            logger.info(f"Página tras carga: '{page.title()}'")
            page.screenshot(path=str(Path(self.base_path) / "debug_after_date_selection.png"))
            
            # 2. Verificar si ya llegamos a la reunión
            def is_at_results():
                # Varios indicadores de estar en una página de resultados
                try:
                    return (
                        page.locator('h1:has-text("Reunión"), h1:has-text("Reunion")').count() > 0 or
                        page.locator(".titulo_reunion").count() > 0 or
                        page.locator("table.elturf_padding_tablas").count() > 0
                    )
                except:
                    return False

            if is_at_results():
                logger.info("✓ Redirección automática a la reunión detectada.")
                header_text = page.locator('h1, .titulo_reunion').first.inner_text().lower()
                if self.hipodromo_nombre.lower() in header_text or self.hipodromo.lower() in header_text:
                    logger.info(f"✓ Confirmado: estamos en {self.hipodromo_nombre}")
                    return True
                elif "elturf" in header_text or "carreras" in header_text:
                    # Generic header found (common case), but structure was confirmed by is_at_results()
                    logger.info(f"✓ Estructura de resultados detectada. Encabezado genérico: '{header_text}' - Continuando.")
                    return True
                else:
                    logger.warning(f"Estamos en una reunión pero el encabezado '{header_text}' no coincide con '{self.hipodromo_nombre}'")

            # 3. Verificar si hay múltiples reuniones e hipódromo
            logger.info("Buscando selector de hipódromos o enlaces de reuniones...")
            meeting_selected = page.evaluate(f"""(targetHipName) => {{
                const selects = Array.from(document.querySelectorAll('select'));
                // Buscar el select que contenga opciones relacionadas con Hipódromos
                const hipSelect = selects.find(s => {{
                    if (s.options.length === 0) return false;
                    const firstOpt = s.options[0].innerText.toLowerCase();
                    return firstOpt.includes('hipódromo') || firstOpt.includes('reunión') || firstOpt.includes('seleccione');
                }});
                
                if (hipSelect) {{
                    const option = Array.from(hipSelect.options).find(o => 
                        o.innerText.toLowerCase().includes(targetHipName.toLowerCase())
                    );
                    if (option) {{
                        hipSelect.value = option.value;
                        hipSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            }}""", self.hipodromo_nombre)

            if meeting_selected:
                logger.info(f"Hipódromo '{self.hipodromo_nombre}' seleccionado del dropdown.")
                time.sleep(4)
                page.wait_for_load_state('networkidle')
                page.screenshot(path=str(Path(self.base_path) / "debug_after_hip_selection.png"))
            else:
                # Si no hay dropdown, buscar enlaces directos
                logger.info(f"No hay selector, buscando enlace directo para '{self.hipodromo_nombre}'...")
                # Intentar variantes
                search_terms = [self.hipodromo_nombre, self.hipodromo]
                if 'Valparaíso' in self.hipodromo_nombre: search_terms.extend(['Valparaiso', 'Sporting'])
                
                link_found = False
                for term in search_terms:
                    link = page.locator(f"a:has-text('{term}')").first
                    if link.count() > 0:
                        logger.info(f"Haciendo click en enlace encontrado con '{term}'")
                        link.click()
                        page.wait_for_load_state('networkidle')
                        time.sleep(3)
                        link_found = True
                        break
                
                if not link_found:
                    logger.warning("No se encontró dropdown ni enlace para el hipódromo.")

            # 4. Verificar que llegamos a la página de resultados
            if is_at_results():
                logger.info("✓ Llegamos a la página de la reunión satisfactoriamente.")
                return True
            
            logger.warning("No se detectó el encabezado de reunión tras todos los intentos. Tomando screenshot final.")
            page.screenshot(path=str(Path(self.base_path) / "debug_after_all_navigation.png"))
            return False

        except Exception as e:
            logger.error(f"Error navegando: {e}")
            return False

    def extract_all_races(self, page) -> Dict:
        """
        Itera por cada carrera y extrae los resultados completos.
        """
        results = {
            "hipodromo": self.hipodromo,
            "hipodromo_nombre": self.hipodromo_nombre,
            "fecha": self.fecha_reunion,
            "carreras": []
        }

        # 1. Identificar todos los enlaces de "Resultado" en la tabla principal
        # Buscamos enlaces que contengan "Resultado" y sean visibles, usualmente son los de la tabla.
        all_links = page.locator('a').filter(has_text="Resultado").all()
        resultado_links = [l for l in all_links if l.is_visible()]
        
        if not resultado_links:
            logger.warning("No se encontraron enlaces de 'Resultado' visibles. Intentando buscar botones de carrera directos...")
            # Fallback a botones de carrera directos
            # MODIFICADO: Regex más flexible para aceptar "1", "1ª", "1°"
            race_regex = re.compile(r'^\d+(?:ª|°)?$')
            race_buttons = page.locator('a.btn-primary, a.btn-danger, a.btn-default').filter(has_text=race_regex).all()
        else:
            logger.info(f"Se detectaron {len(resultado_links)} enlaces de 'Resultado' visibles.")
            # Entramos a la primera carrera para activar el modo "detalle"
            resultado_links[0].scroll_into_view_if_needed()
            resultado_links[0].click(force=True)
            time.sleep(4)
            # Ahora buscamos los botones de navegación que aparecen arriba
            race_regex = re.compile(r'^\d+(?:ª|°)?$')

        # === NUEVA LÓGICA: Navegación por Dropdown ===
        # Buscamos el SELECT de carreras
        logger.info("Buscando SELECT de carreras...")
        
        race_select_locator = page.locator('select.form-control')
        target_select = None
        
        count = race_select_locator.count()
        for i in range(count):
            sel = race_select_locator.nth(i)
            # Check options specifically
            opts_text = sel.inner_text()
            if "1ª" in opts_text and "2ª" in opts_text: 
                target_select = sel
                break
        
        if not target_select:
             logger.error("No se encontró el SELECT de carreras (buscando '1ª' y '2ª' en opciones).")
             return results

        # Extraer opciones válidas
        # Usamos JS para sacar value y texto limpio
        options_data = target_select.evaluate("""(s) => {
            return Array.from(s.options).map(o => ({
                value: o.value,
                text: o.innerText.trim()
            })).filter(o => o.value && o.text.match(/^\d+/) ); 
        }""")
        
        logger.info(f"Se encontraron {len(options_data)} carreras en el dropdown.")
        
        for opt in options_data:
            val = opt['value']
            txt = opt['text']
            
            # Extraer número de carrera
            race_num_match = re.search(r'^(\d+)', txt)
            race_num = race_num_match.group(1) if race_num_match else val
            
            logger.info(f"--- Procesando Carrera {race_num} ({txt}) ---")

            try:
                # 1. Asegurar que el select está disponible (por si hubo reload)
                current_select = None
                all_sel = page.locator('select.form-control').all()
                for s in all_sel:
                    if "1ª" in s.inner_text():
                        current_select = s
                        break
                
                if not current_select:
                     # Recovery: Si no hay select, ver si caímos en pantalla de error/volver
                     volver = page.locator('a.btn').filter(has_text="Volver").first
                     if volver.count() > 0:
                         logger.warning("Pantalla 'Volver' detectada prematuramente. Recuperando...")
                         volver.click()
                         time.sleep(3)
                         # Reintentar encontrar select
                         all_sel = page.locator('select.form-control').all()
                         for s in all_sel:
                             if "1ª" in s.inner_text():
                                 current_select = s
                                 break
                
                if current_select:
                    current_select.select_option(value=val)
                else:
                    logger.error(f"No se pudo encontrar el select de carreras para carrera {race_num}")
                    continue

                # 2. Esperar recarga
                time.sleep(3)
                page.wait_for_load_state('networkidle', timeout=5000)
                
            except Exception as e:
                logger.error(f"Error seleccionando carrera {race_num}: {e}")
                continue
                
            # 3. Extraer datos
            race_data = self.extract_results_from_page(page, race_num)
            if race_data:
                results['carreras'].append(race_data)
                logger.info(f"✓ Carrera {race_num} extraída con éxito.")
            else:
                logger.warning(f"✗ No se pudieron extraer datos para carrera {race_num}")
                
        logger.info(f"Extracción finalizada. Total carreras extraídas: {len(results['carreras'])}")
        return results

    def extract_results_from_page(self, page, race_num: str) -> Optional[Dict]:
        """
        Extrae los resultados de la carrera activa.
        """
        try:
            # 1. Extraer Encabezado de la Carrera (Premio, Distancia, Pista)
            # Buscamos en la tabla .elturf_padding_tablas que suele preceder a los resultados
            race_header = page.locator('table.elturf_padding_tablas').first
            
            premio = f"Carrera {race_num}"
            if race_header.count() > 0:
                header_text = race_header.inner_text()
                # Intentar extraer "Pr. NOMBRE"
                premio_match = re.search(r'Pr\.\s*([^(\n\r]*)', header_text)
                if premio_match:
                    premio = premio_match.group(1).strip()
            
            logger.info(f"Extrayendo Carrera {race_num}: {premio}")
            
            race_data = {
                "nro_carrera": race_num,
                "premio": premio,
                "resultados": []
            }

            # 2. Localizar la tabla de resultados detallada
            # Buscamos la tabla que contiene "Ejemplar (Padrillo)"
            # IMPORTANTE: Usamos un wait_for para dar tiempo a la carga AJAX
            try:
                page.wait_for_selector('table:has-text("Ejemplar (Padrillo)")', timeout=10000)
            except Exception as e:
                logger.warning(f"Timeout esperando tabla de resultados para carrera {race_num}. Verificando estado de la página...")
                
                # A. ¿Hay un prompt de "Si/No"?
                si_btn = page.locator('a.btn').filter(has_text=re.compile(r'^\s*Si\s*$', re.I)).first
                if si_btn.count() > 0:
                    logger.info("Detectado botón 'Si' (prompt). Clickando para ver resultados...")
                    si_btn.click()
                    time.sleep(3)
                    try:
                        page.wait_for_selector('table:has-text("Ejemplar (Padrillo)")', timeout=10000)
                    except:
                        pass
                
                # B. ¿Hay un botón 'Volver'?
                volver = page.locator('a.btn').filter(has_text="Volver").first
                if volver.count() > 0:
                    logger.info("Detectado botón 'Volver'. El sitio podría haber redirigido. Tomando screenshot...")
                    page.screenshot(path=str(Path(self.base_path) / f"debug_missing_table_{race_num}.png"))
                
            target_table = page.locator('table').filter(has_text="Ejemplar (Padrillo)").last
            
            if target_table.count() == 0:
                logger.warning(f"No se encontró la tabla de resultados para carrera {race_num}")
                return None

            # Iteramos todas las filas de esa tabla específica
            rows = target_table.locator('tr').all()
            
            for row in rows:
                cells = row.locator('td').all()
                if len(cells) < 8:
                    continue
                
                # Validar si es una fila de resultado mirando la primera celda (Lugar)
                first_cell_text = cells[0].inner_text().strip()
                
                # Limpiamos el texto para ver si es un número (ej: "1°" -> "1") o un estado (DEB, etc)
                lugar_clean = first_cell_text.replace('°', '').strip()
                
                is_valid_row = False
                if lugar_clean.isdigit():
                    is_valid_row = True
                elif lugar_clean in ['DEB', 'NTR', 'S/P', 'ROD', 'DNF']:
                    is_valid_row = True
                
                if not is_valid_row:
                    continue

                try:
                    # === Estandarización de 12 Columnas ===
                    # 1. Lugar, 2. Numero, 3. Ejemplar, 4. Padrillo, 
                    # 5. Edad, 6. Peso Ejemplar, 7. Distancia, 8. Peso Jinete,
                    # 9. Jinete, 10. Preparador, 11. Stud, 12. Dividendo
                    
                    lugar = lugar_clean
                    numero = cells[1].inner_text().strip()
                    ejemplar_raw = cells[2].inner_text().strip()
                    ejemplar = ejemplar_raw.split('(')[0].strip()
                    padrillo = ejemplar_raw.split('(')[1].replace(')', '').strip() if '(' in ejemplar_raw else ""
                    
                    # Inicializar campos opcionales
                    edad = ""
                    peso_ejemplar = ""
                    distancia = ""
                    peso_jinete = ""
                    jinete = ""
                    preparador = ""
                    stud = ""
                    dividendo = cells[-1].inner_text().strip()

                    # Lógica Diferenciada por Cantidad de Columnas
                    n_cols = len(cells)
                    
                    if n_cols >= 18: # HCH (20 columnas aprox)
                        # Heurística Confirmada:
                        # Index 6: Peso Jinete ("55k")
                        # Index 7: Jinete ("A. Vásquez")
                        # Index 8+: Tiempos/Splits (Por tanto Prep y Stud NO ESTÁN)
                        
                        # --- Heurística de Campos Flotantes (Cols 3-5) ---
                        # Buscamos Edad (2 chars), Peso Ej (3 chars > 400)
                        
                        # Reset iterators
                        found_cnt = 0
                        for i in range(3, 6):
                            txt = cells[i].inner_text().strip()
                            # Edad: 1 o 2 digitos
                            if not edad and txt.isdigit() and len(txt) <= 2:
                                edad = txt
                                continue
                            
                            # Peso Ejemplar: 3 digitos, > 400 (aprox)
                            if not peso_ejemplar and txt.isdigit() and len(txt) == 3 and int(txt) > 350:
                                peso_ejemplar = txt
                                continue
                                
                            # Distancia: Buscar "Cpos", "Cbz", "Pcz" o similar
                            # A veces la distancia está mezclada.
                            # Si no se encuentra patrón claro, se deja vacía.
                            upper_txt = txt.upper()
                            if not distancia and ("CPO" in upper_txt or "CBZ" in upper_txt or "PCZ" in upper_txt or "NRZ" in upper_txt or "VP" in upper_txt):
                                distancia = txt
                                continue

                        # --- Indices Fijos Confirmados ---
                        # Peso Jinete (Index 6)
                        if n_cols > 6:
                            txt_6 = cells[6].inner_text().strip()
                            if "k" in txt_6.lower() or txt_6.isdigit():
                                peso_jinete = txt_6
                        
                        # Jinete (Index 7)
                        if n_cols > 7:
                            jinete = cells[7].inner_text().strip()

                        # Preparador y Stud NO existen en esta tabla (Según confirmación usuario)
                        preparador = ""
                        stud = ""

                    else: # VSC / CHS (11-12 columnas estándar)
                        # VSC JSON: Pos, Num, Ej, Pad, Jin, Prep, Stud, Div.
                        # Indices usuales VSC: 0,1,2, (3,4,5 hidden?), 6,7,8?
                        # En VSC JSON anterior: Jinete (G. Rodriguez) estaba presente.
                        # Asumiremos mapeo estándar:
                        # 0:Pos, 1:Num, 2:Ej, 3:PesoJin, 4:Jinete, 5:Prep, 6:Stud, 7:Tpo, 8:Cpos, 9:Div (aprox)
                        
                        # Intentar extraer si existen
                        if n_cols > 3:
                            # Peso Jinete en col 3?
                             txt = cells[3].inner_text().strip()
                             if "k" in txt or txt.isdigit():
                                 peso_jinete = txt
                             # Si no es peso, quizas es Jinete?
                        
                        # Indices "seguros" para Jinete/Prep/Stud en layout clásico
                        if n_cols > 6:
                            jinete = cells[n_cols-5].inner_text().strip() # Antepenultimos
                            preparador = cells[n_cols-4].inner_text().strip()
                            stud = cells[n_cols-3].inner_text().strip()
                            # Ajuste: Div es -1. Stud -2? Prep -3? Jin -4?
                            # Chequear VSC (11 cols): 0..10. Div=10.
                            # Stud=9? Prep=8? Jin=7?
                            # Usamos indices negativos para seguridad en VSC (que tiene menos varianza de splits)
                            stud = cells[-3].inner_text().strip() # Ante-penultimo (antes de Div y Cpos?)
                            preparador = cells[-4].inner_text().strip()
                            jinete = cells[-5].inner_text().strip()
                            
                            # Distancia (Cpos) suele ser -2 (antes de Div)
                            distancia = cells[-2].inner_text().strip()

                    race_data['resultados'].append({
                        "lugar": lugar,
                        "numero": numero,
                        "ejemplar": ejemplar,
                        "padrillo": padrillo,
                        "edad": edad,
                        "peso_ejemplar": peso_ejemplar,
                        "distancia": distancia,
                        "peso_jinete": peso_jinete,
                        "jinete": jinete,
                        "preparador": preparador,
                        "stud": stud,
                        "dividendo": dividendo
                    })
                except Exception as row_e:
                    logger.warning(f"Error procesando fila en carrera {race_num}: {row_e}")
                    continue

            return race_data if race_data['resultados'] else None
            
        except Exception as e:
            logger.error(f"Error extrayendo carrera {race_num}: {e}")
            return None

    def save_results(self, data: Dict) -> str:
        """Guarda en JSON y retorna la ruta del archivo"""
        filename = f"resultados_detalle_{self.hipodromo}_{self.fecha_reunion}.json"
        path = Path(self.base_path) / "resultados_detalle"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Guardado exitoso: {file_path}")
        return str(file_path)
