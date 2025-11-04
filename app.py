import os
import json
from typing import Tuple
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash, send_file
)
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from io import BytesIO
import pandas as pd
from pymongo.errors import PyMongoError, OperationFailure
from utils.mongo_utils import (
    get_mongo_client, list_databases, create_database,
    insert_documents, list_collections, get_documents,
    delete_document, update_document
)
from utils.file_utils import (
    allowed_file, save_uploaded_file, read_file_preview,
    dataframe_to_json_records
)
from utils.validation import (
    validate_db_name, validate_collection_name,
    validate_json_payload, validate_document_structure
)
from utils.logger import app_logger
from utils.auth import (
    authenticate_user, get_user_by_username, check_user_permission,
    get_user_databases, create_default_user,
    authenticate_user_by_email, create_user_by_email, get_user_by_email,
    get_user_namespace
)

# ------------------------
# Basic config
# ------------------------
load_dotenv()  # load .env if present
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change_this_dev_secret")
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No expiration for CSRF tokens
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']  # Accept CSRF token from header

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Default to localhost for local dev, but allow Docker override via env
# If running in Docker, use: mongodb://mongo:27017/
# If running locally, use: mongodb://localhost:27017/
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
UPLOAD_FOLDER = os.path.join("static", "uploads")

# Legacy env vars for migration (will be deprecated)
DEMO_USER = os.environ.get("DEMO_USER", "admin")
DEMO_PASS = os.environ.get("DEMO_PASS", "password")

mongo_client = get_mongo_client(MONGO_URI)

# Initialize default admin user if it doesn't exist (only if MongoDB is accessible)
try:
    # Test connection first before trying to create user
    mongo_client.admin.command('ping')
    create_default_user(mongo_client, username=DEMO_USER, password=DEMO_PASS)
except Exception as e:
    # Log but don't fail startup - MongoDB might not be ready yet (especially in Docker)
    app_logger.warning(f"MongoDB connection issue (will retry on first request): {e}")

# ------------------------
# Decorators & Helpers
# ------------------------
def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("logged_in"):
                return jsonify({"error": "unauthorized", "message": "Please log in"}), 401
            
            user = get_user_by_username(mongo_client, session.get("username"))
            if not user:
                return jsonify({"error": "unauthorized", "message": "User not found"}), 401
            
            if not check_user_permission(user, permission):
                error_id = app_logger.warning(f"Permission denied: {session.get('username')} tried to {permission}")
                return jsonify({
                    "error": "forbidden",
                    "message": "You don't have permission to perform this action",
                    "error_id": error_id
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ------------------------
# Routes
# ------------------------
@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """API endpoint to get CSRF token for AJAX requests"""
    return jsonify({"csrf_token": generate_csrf()})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        # Authenticate against database by email
        user = authenticate_user_by_email(mongo_client, email, password)
        
        if user:
            session["logged_in"] = True
            session["email"] = user.get("email")
            session["username"] = user.get("username")  # optional legacy
            session["user_role"] = user.get("role", "user")
            session["user_permissions"] = user.get("permissions", {})
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        
        # Fallback to legacy env-based auth (for migration)
        if email == f"{DEMO_USER}@local" and password == DEMO_PASS:
            app_logger.warning("Using legacy env-based authentication (email format)")
            session["logged_in"] = True
            session["email"] = email
            session["username"] = DEMO_USER
            session["user_role"] = "admin"
            session["user_permissions"] = {"databases": "*", "collections": "*"}
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        
        app_logger.warning(f"Failed login attempt (email): {email}")
        flash("Invalid credentials.", "danger")
        return render_template("login.html")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        created = create_user_by_email(mongo_client, email, password)
        if not created:
            flash("Signup failed. Ensure email is valid/unique and password length ≥ 6.", "danger")
            return render_template("signup.html")
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    username = session.get("username")
    user = get_user_by_username(mongo_client, username)
    return render_template("dashboard.html", username=username, user=user)

# ------------------------
# Error Handlers
# ------------------------
@app.errorhandler(404)
def not_found(error):
    app_logger.warning(f"404 Not Found: {request.path}")
    return jsonify({"error": "Resource not found", "message": "The requested resource does not exist"}), 404

@app.errorhandler(500)
def internal_error(error):
    error_id = app_logger.exception("Internal server error occurred")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later.",
        "error_id": error_id
    }), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    error_id = app_logger.warning(f"CSRF validation failed: {request.path}")
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({
            "error": "csrf_error",
            "message": "CSRF token validation failed. Please refresh the page and try again.",
            "error_id": error_id
        }), 400
    flash("Security validation failed. Please try again.", "danger")
    return redirect(request.url or url_for("dashboard"))

