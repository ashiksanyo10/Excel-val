from flask import Flask, render_template, request, jsonify
import pandas as pd
import re
import json
import os
from pathlib import Path

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file(file_path):
    file_extension = Path(file_path).suffix.lower()
    
    # Load file
    try:
        if file_extension == ".xlsx":
            df = pd.read_excel(file_path, dtype=str)  # Read as string to prevent type conversion
        elif file_extension == ".csv":
            df = pd.read_csv(file_path, dtype=str, encoding="utf-8", errors="ignore")
        else:
            return {"error": "Unsupported file format. Only .xlsx and .csv are allowed."}
    except Exception as e:
        return {"error": str(e)}

    validation_results = {"errors": {}, "warnings": {}}

    # Initialize error categories
    error_types = [
        "blank_cells", "non_english_chars", "duplicate_gti",
        "invalid_country_language", "invalid_age_rating", "invalid_date_format"
    ]
    for et in error_types:
        validation_results["errors"][et] = []

    # Columns where "None" is allowed but not blank
    non_blank_columns = [
        "Violence Impact", "Drug Use Impact", "Themes Impact",
        "Language Impact", "Nudity Impact", "Sex Impact"
    ]

    # Rule 1: Check for blank cells (except for other title names)
    for col in df.columns:
        if col in non_blank_columns:
            blank_rows = df[df[col].isna()].index.tolist()
            for row in blank_rows:
                validation_results["errors"]["blank_cells"].append(
                    {"row": row + 2, "column": col, "message": "Cannot be blank (None is allowed)."}
                )
    
    # Rule 2: Check for non-English characters
    non_english_mask = df.map(lambda x: bool(re.search(r"[^\x00-\x7F]", str(x))) if pd.notna(x) else False)
    for row, col in zip(*non_english_mask.where(non_english_mask).stack().index.to_list()):
        validation_results["errors"]["non_english_chars"].append(
            {"row": row + 2, "column": col, "value": df.at[row, col]}
        )

    # Rule 3: Find duplicate GTI values and show both rows where found
    if "GTI" in df.columns:
        duplicate_gtis = df[df.duplicated("GTI", keep=False)]
        for gti in duplicate_gtis["GTI"].unique():
            duplicate_rows = df.index[df["GTI"] == gti].tolist()
            validation_results["errors"]["duplicate_gti"].append(
                {"GTI": gti, "rows": [row + 2 for row in duplicate_rows], "value": gti}
            )

    # Rule 4: Validate Countries and Languages are numeric
    if "Countries" in df.columns and "Languages" in df.columns:
        invalid_country_language_mask = ~(
            df["Countries"].notna() & df["Countries"].str.isnumeric() &
            df["Languages"].notna() & df["Languages"].str.isnumeric()
        )
        invalid_rows = df[invalid_country_language_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_country_language"].append(
                {"row": row + 2, "Countries": df.at[row, "Countries"], "Languages": df.at[row, "Languages"]}
            )

    # Rule 5: Validate Age Rating ID
    valid_age_ratings = {"2", "9", "154", "147"}
    if "Age Rating ID" in df.columns:
        invalid_age_rating_mask = df["Age Rating ID"].notna() & ~df["Age Rating ID"].isin(valid_age_ratings)
        invalid_rows = df[invalid_age_rating_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_age_rating"].append(
                {"row": row + 2, "Age Rating ID": df.at[row, "Age Rating ID"]}
            )

    # Rule 6: Validate Date format (MM/DD/YYYY)
    if "Rating Date" in df.columns:
        date_format = re.compile(r"^\d{2}/\d{2}/\d{4}$")
        invalid_date_mask = df["Rating Date"].notna() & ~df["Rating Date"].astype(str).str.match(date_format)
        invalid_rows = df[invalid_date_mask].index.tolist()
        for row in invalid_rows:
            validation_results["errors"]["invalid_date_format"].append(
                {"row": row + 2, "Rating Date": df.at[row, "Rating Date"]}
            )

    return validation_results

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"error": "No file part"})

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"})

        if file and allowed_file(file.filename):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Perform validation
            validation_results = validate_file(file_path)
            os.remove(file_path)  # Remove file after processing

            return jsonify(validation_results)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
