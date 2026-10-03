# Module: HELIOS Optimizer - Python Function to Calculate an Optimized Energy Plan                            
# Home Energy Linear Integrated Optimization Service (HELIOS Calculator)
# The Optimizer uses SciPy Linear/MILP Programming to calculated the Optimal Energy Plan 
# for Solar Production, Battery Charging/Discharging and expected House Energy Usage for Dynamic Prices during the period.
# A Solar Forecast can be specified with the expected Solar Production.
# A House Forecast can bes specified with the expected (undeferrable) Energy Usage in the House.
# In the future support for Deferrable Devices (like EV, HP and Boiler) will be added. 
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1   Started Implementation with help of Google Gemini
#   2026-08-27: JR  v0.78k Included performance measurements, Improve (PyScript) Performance for the Index in the Variable Array, Vectorized Assignments, Improved Steps: 5, Todo Steps: 4 and may be 3 
#   2026-08-28: JR  v0.78k Split off the common functies into a helios_common.py, this file now only contains the optimizer itself
#   2026-08-31: JR  v0.78l Adding input parameters to the dashboard, improved output markdown cards, adapted the payload (consistent names with kwh, kw, w, ms etc) 
#   2026-09-02: JR  v0.78m Separate input step sizes for import/export prices, house forecast and solar forecast arrays (3 values) instead of a single input step size to allow for different resampling conversions
#   2026-09-03: JR  v0.78m Allow arrays that are too long (e.g. 48 steps for 2 days while the optimization period is only 24 steps for 1 day), the extra steps will be ignored
#   2026-09-04: JR  v0.79n Added Sum (Totals) of Input Arrays and Output Arrays for validation purposes, calculated only at maximum insight level, optionally returned in the payload, error in validation when overall_sum above the threshold
#   2026-09-09: JR  v0.79o Change the Helios Optimizer to a Pure Python function, Adapted the function to use the Python _LOGGER instead of the PyScript log
#
#   Remark: For the full helios history see helios_main.py
#   
# Warning: In Visual Studio this module exists in the same folder as helios_main.py and home_assistant_mock.py, but in Home Assistant in the /config/pyscript/modules folder.

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

# Add the HA config-map to the search path if not already present (so that the helios_common module can be found by the import statement)
from helios_python.helios_common import * # Import the Helios Pure Python Common Functions

HELIOS_VERSION      = "0.7.8o"  # Current Helios Version
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
BAT_EFF             = 0.95      # Default Charge and Discharge Efficiency Factor (overall efficiency is charge_eff * discharge_eff)
BAT_CAP             = 10.0      # Default Battery Capacity (kWh)
SOC_MIN             = 10.0      # Default Battery Minimum SoC (%)  
SOC_MAX             = 90.0      # Default Battery Maximum SoC (%)  
SOC_START           = 50.0      # Default Battery Start SoC (%)   - Current SoC  at the Start of the optimization 
#SOC_TARGET         = 40.0      # Default Battery Min End Target SoC (%) - Minimum Required SoC at the End of the optimization (not applicable since the SOC Minimum will be used as default)
MAX_CHARGE          = 1.2       # Default Battery Max Charge Power (kW)
MAX_DISCHARGE       = 0.8       # Default Battery Max Discharge Power (kW)
CHARGE_COST         = 0.00      # Default Battery Charge cost    per kWh in euro
DISCHARGE_COST      = 0.01      # Default Battert Discharge cost per kWh in euro (minimum of 0.01 required otherwise charging and discharging can happen together)
IMPORT_FIXED        = 0.20      # Default Import Price when no import_prices or import_fixed is provided
EXPORT_FIXED        = 0.05      # Default Export Price when no import_prices or import_fixed is provided
HOUSE_FIXED         = 0.5       # Default House Usage (kW) Power when no house_forecast or house_fixed is provided
SOLAR_ZERO          = 0.0       # Default Solar Forecast (kW) Power when no solar_forecast is provided (solar forecast is zero, a fixed solar forecast makes no sense)
EV_FIXED            = 7.4       # Default Electric Vehicle (EV) Charge Power (kW) when no ev.charge_power is provided
HP_FIXED            = 2.0       # Default Heat Pump (HP) Max Power (kW) when no heat_pump.max_power is provided 
BOILER_FIXED        = 1.5       # Default Boiler Max Power (kW) when no boiler.max_power is provided
ROUND_POWER_KW      = 2         # Round float values for power variables in the plan at 2 decimals 
ROUND_ENERGY_KWH    = 2         # Round float values for energy variables in the plan at 2 decimal
ROUND_BALANCE_KWH   = 4         # Round float values for energy balance delta at 4 decimal (balance must be 0)
ROUND_ENERGY_PCT    = 1         # Round float values for soc percentage variables in the plan at 1 decimal
ROUND_TIME_SEC      = 3         # Round float values for time in seconds at 3 decimals
ROUND_STEP_COST     = 4         # Round step  costs in euro at 4 decimals 
ROUND_TOTAL_COST    = 2         # Round total costs in euro at 2 decimals (4 to look at differences)
MAX_DELTA_COST      = 0.01      # Allow a difference in total costs (fun and sum of steps) of 0.01 euro
MAX_DELTA_BALANCE   = 0.02      # Allow a difference in sum of balance variables of 0.02 kW

# Helios Optimizer Calculate Plan with a return response
# @pyscript_compile # Not needed anymore since the helios_optimizer.py is now in /pyscript/helios_python/ (pure python) folder and not in the /pyscript/ or /pyscript/modules/ (pyscript) folders, it is compiled and imported  
def helios_optimizer_calc_plan( 
    steps=STEPS,                 # 24 steps for 60 minutes is one day,  48 steps is two days
    step_size=STEP_SIZE,         # 96 steps for 15 minutes is one day, 192 steps is two days
    start_step=0,                # 0 = Determine start step automatically using current time
    price_size=None,             # None=price_size is equal to step_size (Default), resample price          arrays from price_size to step_size when not none and different
    house_size=None,             # None=house_size is equal to step_size (Default), resample house forecast arrays from house_size to step_size when not none and different
    solar_size=None,             # None=solar_size is equal to step_size (Default), resample solar forecast arrays from solar_size to step_size when not none and different
    price_factor=None,           # Price Factor 1.0 (or None)=Price in euro per kWh, 0.001=Price in euro per Wh, 0.01=Price in cent per kWh
    insight=INSIGHT_LEVEL,       # Insight Level (0=No Calculation, 1=Minimum, 9=Maximum, see helios_common.py for details)
    output_files=False,          # Output Files (True=Write JSON and CSV files) - Used by the Helios Optimizer Service but not in Calculate Plan Function
    output_folder=None,          # Output Folder - Used by the Helios Service but not in Calculate Plan Function
    optimize_ts=None,            # Optimize timestamp (replaces current timestamp)            
    max_time=MAX_TIME,           # Maximum time in seconds for the HiGHS Solver
    max_iterations=MAX_ITER,     # Maximum iterations      for the HiGHS Solver
    max_grid_import_kw=MAX_GRID, # Maximum Grid Import Power (kW)
    max_grid_export_kw=MAX_GRID, # Maximum Grid Export Power (kW)
    import_prices=None,          # Array with Import Prices (an import price per step)
    export_prices=None,          # Array with Export Prices (an export price per step)
    house_forecast=None,         # Array with House Usage Forecast (the house usage per step)
    import_fixed=IMPORT_FIXED,   # Fixed Import Price (valid for all steps), only used when no import price array is provided
    export_fixed=EXPORT_FIXED,   # Fixed Export Price (valid for all steps), only used when no export price array is provided
    house_fixed=HOUSE_FIXED,     # Fixed Export Price (valid for all steps), only used when no export price array is provided
    solar=None,                  # Solar Parameters 
    battery=None,                # Battery Parameters
    ev=None,                     # Future Electric Vehicle Charging Parameters
    heat_pump=None,              # Future Heat Pump Parameters
    boiler=None                  # Future Boiler Parameters
#   return_response=None         # Return a result (argument only required for the Helios Optimizer Service, Calculate Plan DOES return the payload)
):
    """
    Home Energy Linear Integrated Optimization Service: Helios Optimizer - Calculate Plan:
    A Python Calculate Energy Plan Function that uses SciPy Linear/MILP Programming.
    """

    PERFORMANCE_ARRAY_MS.clear() # Reset the global performance array
#   _LOGGER.warning(f"{HELIOS_CALC_NAME} has Started: Initial Performance Array='{PERFORMANCE_ARRAY_MS}'")
    t_current = time.perf_counter() # start processing steps
    t_start   = t_current # keep the first current in the start variable
    start_dt  = datetime.now() # Start of Service Execution (Current Date and Time)

    try:
        # Initialize the intermediate and output variables (a payload will be built even when an exception occurs):
        # WARNING: Do not include variables that exist in the argument list in the initialization since the input value will be reset!
        res             = None  # Result variable for the (LP) optimization (no optimization has been performed yet) 
        execution_time  = None  # Execution Time  for the (LP) optimization (no optimization has been performed yet) 
        total_fun_cost  = None  # Total Cost from the LP optimization (res.fun value)
        total_grid_cost = None  # Total Cost for all steps (sum of step costs) for the grid import and export only
        total_step_cost = None  # Total Cost for all steps (sum of step costs)
        total_delta_cost= None  # Difference between total_fun_cost (res.fun) and total_step_cost
        soc_min_kwh, soc_max_kwh, soc_start_kwh, soc_target_kwh, soc_end_kwh, capacity_kwh  = 0, 0, 0, 0, 0, 0  # unknown kwh yet 
        soc_min_pct, soc_max_pct, soc_start_pct, soc_target_pct, soc_end_pct                = 0, 0, 0, 0, 0     # unknown percentage yet 
        max_charge_power_kw, max_discharge_power_kw                                         = 0, 0              # No maximums available yet
        soc_end_pct     = None  # Battery End % 
        soc_end_kwh     = None  # Battery End kWh
        end_dt          = None  # End Date Time of the Optimization Period (increased with every step of the optimization)
        calc_code       = RC_UNKNOWN # Calculation Result (-1=Unknown, 0=Success, 1=Infeasible, 2=Invalid Cost, 3-6 Other Errors (tbd), 7=Validation Failed, 8=Optimizer Exception, 9=Service Exception)
        calc_result     = None  # Result of the Calculation/Optimize and Validation (no optimize and validation done yet)
        error_message   = None  # Error Message (usually for an Exception) (no errors occured yet)
        error_stack     = None  # Detailed Error Stack (using traceback)   (no errors occured yet)

        T, start_index, base_index, active_index, end_index, optimize_dt, base_dt = 0, 0, 0, 0, 0, None, None # No number of steps, start/active/end index and base timestamp available yet (assume length of 0, start at 1, optimize/base at None)
        solar_enabled, bat_enabled, ev_enabled, hp_enabled, boiler_enabled, solar_mode = None, None, None, None, None, None
        input_house_sum, input_solar_sum, overall_sum, grid_import_sum, sol_prod_sum, sol_for_sum, sol_skp_sum, bat_discharge_sum, grid_export_sum, bat_charge_sum, house_sum, skipped_sum = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 # No totals available yet
        timestamps = [] # Timestamps array for the optimization steps (length of 0 indicates that no optimization has been performed)) 

        # Initialize the output arrays of for the payload:
