# colchoneria_backend/app.py

from flask import Flask, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

from config import Config

app = Flask(__name__)
# Configuración de la base de datos desde variables de entorno o archivo Config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or Config.SECRET_KEY # Usar variable de entorno para SECRET_KEY primero

# Configuración de la cookie de sesión para solicitudes entre sitios (importante para el frontend en Netlify)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True # Debe ser True para SameSite=None en producción (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = '.onrender.com' # Esto es crucial para Render

print(f"DEBUG: SQLALCHEMY_DATABASE_URI configurado: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Establece la vista de login para redirección

# Configuración de CORS para permitir solicitudes desde tu frontend (ej. Netlify)
CORS(app,
     supports_credentials=True,
     origins=["https://colchoneria-frontend.netlify.app", "http://localhost:4200"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Especifica los métodos permitidos
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"] # Especifica los encabezados permitidos
)

# Modelo de Usuario para Flask-Login
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Modelo de Producto
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)
    # image_url no estaba presente en la versión anterior a la subida de Excel
    # Si tu base de datos ya tiene esta columna, no causará un error,
    # pero no se usará en esta versión.

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'stock': self.stock,
            # 'image_url': self.image_url # Descomentar si la columna ya existe y quieres incluirla
        }

# Crea las tablas de la base de datos si no existen
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ruta para el registro de usuarios
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 409

    new_user = User(username=username, is_admin=is_admin)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user": {"username": username, "is_admin": is_admin}}), 201

# Ruta para el inicio de sesión de usuarios
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        session.permanent = False # Establecer la sesión como no permanente
        return jsonify({"message": "Login successful", "user": {"username": user.username, "is_admin": user.is_admin}}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# Ruta para el cierre de sesión de usuarios
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Session closed successfully"}), 200

# Ruta para verificar el estado actual de la sesión
@app.route('/api/session_status', methods=['GET'])
def session_status():
    if current_user.is_authenticated:
        return jsonify({"is_authenticated": True, "username": current_user.username, "is_admin": current_user.is_admin}), 200
    else:
        return jsonify({"is_authenticated": False, "username": None, "is_admin": False}), 200

# Ruta para obtener todos los productos o filtrar por categoría
@app.route('/api/productos', methods=['GET'])
def get_products():
    category = request.args.get('category')
    if category:
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()
    return jsonify([product.to_dict() for product in products])

# Ruta para obtener un solo producto por ID
@app.route('/api/productos/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

# Ruta para obtener categorías únicas
@app.route('/api/categorias', methods=['GET'])
def get_categories():
    categories = db.session.query(Product.category).distinct().all()
    return jsonify([c[0] for c in categories if c[0]]) # Filtra categorías None/vacías

if __name__ == '__main__':
    app.run(debug=True)
