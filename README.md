# Google Maps Business Scraper PRO v3.0

**Sistema avanzado de extracción de datos de negocios de Google Maps con persistencia automática y recuperación de sesiones**

## 🎯 Características Principales

### Nunca Más Pierdas Tus Datos
- **Auto-guardado inteligente**: Cada 5 negocios procesados
- **Respaldo automático**: Cada 2 minutos durante la extracción
- **Persistencia múltiple**: Local (JSON/CSV) + MySQL opcional
- **Recuperación de sesiones**: Continúa donde lo dejaste usando el ID de sesión
- **Manejo de interrupciones**: Guarda datos automáticamente si se cierra inesperadamente

### Extracción Avanzada
- **Scroll automático**: Carga resultados de forma inteligente
- **Múltiples selectores**: Máxima compatibilidad con cambios de Google Maps
- **Datos completos**: Nombre, calificación, reviews, teléfono, website, dirección, tipo
- **Búsquedas ilimitadas**: Acumula datos de múltiples búsquedas en la misma sesión

### Interfaz Moderna
- **Web app con Streamlit**: Interfaz visual e intuitiva
- **CLI tradicional**: Para usuarios que prefieren línea de comandos
- **Analytics en tiempo real**: Gráficos y estadísticas de los datos extraídos
- **Exportación múltiple**: CSV por criterios, búsquedas individuales, etc.

## 🚀 Instalación Rápida

### 1. Clona o descarga los archivos
```bash
# Clona el repositorio o descarga todos los archivos Python
# Asegúrate de tener todos estos archivos en la misma carpeta:
# - database_manager.py
# - scraper_enhanced.py  
# - streamlit_app_enhanced.py
# - setup.py
# - requirements.txt
```

### 2. Ejecuta la instalación automática
```bash
python setup.py
```

El script de setup automáticamente:
- Instala todas las dependencias necesarias
- Configura MySQL (opcional)
- Crea directorios necesarios
- Verifica Chrome/ChromeDriver
- Crea scripts de ejecución
- Configura el sistema de persistencia

### 3. Ejecuta el scraper

**Opción 1: Interfaz Web (Recomendada)**
```bash
# Linux/Mac
./run_streamlit.sh

# Windows
run_streamlit.bat

# Manual
streamlit run streamlit_app_enhanced.py
```

**Opción 2: Línea de Comandos**
```bash
# Linux/Mac
./run_cli.sh

# Windows  
run_cli.bat

# Manual
python scraper_enhanced.py
```

## 🗄️ Configuración de MySQL (Opcional)

MySQL proporciona persistencia avanzada pero no es obligatorio. Sin MySQL, el sistema usa almacenamiento local.

### Instalación de MySQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

**CentOS/RHEL:**
```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

**Windows:**
- Descarga MySQL Community Server desde mysql.com
- Ejecuta el instalador
- Configura usuario root con contraseña

**macOS:**
```bash
brew install mysql
brew services start mysql
```

### Configuración Inicial
```bash
# Configurar MySQL (solo primera vez)
sudo mysql_secure_installation

# Crear usuario (opcional)
mysql -u root -p
CREATE USER 'scraper_user'@'localhost' IDENTIFIED BY 'tu_password';
GRANT ALL PRIVILEGES ON google_maps_scraper.* TO 'scraper_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 📖 Guía de Uso

### 1. Preparación de URLs

Ve a Google Maps y realiza tu búsqueda:

**Ejemplos de búsquedas válidas:**
- `restaurantes mexicanos cdmx`
- `dentistas cerca de mi ubicación`
- `hoteles en cancún`
- `ferreterías zona norte`

**Copia la URL completa que aparece en tu navegador después de la búsqueda:**
```
https://www.google.com/maps/search/restaurantes+mexicanos+cdmx/@19.4326,-99.1332,13z/data=...
```

### 2. Usando la Interfaz Web