#       import_prices, export_prices, house_forecast, # input arrays (DO NOT initialize!)
        solar_forecast = [] 
        house_plan, solar_plan = [], []
        grid_import_plan, grid_export_plan = [], []
        bat_charge_plan, bat_discharge_plan = [], []
        ev_plan, hp_plan, boiler_plan = [], [], []
        soc_pct_plan, soc_kwh_plan = [], []
        strategy_plan = []
        step_costs, grid_costs = [], []

        # Convert the input parameters to the correct type and validate the values (raises an exception when invalid):)
        T                 = convert_int(steps     , "steps"     , min=24, max=192)         # Number of Steps (integer)
        step_size         = convert_int(step_size , "step_size" , allowed_values=[15,60])  # Step Size in Minutes (integer)
        price_size        = convert_int(price_size, "price_size", allowed_values=[15,60], allow_none=True) # Step Size of Price          Input Arrays in Minutes (integer, default is equal to step_size) 
        house_size        = convert_int(house_size, "house_size", allowed_values=[15,60], allow_none=True) # Step Size of House Forecast Input Arrays in Minutes (integer, default is equal to step_size) 
        solar_size        = convert_int(solar_size, "solar_size", allowed_values=[15,60], allow_none=True) # Step Size of Solar Forecast Input Arrays in Minutes (integer, default is equal to step_size) 
        price_factor      = convert_float(price_factor, "price_factor", allow_none=True)   # Price Factor (float) 1.0=Price in euro per kWh, 0.001=Price in euro per Wh, 0.01=Price in cent per kWh
        dt                = float(step_size / MINUTES_PER_HOUR)                            # Hours per Step (e.g. 15min is 0.25 hour)
        start_index       = convert_int  (start_step, "start_step", min=0, max=T) - 1      # Start Index (-1,0..T-1), while Start Step (0,1..T), -1=automatic start index
        days_in_period    = int(round(T * step_size / MINUTES_PER_HOUR / 24, 0))           # Number of Days in the Optimization Period (integer)
        steps_per_day     = int(round(24 * MINUTES_PER_HOUR / step_size))                  # Number of steps per day
        max_grid_import_kw= convert_float(max_grid_import_kw, "max_grid_import_kw", 0, 50) # Maximum Grid Import is 50 kW, Typical is 5.7 (old house=1x25A), 8.0 (1x35A, avg house), 17.3 (3x25A, current house), 24.2 (3x35A, large and expensive)
        max_grid_export_kw= convert_float(max_grid_export_kw, "max_grid_export_kw", 0, 50) # Maximum Grid Export is 50 kW, See above
        insight           = convert_int(insight   , "insight", allowed_values=[0,1,8,9])   # Insight in the calculation (only partly implemented! Use 8 to exclude the plan from the payload)
        optimize_dt       = convert_ts(optimize_ts, "optimize_date", start_dt)             # Determine the optimization date and time (usually current date and time, specify only a different ts for testing)

        # -------------------------------------------------------------------
        # 0. TIME LOGIC & AUTOMATIC START_INDEX Calculation (based on current time)
        # -------------------------------------------------------------------
        base_dt  = optimize_dt.replace(hour=0, minute=0, second=0, microsecond=0) # Start of Optimization Period is at 00:00 of the day (usually today)

        # When start_index is -1 (start_step is 0), the start index is calculated using the current time (otherwise the specified start step is used)
        if start_index < 0:
            minutes_passed = (optimize_dt - base_dt).total_seconds() / MINUTES_PER_HOUR
            start_index = int(minutes_passed // step_size)
        
        # Make sure the start index is within range [0, T-1]:
        # TODO: Determine if this is really what should happen !!!!
        start_index = max(0, min(start_index, T)) # 0..T, for T all steps will be skipped
        remaining_steps = T - start_index # Determine how many steps are available in the optimization period (without the steps that are already in the past and are skipped)       

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 0) # Phase 0 time in msec

        # -------------------------------------------------------------------
        # 1. CHECK INPUT ARRAYS and INPUT PARAMETERS:
        # -------------------------------------------------------------------
        solar_enabled  = bool(solar     and solar.get    ("enabled", True ))
        bat_enabled    = bool(battery   and battery.get  ("enabled", True ))
        ev_enabled     = bool(ev        and ev.get       ("enabled", False))
        hp_enabled     = bool(heat_pump and heat_pump.get("enabled", False))
        boiler_enabled = bool(boiler    and boiler.get   ("enabled", False))

        # Create arrays with fixed values when no input array is provided:
        expected_price_input_len = T if (price_size is None) else int(round((T * step_size)/price_size, 0)) # Need to calculate the expected length for the price array since resampling may occur afterwards
        expected_house_input_len = T if (price_size is None) else int(round((T * step_size)/price_size, 0)) # Need to calculate the expected length for the house usage array since resampling may occur afterwards
        expected_solar_input_len = T if (price_size is None) else int(round((T * step_size)/price_size, 0)) # Need to calculate the expected length for the solar forecast array since resampling may occur afterwards
        solar_forecast = solar.get("forecast", [SOLAR_ZERO] * expected_price_input_len) if solar_enabled else None # Get the forecase for solar (one level deeper in the parameters then the other arrays)
        import_prices  = [convert_float(p, f"import_price[{i+1}]"  , factor=price_factor, decimals=2) for i,p in enumerate(import_prices )] if import_prices  else [convert_float(import_fixed, "import_fixed")] * expected_price_input_len
        export_prices  = [convert_float(p, f"export_price[{i+1}]"  , factor=price_factor, decimals=2) for i,p in enumerate(export_prices )] if export_prices  else [convert_float(export_fixed, "export_fixed")] * expected_price_input_len
        house_forecast = [convert_float(h, f"house_forecast[{i+1}]", min=0              , decimals=2) for i,h in enumerate(house_forecast)] if house_forecast else [convert_float(house_fixed , "house_fixed" )] * expected_house_input_len
        solar_forecast = [convert_float(s, f"solar_forecast[{i+1}]", min=0              , decimals=2) for i,s in enumerate(solar_forecast)] if solar_enabled  else [SOLAR_ZERO] * expected_solar_input_len # Without solar forecast the solar array has 0.0 values

        if (insight >= INSIGHT_MAX):
            # Sum the input arrays for house usage and solar forecast 
            # The Forecast Periods can different, e.g. sum of 1 day of house forecast and sum of 2 days solar forecast
            # Note: The input arrays are summed before the resampling and especially the extending to the length of the optimization period! 
            input_house_sum = round(sum(house_forecast), 2) # Sum the input house usage forecast 
            input_solar_sum = round(sum(solar_forecast), 2) # Sum the input solar forecast
            _LOGGER.debug(f"Input Totals: House={input_house_sum}, Solar Forecast={input_solar_sum}")

        # Resample the input arrays when step size is not equal to the step size of the input array-s:
        if (price_size is not None) and (price_size != step_size): # Resample of price input arrays required?
            import_prices  = resample(import_prices , price_size, step_size, "import prices" , kind="zero"  , dtype=float, decimals=2) # Resample import prices  from 60 to 15 min, repeat values 4x
            export_prices  = resample(export_prices , price_size, step_size, "export prices" , kind="zero"  , dtype=float, decimals=4) # Resample export prices  from 60 to 15 min, repeat values 4x 
        if (house_size is not None) and (house_size != step_size): # Resample of house forecast input array required?
            house_forecast = resample(house_forecast, house_size, step_size, "house forecast", kind="linear", conserve_sum=True, dtype=float, decimals=2) # Resample house usage    from 60 to 15 min, linear interpolation of forecasts (conserve sum of energy)
        if (solar_size is not None) and (solar_size != step_size): # Resample of solar forecast input array required?
            solar_forecast = resample(solar_forecast, solar_size, step_size, "solar forecast", kind="linear", conserve_sum=True, dtype=float, decimals=2) # Resample solar forecast from 60 to 15 min, linear interpolation of forecasts (conserve sum of energy)
        t_current, phase_ms, run_ms = performance_count(t_current, t_start, '1a-Res') # Phase 1a time in msec

        # Validate the length of the input arrays (must be equal to the number of steps T)
        # Note: The input arrays can be shorter than T, for n days the input arrays can be multiplied with a maximum of n times (e.g. 24 items for 1 day, can become 48 steps for 2 days, etc)
        # This means that at least one day of data must be provided which can be extended to the number of days
        import_prices  = check_and_extend_size(import_prices , T, "import_prices" , True, steps_per_day, days_in_period-1) # Check that the length of the import_prices   array is equal to T (number of steps)
        export_prices  = check_and_extend_size(export_prices , T, "export_prices" , True, steps_per_day, days_in_period-1) # Check that the length of the export_prices   array is equal to T (number of steps)
        house_forecast = check_and_extend_size(house_forecast, T, "house_forecast", True, steps_per_day, days_in_period-1) # Check that the length of the hourse forecast array is equal to T (number of steps)

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, '1b-Ext') # Phase 1b time in msec

        solar_mode     = solar.get("mode", "all").lower() if solar_enabled else "disabled" # Mode: all (default, no dimming or switch), modulating (dimming), binary (on/off)
        solar_mode     = solar_mode if (solar_mode in ['all','modulating','binary']) else 'all' if solar_enabled else 'disabled' # prevent invalid solar modes
        solar_forecast = check_and_extend_size(solar_forecast, T, "solar_forecast", True, steps_per_day, days_in_period-1) # Check that the length of the solar forecast array is equal to T (number of steps) or multiply with a max of days

        # For an enabled Battery: Get the Battery Parameters
        if bat_enabled: # Battery enabled?
            # Get the Battery Capacity and the Charge and Discharge Efficiency:
            capacity_kwh  = convert_float(battery.get("capacity_kwh"        , BAT_CAP), "battery.capacity_kwh"        , decimals=2)
            charge_eff    = convert_float(battery.get("charge_efficiency"   , BAT_EFF), "battery.charge_efficiency"   , decimals=4)
            discharge_eff = convert_float(battery.get("discharge_efficiency", BAT_EFF), "battery.discharge_efficiency", decimals=4)

            # Get the Battery Soc Start value in % and Determine kWH:
            soc_start_pct = convert_float(battery.get("soc_start_pct", SOC_START), "battery.soc_start_pct", decimals=1)
            soc_start_kwh = (soc_start_pct / PERCENTAGE_FACTOR) * capacity_kwh

            # Get the Battery SoC Min and Max values in %:
            soc_min_pct = convert_float(battery.get("soc_min_pct", SOC_MIN), "battery.soc_min_pct", decimals=1)
            soc_max_pct = convert_float(battery.get("soc_max_pct", SOC_MAX), "battery.soc_max_pct", decimals=1)

            # Determine the Battery SoC Min and Max values in kWh
            soc_min_kwh = (soc_min_pct / PERCENTAGE_FACTOR) * capacity_kwh
            soc_max_kwh = (soc_max_pct / PERCENTAGE_FACTOR) * capacity_kwh

            # Get the Maximum Battery Charge and Discharge Power:
            max_charge_power_kw    = convert_float(battery.get("max_charge_power_kw"   , MAX_CHARGE   ), "battery.max_charge_power_kw"   , decimals=3)
            max_discharge_power_kw = convert_float(battery.get("max_discharge_power_kw", MAX_DISCHARGE), "battery.max_discharge_power_kw", decimals=3)

            # Get the Battery Soc Target value in % and Determine kWh:
            soc_target_pct  = convert_float(battery.get("soc_target_pct", soc_min_pct), "battery.soc_target_pct") # Use the SOC Min when no SOC Target (Min) is specified
            soc_target_kwh = (soc_target_pct / PERCENTAGE_FACTOR) * capacity_kwh # Requested Minium SOC Target at the end of the optimization period

            # Get the Battery Charge and Discharge Cost:
            charge_cost    = convert_float(battery.get("charge_cost"   , CHARGE_COST   ), "battery.charge_cost"   , decimals=2)
            discharge_cost = convert_float(battery.get("discharge_cost", DISCHARGE_COST), "battery.discharge_cost", decimals=2)
        
        # Optional Smart Deferrable Devices:
        if ev_enabled: # Electrical Vehicle enabled?
            max_ev_power = convert_float(ev.get("charge_power_kw", EV_FIXED    ), "ev.charge_power_kw" , decimals=4)

        if hp_enabled: # Heat Pump enabled?
            max_hp_power = convert_float(ev.get("max_power_kw"   , HP_FIXED    ), "hp.max_power_kw"    , decimals=4)

        if boiler_enabled: # Boiler enabled?
            max_boiler_power = float(boiler.get("max_power_kw"   , BOILER_FIXED), "boiler.max_power_kw", decimals=4)

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, '1c') # Phase 1c time in msec

        # -------------------------------------------------------------------
        # 2. BUILT DYNAMIC INDEX-MAP for optimization variables array
        # -------------------------------------------------------------------
        active_vars = ["import_energy", "export_energy"] # every optimization has an import an an export variable type
        if bat_enabled: # battery applicable?
            active_vars.extend(["bat_charge", "bat_discharge"]) # add a charge and a discharge variable type
        if solar_enabled: # solar applicable?
            active_vars.append("solar_prod") # add solar produced variable type
            if solar_mode == "binary":
                active_vars.append("solar_switch") # add solar turn on/off variable type (binary)
        if ev_enabled:
            active_vars.append("ev_charge"    ) # add solar charge variable type
        if hp_enabled:
            active_vars.append("hp_energy"    ) # add heatpump energy variable type
        if boiler_enabled:
            active_vars.append("boiler_energy") # add boiler energy variable type

        var_offset = {name: i for i, name in enumerate(active_vars)}
        M = len(active_vars) # Number of variable types
        total_vars = T * M # total number of variables (steps * variable types)

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 2) # Phase 2 time in msec

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

        idx_import_energy = get_idx(0, "import_energy") 
        idx_export_energy = get_idx(0, "export_energy") 
        idx_solar_prod    = get_idx(0, "solar_prod"   ) if solar_enabled  else None
        idx_solar_switch  = get_idx(0, "solar_switch" ) if solar_enabled and (solar_mode == "binary") else None
        idx_bat_charge    = get_idx(0, "bat_charge"   ) if bat_enabled    else None
        idx_bat_discharge = get_idx(0, "bat_discharge") if bat_enabled    else None
        idx_ev_charge     = get_idx(0, "ev_charge"    ) if ev_enabled     else None
        idx_hp_energy     = get_idx(0, "hp_energy"    ) if hp_enabled     else None
        idx_boiler_energy = get_idx(0, "boiler_energy") if boiler_enabled else None
