#!/usr/bin/env python3
"""
Script de instalación y configuración para Google Maps Scraper PRO
Versión 3.0 con persistencia avanzada y MySQL
"""

import os
import sys
import subprocess
import mysql.connector
from mysql.connector import Error

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         Google Maps Business Scraper PRO - Setup            ║
    ║              Versión 3.0 con Persistencia Avanzada          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def install_dependencies():
    """Instala las dependencias necesarias"""
    print("\n🔧 Instalando dependencias de Python...")
    
    requirements = [
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "plotly>=5.15.0",
        "selenium>=4.15.0",
        "undetected-chromedriver>=3.5.0",
        "mysql-connector-python>=8.1.0"
    ]
    
    for req in requirements:
        try:
            print(f"   📦 Instalando {req}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error instalando {req}: {e}")
            return False
    
    print("✅ Todas las dependencias instaladas correctamente")
    return True

def test_mysql_connection():
    """Prueba la conexión con MySQL"""
    print("\n🗄️ Configuración de MySQL (Opcional)")
    print("   Si no tienes MySQL, el sistema usará solo almacenamiento local")
    
    use_mysql = input("¿Deseas configurar MySQL? (s/n): ").strip().lower()
    
    if use_mysql not in ['s', 'si', 'sí', 'y', 'yes']:
        print("ℹ️ Saltando configuración de MySQL. Se usará solo almacenamiento local.")
        return None
    
    print("\n📋 Ingresa los datos de conexión MySQL:")
    host = input("Host (localhost): ").strip() or "localhost"
    user = input("Usuario (root): ").strip() or "root"
    password = input("Contraseña: ").strip()
    database = input("Base de datos (google_maps_scraper): ").strip() or "google_maps_scraper"
    
    mysql_config = {
        'host': host,
        'user': user,
        'password': password,
        'database': database
    }
    
    print(f"\n🔍 Probando conexión a MySQL...")
    
    try:
        # Intentar conectar sin especificar la base de datos primero
        connection = mysql.connector.connect(
            host=mysql_config['host'],
            user=mysql_config['user'],
            password=mysql_config['password']
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Crear la base de datos si no existe
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Base de datos '{mysql_config['database']}' creada/verificada")
            
            cursor.close()
            connection.close()
            
            # Ahora conectar con la base de datos específica
            connection = mysql.connector.connect(**mysql_config)
            
            if connection.is_connected():
                print("✅ Conexión MySQL exitosa")
                
                # Crear tablas necesarias
                create_tables(connection)
                
                connection.close()
                return mysql_config
            
    except Error as e:
        print(f"❌ Error conectando a MySQL: {e}")
        print("💡 Verifica que MySQL esté ejecutándose y las credenciales sean correctas")
        print("💡 El sistema funcionará con almacenamiento local únicamente")
        return None
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def create_tables(connection):
    """Crea las tablas necesarias en MySQL"""
    print("📊 Creando tablas en MySQL...")
    
    try:
        cursor = connection.cursor()
        
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
        
        connection.commit()
        cursor.close()
        
        print("✅ Tablas creadas exitosamente en MySQL")
        return True
        
    except Error as e:
        print(f"❌ Error creando tablas: {e}")
        return False

def create_config_file(mysql_config):
    """Crea archivo de configuración"""
    print("\n📁 Creando archivo de configuración...")
    
    config = {
        'mysql_config': mysql_config,
        'auto_save_enabled': True,
        'default_max_results': 15,
        'auto_save_interval_seconds': 120,
        'data_directory': 'session_data'
    }
    
    try:
        import json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False, default=str)
        
        print("✅ Archivo config.json creado")
        return True
        
    except Exception as e:
        print(f"❌ Error creando configuración: {e}")
        return False

def create_directories():
    """Crea directorios necesarios"""
    print("\n📂 Creando directorios necesarios...")
    
    directories = [
        'session_data',
        'exports',
        'logs',
        'temp_chrome_profiles'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"   📁 {directory}/")
        except Exception as e:
            print(f"   ❌ Error creando {directory}: {e}")
            return False
    
    print("✅ Directorios creados exitosamente")
    return True

