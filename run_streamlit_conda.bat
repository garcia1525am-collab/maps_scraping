@echo off
echo Activando entorno de Conda y ejecutando Streamlit...

:: Activar el entorno de Conda (reemplaza 'mi-entorno' con el nombre de tu entorno)
call conda activate mi-entorno

:: Ejecutar la aplicación Streamlit
streamlit run streamlit_app_enhanced.py

:: Mantener la ventana abierta en caso de error
pause