#       idx_bat_jos = get_idx(0, "jos") # invalid offset (-> exception)

        # -------------------------------------------------------------------
        # 3. COST VECTOR (c), Upper and Lower BOUNDS and INTEGRALITY are determined
        # -------------------------------------------------------------------
        cost_vector  = np.zeros(total_vars)  # Cost factors for each optimization variable (default factor is 0)
#       bounds       = [(0, 0)] * total_vars # Boundaries (lower and upper) for each optimization variable (default is a tuple of (0, 0))
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
            # Remark: import/export_prices must first be converted to np.array-s before being multiplied with a float (dt)
            cost_vector[idx_import_energy + start_index : idx_import_energy + T] =  np.array(import_prices[start_index : T]) * dt # Cost factor per Imported kWh
            cost_vector[idx_export_energy + start_index : idx_export_energy + T] = -np.array(export_prices[start_index : T]) * dt # Cost factor per Exported kWh
            
            # Vectorized assignment for the Cost Factors of the Battery Charge and Discharge Energy (fixed cost value applicable to each active step)
            if bat_enabled: # Battery is applicable? => Set Charge/Discharge Costs
                cost_vector[idx_bat_charge    + start_index : idx_bat_charge    + T] = charge_cost    * dt # Cost factor per Charged    kWh
                cost_vector[idx_bat_discharge + start_index : idx_bat_discharge + T] = discharge_cost * dt # Cost factor per Discharged kWh

            # Vectorized assignment for the Upper boundaries of the Grid Import & Export Power:
            # Remark: The lower boundaries for Grid Import & Export Power are always zero (negative Import is handled via Export)!!
            upper_bounds[idx_import_energy + start_index : idx_import_energy + T] = max_grid_import_kw # Upper boundary for Grid Import in kW
            upper_bounds[idx_export_energy + start_index : idx_export_energy + T] = max_grid_export_kw # Upper boundary for Grid Export in kW

            # Vectorized assignment for the Upper boundaries of the Battery Charge and Discharge Power:
            # Remark: The lower boundaries for Grid Charge & Discharge Power are always zero (negative Charge is handled via Discharge)!
            if bat_enabled: # Battery is applicable? => Set Battery Charge/Discharge Limits
                upper_bounds[idx_bat_charge    + start_index : idx_bat_charge    + T] = max_charge_power_kw    # Upper boundary for Charge    Power in kW
                upper_bounds[idx_bat_discharge + start_index : idx_bat_discharge + T] = max_discharge_power_kw # Upper boundary for Discharge Power in kW

            # Vectorized assignment for the Lower and Upper boundaries of the Solar Production:
            # Solar (all=no dimming or switch (default), modulating=dimming possible, binary=switch off or on):
            if solar_enabled:            
                if solar_mode == 'binary': # Solar Switch is possible
                    milp_enabled = True # MILP optimizer is required for binary mode
                #   lower_bounds[idx_solar_switch + start_index : idx_solar_switch + T] = 0.0 # solar_prod = 0 (Not needed: lower bound is already zero)
                    upper_bounds[idx_solar_switch + start_index : idx_solar_switch + T] = 1.0 # solar_prod = solar_forecast
                    integrality [idx_solar_switch + start_index : idx_solar_switch + T] = 1 # Enable integrality for Solar Switch variable
            
                else: # No Solar Switch ('all' or 'modulating')               
                #   Following step for modulating mode is not needed since the lower bounds are already zero
                #   if solar_mode == 'modulating': # Solar Dimming is possible
                #       lower_bounds[idx_solar_prod + start_index : idx_solar_prod + T] = np.zeros(T-start_index) # Minimum solar production is 0 (dimming is possible)
                    if solar_mode == 'all': # Solar Dimming is not possible (no Solar Dimming)
                        lower_bounds[idx_solar_prod + start_index : idx_solar_prod + T] = np.array(solar_forecast[start_index : T])
                    upper_bounds[idx_solar_prod + start_index : idx_solar_prod + T] = solar_forecast[start_index : T]

            # Vectorized assignment for the Upper boundaries of the EV Charge Power:
            # Remark: The lower boundaries for EV Charge Power are always zero (EV Discharge is not yet supported)!
            if ev_enabled: # Electrical Vehicle enabled?
                upper_bounds[idx_ev_charge    + start_index : idx_ev_charge      + T] = max_ev_power
            
            # Vectorized assignment for the Upper boundaries of the Head Pump Power:
            # Remark: The lower boundaries for Heat Pump Power are always zero (Head Pumps do not produce power)!
            if hp_enabled: # Heat Pump enabled?
                upper_bounds[idx_hp_energy     + start_index : idx_hp_energy     + T] = max_hp_power

            # Vectorized assignment for the Upper boundaries of the Boiler Power:
            # Remark: The lower boundaries for Boiler Power are always zero (Boilers do not produce power)!
            if boiler_enabled: # Boiler enabled?
                upper_bounds[idx_boiler_energy + start_index : idx_boiler_energy + T] = max_boiler_power

            # Create the bounds tuple-list for SciPy Linprog:
            bounds = list(zip(lower_bounds, upper_bounds)) # (upper_bound, lower_bound) tuple for each optimization variable

