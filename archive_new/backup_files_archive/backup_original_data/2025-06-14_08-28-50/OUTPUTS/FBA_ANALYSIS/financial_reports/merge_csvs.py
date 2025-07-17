import os
import pandas as pd

# 1. Set the directory containing your CSV files
input_dir = r"C:\Users\chris\Cloud-Drive_christianhaddad8@gmail.com\Cloud-Drive\Full\claude code\Amazon-FBA-Agent-System-v3\OUTPUTS\FBA_ANALYSIS\financial_reports"

# 2. List all files in that directory and filter for ".csv" extension
all_files = os.listdir(input_dir)
csv_files = [f for f in all_files if f.lower().endswith(".csv")]

if not csv_files:
    raise SystemExit(f"No CSV files found in {input_dir!r}.")

# 3. Read each CSV into a DataFrame and collect them in a list
dataframes = []
for filename in csv_files:
    file_path = os.path.join(input_dir, filename)
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise SystemExit(f"Failed to read {file_path!r}: {e}")
    dataframes.append(df)

# 4. Concatenate all DataFrames into one (assumes identical columns/order)
combined_df = pd.concat(dataframes, ignore_index=True)

# 5. Write the combined DataFrame back out as a new CSV
output_path = os.path.join(input_dir, "combined_output.csv")
combined_df.to_csv(output_path, index=False)

print(f"Combined {len(csv_files)} files into:\n  {output_path}")
