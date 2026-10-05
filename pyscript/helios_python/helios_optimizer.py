# Module: HELIOS Optimizer - Python Function to Calculate an Optimized Energy Plan                            
# Home Energy Linear Integrated Optimization Service (HELIOS Calculator)
# The Optimizer uses SciPy Linear/MILP Programming to calculated the Optimal Energy Plan 
# for Solar Production, Battery Charging/Discharging and expected House Energy Usage for Dynamic Prices during the period.
# A Solar Forecast can be specified with the expected Solar Production.
# A House Forecast can bes specified with the expected (undeferrable) Energy Usage in the House.
# In the future support for Deferrable Devices (like EV, HP and Boiler) will be added. 
#
# Important Decisions:
# - The Optimizer will be a Pure Python Function (helios_optimizer.py) that can be called from the Home Assistant PyScript Helios Optimizer Service (helios_main.py) 
# - The Optimization Variables are in kW (power) and not in kWh (energy), both would have been possible but power (kW) was selected
# - The Optimization Variables are stored in a single array (x) with a dynamic index map to determine the index of each variable type 
#   (e.g. Index Types are Grid Import/Export, Battery Charge/Discharge, Solar Production, House Usage and in the future EV Charge, HP Power and Boiler Power)
# - The Delta Time (e.g. 0.25 hours) for the Optimization (delta_time = 1 / steps_per_hour, e.g. 4 steps per hour) is important for the conversion from kW (power) to kWh (energy)
# - The Boundaries for the Optimization Variables are of course also in kW (power) and are used to limit the maximum power for import/export, charging/discharging, solar production, house usage, etc.
#   Limits for the battery and the grid are in kW (power) already but solar forecast and house forecast are in kWh (energy) and must be converted to kW (power) by multiplying with steps_per_hour (1/delta_time)
# - A specific boundary is the Balance of Power (and Energy): Incoming and Outgoing Power (and Energy) are always in Balance
#   Grid Import - Grid Export + Battery Discharge - Battery Charge  + Solar Production = House Usage
#   1.0 x imp_power - 1.0 x exp_power + 1.0 x bat_disch - 1.0 x bat_charge + 1.0 x solar_prod - 1.0 x ev_charge - 1.0 x hp_power - 1.0 x boil_power = house_energy_forecast (house demand)
# - Battery SOC Limitations (Start, Minimum, Maximum and Target) also are boundaries, 
#   Start SOC is the starting point for these boundaries, Min and Max SOC must be valid in each step, Target SOC must be reach at the end of the optimization period 
# - The Cost Function is in euro (or cent) per kWh and is calculated for each step as the product of the price and the energy (kWh) for that step
#   Therefore the optimization variables (in kW) must be multiplied by the delta_time (in hours) to convert to kWh for the cost calculation
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1   Started Implementation with help of Google Gemini
#   2026-08-27: JR  v0.78k Included performance measurements, Improve (PyScript) Performance for the Index in the Variable Array, Vectorized Assignments, Improved Steps: 5, Todo Steps: 4 and may be 3 
#   2026-08-28: JR  v0.78k Split off the common functies into a helios_common.py, this file now only contains the optimizer itself
#   2026-08-31: JR  v0.78l Adding input parameters to the dashboard, improved output markdown cards, adapted the payload (consistent names with kwh, kw, w, ms etc) 
#   2026-09-02: JR  v0.78m Separate input step sizes for import/export prices, house forecast and solar forecast arrays (3 values) instead of a single input step size to allow for different resampling conversions
#   2026-09-03: JR  v0.78m Allow arrays that are too long (e.g. 48 steps for 2 days while the optimization period is only 24 steps for 1 day), the extra steps will be ignored
#   2026-09-04: JR  v0.79n Added Sum (Totals) of Input Arrays and Output Arrays for validation purposes, calculated only at maximum insight level, optionally returned in the payload, error in validation when overall_sum_kwh above the threshold
#   2026-09-09: JR  v0.79o Change the Helios Optimizer to a Pure Python function, Adapted the function to use the Python _LOGGER instead of the PyScript log, changed dt into delta_time
#   2026-09-09: JR  v0.79o Changed the helios_optimizer_service to asynchronous function and call the helios_optimizer_calc_plan from the service using an await and the task.executor, big performance improvement
#   2026-09-11: JR  v0.79p Corrected errors in the optimization model related to the difference in power and energy rules for steps smaller than 1 hour (e.g. 15 min)
#   2026-09-12: JR  v0.79p Changed arguments solar.forecast and house_forecast to solar.energy_forecast and house_energy_forecast to stress the difference between energy and power values
#   2026-09-18: JR  v0.78r Added HBC Price Array and Provider Price Arrays as Input Price Array (Import and Export Price Arrays are derived from the Input Array)
#   2026-09-18: JR  v0.79r Added a now_ts to the arguments with Naive (without timezone) (HA) Current Time, rename optimize_ts to optimize_ts_str
#   2026-10-01: JR  v0.79s Added Source Price Data parsing to determine the Import and Export Price Arrays (using the Helios Energy Price Parser), added source_type and original_provider to the arguments
#
#   Remark: For the full helios history see helios_main.py
#   
# Warning: In Visual Studio this module exists in the helios_python folder of the Helios Optimizer Project and in Home Assistant in the /config/pyscript/helios_python folder.

import sys                                    # For sys.path.append() to add the Home Assistant Pyscript folder to the path
import time 
import traceback                              # Traceback for Exception Handling (to get the full error message with line-nbr, etc)  
import numpy as np                            # Numeric Pyscript Library (includes numeric array) 

from datetime import datetime, timedelta
#from scipy.optimize import linprog           # Scientific Pyscript Library for LP
import scipy.optimize                         # Scientific Pyscript Library for LP (from scipy.optimize import linprog causes a circular error in pyscript)

# Determine the environment (Visual Studio or Home Assistant):
try: # Assume we are running in Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
    # Do not add the home_assistant_mock.py to the Home Assistant pyscript/helios folder, it is only needed for testing in Visual Studio
    from home_assistant_mock import service, time_trigger, pyscript_compile, log, automation, task, state  # Include HA mock for testing outside of Home Assistant
    _LOGGER = log # Use the mock log for testing in Visual Studio

except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
    import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
    _LOGGER = logging.getLogger(__name__) # Get access to the Python Standard Logger in pure python functions when running in Home Assistant
    if "/config/pyscript" not in sys.path: # Already in the search path for pure python modules in Home Assistant? 
        sys.path.append("/config/pyscript") # Home Assistant Pyscript folder, Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_common.py)
#   pass  # In Home Assistant no mock is needed since service/state/log etc already exist globally!

# The HA config folder is added above to the search path (So that in Home Assistant the following helios_* modules can be found by the import statement in /config/helios_python):
from helios_python.helios_common import * # Import the Pure Python Helios Common Functions    (used also by the Helios Main)
from helios_python.helios_prices import * # Import the Pure Python Helios Energy Price Parser (used also by the Helios Main)

HELIOS_VERSION      = "0.7.8s"  # Current Helios Version
HELIOS_CALC_NAME    = "Helios Optimizer Calculate Plan"
MINUTES_PER_HOUR    = 60.0      # Conversion factor (float) from hours to minutes
PERCENTAGE_FACTOR   = 100.0     # Conversion factor (float) from number to % (e.g. kWh to %)
K_FACTOR            = 1000      # Conversion factor from kilowatt to watt (Watt is used for current values) or for SEC to MSEC
STEPS               = 24        # Default Number of Steps (24 steps of 60 minutes is one day)
STEP_SIZE           = 60        # Default Step Size (60 minutes)
PRICE_FACTOR        = 1.0       # Default Price Factor (1.0 = price is in euro per kWh, 0.001 = price is in euro per Wh, 0.01 = price is in cent per kWh) 
MAX_TIME            = 10.0      # Default Maximum Solver Time (seconds) 
MAX_ITER            = 10000     # Default Maximum Solver Iterations
MAX_GRID            = 11.0      # Default Maximum Grid Import/Export Capacity (kW)
BAT_EFF             = 0.95      # Default Charge and Discharge Efficiency Factor (Overall or Round Trip Efficiency (RTE) is bat_charge_eff * bat_disch_eff)
BAT_CAP             = 10.0      # Default Battery Capacity (kWh)
SOC_MIN             = 10.0      # Default Battery Minimum SoC (%)  
SOC_MAX             = 90.0      # Default Battery Maximum SoC (%)  
SOC_START           = 50.0      # Default Battery Start SoC (%)   - Current SoC  at the Start of the optimization 
#SOC_TARGET         = 40.0      # Default Battery Min End Target SoC (%) - Minimum Required SoC at the End of the optimization (not applicable since the SOC Minimum will be used as default)
MAX_CHARGE          = 1.2       # Default Battery Max Charge Power (kW)
MAX_DISCHARGE       = 0.8       # Default Battery Max Discharge Power (kW)
CHARGE_COST         = 0.00      # Default Battery Charge cost    per kWh in euro
DISCHARGE_COST      = 0.01      # Default Battert Discharge cost per kWh in euro (minimum of 0.01 required otherwise charging and discharging can happen together)
IMPORT_PRICE_FIXED  = 0.20      # Default Import Price when no import_prices or import_fixed is provided
EXPORT_PRICE_FIXED  = 0.05      # Default Export Price when no import_prices or import_fixed is provided
HOUSE_POWER_FIXED   = 0.5       # Default House Usage (kW) Power when no house_energy_forecast or house_power_fixed is provided, 0.5 kW is 500 Watt constant usage is 12 kWh per day
HOUSE_DAY           = 10.0      # Default House Usage for a Day (kWh) when a house_spread_hours is provide
SOLAR_ZERO          = 0.0       # Default Solar Forecast (kW) Power when no solar_energy_forecast is provided (solar forecast is zero, a fixed solar forecast makes no sense)
EV_FIXED            = 7.4       # Default Electric Vehicle (EV) Charge Power (kW) when no ev.charge_power is provided
HP_FIXED            = 2.0       # Default Heat Pump (HP) Max Power (kW) when no heat_pump.max_power is provided 
BOILER_FIXED        = 1.5       # Default Boiler Max Power (kW) when no boiler.max_power is provided
ROUND_PRICES_EURO   = 5         # Round float values for input prices 
ROUND_POWER_KW      = 3         # Round float values for power kW variables in the plan at 3 decimals 
ROUND_POWER_W       = 0         # Round float values for power W  variables in the plan at 0 decimals 
ROUND_ENERGY_KWH    = 2         # Round float values for energy variables in the plan at 2 decimal
ROUND_ENERGY_KWH2   = 4         # Round float values for energy variables in input arrays at 4 decimal (2 extra compared with energy in the plan)
ROUND_DISTRIBUTION  = 5         # Round float values for distribution of (house) daily usage over the steps per day
ROUND_BALANCE_KWH   = 3         # Round float values for energy balance delta at 4 decimal (balance must be 0)
ROUND_ENERGY_PCT    = 1         # Round float values for soc percentage variables in the plan at 1 decimal
ROUND_EFFICIENCY    = 5         # Round float values for charge/discharge efficiency
ROUND_TIME_SEC      = 3         # Round float values for time in seconds at 3 decimals
ROUND_STEP_COST     = 4         # Round step  costs in euro at 4 decimals 
ROUND_TOTAL_COST    = 2         # Round total costs in euro at 2 decimals (4 to look at differences)
MAX_DELTA_COST      = 0.01      # Allow a difference in total costs (fun and sum of steps) of 0.01 euro
MAX_DELTA_BALANCE   = 0.02      # Allow a difference in sum of balance variables of 0.02 kWh