#       for t in range(T):
            # Determine if the current step is in the past and needs to be skipped
            # Past steps will be disabled by setting the upper limit of variables to 0
            # As a result the variables for these steps can only be resolved to zero.
#           is_past = (t < start_index) # Step in the past will be skipped

            # Grid Import & Export:
#           bounds[idx_import_energy + t] = (0.0, float(max_grid_import_kw)  if not is_past else 0.0)
#           bounds[idx_export_energy + t] = (0.0, float(max_grid_export_kw)  if not is_past else 0.0)
#           cost_vector[idx_import_energy + t] =  import_prices[t] * dt # Cost factor per imported kWh
#           cost_vector[idx_export_energy + t] = -export_prices[t] * dt # Cost factor per exported kWh

            # Battery: 
#           if bat_enabled:
#               bounds[idx_bat_charge    + t] = (0.0, max_charge_power_kw    if not is_past else 0.0)
#               bounds[idx_bat_discharge + t] = (0.0, max_discharge_power_kw if not is_past else 0.0)

                # Give charging and discharging a small cost 
                # TODO: Make the charging and discharging cost configurable
                # 0.0001 per kWh did not work so now using 0.01 for discharge only
                # This will prevent the solver to charge and discharge at the same time!
#               if not is_past:
#                   cost_vector[idx_bat_charge    + t] = charge_cost    * dt # Cost factor per charged kWh
#                   cost_vector[idx_bat_discharge + t] = discharge_cost * dt # Cost factor per discharged kWh
        
            # Solar (all=no dimming or switch (default), modulating=dimming possible, binary=switch off or on):
#           if solar_enabled:            
#               if solar_mode == 'binary': # Solar Switch is possible
#                   sol_sw_min = 0.0  # solar_prod = 0
#                   sol_sw_max = 1.0  # solar_prod = solar_forecst
#                   milp_enabled = True # MILP optimizer required

                #   idx_ss = get_idx(t, "solar_switch") 
#                   bounds     [idx_solar_switch + t] = (sol_sw_min, sol_sw_max)
#                   integrality[idx_solar_switch + t] = 1 # Enable integrality for Solar Switch variable
            
#               else: # No Solar Switch ('all' or 'modulating')
#                   sol_pw_max = float(solar_forecast[t]) if not is_past else 0.0 # Maximum Solar Production is the Forecasted value (or 0 for past steps)
#                   if solar_mode == 'modulating': # Solar Dimming is possible
#                       sol_pw_min = 0.0 # Minimum solar production is 0 (dimming is possible)
#                   else: # 'all' (no Solar Dimming)
#                       sol_pw_min = sol_pw_max # solar_prod = solar_forecast (Solar Production is full Solar Forecast, Dimming is not possible)

                #   idx_sp = get_idx(t, "solar_prod") 
#                   bounds[idx_solar_prod + t] = (sol_pw_min, sol_pw_max)

            # Optional Smart Deferrable Devices:
#           if ev_enabled: # Electrical Vehicle enabled?
#               ev_p   = float(ev.get("charge_power"    , EV_FIXED    )) if not is_past else 0.0   
            #   bounds[get_idx(t, "ev_charge"   )] = (0.0, ev_p)
#               bounds[idx_ev_charge + t] = (0.0, ev_p)

#           if hp_enabled: # Heat Pump enabled?
#               hp_p   = float(heat_pump.get("max_power", HP_FIXED    )) if not is_past else 0.0
            #   bounds[get_idx(t, "hp_energy"    )] = (0.0, hp_p)
#               bounds[idx_hp_energy  + t] = (0.0, hp_p)

#           if boiler_enabled: # Boiler enabled?
#               boil_p = float(boiler.get("max_power"   , BOILER_FIXED)) if not is_past else 0.0
            #   bounds[get_idx(t, "boiler_energy")] = (0.0, boil_p)
#               bounds[idx_boiler_energy + t] = (0.0, boil_p)
    
        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 3) # Phase 3 time in msec

        # -------------------------------------------------------------------
        # 4. BALANCE RULES (A_eq, b_eq): Sum of all Power variables is always zero
        # 
        # -------------------------------------------------------------------
        # For each step:
        #   1.0 x import_energy - 1.0 x export_energy + 1.0 x bat_discharge - 1.0 x bat_charge + 1.0 x solar_prod - 1.0 x ev_charge - 1.0 x hp_energy - 1.0 x boiler_energy = house_forecast (house demand)
        A_eq = None # Initialize the left  side of the balance rules array (was [])
        b_eq = None # Initialize the right side of the balance rules array (was [])
        
        A_eq_factors = np.zeros((T, total_vars))
        b_eq_consts  = np.zeros(T)
        steps = np.arange(T) # [0,1,2..T-1] # Steps to be assigned (using Vectorized NP assignment)

        A_eq_factors[steps, idx_import_energy + steps] =  1.0 # Vectorized assignment for import power (all steps in one go)
        A_eq_factors[steps, idx_export_energy + steps] = -1.0 # Vectorized assignment for export power

        if bat_enabled:
            A_eq_factors[steps, idx_bat_discharge + steps] =  1.0 # Vectorized assignment for battery discharge power
            A_eq_factors[steps, idx_bat_charge    + steps] = -1.0 # Vectorized assignment for battery charge power

        if solar_enabled:
            # Modulating and All Modes use solar_prod
            # for Modulating Mode: 0 <= solar_prod <= forecast
            # for All Mode: solar_prod = forecast
            if solar_mode in ["modulating", "all"]:
                A_eq_factors[steps, idx_solar_prod + steps] =  1.0 # Vectorized assignment for solar production power
            # Binary Mode uses solar_switch (0 or 1)
            # solar_switch of 1 is equal to solar_prod = forecast
            if solar_mode == "binary":
                A_eq_factors[steps, idx_solar_switch + steps] = solar_forecast[:T] # Vectorized assignment for solar switch (float already done above!)

        if ev_enabled:
            A_eq_factors[steps, idx_ev_charge     + steps] = -1.0 # Vectorized assignment for ev charge energy

        if hp_enabled:
            A_eq_factors[steps, idx_hp_energy     + steps] = -1.0 # Vectorized assignment for heatpump energy

        if boiler_enabled:
            A_eq_factors[steps, idx_boiler_energy + steps] = -1.0 # Vectorized assignment for boiler energy

        b_eq_consts[start_index:T] = house_forecast[start_index:T] # Vectorized assignment for house usage energy (as forecasted)

        # 5. Zet om naar Python lists via de snelle C-conversie
        A_eq = A_eq_factors.tolist()
        b_eq = b_eq_consts .tolist()

#       A_eq = None # Initialize the left  side of the balance rules array (was [])
#       b_eq = None # Initialize the right side of the balance rules array (was [])

#       for t in range(start_index, T): # For each step: # t = start_index..T-1 (before start_index all factors and constants are already 0)
##          is_past = (t < start_index) # Step in the past have balance 0 (all variables will be 0)

##          row = np.zeros(total_vars)
##          row[idx_import_energy + t] =  1.0
##          row[idx_export_energy + t] = -1.0
#           A_eq_factors[t, idx_import_energy + t] =  1.0
#           A_eq_factors[t, idx_export_energy + t] = -1.0           

#           if bat_enabled:
##              row[idx_bat_discharge + t] =  1.0
##              row[idx_bat_charge    + t] = -1.0
#               A_eq_factors[t, idx_bat_discharge + t] =  1.0
#               A_eq_factors[t, idx_bat_charge    + t] = -1.0

#           if solar_enabled:
#               # Modulating and All Modes use solar_prod
#               # for Modulating Mode: 0 <= solar_prod <= forecast
#               # for All Mode: solar_prod = forecast
#               if solar_mode in ["modulating", "all"]:
##                  row[idx_solar_prod + t] =  1.0
#                   A_eq_factors[t, idx_solar_prod + t] =  1.0
#               # Binary Mode uses solar_switch (0 or 1)
#               # solar_switch of 1 is equal to solar_prod = forecast
#               if solar_mode == "binary":
##                  row[idx_solar_switch + t] = float(solar_forecast[t])
#                   A_eq_factors[t, idx_solar_switch + t] = float(solar_forecast[t])

#           if ev_enabled:
##              row[idx_ev_charge + t] = -1.0
#               A_eq_factors[t, idx_ev_charge + t] = -1.0

#           if hp_enabled:
##              row[idx_hp_energy + t] = -1.0
#               A_eq_factors[t, idx_hp_energy + t] = -1.0

#           if boiler_enabled:
##              row[idx_boiler_energy + t] = -1.0
#               A_eq_factors[t, idx_boiler_energy + t] = -1.0

##          A_eq.append(row)
#           A_eq.append(A_eq_factors[t])

#           if is_past:
#               b_eq.append(0.0)
#           else:
#           net_house_demand = house_forecast[t] # - solar_forecast[t]
#           b_eq_consts[t] = net_house_demand
#           b_eq.append(net_house_demand)
#           b_eq.append(b_eq_consts[t])

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 4) # Phase 4 time in msec

        # -------------------------------------------------------------------
        # 5. BATTERIJ SOC LIMITATIONS & BORDERLINE CASES (A_ub, b_ub)
        # -------------------------------------------------------------------
        # Start the optimization with the specified start SoC
        # Optionally end the optimization above the specified end SoC
        # Keep the battery above the minimum SoC and below the maximum SoC
        # Handle the special case when the start SoC is outside the min, max SoC
        # Handle the border line case when the end SoC is not reachable in the optimization period

        A_ub = []
        b_ub = []

        if bat_enabled:
            # Determine the indexes for the battery variables 
