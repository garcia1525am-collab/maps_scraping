import streamlit as st
import pandas as pd
import time
from io import BytesIO
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from scraper_enhanced import GoogleMapsScraperEnhanced
from database_manager import DatabaseManager, LocalPersistence
import json
import uuid

# Configuración de la página
st.set_page_config(
    page_title="Google Maps Business Scraper Pro",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado mejorado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(40,167,69,0.1);
    }
    .error-box {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #dc3545;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(220,53,69,0.1);
    }
    .info-box {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #17a2b8;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(23,162,184,0.1);
    }
    .warning-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(255,193,7,0.1);
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102,126,234,0.3);
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🗺️ Google Maps Business Scraper PRO</h1>
    <p style="font-size: 1.2em; margin-bottom: 0;">Extracción Avanzada con Auto-guardado y Base de Datos</p>
    <p style="font-size: 0.9em; opacity: 0.9; margin-top: 0.5rem;">✨ Nunca más pierdas tus datos • 💾 Persistencia Automática • 🔄 Recuperación de Sesiones</p>
</div>
""", unsafe_allow_html=True)

# Funciones de inicialización
@st.cache_resource
def init_database_manager(mysql_config):
    """Inicializa el gestor de base de datos (cached)"""
    if not mysql_config:
        return None
    
    try:
        db_manager = DatabaseManager(**mysql_config)
        if db_manager.connect():
            db_manager.create_tables()
            return db_manager
    except Exception as e:
        st.error(f"Error conectando a MySQL: {e}")
    return None

def init_session_state():
    """Inicializa el estado de la sesión"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = []
    
    if 'scraping_history' not in st.session_state:
        st.session_state.scraping_history = []
    
    if 'is_scraping' not in st.session_state:
        st.session_state.is_scraping = False
    
    if 'mysql_config' not in st.session_state:
        st.session_state.mysql_config = None
    
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = None
    
    if 'auto_save_enabled' not in st.session_state:
        st.session_state.auto_save_enabled = True

def load_session_from_storage(session_id, db_manager=None):
    """Carga una sesión desde almacenamiento"""
    local_persistence = LocalPersistence()
    
    # Intentar cargar desde MySQL primero
    if db_manager:
        try:
            backup = db_manager.get_latest_session_backup(session_id)
            if backup:
                session_data = backup['datos']
                return session_data
        except Exception as e:
            st.warning(f"Error cargando desde MySQL: {e}")
    
    # Intentar cargar localmente
    session_data = local_persistence.load_latest_session(session_id)
    return session_data

def save_session_to_storage(session_data, session_id, db_manager=None):
    """Guarda sesión en almacenamiento"""
    local_persistence = LocalPersistence()
    
    # Guardar localmente siempre
    local_persistence.save_session(session_data, session_id)
    
    # Guardar en MySQL si está disponible
    if db_manager:
        try:
            db_manager.save_session_backup(session_id, session_data)
            # Guardar negocios individuales
            if session_data.get('scraped_data'):
                new_businesses = [b for b in session_data['scraped_data'] if not b.get('saved_to_db')]
                if new_businesses:
                    db_manager.save_businesses_batch(new_businesses)
        except Exception as e:
            st.warning(f"Error guardando en MySQL: {e}")

# Inicializar estado
init_session_state()

# Sidebar con configuración avanzada
st.sidebar.markdown("## ⚙️ Panel de Control Avanzado")

# Configuración de base de datos
with st.sidebar.expander("🗄️ Configuración MySQL", expanded=False):
    st.markdown("**Configura tu base de datos MySQL para persistencia avanzada:**")
    
    mysql_host = st.text_input("Host", value="localhost", help="Dirección del servidor MySQL")
    mysql_db = st.text_input("Base de datos", value="google_maps_scraper", help="Nombre de la base de datos")
    mysql_user = st.text_input("Usuario", value="root", help="Usuario de MySQL")
    mysql_password = st.text_input("Contraseña", type="password", help="Contraseña de MySQL")
    
    col_test, col_save = st.columns(2)
    
    with col_test:
        if st.button("🔍 Probar Conexión", use_container_width=True):
            try:
                test_config = {
                    'host': mysql_host,
                    'database': mysql_db,
                    'user': mysql_user,
                    'password': mysql_password
                }
                
                with st.spinner("Probando conexión..."):
                    db_manager = DatabaseManager(**test_config)
                    if db_manager.connect():
                        db_manager.create_tables()
                        st.success("✅ Conexión exitosa")
                        st.session_state.mysql_config = test_config
                        st.session_state.db_manager = db_manager
                    else:
                        st.error("❌ Error de conexión")
                        
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with col_save:
        if st.button("💾 Activar MySQL", use_container_width=True):
            if mysql_host and mysql_db and mysql_user:
                st.session_state.mysql_config = {
                    'host': mysql_host,
                    'database': mysql_db,
                    'user': mysql_user,
                    'password': mysql_password
                }
                st.success("✅ Configuración guardada")
            else:
                st.error("❌ Completa todos los campos")

