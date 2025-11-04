# MongoDB Manager - Web Application

A user-friendly web application for managing MongoDB databases, designed for non-technical users to easily create, manage, and interact with NoSQL databases through an intuitive web interface.

## 🚀 Features

### Core Functionality
- **Database Management**: Create, list, and manage MongoDB databases
- **Collection Management**: Add and delete collections with real-time updates
- **Document CRUD**: Create, read, update, and delete documents with a user-friendly interface
- **File Import**: Upload Excel (XLSX) or CSV files and automatically convert them to MongoDB collections
- **Data Export**: Export collections to CSV format
- **Pagination**: Efficient browsing of large datasets with prev/next navigation
- **Real-time Updates**: AJAX-powered interface with live data refresh

### Security & Authentication
- **Email-based Authentication**: Secure signup and login system
- **User Isolation**: Each user gets their own namespace, ensuring data privacy
- **CSRF Protection**: All forms and API endpoints protected against CSRF attacks
- **Password Hashing**: Secure password storage using Werkzeug
- **Role-based Access Control**: Admin and user roles with granular permissions

### UI/UX Features
- **Dashboard Metrics**: Real-time statistics showing databases, collections, and documents count
- **Interactive Charts**: Visual representation of documents per database using Chart.js
- **Toast Notifications**: Non-intrusive success/error notifications
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Bootstrap 5**: Modern, clean interface

### Technical Features
- **Structured Logging**: Comprehensive error tracking with unique error IDs
- **Input Validation**: Client and server-side validation for all operations
- **Error Handling**: Graceful error handling with user-friendly messages
- **Docker Support**: Full containerization with Docker Compose
- **Production Ready**: Gunicorn + Nginx setup for production deployment

## 📋 Prerequisites

### For Local Development
- Python 3.11 or higher
- MongoDB Community Server (local installation)
- pip (Python package manager)
- Virtual environment (venv)

### For Docker Deployment
- Docker Desktop (or Docker + Docker Compose)
- Git

## 🛠️ Installation & Setup

### Option 1: Docker Deployment (Recommended)

#### Quick Start
```bash
# 1. Clone the repository
git clone <your-repo-url>
cd mongo_db_manager

# 2. (Optional) Create .env file with custom settings
cp ENV_EXAMPLE.txt .env
# Edit .env if needed

# 3. Build and start all services
docker compose up -d --build

# 4. Access the application
# Open http://localhost:8080 in your browser
```

#### Docker Services
- **Web App**: Flask application running on Gunicorn (port 8000 internally)
- **Nginx**: Reverse proxy and static file server (port 8080)
- **MongoDB**: Database server (port 27017)

#### Useful Docker Commands
```bash
# View logs
docker compose logs -f web      # Application logs
docker compose logs -f nginx    # Nginx logs
docker compose logs -f mongo    # MongoDB logs

# Check container status
docker compose ps

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v

# Restart services
docker compose restart
```

### Option 2: Local Development

#### Step 1: Install MongoDB
```bash
# macOS (using Homebrew)
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0

# Verify MongoDB is running
mongosh mongodb://localhost:27017
```

#### Step 2: Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv env1

# Activate virtual environment
# macOS/Linux:
source env1/bin/activate
# Windows:
# env1\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment (Optional)
```bash
# Create .env file
cp ENV_EXAMPLE.txt .env

# Edit .env with your settings:
# FLASK_SECRET_KEY=your-secret-key-here
# MONGO_URI=mongodb://localhost:27017/
```

#### Step 4: Run the Application

**Development Mode:**
```bash
python app.py
# App runs on http://127.0.0.1:5000
```

**Production Mode (with Gunicorn):**
```bash
gunicorn -c gunicorn.conf.py app:app
# App runs on http://127.0.0.1:8000
```

## 📖 Usage Guide

### First Time Setup

1. **Start the Application** (Docker or local)
2. **Access the Login Page**: Navigate to http://localhost:8080 (Docker) or http://localhost:5000 (local dev)
3. **Create an Account**: Click "Create an account" and sign up with your email and password
4. **Login**: Use your email and password to log in

### Creating Databases

1. From the dashboard, enter a database name in the input field
2. Click "Create DB"
3. Your database will be automatically namespaced (e.g., `ns_your_email_com__mydb`)

### Uploading Data from Excel/CSV

1. Click "Upload" in the navigation
2. Select your database from the dropdown
3. Enter a collection name
4. Choose your Excel (.xlsx) or CSV file
5. Click "Preview" to see the data before importing
6. Click "Import to MongoDB" to complete the import

### Managing Collections

1. Click on a database from the dashboard
2. View all collections in that database
3. Click "Add Collection" to create a new collection
4. Click "Open" to view/edit documents in a collection
5. Click "Delete" to remove a collection (⚠️ This action cannot be undone)

### Working with Documents

1. Navigate to a collection
2. **Add Document**: Click "Add Document" and enter JSON data
3. **Edit Document**: Click the edit (✏️) button on any row
4. **Delete Document**: Click the delete (🗑️) button
5. **Export**: Click "Export CSV" to download the collection as CSV

### User Isolation