#           idx_bat_charge    = get_idx(0, "bat_charge")
#           idx_bat_discharge = get_idx(0, "bat_discharge")
            factor_charge_per_dt    = charge_eff * dt
            factor_discharge_per_dt = (1.0 / discharge_eff) * dt

            # PRE-ALLOCATIE: Calculate exactly how many rules we need
            num_rules       = (remaining_steps * 2) + 1  # 2 rules per stap (SOC-Max + SOC-Min) + 1 for SOC-Min-End

            # Allocation of a 2D NumPy array (1x reserved in memory for optimal speed) for per step the SOC Max and Min rules and overall the SOC Min End rule
            A_ub_factors = np.zeros((num_rules, total_vars)) # for each rule: factor for each variable (only battery charge and discharge variables are set in this block)
            b_ub_consts  = np.zeros(num_rules)               # for each rule: constant value
            rule_idx = 0 # Rule Index starts with the first rule

            # A. Borderline Case: Is the requested end-SOC possible in the available charge time?
            max_possible_added_kwh = remaining_steps * max_charge_power_kw * dt * charge_eff # Determine maximum charge capacity (kWh)
        
            # Adapt the end-SOC when infeasible for the solver in the available time (optimization period) 
            soc_target_kwh = min(soc_target_kwh, soc_start_kwh + max_possible_added_kwh) # Minimum of the requested and max possible end-SOC

            # B. Cumulative SOC rules per step
            # Keep the battery SOC above the Minimum and below the Maximum for EVERY STEP of the optimization period
            # For each step two rules are added:
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) below SOC-Max
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) above SOC-Min
            # Sum[s..T-1] ( dt * charge_eff dt * bat_charge[t] - dt * (1 / discharge_eff) * bat_discharge[t]) <=  soc_max_kwh - soc_start_kwh
            # Sum[s..T-1] ( dt * charge_eff dt * bat_charge[t] - dt * (1 / discharge_eff) * bat_discharge[t]) >=  soc_min_kwh - soc_start_kwh
            # Sum[s..T-1] (-dt * charge_eff dt * bat_charge[t] + dt * (1 / discharge_eff) * bat_discharge[t]) <= -soc_min_kwh + soc_start_kwh (multiplied with -1)
            # LP only supports "<=" so the whole formula for soc min is multiplied with minus to go from ">=" to "<="
            #
            # The Sum per step includes in every next step an extra step charge or discharge
            # No rules are added for the steps that are before the start step
            # To prevent infeasible SOC-Min or SOC-Max rules: 
            #   Adapt the SOC-Min and SOC-Max for an under-charged (below SOC-Min) or over-charged (above SOC-Max) battery
            #   when the max charge or max discharge power is insufficient to reach the minimum or maximum SOC during the step.

#           for t in range(1, T + 1): # t = 1..T
#               if t <= start_index:
#                   continue # Current step is before the start index
            for t in range(start_index, T): # t = 0..T-1

#               steps_from_start = t - start_index # steps handle since start index (for t starting at 1)
                steps_from_start = t - start_index + 1 # steps handled since start index (for t starting at 0)

                # When starting above SOC-Max we cannot discharge faster than the max discharge power:
                max_discharge_kwh = steps_from_start * max_discharge_power_kw * factor_discharge_per_dt
                step_allowed_max_kwh = max(soc_max_kwh, soc_start_kwh - max_discharge_kwh)

                # When starting below the SOC-Min, we cannot charge faster than the max charge power:
                max_charge_kwh = steps_from_start * max_charge_power_kw * factor_charge_per_dt
                step_allowed_min_kwh = min(soc_min_kwh, soc_start_kwh + max_charge_kwh)

#               # Initiate the multipliers of the maximum and minimum rules with 0's (future steps are excluded from the sum) - Now: pre-allocated in 2D NumPy array
#               row_max = np.zeros(total_vars)
#               row_min = np.zeros(total_vars)                

                # Fill the multipliers for all steps until and including the current step
                # Remark: The sum includes the skipped steps (before the start step) but the charge and discharge values for these steps will be zero anyway
#               for i in range(t):                # i = 0..t-1 (t   x, excluding t  ..T-1, where above t = 1..T  )
#               for i in range(start_index, t+1): # i = s..t   (t+1 x, excluding t+1..T-1, where above t = 0..T-1)
#                   row_max[get_idx(i, "bat_charge"   )] = charge_eff * dt
#                   row_max[get_idx(i, "bat_discharge")] = -(1.0 / discharge_eff) * dt
#                   row_min[get_idx(i, "bat_charge"   )] = -charge_eff * dt
#                   row_min[get_idx(i, "bat_discharge")] = (1.0 / discharge_eff) * dt

                # Vectorized assignments for the battery charge/discharge variables (steps 1..t, excluding t+1, e.g. 1: 1-1, 2: 1-2) for maximum and minimum rule:
                # Add the SOC-Max rule for the current step:
                A_ub_factors[rule_idx, idx_bat_charge    + start_index : idx_bat_charge    + t+1] = factor_charge_per_dt      # Charge Factors for Max:    charge_eff * dt
                A_ub_factors[rule_idx, idx_bat_discharge + start_index : idx_bat_discharge + t+1] = -factor_discharge_per_dt  # Discharge Factors for Max: -(1.0 / discharge_eff) * dt
                b_ub_consts [rule_idx] = step_allowed_max_kwh - soc_start_kwh # (Feasible) Maximum SOC - Start SOC
#               A_ub.append(A_ub_factors[rule_idx]) # Array with Multipliers for charge and discharge values for the current step (Maximum SOC rule)
#               b_ub.append(b_ub_consts [rule_idx]) # Constant for (Feasible) Max Soc rule
                rule_idx += 1 # Next is the SOC-Min rule for this step
                
                # Add the SOC-Min rule for the current step:
                A_ub_factors[rule_idx, idx_bat_charge    + start_index : idx_bat_charge    + t+1] = -factor_charge_per_dt     # Charge Factors for Min:    -charge_eff * dt
                A_ub_factors[rule_idx, idx_bat_discharge + start_index : idx_bat_discharge + t+1] = factor_discharge_per_dt   # Discharge Factors for Min: (1.0 / discharge_eff) * dt  
                b_ub_consts [rule_idx] = soc_start_kwh - step_allowed_min_kwh # Start SOC - (Feasible) Minimum SOC
#               A_ub.append(A_ub_factors[rule_idx]) # Array with Multipliers for charge and discharge values for the current step (Minimum SOC rule)
#               b_ub.append(b_ub_consts [rule_idx]) # Constant for (Feasible) SOC-Min rule
                rule_idx += 1 # Next is the SOC-Max rule of the next step (or after all steps the SOC-Min-End rule)

            # C. Minimale SOC End Rule for the END of the optimization period:
            # One extra rule is added:
            # - Keep the sum of the SOC-Start + Sum (Charged - Discharged) above SOC-End-Min
            # Sum[s..T-1] ( dt * charge_eff dt * bat_charge[t] - dt * (1 / discharge_eff) * bat_discharge[t]) >=  soc_target_kwh - soc_start_kwh
            # Sum[s..T-1] (-dt * charge_eff dt * bat_charge[t] + dt * (1 / discharge_eff) * bat_discharge[t]) <= -soc_target_kwh + soc_start_kwh (multiplied with -1)
            #
            # This rule allows for an optional minimum SOC-End value for the Battery SOC at the end of the optimization period.
            # If no minimum SOC-End is specified then the optimization will empty the battery to the minimum to optimize the cost value.
            # When an SOC-End-Min < SOC-Min (e.g. 0) is provided then the SOC-Min will automatically overrule the SOC-End
            # To prevent an infeasible SOC-End-Min the SOC-End-Min value has already been adapted above. 

#           row_end = np.zeros(total_vars) # Now: pre-allocated in 2D NumPy array
#           for t in range(start_index, T): # t=s..T-1
#               row_end[get_idx(t, "bat_charge")]    = -charge_eff * dt
#               row_end[get_idx(t, "bat_discharge")] = (1.0 / discharge_eff) * dt
            # Vectorized assignments for the battery charge/discharge variables (steps 0-T-1, excluding T)
            A_ub_factors[rule_idx, idx_bat_charge    + start_index : idx_bat_charge    + T] = -factor_charge_per_dt   # -charge_eff * dt
            A_ub_factors[rule_idx, idx_bat_discharge + start_index : idx_bat_discharge + T] = factor_discharge_per_dt # (1.0 / discharge_eff) * dt
            b_ub_consts [rule_idx] = -(soc_target_kwh - soc_start_kwh) # (Feasible) Minimum End SOC - Start SOC
