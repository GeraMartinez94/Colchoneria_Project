# colchoneria_backend/config.py

class Config:
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'DevelopColchones2025@' # Asegúrate de que esta sea tu contraseña correcta
    DB_NAME = 'colchoneria_db'

    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- ¡NUEVA CLAVE SECRETA PARA FLASK Y FLASK-LOGIN! ---
    # Genera una clave aleatoria y compleja. Puedes usar os.urandom(24).hex() en una consola Python.
    SECRET_KEY = 'una_clave_secreta_muy_segura_y_aleatoria_para_flask_login_y_sesiones' 
