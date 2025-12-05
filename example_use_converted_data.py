#!/usr/bin/env python3
"""
Example: How to use converted FLake input data (pandas CSV format)

This script demonstrates loading configuration and forcing data,
then preparing it for use with the FLake model.
"""

import pandas as pd
import json
import numpy as np

# ============================================================================
# STEP 1: Load configuration from JSON
# ============================================================================

print("="*70)
print("STEP 1: Loading Configuration")
print("="*70)

with open('mueggelsee_config.json', 'r') as f:
    config = json.load(f)

print(f"\nLake Configuration ({len(config)} parameters):")
print("-"*70)
print(f"  Lake depth:        {config['depth_w_lk']} m")
print(f"  Fetch:             {config['fetch_lk']} m")
print(f"  Latitude:          {config['latitude_lk']}°N")
print(f"  Timestep:          {config['del_time_lk']} s ({config['del_time_lk']/86400:.0f} day)")
print(f"  Total timesteps:   {config['time_step_number']}")
print(f"  Sediments:         {config['sediments_on']}")
print(f"  Sediment depth:    {config['depth_bs_lk']} m")
print(f"  Bottom temp:       {config['t_bs_lk']}°C")
print(f"\nInitial conditions:")
print(f"  T_wML:             {config['t_wml_in']}°C")
print(f"  T_bot:             {config['t_bot_in']}°C")
print(f"  h_ML:              {config['h_ml_in']} m")
print(f"\nOptical properties:")
print(f"  Bands:             {config['nband_optic']}")
print(f"  Extinction coef:   {config['extincoef_optic']} m⁻¹")

# ============================================================================
# STEP 2: Load forcing data from CSV
# ============================================================================

print("\n" + "="*70)
print("STEP 2: Loading Forcing Data")
print("="*70)

forcing = pd.read_csv('mueggelsee_forcing.csv')

print(f"\nForcing Data:")
print("-"*70)
print(f"  Shape:             {forcing.shape[0]} timesteps × {forcing.shape[1]} variables")
print(f"  Period:            {forcing.shape[0]/365.25:.1f} years")
print(f"  Columns:           {list(forcing.columns)}")

print(f"\nData Statistics:")
print("-"*70)
print(forcing.describe())

# ============================================================================
# STEP 3: Process forcing data for FLake
# ============================================================================

print("\n" + "="*70)
print("STEP 3: Processing Forcing Data for FLake")
print("="*70)

# Convert temperature from Celsius to Kelvin
forcing['T_air_K'] = forcing['T_air'] + 273.15

# Calculate specific humidity from vapor pressure
# q = 0.622 * e / (P - 0.378*e)
# where e = vapor pressure [hPa], P = surface pressure [hPa]
P_surface = 1013.25  # Standard pressure [hPa] - could get from config if available
forcing['q_air'] = 0.622 * forcing['vapor_pressure'] / (P_surface - 0.378 * forcing['vapor_pressure'])

# Calculate longwave radiation from cloudiness (simplified empirical formula)
# Q_lw ≈ σ * T_air^4 * (0.6 + 0.2*cloudiness)
# where σ = 5.67e-8 W/(m²·K⁴)
sigma = 5.67e-8
forcing['Q_lw'] = sigma * (forcing['T_air_K']**4) * (0.6 + 0.2 * forcing['cloudiness'])

# Add time column in seconds
forcing['time_s'] = (forcing['day'] - 1) * config['del_time_lk']

print(f"\nProcessed columns added:")
print("-"*70)
print(f"  T_air_K:           Air temperature in Kelvin")
print(f"  q_air:             Specific humidity [kg/kg]")
print(f"  Q_lw:              Longwave radiation [W/m²] (estimated from cloudiness)")
print(f"  time_s:            Time in seconds")

print(f"\nSample processed data (first 5 timesteps):")
print("-"*70)
cols_to_show = ['day', 'I_solar', 'T_air', 'T_air_K', 'U_wind', 'q_air', 'Q_lw']
print(forcing[cols_to_show].head().to_string(index=False))

# ============================================================================
# STEP 4: Example - Prepare data for flake_interface()
# ============================================================================

print("\n" + "="*70)
print("STEP 4: Example Data Preparation for flake_interface()")
print("="*70)

