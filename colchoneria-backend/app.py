# colchoneria_backend/app.py

from flask import Flask, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
import os # Importar os para variables de entorno

# Importar la configuración desde config.py
from config import Config

app = Flask(__name__)
# Render inyectará la URL de la base de datos como una variable de entorno DATABASE_URL
# Si DATABASE_URL existe (en Render), la usa; de lo contrario, usa la de config.py (para desarrollo local)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = Config.SECRET_KEY


# --- LÍNEA PARA DEPURACIÓN: Imprime la URI de la base de datos que Flask está usando ---
print(f"DEBUG: SQLALCHEMY_DATABASE_URI configurada: {app.config['SQLALCHEMY_DATABASE_URI']}")


# Inicializar SQLAlchemy con la aplicación Flask
db = SQLAlchemy(app)

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# Define la vista a la que redirigir si un usuario no autenticado intenta acceder a una ruta protegida.
# Aunque para APIs devolvemos JSON, es buena práctica mantenerlo.
login_manager.login_view = 'login'

# --- Manejador de acceso no autorizado para API ---
# Cuando Flask-Login detecta una petición no autorizada, llamará a esta función.
# Para APIs, es crucial devolver una respuesta JSON 401, en lugar de una redirección HTML.
@login_manager.unauthorized_handler
def unauthorized():
    # Para solicitudes de API (que vienen de Angular), siempre devolvemos un 401 JSON.
    # Angular se encargará de la redirección al login en el frontend.
    return jsonify({"message": "No autorizado. Por favor, inicia sesión."}), 401

# Habilitar CORS (Cross-Origin Resource Sharing)
# Esto permite que tu frontend Angular (que corre en un dominio/puerto diferente)
# pueda hacer peticiones a tu backend Flask.
# `supports_credentials=True` es esencial para que las cookies de sesión (usadas por Flask-Login)
# sean enviadas y recibidas correctamente entre el frontend y el backend.
# Asegúrate de que los orígenes listados incluyan la URL de tu frontend de Render si lo despliegas allí.
CORS(app, resources={r"/*": {"origins": ["http://localhost:4200", "https://colchoneria-frontend-tu-id.onrender.com"]}}, supports_credentials=True)
# Nota: "https://colchoneria-frontend-tu-id.onrender.com" es un ejemplo, reemplázalo con la URL real de tu frontend desplegado.


# --- Modelos de Base de Datos ---