# Helios Optimizer Calculate Plan with a return response 
# REMARK: This is now a Pure Python Function which is called asynchronous by helios_optimizer_service using the task.executor, common functies called are also pure python
# @pyscript_compile # Not needed anymore since the helios_optimizer.py is now in /pyscript/helios_python/ (pure python) folder and not in the /pyscript/ or /pyscript/modules/ (pyscript) folders, it is compiled and imported  
def helios_optimizer_calc_plan( 
    steps=STEPS,                 # 24 steps for 60 minutes is one day,  48 steps is two days
    step_size=STEP_SIZE,         # 96 steps for 15 minutes is one day, 192 steps is two days
    start_step=0,                # 0 = Determine start step automatically using current time

    price_size=None,             # None=price_size is equal to step_size (Default), resample price          arrays from price_size to step_size when not none and different
    house_size=None,             # None=house_size is equal to step_size (Default), resample house forecast arrays from house_size to step_size when not none and different
    solar_size=None,             # None=solar_size is equal to step_size (Default), resample solar forecast arrays from solar_size to step_size when not none and different
    price_factor=None,           # Price Factor 1.0 (or None)=Price in euro per kWh, 0.001=Price in euro per Wh, 0.01=Price in cent per kWh (Applicable to Import and Export Prices but not to the Source Price Data)

    max_grid_import_kw=MAX_GRID, # Maximum Grid Import Power (kW)
    max_grid_export_kw=MAX_GRID, # Maximum Grid Export Power (kW)

    solar=None,                  # Solar Parameters (dict)  : Solar Enabled, Solar Mode, Solar Energy Forecast in kWh per step 
    battery=None,                # Battery Parameters (dict): Battery Enabled, Capacity, SOC%-s (Start, Target, Min, Max), Max Charge/Discharge Power, Charge/Discharge Efficiency, Charge/Discharge Cost
    ev=None,                     # Future Electric Vehicle Charging Parameters (dict)
    heat_pump=None,              # Future Heat Pump Parameters (dict)
    boiler=None,                 # Future Boiler Parameters (dict)

    house_energy_forecast=None,  # Array with House Energy Forecast (the house usage in kWh per step)
    house_daily_usage=None,      # Optional House Daily Usage (kWh) as a total value, alternative for house forecast array, will be spread over the day using house_daily_distr
    house_daily_distr=None,      # Optional House Daily Distribution over the Day as a list of 24 values (kWh) for each hour of the day (Remark: This field can be a list but also a string with a list of values)

    import_prices=None,          # Array with Import Prices (an import price in euro per step)
    export_prices=None,          # Array with Export Prices (an export price in euro per step)
    provider_key=None,           # Provider Key for the Source Price Data (e.g. "hbc_marks" for HBC Energy Prices, "frank_energie" for Frank Energie Import Prices, etc)
    source_price_sensor=None,    # Source Price Sensor (Entity Id) (Info Only, since the Source Price Data is already retrieved from HA in the service) - Used by the Helios Service but not in Calculate Plan Function
    source_price_data=None,      # Source Price Data (alternative to import/export prices)
    source_type=None,            # Source (Price) Type (Market, Import or Export) for Source Price Data
    original_provider=None,      # Original (Energy) Provider (Only applicable when the Price Provider is not the Original Source for the Price Data) 

    # Following fixed values arguments are not provided via the helios service (yet):
    import_price_fixed=IMPORT_PRICE_FIXED, # Fixed Import Price (valid for all steps), only used when no import price array is provided
    export_price_fixed=EXPORT_PRICE_FIXED, # Fixed Export Price (valid for all steps), only used when no export price array is provided
    house_power_fixed=HOUSE_POWER_FIXED,   # House Fixed Usage  (valid for all steps), only used when no house usage  array is provided (Alternative for house_daily_usage, only used when house_daily_usage and house_energy_forecast are not provided)

    # Solver limitations, Debug and Testing arguments:
    max_time=MAX_TIME,           # Maximum time in seconds for the HiGHS Solver
    max_iterations=MAX_ITER,     # Maximum iterations      for the HiGHS Solver
    insight=INSIGHT_STD,         # Insight Level (0=No Calculation, 1=Minimum, 9=Maximum, see helios_common.py for details, Standard level is Max)
    write_files=False,           # Write Files (True=Write JSON and CSV files) - Used by the Helios Optimizer Service but not in Calculate Plan Function (Not Applicable to writing files in the VS Main)
    output_folder=None,          # Output Folder (Info Only, since the output files are written already in the service) - Used by the Helios Service but not in Calculate Plan Function

    # Current (Now) Timestamp/Datetime, Timezone and Timezone Offset for the Optimizer (determined by Helios Services using the Home Assistant Datetime Utility)
    # Use for (Regression) Testing ONLY the optimize_ts_str and optimize_off_min to Calculate (Optimize) at a specific (not current) date and time 
    now_ts=None,                 # Home Assistant Naive (no Timezone) Current Timestamp (especially important in container environments) retrieved from homeassistant.util.dt in helios_services.py (when None the OS system time is retrieved)
    now_tz=None,                 # Home Assistant Timezone used for the Optimize Timestamp 
    now_off_min=None,            # Home Assistant Timezone Offset in minutes compared to UTC (needed for lookup in arrays that do not use naive timestamps)
    optimize_ts_str=None,        # Optimize timestamp string (Default is None, Replaces the Current Timestamp as specified in now_ts
    optimize_off_min=0,          # Offset in minutes to UTC for the Timezone of the Optimize Timestamp 

#   return_response=None         # Return a result (argument only required for the Helios Optimizer Service, Calculate Plan DOES return the payload)
):
    """
    Home Energy Linear Integrated Optimization Service: Helios Optimizer - Calculate Plan:
    A Python Calculate Energy Plan Function that uses SciPy Linear/MILP Programming.
    """
    start_ts, optimize_ts  = datetime.now(), None # Start of Service Execution (Current Date and Time)
    t_current, t_start, phase_ms, run_ms = performance_count() # Initialize the performance Array and the Counter
#   _LOGGER.info(f"{HELIOS_CALC_NAME} Started: Initial Performance Array='{PERFORMANCE_ARRAY_MS}'")

    try:
        # ------------------------ PHASE ZERO A ----------------------------#
        # 0a. INITIALIZE ALL VARIABLES and ARRAYS                           #    
        # ------------------------------------------------------------------#      
        # Initialize the intermediate and output variables (Needed since a payload will be built even when an exception occurs):
        # WARNING: Do not include variables that exist in the argument list in the initialization since the input value will be reset!
#       test = -1 / 0 # Test an error in phase -1 (this exception will cause an additional exception when creating the payload since the variables below are not defined)
        res             = None  # Result variable for the (LP) optimization (no optimization has been performed yet) 
        execution_time  = None  # Execution Time  for the (LP) optimization (no optimization has been performed yet) 
        total_fun_cost  = None  # Total Cost from the LP optimization (res.fun value)
        total_grid_cost = None  # Total Cost for all steps (sum of step costs) for the grid import and export only
        total_step_cost = None  # Total Cost for all steps (sum of step costs)
        total_delta_cost= None  # Difference between total_fun_cost (res.fun) and total_step_cost
        soc_min_kwh, soc_max_kwh, soc_start_kwh, soc_target_kwh, soc_end_kwh, capacity_kwh  = 0, 0, 0, 0, 0, 0  # Unknown Energie in kwh yet 
        soc_min_pct, soc_max_pct, soc_start_pct, soc_target_pct, soc_end_pct                = 0, 0, 0, 0, 0     # Unknown SOC Percentages yet 
        max_bat_charge_kw, max_bat_disch_kw, bat_charge_eff, bat_disch_eff                  = 0, 0, 0, 0        # No Battery Maximums or Efficiency Factors available yet
        max_ev_power_kw, max_hp_power_kw, max_boil_power_kw                                 = 0, 0, 0           # No Electical Vehicle, Heatpump and Boiler Maximums available yet 

        soc_end_pct     = None  # Battery End % 
        soc_end_kwh     = None  # Battery End kWh
        end_ts          = None  # End Date Time of the Optimization Period (increased with every step of the optimization)
        calc_code       = RC_UNKNOWN # Calculation Result (-1=Unknown, 0=Success, 1=Infeasible, 2=Invalid Cost, 3-6 Other Errors (tbd), 7=Validation Failed, 8=Optimizer Exception, 9=Service Exception)
        calc_result     = None  # Result of the Calculation/Optimize and Validation (no optimize and validation done yet)
        error_message   = None  # Error Message (usually for an Exception) (no errors occured yet)
        error_stack     = None  # Detailed Error Stack (using traceback)   (no errors occured yet)

        # Initialize the indexes and enable/mode variables:
        T, start_index, base_index, active_index, end_index, base_ts, active_ts = 0, 0, 0, 0, 0, None, None # No number of steps, start/active/end index and base timestamp available yet (assume length of 0, start at 1, optimize/base at None)
        solar_enabled, bat_enabled, ev_enabled, hp_enabled, boiler_enabled, solar_mode = None, None, None, None, None, None

        # Initialize the Strategy, Power (kW) and Sum values for the active step (used later in the Current dictionary in the payload so init in case an exception occurs)
        active_strategy, active_hbc_sub_strat = 'Unknown', 'Unknown' # No Strategies available yet 
        active_house_usg_w, active_sol_for_w, active_sol_prod_w, active_grid_imp_w, active_grid_exp_w, active_grid_net_w = 0, 0, 0, 0, 0, 0
        active_bat_charge_w, active_bat_disch_w, active_bat_net_w, active_ev_power_w, active_hp_power_w, active_boil_power_w = 0, 0, 0, 0, 0, 0
        active_soc_pct, active_soc_kwh = 0, 0
#       active_step_cost, active_grid_cost = 0, 0  # Not yet used (may be in the future also part of current)
        house_input_sum_kwh, solar_input_sum_kwh, overall_sum_kwh, grid_imp_sum_kwh, grid_exp_sum_kwh, house_for_sum_kwh, house_usg_sum_kwh, sol_for_sum_kwh, sol_prod_sum_kwh, bat_disch_sum_kwh, bat_charge_sum_kwh, house_skp_sum_kwh, sol_skp_sum_kwh = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 # No totals available yet

        # Initialize the (Output) Plan Arrays (used later in the Plan dictionary in the payload so init in case an exception occurs):
#       import_prices, export_prices, house_energy_forecast, # input arrays (DO NOT initialize!)
        solar_energy_forecast = None # Input array but inside solar dictionary so needs to be initialized
        timestamps , strategy_plan = [], [] # Timestamps array for the optimization steps (length of 0 indicates that no optimization has been performed)) and Strategy Plan array
        house_for_plan, house_usg_plan, solar_for_plan, solar_prod_plan, grid_imp_plan, grid_exp_plan = [], [], [], [], [], []
        bat_charge_plan, bat_disch_plan, ev_plan, hp_plan, boil_plan = [], [], [], [], []
        soc_pct_plan, soc_kwh_plan, step_costs, grid_costs = [], [], [], []

        # ------------------------ PHASE ZERO B ----------------------------#
        # 0b. ARGUMENT VALIDATION, TIME LOGIC & AUTOMATIC START INDEX Calc  #    
        # ------------------------------------------------------------------#      
#       test = 0 / 0 # Test an error in phase 0
        # Convert the input parameters to the correct type and validate the values (raises an exception when invalid):)
        T                 = convert_int(steps     , "steps"     , min=24, max=192)         # Number of Steps (integer)
        step_size         = convert_int(step_size , "step_size" , allowed_values=[15,60])  # Step Size in Minutes (integer)
        price_size        = convert_int(price_size, "price_size", allowed_values=[15,60], allow_none=True)    # Step Size of Price          Input Arrays in Minutes (integer, default is equal to step_size) 
        house_size        = convert_int(house_size, "house_size", allowed_values=[15,60], allow_none=True)    # Step Size of House Forecast Input Arrays in Minutes (integer, default is equal to step_size) 
        solar_size        = convert_int(solar_size, "solar_size", allowed_values=[15,60], allow_none=True)    # Step Size of Solar Forecast Input Arrays in Minutes (integer, default is equal to step_size) 
        price_factor      = convert_float(price_factor, "price_factor", allow_none=True, min=0.001, max=1000) # Price Factor (float) 1.0=Price in euro per kWh, 0.001=Price in euro per Wh, 0.01=Price in cent per kWh
        delta_time        = float(step_size / MINUTES_PER_HOUR)                            # Hours per Step (e.g. 15 min is 0.25 hours per step)
        steps_per_hour    = float(MINUTES_PER_HOUR / step_size)                            # Steps per Hour (e.g. 15 min is 4.00 steps per hour)
        start_index       = convert_int  (start_step, "start_step", min=0, max=T) - 1      # Start Index (-1,0..T-1), while Start Step (0,1..T), -1=automatic start index
        days_in_period    = int(round(T * step_size / MINUTES_PER_HOUR / 24, 0))           # Number of Days in the Optimization Period (integer)
        steps_per_day     = int(round(24 * MINUTES_PER_HOUR / step_size))                  # Number of steps per day
        max_grid_import_kw= convert_float(max_grid_import_kw, "max_grid_import_kw", min=0, max=50) # Maximum Grid Import is 50 kW, Typical is 5.7 (old house=1x25A), 8.0 (1x35A, avg house), 17.3 (3x25A, current house), 24.2 (3x35A, large and expensive)
        max_grid_export_kw= convert_float(max_grid_export_kw, "max_grid_export_kw", min=0, max=50) # Maximum Grid Export is 50 kW, See above
        insight           = convert_int(insight   , "insight", allowed_values=INSIGHT_OPTIONS) # Insight in the calculation (only partly implemented! Use 8 to exclude the plan from the payload)
        now_ts            = convert_ts(now_ts           , "now_timestamp"     , None  , convert_none=True)  # Determine the Current Date and Time (Must be specified using the Home Assistant Datetime Utility)
        optimize_ts       = convert_ts(optimize_ts_str  , "optimize_timestamp", now_ts, convert_none=True)  # Determine the optimization date and time (usually None which is converted to the naive Current Home Assistant Datetime (from now_ts))
        now_off_min       = convert_int(now_off_min     , "now_off_min"       , min=-1440, max=+1440, allow_none=False) # Use the offset from the now_ts
        optimize_off_min  = convert_int(optimize_off_min, "optimize_off_min"  , min=-1440, max=+1440, allow_none=False) if optimize_ts_str else now_off_min # Use the offset from the optimize_ts unless not specified then use the offset from now_ts

        # Determine the Base (Start at 00:00) Timestamp for the Optimization Period from the Optimize Timestamp (usually based on Current Day).
        # Optimize Timestamp in the input is typically None and is already replaced above by the Current Timestamp (Day and Time) in convert_ts().
        # For (Regression) Testing purposes a specific Optimize Timestamp can be specified.
        # Remark : The Current Timestamp (now_ts) is already determined in the Pyscript Helios Optimize Service using the Home Assistant Datetime Utility (Current Timestamp in the HA Timezone).
        # Warning: If the Current Timestamp (now_ts) is None then convert_ts() will have retrieved the OS System Time (which can be tricky for HA Container environments).
        base_ts  = optimize_ts.replace(hour=0, minute=0, second=0, microsecond=0) # Start of Optimization Period is at 00:00:00.000000 of the day (usually today)

        # Determine Automatically the Start Index (when not specified) from the Optimize Timestamp (usually based on Current Hour and Minutes)
        # When Start Index is -1 (Start Step is 0), the start index is calculated using the Optimize Timestamp (otherwise the specified Start Index/Step is used)
        if start_index < 0:
            minutes_passed = (optimize_ts - base_ts).total_seconds() / MINUTES_PER_HOUR
            start_index = int(minutes_passed // step_size)
        
        # Make sure the start index is within range [0, T-1]:
        start_index = max(0, min(start_index, T)) # 0..T, for T all steps will be skipped
        remaining_steps = T - start_index # Determine how many steps are available in the optimization period (without the steps that are already in the past and are skipped)       

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, '0') # Phase 0 time in msec

        # ------------------------ PHASE ONE -------------------------------#
        # 1. CHECK INPUT ARRAYS and INPUT PARAMETERS:                       #
        # ------------------------------------------------------------------#
