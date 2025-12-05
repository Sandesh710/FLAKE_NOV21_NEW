#!/usr/bin/env python3
"""
FLake Input Converter - Maps to flake_interface() parameter names and units

Converts .NML and .DAT files to match the exact requirements of flake_interface():
- Correct parameter names (depth_w, fetch, T_bs, etc.)
- Correct units (all temperatures in K, pressure in Pa)
- Calculates derived parameters (Coriolis, longwave radiation, specific humidity)

Usage:
    python convert_for_flake.py input.nml input.dat

Output:
    - lake_config.json   (config parameters for flake_interface)
    - forcing.csv        (atmospheric forcing time series)
"""

import re
import json
import sys
import numpy as np


def nml_to_lake_config(nml_file, output_file='lake_config.json'):
    """
    Convert .NML to JSON with exact parameter names for flake_interface.

    Maps NML parameter names → flake_interface names:
    - depth_w_lk → depth_w
    - fetch_lk → fetch
    - T_bs_lk → T_bs (with °C → K conversion)
    - latitude_lk → par_Coriolis (calculated)
    - etc.
    """

    # Parse NML file
    raw_config = {}
    with open(nml_file, 'r') as f:
        content = f.read()

    # Remove comments
    content = re.sub(r'[!#].*$', '', content, flags=re.MULTILINE)

    # Find all key=value pairs
    param_pattern = r'(\w+)\s*=\s*([^,\n]+)'
    params = re.findall(param_pattern, content)

    for key, value in params:
        key = key.strip().lower()
        value = value.strip()

        # Convert to Python types
        if value.lower() in ['.true.', 't', 'true']:
            raw_config[key] = True
        elif value.lower() in ['.false.', 'f', 'false']:
            raw_config[key] = False
        elif '.' in value or 'e' in value.lower() or 'd' in value.lower():
            value = value.replace('D', 'E').replace('d', 'e')
            try:
                raw_config[key] = float(value)
            except:
                raw_config[key] = value.strip('\'"')
        else:
            try:
                raw_config[key] = int(value)
            except:
                raw_config[key] = value.strip('\'"')

    # =========================================================================
    # Map to flake_interface parameter names with correct units
    # =========================================================================

    config = {}

    # Lake geometry (direct mapping, already in correct units)
    config['depth_w'] = raw_config.get('depth_w_lk', 10.0)           # [m]
    config['fetch'] = raw_config.get('fetch_lk', 10000.0)            # [m]
    config['depth_bs'] = raw_config.get('depth_bs_lk', 5.0)          # [m]

    # Bottom temperature: °C → K
    T_bs_celsius = raw_config.get('t_bs_lk', 4.0)
    config['T_bs'] = T_bs_celsius + 273.15                           # [K]

    # Time parameters
    config['del_time'] = raw_config.get('del_time_lk', 86400.0)     # [s]
    config['time_step_number'] = raw_config.get('time_step_number', 365)

    # Calculate Coriolis parameter from latitude
    # par_Coriolis = 2 * Ω * sin(latitude)
    # where Ω = 7.2921e-5 rad/s (Earth's angular velocity)
    latitude_deg = raw_config.get('latitude_lk', 52.0)
    latitude_rad = np.radians(latitude_deg)
    config['par_Coriolis'] = 2.0 * 7.2921e-5 * np.sin(latitude_rad) # [s^-1]
    config['latitude'] = latitude_deg                                 # Keep for reference

    # Initial conditions: °C → K
    config['T_wML_in'] = raw_config.get('t_wml_in', 4.0) + 273.15   # [K]
    config['T_bot_in'] = raw_config.get('t_bot_in', 4.0) + 273.15   # [K]
    config['T_mnw_in'] = raw_config.get('t_wml_in', 4.0) + 273.15   # [K] (use same as T_wML)
    config['T_B1_in'] = raw_config.get('t_bs_lk', 4.0) + 273.15     # [K]
    config['T_ice_in'] = 273.15                                       # [K] (freezing point)
    config['T_snow_in'] = 273.15                                      # [K] (freezing point)

    # Initial thicknesses
    config['h_ML_in'] = raw_config.get('h_ml_in', 5.0)              # [m]
    config['h_ice_in'] = 0.0                                          # [m] (no ice initially)
    config['h_snow_in'] = 0.0                                         # [m] (no snow initially)
    config['H_B1_in'] = raw_config.get('depth_bs_lk', 5.0)          # [m]

    # Shape factors
    config['C_T_in'] = 0.5                                            # Thermocline shape factor

    # Surface temperature (initial guess)
    config['T_sfc_p'] = config['T_wML_in']                           # [K]

    # Measurement heights
    config['height_u_in'] = raw_config.get('z_wind_m(1)', 10.0)     # [m]
    config['height_tq_in'] = raw_config.get('z_taqa_m(1)', 2.0)     # [m]

    # Optical properties
    config['extincoef_optic'] = raw_config.get('extincoef_optic', 1.0)  # [m^-1]
    config['nband_optic'] = raw_config.get('nband_optic', 1)

    # Switches
    config['sediments_on'] = raw_config.get('sediments_on', True)

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Created {output_file}")
    print(f"\nLake Configuration:")
    print(f"  depth_w      = {config['depth_w']:.1f} m")
    print(f"  fetch        = {config['fetch']:.0f} m")
    print(f"  depth_bs     = {config['depth_bs']:.1f} m")
    print(f"  T_bs         = {config['T_bs']:.2f} K ({config['T_bs']-273.15:.1f}°C)")
    print(f"  par_Coriolis = {config['par_Coriolis']:.6e} s^-1")
    print(f"  del_time     = {config['del_time']:.0f} s")
    print(f"\nInitial Conditions:")
    print(f"  T_wML_in     = {config['T_wML_in']:.2f} K ({config['T_wML_in']-273.15:.1f}°C)")
    print(f"  T_bot_in     = {config['T_bot_in']:.2f} K ({config['T_bot_in']-273.15:.1f}°C)")
    print(f"  h_ML_in      = {config['h_ML_in']:.1f} m")

    return config


