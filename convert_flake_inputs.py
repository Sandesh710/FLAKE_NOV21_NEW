#!/usr/bin/env python3
"""
FLake Input File Converter: .NML + .DAT → pandas CSV + config.json

Converts Fortran namelist (.NML) and data (.DAT) files to Python-friendly formats:
- .NML → config.json (lake configuration parameters)
- .DAT → forcing.csv (atmospheric forcing time series)

Usage:
    python convert_flake_inputs.py --nml input.nml --dat forcing.dat

Output:
    - config.json: Lake configuration dictionary
    - forcing.csv: Pandas-ready atmospheric forcing data
"""

import argparse
import json
import re
import pandas as pd
import numpy as np
from pathlib import Path


def parse_nml_file(nml_path):
    """
    Parse Fortran namelist (.NML) file into Python dictionary.

    Handles common FLake namelist parameters:
    - Lake geometry (depth, fetch, latitude)
    - Time integration (timestep, duration)
    - Physical switches (sediments, ice model)
    - Initial conditions

    Parameters:
    -----------
    nml_path : str or Path
        Path to .NML file

    Returns:
    --------
    dict : Configuration parameters
    """
    config = {}

    with open(nml_path, 'r') as f:
        content = f.read()

    # Remove comments (! or # to end of line)
    content = re.sub(r'[!#].*$', '', content, flags=re.MULTILINE)

    # Find all namelist blocks (&NAMELIST_NAME ... /)
    namelist_pattern = r'&(\w+)(.*?)/'
    namelists = re.findall(namelist_pattern, content, re.DOTALL | re.IGNORECASE)

    for namelist_name, namelist_content in namelists:
        # Parse key=value pairs
        # Match: variable_name = value
        param_pattern = r'(\w+)\s*=\s*([^,\n]+)'
        params = re.findall(param_pattern, namelist_content)

        for key, value in params:
            key = key.strip().lower()
            value = value.strip()

            # Convert to appropriate Python type
            try:
                # Try boolean
                if value.lower() in ['.true.', 't', 'true']:
                    config[key] = True
                elif value.lower() in ['.false.', 'f', 'false']:
                    config[key] = False
                # Try float
                elif '.' in value or 'e' in value.lower() or 'd' in value.lower():
                    # Handle Fortran double precision (D instead of E)
                    value = value.replace('D', 'E').replace('d', 'e')
                    config[key] = float(value)
                # Try int
                elif value.isdigit() or (value[0] == '-' and value[1:].isdigit()):
                    config[key] = int(value)
                # Keep as string
                else:
                    # Remove quotes if present
                    config[key] = value.strip('\'"')
            except ValueError:
                config[key] = value.strip('\'"')

    return config