#       test = 1 / 0 # Test an error in phase 1
        solar_enabled  = bool(solar     and solar.get    ("enabled", True ))
        bat_enabled    = bool(battery   and battery.get  ("enabled", True ))
        ev_enabled     = bool(ev        and ev.get       ("enabled", False))
        hp_enabled     = bool(heat_pump and heat_pump.get("enabled", False))
        boiler_enabled = bool(boiler    and boiler.get   ("enabled", False))

        # Determine the expected steps sizes for the input arrays (per type) and the related expected length of the input arrays (per type):
        if price_size is None: price_size = step_size
        if house_size is None: house_size = step_size
        if solar_size is None: solar_size = step_size
        expected_price_input_len = int(round((T * step_size) / price_size, 0)) # Need to calculate the expected length for the price array since resampling may occur afterwards
        expected_house_input_len = int(round((T * step_size) / house_size, 0)) # Need to calculate the expected length for the house usage array since resampling may occur afterwards
        expected_solar_input_len = int(round((T * step_size) / solar_size, 0)) # Need to calculate the expected length for the solar forecast array since resampling may occur afterwards
        
        # Validate the provided import and export price arrays
        # If no import or export array provided then parse the source price dictionary to get the import and export price arrays (using the Helios Energy Price Parser)
        # Or (when price parsing failed) generate an array with fixed values (import_fixed and export_fixed) for all of the steps in the optimization period
        if source_price_data is not None and (import_prices is None or export_prices is None): # Source Prices are provided and Import or Export Prices are not?
            # For now when source prices are provided then assume they are from HBC and the source provider is Frank Energie (set in automation):
            energy_price_parser = HeliosEnergyPriceParser(provider_key=provider_key, config_override={"original_provider": original_provider}, target_tz=optimize_off_min) # Default Max Fallback Days is 1, Target timezone from now (+60 or 120min in NL) 
            processed_price_data = energy_price_parser.get_day_prices(price_data=source_price_data, target_step_size=step_size, lookup_ts=optimize_ts) # Get Energy Prices (Market, Import and Export) for the Optimize Day(s)

        if import_prices is None and (processed_price_data != None) and (len(processed_price_data) > 0): # No Import Price Array specified but Source Price Parsing succeeded?
            import_prices = energy_price_parser.get_simple_price_list(processed_prices=processed_price_data, price_key=TARGET_IP_KEY)
            import_price_size = step_size # The import price size is now equal to the step size since the parser has resampled the source prices to the step size
        else: # Import Price Array specified or Source Price Parsing failed!
            import_prices = [convert_float(p, f"import_price  [{i+1}]", factor=price_factor, decimals=ROUND_PRICES_EURO) for i,p in enumerate(import_prices )] if import_prices  else [convert_float(import_fixed, "import_fixed")] * expected_price_input_len
            import_price_size =  price_size # The import price size is now equal to the (input price size since no parsing has been done

        if export_prices is None and (processed_price_data != None) and (len(processed_price_data) > 0): # No Export Price Array specified but Source Price Parsing succeeded?
            export_prices = energy_price_parser.get_simple_price_list(processed_prices=processed_price_data, price_key=TARGET_EP_KEY)
            export_price_size = step_size # The export price size is now equal to the step size since the parser has resampled the source prices to the step size
        else: # Export Price Array specified or Source Price Parsing failed!
            export_prices = [convert_float(p, f"export_price  [{i+1}]", factor=price_factor, decimals=ROUND_PRICES_EURO) for i,p in enumerate(export_prices )] if export_prices  else [convert_float(export_fixed, "export_fixed")] * expected_price_input_len
            export_price_size =  price_size # The export price size is now equal to the (input) price size since no parsing has been done

        # Validate the provided simple house energy forecast array
        # If no forecast array provided then generate a forecast array using the house daily distributon and the house daily usage (or house power fixed)
        # Or (when no daily usage distribution available) an array with fixed values:
        if (house_daily_usage != None): # House Daily (Energy) Usage (kWh) is specified?
            house_energy_fixed_per_step = round(convert_float(house_daily_usage, "house_daily_usage") / steps_per_day                     , ROUND_ENERGY_KWH2) # Fixed House Energy per step (converted from House Usage Energy)
        else: # House Daily Usage is not specified so use House Fixed Power (in kW)
            house_energy_fixed_per_step = round(convert_float(house_power_fixed, "house_power_fixed"  ) / (MINUTES_PER_HOUR / house_size ), ROUND_ENERGY_KWH2) # Fixed House Energy per step (converted from Fixed House Power )

        if (house_energy_forecast != None): # House Energy Forecast array specified?
            house_energy_forecast = [convert_float(h, f"house_energy_forecast[{i+1}]", min=0, decimals=ROUND_ENERGY_KWH2) for i,h in enumerate(house_energy_forecast)] # Convert House Energy Forecast to floats
        elif (house_daily_distr != None): # House Energy Usage Distribution array specified (defines how to spread the daily energy usage over the hours of the day)
            # Generate a House Energy Forecast from the Daily Usage and the Distribution over the day (Remark: Distribution can be a list of a string of separated values and will be converted to floats in the generate function)
            house_energy_forecast = generate_forecast_for_distribution(steps_per_day * house_energy_fixed_per_step, house_daily_distr, name="house_daily_distr", decimals=ROUND_ENERGY_KWH2) # Generate a forecast array using the distribution of the energy over the hours of the day
            house_size = int((24 * MINUTES_PER_HOUR) / len(house_energy_forecast)) # The length of the house usage distribution array determines the step size of the house energy forecast (not the general step size or the specified house step size)
        else: # No forecast and no spread over the day provided so use a fixed energy per step
           house_energy_forecast = [house_energy_fixed_per_step] * expected_house_input_len # Generate a forecast array with a fixed value for all of the hours of the day

        solar_energy_forecast = solar.get("energy_forecast", [SOLAR_ZERO] * expected_price_input_len) if solar_enabled else None # Get the forecast for solar (one level deeper in the parameters then the other arrays)
        solar_energy_forecast = [convert_float(s, f"solar_energy_forecast[{i+1}]", min=0, decimals=ROUND_ENERGY_KWH2) for i,s in enumerate(solar_energy_forecast)] if solar_enabled else [SOLAR_ZERO] * expected_solar_input_len # Without solar forecast the solar array has 0.0 values

        if (insight >= INSIGHT_MAX):
            # Sum the input arrays for house usage and solar forecast 
            # The Forecast Periods can different, e.g. sum of 1 day of house forecast and sum of 2 days solar forecast
            # Note: The input arrays are summed before the resampling and especially the extending to the length of the optimization period! 
            house_input_sum_kwh, solar_input_sum_kwh = sum(house_energy_forecast), sum(solar_energy_forecast) # Use later in totals to check resampling and extending of forecasts
            _LOGGER.debug(f"Input Totals: House={round(house_input_sum_kwh, ROUND_ENERGY_KWH)}, Solar Forecast={round(solar_input_sum_kwh, ROUND_ENERGY_KWH)}")

        # Resample the input arrays when step size is not equal to the step size of the input array-s:
        # Note: For import and export price arrays that are based on the source price data the price step size is already equal to the step size (parsed and resampled in the Helios Energy Price Parser)
        if (import_price_size != step_size): # Resample of import price arrays required?
            import_prices  = resample(import_prices , import_price_size, step_size, "import prices" , kind="zero"  , dtype=float, decimals=2) # Resample import prices  from 60 to 15 min, repeat values 4x
        if (export_price_size != step_size): # Resample of export price arrays required?
            export_prices  = resample(export_prices , export_price_size, step_size, "export prices" , kind="zero"  , dtype=float, decimals=4) # Resample export prices  from 60 to 15 min, repeat values 4x 
        if (house_size != step_size): # Resample of house forecast input array required?
            house_energy_forecast = resample(house_energy_forecast, house_size, step_size, "house forecast", kind="linear", conserve_sum=True, dtype=float, decimals=ROUND_POWER_KW) # Resample house energy forecast (e.g. from 60 to 15 min), linear interpolation of forecasts (conserve sum of energy)
        if (solar_size != step_size): # Resample of solar forecast input array required?
            solar_energy_forecast = resample(solar_energy_forecast, solar_size, step_size, "solar forecast", kind="linear", conserve_sum=True, dtype=float, decimals=ROUND_POWER_KW) # Resample solar energy forecast (e.g. from 60 to 15 min), linear interpolation of forecasts (conserve sum of energy)

        if (insight >= INSIGHT_MAX):
            _LOGGER.debug(f"Resampled Totals: House={round(sum(house_energy_forecast), ROUND_ENERGY_KWH)}, Solar Forecast={round(sum(solar_energy_forecast), ROUND_ENERGY_KWH)}")
        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, '1a-Res') # Phase 1a time in msec

        # Validate the length of the input arrays (must be equal to the number of steps T)
        # Note: The input arrays can be shorter than T, for n days the input arrays can be multiplied with a maximum of n times (e.g. 24 items for 1 day, can become 48 steps for 2 days, etc)
        # This means that at least one day of data must be provided which can be extended to the number of days
        import_prices         = check_and_extend_size(import_prices , T, "import_prices" , True, steps_per_day, days_in_period-1) # Check that the length of the import_prices   array is equal to T (number of steps)
        export_prices         = check_and_extend_size(export_prices , T, "export_prices" , True, steps_per_day, days_in_period-1) # Check that the length of the export_prices   array is equal to T (number of steps)
        house_energy_forecast = check_and_extend_size(house_energy_forecast, T, "house_energy_forecast", True, steps_per_day, days_in_period-1) # Check that the length of the hourse forecast array is equal to T (number of steps)
        solar_energy_forecast = check_and_extend_size(solar_energy_forecast, T, "solar_energy_forecast", True, steps_per_day, days_in_period-1) # Check that the length of the solar forecast array is equal to T (number of steps) or multiply with a max of days

        if (insight >= INSIGHT_MAX):
            _LOGGER.debug(f"Extended Totals: House={round(sum(house_energy_forecast), ROUND_ENERGY_KWH)}, Solar Forecast={round(sum(solar_energy_forecast), ROUND_ENERGY_KWH)}")
        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, '1b-Ext') # Phase 1b time in msec

        if (solar_enabled):
            solar_mode     = solar.get("mode", "all").lower() if solar_enabled else "disabled" # Mode: all (default, no dimming or switch), modulating (dimming), binary (on/off)
            solar_mode     = solar_mode if (solar_mode in ['all','modulating','binary']) else 'all' if solar_enabled else 'disabled' # prevent invalid solar modes
        
        # JR2026-09-11: Conversion from Solar and House Energy Forecasts to Power Forecasts,
        # This requires a conversion from Energy (kWh) to Power (kW) by multiplying with steps per hour (Power = steps_per_hour * Energy or Power = Energy / delta_time):
        # Introduced an np array for improved performance (calculate only once) of the conversion, using only the first T items in the source array
        # Before the energy power forecast was set to zero when solar is disabled but this is no longer the case (only the production power forecast will be zero)
        solar_power_forecast_np = steps_per_hour * np.array(solar_energy_forecast[:T]) if solar_energy_forecast else np.zeros(T) 
        house_power_forecast_np = steps_per_hour * np.array(house_energy_forecast[:T]) if house_energy_forecast else np.zeros(T) 

        # For an enabled Battery: Get the Battery Parameters
        if bat_enabled: # Battery enabled?
            # Get the Battery Capacity and the Charge and Discharge Efficiency:
            capacity_kwh  = convert_float(battery.get("capacity_kwh"        , BAT_CAP), "battery.capacity_kwh"        , decimals=ROUND_ENERGY_KWH2)
            bat_charge_eff= convert_float(battery.get("charge_efficiency"   , BAT_EFF), "battery.charge_efficiency"   , decimals=ROUND_EFFICIENCY)
            bat_disch_eff = convert_float(battery.get("discharge_efficiency", BAT_EFF), "battery.discharge_efficiency", decimals=ROUND_EFFICIENCY)

            # Get the Battery Soc Start value in % and Determine kWH:
            soc_start_pct = convert_float(battery.get("soc_start_pct", SOC_START), "battery.soc_start_pct", decimals=ROUND_ENERGY_PCT)
            soc_start_kwh = (soc_start_pct / PERCENTAGE_FACTOR) * capacity_kwh

            # Get the Battery SoC Min and Max values in %:
            soc_min_pct = convert_float(battery.get("soc_min_pct", SOC_MIN), "battery.soc_min_pct", decimals=ROUND_ENERGY_PCT)
            soc_max_pct = convert_float(battery.get("soc_max_pct", SOC_MAX), "battery.soc_max_pct", decimals=ROUND_ENERGY_PCT)

            # Determine the Battery SoC Min and Max values in kWh
            soc_min_kwh = (soc_min_pct / PERCENTAGE_FACTOR) * capacity_kwh
            soc_max_kwh = (soc_max_pct / PERCENTAGE_FACTOR) * capacity_kwh

            # Get the Maximum Battery Charge and Discharge Power:
            max_bat_charge_kw = convert_float(battery.get("max_charge_power_kw"   , MAX_CHARGE   ), "battery.max_charge_power_kw"   , decimals=ROUND_ENERGY_KWH2)
            max_bat_disch_kw  = convert_float(battery.get("max_discharge_power_kw", MAX_DISCHARGE), "battery.max_discharge_power_kw", decimals=ROUND_ENERGY_KWH2)

            # Get the Battery Soc Target value in % and Determine kWh:
            soc_target_pct  = convert_float(battery.get("soc_target_pct", soc_min_pct), "battery.soc_target_pct", ROUND_ENERGY_PCT) # Use the SOC Min when no SOC Target (Min) is specified
            soc_target_kwh = (soc_target_pct / PERCENTAGE_FACTOR) * capacity_kwh # Requested Minium SOC Target at the end of the optimization period

            # Get the Battery Charge and Discharge Cost:
            charge_cost    = convert_float(battery.get("charge_cost"   , CHARGE_COST   ), "battery.charge_cost"   , decimals=ROUND_PRICES_EURO)
            discharge_cost = convert_float(battery.get("discharge_cost", DISCHARGE_COST), "battery.discharge_cost", decimals=ROUND_PRICES_EURO)
        
        # Optional Smart Deferrable Devices:
        if ev_enabled: # Electrical Vehicle enabled?
            max_ev_power_kw   = convert_float(ev    .get("max_power_kw", EV_FIXED    ), "ev.max_power_kw"    , decimals=ROUND_POWER_KW)

        if hp_enabled: # Heat Pump enabled?
            max_hp_power_kw   = convert_float(hp    .get("max_power_kw", HP_FIXED    ), "hp.max_power_kw"    , decimals=ROUND_POWER_KW)

        if boiler_enabled: # Boiler enabled?
            max_boil_power_kw = convert_float(boiler.get("max_power_kw", BOILER_FIXED), "boiler.max_power_kw", decimals=ROUND_POWER_KW)

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, '1c') # Phase 1c time in msec

        # ------------------------ PHASE TWO -------------------------------#
        # 2. BUILT DYNAMIC INDEX-MAP for optimization variables array       #
        # ------------------------------------------------------------------#