def dat_to_forcing_csv(dat_file, output_file='forcing.csv'):
    """
    Convert .DAT to CSV with exact parameter names for flake_interface.

    Potsdam .DAT format (6 columns):
    1. day number
    2. I_solar [W/m²]
    3. T_air [°C]  → convert to T_a_in [K]
    4. vapor_pressure [hPa] → convert to q_a_in [kg/kg]
    5. U_wind [m/s] → U_a_in [m/s]
    6. cloudiness [0-1] → use to calculate Q_atm_lw_in [W/m²]

    Output columns for flake_interface:
    - I_atm_in [W/m²]
    - Q_atm_lw_in [W/m²] (calculated)
    - T_a_in [K] (converted)
    - q_a_in [kg/kg] (calculated)
    - U_a_in [m/s]
    - P_a_in [Pa]
    - dMsnowdt_in [kg/(m²·s)]
    """

    # Constants
    sigma = 5.67e-8          # Stefan-Boltzmann constant [W/(m²·K⁴)]
    P_surface_hPa = 1013.25  # Standard sea-level pressure [hPa]
    P_surface_Pa = 101325.0  # Standard sea-level pressure [Pa]

    # Read DAT file and convert
    with open(output_file, 'w') as f_out:
        # Write header with flake_interface parameter names
        header = 'day,I_atm_in,Q_atm_lw_in,T_a_in,q_a_in,U_a_in,P_a_in,dMsnowdt_in\n'
        f_out.write(header)

        with open(dat_file, 'r') as f_in:
            for line in f_in:
                line = line.strip()
                if line and not line.startswith('#'):
                    values = line.split()

                    if len(values) >= 6:
                        day = int(float(values[0]))
                        I_solar = float(values[1])          # [W/m²]
                        T_air_C = float(values[2])          # [°C]
                        vapor_press_hPa = float(values[3])  # [hPa]
                        U_wind = float(values[4])           # [m/s]
                        cloudiness = float(values[5])       # [0-1]

                        # =====================================================
                        # Convert to flake_interface units
                        # =====================================================

                        # 1. I_atm_in: Solar radiation (direct)
                        I_atm_in = I_solar  # [W/m²]

                        # 2. T_a_in: Air temperature °C → K
                        T_a_in = T_air_C + 273.15  # [K]

                        # 3. q_a_in: Specific humidity from vapor pressure
                        # q = 0.622 * e / (P - 0.378*e)
                        # where e = vapor pressure [hPa], P = surface pressure [hPa]
                        q_a_in = 0.622 * vapor_press_hPa / (P_surface_hPa - 0.378 * vapor_press_hPa)  # [kg/kg]

                        # 4. Q_atm_lw_in: Longwave radiation (estimate from cloudiness)
                        # Q_lw = ε_atm * σ * T_a^4
                        # where ε_atm ≈ 0.6 + 0.2*cloudiness (empirical)
                        epsilon_atm = 0.6 + 0.2 * cloudiness
                        Q_atm_lw_in = epsilon_atm * sigma * (T_a_in ** 4)  # [W/m²]

                        # 5. U_a_in: Wind speed (direct)
                        U_a_in = U_wind  # [m/s]

                        # 6. P_a_in: Surface pressure (standard)
                        P_a_in = P_surface_Pa  # [Pa]

                        # 7. dMsnowdt_in: Snow accumulation rate (not in data, assume 0)
                        dMsnowdt_in = 0.0  # [kg/(m²·s)]

                        # Write converted values
                        f_out.write(f'{day},{I_atm_in:.4f},{Q_atm_lw_in:.4f},{T_a_in:.4f},'
                                   f'{q_a_in:.8f},{U_a_in:.4f},{P_a_in:.2f},{dMsnowdt_in:.6f}\n')

    # Count lines
    with open(output_file, 'r') as f:
        n_lines = sum(1 for _ in f) - 1

    print(f"✅ Created {output_file} ({n_lines} timesteps)")
    print(f"\nForcing Variables (flake_interface names):")
    print(f"  I_atm_in     : Solar radiation [W/m²]")
    print(f"  Q_atm_lw_in  : Longwave radiation [W/m²] (calculated)")
    print(f"  T_a_in       : Air temperature [K] (converted from °C)")
    print(f"  q_a_in       : Specific humidity [kg/kg] (calculated)")
    print(f"  U_a_in       : Wind speed [m/s]")
    print(f"  P_a_in       : Surface pressure [Pa]")
    print(f"  dMsnowdt_in  : Snow accumulation [kg/(m²·s)] (assumed 0)")

    # Read and show first few lines
    try:
        import pandas as pd
        df = pd.read_csv(output_file)
        print(f"\nFirst 3 timesteps:")
        print(df.head(3).to_string(index=False))
        print(f"\nData ranges:")
        print(f"  I_atm_in:    {df['I_atm_in'].min():.1f} - {df['I_atm_in'].max():.1f} W/m²")
        print(f"  Q_atm_lw_in: {df['Q_atm_lw_in'].min():.1f} - {df['Q_atm_lw_in'].max():.1f} W/m²")
        print(f"  T_a_in:      {df['T_a_in'].min():.2f} - {df['T_a_in'].max():.2f} K "
              f"({df['T_a_in'].min()-273.15:.1f} to {df['T_a_in'].max()-273.15:.1f}°C)")
        print(f"  U_a_in:      {df['U_a_in'].min():.1f} - {df['U_a_in'].max():.1f} m/s")
    except ImportError:
        pass


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        print("\n❌ Error: Need 2 arguments")
        print("Usage: python convert_for_flake.py <file.nml> <file.dat>")
        sys.exit(1)

    nml_file = sys.argv[1]
    dat_file = sys.argv[2]

    print("="*70)
    print("FLake Input Converter (matched to flake_interface)")
    print("="*70)

    # Convert NML
    print(f"\n📖 Converting {nml_file} → lake_config.json")
    config = nml_to_lake_config(nml_file, 'lake_config.json')

    # Convert DAT
    print(f"\n📖 Converting {dat_file} → forcing.csv")
    dat_to_forcing_csv(dat_file, 'forcing.csv')

    print("\n" + "="*70)
    print("✅ Conversion complete!")
    print("="*70)
    print("\nOutput files ready for flake_interface():")
    print("  - lake_config.json  (configuration parameters)")
    print("  - forcing.csv       (atmospheric forcing)")
    print("\nUsage example:")
    print("""
import pandas as pd
import json

# Load configuration
config = json.load(open('lake_config.json'))

# Load forcing
forcing = pd.read_csv('forcing.csv')

# Run FLake for timestep i:
result = flake_interface(
    dMsnowdt_in=forcing.loc[i, 'dMsnowdt_in'],
    I_atm_in=forcing.loc[i, 'I_atm_in'],
    Q_atm_lw_in=forcing.loc[i, 'Q_atm_lw_in'],
    height_u_in=config['height_u_in'],
    height_tq_in=config['height_tq_in'],
    U_a_in=forcing.loc[i, 'U_a_in'],
    T_a_in=forcing.loc[i, 'T_a_in'],
    q_a_in=forcing.loc[i, 'q_a_in'],
    P_a_in=forcing.loc[i, 'P_a_in'],
    depth_w=config['depth_w'],
    fetch=config['fetch'],
    depth_bs=config['depth_bs'],
    T_bs=config['T_bs'],
    par_Coriolis=config['par_Coriolis'],
    del_time=config['del_time'],
    T_snow_in=T_snow,
    T_ice_in=T_ice,
    T_mnw_in=T_mnw,
    T_wML_in=T_wML,
    T_bot_in=T_bot,
    T_B1_in=T_B1,
    C_T_in=C_T,
    h_snow_in=h_snow,
    h_ice_in=h_ice,
    h_ML_in=h_ML,
    H_B1_in=H_B1,
    T_sfc_p=T_sfc_p
)
""")


if __name__ == '__main__':
    main()