print("""
# Convert units and prepare for FLake
depth_w = config['depth_w_lk']                    # Lake depth [m]
fetch = config['fetch_lk']                        # Fetch [m]
depth_bs = config['depth_bs_lk']                  # Sediment depth [m]
T_bs = config['t_bs_lk'] + 273.15                 # Bottom temp [K]
del_time = config['del_time_lk']                  # Timestep [s]

# Coriolis parameter from latitude
lat_rad = np.radians(config['latitude_lk'])
par_Coriolis = 2 * 7.2921e-5 * np.sin(lat_rad)   # Earth rotation [s⁻¹]

# Initial conditions
T_wML_in = config['t_wml_in'] + 273.15            # Initial mixed layer temp [K]
T_bot_in = config['t_bot_in'] + 273.15            # Initial bottom temp [K]
h_ML_in = config['h_ml_in']                       # Initial ML depth [m]

# Measurement heights (standard WMO)
height_u = 10.0                                    # Wind measurement [m]
height_tq = 2.0                                    # Temp/humidity measurement [m]

# Surface pressure (if not in forcing data)
P_a = 101325.0                                     # Standard pressure [Pa]

# For timestep i:
i = 0  # First timestep
print(f"\\nExample for timestep {i+1}:")
print(f"  I_atm_in     = {forcing.loc[i, 'I_solar']:.1f} W/m²")
print(f"  Q_atm_lw_in  = {forcing.loc[i, 'Q_lw']:.1f} W/m²")
print(f"  T_a_in       = {forcing.loc[i, 'T_air_K']:.2f} K")
print(f"  q_a_in       = {forcing.loc[i, 'q_air']:.6f} kg/kg")
print(f"  U_a_in       = {forcing.loc[i, 'U_wind']:.1f} m/s")
print(f"  P_a_in       = {P_a:.0f} Pa")
""")

# Calculate Coriolis parameter
lat_rad = np.radians(config['latitude_lk'])
par_Coriolis = 2 * 7.2921e-5 * np.sin(lat_rad)

print(f"\nDerived parameters:")
print(f"  Coriolis parameter: {par_Coriolis:.6e} s⁻¹")
print(f"  Bottom temp (K):    {config['t_bs_lk'] + 273.15:.2f} K")

# ============================================================================
# STEP 5: Show how to loop over all timesteps
# ============================================================================

print("\n" + "="*70)
print("STEP 5: Template for Running FLake Model")
print("="*70)

print("""
# Pseudo-code for running FLake over all timesteps:

# Initialize state variables
T_snow = 273.15
T_ice = 273.15
T_mnw = config['t_wml_in'] + 273.15
T_wML = config['t_wml_in'] + 273.15
T_bot = config['t_bot_in'] + 273.15
T_B1 = config['t_bs_lk'] + 273.15
h_snow = 0.0
h_ice = 0.0
h_ML = config['h_ml_in']
H_B1 = config['depth_bs_lk']
C_T = 0.5
T_sfc_p = T_wML

# Storage for results
results = []

# Main time loop
for i in range(len(forcing)):
    # Get forcing for this timestep
    I_atm_in = forcing.loc[i, 'I_solar']
    Q_atm_lw_in = forcing.loc[i, 'Q_lw']
    T_a_in = forcing.loc[i, 'T_air_K']
    q_a_in = forcing.loc[i, 'q_air']
    U_a_in = forcing.loc[i, 'U_wind']
    P_a_in = 101325.0  # Pa
    dMsnowdt_in = 0.0  # No snow accumulation (or calculate from precipitation)

    # Call FLake interface
    result = flake_interface(
        dMsnowdt_in=dMsnowdt_in,
        I_atm_in=I_atm_in,
        Q_atm_lw_in=Q_atm_lw_in,
        height_u_in=10.0,
        height_tq_in=2.0,
        U_a_in=U_a_in,
        T_a_in=T_a_in,
        q_a_in=q_a_in,
        P_a_in=P_a_in,
        depth_w=config['depth_w_lk'],
        fetch=config['fetch_lk'],
        depth_bs=config['depth_bs_lk'],
        T_bs=config['t_bs_lk'] + 273.15,
        par_Coriolis=par_Coriolis,
        del_time=config['del_time_lk'],
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

    # Update state variables for next timestep
    T_snow = result['T_snow_out']
    T_ice = result['T_ice_out']
    T_mnw = result['T_mnw_out']
    T_wML = result['T_wML_out']
    T_bot = result['T_bot_out']
    T_B1 = result['T_B1_out']
    h_snow = result['h_snow_out']
    h_ice = result['h_ice_out']
    h_ML = result['h_ML_out']
    H_B1 = result['H_B1_out']
    C_T = result['C_T_out']
    T_sfc_p = result['T_sfc_n']

    # Store results
    results.append({
        'day': forcing.loc[i, 'day'],
        'T_sfc': T_sfc_p - 273.15,  # Convert to °C
        'T_wML': T_wML - 273.15,
        'h_ice': h_ice,
        'h_ML': h_ML
    })

# Convert results to DataFrame
results_df = pd.DataFrame(results)
results_df.to_csv('flake_results.csv', index=False)
""")

print("\n" + "="*70)
print("✅ Data conversion and preparation complete!")
print("="*70)
print("\nNext steps:")
print("  1. Load your FLake model from flake_model.ipynb")
print("  2. Use the template above to run simulations")
print("  3. Results will be saved to flake_results.csv")
