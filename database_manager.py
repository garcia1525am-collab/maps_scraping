import mysql.connector
from mysql.connector import Error
import json
import pandas as pd
from datetime import datetime
import os
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, host='localhost', database='google_maps_scraper', user='root', password=''):
        """Inicializa el gestor de base de datos"""
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        
    def connect(self):
        """Establece conexión con MySQL"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            if self.connection.is_connected():
                print(f"✅ Conectado a MySQL database: {self.database}")
                return True
                
        except Error as e:
            print(f"❌ Error conectando a MySQL: {e}")
            # Intentar crear la base de datos si no existe
            if "Unknown database" in str(e):
                return self._create_database()
            return False
    
    def _create_database(self):
        """Crea la base de datos si no existe"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            connection.close()
            
            print(f"✅ Base de datos '{self.database}' creada")
            return self.connect()
            
        except Error as e:
            print(f"❌ Error creando base de datos: {e}")
            return False
    
    def create_tables(self):
        """Crea las tablas necesarias"""
        if not self.connection or not self.connection.is_connected():
            return False
            
        try:
            cursor = self.connection.cursor()
            
            # Tabla para negocios
            create_businesses_table = """
            CREATE TABLE IF NOT EXISTS negocios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                calificacion DECIMAL(3,2) DEFAULT NULL,
                num_reviews VARCHAR(100) DEFAULT NULL,
                tipo VARCHAR(255) DEFAULT NULL,
                direccion TEXT DEFAULT NULL,
                telefono VARCHAR(50) DEFAULT NULL,
                website TEXT DEFAULT NULL,
                email VARCHAR(255) DEFAULT NULL,
                busqueda VARCHAR(255) NOT NULL,
                fecha_extraccion DATETIME NOT NULL,
                indice_original INT DEFAULT NULL,
                url_google_maps TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_busqueda (busqueda),
                INDEX idx_fecha_extraccion (fecha_extraccion),
                INDEX idx_nombre (nombre),
                INDEX idx_calificacion (calificacion)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            # Tabla para historial de búsquedas
            create_searches_table = """
            CREATE TABLE IF NOT EXISTS historial_busquedas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                busqueda VARCHAR(255) NOT NULL,
                url TEXT NOT NULL,
                resultados INT NOT NULL,
                fecha DATETIME NOT NULL,
                parametros JSON DEFAULT NULL,
                duracion_segundos INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_busqueda (busqueda),
                INDEX idx_fecha (fecha)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            # Tabla para respaldos automáticos
            create_backups_table = """
            CREATE TABLE IF NOT EXISTS respaldos_sesion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                datos JSON NOT NULL,
                timestamp DATETIME NOT NULL,
                tipo_respaldo ENUM('auto', 'manual') DEFAULT 'auto',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_businesses_table)
            cursor.execute(create_searches_table)
            cursor.execute(create_backups_table)
            
            self.connection.commit()
            print("✅ Tablas creadas exitosamente")
            return True
            
        except Error as e:
            print(f"❌ Error creando tablas: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def save_business(self, business_data: Dict[str, Any]) -> bool:
        """Guarda un negocio en la base de datos"""
        if not self.connection or not self.connection.is_connected():
            return False
            
        try:
            cursor = self.connection.cursor()
            
            # Convertir calificación a decimal si es posible
            calificacion = None
            try:
                if business_data.get('calificacion') != 'No disponible':
                    calificacion = float(business_data.get('calificacion', 0))
            except (ValueError, TypeError):
                calificacion = None
            
            insert_query = """
            INSERT INTO negocios 
            (nombre, calificacion, num_reviews, tipo, direccion, telefono, website, email, 
             busqueda, fecha_extraccion, indice_original, url_google_maps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                business_data.get('nombre', 'No disponible'),
                calificacion,
                business_data.get('num_reviews', 'No disponible'),
                business_data.get('tipo', 'No disponible'),
                business_data.get('direccion', 'No disponible'),
                business_data.get('telefono', 'No disponible'),
                business_data.get('website', 'No disponible'),
                business_data.get('email', 'No disponible'),
                business_data.get('busqueda', 'sin_nombre'),
                business_data.get('fecha_extraccion', datetime.now()),
                business_data.get('indice', 0),
                business_data.get('url_google_maps', '')
            )
            
            cursor.execute(insert_query, values)
            self.connection.commit()
            return True
            
        except Error as e:
            print(f"❌ Error guardando negocio: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def save_businesses_batch(self, businesses_list: List[Dict[str, Any]]) -> int:
        """Guarda múltiples negocios de forma eficiente"""
        if not self.connection or not self.connection.is_connected():
            return 0
            
        saved_count = 0
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO negocios 
            (nombre, calificacion, num_reviews, tipo, direccion, telefono, website, email, 
             busqueda, fecha_extraccion, indice_original, url_google_maps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_values = []
            for business in businesses_list:
                # Convertir calificación
                calificacion = None
                try:
                    if business.get('calificacion') != 'No disponible':
                        calificacion = float(business.get('calificacion', 0))
                except (ValueError, TypeError):
                    calificacion = None
                
                values = (
                    business.get('nombre', 'No disponible'),
                    calificacion,
                    business.get('num_reviews', 'No disponible'),
                    business.get('tipo', 'No disponible'),
                    business.get('direccion', 'No disponible'),
                    business.get('telefono', 'No disponible'),
                    business.get('website', 'No disponible'),
                    business.get('email', 'No disponible'),
                    business.get('busqueda', 'sin_nombre'),
                    business.get('fecha_extraccion', datetime.now()),
                    business.get('indice', 0),
                    business.get('url_google_maps', '')
                )
                batch_values.append(values)
            
            cursor.executemany(insert_query, batch_values)
            self.connection.commit()
            saved_count = cursor.rowcount
            
            print(f"✅ {saved_count} negocios guardados en MySQL")
            return saved_count
            
        except Error as e:
            print(f"❌ Error guardando lote de negocios: {e}")
            return 0
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def save_search_history(self, search_data: Dict[str, Any]) -> bool:
        """Guarda el historial de búsqueda"""
        if not self.connection or not self.connection.is_connected():
            return False
            
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO historial_busquedas 
            (busqueda, url, resultados, fecha, parametros, duracion_segundos)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            values = (
                search_data.get('busqueda', ''),
                search_data.get('url', ''),
                search_data.get('resultados', 0),
                search_data.get('fecha', datetime.now()),
                json.dumps(search_data.get('parametros', {})),
                search_data.get('duracion_segundos', 0)
            )
            
            cursor.execute(insert_query, values)
            self.connection.commit()
            return True
            
        except Error as e:
            print(f"❌ Error guardando historial: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def save_session_backup(self, session_id: str, session_data: Dict[str, Any], backup_type: str = 'auto') -> bool:
        """Guarda respaldo de la sesión"""
        if not self.connection or not self.connection.is_connected():
            return False
            
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO respaldos_sesion 
            (session_id, datos, timestamp, tipo_respaldo)
            VALUES (%s, %s, %s, %s)
            """
            
            values = (
                session_id,
                json.dumps(session_data, default=str, ensure_ascii=False),
                datetime.now(),
                backup_type
            )
            
            cursor.execute(insert_query, values)
            self.connection.commit()
            return True
            
        except Error as e:
            print(f"❌ Error guardando respaldo: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def get_businesses(self, search_name: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera negocios de la base de datos"""
        if not self.connection or not self.connection.is_connected():
            return []
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if search_name:
                query = "SELECT * FROM negocios WHERE busqueda = %s ORDER BY fecha_extraccion DESC"
                params = (search_name,)
            else:
                query = "SELECT * FROM negocios ORDER BY fecha_extraccion DESC"
                params = ()
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            return results
            
        except Error as e:
            print(f"❌ Error obteniendo negocios: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def get_latest_session_backup(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recupera el último respaldo de sesión"""
        if not self.connection or not self.connection.is_connected():
            return None
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            query = """
            SELECT * FROM respaldos_sesion 
            WHERE session_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
            """
            
            cursor.execute(query, (session_id,))
            result = cursor.fetchone()
            
            if result:
                result['datos'] = json.loads(result['datos'])
                return result
            
            return None
            
        except Error as e:
            print(f"❌ Error recuperando respaldo: {e}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """Obtiene el historial de búsquedas"""
        if not self.connection or not self.connection.is_connected():
            return []
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            query = "SELECT * FROM historial_busquedas ORDER BY fecha DESC"
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Parse JSON parameters
            for result in results:
                if result.get('parametros'):
                    result['parametros'] = json.loads(result['parametros'])
            
            return results
            
        except Error as e:
            print(f"❌ Error obteniendo historial: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def cleanup_old_backups(self, days: int = 7):
        """Limpia respaldos antiguos"""
        if not self.connection or not self.connection.is_connected():
            return False
            
        try:
            cursor = self.connection.cursor()
            
            query = """
            DELETE FROM respaldos_sesion 
            WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            
            cursor.execute(query, (days,))
            deleted_count = cursor.rowcount
            self.connection.commit()
            
            if deleted_count > 0:
                print(f"🗑️ {deleted_count} respaldos antiguos eliminados")
            
            return True
            
        except Error as e:
            print(f"❌ Error limpiando respaldos: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def export_to_csv(self, filename: str, search_name: Optional[str] = None) -> bool:
        """Exporta datos de MySQL a CSV"""
        businesses = self.get_businesses(search_name)
        
        if not businesses:
            print("❌ No hay datos para exportar")
            return False
        
        try:
            df = pd.DataFrame(businesses)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ Datos exportados a {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error exportando CSV: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la base de datos"""
        if not self.connection or not self.connection.is_connected():
            return {}
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            stats = {}
            
            # Total de negocios
            cursor.execute("SELECT COUNT(*) as total FROM negocios")
            stats['total_negocios'] = cursor.fetchone()['total']
            
            # Negocios por búsqueda
            cursor.execute("SELECT busqueda, COUNT(*) as count FROM negocios GROUP BY busqueda")
            stats['por_busqueda'] = cursor.fetchall()
            
            # Negocios con contacto
            cursor.execute("SELECT COUNT(*) as count FROM negocios WHERE telefono != 'No disponible'")
            stats['con_telefono'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM negocios WHERE website != 'No disponible'")
            stats['con_website'] = cursor.fetchone()['count']
            
            # Promedio de calificaciones
            cursor.execute("SELECT AVG(calificacion) as promedio FROM negocios WHERE calificacion IS NOT NULL")
            result = cursor.fetchone()
            stats['calificacion_promedio'] = result['promedio'] if result['promedio'] else 0
            
            return stats
            
        except Error as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return {}
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def close(self):
        """Cierra la conexión"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔒 Conexión MySQL cerrada")


# Funciones de utilidad para persistencia local
class LocalPersistence:
    """Manejo de persistencia local como respaldo"""
    
    def __init__(self, data_dir="session_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_session(self, session_data: Dict[str, Any], session_id: str = "default"):
        """Guarda sesión localmente"""
        filename = os.path.join(self.data_dir, f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"💾 Sesión guardada localmente: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error guardando sesión local: {e}")
            return None
    
    def load_latest_session(self, session_id: str = "default") -> Optional[Dict[str, Any]]:
        """Carga la sesión más reciente"""
        try:
            pattern = f"session_{session_id}_*.json"
            files = [f for f in os.listdir(self.data_dir) if f.startswith(f"session_{session_id}_")]
            
            if not files:
                return None
            
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(self.data_dir, x)))
            filepath = os.path.join(self.data_dir, latest_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📂 Sesión cargada desde: {filepath}")
            return data
            
        except Exception as e:
            print(f"❌ Error cargando sesión local: {e}")
            return None
    
    def save_csv_backup(self, businesses: List[Dict[str, Any]], filename: str = None):
        """Guarda respaldo CSV automático"""
        if not filename:
            filename = f"backup_negocios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            df = pd.DataFrame(businesses)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"📊 Respaldo CSV guardado: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")
            return None