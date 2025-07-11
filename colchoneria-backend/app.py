# colchoneria_backend/app.py

from flask import Flask, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
import urllib.parse
import os # Importar os para variables de entorno

# Importar la configuración desde config.py
from config import Config

app = Flask(__name__)
# Render inyectará la URL de la base de datos como una variable de entorno DATABASE_URL
# Si DATABASE_URL existe (en Render), la usa; de lo contrario, usa la de config.py (para desarrollo local)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = Config.SECRET_KEY


# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# Aunque no redirigiremos directamente, es buena práctica mantenerlo apuntando a la vista de login
login_manager.login_view = 'login' 

# --- CAMBIO CRUCIAL AQUÍ: Manejador de acceso no autorizado para API ---
@login_manager.unauthorized_handler
def unauthorized():
    # Para solicitudes de API (que vienen de Angular), siempre devolvemos un 401 JSON
    # Angular se encargará de la redirección al login.
    return jsonify({"message": "No autorizado. Por favor, inicia sesión."}), 401

# Habilitar CORS
CORS(app) 

# --- Modelos de Base de Datos ---

# Modelo para Productos (ya existente, solo se asegura la columna categoria)
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

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'precio': float(self.precio),
            'stock': self.stock,
            'imagen_url': self.imagen_url,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

# --- Nuevo Modelo para Usuarios ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# --- Flask-Login: Función para cargar usuarios ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Creación de tablas en la base de datos ---
with app.app_context():
    db.create_all()

# --- Rutas de la API ---

@app.route('/api/productos', methods=['GET'])
def get_productos():
    try:
        categoria_filtro = request.args.get('categoria')
        if categoria_filtro:
            productos = Product.query.filter(
                Product.activo == True, 
                Product.categoria.ilike(f"%{categoria_filtro}%")
            ).all()
        else:
            productos = Product.query.filter_by(activo=True).all()
        return jsonify([p.to_dict() for p in productos])
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return jsonify({"message": "Error al obtener productos de la base de datos."}), 500

@app.route('/api/productos/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    try:
        product = Product.query.get(product_id)
        if product:
            return jsonify(product.to_dict())
            return jsonify(product.to_dict())
        else:
            return jsonify({"message": f"Producto con ID {product_id} no encontrado."}), 404
    except Exception as e:
        print(f"Error al obtener detalle del producto: {e}")
        return jsonify({"message": "Error al obtener el detalle del producto de la base de datos."}), 500

@app.route('/api/upload-excel', methods=['POST'])
@login_required
def upload_excel():
    if not current_user.is_admin:
        return jsonify({"message": "Acceso denegado. Solo administradores pueden subir archivos."}), 403

    if 'file' not in request.files:
        return jsonify({"message": "No se encontró el archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Archivo no seleccionado"}), 400
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(BytesIO(file.read()))
            
            updates = 0
            inserts = 0
            errors = []

            for index, row in df.iterrows():
                sku = str(row.get('SKU', '')).strip()
                nombre = str(row.get('Nombre', '')).strip()
                descripcion = str(row.get('Descripción', '')).strip()
                categoria = str(row.get('Categoria', 'General')).strip()
                
                try:
                    precio = float(row.get('Precio', 0))
                    stock = int(row.get('Stock', 0))
                except (ValueError, TypeError):
                    errors.append(f"Fila {index + 2}: Precio o Stock inválido. SKU: {sku}")
                    continue

                if not sku or not nombre or precio <= 0:
                    errors.append(f"Fila {index + 2}: Datos incompletos o inválidos (SKU, Nombre, Precio debe ser > 0). SKU: {sku}")
                    continue

                try:
                    existing_product = Product.query.filter_by(sku=sku).first()

                    if existing_product:
                        existing_product.nombre = nombre
                        existing_product.descripcion = descripcion
                        existing_product.categoria = categoria
                        existing_product.precio = precio
                        existing_product.stock = stock
                        existing_product.activo = True
                        updates += 1
                    else:
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
                    db.session.commit()
                except Exception as err:
                    db.session.rollback()
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

@app.route('/api/productos', methods=['DELETE'])
@login_required
def delete_all_products():
    if not current_user.is_admin:
        return jsonify({"message": "Acceso denegado. Solo administradores pueden eliminar productos."}), 403
    try:
        db.session.query(Product).delete()
        db.session.commit()
        return jsonify({"message": "Todos los productos han sido eliminados correctamente."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar productos: {e}")
        return jsonify({"message": "Error al eliminar los productos de la base de datos."}), 500

@app.route('/api/categorias', methods=['GET'])
def get_unique_categories():
    try:
        categorias = db.session.query(Product.categoria).distinct().order_by(Product.categoria).all()
        return jsonify([c[0] for c in categorias if c[0] is not None and c[0].strip() != ''])
    except Exception as e:
        print(f"Error al obtener categorías: {e}")
        return jsonify({"message": "Error al obtener categorías."}), 500

# --- Rutas de Autenticación ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"message": "Faltan nombre de usuario o contraseña"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "El nombre de usuario ya existe"}), 409

    new_user = User(username=username, is_admin=is_admin)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Usuario registrado exitosamente", "user": {"username": username, "is_admin": is_admin}}), 201

# Ruta para iniciar sesión
@app.route('/api/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'GET':
        # Esta rama maneja las peticiones GET a /api/login, que ocurren cuando
        # Flask-Login redirige a esta URL porque un usuario no está autenticado
        # y trató de acceder a una ruta protegida.
        return jsonify({"message": "Por favor, inicia sesión para continuar."}), 200

    # Si es una petición POST (envío del formulario de login desde Angular)
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user) # Inicia la sesión del usuario
        return jsonify({"message": "Inicio de sesión exitoso", "user": {"username": user.username, "is_admin": user.is_admin}}), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401

# Ruta para cerrar sesión
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user() # Cierra la sesión del usuario
    return jsonify({"message": "Sesión cerrada exitosamente"}), 200

# Ruta para verificar el estado de la sesión (útil para el frontend)
@app.route('/api/session_status', methods=['GET'])
def session_status():
    if current_user.is_authenticated:
        return jsonify({"is_authenticated": True, "username": current_user.username, "is_admin": current_user.is_admin}), 200
    else:
        return jsonify({"is_authenticated": False}), 200

# --- Ejecutar la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