#       test = 2 / 0 # Test an error in phase 2
        active_vars = ["imp_power", "exp_power"] # Every optimization has an Import an an Export variable type
        if bat_enabled: # battery applicable?
            active_vars.extend(["bat_charge", "bat_disch"]) # Add a Charge and a Discharge variable type
        if solar_enabled: # solar applicable?
            active_vars.append("solar_prod") # add Solar Produced variable type
            if solar_mode == "binary":
                active_vars.append("solar_switch") # add Solar Turn on/off variable type (binary)
        if ev_enabled:
            active_vars.append("ev_charge" ) # add Electrical Vehicle (EV) Charge variable type
        if hp_enabled:
            active_vars.append("hp_power"  ) # add Heatpump (HP) Power variable type
        if boiler_enabled:
            active_vars.append("boil_power") # add Boiler Power variable type

        var_offset = {name: i for i, name in enumerate(active_vars)}
        M = len(active_vars) # Number of variable types
        total_vars = T * M # total number of variables (steps * variable types)

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 2) # Phase 2 time in msec

        # Function to determine the index in the variable array
        # Input is the step index and the variable type
        # Each variable type exist in the array once for each step
        # Return the array index
        # OLD Situation (Interleaved Layout):
        def get_idx_old(t, var_name):
           return t * M + var_offset[var_name]
        # NEW Situation (Block Layout), for improved performance via fixed indexes:
        def get_idx(t, var_name):
           return var_offset[var_name] * T + t

        idx_imp_power    = get_idx(0, "imp_power") 
        idx_exp_power    = get_idx(0, "exp_power") 
        idx_solar_prod   = get_idx(0, "solar_prod"  ) if solar_enabled  else None
        idx_solar_switch = get_idx(0, "solar_switch") if solar_enabled and (solar_mode == "binary") else None
        idx_bat_charge   = get_idx(0, "bat_charge"  ) if bat_enabled    else None
        idx_bat_disch    = get_idx(0, "bat_disch"   ) if bat_enabled    else None
        idx_ev_charge    = get_idx(0, "ev_charge"   ) if ev_enabled     else None
        idx_hp_power     = get_idx(0, "hp_power"    ) if hp_enabled     else None
        idx_boil_power   = get_idx(0, "boil_power"  ) if boiler_enabled else None
#       idx_bat_jos      = get_idx(0, "jos") # invalid offset (-> exception)

        # ------------------------ PHASE THREE -----------------------------#
        # 3. COST VECTOR (c), Upper, Lower BOUNDS and INTEGRALITY           #
        # ------------------------------------------------------------------#
#       test = 3 / 0 # Test an error in phase 3
        cost_vector  = np.zeros(total_vars)  # Cost factors for each optimization variable (default factor is 0)
        lower_bounds = np.zeros(total_vars)  # Lower Boundaries for each optimization variable (default is a minimum of 0)
        upper_bounds = np.zeros(total_vars)  # Upper Boundaries for each optimization variable (default is a maximum of 0)
        integrality  = np.zeros(total_vars)  # Integer (Binary) variable is 0 = continuous, 1 = on or off (binary)
        milp_enabled = False # Enable MILP optimizer only when binary variables are required

        # For each step determine the cost and the bounds per variable
        # Per step the cost is a import-price * import + export-price * export
        # Total cost is the sum of all step costs
        # The total cost will be minimized (more negative is good)
        # Skipped steps (in the past) are included but have zero cost since import and export are zero
        active_steps = T - start_index
        
        if (active_steps > 0):
            # Vectorized assignment for the Cost Factors of the Grid Import & Export Energy (based on the dynamic price arrays per step):
            # Only for the active steps from start_index .. T (skipped steps have 0 cost)
            # Remark: import/export_prices must first be converted to np.array-s before being multiplied with a float (delta_time)
            cost_vector[idx_imp_power + start_index : idx_imp_power + T] =  np.array(import_prices[start_index : T]) * delta_time # Cost factor per Imported kWh
            cost_vector[idx_exp_power + start_index : idx_exp_power + T] = -np.array(export_prices[start_index : T]) * delta_time # Cost factor per Exported kWh

            # Vectorized assignment for the Cost Factors of the Battery Charge and Discharge Energy (fixed cost value applicable to each active step)
            if bat_enabled: # Battery is applicable? => Set Charge/Discharge Costs
                cost_vector[idx_bat_charge + start_index : idx_bat_charge + T] = charge_cost    * delta_time # Cost factor per Charged    kWh
                cost_vector[idx_bat_disch  + start_index : idx_bat_disch  + T] = discharge_cost * delta_time # Cost factor per Discharged kWh

            # Vectorized assignment for the Upper boundaries of the Grid Import & Export Power:
            # Remark: The lower boundaries for Grid Import & Export Power are always zero (negative Import is handled via Export)!!
            upper_bounds[idx_imp_power + start_index : idx_imp_power + T] = max_grid_import_kw # Upper boundary for Grid Import in kW
            upper_bounds[idx_exp_power + start_index : idx_exp_power + T] = max_grid_export_kw # Upper boundary for Grid Export in kW

            # Vectorized assignment for the Upper boundaries of the Battery Charge and Discharge Power:
            # Remark: The lower boundaries for Grid Charge & Discharge Power are always zero (negative Charge is handled via Discharge)!
            if bat_enabled: # Battery is applicable? => Set Battery Charge/Discharge Limits
                upper_bounds[idx_bat_charge + start_index : idx_bat_charge + T] = max_bat_charge_kw    # Upper boundary for Charge    Power in kW
                upper_bounds[idx_bat_disch  + start_index : idx_bat_disch  + T] = max_bat_disch_kw # Upper boundary for Discharge Power in kW

            # Vectorized assignment for the Lower and Upper boundaries of the Solar Production:
            # Solar (all=no dimming or switch (default), modulating=dimming possible, binary=switch off or on):
            if solar_enabled:            
                if solar_mode == 'binary': # Solar Switch is possible
                    milp_enabled = True # MILP optimizer is required for binary mode
                #   lower_bounds[idx_solar_switch + start_index : idx_solar_switch + T] = 0.0 # solar_prod = 0 (Not needed: lower bound is already zero)
                    upper_bounds[idx_solar_switch + start_index : idx_solar_switch + T] = 1.0 # solar_prod = solar_power_forecast (not solar_energy_forecast)
                    integrality [idx_solar_switch + start_index : idx_solar_switch + T] = 1 # Enable integrality for Solar Switch variable
            
                else: # No Solar Switch ('all' or 'modulating')               
                #   Following step for modulating mode is not needed since the lower bounds are already zero
                #   if solar_mode == 'modulating': # Solar Dimming is possible
                #       lower_bounds[idx_solar_prod + start_index : idx_solar_prod + T] = np.zeros(T-start_index) # Minimum solar production is 0 (dimming is possible)
                    if solar_mode == 'all': # Solar Dimming is not possible (no Solar Dimming)
                        lower_bounds[idx_solar_prod + start_index : idx_solar_prod + T] = steps_per_hour * np.array(solar_energy_forecast[start_index : T])
                    upper_bounds    [idx_solar_prod + start_index : idx_solar_prod + T] = steps_per_hour * np.array(solar_energy_forecast[start_index : T])

            # Vectorized assignment for the Upper boundaries of the EV Charge Power:
            # Remark: The lower boundaries for EV Charge Power are always zero (EV Discharge is not yet supported)!
            if ev_enabled: # Electrical Vehicle enabled?
                upper_bounds[idx_ev_charge  + start_index : idx_ev_charge  + T] = max_ev_power_kw
            
            # Vectorized assignment for the Upper boundaries of the Head Pump Power:
            # Remark: The lower boundaries for Heat Pump Power are always zero (Head Pumps do not produce power)!
            if hp_enabled: # Heat Pump enabled?
                upper_bounds[idx_hp_power   + start_index : idx_hp_power   + T] = max_hp_power_kw

            # Vectorized assignment for the Upper boundaries of the Boiler Power:
            # Remark: The lower boundaries for Boiler Power are always zero (Boilers do not produce power)!
            if boiler_enabled: # Boiler enabled?
                upper_bounds[idx_boil_power + start_index : idx_boil_power + T] = max_boil_power_kw

            # Create the bounds tuple-list for SciPy Linprog:
            bounds = list(zip(lower_bounds, upper_bounds)) # (upper_bound, lower_bound) tuple for each optimization variable

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 3) # Phase 3 time in msec

        # ------------------------ PHASE FOUR ------------------------------#
        # 4. BALANCE RULES (A_eq, b_eq): Sum of Power variables is always zero
        # --------------------------------------------------------------------
        # For each step (skipped steps are excluded):
        #   1.0 x imp_power - 1.0 x exp_power + 1.0 x bat_disch - 1.0 x bat_charge + 1.0 x solar_prod - 1.0 x ev_charge - 1.0 x hp_power - 1.0 x boil_power = house_power_forecast (house usage/demand)
