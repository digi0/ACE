import pandas as pd

file_path = "ACE_vlt.xlsx"

df = pd.read_excel(file_path, sheet_name="PSU CMPSC")

print("Number of rows:", len(df))
print("Number of columns:", len(df.columns))
print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())