def handle_mongo_error(e: Exception, operation: str):
    """Handle MongoDB errors gracefully"""
    error_id = app_logger.error(f"MongoDB error in {operation}", exc_info=e)
    
    if isinstance(e, OperationFailure):
        if "Authentication failed" in str(e):
            return jsonify({
                "error": "Authentication failed",
                "message": "Unable to connect to MongoDB. Please check your credentials.",
                "error_id": error_id
            }), 401
        elif "not authorized" in str(e).lower():
            return jsonify({
                "error": "Not authorized",
                "message": "You don't have permission to perform this operation.",
                "error_id": error_id
            }), 403
        else:
            return jsonify({
                "error": "Database operation failed",
                "message": str(e),
                "error_id": error_id
            }), 400
    
    if isinstance(e, PyMongoError):
        return jsonify({
            "error": "Database connection error",
            "message": "Unable to connect to MongoDB. Please check your connection settings.",
            "error_id": error_id
        }), 503
    
    return jsonify({
        "error": "Database error",
        "message": "An error occurred while accessing the database.",
        "error_id": error_id
    }), 500


# ------------------------
# API endpoints
# ------------------------
@app.route("/api/databases", methods=["GET"])
def api_list_databases():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    try:
        username = session.get("username")
        user = get_user_by_username(mongo_client, username)
        
        if user:
            # Filter databases based on user permissions
            dbs = get_user_databases(mongo_client, user)
        else:
            # Fallback: show all databases (legacy behavior)
            dbs = list_databases(mongo_client)
        
        app_logger.info(f"Database list retrieved for user: {username}")
        return jsonify({"databases": dbs})
    except Exception as e:
        return handle_mongo_error(e, "list_databases")


@app.route("/api/databases", methods=["POST"])
@permission_required("can_create_db")
def api_create_database():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("name")
    
    if not db_name:
        error_id = app_logger.warning("Database creation attempted without name")
        return jsonify({
            "error": "missing name",
            "message": "Database name is required",
            "error_id": error_id
        }), 400
    
    # Validate database name
    is_valid, error_msg = validate_db_name(db_name)
    if not is_valid:
        error_id = app_logger.warning(f"Invalid database name attempted: {db_name}")
        return jsonify({
            "error": "invalid_name",
            "message": error_msg,
            "error_id": error_id
        }), 400

    try:
        # Namespace prefix for isolation
        current_email = session.get("email") or session.get("username")
        ns = get_user_namespace(current_email)
        if not db_name.startswith(ns):
            db_name = f"{ns}{db_name}"
        create_database(mongo_client, db_name)
        db = mongo_client[db_name]
        if "init_collection" not in db.list_collection_names():
            db["init_collection"].insert_one({"initialized": True})
        app_logger.info(f"Database created successfully: {db_name}")
        return jsonify({"ok": True, "db": db_name, "message": "Database created successfully"})
    except Exception as e:
        return handle_mongo_error(e, "create_database")