#       test = 4 / 0 # Test an error in phase 4
        A_eq = None # Initialize the left  side of the balance rules array (was [])
        b_eq = None # Initialize the right side of the balance rules array (was [])
        
        A_eq_factors = np.zeros((T, total_vars))
        b_eq_consts  = np.zeros(T)
        steps = np.arange(T) # [0,1,2..T-1] # Steps to be assigned (using Vectorized NP assignment)

        A_eq_factors[steps, idx_imp_power + steps] =  1.0 # Vectorized assignment for import power (all steps in one go)
        A_eq_factors[steps, idx_exp_power + steps] = -1.0 # Vectorized assignment for export power

        if bat_enabled:
            A_eq_factors[steps, idx_bat_disch  + steps] =  1.0 # Vectorized assignment for battery discharge power
            A_eq_factors[steps, idx_bat_charge + steps] = -1.0 # Vectorized assignment for battery charge power

        if solar_enabled:
            # Modulating and All Modes use solar_prod
            # for Modulating Mode: 0 <= solar_prod <= forecast
            # for All Mode: solar_prod = forecast
            if solar_mode in ["modulating", "all"]:
                A_eq_factors[steps, idx_solar_prod + steps] =  1.0 # Vectorized assignment for solar production power
            # Binary Mode uses solar_switch (0 or 1)
            # solar_switch of 1 is equal to solar_prod = forecast
            if solar_mode == "binary":
                A_eq_factors[steps, idx_solar_switch + steps] = solar_power_forecast_np[:T] # Vectorized assignment for solar switch (float already done above!)

        if ev_enabled:
            A_eq_factors[steps, idx_ev_charge  + steps] = -1.0 # Vectorized assignment for ev charge energy

        if hp_enabled:
            A_eq_factors[steps, idx_hp_power   + steps] = -1.0 # Vectorized assignment for heatpump energy

        if boiler_enabled:
            A_eq_factors[steps, idx_boil_power + steps] = -1.0 # Vectorized assignment for boiler energy

        # JR2026-09-11: Use Power instead of Energy (Array) in the equal boundaries
        b_eq_consts[start_index:T] = house_power_forecast_np[start_index:T] # Vectorized assignment for House Usage Power (as forecasted) 

        # 5. Convert to Python lists with a fast C-conversion:
        A_eq = A_eq_factors.tolist()
        b_eq = b_eq_consts .tolist()

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 4) # Phase 4 time in msec

        # ------------------------ PHASE FIVE ------------------------------#
        # 5. BATTERIJ SOC LIMITATIONS & BORDERLINE CASES (A_ub, b_ub)       #
        # ------------------------------------------------------------------#
        # Start the optimization with the specified Start SOC.
        # Optionally end the optimization above the specified end SOC.
        # Keep the battery above the Minimum SOC and below the Maximum SOC.
        # Handle the special case when the Start SOC is outside the valid range for the SOC (Min,Max).
        # Handle the border line case when the end SOC is not reachable in the optimization period.
        A_ub = []
        b_ub = []
#       test = 5 / 0 # Test an error in phase 5

        if bat_enabled:
            # Determine the indexes for the battery variables 
            factor_charge_per_dt    = bat_charge_eff * delta_time
            factor_discharge_per_dt = (1.0 / bat_disch_eff) * delta_time

            # PRE-ALLOCATIE: Calculate exactly how many rules we need
            num_rules       = (remaining_steps * 2) + 1  # 2 rules per stap (SOC-Max + SOC-Min) + 1 for SOC-Min-End

            # Allocation of a 2D NumPy array (1x reserved in memory for optimal speed) for per step the SOC Max and Min rules and overall the SOC Min End rule
            A_ub_factors = np.zeros((num_rules, total_vars)) # for each rule: factor for each variable (only battery charge and discharge variables are set in this block)
            b_ub_consts  = np.zeros(num_rules)               # for each rule: constant value
            rule_idx = 0 # Rule Index starts with the first rule

            # A. Borderline Case: Is the requested end-SOC possible in the available charge time?
            max_possible_added_kwh = remaining_steps * max_bat_charge_kw * delta_time * bat_charge_eff # Determine maximum charge capacity (kWh)
        
            # Adapt the end-SOC when infeasible for the solver in the available time (optimization period) 
            soc_target_kwh = min(soc_target_kwh, soc_start_kwh + max_possible_added_kwh) # Minimum of the requested and max possible end-SOC

            # B. Cumulative SOC rules per step
            # Keep the battery SOC above the Minimum and below the Maximum for EVERY STEP of the optimization period
            # For each step two rules are added:
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) below SOC-Max
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) above SOC-Min
            # Sum[s..T-1] ( delta_time * bat_charge_eff * delta_time * bat_charge[t] - delta_time * (1 / bat_disch_eff) * bat_disch[t]) <=  soc_max_kwh - soc_start_kwh
            # Sum[s..T-1] ( delta_time * bat_charge_eff * delta_time * bat_charge[t] - delta_time * (1 / bat_disch_eff) * bat_disch[t]) >=  soc_min_kwh - soc_start_kwh
            # Sum[s..T-1] (-delta_time * bat_charge_eff * delta_time * bat_charge[t] + delta_time * (1 / bat_disch_eff) * bat_disch[t]) <= -soc_min_kwh + soc_start_kwh (multiplied with -1)
            # LP only supports "<=" so the whole formula for soc min is multiplied with minus to go from ">=" to "<="
            #
            # The Sum per step includes in every next step an extra step charge or discharge
            # No rules are added for the steps that are before the start step
            # To prevent infeasible SOC-Min or SOC-Max rules: 
            #   Adapt the SOC-Min and SOC-Max for an under-charged (below SOC-Min) or over-charged (above SOC-Max) battery
            #   when the max charge or max discharge power is insufficient to reach the minimum or maximum SOC during the step.
            for t in range(start_index, T): # t = 0..T-1

                steps_from_start = t - start_index + 1 # steps handled since start index (for t starting at 0)

                # When starting above SOC-Max we cannot discharge faster than the max discharge power:
                max_discharge_energy_kwh = steps_from_start * max_bat_disch_kw * factor_discharge_per_dt
                step_allowed_max_kwh = max(soc_max_kwh, soc_start_kwh - max_discharge_energy_kwh)

                # When starting below the SOC-Min, we cannot charge faster than the max charge power:
                max_charge_energy_kwh = steps_from_start * max_bat_charge_kw * factor_charge_per_dt
                step_allowed_min_kwh = min(soc_min_kwh, soc_start_kwh + max_charge_energy_kwh)

                # Vectorized assignments for the battery charge/discharge variables (steps 1..t, excluding t+1, e.g. 1: 1-1, 2: 1-2) for maximum and minimum rule:
                # Add the SOC-Max rule for the current step:
                A_ub_factors[rule_idx, idx_bat_charge + start_index : idx_bat_charge + t+1] = factor_charge_per_dt      # Charge Factors for Max:    bat_charge_eff * delta_time
                A_ub_factors[rule_idx, idx_bat_disch  + start_index : idx_bat_disch  + t+1] = -factor_discharge_per_dt  # Discharge Factors for Max: -(1.0 / bat_disch_eff) * delta_time
                b_ub_consts [rule_idx] = step_allowed_max_kwh - soc_start_kwh # (Feasible) Maximum SOC - Start SOC
                rule_idx += 1 # Next is the SOC-Min rule for this step
                
                # Add the SOC-Min rule for the current step:
                A_ub_factors[rule_idx, idx_bat_charge + start_index : idx_bat_charge + t+1] = -factor_charge_per_dt     # Charge Factors for Min:    -bat_charge_eff * delta_time
                A_ub_factors[rule_idx, idx_bat_disch  + start_index : idx_bat_disch  + t+1] = factor_discharge_per_dt   # Discharge Factors for Min: (1.0 / bat_disch_eff) * delta_time  
                b_ub_consts [rule_idx] = soc_start_kwh - step_allowed_min_kwh # Start SOC - (Feasible) Minimum SOC
                rule_idx += 1 # Next is the SOC-Max rule of the next step (or after all steps the SOC-Min-End rule)

            # C. Minimale SOC End Rule for the END of the optimization period:
            # One extra rule is added:
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) above SOC-End-Min
            # Sum[s..T-1] ( delta_time * bat_charge_eff * delta_time * bat_charge[t] - delta_time * (1 / bat_disch_eff) * bat_disch[t]) >=  soc_target_kwh - soc_start_kwh
            # Sum[s..T-1] (-delta_time * bat_charge_eff * delta_time * bat_charge[t] + delta_time * (1 / bat_disch_eff) * bat_disch[t]) <= -soc_target_kwh + soc_start_kwh (multiplied with -1)
            #
            # This rule allows for an optional minimum SOC-End value for the Battery SOC at the end of the optimization period.
            # If no minimum SOC-End is specified then the optimization will empty the battery to the minimum to optimize the cost value.
            # When an SOC-End-Min < SOC-Min (e.g. 0) is provided then the SOC-Min will automatically overrule the SOC-End
            # To prevent an infeasible SOC-End-Min the SOC-End-Min value has already been adapted above. 

            # Vectorized assignments for the battery charge/discharge variables (steps 0-T-1, excluding T)
            A_ub_factors[rule_idx, idx_bat_charge + start_index : idx_bat_charge + T] = -factor_charge_per_dt   # -bat_charge_eff * delta_time
            A_ub_factors[rule_idx, idx_bat_disch  + start_index : idx_bat_disch  + T] = factor_discharge_per_dt # (1.0 / bat_disch_eff) * delta_time
            b_ub_consts [rule_idx] = -(soc_target_kwh - soc_start_kwh) # (Feasible) Minimum End SOC - Start SOC
            rule_idx += 1 # Not really a Next but the previous one is done

            A_ub = A_ub_factors.tolist() # append all A battery factors in one step
            b_ub = b_ub_consts.tolist()  # append all b battery constants in one step  

        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 5) # Phase 5 time in msec

        # ------------------------ PHASE SIX -------------------------------#
        # 6. Call SCIPY with HiGHs SOLVER                                   #
        # ------------------------------------------------------------------#
#       test = 6 / 0 # Test an error in Phase 6
        solver_options = { # Solver time and iteration limits
            "time_limit": float(max_time), # Maximum Secondes   for the Solver
            "maxiter": int(max_iterations) # Maximum Iterations for the Solver
        }

        # Calculate with LP the optimal power values for the optimization variables.
        # Calculate the total cost as the sum of the costs per step
        # Each optimization (power) variable has its own cost factor (valid in all steps).
        # Stick to the small than ('<=') and equal to ('=') rules as defined for the variables.
        # Keep the variables within the specified boundaries for each step.
        # The Optimal solution has the lowest cost value (all steps together).
#       t_start = time.perf_counter() # Start of LP run
        res = scipy.optimize.linprog(
            cost_vector,                 # Cost factors per optimization variable
            A_ub=A_ub if A_ub else None, # Left  side of smaller or equal (<=) rules
            b_ub=b_ub if b_ub else None, # Right side of smaller or equal (<=) rules
            A_eq=A_eq,                   # Left  side of = rules
            b_eq=b_eq,                   # Right side of equal (=) rules
            bounds=bounds,               # Boundaries for the optimization variables
            method="highs",              # LP method: HiGHS
            options=solver_options,      # Solver time and iteration limits
            integrality=integrality if milp_enabled else None # Allow for binary/integer variables
        )

        # Determine Step 6 (LP HiGHS run) performance:
