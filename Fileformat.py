import pandas as pd
import os

def load_file(file_path):
    """Load an Excel (.xlsx) or CSV (.csv) file into a Pandas DataFrame."""
    ext = os.path.splitext(file_path)[-1].lower()  # Extract file extension
    
    if ext == ".xlsx":
        df = pd.read_excel(file_path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(file_path, dtype=str)  # Ensure all data is read as strings
    else:
        raise ValueError("Invalid file format. Only .xlsx and .csv are supported.")
    
    return df