# ------------------------
# Collections view (fixed Add/Delete)
# ------------------------
@app.route("/collections/<db_name>")
@login_required
def collections(db_name):
    # Validate DB name
    is_valid, error_msg = validate_db_name(db_name)
    if not is_valid:
        error_id = app_logger.warning(f"Invalid database name in URL: {db_name}")
        flash(f"Invalid database name: {error_msg}", "danger")
        return redirect(url_for("dashboard"))
    
    # Check user has access to this database
    user = get_user_by_email(mongo_client, session.get("email")) or get_user_by_username(mongo_client, session.get("username"))
    if user:
        user_dbs = get_user_databases(mongo_client, user)
        if db_name not in user_dbs:
            error_id = app_logger.warning(f"Access denied: {username} tried to access DB: {db_name}")
            flash("You don't have permission to access this database.", "danger")
            return redirect(url_for("dashboard"))
    
    try:
        collections = list_collections(mongo_client, db_name)
        return render_template("collections.html", db_name=db_name, collections=collections)
    except Exception as e:
        error_id = app_logger.error(f"Error listing collections for DB: {db_name}", exc_info=e)
        flash(f"Error accessing database: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

@app.route("/api/collection/add", methods=["POST"])
@permission_required("can_create_collection")
def api_add_collection():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Collection creation attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Both database name and collection name are required",
            "error_id": error_id
        }), 400
    
    # Validate names
    db_valid, db_msg = validate_db_name(db_name)
    if not db_valid:
        error_id = app_logger.warning(f"Invalid database name: {db_name}")
        return jsonify({"error": "invalid_db_name", "message": db_msg, "error_id": error_id}), 400
    
    coll_valid, coll_msg = validate_collection_name(collection_name)
    if not coll_valid:
        error_id = app_logger.warning(f"Invalid collection name: {collection_name}")
        return jsonify({"error": "invalid_collection_name", "message": coll_msg, "error_id": error_id}), 400
    
    try:
        db = mongo_client[db_name]
        db.create_collection(collection_name)
        app_logger.info(f"Collection created: {db_name}.{collection_name}")
        return jsonify({"ok": True, "collection": collection_name, "message": "Collection created successfully"})
    except Exception as e:
        return handle_mongo_error(e, "create_collection")

@app.route("/api/collection/delete", methods=["POST"])
@permission_required("can_delete_collection")
def api_delete_collection():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Collection deletion attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Both database name and collection name are required",
            "error_id": error_id
        }), 400
    
    try:
        db = mongo_client[db_name]
        db.drop_collection(collection_name)
        app_logger.info(f"Collection deleted: {db_name}.{collection_name}")
        return jsonify({"ok": True, "deleted": collection_name, "message": "Collection deleted successfully"})
    except Exception as e:
        return handle_mongo_error(e, "delete_collection")


# ------------------------
# API Aliases & Helpers for collections
# ------------------------
@app.route("/api/collection/create", methods=["POST"])
@permission_required("can_create_collection")
def api_collection_create_alias():
    """Alias to keep frontend JS simpler; mirrors /api/collection/add"""
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Collection creation attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Both database name and collection name are required",
            "error_id": error_id
        }), 400
    
    # Validate names
    db_valid, db_msg = validate_db_name(db_name)
    if not db_valid:
        error_id = app_logger.warning(f"Invalid database name: {db_name}")
        return jsonify({"error": "invalid_db_name", "message": db_msg, "error_id": error_id}), 400
    
    coll_valid, coll_msg = validate_collection_name(collection_name)
    if not coll_valid:
        error_id = app_logger.warning(f"Invalid collection name: {collection_name}")
        return jsonify({"error": "invalid_collection_name", "message": coll_msg, "error_id": error_id}), 400
    
    try:
        db = mongo_client[db_name]
        db.create_collection(collection_name)
        app_logger.info(f"Collection created: {db_name}.{collection_name}")
        return jsonify({"ok": True, "collection": collection_name, "message": "Collection created successfully"})
    except Exception as e:
        return handle_mongo_error(e, "create_collection")


@app.route("/api/collections/<db_name>", methods=["GET"])
def api_list_collections_json(db_name):
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    # Validate DB name
    is_valid, error_msg = validate_db_name(db_name)
    if not is_valid:
        error_id = app_logger.warning(f"Invalid database name in API: {db_name}")
        return jsonify({"error": "invalid_db_name", "message": error_msg, "error_id": error_id}), 400
    
    try:
        cols = list_collections(mongo_client, db_name)
        return jsonify({"collections": cols})
    except Exception as e:
        return handle_mongo_error(e, "list_collections")


# ------------------------
# Upload Excel/CSV + Import
# ------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files.get("file")
        db_name = request.form.get("db_name")
        collection_name = request.form.get("collection_name")

        if not (file and allowed_file(file.filename)):
            flash("Please upload a valid Excel or CSV file.", "danger")
            return redirect(url_for("upload"))

        path = save_uploaded_file(file, UPLOAD_FOLDER)
        headers, preview, df = read_file_preview(path)

        if "preview" in request.form:
            return render_template(
                "upload.html",
                headers=headers,
                preview=preview,
                db_name=db_name,
                collection_name=collection_name,
                file_path=path
            )

        if "import" in request.form:
            file_path = request.form.get("file_path")
            headers, preview, df = read_file_preview(file_path)
            records = dataframe_to_json_records(df)
            inserted = insert_documents(mongo_client, db_name, collection_name, records)
            flash(f"Inserted {inserted} documents into {db_name}.{collection_name}", "success")
            return redirect(url_for("dashboard"))

    dbs = list_databases(mongo_client)
    return render_template("upload.html", databases=dbs)