#           A_ub.append(A_ub_factors[rule_idx]) # Array with Multipliers for charge and discharge values for all steps (Minimum SOC End rule)
#           b_ub.append(b_ub_consts [rule_idx]) # Constant for (Feasible) SOC-End-Min rule
            rule_idx += 1 # Not really a Next but the previous one is done

            A_ub = A_ub_factors.tolist() # append all A battery factors in one step
            b_ub = b_ub_consts.tolist()  # append all b battery constants in one step  

        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 5) # Phase 5 time in msec

        # -------------------------------------------------------------------
        # 6. Call SCIPY with HiGHs SOLVER
        # -------------------------------------------------------------------
        solver_options = { # Solver time and iteration limits
            "time_limit": float(max_time), # Maximum Secondes   for the Solver
            "maxiter": int(max_iterations) # Maximum Iterations for the Solver
        }

        # Calculate with LP the optimal values of the optimization variables
        # Calculate the cost as the sum of the cost per step
        # Each optimization variable has its own cost factor (valid in all steps)
        # Stick to the ('<=' and '=') rules as defined for the variables
        # Keep the variables within the specified boundaries for each step
        # The Optimal solution has the lowest cost value (all steps together)
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
        t_current, phase_ms, run_ms = performance_count(t_current, t_start, '6-LP') # Phase 6 time in msec
        execution_time = phase_ms # LP performance is also stored separately

        # -------------------------------------------------------------------
        # 7. PROCESS RESULTS and DETERMINE STRATEGIES
        # -------------------------------------------------------------------
        # The output arrays (including the timestamps) are already defined at the top:    
        if res.success:
            current_soc_kwh = soc_start_kwh if bat_enabled else 0.0 # Current State of Charge for the Battery (kWh)
            step_dt, step_index = base_dt, 0 # Start at 00:00 today

            # Vectorized assignments and functions (for all steps in one go):
            # Use Import, Export from the optimized variables
            imp_arr = np.round(res.x[idx_import_energy : idx_import_energy + T], ROUND_POWER_KW) # Vectorized rounding of the import power array
            exp_arr = np.round(res.x[idx_export_energy : idx_export_energy + T], ROUND_POWER_KW) # Vectorized rounding of the export power array

            # Use Solar and House Power from the Forecasts:
            house_arr     = np.round(house_forecast[:T], ROUND_POWER_KW) # Vectorized rounding of the house usage forecast power array
            sol_for_arr   = np.round(solar_forecast[:T], ROUND_POWER_KW) if solar_enabled else np.zeros(T) # Vectorized rounding of the solar forecast power array

            # Use Solar Production from the optimized variables (solar switch or production):
            # Vectorized rounding of the solar production array
            if solar_enabled: # Is Solar Enabled?
                if solar_mode == "binary": # Solar On or Off only?
                    sol_prod_arr = np.round(res.x[idx_solar_switch : idx_solar_switch + T] * solar_forecast[:T], ROUND_POWER_KW) # Maximum Solar or Nul
                else: # # Solar 'all' or 'modulating'
                    sol_prod_arr = np.round(res.x[idx_solar_prod   : idx_solar_prod   + T]                     , ROUND_POWER_KW) # 0 <= Production <= Forecast
            else: # Solar Disabled!
                sol_prod_arr = np.zeros(T)

            # Use Battery Charge and Discharge Power from the optimized variables (but only when the battery is enabled)
            # Vectorized rounding of the battery charge and discharge arrays
            if bat_enabled: # Is Battery Enabled?
                c_p_arr = np.round(res.x[idx_bat_charge    : idx_bat_charge    + T], ROUND_POWER_KW) 
                d_p_arr = np.round(res.x[idx_bat_discharge : idx_bat_discharge + T], ROUND_POWER_KW) 
            else:
                c_p_arr, d_p_arr = np.zeros(T), np.zeros(T)

            # Use Deferrable Devices Power from the optimized variables (but only when the deferrable devices is enabled)
            # Vectorized rounding of the EV charge, Heatpump and Boiler Power arrays
            ev_p_arr   = np.round(res.x[idx_ev_charge     : idx_ev_charge     + T], ROUND_POWER_KW) if ev_enabled     else np.zeros(T)
            hp_p_arr   = np.round(res.x[idx_hp_energy     : idx_hp_energy     + T], ROUND_POWER_KW) if hp_enabled     else np.zeros(T)
            boil_p_arr = np.round(res.x[idx_boiler_energy : idx_boiler_energy + T], ROUND_POWER_KW) if boiler_enabled else np.zeros(T)

            step_index = base_index # Start at the first (=0) interval in the optimization period
            for t in range(T): # for each step get variables from the optimization:
#               timestamps.append(step_dt.isoformat(timespec="minutes").replace('T',' ') if step_dt is not None else None) # Timestamp for start of next step

                # Use Import, Export from the optimized variables
#               imp     = round(float(res.x[idx_import_energy + t]), ROUND_POWER_KW)
#               exp     = round(float(res.x[idx_export_energy + t]), ROUND_POWER_KW)

                # Use Solar and House Power from the Forecasts:
#               house   = round(house_forecast[t], ROUND_POWER_KW)
#               sol_for = round(solar_forecast[t], ROUND_POWER_KW) if solar_enabled else 0.0

                # Use Solar Production from the optimized variables (solar switch or production):
#               if solar_enabled: # Is Solar Enabled?
#                   if solar_mode == "binary": # Solar On or Off only?
#                       sol_prod= round(int  (res.x[idx_solar_switch + t]) * sol_for_arr[t], ROUND_POWER_KW) # Maximum Solar or Nul
#                   else: # Solar 'all' or 'modulating'
#                       sol_prod= round(float(res.x[idx_solar_prod   + t])                 , ROUND_POWER_KW) # 0 <= Production <= Forecast
#               else: # 'disabled'
#                   sol_prod = 0.0

                # Use Battery Charge and Discharge Power from the optimized variables (but only when the battery is enabled)
#               c_p     = round(float(res.x[idx_bat_charge    + t]), ROUND_POWER_KW) if bat_enabled    else 0.0
#               d_p     = round(float(res.x[idx_bat_discharge + t]), ROUND_POWER_KW) if bat_enabled    else 0.0

                # Use Deferrable Devices Power from the optimized variables (but only when the deferrable devices is enabled)
#               ev_p    = round(float(res.x[idx_ev_charge     + t]), ROUND_POWER_KW) if ev_enabled     else 0.0
#               hp_p    = round(float(res.x[idx_hp_energy     + t]), ROUND_POWER_KW) if hp_enabled     else 0.0
#               boil_p  = round(float(res.x[idx_boiler_energy + t]), ROUND_POWER_KW) if boiler_enabled else 0.0

                # Calculate Battery SoC % and KWh per step:
                c_p, d_p, house, sol_prod = c_p_arr[t], d_p_arr[t], house_arr[t], sol_prod_arr[t]
                if bat_enabled: # Is battery enabled?
                    delta_kwh = float(((c_p * charge_eff) - (d_p / discharge_eff)) * dt) # 2026-09-05 JR: Calculate delta kWh (convert to float since c_p and d_p have np.float values)
                    current_soc_kwh = max(0.0, min(capacity_kwh, current_soc_kwh + delta_kwh))
                    current_soc_pct = round((current_soc_kwh / capacity_kwh) * PERCENTAGE_FACTOR, ROUND_ENERGY_KWH)
                else: # battery not enabled
                    current_soc_pct = 0.0

                # Add the current soc kwh and percentage to the plan arrays:
                # 2026-09-05 JR: Float conversion removed and added to delta_kwh which is calculated (above) from the c_p and d_p np.array values
                soc_kwh_plan .append(round(current_soc_kwh, ROUND_ENERGY_KWH)) 
                soc_pct_plan .append(round(current_soc_pct, ROUND_ENERGY_PCT)) 

                # Determine (Battery) Strategy (with 'Skipped' for skipped steps)
                if t < start_index:
                    strat = "Skipped"
                else:
                    net_house_demand  = max(0.0, house - sol_prod)
                    net_solar_surplus = max(0.0, sol_prod - house)

                    if c_p > (net_solar_surplus + 0.1):
                        if import_prices[t] < 0 or sol_prod < 0.05:
                            strat = "Buy"
                        elif sol_prod >= c_p:
                            strat = "Charge Solar"
                        else:
                            strat = "Charge"
                    elif d_p > (net_house_demand + 0.1):
                        if exp_arr[t] > 0.05:
                            strat = "Sell"
                        else:
                            strat = "Discharge"
                    elif c_p > 0.05 or d_p > 0.05:
                        strat = "NOM"
                    else:
                        strat = "Disabled"

                strategy_plan.append(strat)

                # Append variable value for the step to the payload arrays:
                # Variables are now rounded in one step for the whole np.array
#               grid_import_plan.append(imp)
#               grid_export_plan.append(exp)
#               house_plan.append(house)
#               solar_plan.append(sol_prod)
#               bat_charge_plan.append(c_p)
#               bat_discharge_plan.append(d_p)                               
#               ev_plan.append(ev_p)
#               hp_plan.append(hp_p)
#               boiler_plan.append(boil_p)
            
                # Cost for Grid Import: 
#               import_cost    = import_prices[t] * dt * imp_arr[t]     
                # Provit (or Cost when negative) for Grid Export:
#               export_revenue = export_prices[t] * dt * exp_arr[t] 
    
                # Cost for Battery Charging and Discharging:
#               charging_cost     = (float(c_p_arr[t]) * dt * charge_cost   ) if bat_enabled else 0.0
#               discharging_cost  = (float(d_p_arr[t]) * dt * discharge_cost) if bat_enabled else 0.0

                # Net cost for this specific step:
