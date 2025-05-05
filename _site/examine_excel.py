import pandas as pd

# Read the Excel file
excel_file = 'assets/Comparison - USP Bomag- Tier 3 .xlsx'
print(f"\nExamining Excel file: {excel_file}")

# Read all sheets
xl = pd.ExcelFile(excel_file)
print("\nAvailable sheets:", xl.sheet_names)

for sheet_name in xl.sheet_names:
    print(f"\nExamining sheet: {sheet_name}")
    # Read the sheet
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    
    # Print basic info
    print("\nFirst few rows:")
    print(df.head())
    
    # Print column names
    print("\nColumns:", df.columns.tolist())
    
    # Print shape
    print("\nShape:", df.shape)
    
    # Print non-null counts
    print("\nNon-null counts:")
    print(df.count()) 