# ------------------------
# Data View + CRUD + Pagination + Refresh
# ------------------------
@app.route("/data/<db_name>/<collection_name>")
def data_view(db_name, collection_name):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    # Validate names
    db_valid, db_msg = validate_db_name(db_name)
    if not db_valid:
        error_id = app_logger.warning(f"Invalid database name in URL: {db_name}")
        flash(f"Invalid database name: {db_msg}", "danger")
        return redirect(url_for("dashboard"))
    
    coll_valid, coll_msg = validate_collection_name(collection_name)
    if not coll_valid:
        error_id = app_logger.warning(f"Invalid collection name in URL: {collection_name}")
        flash(f"Invalid collection name: {coll_msg}", "danger")
        return redirect(url_for("collections", db_name=db_name))

    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        skip = (page - 1) * limit

        docs = list(mongo_client[db_name][collection_name].find({}, {"_id": 0}).skip(skip).limit(limit))
        total = mongo_client[db_name][collection_name].count_documents({})

        return render_template(
            "data_view.html",
            db_name=db_name,
            collection_name=collection_name,
            documents=docs,
            page=page,
            limit=limit,
            total=total
        )
    except Exception as e:
        error_id = app_logger.error(f"Error accessing collection: {db_name}.{collection_name}", exc_info=e)
        flash(f"Error accessing collection: {str(e)}", "danger")
        return redirect(url_for("collections", db_name=db_name))

@app.route("/api/document/delete", methods=["POST"])
def api_delete_document():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    query = payload.get("query", {})
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Document deletion attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Database name and collection name are required",
            "error_id": error_id
        }), 400
    
    if not query:
        error_id = app_logger.warning("Document deletion attempted without query")
        return jsonify({
            "error": "missing_query",
            "message": "Delete query is required",
            "error_id": error_id
        }), 400
    
    try:
        deleted = delete_document(mongo_client, db_name, collection_name, query)
        app_logger.info(f"Document deleted: {db_name}.{collection_name} ({deleted} deleted)")
        return jsonify({"deleted": deleted, "message": f"Deleted {deleted} document(s)"})
    except Exception as e:
        return handle_mongo_error(e, "delete_document")

@app.route("/api/document/update", methods=["POST"])
def api_update_document():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    query = payload.get("query", {})
    new_values = payload.get("new_values", {})
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Document update attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Database name and collection name are required",
            "error_id": error_id
        }), 400
    
    if not query:
        error_id = app_logger.warning("Document update attempted without query")
        return jsonify({
            "error": "missing_query",
            "message": "Update query is required",
            "error_id": error_id
        }), 400
    
    if not new_values:
        error_id = app_logger.warning("Document update attempted with empty update values")
        return jsonify({
            "error": "empty_update",
            "message": "Update values cannot be empty",
            "error_id": error_id
        }), 400
    
    # Never allow updating immutable _id
    if isinstance(new_values, dict) and "_id" in new_values:
        try:
            new_values.pop("_id")
        except Exception:
            pass
    
    try:
        modified = update_document(mongo_client, db_name, collection_name, query, new_values)
        app_logger.info(f"Document updated: {db_name}.{collection_name} ({modified} modified)")
        return jsonify({"modified": modified, "message": f"Updated {modified} document(s)"})
    except Exception as e:
        return handle_mongo_error(e, "update_document")

@app.route("/api/document/add", methods=["POST"])
def api_add_document():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    payload = request.json or {}
    db_name = payload.get("db")
    collection_name = payload.get("collection")
    doc = payload.get("doc", {})
    
    if not (db_name and collection_name):
        error_id = app_logger.warning("Document insertion attempted with missing parameters")
        return jsonify({
            "error": "missing_parameters",
            "message": "Database name and collection name are required",
            "error_id": error_id
        }), 400
    
    if not doc:
        error_id = app_logger.warning("Document insertion attempted with empty document")
        return jsonify({
            "error": "empty_document",
            "message": "Document cannot be empty",
            "error_id": error_id
        }), 400
    
    # Validate document structure
    is_valid, error_msg = validate_document_structure(doc)
    if not is_valid:
        error_id = app_logger.warning(f"Invalid document structure: {error_msg}")
        return jsonify({
            "error": "invalid_document",
            "message": error_msg,
            "error_id": error_id
        }), 400
    
    try:
        db = mongo_client[db_name]
        result = db[collection_name].insert_one(doc)
        app_logger.info(f"Document inserted: {db_name}.{collection_name}")
        return jsonify({"inserted_id": str(result.inserted_id), "message": "Document inserted successfully"})
    except Exception as e:
        return handle_mongo_error(e, "insert_document")