#               net_grid_cost = import_cost - export_revenue
#               net_step_cost = net_grid_cost + charging_cost + discharging_cost
#               step_costs.append(round(float(net_step_cost), ROUND_STEP_COST)) # float needed ?????
#               grid_costs.append(round(float(net_grid_cost), ROUND_STEP_COST)) # float needed ?????

                step_dt = step_dt + timedelta(minutes=step_size) # Timestamp for next step
                step_index += 1 # next index
        
            # Convert the np arrays to plan arrays:
            if (insight >= INSIGHT_PLAN):
                # WARNING: In step 9 the current values (for the active step) are retrieved from the plan arrays => plan arrays are currently mandatory for the current values
                # TODO: This step 9 needs to be adapted so that the current values are retrieved from the *_arr or even better from the res.x[*] variables 
                grid_import_plan   = imp_arr     .tolist()
                grid_export_plan   = exp_arr     .tolist()
                house_plan         = house_arr   .tolist() # House Forecast is also House Usage Plan
                solar_forecast     = sol_for_arr .tolist() # Solar Forecast (2026-0-24: rounded, before not rounded!)
                solar_plan         = sol_prod_arr.tolist() # Solar Production Plan
                bat_charge_plan    = c_p_arr     .tolist()
                bat_discharge_plan = d_p_arr     .tolist()
                ev_plan            = ev_p_arr    .tolist()
                hp_plan            = hp_p_arr    .tolist()
                boiler_plan        = boil_p_arr  .tolist()

            # Vectorized Cost for Grid Import: 
            import_cost_arr    = np.array(import_prices[:T]) * dt * imp_arr     
            # Vectorized Provit (or Cost when negative) for Grid Export:
            export_revenue_arr = np.array(export_prices[:T]) * dt * exp_arr 
    
            # Vectorized Cost for Battery Charging and Discharging:
            charging_cost_arr    = (c_p_arr * dt * charge_cost   ) if bat_enabled else np.zeros(T)
            discharging_cost_arr = (d_p_arr * dt * discharge_cost) if bat_enabled else np.zeros(T)

            # Vectorized Net cost for this specific step:
            net_grid_cost_arr = import_cost_arr - export_revenue_arr
            net_step_cost_arr = net_grid_cost_arr + charging_cost_arr + discharging_cost_arr
            
            step_costs = np.round(net_step_cost_arr, ROUND_STEP_COST).tolist() 
            grid_costs = np.round(net_grid_cost_arr, ROUND_STEP_COST).tolist() 

            # Assign the timestamps for each step after filling all other plan arrays (length of timestamps array is never larger than any of the others):    
            timestamps = [datetime_isoformat(base_dt + timedelta(minutes=t * step_size)) for t in range(T)]  # Vectorized assign the timestamps array for each step (format: YYYY:MM:DD HH:MM)

            end_dt    = step_dt # End Time of last step (End of Optimization Period)
            end_index = step_index - 1 # End Index is index of last step (next step is not processed)
            soc_end_kwh = current_soc_kwh
            soc_end_pct = (PERCENTAGE_FACTOR * current_soc_kwh / capacity_kwh) if (capacity_kwh > 0) else 0

            # Sum the total cost values and round with ROUND_STEP_COST decimals (not yet to ROUND_TOTAL_COST, first need to compare)
            # Uses .item() to convert a np.float(float_value) to its actual float_value (otherwise the output/json will have these ugly np.float() values)
            total_fun_cost  = round(res.fun                         , ROUND_STEP_COST ) 
            total_step_cost = round(np.sum(net_step_cost_arr).item(), ROUND_STEP_COST ) 
            total_grid_cost = round(np.sum(net_grid_cost_arr).item(), ROUND_TOTAL_COST)  
    
        t_current, phase_ms, run_ms = performance_count(t_current, t_start, 7) # Phase 7 time in msec

        # -------------------------------------------------------------------
        # 8. VALIDATE THE RESULTS AND CALCULATE TOTALS:
        # -------------------------------------------------------------------
        try:
            if res.success: # Optimization successful?
                calc_result, calc_code = "Optimized", RC_SUCCESS

                if (insight >= INSIGHT_MAX):
                    # Validate Step Costs: Total Fun Cost must equal to Sum of Step Costs (Total Delta Cost < MAX_DELTA_COST)
                    if (total_step_cost is not None): # Total Step Cost available?
                        total_delta_cost = round(total_fun_cost - total_step_cost, ROUND_STEP_COST)
                        if (abs(total_delta_cost) >= MAX_DELTA_COST): # Difference between fun cost and step total at or above 0.01 euro?
                            # WARNING: The invalid cost is reported in the Calculation Code and in the Calculation Result but has NO effect on the Success of the optimization
                            calc_result, calc_code = "Cost Error", RC_INVALID_COST # Optimized successfull but step cost validation has failed
                            error_message = f"Optimization terminated successfully. (Helios Optimizer Step Cost Validation failed with a delta of {total_delta_cost})" # Replace the solver message for the step cost validation failure
                            _LOGGER.error(f"Optimization Fun Cost not equal to Sum of Step Costs: {total_delta_cost}")
                
                        _LOGGER.debug(f"Optimization Cost Delta: {total_delta_cost} = Fun Cost {total_fun_cost} - Sum Step Costs {total_step_cost}")                     

                        # Round to the final number of decimals (after the compare, before already rounded to ROUND_STEP_COST):
                        total_fun_cost  = round(total_fun_cost , ROUND_TOTAL_COST)
                        total_step_cost = round(total_step_cost, ROUND_TOTAL_COST)

                    # Calculate the Totals (Sum for all steps) for each Optimization Variable: 
                    # House and Solar Forecast are not zero for skipped steps so for these variables the skipped steps are excluded (and calculated separate))
                    # Note: The sum is calculated using the np.arrays which contain the step values for each Optimization Variable
                    #       The item() method is used to convert the np.float(float_value) to its actual float_value (Otherwise the output/json would have these ugly np.float() values)
                    grid_import_sum   = np.sum(imp_arr     [:T]).item() # Sum the Grid Import array
                    grid_export_sum   = np.sum(exp_arr     [:T]).item() # sum the Grid Export array
                    house_sum         = np.sum(house_arr   [start_index:T]).item() # sum the optimized part of the house usage array
                    skipped_sum       = np.sum(house_arr   [0:start_index]).item() # sum the skipped part of the house usage array
                    sol_for_sum       = np.sum(sol_for_arr [start_index:T]).item() # sum the optimized part of the solar forecast array
                    sol_skp_sum       = np.sum(sol_for_arr [0:start_index]).item() # sum the skipped part of the solar forecast array
                    sol_prod_sum      = np.sum(sol_prod_arr[:T]).item() # sum the solar production array  (0 for skipped steps or when solar   disabled)
                    bat_charge_sum    = np.sum(c_p_arr     [:T]).item() # sum the battery charge array    (0 for skipped steps or when battery disabled)
                    bat_discharge_sum = np.sum(d_p_arr     [:T]).item() # sum the battery discharge array (0 for skipped steps or when battery disabled)

                    # Validate Energy Balance: Calculate the Overall Energy Balance Sum = Grid Import-Export Sum + Solar Production Sum + Battery Discharge-Charge Sum - House Usage Sum (Balance must be near Zero):
                    overall_sum = grid_import_sum + sol_prod_sum + bat_discharge_sum - grid_export_sum - bat_charge_sum - house_sum
                    if abs(overall_sum) >= MAX_DELTA_BALANCE:
                        # WARNING: The invalid overall sum is reported in the Calculation Code and in the Calculation Result but has NO effect on the Success of the optimization
                        calc_result, calc_code = "Balance Error", RC_INVALID_BALANCE # Optimized successful but balance validation has failed
                        error_message = f"Optimization terminated successfully. (Helios Optimizer Overall Balance Sum Validation failed with a sum of {overall_sum})" # Replaces the solver message for the balance validation failure
                        _LOGGER.error(f"Optimization Overall Balance is NOT Zero: {overall_sum}")

                    # Round the totals for all Optimizaton Variables (these will be stored later in the payload):
                    overall_sum       = round(overall_sum      , ROUND_BALANCE_KWH)
                    grid_import_sum   = round(grid_import_sum  , ROUND_ENERGY_KWH )
                    grid_export_sum   = round(grid_export_sum  , ROUND_ENERGY_KWH )
                    house_sum         = round(house_sum        , ROUND_ENERGY_KWH )
                    skipped_sum       = round(skipped_sum      , ROUND_ENERGY_KWH )
                    sol_for_sum       = round(sol_for_sum      , ROUND_ENERGY_KWH )
                    sol_skp_sum       = round(sol_skp_sum      , ROUND_ENERGY_KWH )
                    sol_prod_sum      = round(sol_prod_sum     , ROUND_ENERGY_KWH )
                    bat_charge_sum    = round(bat_charge_sum   , ROUND_ENERGY_KWH )
                    bat_discharge_sum = round(bat_discharge_sum, ROUND_ENERGY_KWH )
                    _LOGGER.debug(f"Optimization({start_index+1}) Totals: {overall_sum} = Import {grid_import_sum} + Solar {sol_prod_sum} ({sol_for_sum}, {sol_skp_sum}) + Discharge {bat_discharge_sum} - Export {grid_export_sum} - Charge {bat_charge_sum} - House {house_sum}, Skipped {skipped_sum}")                     

                    # TODO: Validate Lower and Upper Boundaries in each Step and for each Optimization Variable
                    # TODO: Validate Minimum and Maximum SOC    in each Step and for the Battery SOC Value (based upon Start SOC and Charge and Discharge Variables for previous and current steps)
                    # TODO: Validate Target SOC                 in last Step and for the Battery SOC Value (based upon Start SOC and Charge and Discharge Variables for all steps)

            else: # Optimization is infeasible (no optimum found)
                calc_result, calc_code = "Infeasible", RC_INFEASIBLE

        except Exception as e: # Exception occured in the validation phase
            error_message = f"Optimizer Step Cost Validation Failed with {repr(e)}"
            calc_result, calc_code = "Validation Failed", RC_VALIDATION_FAILED
            _LOGGER.error(f"{HELIOS_CALC_NAME} Exception: {error_message}")

    # Overall exception handling for the entire optimization function:
    except Exception as e: 
        error_message = f"Optimizer Calculation Failed with {repr(e)}"
        error_stack = traceback.format_exc() # Retrieve the python error stack from traceback
        calc_result, calc_code = "Optimizer Exception", RC_OPTIMIZER_EXCEPTION
        _LOGGER.error(f"{HELIOS_CALC_NAME} Exception: {error_message}")
        _LOGGER.error(f"Full Exception Message for {HELIOS_CALC_NAME}:")
        _LOGGER.error(error_stack)        
    
    t_current, phase_ms, run_ms = performance_count(t_current, t_start, 8) # Phase 8 time in msec

    # -------------------------------------------------------------------
    # 9. BUILT THE RESULTING PAYLOAD:
    # -------------------------------------------------------------------
    active_index  = min(start_index, (T - 1) if T > 0 else 0) # Determine the currently active step, use last step when outside the optimization period 
    optimized_plan_length = len(timestamps) # length of the optimized plan, 0 (empty) when the plan is not completely generated (last step of the plan generation is assigning the timestamps)

    # Determine the Current Power values in Watt (from kW) for the active step (current period)
    if (active_index < optimized_plan_length): # Active step is within the optimization period 
        active_ts     = timestamps   [active_index] 
        current_strat = strategy_plan[active_index] 
        grid_w   = K_FACTOR * (grid_import_plan[active_index] - grid_export_plan[active_index]) # Net Grid Power in Watt
        ev_w     = K_FACTOR * ev_plan[active_index]
        hp_w     = K_FACTOR * hp_plan[active_index]
        boiler_w = K_FACTOR * boiler_plan[active_index]
        
        # Warning: Battery is Charging OR Discharging but currently this is not yet enforced by the optimization model!
        # A rule may need to be added to enforce this or a cost for (dis)charging may be added to prevent this
        net_w = K_FACTOR * (bat_charge_plan[active_index] - bat_discharge_plan[active_index]) # Net Battery Power in Watt

    else:
        active_ts     = None
        current_strat = "Unknown" # Current strategy
        grid_w, ev_w, hp_w, boiler_w, net_w = 0.0, 0.0, 0.0, 0.0, 0.0

    # Maximum values for charge/discharge power and grid import/export in Watt 
    ch_m_w   = K_FACTOR * max_charge_power_kw    if bat_enabled else 0.0
    dis_m_w  = K_FACTOR * max_discharge_power_kw if bat_enabled else 0.0
    grid_i_w = K_FACTOR * max_grid_import_kw
    grid_e_w = K_FACTOR * max_grid_export_kw
  
    stop_dt = datetime.now() # Stop of Service Execution (Current Time)

    full_payload = {
        # Optimization/Solver Result and Timing: 
    #   "friendly_name": "Helios Optimized Energy Plan", # Friendly name is set in main module in the state.set() function 

        "success"         : res.success if res is not None else False,
        "calc_code"       : calc_code,   # 0=Success (see above for other values)
        "calc_result"     : calc_result, # Result of optimizer (solver), processing, exceptions and validation

        "total_fun_cost"  : total_fun_cost  , # round((float(res.fun) if res is not None and res.fun is not None else 0), ROUND_TOTAL_COST), 
        "total_step_cost" : total_step_cost ,     
        "total_delta_cost": total_delta_cost, # Difference between total fun and total step (rounded at 4 decimals)
        "total_grid_cost" : total_grid_cost ,

        "steps"           : T,    
        "step_size"       : step_size,
        "start_step"      : start_index  + 1,

        "base_step"       : base_index   + 1, # First interval: Always 1
        "active_step"     : active_index + 1, # Based on the start step unless start step not in 1..T
        "end_step"        : end_index    + 1, # Last interval: Should be T

        "base_time"       : datetime_string(base_dt) if base_dt   is not None else None, # Start of First Interval (YYYY-MM-DD HH:MM)
        "active_time"     : active_ts, # Timestamp for the currently active step (current period), already a string in isoformat (without T)
        "end_time"        : datetime_string(end_dt ) if end_dt    is not None else None, # Start of Last Interval  (YYYY-MM-DD HH:MM)

        "solar_mode"      : solar_mode, # Values: "all", "modulating", "binary", "disabled" (solar not enabled)

        "battery_mode"    : "enabled" if bat_enabled else "disabled",
        "capacity_kwh"    : round(capacity_kwh  , ROUND_ENERGY_KWH) if (bat_enabled) else 0.0,     

        "soc_min_kwh"     : round(soc_min_kwh   , ROUND_ENERGY_KWH) if (bat_enabled) else 0.0,
        "soc_max_kwh"     : round(soc_max_kwh   , ROUND_ENERGY_KWH) if (bat_enabled) else 0.0,
        "soc_start_kwh"   : round(soc_start_kwh , ROUND_ENERGY_KWH) if (bat_enabled and soc_start_kwh  is not None) else None,
        "soc_target_kwh"  : round(soc_target_kwh, ROUND_ENERGY_KWH) if (bat_enabled and soc_target_kwh is not None) else None, # Warning: when infeasible the soc target is adapted to a feasible kwh value
        "soc_end_kwh"     : round(soc_end_kwh   , ROUND_ENERGY_KWH) if (bat_enabled and soc_end_kwh    is not None) else None,

        "soc_min_pct"     : round(soc_min_pct   , ROUND_ENERGY_PCT) if (bat_enabled) else 0.0,
        "soc_max_pct"     : round(soc_max_pct   , ROUND_ENERGY_PCT) if (bat_enabled) else 0.0,
        "soc_start_pct"   : round(soc_start_pct , ROUND_ENERGY_PCT) if (bat_enabled and soc_start_pct  is not None) else None,
        "soc_target_pct"  : round(soc_target_pct, ROUND_ENERGY_PCT) if (bat_enabled and soc_target_pct is not None) else None, # Warning: when infeasible the soc target is adapted to a feasible percentage
        "soc_end_pct"     : round(soc_end_pct   , ROUND_ENERGY_PCT) if (bat_enabled and soc_end_pct    is not None) else None,
            
        # Current Strategy and Power values for the active step (current period)
        # Remark: Plan is in kW but Current is in Watt
        "current": {
            "battery_strategy"    : current_strat, # Battery Strategy 

            "battery_net_power_w" : net_w,      # Net Battery Power in W: Charge is Positive (+), Discharge is Negative (-)
            "battery_power_w"     : abs(net_w), # Battery Power in Watt is always positive (for Charging and Discharging), absolute value of net
            "battery_charge_w"    : (net_w      if net_w > 0 else 0),  # Charge    is only applicable when net battery power is positive
            "battery_discharge_w" : (abs(net_w) if net_w < 0 else 0),  # Discharge is only applicable when net battery power is negative

            "grid_power_w"        : grid_w  , # Net Grid Power in Watt
            "ev_power_w"          : ev_w    , # EV Power in Watt
            "hp_power_w"          : hp_w    , # Heat Pump Power in Watt
            "boiler_power_w"      : boiler_w, # Boiler Power in Watt

            "max_charge_w"        : ch_m_w  , # Maximum Battery Charge Power in Watt 
            "max_discharge_w"     : dis_m_w , # Maximum Battery Discharge Power in Watt
            "max_grid_import_w"   : grid_i_w, # Maximum Grid Import Power in Watt
            "max_grid_export_w"   : grid_e_w  # Maximum Grid Export Power in Watt
        },

        "version"                 : HELIOS_VERSION,
        "scipy"                   : SCIPY_VERSION,
        "last_run_started"        : datetime_isoformat_msec(start_dt) if start_dt is not None else None, # Start of the Run (YYYY:MM:DD HH:MM:SS:TTT)
        "last_run_stopped"        : datetime_isoformat_msec(stop_dt ) if stop_dt  is not None else None, # End   of the Run (YYYY:MM:DD HH:MM:SS:TTT)
        "service_calc_time_ms"    : None, # Service Calculation time is overwritten in the helios_optimizer_servic function (helios_services.py) 

        "solver_execution_time_ms": execution_time  if execution_time is not None else 0,
        "solver_iterations"       : res.nit     if res is not None and res.nit     is not None else 0,
        "solver_message"          : res.message if error_message is None else error_message, # Use the solver message unless an error message is set 

        "insight"                 : insight,     # debug level
        "error_trace"             : error_stack, # for debugging only
        "totals"                  : None,        # for debugging only 
        "performance_ms"          : None,        # for debugging only
        "plan"                    : {} # No plan added yet (Warning: Helios Graph and Table need the plan arrays)
    }
    if (insight >= INSIGHT_MAX):
        # Add the totals for debugging purposes:
        full_payload["totals"] = {
           "input_house"  : input_house_sum,
           "input_solar"  : input_solar_sum,
           "overall"      : overall_sum,
           "import"       : grid_import_sum,
           "production"   : sol_prod_sum,
           "forecast"     : sol_for_sum,
           "discharge"    : bat_discharge_sum,
           "export"       : grid_export_sum,
           "charge"       : bat_charge_sum,
           "house"        : house_sum,
           "solar_skipped": sol_skp_sum,
           "house_skipped": skipped_sum
        }

        # Add the performance details for debugging purposes:
        full_payload["performance_ms"] = PERFORMANCE_ARRAY_MS

        # Complete Dayplanning for Tables/Graphs and for Testing
        # Per Step: Timestamps, Strategie, Batterij SoC percentage and SoC kWh
        #  other plan values in kW per step
        full_plan = {
            "timestamp"           : timestamps,
            "import_prices"       : import_prices,
            "export_prices"       : export_prices,
            "step_costs"          : step_costs,
            "house_kw"            : house_plan,
            "solar_forecast_kw"   : solar_forecast,
            "solar_production_kw" : solar_plan,
            "strategy"            : strategy_plan,
            "soc_pct"             : soc_pct_plan,
            "soc_kwh"             : soc_kwh_plan,
            "grid_import_kw"      : grid_import_plan,
            "grid_export_kw"      : grid_export_plan,
            "battery_discharge_kw": bat_discharge_plan if bat_enabled    else None,
            "battery_charge_kw"   : bat_charge_plan    if bat_enabled    else None,
            "ev_charge_kw"        : ev_plan            if ev_enabled     else None, # Tested with fixed value array that markdown table and apexcharts with optional ev column work with dummy array: [1.0] * T,
            "heat_pump_kw"        : hp_plan            if hp_enabled     else None, 
            "boiler_kw"           : boiler_plan        if boiler_enabled else None
        }
        full_payload["plan"] = full_plan # Set the full plan arrays in the full payload
        
    t_current, phase_ms, run_ms = performance_count(t_current, t_start, 9) # Phase 9 time in msec

    # -------------------------------------------------------------------
    # 10. RETURN the RESULT:
    # -------------------------------------------------------------------
    # Set the HA Helios Energy Plan Entity and its attributes (Now: see helios_optimizer.py):
    # state.set(
    #    "pyscript.helios_energy_plan",
    #    value=total_cost_eur,
    #    new_attributes=full_payload
    #)
    if (res is not None and error_message is None):
        if res.success:
            _LOGGER.info(f"{HELIOS_CALC_NAME} succesful in {execution_time}ms (cost={round(res.fun,4)}, start_step={start_index + 1}, iterations={res.nit}).")        
        else:
            _LOGGER.warning(f"{HELIOS_CALC_NAME} infeasible: {res.message}")
    else:
        _LOGGER.error(f"{HELIOS_CALC_NAME} failed: {error_message}")

    # Return Full Payload to the Service Trace
    end_dt = datetime.now()
    t_current, phase_ms, run_ms = performance_count(t_current, t_start, 10) # Phase 10 time in msec
    PERFORMANCE_ARRAY_MS.append(f"CalcTotal={run_ms:.1f}")
    _LOGGER.debug(f"{HELIOS_CALC_NAME}: Run Time={round(K_FACTOR * (end_dt - start_dt).total_seconds(), ROUND_TIME_MSEC):.1f}ms, Performance={run_ms:.1f}ms")
    _LOGGER.debug(f"{HELIOS_CALC_NAME}: Step Performance Array in ms:\n{PERFORMANCE_ARRAY_MS}") # Print performance array for all steps and total run in ms
    _LOGGER.info (f"{HELIOS_CALC_NAME}: Run Time={run_ms:.1f}ms")

    return full_payload