1. **Ejecuta**: `streamlit run streamlit_app_enhanced.py`
2. **Configura MySQL** (opcional) en el panel lateral
3. **Ingresa la URL** de tu búsqueda de Google Maps
4. **Nombra tu búsqueda**: Ej: "restaurantes_cdmx"
5. **Selecciona cantidad** de resultados (recomendado: 15-50)
6. **Inicia el scraping**

El sistema automáticamente:
- Guarda cada 5 negocios extraídos
- Crea respaldos cada 2 minutos  
- Genera un ID de sesión único
- Permite continuar si se interrumpe

### 3. Usando la Línea de Comandos

```bash
python scraper_enhanced.py
```

El scraper te preguntará:
- Si usar MySQL
- URL de búsqueda
- Cantidad de resultados
- Nombre de la búsqueda
- ID de sesión (para continuar una sesión anterior)

### 4. Recuperación de Sesiones

Si el proceso se interrumpe:

**En interfaz web:**
- Anota tu ID de sesión (se muestra en pantalla)
- Reinicia la aplicación
- En "Gestión de Sesiones" ingresa tu ID
- Click en "Cargar Sesión"

**En línea de comandos:**
- Ejecuta el scraper nuevamente
- Cuando pregunte por ID de sesión, ingresa el mismo ID anterior
- El sistema recuperará automáticamente tus datos

## 📊 Estructura de Datos

### Información Extraída por Negocio:
- **Nombre**: Nombre del negocio
- **Calificación**: Puntuación (1-5 estrellas)
- **Número de reviews**: Cantidad de reseñas
- **Tipo**: Categoría del negocio
- **Dirección**: Dirección física completa
- **Teléfono**: Número de contacto
- **Website**: Sitio web oficial
- **Email**: Correo electrónico (cuando disponible)
- **Fecha de extracción**: Cuándo se obtuvo el dato
- **Búsqueda**: A qué búsqueda pertenece
- **ID de sesión**: Identificador único de la sesión

### Archivos Generados:
- **`negocios_[nombre_busqueda].csv`**: Datos de una búsqueda específica
- **`session_[session_id]_[timestamp].csv`**: Datos completos de la sesión
- **`session_data/`**: Respaldos automáticos en JSON
- **`EMERGENCY_backup_*.csv`**: Respaldos de emergencia

## 🗄️ Base de Datos MySQL

### Tablas Creadas Automáticamente:

**`negocios`**: Almacena todos los negocios extraídos
```sql
- id (PK)
- nombre, calificacion, num_reviews, tipo
- direccion, telefono, website, email  
- busqueda, fecha_extraccion
- url_google_maps, session_id
- created_at, updated_at
```

**`historial_busquedas`**: Registro de todas las búsquedas realizadas
```sql
- id (PK)
- busqueda, url, resultados, fecha
- parametros (JSON), duracion_segundos
```

**`respaldos_sesion`**: Respaldos automáticos de sesiones
```sql
- id (PK) 
- session_id, datos (JSON), timestamp
- tipo_respaldo (auto/manual)
```

### Consultas Útiles:
```sql
-- Ver todos los negocios con teléfono
SELECT nombre, telefono, direccion FROM negocios WHERE telefono != 'No disponible';

-- Estadísticas por búsqueda
SELECT busqueda, COUNT(*) as total, AVG(calificacion) as promedio
FROM negocios 
WHERE calificacion IS NOT NULL 
GROUP BY busqueda;

-- Negocios mejor calificados
SELECT nombre, calificacion, num_reviews, direccion 
FROM negocios 
WHERE calificacion >= 4.5 
ORDER BY calificacion DESC, CAST(num_reviews AS UNSIGNED) DESC;
```

## 🛠️ Solución de Problemas

### Error: Chrome no encontrado
```bash
# Reinstalar undetected-chromedriver
pip uninstall undetected-chromedriver
pip install undetected-chromedriver

# O especificar ruta de Chrome manualmente en el código
```

### Error: MySQL conexión falló
- Verifica que MySQL esté ejecutándose: `sudo systemctl status mysql`
- Confirma usuario y contraseña: `mysql -u root -p`
- El sistema funcionará solo con almacenamiento local si falla MySQL