#       t_end = time.perf_counter() # End of LP run
#       execution_time = round(K_FACTOR * (t_end - t_start), 2) # calculate execution time in milliseconds
        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, '6-LP') # Phase 6 time in msec
        execution_time = phase_ms # LP performance is also stored separately in the Payload

        # ---------------------- PHASE SEVEN -------------------------------#
        # 7. PROCESS OPTIMIZER RESULTS and DETERMINE STRATEGIES             #
        # ------------------------------------------------------------------#
        # The output arrays (*_plan) (including the timestamps) are lists that are already initialized at the top.
        # As an intermediate step the power variables in the result (res.x) are transfered to np.arrays (*_arr) for performance reasons.
        # Power Plan List:      Power np.array:     Index in res.x
        # grid_imp_plan         grid_imp_kw_arr     idx_imp_power
        # grid_exp_plan         grid_exp_kw_arr     idx_exp_power
        # house_for_plan        house_for_kw_arr    using house_power_forecast (no optimizaton variable)
        # house_usg_plan        house_usg_kw_arr    trimmed version of the house_for_kw_arr (skipped steps are zero)
        # solar_for_plan        sol_for_kw_arr      using solar_power_forecast (no optimizaton variable)
        # solar_prod_plan       sol_prod_kw_arr     idx_solar_prod (for all and modulating) & idx_solar_switch (for binary)
        # bat_charge_plan       bat_charge_kw_arr   idx_bat_charge
        # bat_disch_plan        bat_disch_kw_arr    idx_bat_disch
        # ev_plan               ev_charge_kw_arr    idx_ev_charge
        # hp_plan               hp_power_kw_arr     idx_hp_power
        # boil_plan             boil_power_kw_arr   idx_boil_power
        # Battery Energy Plan:
        # soc_kwh_plan          Calculate from soc_kwh_plan[t-1] + bat_charge_kw_arr[t] (bat_charge_kw) - bat_disch_kw_arr[t] (bat_disch_kw) (Starts with soc_start_kwh)
        # soc_pct_plan          Calculate from soc_kwh_plan[t] and capacity_kwh
        # strategy_plan         Calculate based upon

#       test = 7 / 0 # Test an error in phase 7
        if (res != None) and res.success: # Solution Found (not Infeasible)?
            current_soc_kwh = soc_start_kwh if bat_enabled else 0.0 # Current State of Charge for the Battery (kWh)
            step_ts, step_index = base_ts, 0 # Start at 00:00 today

            # Vectorized assignments and functions (for all steps in one go):
            # Use Import, Export from the optimized variables
            grid_imp_kw_arr = np.round(res.x[idx_imp_power : idx_imp_power + T], ROUND_POWER_KW) # Vectorized rounding of the import power array
            grid_exp_kw_arr = np.round(res.x[idx_exp_power : idx_exp_power + T], ROUND_POWER_KW) # Vectorized rounding of the export power array

            # JR2026-09-11: Use the (converted from Energy) Solar and House Power Forecast Arrays instead of the Energy Forecast Arrays
            # The Solar Forecast has not been part of the optimization so we just copy the (resampled and/or extended and converted from Energy) Solar Power Forecast Array
            house_for_kw_arr = np.round(house_power_forecast_np[:T], ROUND_POWER_KW) # Vectorized rounding and conversion of the house energy (kWh) forecast to the House Forecast Power Array
            sol_for_kw_arr   = np.round(solar_power_forecast_np[:T], ROUND_POWER_KW) # Vectorized rounding and conversion of the solar energy (kWh) forecast to the Solar Forecast Power array
            house_usg_kw_arr = house_for_kw_arr.copy() # Make a copy of the House Forecast Power Array in the House Usage Power Array
            house_usg_kw_arr[:start_index] = 0.0    # Reset/Trim the House Forecast Power values in the Skipped period (we want the Power Balance to be zero in the Plan)

            # Vectorized rounding of the Solar Production Power and Solar Forecast Power arrays
            if solar_enabled: # Is Solar Enabled?
                if solar_mode == "binary": # Solar On or Off only?
                    # JR2026-09-11: Use the (converted from Energy) Solar Power Forecast Arrays instead of the Energy Forecast Array
                    sol_prod_kw_arr = np.round(res.x[idx_solar_switch : idx_solar_switch + T] * solar_power_forecast_np[:T], ROUND_POWER_KW) # Maximum Solar or Nul (Convert Solar Binary Switch to Solar Production Power )
                else: # Solar 'all' or 'modulating'
                    sol_prod_kw_arr = np.round(res.x[idx_solar_prod   : idx_solar_prod   + T]                              , ROUND_POWER_KW) # 0 <= Solar Production Power <= Solar Forecast Power
            else: # Solar Disabled!
                sol_prod_kw_arr = np.zeros(T)

            # Use Battery Charge and Discharge Power from the optimized variables (but only when the battery is enabled)
            # Vectorized rounding of the battery charge and discharge arrays
            if bat_enabled: # Is Battery Enabled?
                bat_charge_kw_arr = np.round(res.x[idx_bat_charge : idx_bat_charge + T], ROUND_POWER_KW) 
                bat_disch_kw_arr  = np.round(res.x[idx_bat_disch  : idx_bat_disch  + T], ROUND_POWER_KW) 
            else:
                bat_charge_kw_arr, bat_disch_kw_arr = np.zeros(T), np.zeros(T)

            # Use Deferrable Devices Power from the optimized variables (but only when the deferrable devices is enabled)
            # Vectorized rounding of the EV charge, Heatpump and Boiler Power arrays
            ev_charge_kw_arr  = np.round(res.x[idx_ev_charge  : idx_ev_charge  + T], ROUND_POWER_KW) if ev_enabled     else np.zeros(T)
            hp_power_kw_arr   = np.round(res.x[idx_hp_power   : idx_hp_power   + T], ROUND_POWER_KW) if hp_enabled     else np.zeros(T)
            boil_power_kw_arr = np.round(res.x[idx_boil_power : idx_boil_power + T], ROUND_POWER_KW) if boiler_enabled else np.zeros(T)

            step_index = base_index # Start at the first (=0) interval in the optimization period
            for t in range(T): # for each step get variables from the optimization:
                bat_charge_kw, bat_disch_kw, house_usg_kw, sol_for_kw, sol_prod_kw = bat_charge_kw_arr[t], bat_disch_kw_arr[t], house_usg_kw_arr[t], sol_for_kw_arr[t], sol_prod_kw_arr[t] # Step values for Battery Charge, Discharge, House and Solar Forecast and Solar Production Power
                grid_exp_kw, grid_imp_kw = grid_exp_kw_arr[t], grid_imp_kw_arr[t] # Step values for Grid Import and Export Power
                ev_charge_kw, hp_power_kw, boil_power_kw = ev_charge_kw_arr[t], hp_power_kw_arr[t], boil_power_kw_arr[t] # Step values for EV, Heatpump and Boiler Power
                import_price, export_price = import_prices[t], export_prices[t] # Step values for Import and Export Price

                # Calculate Battery SoC % and KWh per step:
                if bat_enabled: # Is battery enabled?
                    # bat_charge_kw and bat_disch_kw are the values used in the balance, the delta needs to be compensated for the charge and discharge efficiency, 
                    # The battery is less charged (* efficiency) and more discharged (/ efficiency) than the values used in the balance
                    delta_kwh = float(((bat_charge_kw * bat_charge_eff) - (bat_disch_kw / bat_disch_eff)) * delta_time) # JR2026-09-05: Calculate delta kWh (convert to float since bat_charge_kw and bat_disch_kw have np.float values)
                    current_soc_kwh = max(0.0, min(capacity_kwh, current_soc_kwh + delta_kwh))
                    current_soc_pct = (current_soc_kwh * PERCENTAGE_FACTOR) / capacity_kwh # JR2026-09-13: No rounding necessary here (duplicate)
                else: # battery not enabled
                    current_soc_pct = 0.0

                # Add the current soc kwh and percentage to the plan arrays:
                # 2026-09-05 JR: Float conversion removed and added to delta_kwh which is calculated (above) from the bat_charge_kw and bat_disch_kw np.array values
                soc_kwh_plan.append(round(current_soc_kwh, ROUND_ENERGY_KWH)) 
                soc_pct_plan.append(round(current_soc_pct, ROUND_ENERGY_PCT)) 

                # Determine the (Battery) Strategy for the Step from the Power levels (for skipped steps strategy is 'Skipped')
                if t < start_index: # Step in the Past?
                    strat = 'Skipped' # Step is in the Past: always use 'Skipped'
                else: # Current or Future Step!
                    # Determine House Demand or Solar Surplus (only one of the two will have a value and the other is zero)
                    net_house_demand_kw  = max(0.0, house_usg_kw - sol_prod_kw) # House needs more than Sun is producing
                    net_solar_surplus_kw = max(0.0, sol_prod_kw - house_usg_kw) # Sun is producing more than House needs

                    if bat_charge_kw > (net_solar_surplus_kw + 0.1): # Battery charges more than Sun Surplus?
                        if import_price < 0 or sol_prod_kw < 0.05: # Negative prices or No Sun?
                            strat = 'Buy' # Buying for selling later
                            hbc_sub_strat = 'Charge'
                        elif sol_prod_kw >= bat_charge_kw: # Charging only with Sun Production 
                            strat = 'Charge Solar'
                            hbc_sub_strat = 'Charge PV'
                        else: # Charging more than Sun Production / Surplus?
                            strat = 'Charge'
                            hbc_sub_strat = 'Charge'
                    elif bat_disch_kw > (net_house_demand_kw + 0.1): # Battery discharges more than House Demand?
                        if grid_exp_kw_arr[t] > 0.05: # Profit on Discharge
                            strat = 'Sell'
                            hbc_sub_strat = 'Sell'
                        else: # Discharge without or with little Profit
                            strat = 'Discharge'
                            hbc_sub_strat = 'Sell'
                    elif bat_charge_kw > 0.05 or bat_disch_kw > 0.05: # Significant Charge or Discharge without Sun Surplus or House Demand
                        strat = 'NOM' # Self Consumption
                        hbc_sub_strat = 'Self-consumption'
                    else: # No Significant Battery Activity
                        strat = 'Disabled' # User may decide: Self Consumption, Zero Import, Standby