# Modelo para Productos
# Mapea a la tabla 'productos' en tu base de datos.
class Product(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(100), default='General')
    precio = db.Column(db.DECIMAL(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen_url = db.Column(db.String(255))
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Método para serializar el objeto Product a un diccionario (útil para jsonify)
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'precio': float(self.precio), # Convertir Decimal a float para JSON
            'stock': self.stock,
            'imagen_url': self.imagen_url,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

# Modelo para Usuarios
# Utiliza UserMixin de Flask-Login para integrar las funcionalidades de usuario.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) # True para administrador, False para usuario común

    # Establece la contraseña hasheada
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Verifica la contraseña hasheada
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# --- Flask-Login: Función para cargar usuarios ---
# Esta función es utilizada por Flask-Login para recargar el objeto de usuario
# desde el ID de usuario almacenado en la sesión.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Creación de tablas en la base de datos ---
# Esto creará las tablas definidas por los modelos (Product y User) si no existen
# en la base de datos conectada. Se ejecuta dentro de un contexto de aplicación.
with app.app_context():
    db.create_all()

# --- Rutas de la API ---

# Ruta pública: Obtener todos los productos (con filtro opcional por categoría)
@app.route('/api/productos', methods=['GET'])
def get_productos():
    try:
        categoria_filtro = request.args.get('categoria')
        if categoria_filtro:
            # Filtra productos activos y por categoría (insensible a mayúsculas/minúsculas)
            productos = Product.query.filter(
                Product.activo == True,
                Product.categoria.ilike(f"%{categoria_filtro}%") # Búsqueda parcial de categoría
            ).all()
        else:
            # Obtiene todos los productos activos si no hay filtro de categoría
            productos = Product.query.filter_by(activo=True).all()
        return jsonify([p.to_dict() for p in productos])
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return jsonify({"message": "Error al obtener productos de la base de datos."}), 500

# Ruta pública: Obtener detalles de un producto por ID
@app.route('/api/productos/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    try:
        product = Product.query.get(product_id)
        if product:
            return jsonify(product.to_dict())
        else:
            return jsonify({"message": f"Producto con ID {product_id} no encontrado."}), 404
    except Exception as e:
        print(f"Error al obtener detalle del producto: {e}")
        return jsonify({"message": "Error al obtener el detalle del producto de la base de datos."}), 500

# Ruta protegida: Subir archivo Excel (solo accesible para usuarios administradores logueados)
@app.route('/api/upload-excel', methods=['POST'])
@login_required # Requiere que el usuario esté logueado para acceder a esta ruta
def upload_excel():
    # Verifica si el usuario logueado es administrador
    if not current_user.is_admin:
        return jsonify({"message": "Acceso denegado. Solo administradores pueden subir archivos."}), 403

    if 'file' not in request.files:
        return jsonify({"message": "No se encontró el archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Archivo no seleccionado"}), 400

    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            # Lee el archivo Excel en un DataFrame de pandas
            df = pd.read_excel(BytesIO(file.read()))

            updates = 0
            inserts = 0
            errors = []

            # Itera sobre las filas del DataFrame para procesar los productos
            for index, row in df.iterrows():
                # Obtiene los datos de las columnas del Excel, limpiando espacios y estableciendo valores por defecto
                sku = str(row.get('SKU', '')).strip()
                nombre = str(row.get('Nombre', '')).strip()
                descripcion = str(row.get('Descripción', '')).strip()
                categoria = str(row.get('Categoria', 'General')).strip()

                try:
                    precio = float(row.get('Precio', 0))
                    stock = int(row.get('Stock', 0))
                except (ValueError, TypeError):
                    errors.append(f"Fila {index + 2}: Precio o Stock inválido. SKU: {sku}")
                    continue # Salta esta fila si hay un error de tipo

                if not sku or not nombre or precio <= 0:
                    errors.append(f"Fila {index + 2}: Datos incompletos o inválidos (SKU, Nombre, Precio debe ser > 0). SKU: {sku}")
                    continue # Salta esta fila si faltan datos o el precio es inválido

                try:
                    # Busca un producto existente por SKU
                    existing_product = Product.query.filter_by(sku=sku).first()

                    if existing_product:
                        # Si el producto existe, actualiza sus campos
                        existing_product.nombre = nombre
                        existing_product.descripcion = descripcion
                        existing_product.categoria = categoria
                        existing_product.precio = precio
                        existing_product.stock = stock
                        existing_product.activo = True # Asegura que el producto esté activo
                        updates += 1
                    else:
                        # Si el producto no existe, crea uno nuevo
                        new_product = Product(
                            sku=sku,
                            nombre=nombre,
                            descripcion=descripcion,
                            categoria=categoria,
                            precio=precio,
                            stock=stock
                        )
                        db.session.add(new_product)
                        inserts += 1
                    db.session.commit() # Confirma la operación en la base de datos
                except Exception as err:
                    db.session.rollback() # Revierte la transacción en caso de error
                    errors.append(f"Fila {index + 2}: Error en la base de datos: {err}. SKU: {sku}")

            response_message = f"Proceso de Excel completado. Insertados: {inserts}, Actualizados: {updates}."
            if errors:
                response_message += f" Se encontraron {len(errors)} errores."

            return jsonify({
                "message": response_message,
                "inserts": inserts,
                "updates": updates,
                "errors": errors
            }), 200

        except Exception as e:
            return jsonify({"message": f"Error al procesar el archivo Excel: {str(e)}"}), 500
    else:
        return jsonify({"message": "Formato de archivo no soportado. Por favor, sube un .xlsx o .xls"}), 400

# Ruta protegida: Eliminar todos los productos (solo accesible para usuarios administradores logueados)
@app.route('/api/productos', methods=['DELETE'])
@login_required # Requiere que el usuario esté logueado
def delete_all_products():
    # Verifica si el usuario logueado es administrador
    if not current_user.is_admin:
        return jsonify({"message": "Acceso denegado. Solo administradores pueden eliminar productos."}), 403
    try:
        db.session.query(Product).delete() # Elimina todos los registros de la tabla Product
        db.session.commit() # Confirma la eliminación
        return jsonify({"message": "Todos los productos han sido eliminados correctamente."}), 200
    except Exception as e:
        db.session.rollback() # Revierte en caso de error
        print(f"Error al eliminar productos: {e}")
        return jsonify({"message": "Error al eliminar los productos de la base de datos."}), 500

# Ruta pública: Obtener categorías únicas de productos
@app.route('/api/categorias', methods=['GET'])
def get_unique_categories():
    try:
        # Obtiene todas las categorías únicas, las ordena y filtra valores nulos o vacíos
        categorias = db.session.query(Product.categoria).distinct().order_by(Product.categoria).all()
        return jsonify([c[0] for c in categorias if c[0] is not None and c[0].strip() != ''])
    except Exception as e:
        print(f"Error al obtener categorías: {e}")
        return jsonify({"message": "Error al obtener categorías."}), 500

# --- Rutas de Autenticación ---

# Ruta para registrar un nuevo usuario
# Nota: En una aplicación de producción real, el registro de administradores
# debería ser un proceso más controlado (ej. solo un superadmin puede crear otros admins).
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False) # Por defecto, un nuevo usuario no es admin

    if not username or not password:
        return jsonify({"message": "Faltan nombre de usuario o contraseña"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "El nombre de usuario ya existe"}), 409

    new_user = User(username=username, is_admin=is_admin)
    new_user.set_password(password) # Hashea la contraseña antes de guardarla
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Usuario registrado exitosamente", "user": {"username": username, "is_admin": is_admin}}), 201

# Ruta para iniciar sesión
@app.route('/api/login', methods=['POST']) # Cambiado a /api/login para consistencia con Angular
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user) # Inicia la sesión del usuario con Flask-Login
        return jsonify({"message": "Inicio de sesión exitoso", "user": {"username": user.username, "is_admin": user.is_admin}}), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401

# Ruta para cerrar sesión
@app.route('/logout', methods=['POST'])
@login_required # Solo un usuario logueado puede cerrar sesión
def logout():
    logout_user() # Cierra la sesión del usuario con Flask-Login
    return jsonify({"message": "Sesión cerrada exitosamente"}), 200

# Ruta para verificar el estado de la sesión (útil para el frontend)
# Permite que el frontend sepa si hay una sesión activa y quién es el usuario.
@app.route('/api/session_status', methods=['GET'])
def session_status():
    if current_user.is_authenticated:
        return jsonify({"is_authenticated": True, "username": current_user.username, "is_admin": current_user.is_admin}), 200
    else:
        return jsonify({"is_authenticated": False}), 200

# --- Ejecutar la aplicación ---
if __name__ == '__main__':
    # Cuando debug=True, Flask proporciona un depurador interactivo
    # y recarga el servidor automáticamente al detectar cambios.
    # NO USAR debug=True en producción.
    app.run(debug=True, port=5000)