- Each user's databases are automatically prefixed with their email namespace
- Users can only see and manage databases they created
- Admin users have access to all databases

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

# MongoDB Connection
MONGO_URI=mongodb://localhost:27017/        # For local
# MONGO_URI=mongodb://mongo:27017/          # For Docker Compose

# Legacy Demo User (for migration)
DEMO_USER=admin
DEMO_PASS=password
```

### MongoDB Connection

- **Local Development**: `mongodb://localhost:27017/`
- **Docker Compose**: `mongodb://mongo:27017/`
- **MongoDB Atlas**: `mongodb+srv://username:password@cluster.mongodb.net/`

### Gunicorn Configuration

Edit `gunicorn.conf.py` to adjust:
- Number of workers
- Threads per worker
- Timeout settings
- Logging configuration

## 📁 Project Structure

```
mongo_db_manager/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── gunicorn.conf.py      # Gunicorn configuration
├── docker-compose.yml    # Docker Compose setup
├── Dockerfile            # Docker image definition
├── .gitignore            # Git ignore rules
├── README.md             # This file
│
├── utils/                # Utility modules
│   ├── mongo_utils.py    # MongoDB operations
│   ├── file_utils.py     # File handling (Excel/CSV)
│   ├── validation.py     # Input validation
│   ├── auth.py           # Authentication & authorization
│   └── logger.py         # Structured logging
│
├── templates/            # Jinja2 templates
│   ├── base.html         # Base template
│   ├── login.html        # Login page
│   ├── signup.html       # Signup page
│   ├── dashboard.html    # Main dashboard
│   ├── collections.html  # Collections view
│   ├── data_view.html    # Document viewer/editor
│   └── upload.html       # File upload page
│
├── static/               # Static files
│   ├── css/
│   │   └── style.css     # Custom styles
│   ├── js/
│   │   ├── main.js       # Global utilities
│   │   ├── collection.js # Collection management
│   │   └── data_view.js  # Data view operations
│   └── uploads/          # Uploaded files storage
│
└── nginx/                # Nginx configuration
    └── default.conf      # Nginx reverse proxy config
```

## 🔐 Security Features

### Authentication
- Email-based user accounts
- Secure password hashing (Werkzeug)
- Session management
- CSRF protection on all forms

### Authorization
- User namespace isolation
- Role-based access control (admin/user)
- Permission checks on all operations
- Database-level access filtering

### Best Practices
- Input validation (client & server)
- SQL injection prevention (parameterized queries)
- XSS protection (Jinja2 auto-escaping)
- Secure file uploads (validation & sanitization)

## 🐛 Troubleshooting

### Common Issues

#### 502 Bad Gateway (Docker)
```bash
# Check if web container is running
docker compose ps

# Check web container logs
docker compose logs web

# Restart containers
docker compose restart
```

#### MongoDB Connection Failed
```bash
# Verify MongoDB is running
# Local: mongosh mongodb://localhost:27017
# Docker: docker compose logs mongo

# Check MONGO_URI in .env or docker-compose.yml
```

#### Module Not Found Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or rebuild Docker image
docker compose build --no-cache web
```

#### Port Already in Use
```bash
# Change ports in docker-compose.yml
# Or stop conflicting services
lsof -ti:8080 | xargs kill  # macOS/Linux
```

## 📊 API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /signup` - Signup page
- `POST /signup` - Create new user
- `GET /logout` - Logout user

### Databases
- `GET /api/databases` - List all databases (filtered by user)
- `POST /api/databases` - Create new database
- `GET /api/info` - Connection info and database list

### Collections
- `GET /collections/<db_name>` - View collections page
- `GET /api/collections/<db_name>` - List collections (JSON)
- `POST /api/collection/create` - Create collection
- `POST /api/collection/delete` - Delete collection

### Documents
- `GET /data/<db_name>/<collection_name>` - View documents
- `GET /api/data/<db_name>/<collection_name>` - Get documents (paginated)
- `POST /api/document/add` - Insert document
- `POST /api/document/update` - Update document
- `POST /api/document/delete` - Delete document
- `GET /api/export/<db_name>/<collection_name>` - Export to CSV

### Metrics
- `GET /api/metrics/overview` - Dashboard statistics

## 🧪 Testing

### Manual Testing Checklist
- [ ] Sign up with new email
- [ ] Login with credentials
- [ ] Create a database
- [ ] Create a collection
- [ ] Upload Excel/CSV file
- [ ] View documents with pagination
- [ ] Add/edit/delete documents
- [ ] Export collection to CSV
- [ ] Verify user isolation (multiple users)

## 📝 License

This project is open source and available for personal and commercial use.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub.

## 🎯 Roadmap

- [ ] Multi-user collaboration (shared databases)
- [ ] Advanced query builder
- [ ] Data visualization (charts/graphs)
- [ ] Backup and restore functionality
- [ ] API authentication tokens
- [ ] Real-time collaboration
- [ ] Advanced search and filtering

## 🙏 Acknowledgments

- Built with Flask, MongoDB, and Bootstrap
- Icons and UI elements from Bootstrap 5
- Charts powered by Chart.js

---

**Happy Database Managing!** 🎉

