from flask import Flask, request, jsonify, render_template
import pandas as pd
import re
import os
from werkzeug.utils import secure_filename
from pathlib import Path

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper Function: Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to Validate File
def validate_file(file_path):
    file_extension = Path(file_path).suffix.lower()

    # Load the file
    if file_extension == '.xlsx':
        df = pd.read_excel(file_path, dtype=str)
    elif file_extension == '.csv':
        df = pd.read_csv(file_path, dtype=str, encoding='latin1', errors='replace')
    else:
        return {"error": "Unsupported file format. Only .xlsx and .csv are supported."}

    validation_results = {
        'blank_cells': [],
        'non_english_chars': [],
        'duplicate_gtis': [],
        'invalid_country_language': [],
        'invalid_age_rating': [],
        'invalid_date_format': []
    }

    # Rule 1: Check for Blank Cells
    blank_cells = df.isnull().any(axis=1)
    if blank_cells.any():
        blank_rows = df[blank_cells].index.tolist()
        blank_columns = df.columns[df.isnull().any()].tolist()
        validation_results['blank_cells'] = [{'row': row + 2, 'columns': blank_columns} for row in blank_rows]

    # Rule 2: Detect Non-English Characters
    def find_non_english_chars(text):
        return ''.join(re.findall(r'[^\x00-\x7F]', str(text)))  # Extract non-English characters

    non_english_mask = df.apply(lambda col: col.map(lambda x: find_non_english_chars(x) if pd.notna(x) else ""))
    non_english_rows = df[non_english_mask.apply(lambda x: x.str.len() > 0, axis=1)].index.tolist()
    
    for row in non_english_rows:
        invalid_columns = df.columns[non_english_mask.loc[row] != ""].tolist()
        for col in invalid_columns:
            validation_results['non_english_chars'].append({
                'row': row + 2,
                'column': col,
                'value': str(df.at[row, col]),
                'invalid_chars': non_english_mask.at[row, col]
            })

    # Rule 3: Flag Duplicate GTI and Show All Locations
    if 'GTI' in df.columns:
        duplicate_gtis = df[df.duplicated('GTI', keep=False)]
        if not duplicate_gtis.empty:
            for gti in duplicate_gtis['GTI'].unique():
                duplicate_rows = df.index[df['GTI'] == gti].tolist()
                validation_results['duplicate_gtis'].append({'GTI': str(gti), 'rows': [row + 2 for row in duplicate_rows]})

    # Rule 4: Validate Country & Language
    if 'Countries' in df.columns and 'Languages' in df.columns:
        invalid_country_language_mask = ~(df['Countries'].str.isdigit() & df['Languages'].str.isdigit())
        invalid_country_language_rows = df[invalid_country_language_mask].index.tolist()
        for row in invalid_country_language_rows:
            validation_results['invalid_country_language'].append({
                'row': row + 2,
                'Countries': str(df.at[row, 'Countries']),
                'Languages': str(df.at[row, 'Languages'])
            })

    # Rule 5: Validate Age Rating ID
    if 'Age Rating ID' in df.columns:
        valid_age_ratings = {"2", "9", "154", "147"}
        invalid_age_rating_mask = ~df['Age Rating ID'].isin(valid_age_ratings)
        invalid_age_rating_rows = df[invalid_age_rating_mask].index.tolist()
        for row in invalid_age_rating_rows:
            validation_results['invalid_age_rating'].append({
                'row': row + 2,
                'Age Rating ID': str(df.at[row, 'Age Rating ID'])
            })

    # Rule 6: Validate Date Format
    if 'Rating Date' in df.columns:
        date_format = re.compile(r'^\d{2}/\d{2}/\d{4}$')
        df['Rating Date'] = df['Rating Date'].astype(str)
        invalid_date_mask = ~df['Rating Date'].str.match(date_format, na=False)
        invalid_date_rows = df[invalid_date_mask].index.tolist()
        for row in invalid_date_rows:
            validation_results['invalid_date_format'].append({
                'row': row + 2,
                'Rating Date': str(df.at[row, 'Rating Date'])
            })

    return validation_results

# Flask Route: Upload & Validate File
@app.route('/', methods=['GET'])
def index():
    return render_template('upload.html')

@app.route('/validate', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        results = validate_file(filepath)
        return jsonify(results)

    return jsonify({"error": "Invalid file type"}), 400

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
