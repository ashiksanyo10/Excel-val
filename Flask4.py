import pandas as pd
import re
import json
from pathlib import Path

def validate_file(file_path):
    # Determine the file type
    file_extension = Path(file_path).suffix.lower()

    # Load the file based on its type
    if file_extension == ".xlsx":
        df = pd.read_excel(file_path)
    elif file_extension == ".csv":
        df = pd.read_csv(file_path, encoding_errors="ignore")  # Handle encoding issues
    else:
        raise ValueError("Unsupported file format. Only .xlsx and .csv are supported.")

    validation_results = {
        "errors": {
            "blank_cells": [],
            "non_english_chars": [],
            "duplicate_gtis": [],
            "invalid_country_language": [],
            "invalid_age_rating": [],
            "invalid_date_format": [],
            "missing_content_descriptors": []
        }
    }

    # Content descriptor columns
    content_descriptor_columns = [
        "Violence Impact", "Drug Use Impact", "Themes Impact",
        "Language Impact", "Nudity Impact", "Sex Impact"
    ]

    # Rule 1: Blank Cells (excluding "Other Title Name(s)" and handling content descriptors separately)
    columns_to_check = [col for col in df.columns if col != "Other Title Name(s)"]
    blank_cells = df[columns_to_check].apply(lambda x: x.isnull() | (x == ""))

    for row in df[blank_cells.any(axis=1)].index:
        missing_columns = [col for col in df.columns if blank_cells.at[row, col]]

        # Remove content descriptors from this check (they have their own rule)
        missing_columns = [col for col in missing_columns if col not in content_descriptor_columns]

        if missing_columns:
            validation_results["errors"]["blank_cells"].append({
                "row": row + 2,
                "columns": missing_columns
            })

    # Rule 2: Content Descriptors Must Be Present (Can be "None" but not blank)
    for row in df.index:
        missing_descriptors = [
            col for col in content_descriptor_columns 
            if pd.isna(df.at[row, col]) or df.at[row, col] == ""
        ]
        if missing_descriptors:
            validation_results["errors"]["missing_content_descriptors"].append({
                "row": row + 2,
                "columns": missing_descriptors
            })

    # Rule 3: Detect Non-English Characters
    non_english_mask = df.map(lambda x: bool(re.search(r"[^\x00-\x7F]", str(x))) if pd.notna(x) else False)

    for row in df[non_english_mask.any(axis=1)].index:
        invalid_columns = [col for col in df.columns if non_english_mask.at[row, col]]
        for col in invalid_columns:
            validation_results["errors"]["non_english_chars"].append({
                "row": row + 2,
                "column": col,
                "value": df.at[row, col]
            })

    # Rule 4: Flag Duplicate GTI with Row Numbers and Values
    if "GTI" in df.columns:
        duplicate_gtis = df[df.duplicated("GTI", keep=False)]
        if not duplicate_gtis.empty:
            for gti in duplicate_gtis["GTI"].unique():
                duplicate_rows = df.index[df["GTI"] == gti].tolist()
                validation_results["errors"]["duplicate_gtis"].append({
                    "GTI": gti,
                    "rows": [row + 2 for row in duplicate_rows],
                    "values": df.loc[duplicate_rows, "GTI"].tolist()
                })

    # Rule 5: Validate Country and Language (Handle NaN properly)
    if "Countries" in df.columns and "Languages" in df.columns:
        invalid_country_language_mask = ~(df["Countries"].fillna("").astype(str).str.isnumeric() & df["Languages"].fillna("").astype(str).str.isnumeric())
        invalid_rows = df[invalid_country_language_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_country_language"].append({
                "row": row + 2,
                "Countries": df.at[row, "Countries"],
                "Languages": df.at[row, "Languages"]
            })

    # Rule 6: Validate Age Rating ID (Handle NaN properly)
    if "Age Rating ID" in df.columns:
        valid_age_ratings = {2, 9, 154, 147}
        invalid_age_rating_mask = ~df["Age Rating ID"].fillna(-1).astype(int).isin(valid_age_ratings)
        invalid_rows = df[invalid_age_rating_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_age_rating"].append({
                "row": row + 2,
                "Age Rating ID": df.at[row, "Age Rating ID"]
            })

    # Rule 7: Validate Date Format (Handle NaN properly)
    if "Rating Date" in df.columns:
        date_format = re.compile(r"^\d{2}/\d{2}/\d{4}$")
        invalid_date_mask = ~df["Rating Date"].astype(str).fillna("").str.match(date_format)
        invalid_rows = df[invalid_date_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_date_format"].append({
                "row": row + 2,
                "Rating Date": df.at[row, "Rating Date"]
            })

    return validation_results

# Example usage
file_path = input("Enter the path to your file (either .xlsx or .csv): ")
results = validate_file(file_path)
print(json.dumps(results, indent=4, ensure_ascii=False))
