#!/usr/bin/env python3
"""
Simple FLake Input Converter: .NML → JSON, .DAT → CSV

Usage:
    python simple_convert.py input.nml input.dat

Example:
    python simple_convert.py Mueggelsee80-96.nml Potsdam80-96.dat

Output:
    - config.json (from .nml)
    - forcing.csv (from .dat)
"""

import re
import json
import sys


def nml_to_json(nml_file, output_file='config.json'):
    """Convert Fortran namelist (.NML) to JSON."""

    config = {}

    with open(nml_file, 'r') as f:
        content = f.read()

    # Remove comments (! or #)
    content = re.sub(r'[!#].*$', '', content, flags=re.MULTILINE)

    # Find all key=value pairs
    param_pattern = r'(\w+)\s*=\s*([^,\n]+)'
    params = re.findall(param_pattern, content)

    for key, value in params:
        key = key.strip().lower()
        value = value.strip()

        # Convert to Python types
        if value.lower() in ['.true.', 't', 'true']:
            config[key] = True
        elif value.lower() in ['.false.', 'f', 'false']:
            config[key] = False
        elif '.' in value or 'e' in value.lower() or 'd' in value.lower():
            value = value.replace('D', 'E').replace('d', 'e')
            try:
                config[key] = float(value)
            except:
                config[key] = value.strip('\'"')
        else:
            try:
                config[key] = int(value)
            except:
                config[key] = value.strip('\'"')

    # Save as JSON
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Created {output_file} ({len(config)} parameters)")
    return config


def dat_to_csv(dat_file, output_file='forcing.csv'):
    """Convert Fortran data (.DAT) to CSV with proper column names."""

    # Column names for Potsdam forcing format (6 columns)
    columns = ['day', 'I_solar', 'T_air', 'vapor_pressure', 'U_wind', 'cloudiness']

    # Read and convert
    with open(dat_file, 'r') as f_in, open(output_file, 'w') as f_out:
        # Write header
        f_out.write(','.join(columns) + '\n')

        # Write data
        for line in f_in:
            line = line.strip()
            if line and not line.startswith('#'):
                # Split on whitespace, convert to comma-separated
                values = line.split()
                f_out.write(','.join(values) + '\n')

    # Count lines
    with open(output_file, 'r') as f:
        n_lines = sum(1 for _ in f) - 1  # Subtract header

    print(f"✅ Created {output_file} ({n_lines} timesteps)")


def process_forcing_csv(csv_file):
    """Add computed columns to forcing CSV (requires pandas)."""

    try:
        import pandas as pd
    except ImportError:
        print("⚠️  pandas not available - skipping processing step")
        print("   Install with: pip install pandas")
        return

    # Read CSV
    df = pd.read_csv(csv_file)

    # Add computed columns
    df['T_air_K'] = df['T_air'] + 273.15

    # Specific humidity from vapor pressure
    P_surf = 1013.25  # hPa
    df['q_air'] = 0.622 * df['vapor_pressure'] / (P_surf - 0.378 * df['vapor_pressure'])

    # Longwave radiation estimate
    sigma = 5.67e-8
    df['Q_lw'] = sigma * (df['T_air_K']**4) * (0.6 + 0.2 * df['cloudiness'])

    # Save
    df.to_csv(csv_file, index=False)
    print(f"✅ Added processed columns: T_air_K, q_air, Q_lw")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        print("\n❌ Error: Need 2 arguments")
        print("Usage: python simple_convert.py <file.nml> <file.dat>")
        sys.exit(1)

    nml_file = sys.argv[1]
    dat_file = sys.argv[2]

    print("="*70)
    print("FLake Input Converter")
    print("="*70)

    # Convert NML to JSON
    print(f"\n📖 Converting {nml_file} → config.json")
    config = nml_to_json(nml_file, 'config.json')

    # Show key parameters
    print("\nKey parameters:")
    keys_to_show = ['depth_w_lk', 'fetch_lk', 'latitude_lk', 'del_time_lk',
                    't_wml_in', 'h_ml_in', 'extincoef_optic']
    for key in keys_to_show:
        if key in config:
            print(f"  {key:20s} = {config[key]}")

    # Convert DAT to CSV
    print(f"\n📖 Converting {dat_file} → forcing.csv")
    dat_to_csv(dat_file, 'forcing.csv')

    # Process forcing data
    print(f"\n📖 Processing forcing.csv")
    process_forcing_csv('forcing.csv')

    print("\n" + "="*70)
    print("✅ Conversion complete!")
    print("="*70)
    print("\nOutput files:")
    print("  - config.json   (lake configuration)")
    print("  - forcing.csv   (atmospheric forcing)")
    print("\nUsage in Python:")
    print("  import pandas as pd")
    print("  import json")
    print("  ")
    print("  config = json.load(open('config.json'))")
    print("  forcing = pd.read_csv('forcing.csv')")


if __name__ == '__main__':
    main()
