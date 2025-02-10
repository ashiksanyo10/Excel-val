import pandas as pd
import re
import json
from pathlib import Path

def validate_file(file_path):
    # Determine the file type
    file_extension = Path(file_path).suffix.lower()

    # Load the file based on its type
    if file_extension == '.xlsx':
        df = pd.read_excel(file_path, dtype=str)  # Read as strings to avoid dtype issues
    elif file_extension == '.csv':
        df = pd.read_csv(file_path, dtype=str)  # Read as strings
    else:
        raise ValueError("Unsupported file format. Only .xlsx and .csv are supported.")

    # Initialize a dictionary to hold validation results
    validation_results = {
        'blank_cells': [],
        'non_english_chars': [],
        'duplicate_gtis': [],
        'invalid_country_language': [],
        'invalid_age_rating': [],
        'invalid_date_format': []
    }

    # Rule 1: Check for blank cells (vectorized)
    blank_cells = df.isnull().any(axis=1)
    if blank_cells.any():
        blank_rows = df[blank_cells].index.tolist()
        blank_columns = df.columns[df.isnull().any()].tolist()
        validation_results['blank_cells'] = [{'row': row + 2, 'columns': blank_columns} for row in blank_rows]

    # Rule 2: Check for non-English characters (vectorized)
    non_english_mask = df.applymap(lambda x: bool(re.match(r'^[A-Za-z0-9\s.,!?;:\'"-]*$', str(x))) if pd.notna(x) else True)
    non_english_rows = df[~non_english_mask.all(axis=1)].index.tolist()
    for row in non_english_rows:
        invalid_columns = df.columns[~non_english_mask.loc[row]].tolist()
        for col in invalid_columns:
            validation_results['non_english_chars'].append({'row': row + 2, 'column': col, 'value': str(df.at[row, col])})

    # Rule 3: Flag duplicate GTI (vectorized)
    duplicate_gtis = df[df.duplicated('GTI', keep=False)]
    if not duplicate_gtis.empty:
        for gti in duplicate_gtis['GTI'].unique():
            duplicate_rows = df.index[df['GTI'] == gti].tolist()
            validation_results['duplicate_gtis'].append({'GTI': str(gti), 'rows': [row + 2 for row in duplicate_rows]})

    # Rule 4: Validate Country and Language are numerical and not empty (vectorized)
    invalid_country_language_mask = ~(df['Countries'].str.isdigit() & df['Languages'].str.isdigit())
    invalid_country_language_rows = df[invalid_country_language_mask].index.tolist()
    for row in invalid_country_language_rows:
        validation_results['invalid_country_language'].append({'row': row + 2, 'Countries': str(df.at[row, 'Countries']), 'Languages': str(df.at[row, 'Languages'])})

    # Rule 5: Validate Age Rating ID (vectorized)
    valid_age_ratings = {"2", "9", "154", "147"}
    invalid_age_rating_mask = ~df['Age Rating ID'].isin(valid_age_ratings)
    invalid_age_rating_rows = df[invalid_age_rating_mask].index.tolist()
    for row in invalid_age_rating_rows:
        validation_results['invalid_age_rating'].append({'row': row + 2, 'Age Rating ID': str(df.at[row, 'Age Rating ID'])})

    # Rule 6: Validate Date format (vectorized)
    date_format = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    df['Rating Date'] = df['Rating Date'].astype(str)  # Convert to string to prevent Timestamp error
    invalid_date_mask = ~df['Rating Date'].str.match(date_format, na=False)
    invalid_date_rows = df[invalid_date_mask].index.tolist()
    for row in invalid_date_rows:
        validation_results['invalid_date_format'].append({'row': row + 2, 'Rating Date': str(df.at[row, 'Rating Date'])})

    return validation_results

# Example usage
file_path = input("Enter the path to your file (either .xlsx or .csv): ")
results = validate_file(file_path)
print(json.dumps(results, indent=4))
