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
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Session cookie configuration for cross-site requests (important for frontend on Netlify)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True # Must be True for SameSite=None in production (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = '.onrender.com' 

print(f"DEBUG: SQLALCHEMY_DATABASE_URI configured: {app.config['SQLALCHEMY_DATABASE_URI']}")

# --- Cloudinary Initialization ---
cloudinary_initialized = False
try:
    # Get Cloudinary credentials from environment variables
    cloudinary_cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    cloudinary_api_key = os.environ.get('CLOUDINARY_API_KEY')
    cloudinary_api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    # Initialize Cloudinary SDK if all credentials are provided
    if cloudinary_cloud_name and cloudinary_api_key and cloudinary_api_secret:
        cloudinary.config(
            cloud_name = cloudinary_cloud_name,
            api_key = cloudinary_api_key,
            api_secret = cloudinary_api_secret
        )
        cloudinary_initialized = True
        print("Cloudinary SDK initialized successfully.")
    else:
        print("Cloudinary environment variables not configured. Image upload functionality will not be available.")
except Exception as e:
    print(f"Error initializing Cloudinary SDK: {e}")


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to 'login' endpoint if unauthorized

# Unauthorized handler for Flask-Login
@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "Unauthorized. Please log in."}), 401

# CORS configuration to allow requests from your frontend
CORS(app, resources={r"/*": {"origins": ["http://localhost:4200", "https://colchoneriafrontend.netlify.app"]}}, supports_credentials=True)