### Error: Módulo no encontrado
```bash
# Reinstalar dependencias
pip install -r requirements.txt

# O instalar manualmente
pip install streamlit pandas plotly selenium undetected-chromedriver mysql-connector-python
```

### Scraper se detiene o es bloqueado
- Usa pausas más largas entre requests (modifica `time.sleep()` en el código)
- Cambia User-Agent en `scraper_enhanced.py`
- Usa diferentes rangos de IP o proxies
- Respeta los límites de rate limiting de Google

### Recuperar datos perdidos
```bash
# Buscar respaldos locales
ls session_data/

# Cargar sesión específica
python scraper_enhanced.py
# Ingresa el session_id cuando lo solicite

# Verificar en MySQL
mysql -u root -p
USE google_maps_scraper;
SELECT session_id, timestamp FROM respaldos_sesion ORDER BY timestamp DESC;
```

## ⚡ Optimización y Rendimiento

### Configuraciones Recomendadas:
- **Resultados por búsqueda**: 15-50 (evita búsquedas muy grandes)
- **Pausas entre requests**: 2-3 segundos
- **Auto-guardado**: Cada 5 negocios (configurable)
- **Respaldo automático**: Cada 2 minutos

### Para Búsquedas Grandes:
1. Divide en múltiples sesiones más pequeñas
2. Usa diferentes criterios geográficos
3. Programa pausas largas entre búsquedas
4. Monitorea el uso de memoria

## 📁 Estructura del Proyecto

```
google-maps-scraper-pro/
├── database_manager.py          # Gestor de MySQL y persistencia
├── scraper_enhanced.py         # Scraper principal con auto-guardado
├── streamlit_app_enhanced.py   # Interfaz web moderna
├── setup.py                    # Script de instalación
├── requirements.txt            # Dependencias
├── README.md                   # Esta documentación
├── config.json                 # Configuración generada por setup
├── session_data/               # Respaldos locales automáticos
├── exports/                    # Exportaciones CSV
├── logs/                       # Archivos de log (futuro)
└── temp_chrome_profiles/       # Perfiles temporales de Chrome
```

## 🔒 Consideraciones de Seguridad y Legalidad

### Uso Responsable:
- **Respeta los términos de servicio** de Google Maps
- **No hagas scraping masivo** que pueda sobrecargar los servidores
- **Usa pausas apropiadas** entre requests
- **No redistribuyas datos personales** sin autorización
- **Verifica la legalidad** en tu jurisdicción

### Buenas Prácticas:
- Limita a datos públicos disponibles en Google Maps
- No extraigas más datos de los necesarios
- Respeta robots.txt y políticas de rate limiting
- Considera usar APIs oficiales cuando estén disponibles
- Mantén actualizadas las dependencias de seguridad

## 🆘 Soporte y Contribuciones

### En caso de problemas:
1. Verifica que tienes la versión más reciente
2. Revisa la sección "Solución de Problemas"
3. Verifica los logs en `session_data/`
4. Prueba con una búsqueda más pequeña primero

### Características de la versión actual:
- ✅ Auto-guardado y recuperación de sesiones
- ✅ Soporte para MySQL + almacenamiento local  
- ✅ Interfaz web moderna con Streamlit
- ✅ Manejo robusto de interrupciones
- ✅ Exportación múltiple de datos
- ✅ Analytics y visualizaciones

### Próximas mejoras planificadas:
- 🔄 Soporte para proxies y rotación de IP
- 📊 Dashboard de métricas en tiempo real
- 🌐 API REST para integración externa
- 📱 Versión mobile-responsive
- 🤖 Detección automática de cambios en Google Maps

---

**⚠️ Disclaimer**: Este software es para propósitos educativos y de investigación. El uso debe cumplir con los términos de servicio de Google y las leyes locales aplicables. Los desarrolladores no se hacen responsables del mal uso de esta herramienta.

**📧 Soporte**: Para problemas técnicos, verifica primero que tengas todas las dependencias instaladas y que MySQL (si lo usas) esté funcionando correctamente.