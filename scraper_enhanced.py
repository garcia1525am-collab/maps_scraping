import time
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import os
import uuid
from datetime import datetime
from database_manager import DatabaseManager, LocalPersistence
import threading
import signal
import sys

class GoogleMapsScraperEnhanced:
    def __init__(self, auto_save=True, mysql_config=None, session_id=None):
        """Inicializa el scraper con capacidades mejoradas de persistencia"""
        self.driver = None
        self.wait = None
        self.auto_save = auto_save
        self.session_id = session_id or str(uuid.uuid4())[:8]
        
        # Sistema de persistencia
        self.db_manager = None
        self.local_persistence = LocalPersistence()
        self.extracted_businesses = []
        self.search_history = []
        
        # Configurar base de datos si está disponible
        if mysql_config:
            self.db_manager = DatabaseManager(**mysql_config)
            if self.db_manager.connect():
                self.db_manager.create_tables()
                print(f"✅ Sistema de base de datos MySQL activo")
            else:
                print("⚠️ MySQL no disponible, usando solo persistencia local")
                self.db_manager = None
        
        # Timer para auto-guardado periódico
        self.auto_save_timer = None
        if self.auto_save:
            self._start_auto_save_timer()
        
        self.setup_driver()
    
    def _signal_handler(self, signum, frame):
        """Maneja interrupciones del sistema para guardar datos"""
        print(f"\n🚨 Interrupción detectada (señal {signum})")
        print("💾 Guardando datos antes de cerrar...")
        
        self._save_current_session()
        self.close()
        
        print("✅ Datos guardados. Cerrando aplicación...")
        sys.exit(0)
    
    def _start_auto_save_timer(self):
        """Inicia timer para auto-guardado cada 2 minutos"""
        def auto_save():
            if self.extracted_businesses:
                print("🔄 Auto-guardado ejecutándose...")
                self._save_current_session()
            
            # Programar siguiente auto-guardado
            self.auto_save_timer = threading.Timer(120.0, auto_save)  # 2 minutos
            self.auto_save_timer.daemon = True
            self.auto_save_timer.start()
        
        self.auto_save_timer = threading.Timer(120.0, auto_save)
        self.auto_save_timer.daemon = True
        self.auto_save_timer.start()
        print("⏰ Auto-guardado activado (cada 2 minutos)")
    
    def _save_current_session(self):
        """Guarda la sesión actual en MySQL y localmente"""
        if not self.extracted_businesses and not self.search_history:
            return
        
        session_data = {
            'session_id': self.session_id,
            'extracted_businesses': self.extracted_businesses,
            'search_history': self.search_history,
            'timestamp': datetime.now().isoformat(),
            'total_businesses': len(self.extracted_businesses)
        }
        
        # Guardar en MySQL si está disponible
        if self.db_manager:
            try:
                # Guardar negocios en lotes si hay muchos nuevos
                new_businesses = [b for b in self.extracted_businesses if not b.get('saved_to_db', False)]
                if new_businesses:
                    saved_count = self.db_manager.save_businesses_batch(new_businesses)
                    # Marcar como guardados
                    for business in new_businesses:
                        business['saved_to_db'] = True
                    print(f"💾 {saved_count} negocios nuevos guardados en MySQL")
                
                # Guardar respaldo de sesión
                self.db_manager.save_session_backup(self.session_id, session_data)
                
                # Guardar historial de búsquedas nuevas
                new_searches = [s for s in self.search_history if not s.get('saved_to_db', False)]
                for search in new_searches:
                    self.db_manager.save_search_history(search)
                    search['saved_to_db'] = True
                
            except Exception as e:
                print(f"⚠️ Error guardando en MySQL: {e}")
        
        # Guardar localmente como respaldo
        self.local_persistence.save_session(session_data, self.session_id)
        
        # Guardar CSV de respaldo
        if self.extracted_businesses:
            self.local_persistence.save_csv_backup(
                self.extracted_businesses, 
                f"autosave_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

    def load_previous_session(self, session_id=None):
        """Carga una sesión anterior"""
        target_session_id = session_id or self.session_id
        
        # Intentar cargar desde MySQL primero
        if self.db_manager:
            backup = self.db_manager.get_latest_session_backup(target_session_id)
            if backup:
                session_data = backup['datos']
                self.extracted_businesses = session_data.get('extracted_businesses', [])
                self.search_history = session_data.get('search_history', [])
                print(f"📂 Sesión {target_session_id} cargada desde MySQL")
                print(f"   📊 {len(self.extracted_businesses)} negocios recuperados")
                return True
        
        # Intentar cargar localmente
        session_data = self.local_persistence.load_latest_session(target_session_id)
        if session_data:
            self.extracted_businesses = session_data.get('extracted_businesses', [])
            self.search_history = session_data.get('search_history', [])
            print(f"📂 Sesión {target_session_id} cargada desde archivos locales")
            print(f"   📊 {len(self.extracted_businesses)} negocios recuperados")
            return True
        
        print(f"ℹ️ No se encontraron datos previos para la sesión {target_session_id}")
        return False

    def setup_driver(self):
        """Configura el navegador Chrome con undetected_chromedriver"""
        options = uc.ChromeOptions()
        
        # Configuraciones estables
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-default-apps")
        
        # User-Agent más realista
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            print("✅ Configurando Undetected ChromeDriver...")
            
            # Crear directorio temporal para datos del usuario
            temp_user_data = os.path.join(os.getcwd(), f"temp_chrome_profile_{self.session_id}")
            options.add_argument(f"--user-data-dir={temp_user_data}")
            
            self.driver = uc.Chrome(
                options=options,
                version_main=None,
                driver_executable_path=None,
                use_subprocess=False
            )
            
            self.wait = WebDriverWait(self.driver, 25)
            print("✅ Chrome iniciado correctamente")
            
        except Exception as e:
            print(f"❌ Error configurando Undetected ChromeDriver: {e}")
            print("\n🔄 Intentando configuración alternativa...")
            try:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--headless")
                
                self.driver = uc.Chrome(options=options)
                self.wait = WebDriverWait(self.driver, 25)
                print("✅ Chrome iniciado en modo alternativo")
                
            except Exception as e2:
                print(f"❌ Error en configuración alternativa: {e2}")
                raise

    def scroll_and_load_results(self, max_results=10):
        """Hace scroll inteligente para cargar más resultados de Google Maps"""
        print(f"🔄 Cargando hasta {max_results} resultados...")
        
        # Esperar un momento inicial para que cargue la página
        time.sleep(3)
        
        # Buscar el panel de resultados con selectores más específicos
        results_panel_selectors = [
            "div[role='main']",
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",  # Panel lateral de resultados
            "div.Nv2PK.THOPZb",
            "div[data-value='Search results']",
            ".m6QErb",
            "[role='main'] [role='feed']"
        ]
        
        results_panel = None
        for selector in results_panel_selectors:
            try:
                results_panel = self.driver.find_element(By.CSS_SELECTOR, selector)
                if results_panel and results_panel.is_displayed():
                    print(f"✅ Panel de resultados encontrado: {selector}")
                    break
            except:
                continue
        
        unique_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 20
        no_new_results_count = 0
        
        while len(unique_urls) < max_results and scroll_attempts < max_scroll_attempts:
            scroll_attempts += 1
            
            # Obtener enlaces actuales antes del scroll
            current_links = self.get_current_business_links()
            previous_count = len(unique_urls)
            
            # Agregar nuevos enlaces únicos
            for link in current_links:
                if len(unique_urls) >= max_results:
                    break
                if link and '/maps/place/' in link:
                    unique_urls.add(link)
            
            current_count = len(unique_urls)
            print(f"   📊 Intento {scroll_attempts}: {current_count} resultados únicos encontrados")
            
            # Auto-guardado cada 10 resultados nuevos
            if self.auto_save and current_count > 0 and current_count % 10 == 0:
                print("🔄 Auto-guardado intermedio...")
                self._save_current_session()
            
            # Verificar si encontramos nuevos resultados
            if current_count == previous_count:
                no_new_results_count += 1
            else:
                no_new_results_count = 0
            
            # Si llevamos varios intentos sin nuevos resultados, salir
            if no_new_results_count >= 5:
                print(f"⚠️ No se encontraron nuevos resultados en los últimos {no_new_results_count} intentos")
                break
                
            if current_count >= max_results:
                print(f"✅ ¡Objetivo alcanzado! {current_count} resultados encontrados")
                break
            
            # Estrategias múltiples de scroll (igual que antes)
            try:
                if results_panel:
                    # Método 1: Scroll en el panel de resultados
                    self.driver.execute_script("""
                        arguments[0].scrollBy(0, 800);
                        arguments[0].scrollTop = arguments[0].scrollTop;
                    """, results_panel)
                    
                    # Método 2: Scroll hasta el último elemento visible
                    try:
                        last_result = results_panel.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
                        if last_result:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", last_result[-1])
                    except:
                        pass
                        
                else:
                    # Scroll en toda la página si no encontramos el panel
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                
                # Métodos adicionales de scroll (similares al original)
                if scroll_attempts % 3 == 0:
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.PAGE_DOWN).perform()
                    time.sleep(1)
                    actions.send_keys(Keys.END).perform()
                        
            except Exception as e:
                print(f"   ⚠️ Error en scroll {scroll_attempts}: {e}")
            
            # Esperar a que se carguen nuevos resultados
            time.sleep(2.5)
        
        print(f"🏁 Scroll completado: {len(unique_urls)} resultados únicos disponibles")
        return list(unique_urls)

    def get_current_business_links(self):
        """Obtiene todos los enlaces de negocios visibles actualmente"""
        business_links = []
        
        # Selectores más específicos y completos
        selectors = [
            "a[href*='/maps/place/'][data-value]",
            "a[href*='/maps/place/']",
            "a[data-result-index]",
            ".hfpxzc",
            "a[jsaction*='navigate']",
            "div[role='article'] a[href*='place']",
            ".Nv2PK a[href*='place']",
            "[role='main'] a[href*='/maps/place/']",
            ".THOPZb a[href*='/maps/place/']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        if href and '/maps/place/' in href and href not in business_links:
                            if element.is_displayed():
                                business_links.append(href)
                    except:
                        continue
            except Exception as e:
                continue
        
        # Eliminar duplicados manteniendo el orden
        unique_links = []
        seen = set()
        for link in business_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links

    def search_businesses(self, url, max_results=10, search_name="busqueda"):
        """Busca y extrae información de negocios en Google Maps con auto-guardado"""
        start_time = time.time()
        print(f"🔍 Accediendo a: {url}")
        
        if "google.com/maps" not in url and "maps.google.com" not in url:
            print("❌ La URL no parece ser una búsqueda válida de Google Maps")
            return []
        
        try:
            self.driver.get(url)
            print("⏳ Esperando que cargue la página de resultados...")
            
            # Esperar a que aparezcan los primeros resultados
            time.sleep(5)
            
            # Intentar cerrar cualquier popup
            try:
                close_buttons = [
                    "button[aria-label*='close']",
                    "button[aria-label*='dismiss']", 
                    "button[data-value='Accept']",
                    ".VfPpkd-Bz112c-LgbsSe"
                ]
                for selector in close_buttons:
                    try:
                        button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if button.is_displayed():
                            button.click()
                            time.sleep(1)
                            break
                    except:
                        continue
            except:
                pass
            
            # Verificar resultados básicos
            initial_selectors = [
                "a[href*='/maps/place/']",
                "div[role='article']",
                ".Nv2PK"
            ]
            
            found_results = False
            for selector in initial_selectors:
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    found_results = True
                    print(f"✅ Resultados iniciales encontrados con: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not found_results:
                print("❌ No se encontraron resultados iniciales")
                return []
            
            # Scroll automático mejorado
            unique_urls = self.scroll_and_load_results(max_results)
            
            if not unique_urls:
                print("❌ No se pudieron obtener URLs de negocios")
                return []
            
            print(f"✅ Se encontraron {len(unique_urls)} negocios únicos para procesar")
            
            # Limitar a la cantidad solicitada
            urls_to_process = unique_urls[:max_results]
            
            businesses_data = []
            for i, business_url in enumerate(urls_to_process):
                print(f"\n🔍 Procesando negocio {i+1}/{len(urls_to_process)}...")
                data = self.extract_business_data(business_url, i)
                if data:
                    # Agregar metadatos
                    data['busqueda'] = search_name
                    data['fecha_extraccion'] = datetime.now()
                    data['url_google_maps'] = business_url
                    data['session_id'] = self.session_id
                    
                    businesses_data.append(data)
                    self.extracted_businesses.append(data)
                    
                    # Auto-guardado cada 5 negocios
                    if self.auto_save and len(businesses_data) % 5 == 0:
                        print(f"💾 Auto-guardado: {len(businesses_data)} negocios procesados")
                        self._save_current_session()
                
                # Pausa entre solicitudes
                time.sleep(2)
            
            # Guardar historial de búsqueda
            end_time = time.time()
            search_record = {
                'busqueda': search_name,
                'url': url,
                'resultados': len(businesses_data),
                'fecha': datetime.now(),
                'duracion_segundos': int(end_time - start_time),
                'parametros': {
                    'max_results': max_results,
                    'session_id': self.session_id
                }
            }
            self.search_history.append(search_record)
            
            # Guardado final
            if self.auto_save:
                print("💾 Guardado final de la búsqueda...")
                self._save_current_session()
            
            return businesses_data
            
        except Exception as e:
            print(f"❌ Error durante la búsqueda: {e}")
            # Intentar guardar datos parciales en caso de error
            if self.auto_save and self.extracted_businesses:
                print("💾 Guardando datos parciales debido al error...")
                self._save_current_session()
            return []

    def extract_business_data(self, url, index):
        """Navega a la página de un negocio y extrae toda su información"""
        business_data = {
            'indice': index, 
            'nombre': 'No disponible', 
            'calificacion': 'No disponible', 
            'num_reviews': 'No disponible', 
            'tipo': 'No disponible', 
            'direccion': 'No disponible', 
            'telefono': 'No disponible', 
            'website': 'No disponible', 
            'email': 'No disponible'
        }
        
        try:
            print(f"   🚗 Navegando a la página del negocio...")
            self.driver.get(url)
            
            # Espera más flexible para diferentes elementos
            selectors_to_wait = [
                "h1.DUwDvf",
                "h1[data-attrid='title']",
                ".x3AX1-LfntMc-header-title-title"
            ]
            
            title_element = None
            for selector in selectors_to_wait:
                try:
                    title_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not title_element:
                print("   ❌ No se pudo cargar la página del negocio")
                return None
                
            print("   ✅ Página de detalles cargada.")

            # Extracción de datos con múltiples selectores de respaldo
            try:
                name_selectors = ["h1.DUwDvf", "h1[data-attrid='title']", ".x3AX1-LfntMc-header-title-title"]
                for selector in name_selectors:
                    try:
                        business_data['nombre'] = self.driver.find_element(By.CSS_SELECTOR, selector).text
                        break
                    except:
                        continue
            except: 
                pass
                
            try:
                rating_selectors = ["div.F7nice", ".MW4etd", ".ceNzKf"]
                for selector in rating_selectors:
                    try:
                        rating_text = self.driver.find_element(By.CSS_SELECTOR, selector).text
                        parts = rating_text.split('(')
                        if len(parts) > 0: 
                            business_data['calificacion'] = parts[0].strip()
                        if len(parts) > 1: 
                            business_data['num_reviews'] = parts[1].replace(')', '').strip()
                        break
                    except:
                        continue
            except: 
                pass
                
            try:
                type_selectors = ["button.DkEaL", ".YhemCb"]
                for selector in type_selectors:
                    try:
                        business_data['tipo'] = self.driver.find_element(By.CSS_SELECTOR, selector).text
                        break
                    except:
                        continue
            except: 
                pass
                
            try:
                address_selectors = [
                    "button[data-item-id='address']",
                    "[data-item-id='address'] .Io6YTe",
                    ".LrzXr"
                ]
                for selector in address_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        address = element.get_attribute('aria-label') or element.text
                        business_data['direccion'] = address.replace('Dirección:', '').strip()
                        break
                    except:
                        continue
            except: 
                pass
                
            try:
                phone_selectors = [
                    "button[data-item-id^='phone:tel:']",
                    "[data-item-id*='phone'] .Io6YTe"
                ]
                for selector in phone_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        phone = element.get_attribute('aria-label') or element.text
                        business_data['telefono'] = phone.replace('Teléfono:', '').strip()
                        break
                    except:
                        continue
            except: 
                pass
                
            try:
                website_selectors = [
                    "a[data-item-id='authority']",
                    "a[href^='http']:not([href*='google.com'])"
                ]
                for selector in website_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        business_data['website'] = element.get_attribute('href')
                        break
                    except:
                        continue
            except: 
                pass
            
            print(f"   ✅ Extraído: {business_data['nombre']}")
            return business_data

        except TimeoutException:
            print("   ❌ La página del negocio no cargó a tiempo")
            return None
        except Exception as e:
            print(f"   ⚠️ Error inesperado extrayendo datos: {e}")
            return None

    def get_session_summary(self):
        """Obtiene resumen de la sesión actual"""
        return {
            'session_id': self.session_id,
            'total_businesses': len(self.extracted_businesses),
            'total_searches': len(self.search_history),
            'last_activity': datetime.now().isoformat() if self.extracted_businesses else None,
            'searches': [s['busqueda'] for s in self.search_history]
        }

    def export_session_data(self, format='csv', filename=None):
        """Exporta todos los datos de la sesión"""
        if not self.extracted_businesses:
            print("❌ No hay datos para exportar")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{self.session_id}_{timestamp}"
        
        if format.lower() == 'csv':
            filepath = f"{filename}.csv"
            df = pd.DataFrame(self.extracted_businesses)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"📊 Datos exportados a {filepath}")
            return filepath
        
        return None

    def save_to_csv(self, businesses, filename='negocios_extraidos.csv'):
        """Método de compatibilidad con el scraper original"""
        if not businesses:
            print("❌ No hay datos para guardar")
            return
        
        df = pd.DataFrame(businesses)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 Datos guardados en {filename}")
        print(f"📊 Total de negocios extraídos: {len(businesses)}")
        
        # Mostrar resumen de datos extraídos
        print("\n📋 Resumen de extracción:")
        for col in df.columns:
            no_disponible = (df[col] == 'No disponible').sum()
            disponible = len(df) - no_disponible
            print(f"  {col}: {disponible}/{len(df)} disponibles")
    
    def close(self):
        """Cierra el navegador y limpia recursos"""
        # Cancelar timer de auto-guardado
        if self.auto_save_timer:
            self.auto_save_timer.cancel()
        
        # Guardado final
        if self.auto_save and (self.extracted_businesses or self.search_history):
            print("💾 Guardado final antes de cerrar...")
            self._save_current_session()
        
        # Cerrar navegador
        if self.driver:
            self.driver.quit()
            print("\n🔒 Navegador cerrado")
        
        # Cerrar conexión a base de datos
        if self.db_manager:
            self.db_manager.close()
        
        # Limpiar directorio temporal
        temp_user_data = os.path.join(os.getcwd(), f"temp_chrome_profile_{self.session_id}")
        try:
            if os.path.exists(temp_user_data):
                import shutil
                shutil.rmtree(temp_user_data, ignore_errors=True)
        except:
            pass
        
        print(f"✅ Sesión {self.session_id} cerrada correctamente")


def main():
    print("🚀 Google Maps Business Scraper MEJORADO con Persistencia")
    print("="*70)
    
    # Configuración MySQL (opcional)
    mysql_config = None
    use_mysql = input("¿Usar base de datos MySQL? (s/n): ").strip().lower()
    
    if use_mysql in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n⚙️ Configuración MySQL:")
        host = input("Host (localhost): ").strip() or "localhost"
        database = input("Base de datos (google_maps_scraper): ").strip() or "google_maps_scraper"
        user = input("Usuario (root): ").strip() or "root"
        password = input("Contraseña: ").strip()
        
        mysql_config = {
            'host': host,
            'database': database,
            'user': user,
            'password': password
        }
    
    # Crear scraper
    scraper = None
    session_id = input("\nID de sesión (Enter para nuevo): ").strip() or None
    
    try:
        scraper = GoogleMapsScraperEnhanced(
            auto_save=True,
            mysql_config=mysql_config,
            session_id=session_id
        )
        
        # Intentar cargar sesión anterior
        if session_id:
            scraper.load_previous_session()
        
        # Mostrar resumen de sesión
        summary = scraper.get_session_summary()
        print(f"\n📊 SESIÓN ACTUAL: {summary['session_id']}")
        print(f"   Negocios: {summary['total_businesses']}")
        print(f"   Búsquedas: {summary['total_searches']}")
        
        all_businesses = scraper.extracted_businesses.copy()
        search_count = len(scraper.search_history)
        
        while True:
            search_count += 1
            print(f"\n🔍 BÚSQUEDA #{search_count}")
            print("-" * 30)
            
            # Solicitar URL
            url = input("🌐 URL de búsqueda de Google Maps (o 'salir'): ").strip()
            
            if url.lower() in ['salir', 'exit', 'quit', 's', '']:
                break
            
            if "google.com/maps" not in url and "maps.google.com" not in url:
                print("❌ URL no válida")
                continue
            
            # Parámetros de búsqueda
            try:
                max_results = int(input("📊 ¿Cuántos negocios extraer? (10): ") or "10")
            except:
                max_results = 10
            
            search_name = input("🏷️ Nombre para esta búsqueda: ").strip()
            if not search_name:
                search_name = f"busqueda_{search_count}"
            
            print(f"\n⚡ Procesando búsqueda: {search_name}")
            print("="*60)
            
            # Realizar búsqueda
            businesses = scraper.search_businesses(url, max_results=max_results, search_name=search_name)
            
            if businesses:
                print(f"✅ Búsqueda '{search_name}' completada: {len(businesses)} negocios")
            else:
                print(f"❌ No se obtuvieron resultados para '{search_name}'")
            
            # Resumen actual
            current_summary = scraper.get_session_summary()
            print(f"\n📈 RESUMEN ACTUAL:")
            print(f"   • Total negocios: {current_summary['total_businesses']}")
            print(f"   • Total búsquedas: {current_summary['total_searches']}")
            
            # Preguntar si continuar
            continuar = input(f"\n🔄 ¿Hacer otra búsqueda? (s/n): ").strip().lower()
            if continuar not in ['s', 'si', 'sí', 'y', 'yes']:
                break
        
        # Exportar datos finales
        if scraper.extracted_businesses:
            print(f"\n💾 EXPORTANDO DATOS FINALES...")
            
            # CSV consolidado
            filepath = scraper.export_session_data('csv')
            
            # Mostrar resumen final
            final_summary = scraper.get_session_summary()
            print(f"\n📊 RESUMEN FINAL:")
            print(f"   • Sesión: {final_summary['session_id']}")
            print(f"   • Total negocios: {final_summary['total_businesses']}")
            print(f"   • Total búsquedas: {final_summary['total_searches']}")
            print(f"   • Archivo CSV: {filepath}")
            
            if mysql_config:
                print(f"   • Datos también guardados en MySQL")
                
        else:
            print("\n❌ No se obtuvieron datos.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
    
    finally:
        if scraper:
            scraper.close()
        print(f"\n✅ ¡Todos los datos han sido guardados automáticamente!")
        print("💡 Puedes recuperar tu sesión la próxima vez usando el mismo ID")

if __name__ == "__main__":
    main()