# --- Database Models ---
class Product(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(100), default='General')
    precio = db.Column(db.DECIMAL(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen_url = db.Column(db.String(255)) # Field to store the image URL from Cloudinary
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Converts a Product object to a dictionary for JSON serialization
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'precio': float(self.precio),
            'stock': self.stock,
            'imagen_url': self.imagen_url, # Include image URL in the dictionary
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Sets the user's password by hashing it
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Checks if the provided password matches the hashed password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Flask-Login user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# --- API Routes ---

# Route to get all active products, optionally filtered by category
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
        print(f"Error getting products: {e}")
        return jsonify({"message": "Error getting products from the database."}), 500

# Route to get details of a specific product by ID
@app.route('/api/productos/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    try:
        product = Product.query.get(product_id)
        if product:
            return jsonify(product.to_dict())
        else:
            return jsonify({"message": f"Product with ID {product_id} not found."}), 404
    except Exception as e:
        print(f"Error getting product detail: {e}")
        return jsonify({"message": "Error getting product detail from the database."}), 500

# Route to upload Excel file and product images
@app.route('/api/upload-excel', methods=['POST'])
@login_required # Requires user to be logged in
def upload_excel():
    # Check if the current user is an admin
    if not current_user.is_admin:
        return jsonify({"message": "Access denied. Only administrators can upload files."}), 403

    # 1. Handle Excel file
    if 'excel_file' not in request.files:
        return jsonify({"message": "No Excel file found"}), 400

    excel_file = request.files['excel_file']
    if excel_file.filename == '':
        return jsonify({"message": "Excel file not selected"}), 400

    if not excel_file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"message": "Unsupported Excel file format. Please upload a .xlsx or .xls"}), 400

    # 2. Handle image files (optional)
    uploaded_images = request.files.getlist('images') # Get all files with the name 'images'
    image_urls_map = {} # Map to store {normalized_filename_without_extension: public_url}
    image_upload_errors = []

    # Process image uploads if images are provided and Cloudinary is initialized
    if uploaded_images and cloudinary_initialized:
        print(f"DEBUG: Received {len(uploaded_images)} images. Uploading to Cloudinary...")
        for img_file in uploaded_images:
            if img_file.filename == '':
                continue

            original_filename = img_file.filename
            # Clean up filename for association key and Cloudinary public_id
            # Remove extension and normalize (e.g., spaces to underscores, lowercase)
            filename_without_ext = os.path.splitext(original_filename)[0]
            # Further normalize: replace spaces, dots, and hyphens with underscores, then lowercase
            normalized_filename = filename_without_ext.replace(' ', '_').replace('.', '_').replace('-', '_').lower()

            try:
                # Upload the file to Cloudinary
                # 'public_id' helps control the file name in Cloudinary
                # 'folder' organizes your images into a specific folder in Cloudinary
                upload_result = cloudinary.uploader.upload(img_file,
                                                          public_id=normalized_filename,
                                                          folder="colchoneria_products", # Folder in your Cloudinary account
                                                          resource_type="image") # Ensure it's treated as an image
                public_url = upload_result['secure_url'] # Get the secure HTTPS URL
                image_urls_map[normalized_filename] = public_url
                print(f"DEBUG: Uploaded {original_filename} to Cloudinary: {public_url}")
            except Exception as e:
                error_msg = f"Error uploading {original_filename} to Cloudinary: {e}"
                image_upload_errors.append(error_msg)
                print(f"ERROR: {error_msg}")
    elif uploaded_images and not cloudinary_initialized:
        image_upload_errors.append("Images not uploaded: Cloudinary SDK is not initialized. Check environment variables.")
        print("ERROR: Images not uploaded: Cloudinary SDK is not initialized.")


    # 3. Process the Excel file
    updates = 0
    inserts = 0
    excel_processing_errors = []

    try:
        df = pd.read_excel(BytesIO(excel_file.read()))

        for index, row in df.iterrows():
            sku = str(row.get('SKU', '')).strip()
            nombre = str(row.get('Nombre', '')).strip()
            descripcion = str(row.get('Descripción', '')).strip()
            categoria = str(row.get('Categoria', 'General')).strip()

            # Normalize SKU and Name for association with uploaded images
            normalized_sku = sku.replace(' ', '_').replace('.', '_').replace('-', '_').lower()
            normalized_nombre = nombre.replace(' ', '_').replace('.', '_').replace('-', '_').lower()

            # Determine the image URL for the product:
            # 1. Try to match with uploaded images by normalized filename (SKU or Name)
            # 2. If no match, use the URL that might come in the Excel (if 'URL Imagen' column exists)
            # 3. If nothing, the URL will be None
            product_image_url = None
            if normalized_sku and normalized_sku in image_urls_map: # Ensure SKU is not empty
                product_image_url = image_urls_map[normalized_sku]
                print(f"DEBUG: SKU '{sku}' associated with uploaded image: {product_image_url}")
            elif normalized_nombre and normalized_nombre in image_urls_map: # Ensure Name is not empty
                product_image_url = image_urls_map[normalized_nombre]
                print(f"DEBUG: Name '{nombre}' associated with uploaded image: {product_image_url}")
            else:
                # If no associated image was uploaded, try to read from an 'URL Imagen' column in the Excel
                excel_image_url = str(row.get('URL Imagen', '')).strip()
                if excel_image_url:
                    product_image_url = excel_image_url
                    print(f"DEBUG: Using Excel image URL for '{sku}': {product_image_url}")
                else:
                    print(f"DEBUG: No image URL found for '{sku}' (neither uploaded nor in Excel).")


            try:
                precio = float(row.get('Precio', 0))
                stock = int(row.get('Stock', 0))
            except (ValueError, TypeError):
                excel_processing_errors.append(f"Row {index + 2}: Invalid Price or Stock. SKU: {sku}")
                continue

            if not sku or not nombre or precio <= 0:
                excel_processing_errors.append(f"Row {index + 2}: Incomplete or invalid data (SKU, Name, Price must be > 0). SKU: {sku}")
                continue

            try:
                existing_product = Product.query.filter_by(sku=sku).first()

                if existing_product:
                    existing_product.nombre = nombre
                    existing_product.descripcion = descripcion
                    existing_product.categoria = categoria
                    existing_product.precio = precio
                    existing_product.stock = stock
                    existing_product.imagen_url = product_image_url # Assign the image URL
                    existing_product.activo = True
                    updates += 1
                else:
                    new_product = Product(
                        sku=sku,
                        nombre=nombre,
                        descripcion=descripcion,
                        categoria=categoria,
                        precio=precio,
                        stock=stock,
                        imagen_url=product_image_url # Assign the image URL
                    )
                    db.session.add(new_product)
                    inserts += 1
                db.session.commit()
            except Exception as err:
                db.session.rollback()
                excel_processing_errors.append(f"Row {index + 2}: Database error: {err}. SKU: {sku}")

        final_errors = image_upload_errors + excel_processing_errors
        response_message = f"Process completed. Inserted: {inserts}, Updated: {updates}."
        if final_errors:
            response_message += f" {len(final_errors)} errors found."

        return jsonify({
            "message": response_message,
            "inserts": inserts,
            "updates": updates,
            "errors": final_errors
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error processing Excel file: {str(e)}"}), 500

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

# Route to get unique product categories
@app.route('/api/categorias', methods=['GET'])
def get_unique_categories():
    try:
        categorias = db.session.query(Product.categoria).distinct().order_by(Product.categoria).all()
        return jsonify([c[0] for c in categorias if c[0] is not None and c[0].strip() != ''])
    except Exception as e:
        print(f"Error getting categories: {e}")
        return jsonify({"message": "Error getting categories."}), 500

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

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
        return jsonify({"is_authenticated": False}), 200

# Main entry point for the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=5000)