def check_chrome():
    """Verifica que Chrome esté instalado"""
    print("\n🌐 Verificando instalación de Chrome...")
    
    try:
        import undetected_chromedriver as uc
        
        # Intentar crear una instancia temporal
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = uc.Chrome(options=options)
        driver.quit()
        
        print("✅ Chrome y ChromeDriver funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"⚠️ Problema con Chrome/ChromeDriver: {e}")
        print("💡 El scraper intentará descargar ChromeDriver automáticamente")
        return True  # Continuar de todas formas

def create_run_scripts():
    """Crea scripts de ejecución"""
    print("\n📝 Creando scripts de ejecución...")
    
    # Script para Streamlit
    streamlit_script = """#!/bin/bash
# Script para ejecutar la interfaz Streamlit
echo "🚀 Iniciando Google Maps Scraper PRO - Interfaz Web"
echo "📱 La aplicación se abrirá en tu navegador web"
echo "🔗 URL local: http://localhost:8501"
echo ""

streamlit run streamlit_app_enhanced.py --theme.base="light" --theme.primaryColor="#667eea"
"""
    
    # Script para línea de comandos
    cli_script = """#!/bin/bash
# Script para ejecutar el scraper en línea de comandos
echo "🖥️ Iniciando Google Maps Scraper PRO - Línea de Comandos"
echo ""

python scraper_enhanced.py
"""
    
    try:
        with open('run_streamlit.sh', 'w') as f:
            f.write(streamlit_script)
        os.chmod('run_streamlit.sh', 0o755)
        
        with open('run_cli.sh', 'w') as f:
            f.write(cli_script)
        os.chmod('run_cli.sh', 0o755)
        
        # Scripts para Windows
        with open('run_streamlit.bat', 'w') as f:
            f.write("@echo off\necho Iniciando interfaz web...\nstreamlit run streamlit_app_enhanced.py\npause\n")
        
        with open('run_cli.bat', 'w') as f:
            f.write("@echo off\necho Iniciando scraper CLI...\npython scraper_enhanced.py\npause\n")
        
        print("✅ Scripts de ejecución creados:")
        print("   📱 run_streamlit.sh/.bat - Interfaz web")
        print("   🖥️ run_cli.sh/.bat - Línea de comandos")
        return True
        
    except Exception as e:
        print(f"❌ Error creando scripts: {e}")
        return False

def show_usage_instructions():
    """Muestra las instrucciones de uso"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    INSTALACIÓN COMPLETADA                   ║
    ╚══════════════════════════════════════════════════════════════╝
    
    🎉 ¡El sistema ha sido configurado exitosamente!
    
    📋 FORMAS DE EJECUTAR EL SCRAPER:
    
    1️⃣ INTERFAZ WEB (Recomendado):
       • Linux/Mac: ./run_streamlit.sh
       • Windows: run_streamlit.bat
       • Manual: streamlit run streamlit_app_enhanced.py
    
    2️⃣ LÍNEA DE COMANDOS:
       • Linux/Mac: ./run_cli.sh  
       • Windows: run_cli.bat
       • Manual: python scraper_enhanced.py
    
    🔧 CARACTERÍSTICAS PRINCIPALES:
    
    ✅ Auto-guardado cada 5 negocios extraídos
    ✅ Respaldo automático cada 2 minutos
    ✅ Recuperación de sesiones por ID
    ✅ Almacenamiento local + MySQL (opcional)
    ✅ Manejo de interrupciones del sistema
    ✅ Exportación múltiple (CSV, por búsqueda, etc.)
    ✅ Interfaz web moderna e intuitiva
    
    🛡️ NUNCA MÁS PERDERÁS TUS DATOS
    
    📁 ARCHIVOS IMPORTANTES:
    
    • database_manager.py - Gestor de MySQL y persistencia
    • scraper_enhanced.py - Scraper con auto-guardado  
    • streamlit_app_enhanced.py - Interfaz web moderna
    • config.json - Configuración del sistema
    • session_data/ - Respaldos automáticos locales
    
    🔍 EJEMPLOS DE URLs VÁLIDAS:
    
    • Restaurantes: https://www.google.com/maps/search/restaurantes+cdmx/@19.4326,-99.1332,13z
    • Dentistas: https://www.google.com/maps/search/dentistas+cerca+de+mi/@lat,lng,15z
    • Hoteles: https://www.google.com/maps/search/hoteles+cancun/@21.1619,-86.8515,12z
    
    ⚠️ IMPORTANTE:
    
    • Usa el scraper responsablemente
    • Respeta los términos de servicio de Google
    • Haz pausas entre búsquedas grandes
    • Mantén actualizadas las dependencias
    
    🆘 SOPORTE Y PROBLEMAS:
    
    • Los datos se guardan automáticamente cada 5 negocios
    • Si se interrumpe el proceso, usa el mismo ID de sesión para continuar
    • Los respaldos locales están en session_data/
    • Para problemas con Chrome, reinstala undetected-chromedriver
    
    ¡Disfruta extrayendo datos de Google Maps sin preocuparte por perderlos!
    """)

def main():
    """Función principal del setup"""
    print_banner()
    
    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Tu versión: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    
    # Pasos de instalación
    steps = [
        ("Instalar dependencias", install_dependencies),
        ("Crear directorios", create_directories),
        ("Verificar Chrome", check_chrome),
        ("Configurar MySQL", test_mysql_connection),
        ("Crear scripts", create_run_scripts)
    ]
    
    mysql_config = None
    
    for step_name, step_function in steps:
        print(f"\n{'='*60}")
        print(f"📋 {step_name}")
        print('='*60)
        
        if step_function == test_mysql_connection:
            result = step_function()
            if result:
                mysql_config = result
                create_config_file(mysql_config)
        else:
            result = step_function()
            
        if result is False:
            print(f"\n❌ Falló el paso: {step_name}")
            print("💡 Revisa los errores anteriores e intenta de nuevo")
            return False
    
    # Mostrar instrucciones finales
    show_usage_instructions()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎊 ¡Setup completado exitosamente!")
            print("🚀 Ya puedes ejecutar el scraper usando los scripts creados")
        else:
            print("\n❌ Setup incompleto")
            print("💡 Revisa los errores y ejecuta de nuevo")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado durante el setup: {e}")
        print("💡 Contacta al soporte técnico")