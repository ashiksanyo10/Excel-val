import pandas as pd
import json
import re

def validate_excel(file_path):
    df = pd.read_excel(file_path, dtype=str)  # Read Excel file as string

    errors = {}

    # Expected columns
    required_columns = [
        "GTI", "Entity", "Title Name", "Other title names", "Duration",
        "Producers", "Directors", "Production Company Name", "Year of Production",
        "Countries", "Languages", "Is Version Original", "Age Rating ID",
        "Content Descriptors", "Violence Impact", "Drug Use Impact",
        "Themes Impact", "Language Impact", "Nudity Impact", "Sex Impact",
        "ACB Rated", "Different Version Production Exists", "Rating Date"
    ]

    # Check for missing columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in the Excel file: {missing_cols}")

    # Vectorized Duplicate Check for GTI
    duplicate_gtis = df[df.duplicated(subset=['GTI'], keep=False)]["GTI"].tolist()
    df["GTI_Duplicate"] = df["GTI"].isin(duplicate_gtis)

    # Vectorized Check for Missing Values (except "Other title names")
    missing_check = df.isna() | (df == "")
    required_non_blank_columns = [col for col in required_columns if col != "Other title names"]
    missing_values = missing_check[required_non_blank_columns].any(axis=1)

    # Vectorized English Character Check
    english_regex = r'^[a-zA-Z0-9\s.,&()\'"-]*$'
    text_columns = ["Title Name", "Producers", "Directors", "Production Company Name"]
    df["Non_English_Found"] = df[text_columns].apply(lambda x: x.str.match(english_regex) == False, axis=1).any(axis=1)

    # Vectorized Numeric Check for 'Countries' and 'Languages'
    df["Invalid_Country_Language"] = ~df["Countries"].str.isdigit() | ~df["Languages"].str.isdigit()

    # Vectorized Age Rating Validation
    valid_age_ratings = {"2", "9", "154", "147"}
    df["Invalid_Age_Rating"] = ~df["Age Rating ID"].isin(valid_age_ratings)

    # Vectorized Date Format Validation (MM/DD/YYYY)
    date_regex = r"^(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])/\d{4}$"
    df["Invalid_Date_Format"] = ~df["Rating Date"].str.match(date_regex)

    # Vectorized Check for Impact Columns (Shouldn't be blank, can be 'None')
    impact_columns = ["Violence Impact", "Drug Use Impact", "Themes Impact", "Language Impact", "Nudity Impact", "Sex Impact"]
    df["Impact_Column_Blank"] = df[impact_columns].apply(lambda x: x.isna() | (x == ""), axis=1).any(axis=1)
    df["Impact_Column_Invalid"] = ~df[impact_columns].apply(lambda x: x.isin(["None", "Low", "Medium", "High"]), axis=1).all(axis=1)

    # **Collecting Errors Efficiently**
    df_errors = df.loc[
        missing_values |
        df["GTI_Duplicate"] |
        df["Non_English_Found"] |
        df["Invalid_Country_Language"] |
        df["Invalid_Age_Rating"] |
        df["Invalid_Date_Format"] |
        df["Impact_Column_Blank"] |
        df["Impact_Column_Invalid"]
    ]

    # Structuring Error Report as JSON
    error_report = {}
    for index, row in df_errors.iterrows():
        row_errors = []

        if missing_values.iloc[index]:
            row_errors.append("Missing required values")
        if row["GTI_Duplicate"]:
            row_errors.append(f"Duplicate GTI '{row['GTI']}'")
        if row["Non_English_Found"]:
            row_errors.append("Non-English characters found in text fields")
        if row["Invalid_Country_Language"]:
            row_errors.append("Non-numeric value found in 'Countries' or 'Languages'")
        if row["Invalid_Age_Rating"]:
            row_errors.append(f"Invalid Age Rating ID '{row['Age Rating ID']}' (Allowed: 2, 9, 154, 147)")
        if row["Invalid_Date_Format"]:
            row_errors.append(f"Invalid date format in 'Rating Date' (Expected: MM/DD/YYYY)")
        if row["Impact_Column_Blank"]:
            row_errors.append("Impact columns cannot be blank (Allowed: 'None', 'Low', 'Medium', 'High')")
        if row["Impact_Column_Invalid"]:
            row_errors.append("Impact column contains invalid values (Allowed: 'None', 'Low', 'Medium', 'High')")

        error_report[index + 1] = row_errors  # Use row number (1-based index)

    # Print JSON report
    print(json.dumps(error_report, indent=4))

# Example usage
validate_excel("input.xlsx")  # Replace with your Excel file path