#                       hbc_sub_strat = 'Self-consumption'
#                       hbc_sub_strat = 'Standby / peak shave'
                        hbc_sub_strat = 'Zero import'

                strategy_plan.append(strat)

                # Keep the results for the Active (Current) Step:
                # This are mainly Power values in kW (TODO: convert already to W and round as preparation for Current Dictionary)
                if (t == start_index): # Active Step?
                    active_index         = t # start_index
                    active_ts            = step_ts
                    active_strategy      = strat
                    active_hbc_sub_strat = hbc_sub_strat

                    # Keep the Active Power Values (for start_index) in Watt (from kW)
                    active_house_usg_w = K_FACTOR * house_usg_kw
                    active_sol_for_w   = K_FACTOR * sol_for_kw
                    active_sol_prod_w  = K_FACTOR * sol_prod_kw
                    active_grid_imp_w  = K_FACTOR * grid_imp_kw
                    active_grid_exp_w  = K_FACTOR * grid_exp_kw
                    active_grid_net_w  = active_grid_imp_w - active_grid_exp_w

                    # Warning: Battery is Charging OR Discharging but currently this is not enforced by the optimization model!
                    # A rule may need to be added to enforce this but at the moment we (try) to prevent this by setting a cost for (dis)charging 
                    # These cost(s) will make the model decide between charging or discharging since doing both is more expensive
                    active_bat_charge_w = K_FACTOR * bat_charge_kw
                    active_bat_disch_w  = K_FACTOR * bat_disch_kw
                    active_bat_net_w    = active_bat_charge_w - active_bat_disch_w
                    active_ev_power_w   = K_FACTOR * ev_charge_kw
                    active_hp_power_w   = K_FACTOR * hp_power_kw
                    active_boil_power_w = K_FACTOR * boil_power_kw

                    active_soc_pct = current_soc_pct
                    active_soc_kwh = current_soc_kwh

                step_ts = step_ts + timedelta(minutes=step_size) # Timestamp for next step
                step_index += 1 # next index
        
            # Convert the np arrays to plan arrays:
            if (insight >= INSIGHT_PLAN): # Plan Insight Enabled? -> Convert NP Arrays to Lists (List will be included in the Payload later)
                # WARNING: In step 9 the current values (for the active step) are retrieved from the plan arrays => plan arrays are currently mandatory for the current values
                grid_imp_plan   = grid_imp_kw_arr  .tolist()
                grid_exp_plan   = grid_exp_kw_arr  .tolist()
                house_for_plan  = house_for_kw_arr .tolist() # House Forecast Plan is from House Forecast (skipped period is also filled)
                house_usg_plan  = house_usg_kw_arr .tolist() # House Usage    Plan is from House Forecast (but skipped period is reset to zeros)
                solar_for_plan  = sol_for_kw_arr   .tolist() # Solar Forecast Plan 
                solar_prod_plan = sol_prod_kw_arr  .tolist() # Solar Production Plan
                bat_charge_plan = bat_charge_kw_arr.tolist()
                bat_disch_plan  = bat_disch_kw_arr .tolist()
                ev_plan         = ev_charge_kw_arr .tolist()
                hp_plan         = hp_power_kw_arr  .tolist()
                boil_plan       = boil_power_kw_arr.tolist()

            # Vectorized Cost for Grid Import: 
            import_cost_arr    = np.array(import_prices[:T]) * delta_time * grid_imp_kw_arr     
            # Vectorized Provit (or Cost when negative) for Grid Export:
            export_revenue_arr = np.array(export_prices[:T]) * delta_time * grid_exp_kw_arr 
    
            # Vectorized Cost for Battery Charging and Discharging:
            charging_cost_arr    = (bat_charge_kw_arr * delta_time * charge_cost   ) if bat_enabled else np.zeros(T)
            discharging_cost_arr = (bat_disch_kw_arr * delta_time * discharge_cost) if bat_enabled else np.zeros(T)

            # Vectorized Net cost for this specific step:
            net_grid_cost_arr = import_cost_arr - export_revenue_arr
            net_step_cost_arr = net_grid_cost_arr + charging_cost_arr + discharging_cost_arr
            
            step_costs = np.round(net_step_cost_arr, ROUND_STEP_COST).tolist() 
            grid_costs = np.round(net_grid_cost_arr, ROUND_STEP_COST).tolist() 

            # Assign the timestamps for each step after filling all other plan arrays (length of timestamps array is never larger than any of the others):    
            timestamps = [datetime_isoformat(base_ts + timedelta(minutes=t * step_size)) for t in range(T)]  # Vectorized assign the timestamps array for each step (format: YYYY:MM:DD HH:MM)

            end_ts    = step_ts # End Time of last step (End of Optimization Period)
            end_index = step_index - 1 # End Index is index of last step (next step is not processed)
            soc_end_kwh = current_soc_kwh
            soc_end_pct = (PERCENTAGE_FACTOR * current_soc_kwh / capacity_kwh) if (capacity_kwh > 0) else 0

            # Sum the total cost values for the individual step optimizer costs and the indiviual grid step cost 
            # Uses .item() to convert a np.float(float_value) to its actual float_value (otherwise the output/json will have these ugly np.float() values)
            total_fun_cost  = res.fun # The Total Cost as reported by the optimizer (LP Solver)                        
            total_step_cost = np.sum(net_step_cost_arr).item() # Individual step cost as calculated above (same factors as the optimizer uses)
            total_grid_cost = np.sum(net_grid_cost_arr).item() # Individual grid step cost as calculated above (without the battery costs, only import and export)
    
        t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 7) # Phase 7 time in msec

        # ---------------------- PHASE EIGHT -------------------------------#
        # 8. VALIDATE the RESULTS and CALCULATE TOTALS:                     #
        # ------------------------------------------------------------------#
        try:
