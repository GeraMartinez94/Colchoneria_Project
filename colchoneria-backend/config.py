# colchoneria_backend/config.py

import urllib.parse 

class Config:
    # Configuración para desarrollo local (MySQL)
    DB_HOST = 'localhost'       
    DB_USER = 'root'            
    DB_PASSWORD = '' # <-- ¡¡¡CAMBIADO A CADENA VACÍA SEGÚN TU CONFIGURACIÓN DE MYSQL!!!
    DB_NAME = 'colchoneria_db'  # <-- ¡Asegúrate de que este nombre sea EXACTO!

    # Codifica la contraseña si contiene caracteres especiales
    # Si la contraseña es vacía, quote_plus('') seguirá siendo ''
    ENCODED_DB_PASSWORD = urllib.parse.quote_plus(DB_PASSWORD)

    # Construcción de la URI de la base de datos
    # Añadimos el parámetro auth_plugin para especificar el método de autenticación
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{ENCODED_DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}?auth_plugin=mysql_native_password'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECRET_KEY = 'una_clave_secreta_muy_segura_y_aleatoria_para_flask_login_y_sesiones' 
