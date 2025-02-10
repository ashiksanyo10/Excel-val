import pandas as pd
import re
import json
from pathlib import Path

def validate_file(file_path):
    # Determine file type and read file
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == '.xlsx':
            df = pd.read_excel(file_path, dtype=str)
        elif file_extension == '.csv':
            df = pd.read_csv(file_path, dtype=str, encoding='utf-8', errors='ignore')
        else:
            return {"error": "Unsupported file format. Only .xlsx and .csv are allowed."}
    except Exception as e:
        return {"error": str(e)}

    # Initialize dictionary for errors
    validation_results = {
        "errors": {
            "blank_cells": [],
            "non_english_characters": [],
            "duplicate_gti": [],
            "invalid_country_language": [],
            "invalid_age_rating": [],
            "invalid_date_format": []
        }
    }

    # Rule 1: Check for blank cells (except "Other Title Name(s)")
    columns_to_check = [col for col in df.columns if col != "Other Title Name(s)"]
    blank_cells = df[columns_to_check].isnull().any(axis=1)
    if blank_cells.any():
        for row in df[blank_cells].index:
            missing_columns = df.columns[df.loc[row].isnull()].tolist()
            validation_results["errors"]["blank_cells"].append({
                "row": row + 2,
                "columns": missing_columns
            })

    # Rule 2: Check for non-English characters
    non_english_mask = df.applymap(lambda x: re.findall(r'[^\x00-\x7F]', str(x)) if pd.notna(x) else [])
    for index, row in non_english_mask.iterrows():
        for col, non_english_chars in row.items():
            if non_english_chars:
                validation_results["errors"]["non_english_characters"].append({
                    "row": index + 2,
                    "column": col,
                    "invalid_chars": ''.join(non_english_chars)
                })

    # Rule 3: Check for duplicate GTI values
    if "GTI" in df.columns:
        duplicate_gtis = df[df.duplicated('GTI', keep=False)]
        for gti in duplicate_gtis['GTI'].unique():
            duplicate_rows = df.index[df['GTI'] == gti].tolist()
            validation_results["errors"]["duplicate_gti"].append({
                "GTI": gti,
                "rows": [row + 2 for row in duplicate_rows]
            })

    # Rule 4: Validate Country and Language columns
    if "Countries" in df.columns and "Languages" in df.columns:
        invalid_rows = df[~df["Countries"].str.isdigit() | ~df["Languages"].str.isdigit()].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_country_language"].append({
                "row": row + 2,
                "Countries": df.at[row, "Countries"],
                "Languages": df.at[row, "Languages"]
            })

    # Rule 5: Validate Age Rating ID
    if "Age Rating ID" in df.columns:
        valid_age_ratings = {"2", "9", "154", "147"}
        invalid_rows = df[~df["Age Rating ID"].isin(valid_age_ratings)].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_age_rating"].append({
                "row": row + 2,
                "Age Rating ID": df.at[row, "Age Rating ID"]
            })

    # Rule 6: Validate Date format
    if "Rating Date" in df.columns:
        date_format = re.compile(r'^\d{2}/\d{2}/\d{4}$')
        invalid_rows = df[~df["Rating Date"].astype(str).str.match(date_format)].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_date_format"].append({
                "row": row + 2,
                "Rating Date": df.at[row, "Rating Date"]
            })

    return validation_results