#           test = 8 / 0 # Test an error in phase 8
            if (res != None) and res.success: # Optimization successful?
                calc_result, calc_code = "Optimized", RC_SUCCESS

                if (insight >= INSIGHT_MAX): # Validation (Max) Insight Enabled? -> Check Sum of Step Costs
                    # Validate Step Costs: Total Fun Cost must equal to Sum of Step Costs (Total Delta Cost < MAX_DELTA_COST)
                    if (total_step_cost != None): # Total Step Cost available?
                        total_delta_cost = round(total_fun_cost - total_step_cost, ROUND_STEP_COST)
                        if (abs(total_delta_cost) >= MAX_DELTA_COST): # Difference between fun cost and step total at or above 0.01 euro?
                            # WARNING: The invalid cost is reported in the Calculation Code and in the Calculation Result but has NO effect on the Success of the optimization
                            calc_result, calc_code = "Cost Error", RC_INVALID_COST # Optimized successfull but step cost validation has failed
                            error_message = f"Optimization terminated successfully. (Helios Optimizer Step Cost Validation failed with a delta of {total_delta_cost})" # Replace the solver message for the step cost validation failure
                            _LOGGER.error(f"[{HELIOS_CALC_NAME}] Validation Error: Optimization Fun Cost not equal to Sum of Step Costs (Delta={total_delta_cost})")
                
                        _LOGGER.debug(f"Optimization Cost Delta: {total_delta_cost} = Fun Cost {round(total_fun_cost, ROUND_STEP_COST)} - Sum Step Costs {round(total_step_cost, ROUND_STEP_COST)}")                     

                if (insight >= INSIGHT_SUM): # Totals (Sum) Insight Enabled? -> Calculate Sums for Optimization Variables (Convert Power (kW) Variables to Energy (kWh) Sums)
                    # Calculate the Totals (Sum for all steps) for each Optimization Variable: 
                    # House and Solar Forecast are not zero for skipped steps so for these variables the skipped steps are excluded (and calculated separate)
                    # Note: The sum is calculated using the np.arrays which contain the step values for each Optimization Variable
                    #       The item() method is used to convert the np.float(float_value) to its actual float_value (Otherwise the output/json would have these ugly np.float() values)
                    # JR2026-09-11: Conversion from Solar and House Energy Forecasts to Power Forecasts (divide Power by the Steps per Hour (steps_per_hour) to get Energy):
                    house_for_sum_kwh  = np.sum(house_for_kw_arr [:T]).item()            / steps_per_hour # Sum the house forecast array
                    house_usg_sum_kwh  = np.sum(house_usg_kw_arr [:T]).item()            / steps_per_hour # Sum the optimized part of the house usage array (same as np.sum(house_for_kw_arr[start_index:T]).item())
                    house_skp_sum_kwh  = np.sum(house_for_kw_arr [0:start_index]).item() / steps_per_hour # Sum the skipped part of the house usage array
                    sol_for_sum_kwh    = np.sum(sol_for_kw_arr   [:T]).item()            / steps_per_hour # Sum the optimized part of the solar forecast array
                    sol_prod_sum_kwh   = np.sum(sol_prod_kw_arr  [:T]).item()            / steps_per_hour # Sum the solar production array  (0 for skipped steps or when solar   disabled)
                    sol_skp_sum_kwh    = np.sum(sol_for_kw_arr   [0:start_index]).item() / steps_per_hour # Sum the skipped part of the solar forecast array
                    bat_disch_sum_kwh  = np.sum(bat_disch_kw_arr [:T]).item()            / steps_per_hour # Sum the battery discharge array (0 for skipped steps or when battery disabled)
                    bat_charge_sum_kwh = np.sum(bat_charge_kw_arr[:T]).item()            / steps_per_hour # Sum the battery charge array    (0 for skipped steps or when battery disabled)
                    grid_imp_sum_kwh   = np.sum(grid_imp_kw_arr  [:T]).item()            / steps_per_hour # Sum the Grid Import array
                    grid_exp_sum_kwh   = np.sum(grid_exp_kw_arr  [:T]).item()            / steps_per_hour # Sum the Grid Export array

                if (insight >= INSIGHT_MAX): # Validation (Max) Insight Enabled? -> Check Overall Power Balance (all steps together)
                    # Validate Power Balance: Calculate the Overall Power Balance Sum = Grid Import-Export Sum + Solar Production Sum + Battery Discharge-Charge Sum - House Usage Sum (Balance must be near Zero):
                    overall_sum_kwh = grid_imp_sum_kwh + sol_prod_sum_kwh + bat_disch_sum_kwh - grid_exp_sum_kwh - bat_charge_sum_kwh - house_usg_sum_kwh
                    if abs(overall_sum_kwh) >= MAX_DELTA_BALANCE: # compare in kwh
                        # WARNING: The invalid overall sum is reported in the Calculation Code and in the Calculation Result but has NO effect on the Success of the optimization
                        calc_result, calc_code = "Balance Error", RC_INVALID_BALANCE # Optimized successful but balance validation has failed
                        error_message = f"Optimization terminated successfully. (Helios Optimizer Overall Balance Sum Validation failed with a sum of {overall_sum_kwh})" # Replaces the solver message for the balance validation failure
                        _LOGGER.error(f"[{HELIOS_CALC_NAME}] Validation Error: Optimization Overall Balance is NOT Zero ({overall_sum_kwh})")

                    _LOGGER.debug(f"Optimization({start_index+1}) Totals: {round(overall_sum_kwh, ROUND_BALANCE_KWH)}" + 
                         f" = Import {round(grid_imp_sum_kwh, ROUND_ENERGY_KWH)}" 
                         f" + Solar {round(sol_prod_sum_kwh, ROUND_ENERGY_KWH)} ({round(sol_for_sum_kwh, ROUND_ENERGY_KWH)}, {round(sol_skp_sum_kwh, ROUND_ENERGY_KWH)}) + Discharge {round(bat_disch_sum_kwh, ROUND_ENERGY_KWH)}" + 
                         f" - Export {round(grid_exp_sum_kwh, ROUND_ENERGY_KWH)} - Charge {round(bat_charge_sum_kwh, ROUND_ENERGY_KWH)} - House {round(house_usg_sum_kwh, ROUND_ENERGY_KWH)}, Skipped {round(house_skp_sum_kwh, ROUND_ENERGY_KWH)} ")                     

                    # TODO: Validate Lower and Upper Boundaries in each Step and for each Optimization Variable
                    # TODO: Validate Minimum and Maximum SOC    in each Step and for the Battery SOC Value (based upon Start SOC and Charge and Discharge Variables for previous and current steps)
                    # TODO: Validate Target SOC                 in last Step and for the Battery SOC Value (based upon Start SOC and Charge and Discharge Variables for all steps)

            else: # Optimization is infeasible (no optimum found)
                calc_result, calc_code = "Infeasible", RC_INFEASIBLE

        except Exception as e: # Exception occured in the validation phase
            error_message = f"Optimizer Step Cost Validation Failed with {repr(e)}"
            calc_result, calc_code = "Validation Failed", RC_VALIDATION_FAILED
            _LOGGER.error(f"[{HELIOS_CALC_NAME}] Exception: {error_message}")

    # Overall exception handling for the entire optimization function:
    except Exception as e: 
        error_message = f"Optimizer Calculation Failed with {repr(e)}"
        error_stack = traceback.format_exc() # Retrieve the python error stack from traceback
        calc_result, calc_code = "Optimizer Exception", RC_OPTIMIZER_EXCEPTION
        _LOGGER.error(f"\n[{HELIOS_CALC_NAME}] Exception: {error_message}")
        _LOGGER.error(f"Full Exception Message for [{HELIOS_CALC_NAME}]:")
        _LOGGER.error(error_stack)        
    
    t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 8) # Phase 8 time in msec

    # ---------------------- PHASE NINE --------------------------------#
    # 9. BUILT THE RESULTING PAYLOAD:                                   #
    # ------------------------------------------------------------------#
    optimized_plan_length = len(timestamps) # length of the optimized plan, 0 (empty) when the plan is not completely generated (last step of the plan generation is assigning the timestamps)

    # Maximum values for charge/discharge power and grid import/export in Watt 
    max_bat_charge_w  = K_FACTOR * max_bat_charge_kw if bat_enabled else 0.0
    max_bat_disch_w   = K_FACTOR * max_bat_disch_kw  if bat_enabled else 0.0
    max_grid_import_w = K_FACTOR * max_grid_import_kw
    max_grid_export_w = K_FACTOR * max_grid_export_kw
  
    stop_ts = datetime.now() # Stop of Service Execution (Current Time)
    a_b_net_w_rounded = round(active_bat_net_w, ROUND_POWER_W) # Pre-round the active_bat_net_w since it is used multiple times
    full_payload = {
        # Optimization/Solver Result and Timing: 
    #   "friendly_name": "Helios Optimized Energy Plan", # Friendly name is set in main module in the state.set() function 

        "success"         : res.success if (res != None) else False,
        "calc_code"       : calc_code,    # 0=Success (see above for other values)
        "calc_result"     : calc_result,  # Result of optimizer (solver), processing, exceptions and validation
        "optimize_time"   : datetime_string(optimize_ts) if (optimize_ts != None) else None, # Optimize Time (YYYY-MM-DD HH:MM) - Usually (HA) Current Timestamp but can be different for (Regression) Testing/Debugging
        "optimize_tz"     : str(now_tz),  # Timezone (as string) used to create the naive optimize timestamp (optimize_ts), may be needed for lookup in arrays that do not use a naive timestamp (e.g. price or forecast arrays)
        "optimize_off_min": now_off_min,  # Timezone offset in minutes compared to UTC

        "total_fun_cost"  : round(total_fun_cost , ROUND_TOTAL_COST) if total_fun_cost  else None, 
        "total_step_cost" : round(total_step_cost, ROUND_TOTAL_COST) if total_step_cost else None,    
        "total_delta_cost": total_delta_cost, # Difference between total fun and total step (already rounded at 4 decimals)
        "total_grid_cost" : round(total_grid_cost, ROUND_TOTAL_COST) if total_grid_cost else None,

        "steps"           : T,    
        "step_size"       : step_size,
        "start_step"      : start_index  + 1,

        "base_step"       : base_index   + 1, # First interval: Always 1
        "active_step"     : active_index + 1, # Based on the start step unless start step not in 1..T
        "end_step"        : end_index    + 1, # Last interval: Should be T

        "base_time"       : datetime_string(base_ts    ) if (base_ts     != None) else None, # Start of First Interval  (YYYY-MM-DD HH:MM)
        "active_time"     : datetime_string(active_ts  ) if (active_ts   != None) else None, # Start of Active Interval (Current period  )
        "end_time"        : datetime_string(end_ts     ) if (end_ts      != None) else None, # Start of Last Interval   (YYYY-MM-DD HH:MM)

        "solar_mode"      : solar_mode, # Values: "all", "modulating", "binary", "disabled" (solar not enabled)

        "battery_mode"    : "enabled" if bat_enabled else "disabled",
        "capacity_kwh"    : round(capacity_kwh  , ROUND_ENERGY_KWH) if bat_enabled else 0.0,
        "charge_eff"      : round(bat_charge_eff, ROUND_EFFICIENCY) if bat_enabled else 0.0,
        "discharge_eff"   : round(bat_disch_eff , ROUND_EFFICIENCY) if bat_enabled else 0.0,

        "soc_min_kwh"     : round(soc_min_kwh   , ROUND_ENERGY_KWH) if bat_enabled else 0.0,
        "soc_max_kwh"     : round(soc_max_kwh   , ROUND_ENERGY_KWH) if bat_enabled else 0.0,
        "soc_start_kwh"   : round(soc_start_kwh , ROUND_ENERGY_KWH) if bat_enabled and (soc_start_kwh  != None) else None,
        "soc_target_kwh"  : round(soc_target_kwh, ROUND_ENERGY_KWH) if bat_enabled and (soc_target_kwh != None) else None, # Warning: when infeasible the soc target is adapted to a feasible kwh value
        "soc_end_kwh"     : round(soc_end_kwh   , ROUND_ENERGY_KWH) if bat_enabled and (soc_end_kwh    != None) else None,

        "soc_min_pct"     : round(soc_min_pct   , ROUND_ENERGY_PCT) if bat_enabled else 0.0,
        "soc_max_pct"     : round(soc_max_pct   , ROUND_ENERGY_PCT) if bat_enabled else 0.0,
        "soc_start_pct"   : round(soc_start_pct , ROUND_ENERGY_PCT) if bat_enabled and (soc_start_pct  != None) else None,
        "soc_target_pct"  : round(soc_target_pct, ROUND_ENERGY_PCT) if bat_enabled and (soc_target_pct != None) else None, # Warning: when infeasible the soc target is adapted to a feasible percentage
        "soc_end_pct"     : round(soc_end_pct   , ROUND_ENERGY_PCT) if bat_enabled and (soc_end_pct    != None) else None,
            
        # Current Strategy and Power values for the active step (current period)
        # Remark: Plan is in kW but Current is in Watt
        "current": { # for active_index and active_ts (see above)
            "battery_strategy"    : active_strategy, # Battery Strategy (current_strategy)
            "hbc_sub_strategy"    : active_hbc_sub_strat,                                    # Active Strategy translated to a HBC Battery Sub Strategy to be used by the Helios Strategy Flow in HBC     
            "battery_net_power_w" : a_b_net_w_rounded,                                       # Net Battery Power in W: Charge is Positive (+), Discharge is Negative (-) (bat_net_w)
            "battery_power_w"     : abs(a_b_net_w_rounded),                                  # Battery Power in Watt is always positive (for Charging and Discharging), absolute value of net (bat_net_w)
            "battery_charge_w"    : (a_b_net_w_rounded   if (a_b_net_w_rounded > 0) else 0), # Charge    is only applicable when net battery power is positive (bat_net_w)
            "battery_discharge_w" : (-a_b_net_w_rounded  if (a_b_net_w_rounded < 0) else 0), # Discharge is only applicable when net battery power is negative (bat_net_w)

            "house_usage_w"       : round(active_house_usg_w , ROUND_POWER_W), # House Usage (= House Forecast) in Watt 
            "grid_power_w"        : round(active_grid_net_w  , ROUND_POWER_W), # Net Grid Power in Watt (grid_w)
            "ev_power_w"          : round(active_ev_power_w  , ROUND_POWER_W), # EV Power in Watt (ev_w)
            "hp_power_w"          : round(active_hp_power_w  , ROUND_POWER_W), # Heat Pump Power in Watt (hp_w)
            "boiler_power_w"      : round(active_boil_power_w, ROUND_POWER_W), # Boiler Power in Watt

            "max_charge_w"        : max_bat_charge_w,  # Maximum Battery Charge Power in Watt 
            "max_discharge_w"     : max_bat_disch_w,   # Maximum Battery Discharge Power in Watt
            "max_grid_import_w"   : max_grid_import_w, # Maximum Grid Import Power in Watt
            "max_grid_export_w"   : max_grid_export_w  # Maximum Grid Export Power in Watt
        },

        "version"                 : HELIOS_VERSION,
        "python"                  : PYTHON_VERSION,
        "python_details"          : PYTHON_DETAILS if (insight >= INSIGHT_MAX) else None,
        "python_info"             : PYTHON_INFO    if (insight >= INSIGHT_MAX) else None,
        "scipy"                   : SCIPY_VERSION,
        "last_run_started"        : datetime_isoformat_msec(start_ts) if (start_ts != None) else None, # Start of the Run (YYYY:MM:DD HH:MM:SS:TTT)
        "last_run_stopped"        : datetime_isoformat_msec(stop_ts ) if (stop_ts  != None) else None, # End   of the Run (YYYY:MM:DD HH:MM:SS:TTT)
        "service_calc_time_ms"    : None, # Service Calculation time is overwritten in the helios_optimizer_servic function (helios_services.py) 

        "solver_execution_time_ms": execution_time  if (execution_time != None) else 0,
        "solver_iterations"       : res.nit     if (res != None) and (res.nit != None      ) else 0,
        "solver_message"          : res.message if (res != None) and (error_message is None) else error_message, # Use the solver message unless an error message is set 

        "insight"                 : insight,       # debug level
        "write_files"             : write_files,   # writing files (params (JSON), payload (JSON) and table(CSV) to output folder
        "output_folder"           : output_folder, # output folder for writing files 
        "error_trace"             : error_stack,   # exception stack, for debugging only
        "totals"                  : None,          # sum of arrays  , for debugging and validation only 
        "performance_ms"          : None,          # for debugging only
        "plan"                    : {} # No plan added yet (Warning: Helios Graph and Table need the plan arrays)
    }
    if (insight >= INSIGHT_SUM): # Sum Insight? -> Include Totals in Payload
        # Add the totals for debugging purposes:
        full_payload["totals"] = {
           # Input Arrays (before resample and extend of the arrays, for checking)
           "house_input_kwh"      : round(house_input_sum_kwh, ROUND_ENERGY_KWH),
           "solar_input_kwh"      : round(solar_input_sum_kwh, ROUND_ENERGY_KWH),

           # Output Arrays and Overall as check:
           "house_forecast_kwh"   : round(house_for_sum_kwh  , ROUND_ENERGY_KWH),
           "house_usage_kwh"      : round(house_usg_sum_kwh  , ROUND_ENERGY_KWH),
           "solar_forecast_kwh"   : round(sol_for_sum_kwh    , ROUND_ENERGY_KWH),
           "solar_production_kwh" : round(sol_prod_sum_kwh   , ROUND_ENERGY_KWH),
           "battery_discharge_kwh": round(bat_disch_sum_kwh  , ROUND_ENERGY_KWH),
           "battery_charge_kwh"   : round(bat_charge_sum_kwh , ROUND_ENERGY_KWH),
           "grid_import_kwh"      : round(grid_imp_sum_kwh   , ROUND_ENERGY_KWH),
           "grid_export_kwh"      : round(grid_exp_sum_kwh   , ROUND_ENERGY_KWH),
           "overall_kwh"          : round(overall_sum_kwh    , ROUND_BALANCE_KWH),

           # Skipped steps for solar and house:
           "solar_skipped_kwh"    : round(sol_skp_sum_kwh    , ROUND_ENERGY_KWH),
           "house_skipped_kwh"    : round(house_skp_sum_kwh  , ROUND_ENERGY_KWH)
        }

    if (insight >= INSIGHT_PLAN): # Plan Insight? -> Include Plan Arrays in Payload
        # Complete Dayplanning for Tables/Graphs and for Testing
        # Per Step: Timestamps, Strategie, Batterij SoC percentage and SoC kWh
        #  other plan values in kW per step
        full_payload["plan"] = {
            "timestamp"           : timestamps,
            "import_prices"       : import_prices,
            "export_prices"       : export_prices,
            "step_costs"          : step_costs,
            "house_forecast_kw"   : house_for_plan, # House Forecast is the House Usage    but filled in the skipped period
            "house_usage_kw"      : house_usg_plan, # House Usage    is the House Forecast but trimmed to zero in the skipped period
            "solar_forecast_kw"   : solar_for_plan, 
            "solar_production_kw" : solar_prod_plan,
            "strategy"            : strategy_plan,
            "soc_pct"             : soc_pct_plan,
            "soc_kwh"             : soc_kwh_plan,
            "grid_import_kw"      : grid_imp_plan,
            "grid_export_kw"      : grid_exp_plan,
            "battery_discharge_kw": bat_disch_plan  if bat_enabled    else None,
            "battery_charge_kw"   : bat_charge_plan if bat_enabled    else None,
            "ev_charge_kw"        : ev_plan         if ev_enabled     else None, # Tested with fixed value array that markdown table and apexcharts with optional ev column work with dummy array: [1.0] * T,
            "heat_pump_kw"        : hp_plan         if hp_enabled     else None, 
            "boiler_kw"           : boil_plan       if boiler_enabled else None
        }
#       full_payload["plan"] = full_plan # Set the full plan arrays in the full payload

    if (insight >= INSIGHT_MAX): # Maximum Insight? -> Include Performance Info per Phase
        # Add the performance details for debugging purposes:
        full_payload["performance_ms"] = PERFORMANCE_ARRAY_MS
        
    t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 9) # Phase 9 time in msec

    # ---------------------- PHASE TEN ---------------------------------#
    # 10. RETURN the RESULT with the FULL PAYLOAD:                      #
    # ------------------------------------------------------------------#
    # Depending on the success of the optimization log the result with different logging levels:
    if (res != None) and (error_message is None):
        if res.success:
            _LOGGER.info(f"[{HELIOS_CALC_NAME}] Succeeded: {execution_time}ms (cost={round(res.fun,4)}, start_step={start_index + 1}, iterations={res.nit}).")        
        else:
            _LOGGER.warning(f"[{HELIOS_CALC_NAME}] Infeasible: {res.message}")
    else:
        _LOGGER.error(f"[{HELIOS_CALC_NAME}] Failed: {error_message}")

    # Determine the performance of the Last Phase and add the Total Run Time to the Performance Array aswell:
    t_current, t_start, phase_ms, run_ms = performance_count(t_current, t_start, 10) # Phase 10 time in msec
    PERFORMANCE_ARRAY_MS.append(f"CalcTotal={run_ms:.1f}") # Add the total time to the global performance array

    # Some detailed logging information (only applicable for debug log level):
    final_ts = datetime.now() # Stop Timestamp (stop_ts) has already been determined (and is saved in the payload) but some additional activity has been performed afterwards
    _LOGGER.debug(f"Run Time based on Timestamp: {round(K_FACTOR * (final_ts - start_ts).total_seconds(), ROUND_TIME_MSEC):.1f}ms, Performance={run_ms:.1f}ms")
    _LOGGER.debug(f"Phase Performance Array in ms:\n{PERFORMANCE_ARRAY_MS}") # Print performance array for all phases of the calculator and total run time in ms

    # Return Full Payload to the Service Trace
    # Remark: The HA Helios Optimizer Energy Plan Entity and its Attributes are now set in the Helios Optimizer Service (See helios_services.py) using the returned payload.
    return full_payload