def parse_dat_file(dat_path, auto_detect=True):
    """
    Parse Fortran data (.DAT) file into pandas DataFrame.

    Handles two common formats:
    1. Auto-detect: First line is header with column names
    2. Fixed format: Known column structure for FLake forcing

    Common FLake forcing columns:
    - time (or year, month, day, hour)
    - I_solar: Solar radiation [W/m²]
    - Q_lw: Longwave radiation [W/m²]
    - T_air: Air temperature [K] or [°C]
    - q_air: Specific humidity [kg/kg] or relative humidity [%]
    - U_wind: Wind speed [m/s]
    - P_air: Surface pressure [Pa] or [hPa]
    - precip: Precipitation [mm/hr] or [kg/m²/s]

    Parameters:
    -----------
    dat_path : str or Path
        Path to .DAT file
    auto_detect : bool
        If True, try to auto-detect format from first line

    Returns:
    --------
    pandas.DataFrame : Forcing data
    """

    # Read first few lines to detect format
    with open(dat_path, 'r') as f:
        lines = [f.readline() for _ in range(10)]

    # Check if first line is a header (contains non-numeric characters)
    first_line = lines[0].strip()
    has_header = not all(c.isdigit() or c in '.- \t' for c in first_line.replace('E', '').replace('e', ''))

    if auto_detect and has_header:
        # Use first line as header
        df = pd.read_csv(dat_path, delim_whitespace=True)
        # Standardize column names
        df.columns = df.columns.str.lower().str.strip()

    else:
        # No header - use default FLake forcing column names
        print("No header detected. Using default FLake forcing column names.")
        print("Expected columns: time, I_solar, Q_lw, T_air, q_air, U_wind, P_air")

        # Try to detect number of columns
        first_data_line = next(line for line in lines if line.strip() and not line.strip().startswith('#'))
        n_cols = len(first_data_line.split())

        # Default column names for common formats
        if n_cols == 7:
            col_names = ['time', 'I_solar', 'Q_lw', 'T_air', 'q_air', 'U_wind', 'P_air']
        elif n_cols == 8:
            col_names = ['time', 'I_solar', 'Q_lw', 'T_air', 'q_air', 'U_wind', 'P_air', 'precip']
        elif n_cols == 10:
            col_names = ['year', 'month', 'day', 'hour', 'I_solar', 'Q_lw', 'T_air', 'q_air', 'U_wind', 'P_air']
        else:
            # Generic column names
            col_names = [f'col_{i}' for i in range(n_cols)]
            print(f"Warning: Unusual number of columns ({n_cols}). Using generic names: {col_names}")

        # Read data
        df = pd.read_csv(dat_path, delim_whitespace=True, names=col_names, comment='#')

    # Convert datetime if separate year/month/day/hour columns exist
    if all(col in df.columns for col in ['year', 'month', 'day', 'hour']):
        df['datetime'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']])
        df['time'] = (df['datetime'] - df['datetime'].iloc[0]).dt.total_seconds()

    return df


def create_example_files():
    """
    Create example .NML and .DAT files for testing.

    This generates sample input files in the expected FLake format.
    """

    # Example NML file
    example_nml = """!
! FLake Configuration Namelist
!
&LAKE_PARAMS
  depth_w = 20.0          ! Lake depth [m]
  depth_bs = 5.0          ! Bottom sediment depth [m]
  T_bs = 277.13           ! Bottom temperature [K]
  fetch = 10000.0         ! Wind fetch [m]
  latitude = 52.0         ! Latitude [degrees]
/

&TIME_PARAMS
  del_time = 3600.0       ! Timestep [s] (1 hour)
  start_year = 2023
  start_month = 1
  start_day = 1
  duration_days = 365
/

&PHYSICS_SWITCHES
  lflk_botsed_use = .true.   ! Use bottom sediments?
/

&INITIAL_CONDITIONS
  T_snow_init = 273.15    ! Initial snow temperature [K]
  T_ice_init = 273.15     ! Initial ice temperature [K]
  T_wML_init = 277.0      ! Initial mixed layer temp [K]
  h_snow_init = 0.0       ! Initial snow thickness [m]
  h_ice_init = 0.0        ! Initial ice thickness [m]
  h_ML_init = 10.0        ! Initial mixed layer depth [m]
/
"""

    # Example DAT file (10 days hourly data)
    print("Generating example forcing data...")
    n_hours = 240  # 10 days
    time = np.arange(n_hours) * 3600.0  # seconds

    # Synthetic forcing data with diurnal cycle
    hour_of_day = np.arange(n_hours) % 24
    I_solar = np.maximum(0, 500 * np.sin(np.pi * hour_of_day / 12))  # W/m²
    Q_lw = 300 + 50 * np.sin(2 * np.pi * time / (24*3600))  # W/m²
    T_air = 283.15 + 5 * np.sin(2 * np.pi * time / (24*3600))  # K
    q_air = 0.008 + 0.002 * np.sin(2 * np.pi * time / (24*3600))  # kg/kg
    U_wind = 3.0 + 2.0 * np.random.random(n_hours)  # m/s
    P_air = 101325.0 + 500 * np.random.randn(n_hours)  # Pa

    example_dat_df = pd.DataFrame({
        'time': time,
        'I_solar': I_solar,
        'Q_lw': Q_lw,
        'T_air': T_air,
        'q_air': q_air,
        'U_wind': U_wind,
        'P_air': P_air
    })

    # Write example files
    with open('example_input.nml', 'w') as f:
        f.write(example_nml)

    # Write DAT in Fortran fixed-width format
    with open('example_forcing.dat', 'w') as f:
        f.write("# time(s)    I_solar(W/m2)  Q_lw(W/m2)  T_air(K)  q_air(kg/kg)  U_wind(m/s)  P_air(Pa)\n")
        for _, row in example_dat_df.iterrows():
            f.write(f"{row['time']:12.1f} {row['I_solar']:12.2f} {row['Q_lw']:12.2f} "
                   f"{row['T_air']:10.2f} {row['q_air']:12.6f} {row['U_wind']:10.2f} "
                   f"{row['P_air']:12.1f}\n")

    print("✅ Created example_input.nml")
    print("✅ Created example_forcing.dat")
    print("\nTo convert these examples:")
    print("  python convert_flake_inputs.py --nml example_input.nml --dat example_forcing.dat")


def main():
    parser = argparse.ArgumentParser(
        description='Convert FLake Fortran input files to pandas CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert existing files
  python convert_flake_inputs.py --nml lake_config.nml --dat forcing_data.dat

  # Create example files for testing
  python convert_flake_inputs.py --create-examples

  # Specify custom output names
  python convert_flake_inputs.py --nml input.nml --dat input.dat --out my_data

Output files:
  - config.json: Lake configuration (from .NML)
  - forcing.csv: Atmospheric forcing (from .DAT)
"""
    )

    parser.add_argument('--nml', type=str, help='Path to .NML namelist file')
    parser.add_argument('--dat', type=str, help='Path to .DAT forcing data file')
    parser.add_argument('--out', type=str, default='flake_input',
                       help='Output filename prefix (default: flake_input)')
    parser.add_argument('--create-examples', action='store_true',
                       help='Create example input files for testing')

    args = parser.parse_args()

    # Create examples if requested
    if args.create_examples:
        create_example_files()
        return

    # Check that input files are provided
    if not args.nml and not args.dat:
        parser.print_help()
        print("\n❌ Error: Must provide --nml and/or --dat, or use --create-examples")
        return

    # Parse NML file
    if args.nml:
        print(f"\n📖 Reading {args.nml}...")
        config = parse_nml_file(args.nml)

        # Save as JSON
        config_file = f"{args.out}_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Created {config_file}")
        print(f"   Found {len(config)} parameters:")
        for key, value in list(config.items())[:10]:
            print(f"      {key} = {value}")
        if len(config) > 10:
            print(f"      ... and {len(config)-10} more")

    # Parse DAT file
    if args.dat:
        print(f"\n📖 Reading {args.dat}...")
        df = parse_dat_file(args.dat)

        # Save as CSV
        csv_file = f"{args.out}_forcing.csv"
        df.to_csv(csv_file, index=False)

        print(f"✅ Created {csv_file}")
        print(f"   Shape: {df.shape[0]} timesteps × {df.shape[1]} variables")
        print(f"   Columns: {list(df.columns)}")
        print(f"\n   First few rows:")
        print(df.head(3).to_string(index=False))

    print("\n" + "="*70)
    print("✅ Conversion complete!")
    print("="*70)
    print("\nUsage in Python:")
    print(f"""
import pandas as pd
import json

# Load configuration
with open('{args.out}_config.json', 'r') as f:
    config = json.load(f)

# Load forcing data
forcing = pd.read_csv('{args.out}_forcing.csv')

# Example: Run FLake for each timestep
for i in range(len(forcing)):
    result = flake_interface(
        I_atm_in=forcing.loc[i, 'I_solar'],
        Q_atm_lw_in=forcing.loc[i, 'Q_lw'],
        T_a_in=forcing.loc[i, 'T_air'],
        q_a_in=forcing.loc[i, 'q_air'],
        U_a_in=forcing.loc[i, 'U_wind'],
        P_a_in=forcing.loc[i, 'P_air'],
        depth_w=config['depth_w'],
        del_time=config['del_time'],
        # ... other parameters
    )
""")


if __name__ == '__main__':
    main()