# Gestión de sesiones
with st.sidebar.expander("📂 Gestión de Sesiones", expanded=True):
    current_session = st.session_state.session_id
    st.markdown(f"**Sesión actual:** `{current_session}`")
    
    # Input para ID de sesión personalizado
    new_session_id = st.text_input(
        "🆔 ID de Sesión Personalizado",
        placeholder="Ingresa un ID o deja vacío para generar uno nuevo",
        help="Usa el mismo ID para continuar una sesión anterior"
    )
    
    col_new, col_load = st.columns(2)
    
    with col_new:
        if st.button("🆕 Nueva Sesión", use_container_width=True):
            if new_session_id:
                st.session_state.session_id = new_session_id.strip()
            else:
                st.session_state.session_id = str(uuid.uuid4())[:8]
            
            st.session_state.scraped_data = []
            st.session_state.scraping_history = []
            st.success(f"✅ Nueva sesión: {st.session_state.session_id}")
            st.rerun()
    
    with col_load:
        if st.button("📂 Cargar Sesión", use_container_width=True):
            if new_session_id:
                session_data = load_session_from_storage(
                    new_session_id.strip(), 
                    st.session_state.db_manager
                )
                
                if session_data:
                    st.session_state.session_id = new_session_id.strip()
                    st.session_state.scraped_data = session_data.get('extracted_businesses', [])
                    st.session_state.scraping_history = session_data.get('search_history', [])
                    st.success(f"✅ Sesión cargada: {len(st.session_state.scraped_data)} negocios")
                    st.rerun()
                else:
                    st.error("❌ Sesión no encontrada")
            else:
                st.error("❌ Ingresa un ID de sesión")

# Auto-guardado
with st.sidebar.expander("🔄 Auto-guardado", expanded=False):
    st.session_state.auto_save_enabled = st.checkbox(
        "Activar auto-guardado",
        value=st.session_state.auto_save_enabled,
        help="Guarda automáticamente cada 5 negocios procesados"
    )
    
    if st.button("💾 Guardar Ahora", use_container_width=True):
        if st.session_state.scraped_data or st.session_state.scraping_history:
            session_data = {
                'session_id': st.session_state.session_id,
                'extracted_businesses': st.session_state.scraped_data,
                'search_history': st.session_state.scraping_history,
                'timestamp': datetime.now().isoformat()
            }
            
            save_session_to_storage(
                session_data,
                st.session_state.session_id,
                st.session_state.db_manager
            )
            st.success("✅ Sesión guardada manualmente")
        else:
            st.info("ℹ️ No hay datos para guardar")

# Estadísticas de la sesión actual
with st.sidebar.expander("📊 Estadísticas de Sesión", expanded=True):
    if st.session_state.scraped_data:
        total_businesses = len(st.session_state.scraped_data)
        searches_count = len(st.session_state.scraping_history)
        
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("🏪 Negocios", total_businesses)
        with col_stat2:
            st.metric("🔍 Búsquedas", searches_count)
        
        if total_businesses > 0:
            df = pd.DataFrame(st.session_state.scraped_data)
            
            # Métricas de completitud
            completeness_metrics = {}
            for col in ['telefono', 'website', 'direccion', 'calificacion']:
                if col in df.columns:
                    available = (df[col] != 'No disponible').sum()
                    percentage = (available / total_businesses) * 100
                    completeness_metrics[col] = percentage
            
            st.markdown("**📈 Completitud de Datos:**")
            for field, percentage in completeness_metrics.items():
                st.progress(percentage / 100, text=f"{field.title()}: {percentage:.1f}%")
        
        # Indicador de MySQL
        if st.session_state.db_manager:
            st.markdown("✅ **MySQL conectado**")
        else:
            st.markdown("⚠️ **Solo almacenamiento local**")
            
    else:
        st.info("🎯 Inicia tu primera búsqueda para ver estadísticas")

