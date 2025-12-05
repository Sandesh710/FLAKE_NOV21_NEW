#!/usr/bin/env python3
"""
Fix column names in converted FLake forcing CSV.

The Potsdam80-96.dat file has 6 columns without headers:
- col_0: Day number (timestep)
- col_1: Solar radiation [W/m²]
- col_2: Air temperature [°C]
- col_3: Vapor pressure [hPa]
- col_4: Wind speed [m/s]
- col_5: Cloudiness fraction [0-1]

Usage:
    python fix_column_names.py mueggelsee_forcing.csv
"""

import pandas as pd
import sys

def fix_column_names(csv_file):
    """
    Fix generic column names (col_0, col_1, ...) to meaningful names.

    Parameters:
    -----------
    csv_file : str
        Path to CSV file with generic column names
    """
    # Read the CSV
    df = pd.read_csv(csv_file)

    # Check if it has generic column names
    if 'col_0' not in df.columns:
        print(f"❌ File {csv_file} doesn't have generic column names.")
        print(f"   Current columns: {list(df.columns)}")
        return

    # Rename columns based on Potsdam forcing format
    df.columns = ['day', 'I_solar', 'T_air', 'vapor_pressure', 'U_wind', 'cloudiness']

    # Save with proper column names
    df.to_csv(csv_file, index=False)

    print(f"✅ Fixed column names in {csv_file}")
    print(f"\nDataset summary:")
    print(f"  Period: {len(df)} days ({len(df)/365.25:.1f} years)")
    print(f"  Columns: {list(df.columns)}")
    print(f"\n  Data ranges:")
    print(f"    Solar radiation: {df['I_solar'].min():.1f} - {df['I_solar'].max():.1f} W/m²")
    print(f"    Air temperature: {df['T_air'].min():.1f} - {df['T_air'].max():.1f} °C")
    print(f"    Wind speed: {df['U_wind'].min():.1f} - {df['U_wind'].max():.1f} m/s")
    print(f"    Cloudiness: {df['cloudiness'].min():.2f} - {df['cloudiness'].max():.2f}")
    print(f"\nFirst 5 rows:")
    print(df.head().to_string(index=False))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python fix_column_names.py <csv_file>")
        print("Example: python fix_column_names.py mueggelsee_forcing.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    fix_column_names(csv_file)
