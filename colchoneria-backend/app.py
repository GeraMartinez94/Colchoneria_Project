# colchoneria_backend/app.py

from flask import Flask, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
import os

# Cloudinary imports
import cloudinary
import cloudinary.uploader
import cloudinary.api

from config import Config

app = Flask(__name__)
# Database configuration from environment variables or Config file
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or Config.SECRET_KEY # Use environment variable for SECRET_KEY first

# Session cookie configuration for cross-site requests (important for frontend on Netlify)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True # Must be True for SameSite=None in production (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True

print(f"DEBUG: SQLALCHEMY_DATABASE_URI configured: {app.config['SQLALCHEMY_DATABASE_URI']}")

# --- Cloudinary Initialization ---
cloudinary_initialized = False
try:
    # Get Cloudinary credentials from environment variables
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET')
    )
    cloudinary_initialized = True
    print("Cloudinary initialized successfully.")
except Exception as e:
    print(f"Error initializing Cloudinary: {e}")
    cloudinary_initialized = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Set the login view for redirection

# CORS configuration to allow requests from your frontend (e.g., Netlify)
CORS(app,
     supports_credentials=True,
     origins=["https://colchoneria-frontend.netlify.app", "http://localhost:4200"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Especificar métodos permitidos
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"] # Especificar encabezados permitidos
)

# User model for Flask-Login
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(500)) # Field for image URL

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'stock': self.stock,
            'image_url': self.image_url
        }

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for user registration
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

# Route for user login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        session.permanent = False # Set session as non-permanent
        return jsonify({"message": "Login successful", "user": {"username": user.username, "is_admin": user.is_admin}}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# Route for user logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Session closed successfully"}), 200

# Route to check current session status
@app.route('/api/session_status', methods=['GET'])
def session_status():
    if current_user.is_authenticated:
        return jsonify({"is_authenticated": True, "username": current_user.username, "is_admin": current_user.is_admin}), 200
    else:
        return jsonify({"is_authenticated": False, "username": None, "is_admin": False}), 200

# Route to upload Excel file and images
@app.route('/api/upload-excel', methods=['POST'])
@login_required
def upload_excel():
    if not current_user.is_admin:
        return jsonify({"message": "Access denied. Only administrators can upload files."}), 403

    if 'excel_file' not in request.files:
        return jsonify({"message": "No se encontró el archivo Excel"}), 400

    excel_file = request.files['excel_file']
    if excel_file.filename == '':
        return jsonify({"message": "No se seleccionó ningún archivo Excel"}), 400

    if not excel_file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"message": "Formato de archivo no soportado. Por favor, sube un archivo .xlsx o .xls"}), 400

    try:
        df = pd.read_excel(BytesIO(excel_file.read()))
        products_to_add = []
        upload_errors = []

        # Process images if they exist
        image_files = request.files.getlist('images')
        uploaded_image_urls = {}

        if cloudinary_initialized:
            for img_file in image_files:
                if img_file.filename:
                    try:
                        # Use the filename (without extension) as the public ID
                        public_id = os.path.splitext(img_file.filename)[0]
                        upload_result = cloudinary.uploader.upload(img_file, public_id=public_id, folder="colchoneria_products")
                        uploaded_image_urls[public_id.lower()] = upload_result['secure_url']
                        print(f"Uploaded image {img_file.filename} to Cloudinary: {upload_result['secure_url']}")
                    except Exception as e:
                        upload_errors.append(f"Error al subir la imagen {img_file.filename} a Cloudinary: {e}")
                        print(f"Cloudinary upload error for {img_file.filename}: {e}")
        else:
            upload_errors.append("Cloudinary no está inicializado. Las imágenes no se subirán.")

        for index, row in df.iterrows():
            try:
                sku = str(row['SKU']).strip()
                name = str(row['Nombre']).strip()
                price = float(row['Precio'])
                description = str(row['Descripción']).strip() if 'Descripción' in row and pd.notna(row['Descripción']) else None
                category = str(row['Categoría']).strip() if 'Categoría' in row and pd.notna(row['Categoría']) else 'General'
                stock = int(row['Stock']) if 'Stock' in row and pd.notna(row['Stock']) else 0

                # Determine image URL based on SKU or Name
                image_url = None
                if sku.lower() in uploaded_image_urls:
                    image_url = uploaded_image_urls[sku.lower()]
                elif name.lower() in uploaded_image_urls:
                    image_url = uploaded_image_urls[name.lower()]
                else:
                    # If no image found by SKU or Name, check for exact filename match (without extension)
                    for filename_key, url in uploaded_image_urls.items():
                        if filename_key.lower() == sku.lower() or filename_key.lower() == name.lower():
                            image_url = url
                            break

                existing_product = Product.query.filter_by(sku=sku).first()
                if existing_product:
                    existing_product.name = name
                    existing_product.description = description
                    existing_product.price = price
                    existing_product.category = category
                    existing_product.stock = stock
                    if image_url: # Only update image if a new one was provided
                        existing_product.image_url = image_url
                    db.session.add(existing_product)
                else:
                    new_product = Product(
                        sku=sku,
                        name=name,
                        description=description,
                        price=price,
                        category=category,
                        stock=stock,
                        image_url=image_url # Assign the determined image URL
                    )
                    products_to_add.append(new_product)
            except KeyError as ke:
                upload_errors.append(f"Falta una columna requerida en la fila {index + 2}: {ke}. Asegúrate de que las columnas 'SKU', 'Nombre', 'Precio' existan.")
            except ValueError as ve:
                upload_errors.append(f"Error de formato de datos en la fila {index + 2}: {ve}. Revisa 'Precio' y 'Stock'.")
            except Exception as e:
                upload_errors.append(f"Error desconocido en la fila {index + 2}: {e}")

        if products_to_add:
            db.session.add_all(products_to_add)
        db.session.commit()

        message = "Datos de productos procesados y actualizados con éxito."
        if upload_errors:
            message += " Se encontraron algunos errores durante la subida de imágenes o el procesamiento de datos."
            return jsonify({"message": message, "errors": upload_errors}), 200
        return jsonify({"message": message}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error processing Excel file or images: {e}")
        return jsonify({"message": f"Error interno del servidor al procesar el archivo: {e}", "errors": [str(e)]}), 500


# Route to get all products or filter by category
@app.route('/api/productos', methods=['GET'])
def get_products():
    category = request.args.get('category')
    if category:
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()
    return jsonify([product.to_dict() for product in products])

# Route to get a single product by ID
@app.route('/api/productos/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

# Route to delete all products (admin only)
@app.route('/api/productos', methods=['DELETE'])
@login_required
def delete_all_products():
    if not current_user.is_admin:
        return jsonify({"message": "Access denied. Only administrators can delete products."}), 403
    try:
        db.session.query(Product).delete()
        db.session.commit()
        return jsonify({"message": "All products have been deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting products: {e}")
        return jsonify({"message": "Error deleting products from the database."}), 500

# Route to get unique categories
@app.route('/api/categorias', methods=['GET'])
def get_categories():
    categories = db.session.query(Product.category).distinct().all()
    return jsonify([c[0] for c in categories if c[0]]) # Filter out None/empty categories

if __name__ == '__main__':
    app.run(debug=True)