# Función para realizar scraping mejorado
def perform_enhanced_scraping(url, max_results, search_name):
    """Realiza scraping con auto-guardado y persistencia"""
    try:
        # Crear scraper con configuración avanzada
        scraper = GoogleMapsScraperEnhanced(
            auto_save=st.session_state.auto_save_enabled,
            mysql_config=st.session_state.mysql_config,
            session_id=st.session_state.session_id
        )
        
        # Cargar datos existentes en el scraper
        if st.session_state.scraped_data:
            scraper.extracted_businesses = st.session_state.scraped_data.copy()
        if st.session_state.scraping_history:
            scraper.search_history = st.session_state.scraping_history.copy()
        
        # Progress placeholder
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Realizar scraping
        with st.spinner('🌐 Accediendo a Google Maps...'):
            businesses = scraper.search_businesses(url, max_results=max_results, search_name=search_name)
        
        if businesses:
            # Actualizar session state
            st.session_state.scraped_data = scraper.extracted_businesses.copy()
            st.session_state.scraping_history = scraper.search_history.copy()
            
            # Guardado final
            session_data = {
                'session_id': st.session_state.session_id,
                'extracted_businesses': st.session_state.scraped_data,
                'search_history': st.session_state.scraping_history,
                'timestamp': datetime.now().isoformat()
            }
            
            save_session_to_storage(
                session_data,
                st.session_state.session_id,
                st.session_state.db_manager
            )
            
            return True, businesses
        else:
            return False, "No se encontraron resultados"
            
    except Exception as e:
        return False, f"Error durante el scraping: {str(e)}"
    finally:
        try:
            scraper.close()
        except:
            pass

# Configuración principal
st.markdown("## 🔍 Nueva Búsqueda de Negocios")

# Formulario de búsqueda mejorado
with st.form("enhanced_search_form", clear_on_submit=False):
    search_url = st.text_input(
        "🌐 URL de Búsqueda de Google Maps",
        placeholder="https://www.google.com/maps/search/restaurantes+cerca+de+mi/@19.4326,-99.1332,15z",
        help="Pega aquí la URL completa de tu búsqueda en Google Maps"
    )
    
    col_name, col_results, col_session = st.columns([3, 1, 1])
    
    with col_name:
        search_name = st.text_input(
            "🏷️ Nombre de la Búsqueda",
            placeholder="ej: restaurantes_cdmx, dentistas_zona_norte",
            help="Un nombre descriptivo para identificar esta búsqueda"
        )
    
    with col_results:
        form_max_results = st.number_input(
            "📊 Resultados",
            min_value=1,
            max_value=100,
            value=15
        )
    
    with col_session:
        st.markdown("**Sesión Actual:**")
        st.code(st.session_state.session_id)
    
    # Opciones avanzadas
    with st.expander("⚙️ Opciones Avanzadas"):
        col_auto, col_backup = st.columns(2)
        
        with col_auto:
            auto_save_this_search = st.checkbox(
                "🔄 Auto-guardar esta búsqueda",
                value=st.session_state.auto_save_enabled,
                help="Guarda automáticamente cada 5 negocios"
            )
        
        with col_backup:
            create_backup = st.checkbox(
                "💾 Crear respaldo CSV automático",
                value=True,
                help="Crea un archivo CSV de respaldo durante el proceso"
            )
    
    # Botones de acción
    col_submit, col_clear, col_export = st.columns([2, 1, 1])
    
    with col_submit:
        submit_button = st.form_submit_button(
            "🚀 Iniciar Scraping Avanzado",
            use_container_width=True,
            type="primary"
        )
    
    with col_clear:
        clear_button = st.form_submit_button(
            "🗑️ Limpiar Datos",
            use_container_width=True
        )
    
    with col_export:
        quick_export = st.form_submit_button(
            "📊 Exportar Rápido",
            use_container_width=True
        )

# Lógica de botones
if clear_button:
    st.session_state.scraped_data = []
    st.session_state.scraping_history = []
    st.success("✅ Todos los datos han sido limpiados")
    st.rerun()

if quick_export and st.session_state.scraped_data:
    csv_buffer = BytesIO()
    df = pd.DataFrame(st.session_state.scraped_data)
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="📥 Descargar CSV Actual",
        data=csv_data,
        file_name=f"session_{st.session_state.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Lógica de scraping