@app.route("/api/data/refresh", methods=["GET"])
def api_data_refresh():
    """AJAX inline refresh for data table"""
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 401
    db_name = request.args.get("db")
    collection = request.args.get("collection")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    skip = (page - 1) * limit

    docs = list(mongo_client[db_name][collection].find({}, {"_id": 0}).skip(skip).limit(limit))
    total = mongo_client[db_name][collection].count_documents({})
    return jsonify({"documents": docs, "total": total})

@app.route("/api/data/<db_name>/<collection_name>", methods=["GET"])
def api_get_collection_data(db_name, collection_name):
    """Paginated JSON endpoint for fetching documents in a collection"""
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized", "message": "Please log in to access this resource"}), 401
    
    # Validate names
    db_valid, db_msg = validate_db_name(db_name)
    if not db_valid:
        error_id = app_logger.warning(f"Invalid database name in API: {db_name}")
        return jsonify({"error": "invalid_db_name", "message": db_msg, "error_id": error_id}), 400
    
    coll_valid, coll_msg = validate_collection_name(collection_name)
    if not coll_valid:
        error_id = app_logger.warning(f"Invalid collection name in API: {collection_name}")
        return jsonify({"error": "invalid_collection_name", "message": coll_msg, "error_id": error_id}), 400

    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10
        
        skip = (page - 1) * limit

        db = mongo_client[db_name]
        collection = db[collection_name]

        total = collection.count_documents({})
        docs = list(collection.find().skip(skip).limit(limit))

        # Convert ObjectId to string
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return jsonify({
            "docs": docs,
            "total": total,
            "page": page,
            "limit": limit
        }), 200

    except Exception as e:
        return handle_mongo_error(e, "get_collection_data")


# ------------------------
# Export collection to CSV
# ------------------------
@app.route("/api/export/<db_name>/<collection_name>", methods=["GET"])
def api_export_collection_csv(db_name, collection_name):
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 401
    try:
        docs = list(mongo_client[db_name][collection_name].find())
        # Convert ObjectId to string for CSV export
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        df = pd.DataFrame(docs)
        buf = BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        filename = f"{db_name}_{collection_name}.csv"
        return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------
# Diagnostics
# ------------------------
@app.route("/api/info", methods=["GET"])
def api_info():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 401
    try:
        # ping server
        mongo_client.admin.command("ping")
        # mask credentials if present
        uri = MONGO_URI
        masked = uri
        if "@" in uri and "://" in uri:
            scheme, rest = uri.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                masked = f"{scheme}://***:***@{host}"
        return jsonify({
            "ok": True,
            "mongo_uri": masked,
            "databases": list_databases(mongo_client)
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ------------------------
# Run
# ------------------------
if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)

# ------------------------
# Metrics API (placed above run in real app; kept functional here)
# ------------------------

@app.route("/api/metrics/overview", methods=["GET"])
def api_metrics_overview():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 401
    try:
        # Determine current user and namespace filtering
        user = get_user_by_email(mongo_client, session.get("email")) or get_user_by_username(mongo_client, session.get("username"))
        db_names = get_user_databases(mongo_client, user) if user else list_databases(mongo_client)

        overview = []
        total_collections = 0
        total_documents = 0
        for db_name in db_names:
            try:
                cols = mongo_client[db_name].list_collection_names()
            except Exception:
                cols = []
            num_cols = len(cols)
            total_collections += num_cols
            db_docs = 0
            for c in cols:
                try:
                    db_docs += mongo_client[db_name][c].count_documents({})
                except Exception:
                    pass
            total_documents += db_docs
            overview.append({
                "db": db_name,
                "collections": num_cols,
                "documents": db_docs
            })

        data = {
            "databases": len(db_names),
            "collections": total_collections,
            "documents": total_documents,
            "per_db": overview
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
