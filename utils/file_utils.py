import os
import pandas as pd
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    """Save uploaded file safely and return the saved path"""
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    path = os.path.join(upload_folder, filename)
    file.save(path)
    return path

def read_file_preview(file_path, max_rows=10):
    """Read Excel or CSV and return a preview (list of dicts) + headers"""
    ext = file_path.rsplit(".", 1)[1].lower()
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(file_path)
    elif ext == "csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file type")
    preview = df.head(max_rows).to_dict(orient="records")
    headers = list(df.columns)
    return headers, preview, df

def dataframe_to_json_records(df):
    """Convert a pandas DataFrame to list of dicts for MongoDB insertion"""
    return df.to_dict(orient="records")