if submit_button and search_url:
    if "google.com/maps" not in search_url and "maps.google.com" not in search_url:
        st.markdown("""
        <div class="error-box">
            <strong>❌ URL no válida</strong><br>
            La URL debe ser una búsqueda de Google Maps válida.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Preparar nombre de búsqueda
        if not search_name:
            search_name = f"busqueda_{len(st.session_state.scraping_history) + 1}"
        
        # Información de la sesión
        st.markdown(f"""
        <div class="info-box">
            <strong>🚀 Iniciando Scraping Avanzado</strong><br>
            📊 Sesión: {st.session_state.session_id}<br>
            🏷️ Búsqueda: {search_name}<br>
            📈 Resultados solicitados: {form_max_results}<br>
            🔄 Auto-guardado: {'Activado' if auto_save_this_search else 'Desactivado'}<br>
            🗄️ MySQL: {'Conectado' if st.session_state.db_manager else 'No disponible'}
        </div>
        """, unsafe_allow_html=True)
        
        # Realizar scraping
        success, result = perform_enhanced_scraping(search_url, form_max_results, search_name)
        
        if success:
            businesses = result
            st.markdown(f"""
            <div class="success-box">
                <strong>✅ Extracción completada exitosamente</strong><br>
                📊 Negocios encontrados: {len(businesses)}<br>
                🏷️ Búsqueda: {search_name}<br>
                💾 Datos guardados automáticamente en sesión: {st.session_state.session_id}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="error-box">
                <strong>❌ Error en la extracción</strong><br>
                {result}
            </div>
            """, unsafe_allow_html=True)

# Panel de resultados mejorado
if st.session_state.scraped_data:
    st.markdown("---")
    st.markdown("## 📊 Panel de Resultados Avanzado")
    
    df = pd.DataFrame(st.session_state.scraped_data)
    
    # Métricas principales con indicadores de estado
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("🏪 Total Negocios", len(df))
    
    with col2:
        with_phone = (df['telefono'] != 'No disponible').sum()
        phone_percentage = (with_phone / len(df)) * 100
        st.metric("📞 Con Teléfono", with_phone, delta=f"{phone_percentage:.1f}%")
    
    with col3:
        with_website = (df['website'] != 'No disponible').sum()
        website_percentage = (with_website / len(df)) * 100
        st.metric("🌐 Con Website", with_website, delta=f"{website_percentage:.1f}%")
    
    with col4:
        with_rating = (df['calificacion'] != 'No disponible').sum()
        rating_percentage = (with_rating / len(df)) * 100
        st.metric("⭐ Con Calificación", with_rating, delta=f"{rating_percentage:.1f}%")
    
    with col5:
        avg_rating = None
        try:
            ratings = df[df['calificacion'] != 'No disponible']['calificacion']
            ratings_numeric = pd.to_numeric(ratings, errors='coerce').dropna()
            if not ratings_numeric.empty:
                avg_rating = ratings_numeric.mean()
        except:
            avg_rating = None
        
        if avg_rating:
            st.metric("📊 Promedio", f"{avg_rating:.1f} ⭐")
        else:
            st.metric("📊 Promedio", "N/A")
    
    with col6:
        # Indicador de persistencia
        if st.session_state.db_manager:
            st.metric("🗄️ Almacenamiento", "MySQL + Local")
        else:
            st.metric("💾 Almacenamiento", "Solo Local")
    
    # Pestañas mejoradas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Datos Interactivos", 
        "📈 Analytics Avanzado", 
        "🗂️ Historial Completo", 
        "💾 Exportación Masiva",
        "🔄 Gestión de Sesión"
    ])
    
    with tab1:
        st.markdown("### 📋 Explorador de Datos Interactivo")
        
        # Filtros avanzados
        col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
        
        with col_filter1:
            busquedas_unicas = df['busqueda'].unique() if 'busqueda' in df.columns else []
            filtro_busqueda = st.multiselect(
                "🔍 Filtrar por búsqueda:",
                busquedas_unicas,
                default=busquedas_unicas
            )
        
        with col_filter2:
            filtros_rapidos = st.multiselect(
                "⚡ Filtros rápidos:",
                ["Solo con teléfono", "Solo con website", "Solo con calificación", "Calificación > 4.0"],
                default=[]
            )
        
        with col_filter3:
            ordenar_por = st.selectbox(
                "📊 Ordenar por:",
                ["Índice", "Nombre", "Calificación", "Número de reviews"],
                index=0
            )
        
        with col_filter4:
            mostrar_limite = st.number_input(
                "📄 Límite de filas:",
                min_value=10,
                max_value=1000,
                value=100,
                step=10
            )
        
        # Aplicar filtros
        df_filtered = df.copy()
        
        if filtro_busqueda and 'busqueda' in df.columns:
            df_filtered = df_filtered[df_filtered['busqueda'].isin(filtro_busqueda)]
        
        for filtro in filtros_rapidos:
            if filtro == "Solo con teléfono":
                df_filtered = df_filtered[df_filtered['telefono'] != 'No disponible']
            elif filtro == "Solo con website":
                df_filtered = df_filtered[df_filtered['website'] != 'No disponible']
            elif filtro == "Solo con calificación":
                df_filtered = df_filtered[df_filtered['calificacion'] != 'No disponible']
            elif filtro == "Calificación > 4.0":
                try:
                    ratings = pd.to_numeric(df_filtered['calificacion'], errors='coerce')
                    df_filtered = df_filtered[ratings > 4.0]
                except:
                    pass
        
        # Limitar resultados mostrados
        df_display = df_filtered.head(mostrar_limite)
        
        # Información de filtros
        if len(df_filtered) != len(df):
            st.info(f"📊 Mostrando {len(df_display)} de {len(df_filtered)} negocios filtrados (Total: {len(df)})")
        else:
            st.info(f"📊 Mostrando {len(df_display)} de {len(df)} negocios")
        
        # Tabla interactiva
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "nombre": st.column_config.TextColumn("🏪 Nombre", width="large"),
                "calificacion": st.column_config.NumberColumn("⭐ Calificación", format="%.1f"),
                "num_reviews": st.column_config.TextColumn("📝 Reviews"),
                "tipo": st.column_config.TextColumn("🏷️ Tipo"),
                "direccion": st.column_config.TextColumn("📍 Dirección", width="large"),
                "telefono": st.column_config.TextColumn("📞 Teléfono"),
                "website": st.column_config.LinkColumn("🌐 Website"),
                "busqueda": st.column_config.TextColumn("🔍 Búsqueda"),
                "fecha_extraccion": st.column_config.DatetimeColumn("📅 Extraído"),
                "session_id": st.column_config.TextColumn("🆔 Sesión")
            },
            height=500
        )
    
    with tab2:
        st.markdown("### 📈 Analytics y Visualizaciones Avanzadas")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Gráfico de tipos de negocio
            if 'tipo' in df.columns:
                tipo_counts = df[df['tipo'] != 'No disponible']['tipo'].value_counts().head(15)
                if not tipo_counts.empty:
                    fig = px.bar(
                        x=tipo_counts.values,
                        y=tipo_counts.index,
                        orientation='h',
                        title="🏪 Top 15 Tipos de Negocio",
                        labels={'x': 'Cantidad', 'y': 'Tipo de Negocio'},
                        color=tipo_counts.values,
                        color_continuous_scale="viridis"
                    )
                    fig.update_layout(height=500, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            # Distribución de calificaciones
            if 'calificacion' in df.columns:
                ratings = df[df['calificacion'] != 'No disponible']['calificacion']
                if not ratings.empty:
                    try:
                        ratings_numeric = pd.to_numeric(ratings, errors='coerce').dropna()
                        if not ratings_numeric.empty:
                            fig = px.histogram(
                                ratings_numeric,
                                title="⭐ Distribución de Calificaciones",
                                labels={'value': 'Calificación', 'count': 'Cantidad'},
                                nbins=20,
                                color_discrete_sequence=['#667eea']
                            )
                            fig.update_layout(height=500, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.info("No se pudieron procesar las calificaciones")
        
        # Analytics por búsqueda
        if 'busqueda' in df.columns:
            st.markdown("#### 📊 Analytics por Búsqueda")
            
            busqueda_stats = df.groupby('busqueda').agg({
                'nombre': 'count',
                'telefono': lambda x: (x != 'No disponible').sum(),
                'website': lambda x: (x != 'No disponible').sum(),
                'calificacion': lambda x: pd.to_numeric(x, errors='coerce').mean()
            }).round(2)
            
            busqueda_stats.columns = ['Total', 'Con Teléfono', 'Con Website', 'Calificación Promedio']
            
            st.dataframe(
                busqueda_stats,
                use_container_width=True,
                column_config={
                    "Total": st.column_config.NumberColumn("📊 Total Negocios"),
                    "Con Teléfono": st.column_config.NumberColumn("📞 Con Teléfono"),
                    "Con Website": st.column_config.NumberColumn("🌐 Con Website"),
                    "Calificación Promedio": st.column_config.NumberColumn("⭐ Promedio", format="%.2f")
                }
            )
    
    with tab3:
        st.markdown("### 🗂️ Historial Completo y Trazabilidad")
        
        if st.session_state.scraping_history:
            history_df = pd.DataFrame(st.session_state.scraping_history)
            
            # Métricas del historial
            col_h1, col_h2, col_h3, col_h4 = st.columns(4)
            
            with col_h1:
                st.metric("📊 Total Búsquedas", len(history_df))
            
            with col_h2:
                total_results = history_df['resultados'].sum()
                st.metric("🏪 Total Negocios", total_results)
            
            with col_h3:
                avg_results = history_df['resultados'].mean()
                st.metric("📈 Promedio/Búsqueda", f"{avg_results:.1f}")
            
            with col_h4:
                if 'duracion_segundos' in history_df.columns:
                    avg_duration = history_df['duracion_segundos'].mean()
                    st.metric("⏱️ Tiempo Promedio", f"{avg_duration:.0f}s")
            
            # Tabla de historial detallada
            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'busqueda': st.column_config.TextColumn('🔍 Búsqueda'),
                    'url': st.column_config.TextColumn('🌐 URL', width="large"),
                    'resultados': st.column_config.NumberColumn('📊 Resultados'),
                    'fecha': st.column_config.DatetimeColumn('📅 Fecha'),
                    'duracion_segundos': st.column_config.NumberColumn('⏱️ Duración (s)')
                }
            )
        else:
            st.info("📝 No hay historial de búsquedas aún.")
    
    with tab4:
        st.markdown("### 💾 Centro de Exportación Masiva")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            st.markdown("#### 📊 Exportaciones por Criterio")
            
            # CSV completo con timestamp
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_data = csv_buffer.getvalue()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            st.download_button(
                label="📊 Descargar Dataset Completo",
                data=csv_data,
                file_name=f"dataset_completo_session_{st.session_state.session_id}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
            
            # Solo con teléfono
            df_with_phone = df[df['telefono'] != 'No disponible']
            if not df_with_phone.empty:
                csv_phone_buffer = BytesIO()
                df_with_phone.to_csv(csv_phone_buffer, index=False, encoding='utf-8-sig')
                csv_phone_data = csv_phone_buffer.getvalue()
                
                st.download_button(
                    label=f"📞 Con Teléfono ({len(df_with_phone)} negocios)",
                    data=csv_phone_data,
                    file_name=f"negocios_con_telefono_{st.session_state.session_id}_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Solo con website
            df_with_website = df[df['website'] != 'No disponible']
            if not df_with_website.empty:
                csv_website_buffer = BytesIO()
                df_with_website.to_csv(csv_website_buffer, index=False, encoding='utf-8-sig')
                csv_website_data = csv_website_buffer.getvalue()
                
                st.download_button(
                    label=f"🌐 Con Website ({len(df_with_website)} negocios)",
                    data=csv_website_data,
                    file_name=f"negocios_con_website_{st.session_state.session_id}_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Calificación alta
            try:
                df_high_rating = df[pd.to_numeric(df['calificacion'], errors='coerce') >= 4.0]
                if not df_high_rating.empty:
                    csv_rating_buffer = BytesIO()
                    df_high_rating.to_csv(csv_rating_buffer, index=False, encoding='utf-8-sig')
                    csv_rating_data = csv_rating_buffer.getvalue()
                    
                    st.download_button(
                        label=f"⭐ Calificación ≥4.0 ({len(df_high_rating)} negocios)",
                        data=csv_rating_data,
                        file_name=f"negocios_alta_calificacion_{st.session_state.session_id}_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            except:
                pass
        
        with col_export2:
            st.markdown("#### 📋 Exportaciones por Búsqueda")
            
            if 'busqueda' in df.columns:
                busquedas_disponibles = df['busqueda'].unique()
                
                for busqueda in busquedas_disponibles:
                    df_busqueda = df[df['busqueda'] == busqueda]
                    
                    csv_busqueda_buffer = BytesIO()
                    df_busqueda.to_csv(csv_busqueda_buffer, index=False, encoding='utf-8-sig')
                    csv_busqueda_data = csv_busqueda_buffer.getvalue()
                    
                    st.download_button(
                        label=f"🔍 {busqueda} ({len(df_busqueda)})",
                        data=csv_busqueda_data,
                        file_name=f"busqueda_{busqueda}_{st.session_state.session_id}_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key=f"download_busqueda_{busqueda}"
                    )
        
        # Exportación a MySQL
        if st.session_state.db_manager:
            st.markdown("#### 🗄️ Exportar a MySQL")
            
            col_mysql1, col_mysql2 = st.columns(2)
            
            with col_mysql1:
                if st.button("💾 Forzar Sync a MySQL", use_container_width=True):
                    try:
                        with st.spinner("Sincronizando con MySQL..."):
                            # Marcar todos como no guardados para forzar sync
                            for business in st.session_state.scraped_data:
                                business.pop('saved_to_db', None)
                            
                            saved_count = st.session_state.db_manager.save_businesses_batch(
                                st.session_state.scraped_data
                            )
                            
                            st.success(f"✅ {saved_count} negocios sincronizados con MySQL")
                    except Exception as e:
                        st.error(f"❌ Error sincronizando: {e}")
            
            with col_mysql2:
                if st.button("📊 Ver Estadísticas MySQL", use_container_width=True):
                    try:
                        stats = st.session_state.db_manager.get_statistics()
                        
                        st.markdown("**📈 Estadísticas de la Base de Datos:**")
                        col_s1, col_s2 = st.columns(2)
                        
                        with col_s1:
                            st.metric("Total en BD", stats.get('total_negocios', 0))
                            st.metric("Con Teléfono", stats.get('con_telefono', 0))
                        
                        with col_s2:
                            st.metric("Con Website", stats.get('con_website', 0))
                            st.metric("Calif. Promedio", f"{stats.get('calificacion_promedio', 0):.2f}")
                        
                    except Exception as e:
                        st.error(f"❌ Error obteniendo estadísticas: {e}")
    
    with tab5:
        st.markdown("### 🔄 Gestión Avanzada de Sesión")
        
        col_session1, col_session2 = st.columns(2)
        
        with col_session1:
            st.markdown("#### 📊 Información de la Sesión Actual")
            
            session_info = {
                "ID de Sesión": st.session_state.session_id,
                "Total de Negocios": len(st.session_state.scraped_data),
                "Total de Búsquedas": len(st.session_state.scraping_history),
                "Estado MySQL": "Conectado" if st.session_state.db_manager else "Desconectado",
                "Auto-guardado": "Activo" if st.session_state.auto_save_enabled else "Inactivo"
            }
            
            for key, value in session_info.items():
                st.text(f"{key}: {value}")
            
            # Guardar sesión manualmente
            if st.button("💾 Guardar Sesión Completa", use_container_width=True):
                session_data = {
                    'session_id': st.session_state.session_id,
                    'extracted_businesses': st.session_state.scraped_data,
                    'search_history': st.session_state.scraping_history,
                    'timestamp': datetime.now().isoformat(),
                    'total_businesses': len(st.session_state.scraped_data)
                }
                
                save_session_to_storage(
                    session_data,
                    st.session_state.session_id,
                    st.session_state.db_manager
                )
                st.success("✅ Sesión guardada completamente")
        
        with col_session2:
            st.markdown("#### 🔍 Explorar Sesiones Guardadas")
            
            # Listar sesiones locales disponibles
            local_persistence = LocalPersistence()
            try:
                import os
                session_files = [f for f in os.listdir(local_persistence.data_dir) 
                               if f.startswith('session_') and f.endswith('.json')]
                
                if session_files:
                    st.markdown("**📂 Sesiones Locales Disponibles:**")
                    for file in session_files[-5:]:  # Mostrar últimas 5
                        session_id_from_file = file.split('_')[1]
                        st.text(f"• {session_id_from_file}")
                else:
                    st.info("No hay sesiones locales guardadas")
                    
            except Exception as e:
                st.warning(f"Error listando sesiones: {e}")
            
            # Cargar desde ID específico
            load_session_id = st.text_input("🆔 Cargar ID específico:", key="load_specific")
            
            if st.button("📂 Cargar Sesión Específica", use_container_width=True):
                if load_session_id:
                    session_data = load_session_from_storage(
                        load_session_id,
                        st.session_state.db_manager
                    )
                    
                    if session_data:
                        # Confirmar antes de reemplazar
                        if st.session_state.scraped_data:
                            st.warning("⚠️ Esto reemplazará la sesión actual")
                        
                        st.session_state.session_id = load_session_id
                        st.session_state.scraped_data = session_data.get('extracted_businesses', [])
                        st.session_state.scraping_history = session_data.get('search_history', [])
                        st.success(f"✅ Sesión {load_session_id} cargada exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Sesión no encontrada")
                else:
                    st.error("❌ Ingresa un ID de sesión válido")
        
        # Respaldo y recuperación de emergencia
        st.markdown("#### 🚨 Respaldo de Emergencia")
        
        col_emergency1, col_emergency2 = st.columns(2)
        
        with col_emergency1:
            if st.button("🆘 Crear Respaldo de Emergencia", use_container_width=True):
                if st.session_state.scraped_data:
                    # Crear respaldo completo
                    emergency_data = {
                        'session_id': st.session_state.session_id,
                        'extracted_businesses': st.session_state.scraped_data,
                        'search_history': st.session_state.scraping_history,
                        'timestamp': datetime.now().isoformat(),
                        'backup_type': 'emergency',
                        'total_businesses': len(st.session_state.scraped_data)
                    }
                    
                    # Guardar en múltiples formatos
                    local_persistence.save_session(emergency_data, f"EMERGENCY_{st.session_state.session_id}")
                    
                    # CSV de respaldo
                    df_emergency = pd.DataFrame(st.session_state.scraped_data)
                    emergency_csv = f"EMERGENCY_backup_{st.session_state.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    local_persistence.save_csv_backup(st.session_state.scraped_data, emergency_csv)
                    
                    # Intentar MySQL si está disponible
                    if st.session_state.db_manager:
                        try:
                            st.session_state.db_manager.save_session_backup(
                                f"EMERGENCY_{st.session_state.session_id}",
                                emergency_data,
                                'manual'
                            )
                        except:
                            pass
                    
                    st.success("✅ Respaldo de emergencia creado exitosamente")
                    st.info(f"📁 Archivos: JSON + CSV guardados localmente")
                else:
                    st.warning("⚠️ No hay datos para respaldar")
        
        with col_emergency2:
            if st.button("🔄 Limpiar Respaldos Antiguos", use_container_width=True):
                if st.session_state.db_manager:
                    try:
                        st.session_state.db_manager.cleanup_old_backups(7)  # 7 días
                        st.success("✅ Respaldos antiguos limpiados")
                    except Exception as e:
                        st.error(f"❌ Error limpiando: {e}")
                else:
                    st.info("ℹ️ Función disponible solo con MySQL")

# Información de seguridad y recuperación
st.markdown("---")
st.markdown("## 🛡️ Sistema de Seguridad y Recuperación de Datos")

col_security1, col_security2, col_security3 = st.columns(3)

with col_security1:
    st.markdown("""
    <div class="info-box">
        <strong>💾 Auto-guardado Inteligente</strong><br>
        • Guardado cada 5 negocios extraídos<br>
        • Respaldo automático cada 2 minutos<br>
        • Guardado al cerrar el navegador<br>
        • Manejo de interrupciones del sistema
    </div>
    """, unsafe_allow_html=True)

with col_security2:
    st.markdown("""
    <div class="success-box">
        <strong>🔄 Persistencia Múltiple</strong><br>
        • Almacenamiento local (JSON + CSV)<br>
        • Base de datos MySQL (opcional)<br>
        • Recuperación por ID de sesión<br>
        • Historial completo de búsquedas
    </div>
    """, unsafe_allow_html=True)

with col_security3:
    st.markdown("""
    <div class="warning-box">
        <strong>🚨 Recuperación de Emergencia</strong><br>
        • Respaldos manuales disponibles<br>
        • Carga desde ID específico<br>
        • Exportación antes de cada búsqueda<br>
        • Datos nunca se pierden completamente
    </div>
    """, unsafe_allow_html=True)

# Footer mejorado
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem; background: linear-gradient(135deg, #f8f9ff 0%, #e6eaff 100%); border-radius: 15px; margin-top: 2rem;">
    <h3 style="color: #667eea; margin-bottom: 1rem;">🗺️ Google Maps Business Scraper PRO</h3>
    <p style="margin-bottom: 0.5rem;"><strong>Desarrollado con ❤️ usando Streamlit + MySQL</strong></p>
    <p style="margin-bottom: 0.5rem;">🛡️ <em>Sistema de Persistencia Avanzado - Nunca más pierdas tus datos</em></p>
    <p style="margin-bottom: 0.5rem;">⚠️ <em>Usar responsablemente y respetando los términos de servicio de Google</em></p>
    <p style="font-size: 0.9em; opacity: 0.8;">🚀 Versión 3.0 - Con Auto-guardado y Recuperación Inteligente</p>
</div>
""", unsafe_allow_html=True)