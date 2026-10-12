# Main: HELIOS Optimizer Service - Home Assistant Service to Calculate an Optimized Energy Plan                            
# Home Energy Linear Integrated Optimization Service (HELIOS Optimizer)
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1   Started Implementation with help of Google Gemini
#   2026-08-27: JR: v0.78k Included performance measurements (from 12.5s to <1s for 192 steps, 15 min)
#   2026-08-31: JR  v0.78l Adding input parameters to the dashboard, improved output markdown cards, adapted the payload (consistent names with kwh, kw, w, ms etc) 
#   2026-09-02: JR  v0.78m Handling invalid arguments in the service call, this allows the HA Automation to report the error (instead of failing with a NoneType erorr)
#   2026-09-02: JR  v0.78m Separate input step sizes for import/export prices, house forecast and solar forecast arrays (3 values) instead of a single input step size to allow for different resampling conversions 
#   2026-09-04: JR  v0.79n Added Sum (Totals) of Input Arrays and Output Arrays for validation purposes
#   2026-09-07: JR  v0.79o Added input and output files (in the helios service) for validation and regression test purposes
#   2026-09-09: JR  v0.79o Moved the raw file handling functions from helios_services.py to helios_common.py (this are all pure/raw python functions that do not need HA functions)
#   2026-09-09: JR  v0.79o Changed the helios_optimizer_service to asynchronous function and call the helios_optimizer_calc_plan from the service using an await and the task.executor, big performance improvement
#   2026-09-12: JR  v0.79p Changed arguments solar.forecast and house_forecast to solar.energy_forecast and house_energy_forecast to stress the difference between energy and power values
#   2026-09-18: JR  v0.78r Added HBC Price Array and Provider Price Arrays as Input Price Array (Import and Export Price Arrays are derived from the Input Array), 
#   2026-09-18: JR  v0.79r Use HA Datetime Util for Now() to support HA Container Enviorments, Use Naive (without timezone) Timestamps for optimization time (and price and forecast array lookups), rename optimize_ts to optimize_ts_str
#   2026-09-30: JR  v0.78s Included Support for Conversion from Source Price to Target Price, Group Steps and Average Price, Expand Steps (Repeat), Fill Gaps in Day(s), Fallback Days, 
#   2026-10-07: JR  v0.90  First Public Release (Read-only for HBC), Support for HBC Price Data, Updates Helios Optimizer Entities for HBC (Sub-Strategy and Net Power) but has no Helios Strategy yet in HBC
#   2026-10-12: JR  v0.91  Initializes Helios Optimizer Input Entities depending on the previous helios release version, For some initial values of Input Entities HBC values are used (sell/charge target, max discharge/charge power)
#
#   Remark: For a full history see helios_main.py

# Modules used by Home Assistant with PyScript must be in the "modules" folder of the Home Assistant configuration directory. 
# Modules used by Visual Studio must be in the same folder as the Main Python script.
# Pure Python Modules used by Home Assistant Visual Studio Code must be in the sub-folder helios_python (in HA pyscript/helios_python, in VS: c:\$code\VisualStudio2026\HeliosOptimizer\helios_python)
import sys  # For sys.path.append() to add the Home Assistant /config/pyscript folder to the path to allow /config/pyscript/helios_python to be found !!!

from io   import TextIOWrapper

# Determine the environment (Visual Studio or Home Assistant):
dt_util = None # Home Assistant Datetime Utility not yet available
try: # Assume we are running in Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
    HELIOS_FOLDER  = 'export/'  # Used by Helios Services AND Helios Main (in Visual Studio)
    HELIOS_RESULTS = 'results/' # Only used by Helios Main (in Visual Studio)

    # Do not add the home_assistant_mock.py to the Home Assistant pyscript/helios folder, it is only needed for testing in Visual Studio
    from home_assistant_mock import service, time_trigger, pyscript_compile, log, automation, task, state  # Include HA mock for testing outside of Home Assistant
#   _LOGGER = log # Use the mock log for testing in Visual Studio (Disabled _LOGGER: Using mock log in Helios Services)

except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
    HELIOS_FOLDER = '/config/export/'

    try: # Use Home Assistant Datetime for Price and Forecast Lookups
        import homeassistant.util.dt as dt_util # Get the HA Datetime Utility (especially important for container environments)
    except:
        pass # use OS datetime 

    # Disabled _LOGGER: Using Home Assistant PyScript log in Helios Services:
#   import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
#   _LOGGER  = logging.getLogger(__name__) # Get access to the HomeAssistant Logger in standard python functions (not needed in helios_services since access to HA log is available)
    
if "/config/pyscript" not in sys.path: # Already in the search path for pure python modules in Home Assistant? 
        sys.path.append("/config/pyscript") # Home Assistant Pyscript folder, Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)
#   pass  # In Home Assistant no mock is needed since service/state/log etc already exist globally!

from helios_python.helios_optimizer import * # Import helios_optimizer.py for the Helios Pure Python Calculate Plan function and other Optimize Energy functions (and Helios Common Functions via helios_common.py)

# Constant values for the Home Assistant Entities and Automations used by the Helios Service
# Home Assistant Entities used by the Helios Optimizer Service (these entities must be created in Home Assistant before the service can be used)
HELIOS_OPTIM_PLAN        = 'input_number.helios_optimizer_energy_plan'          # Sensor Helios Optimizer Result with Status, Current and Plan in the attributes
HELIOS_OPTIM_PLAN_OLD    = 'pyscript.helios_energy_plan'                        # Sensor Helios Result with Status, Current and Plan in the attributes
HELIOS_HBC_SUB_STRAT     = 'input_select.helios_optimizer_hbc_sub_strategy'     # Sensor Helios Sub Strategy for HBC
HELIOS_HBC_NET_POWER     = 'input_number.helios_optimizer_hbc_net_power'        # Sensor Helios Net Battery Power for HBC (Charge is Positive, Discharge is Negative), Translated later to Charge and Discharge Power (both Positive)
HELIOS_AUTOMATION        = 'automation.helios_optimizer_automation_task'        # Sensor Helios Optimizer Automation Task that calls the Helios Optimizer Service to calculate the Optimal Energy Plan
HELIOS_RUNNING           = 'input_boolean.helios_optimizer_running'             # Sensor Helios Automation is running (True/False) for the UI Button to show the service is running (extra second added for short service calls)

# Home Assisant Entities (a copy in home_assistant_mock.py and the original in helios_services.py):
HELIOS_INPUT_VERSION     = 'input_text.helios_optimizer_version'                # Sensor Helios Optimizer Version 
HELIOS_INPUT_STEPS       = 'input_number.helios_optimizer_steps'                # Sensor Helios Optimizer Steps (24, 48, 96 or 192 steps of 60 or 15 minutes)
HELIOS_INPUT_STEP_SIZE   = 'input_select.helios_optimizer_step_size'            # Sensor Helios Optimizer Step Size (Dropdown Select for 60 or 15 minutes)
HELIOS_INPUT_START_STEP  = 'input_number.helios_optimizer_start_step'           # Sensor Helios Optimizer Start Step (0=Automatic, 1-192 is manual for testing)
HELIOS_INPUT_MAX_GRID_IMP= 'input_number.helios_optimizer_max_grid_import'      # Sensor Helios Optimizer Maximum Grid Import in kW
HELIOS_INPUT_MAX_GRID_EXP= 'input_number.helios_optimizer_max_grid_export'      # Sensor Helios Optimizer Maximum Grid Export in kW
HELIOS_INPUT_HOUSE_USAGE = 'input_number.helios_optimizer_house_daily_usage'    # Sensor Helios Optimizer House Daily Usage over the Day in kWh
HELIOS_INPUT_HOUSE_DISTR = 'input_text.helios_optimizer_house_daily_distr'      # Sensor Helios Optimizer House Daily Distribution of the House Usage over the Day as a list of 24 or 96 relative values for each hour or quarter of an hour of the day

HELIOS_INPUT_BAT_ENABLED = 'input_boolean.helios_optimizer_battery_enabled'     # Sensor Helios Optimizer Battery Enabled (True/False, On/Off)
HELIOS_INPUT_SOC_TARGET  = 'input_number.helios_optimizer_soc_target_pct'       # Sensor Helios Optimizer Battery Target SOC (State of Charge) in % for the Optimization (for End of Optimizaton Period/Horizon)
HELIOS_INPUT_SOC_MIN     = 'input_number.helios_optimizer_soc_min_pct'          # Sensor Helios Optimizer Battery Minimum SOC (State of Charge) in % for the Optimization (Overall Minimum for ALL Steps / full Period)
HELIOS_INPUT_SOC_MAX     = 'input_number.helios_optimizer_soc_max_pct'          # Sensor Helios Optimizer Battery Maximum SOC (State of Charge) in % for the Optimization (Overall Maximum for ALL Steps / full Period)
HELIOS_INPUT_CHARGE_LIMIT= 'input_number.helios_optimizer_charge_limit'         # Sensor Helios Optimizer Maximum Battery Charge    Limit in kW   (all batteries together) 
HELIOS_INPUT_DISCH_LIMIT = 'input_number.helios_optimizer_discharge_limit'      # Sensor Helios Optimizer Maximum Battery Discharge Limit in kW   (all batteries together) 
HELIOS_INPUT_CHARGE_EFF  = 'input_number.helios_optimizer_charge_efficiency'    # Sensor Helios Optimizer Battery Charge    Efficiency Percentage (all batteries together) 
HELIOS_INPUT_DISCH_EFF   = 'input_number.helios_optimizer_discharge_efficiency' # Sensor Helios Optimizer Battery Discharge Efficiency Percentage (all batteries together) 

HELIOS_INPUT_SOLAR_MODE  = 'input_select.helios_optimizer_solar_mode'           # Sensor Helios Optimizer Solar Mode (Dropdown Select for SOLAR_ALL, SOLAR_MOD, SOLAR_BIN or SOLAR_DIS)

HELIOS_TEMPL_HBC_MAX_CAP = 'sensor.helios_template_hbc_maximum_energy'          # Sensor Helios Template with HBC Total Maximum   Energy for all of the Batteries
HELIOS_TEMPL_HBC_REM_ENGY= 'sensor.helios_template_hbc_remaining_energy'        # Sensor Helios Template with HBC Total Remaining Energy for all of the Batteries
HELIOS_TEMPL_HBC_TOT_SOC = 'sensor.helios_template_hbc_total_soc'               # Sensor Helios Template with HBC Total SOC Percentage   for all of the Batteries (derived from Maximum and Remaining above)
HELIOS_TEMPL_HBC_MAX_CHG = 'sensor.helios_template_hbc_max_charge_power'        # Sensor Helios Template with HBC Maximum Battery Charge    Power
HELIOS_TEMPL_HBC_MAX_DIS = 'sensor.helios_template_hbc_max_discharge_power'     # Sensor Helios Template with HBC Maximum Battery Discharge Power

HBC_STRAT_SELL_TARGET_SOC= 'input_number.house_battery_strategy_sell_target_soc'   # Sensor HBC Strategy Sell (Discharge) Target SOC Percentage
HBC_STRAT_BUY_TARGET_SOC = 'input_number.house_battery_strategy_charge_target_soc' # Sensor HBC Strategy Buy  (Charge   ) Target SOC Percentage

HELIOS_PLAN_NAME     = 'Helios Optimizer Energy Plan'              # Friendly Name for the Helios Result Entity
HELIOS_RUNNING_NAME  = 'Helios Optimizer Running'                  # Friendly Name for the Helios Running Entity  
HELIOS_SERVICE_NAME  = 'Helios Optimizer Service'                  # Name of the Helios Optimizer Service
HELIOS_ASYNC_FF_NAME = 'Helios Async File Functions'               # Name of the Helios Async File Functions      
HELIOS_MAIN_NAME     = 'Helios Optimizer Regression Test'          # Name of the Helios Optimizer Main Routine (Regression Test)

HELIOS_INPUT_FNAME5  = 'helios_optimizer_input_ha_192s15i81.json'  # JSON Input file  with the input parameters for testing purposes (see main), only for run type 0 (others use the base parameters from main)
HELIOS_OUTPUT_FNAME  = 'helios_optimizer_output.json'              # JSON Output file with the output results   for testing purposes (see main), renamed to _expected_xxx for validation
HELIOS_PLAN_FNAME    = 'helios_optimizer_plan.csv'                 # CSV  Output file with the plan variables as a spreadsheet table (value for each step), used in main    (see alos TABLE)
HELIOS_RESULTS_FNAME = 'helios_test_results_{date}.csv'            # CSV  Output file with the results summary  for multiple test runs (date is replaced by current date)
HELIOS_PARAMS_FNAME  = 'helios_optimizer_params.json'              # JSON Output file with the input parameters for the optimizer
HELIOS_PAYLOAD_FNAME = 'helios_optimizer_payload.json'             # JSON Output file with the output (payload) of  the optimizer
HELIOS_TABLE_FNAME   = 'helios_optimizer_table.csv'                # CSV  Output file with the plan variables as a spreadsheet table (value for each step), used in service (see also PLAN)

SERVICE_PERFORMANCE_MS: list = [] # Global variable for Performance of all runs (collecting performance results for multiple runs)

# Helios Optimizer Service with a return response (payload with the results of the calculation)
# Definition of the Home Assistant Service that calculates an Optimized Energy Plan
# The Service handles only the Home Assistant specific calls
# The actual calculation is done by helios_optimizer_calc_plan() and runs using pure python (without HA specific pyscript functions)
@service(supports_response="optional") 
async def helios_optimizer_service(
    steps=24,        # Optimization Steps:     24 steps for 60 minutes is one day,  48 steps is two days
    step_size=60,    # Optimization Step Size: 96 steps for 15 minutes is one day, 192 steps is two days
    start_step=0,    # Optimization Starts at Start Step (1..steps), 0 = Determine start step automatically using current time

    price_size=None, # None when resample of price          array is not needed, price step size when step size of price          input array is not equal to the optimization step size
    house_size=None, # None when resample of house forecast array is not needed, house step size when step size of house forecast input array is not equal to the optimization step size
    solar_size=None, # None when resample of solar forecast array is not needed, solar step size when step size of solar forecast input array is not equal to the optimization step size
    price_factor=PRICE_FACTOR,   # 1.0 (default) or 0.01 (convert from cents to euro)

    max_grid_import_kw=MAX_GRID, # Maximum Grid Import Power (kW) for the Optimization
    max_grid_export_kw=MAX_GRID, # Maximum Grid Export Power (kW) for the Optimization

    battery=None,                # Battery Parameters (dict)
    solar=None,                  # Solar Parameters (dict)
    ev=None,                     # Future
    heat_pump=None,              # Future
    boiler=None,                 # Future

    # Use House Energy Forecast or House Daily Usage and Distribution:
    house_energy_forecast=None,  # Simple House Energy Usage Forecast Array with list of usage values per step (per hour or per 15 minutes)
    house_daily_usage=None,      # House Daily Usage (kWh) as a total value, Alternative when house forecast array is not available, will be spread over the day using house_daily_distr
    house_daily_distr=None,      # House Daily Distribution of the House Usage over the Day as a list of 24 or 96 relative values for each hour or quarter of an hour of the day

    # Use Import and Export Prices or Source Prices and Source Type (and optionally Source Provider):
    import_prices=None,          # Simple Grid Import Prices (€/kWh) as a list of prices per step (per hour or per 15 minutes)
    export_prices=None,          # Simple Grid Export Prices (€/kWh) as a list of prices per step (per hour or per 15 minutes)
    provider_key=None,           # Provider Key (used to retrieve the provider profile to calculate the Import/Export Prices from the Source Price Data), Not needed when import_prices and export_prices are provided directly
    source_price_sensor=None,    # Source Price Sensor (Entity ID), Needed since the Home Assistant automation cannot pass the attributes of an Entity as a dictionary to the service via source_price_data
    source_price_data=None,      # Source Price Data (e.g. €/kWh or cents/kWh or €/kWh), A Dictionary with timestamps and prices (per hour or per 15 minutes), alternative when import and export prices are not available, can be HBC Price Data or Provider Price Data
    source_type=None,            # Source (Price) Type (Price Types are Market, Import or Export) for the source_price_data
    original_provider=None,      # Orginal (Energy) Provider, Needed when the Source Price Data is provided indirectly by the Energy Provider (e.g. for HBC Price Data which is retrieved from original Provider Price Data using Cheapest Hours)

    max_time=MAX_TIME,           # Maximum Time for the Linear Programming Module (HiGHS Solver of SciPy)
    max_iterations=MAX_ITER,     # Maximum Iterations for the LP Module

    insight=INSIGHT_STD,         # Debug level
    write_files=True,            # Write the Helios Optimizer Input Parameters and Output Payload to export files for debugging and regression testing purposes (only applies to services output files not to VS Main)
    output_folder=None,          # Output folder for the export files  
    optimize_ts_str=None,        # Optimization Timestamp String (ts), for (regression) testing/debugging, typically this will be None and the Current (HA) Timestamp will be used
    optimize_off_min=None,       # Optimization Timestamp Timezone Offset in Minutes

    # Following parameters are automatically provided by Home Assistant when the service is called, but are not used in the service itself
    # WARNING: If these parameters are not included in the service definition, the check on kwargs will throw an TypeError
    #    Any new parameters added by Home Assistant in the future need to be added here, otherwise the service will fail with a TypeError !!!
    return_response=None, # Return a result (Must be a dictionary!)
    trigger_type=None,    # Trigger type (time_trigger, state_trigger, event_trigger) for the service call
    context=None,         # Context of the service call (used for logging and debugging)

    **kwargs  # <--- Catches all unknown parameters (MUST be EMPTY for correct calls, otherwise the service cannot check for unexpected parameters, so add any new HA parameters in the parameter list above)
):
    """
    Home Energy Linear Integrated Optimization Service: Helios Optimizer Service
    A Home Assistant PyScript Calculate Energy Plan Service that uses SciPy Linear/MILP Programming.
    """
    try:
        service_begin_ts, service_computed_ts, service_end_ts = datetime.now(), None, None
        calc_code, calc_result, total_fun_cost = RC_SUCCESS, None, "unavailable" # Default to success, will be changed if an exception occurs
        log.info(f"{HELIOS_SERVICE_NAME}: Started at {service_begin_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

        now_ts  = service_begin_ts # Local Timestamp (does not have a timezone yet)
        now_tz  = now_ts.astimezone().tzinfo # Get Timezone info object from timestamp (but we can get it from the datetime)
        now_off = now_tz.utcoffset(now_ts)
        try: # Try to retrieve the Home Assistant Timestamp and Timezone
            if dt_util: # Home Assistant Datetime Utility available?
                now_ts  = dt_util.now()                               
                now_tz  = dt_util.get_time_zone(hass.config.time_zone)
                now_off = now_tz.utcoffset(now_ts)
        except Exception as e:
            log.warning(f"{HELIOS_SERVICE_NAME}: Home Assistant Timestamp or Timezone retrieval failed: {repr(e)}")
        now_ts =  now_ts.replace(tzinfo=None) # Use internally a naive (no timezone info) timestamp (from HA when available) for lookups in price arrays
        now_off_min = int(now_off.total_seconds() / 60) # Timezone offset in minutes (integer)

        # CHECK on Unexpected arguments parameters (all supported keyword arguments have a default value and are optional):
        if kwargs: # Unexpected keyword argument(s) received?
            unknown_keys = list(kwargs.keys())
            raise TypeError(
                f"Unexpected keyword argument(s) received by helios_optimizer_service(): {', '.join(unknown_keys)}"
            )
        output_folder = output_folder if output_folder else HELIOS_FOLDER # Make sure the output folder is filled (with default when None specified)

        battery_info = battery if battery else {}
        solar_info   = solar   if solar   else {}

        # Initialize the Helios Optimizer Entities (executed only once until new entities are added in the next release)
        helios_optimizer_init()

        # Home Assistant refuses to pass all attributes of an entity as a dictionary to the service (from the automation), instead it converts it to a json structure
        # Warning: The source price data is retrieved from HA when a source_price_sensor is specified and REPLACES the source_price_data that was sent as an argument
        if source_price_sensor and state.exist(source_price_sensor): # Source Price Id specified and the entity exists in Home Assistant, retrieve the attributes of the entity as a dictionary
            source_price_type1 = type(source_price_data)
            source_price_data2 = state.getattr(source_price_sensor) # Get the attributes of the source price entity as a dictionary (this is a Home Assistant specific function, not available in Visual Studio)       
            source_price_type2 = type(source_price_data2)
            await async_write_message('test.log', f"Testing to write a file with steps={steps}, size={step_size}, start={start_step}, soc={battery_info.get('soc_start_pct', None)}, solar_info='{solar_info.get('mode', 'unknown')}', price size={price_size}, source price id={source_price_sensor}, type={source_price_type1}, type2={source_price_type2}")
            await async_write_message('test.log', f"source price data={source_price_data}")
            await async_write_message('test.log', f"source price data={source_price_data2}")
            source_price_data = source_price_data2

        # OPTIMIZER INPUT PARAMETERS:    
        optimizer_params = {
            "steps"                : steps,
            "step_size"            : step_size,
            "start_step"           : start_step,

            "price_size"           : price_size,
            "house_size"           : house_size,
            "solar_size"           : solar_size,
            "price_factor"         : price_factor,

            "max_grid_import_kw"   : max_grid_import_kw,
            "max_grid_export_kw"   : max_grid_export_kw,

            "battery"              : battery,               # Battery Parameters (dict): Battery Enabled, Capacity, SOC%-s (Start, Target, Min, Max), Max Charge/Discharge Power, Charge/Discharge Efficiency, Charge/Discharge Cost 
            "solar"                : solar,                 # Solar Parameters (dict): Solar Enabled, Solar Mode, Solar Energy Forecast in kWh per step
            "ev"                   : ev,                    # Electric Vehicle Parameters (dict) - Future
            "heat_pump"            : heat_pump,             # Heat Pump Parameters (dict)        - Future
            "boiler"               : boiler,                # Boiler Parameters (dict)           - Future

            "house_energy_forecast": house_energy_forecast, # Simple House Usage Energy Forecast Array in kWh per step
            "house_daily_usage"    : house_daily_usage,     # Optional House Daily Usage in kWh as a total value
            "house_daily_distr"    : house_daily_distr,     # Optional House Daily Distribution of the House Usage over the Day

            "import_prices"        : import_prices,         # Simple Import Price Array in euro per step
            "export_prices"        : export_prices,         # Simple Export Price Array in euro per step
            "provider_key"         : provider_key,          # Provider Key (used to retrieve the provider profile to calculate the Import/Export Prices from the Source Price Data)
            "source_price_sensor"  : source_price_sensor,   # Source Price Sensor (Entity ID) (info only since the service already retrieved the related source price data)
            "source_price_data"    : source_price_data,     # Source Price Data, Dictionary with Price Info (alternative to Simple Import/Export Price Arrays)
            "source_type"          : source_type,           # Source (Price) Type (Price Types are Market, Import or Export)
            "original_provider"    : original_provider,     # Optional Original (Energy) Provider (Only applicable when the Price Provider is not the Original Source for the Price Data) 

            "max_time"             : max_time,
            "max_iterations"       : max_iterations,

            "insight"              : insight,
            "write_files"          : write_files,     # Writing Files, Info only (used in the service but not by the calculator, not applicable to VS Main during testing)
            "output_folder"        : output_folder,   # Output Folder, Info only (used in the service but not by the calculator)
            "now_ts"               : now_ts,          # Naive Datetime for Now (from Home Assistant when available, especially important in container environments)
            "now_tz"               : now_tz,          # Timezone Used for the Naive Datetime Now
            "now_off_min"          : now_off_min,     # Offset in Minutes of the Timezone Used for the Naive Datetime Now
            "optimize_ts_str"      : optimize_ts_str, # Optimize Datetime String (for (regression) testing only)
            "optimize_off_min"     : optimize_off_min if optimize_off_min else 0, # Offset in minutes to UTC for the Timezone of the Optimize Timestamp
        }

        # WRITE INPUT PARAMETERS FILE:
        if write_files: # Write the input parameters to a JSON file for debugging and regression testing purposes
            adapted_params = optimizer_params if optimize_ts_str else {**optimizer_params, "optimize_ts_str": datetime_isoformat(timespec="seconds")} # Replace in the parameters the optimizer timestamp with now when no timestamp provided
            await async_write_dict_to_json_file(output_folder + HELIOS_PARAMS_FNAME, adapted_params) # Write the input parameters to a JSON file for debugging and regression testing purposes

        # CALL the HELIOS OPTIMIZER CALCulate PLAN function with the parameters as provided in the Helios Optimizer Service:
        # The Helios Optimizer Calculate Plan function is designed to be independent of Home Assistant, allowing for easier testing and debugging in Visual Studio.
#       payload = helios_optimizer_calc_plan(**optimizer_params) # Run the Helios Optimizer Calculate Plan function with the provided parameters (Synchronous call, be very careful with blocking functions like file io and logging)
        payload = await task.executor(helios_optimizer_calc_plan, **optimizer_params) # Asynchronous Call to the Helios Optimizer Calculation Plan (Pure Python) Function, Waiting (await) for the result, performance is now much better!  
#       calc_code      = payload.get('calc_code'     , -1  )
        calc_result    = payload.get('calc_result'   , None)
        total_fun_cost = payload.get('total_fun_cost', None)

        # ADD the Service EXECUTION TIME to the payload for logging and debugging purposes:
        service_computed_ts = datetime.now()
        service_compute_ms = round(1000*(service_computed_ts - service_begin_ts).total_seconds(), 1) # Performance of the calculation of the plan in ms
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Computed Time (excluding state.sets)={service_compute_ms:.1f}ms")
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Computed at {service_computed_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} with result '{calc_result}'")
        SERVICE_PERFORMANCE_MS.append(service_compute_ms) # Append this runs computation time (without state.sets)

        payload['last_service_begin'     ] = datetime_isoformat_msec(service_begin_ts    ) if (service_begin_ts     != None) else None # Begin of the Service (YYYY:MM:DD HH:MM:SS:TTT)
        payload["last_service_computed"  ] = datetime_isoformat_msec(service_computed_ts ) if (service_computed_ts  != None) else None # End Calculation      (YYYY:MM:DD HH:MM:SS:TTT)
        payload['service_compute_time_ms'] = round(service_compute_ms,1) # Add Total Calculation Execution Time for the Calculation to the payload (without the state.set)

    # HANDLE SERVICE EXCEPTIONS (Remark: Exceptions are more likely to be handled by the Exception handler of the helios_optimizer_calc_plan):
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}] Exception in Calculate Plan: {error_message}")
        payload = { # Construct a simple version of the payload for the service exception
            "success"                 : False, 
            "calc_code"               : RC_SERVICE_EXCEPTION, 
            "calc_result"             : "Service Exception", 
            "version"                 : HELIOS_VERSION,
            "scipy"                   : SCIPY_VERSION,

            "last_service_begin"      : datetime_isoformat_msec(service_begin_ts) if (service_begin_ts != None) else None, # Start of the Run (YYYY:MM:DD HH:MM:SS:TTT)
            "last_calc_started"       : None, # Calculation did not complete
            "last_calc_stopped"       : None, # Calculation did not complete
            "last_service_computed"   : None, # Calculation did not complete
            "last_service_end"        : None, # End   of the Service will be set at the end of the Service

            "service_total_time_ms"   : None, # Service total run time will be set at the end of the Service
            "service_compute_time_ms" : None, # Calculation did not complete (no compute   time available)
            "calc_exec_time_ms"       : None, # Calculation did not complete (no execution time available)

            "solver_exec_time_ms"     : None, # Calculation did not complete (no solver time available)
            "solver_iterations"       : 0,    # Calculation did not complete (no solver iterations available)
            "solver_message"          : error_message # Calculation did not complete (no solver message available, an error message will be returned instead)
        } 
  
    # SET Home Assistant STATE for the Helios Optimizer Energy Plan (with the payload in the attributes):
    try:    
        # Store the optimization result in the Home Assistant Helios Optimizer Energy Plan Entity and its attributes 
        if state.exist(HELIOS_OPTIM_PLAN):
            # Entity already exist, the status and attributes can be updated
            state.set(
                HELIOS_OPTIM_PLAN,
                value=total_fun_cost, # Use the Total Cost from the payload as the main value of the entity, so it can be used in automations and templates and graphs
                friendly_name=HELIOS_PLAN_NAME,
                unit_of_measurement="€", # Use the Euro sign as the unit of measurement for the Total Cost
                min=-1000, max=1000, step=0.01, initial=None, # Use a reasonable range for the Total Cost (in Euro) and a step size of 1 cent and no initial value (since the value is set by the optimizer)
                new_attributes=payload
            )

            # The Helios Optimizer Energy Plan Entity is now updated with the new payload (two fields from this payload also have their own Home Assistant Entities)
            # The HBC Sub Strategy and Net Battery Power are also updated in their respective entities for use in the Home Assistant Node-Red Flow for the Helios Strategy:
            current = payload.get('current', None)
            if ha_exist(HELIOS_HBC_SUB_STRAT) and current: # The HBC Sub Strategy Entity and payload['current'] must exist?
                hbc_sub_strategy = current.get('hbc_sub_strategy', None)         # Get the HBC Sub Strategy from the payload
                ha_set_state(HELIOS_HBC_SUB_STRAT, value=hbc_sub_strategy)          # Set the HBC Sub Strategy 
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_HBC_SUB_STRAT} does not exist!")    

            if ha_exist(HELIOS_HBC_NET_POWER) and current: # The HBC Net Battery Power Entity and payload['current'] must exist 
                hbc_net_battery_power = current.get('battery_net_power_w', None) # Get the Net Battery Power in Watt from the payload
                ha_set_int(HELIOS_HBC_NET_POWER, value=int(hbc_net_battery_power) if hbc_net_battery_power != None else None) # Set the Net Battery Power for HBC (Charge is Positive, Discharge is Negative) in Watt
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_HBC_NET_POWER} does not exist!")    

        else: # The entity must already exist before we write to it (since otherwise a pyscript entity would be created)!
            log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_OPTIM_PLAN} does not exist!")    

    #   task.sleep(1)
    #   task.sleep(0.001)
        service_end_ts = datetime.now()
        service_end_ms = round(1000*(service_end_ts - service_begin_ts).total_seconds(), 1) # Performance of the calculation and the state.set:
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Run Time (including state.set)={service_end_ms:.1f}ms")
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Run Finished at {service_end_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} with result '{calc_result}'")

        payload['last_service_end'     ] = datetime_isoformat_msec(service_end_ts) if (service_end_ts != None) else None # End of the Service Run (YYYY:MM:DD HH:MM:SS:TTT)
        payload['service_total_time_ms'] = round(service_end_ms,1) # Add Total Service Execution Time including the Set Entity States to the payload
    
    # HANDLE SET STATE EXCEPTIONS:
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}] Exception in HA Set State: {error_message}")
        if (calc_code == RC_SUCCESS): # Only set the calc_code, calc_result and solver_message when they are not already set by previous errors
            payload['calc_code']      = RC_SETSTATE_EXCEPTION  # adapt the calc_code to indicate that the state.set failed after a successful calculation
            payload['calc_result']    = "State Set Exception" 
            payload['solver_message'] = error_message

    # WRITE OUTPUT (RESULT) FILES
    try:
        if write_files: # Write the input parameters to a JSON file for debugging and regression testing purposes
            # WRITE PAYLOAD FILE (All Results) to JSON:
            char_count = await async_write_dict_to_json_file(output_folder + HELIOS_PAYLOAD_FNAME, payload) # Write the output to a JSON file for debugging and regression testing purposes
    
            # WRITE ENERGY PLAN FILE to CVS File (Only the Optimized Energy Plan Arrays as a Table):
            headers, row_list = convert_dictoflists_to_listofdicts(payload.get('plan', {}))
            line_count = await async_write_csv_file(output_folder + HELIOS_TABLE_FNAME, row_list=row_list, headers=headers, row_key=None)
    
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}] Exception in Write Output Files: {error_message}")

    return payload # Return the payload to the Home Assistant Automation in the return_response (see the automation trace for details)

def helios_optimizer_init():
    """
    Helios Optimizer Initialisation of (new) Home Assistant Helios Optimizer Entities.
    Depending on the Helios Optimizer Version the HA Entities will be initialized.
    Typically Entities already initialized in an earlier version will not be initialized again.
    """ 
    if ha_exist(HELIOS_INPUT_VERSION): # Does the HA Helios Optimizer Version Entity Exist?
        init_count = 0
        previous_version_tuple = parse_version(ha_get_text(HELIOS_INPUT_VERSION, "0.0.0"))
        current_version_tuple  = parse_version(HELIOS_VERSION)
        if (current_version_tuple > previous_version_tuple): # Helios Current Version is higher than the Previous Version
            # Initialize Entities when new in a helios release (depending on the version):
            if (previous_version_tuple < (0,3,0)): # Below v0.3.0 Optimizer Entities
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_STEPS       , STEPS       )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_STEP_SIZE   , STEP_SIZE   )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_START_STEP  , STEP_ZERO   )

            if (previous_version_tuple < (0,3,1)): # Below v0.3.1 Maximum Grid Power Entities
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_MAX_GRID_IMP, MAX_GRID    )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_MAX_GRID_EXP, MAX_GRID    )

            if (previous_version_tuple < (0,8,0)): # Below v0.8.0 all applicable optimizer arguments must be initialized
                # Initialize the Helios House Daily Usage and House Daily Usage Distribution Entities:
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_HOUSE_USAGE , HOUSE_DAY   )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_HOUSE_DISTR , HOUSE_DISTR )

#               HELIOS_TEMPL_HBC_MAX_CAP 
#               HELIOS_TEMPL_HBC_REM_ENGY
#               HELIOS_TEMPL_HBC_TOT_SOC 
                # Get some default battery values from HBC and use them when available (otherwise use the Helios defaults):
                hbc_sell_target_soc = ha_get_float(HBC_STRAT_SELL_TARGET_SOC, SOC_MIN        , raise_error=False)
                hbc_buy_target_soc  = ha_get_float(HBC_STRAT_BUY_TARGET_SOC , SOC_MAX        , raise_error=False) 
                hbc_max_charge      = ha_get_float(HELIOS_TEMPL_HBC_MAX_CHG , 1000*MAX_CHARGE, raise_error=False) # Maximum HBC Battery Charge    Power in W
                hbc_max_discharge   = ha_get_float(HELIOS_TEMPL_HBC_MAX_DIS , 1000*MAX_DISCH , raise_error=False) # Maximum HBC Battery Discharge Power in W

                # Initialize the Helios Battery Entities:
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_BAT_ENABLED , BAT_ON    ) 
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOC_TARGET  , SOC_TARGET)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOC_MIN     , hbc_sell_target_soc)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOC_MAX     , hbc_buy_target_soc )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_CHARGE_LIMIT, hbc_max_charge    / 1000)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_DISCH_LIMIT , hbc_max_discharge / 1000)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_CHARGE_EFF  , BAT_EFF   )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_DISCH_EFF   , BAT_EFF   )

                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOLAR_MODE  , SOLAR_MODE)

            # Update the Helios Optimizer Version (above initializations will not happen again afterwards until the version is increased):
            ha_set_text(HELIOS_INPUT_VERSION, HELIOS_VERSION) # Store the latest version in HA Entity

            try: # Create a Home Assistant Persistent Notification
                title   = "Helios Optimizer Initialized"
                message = f"Helios Optimizer has been upgraded to version '{HELIOS_VERSION}'."
                if (init_count > 0):
                    message += f"\nHelios Optimizer Initialized {init_count} Entities."

                persistent_notification.create( # Only in HA!
                    title=title,
                    message=message,
                    notification_id="helios_optimizer_init"
                )
            except: # Not Possible outside Home Assistant!
                log.warning(f"{title}: {message}")

def helios_optimizer_init_entity(entity_id: str, value: any, raise_error = True) -> int:
    """Initialize an Entity State with the (default) value (Integer, Float, Boolean or String)."""
    entity_count = 0
    if ha_exist(entity_id):
        try:
            if isinstance(value, bool): # First check on boolean (since a boolean is also an integer)
                ha_set_bool(entity_id, value, existing_only=True)
            elif isinstance(value, int):
                ha_set_int(entity_id, value, existing_only=True)
            elif isinstance(value, float):
                ha_set_float(entity_id, value, existing_only=True)
            else:
                ha_set_text(entity_id, str(value), existing_only=True)

            entity_count = 1 # Entity Updated

        except Exception as e: # An Error occured in the Entity Update

            error_message = f"Initialization of Helios Optimizer Entity '{entity_id}' Failed: {repr(e)}"
            if raise_error:
                raise ValueError(error_message) 
            log.error(f"[{HELIOS_SERVICE_NAME}-Init-Entity] Exception: {error_message}")
    else:
        error_message = f"Helios Optimizer Entity '{entity_id}' does not exist!"
        if raise_error:
            raise TypeError(error_message) 
        log.warning(f"[{HELIOS_SERVICE_NAME}-Init-Entity] Error: {error_message}")

    return entity_count # Helios Entity Initialization Successful (return 1)

@service(supports_response="optional") 
def helios_hello_world(
    entity_id: str = None, # Entity ID to retrieve
    attr_name: str = None, # Attribute Name (Optional)
    return_response=None,  # Return a result (must be a Dictonary!)
    trigger_type=None,     # Trigger type (time_trigger, state_trigger, event_trigger) for the service call
    context=None,          # Context of the service call (used for logging and debugging)
    **kwargs  # <--- Catches all unknown parameters 
    ):
    """
    Helios Optimizer Hello World Service for testing of Home Assistant PyScript State Functions and for a HA Notification. 
    If it runs you can be sure that PyScript is working!
    This function will return a dictionary with all Attributes of the Entity or a name: value of the specified Attribute.
    Specify an Entity (with entity_id) and an optional Attribute (attr_name). Without any argument the Helios Optimizer Energy Plan Entity will be used.
    For Entities that do not exist or Attributes that do not exist, an error message will be returned.
    Any Exception that is thrown will be caught and the error message will be returned aswell.
    The Service always returns a Dictionary with all of the Attributes or a single Attribute (attr_name: attr_value) or an Error/Exception.
    For debugging purposes it will also log the results of the retrieval of entity state, number of attributes and optional an entity attribute value.
    """
    results, message = {}, None
    try:
        if (entity_id is None) or (entity_id == ""): # Entity Id not specified?
            entity_id = HELIOS_OPTIM_PLAN # Use the default Helios Optimizer Energy Plan Entity Id

#       value = state.get(entity_id) # Get Entity using State (throws an exception when entity id does not exist)
        if state.exist(entity_id): # Does the Entity Exist?
            value = state.get(entity_id) # Get Entity using State
            log.error(f"[{HELIOS_SERVICE_NAME}]: Get Entity({entity_id}): '{value}'")
            attributes = state.getattr(entity_id) or {} # Get Entity Attributes using state.getattr (returns a Dictionary or None when entity does not exist, so use {} as default)
#           log.error(f"[{HELIOS_SERVICE_NAME}]: Get Entity-Attrs({entity_id}): {attributes}") # Warning: Can be a lot of data in the log for large attributes
            log.error(f"[{HELIOS_SERVICE_NAME}]: Get Entity-Attrs({entity_id})-Length: {len(attributes)}") # Return the number of attributes for the entity (can be 0 when no attributes exist)

            if (attr_name != None): # Attribute name specified, retrieve the attribute value
                if attr_name in attributes.keys(): # Does the attribute exist?
                    attr1_value = attributes.get(attr_name, 'onbekend1') # Use state.getattr with entity_id and get with attr_name
                    if isinstance(attr1_value, str): # String? (Only print when attribute is a string, not dictionaries or lists)
                        log.error(f"[{HELIOS_SERVICE_NAME}]: Get1 Entity-Attr({entity_id},{attr_name}): '{attr1_value}'")
                
                    attr2_value = state.get(f"{entity_id}.{attr_name}") # Use state.get with entity_id.attr_name
                    if isinstance(attr2_value, str): # String? (Only print when attribute is a string, not dictionaries or lists)
                        log.error(f"[{HELIOS_SERVICE_NAME}]: Get2 Entity-Attr({entity_id},{attr_name}): '{attr2_value}'")

                    if isinstance(attr1_value, (dict)): # Attribute Value already a dictionary?
                        results = attr1_value # Return the attribute value as a dictionary
                    else: # Attribute Value is not a dictionary (We need to return a dictionary so convert the value to a dictionary)
                        results = {attr_name: attr1_value} # Return the attribute value as a dictionary with the attribute name as key
                
                else: # Attribute does not exist!
                    message = f"Attribute '{attr_name}' for Entity Id '{entity_id}' does not exist!"
                    results = {"Error": message}
            
            else: # No Attribute name specified (return All Attributes)!
                results = attributes # Return the Attributes as a dictionary

        else: # Entity does not exist!
            message = f"Entity Id '{entity_id}' does not exist!"
            results = {"Error": message}
    
    except Exception as e:
        message = repr(e)
        results = {"Exception": message}

    try: # Create a Home Assistant Persistent Notification
        if message is None: # No message yet so built one with the Entity Info (without all attributes)
            title   = "Helios Optimizer Hello World is Ready"
            message = f"Entity '{entity_id}' has State Value '{value}' and has {len(attributes)} attributes."
        else: # Message already exists (error or exception), so use it as the notification message
            title   = "Helios Optimizer Hello World has an Error"

        persistent_notification.create( # Only in HA!
            title=title,
            message=message,
            notification_id="helios_hello_world"
        )
    except: # Not Possible outside Home Assistant!
        log.warning(f"{title}: {message}")

    return results # Return always a dictionary 

# Home Assistant Service to Start the Helios Automation and Show the Running Status in the UI
# This service is called by the Home Assistant Button in the UI and triggers the Helios Automation to calculate the optimized energy plan
# All the input parameters for the optimization are provided by the Home Assistant Helios Automation, so this service does not need any input parameters
# Warning: This service cannot be started in Visual Studio since it has no access to the HA Automation!
@service
def helios_optimizer_automation():
#   state.delete(HELIOS_OPTIM_PLAN) # Removes the Optimized Energy Plan (disable the automation.trigger since otherwise a new plan is created as a pyscript entity)

    # 1. Turn on the helios optimizer running status (switches the button to orange)
    state.set(HELIOS_RUNNING, "on", friendly_name=HELIOS_RUNNING_NAME)
    
    # 2. Start/Trigger the HA Automation (which also provides the input parameters for the above service)
    automation.trigger(entity_id=HELIOS_AUTOMATION)
    
    # 3. Wait an extra 1 second otherwise the color change of the start button will not be visible if the optimization is very fast (e.g. less than 200 millisecond)
    task.sleep(1)
    
    # 4. Turn off the helios optimizer running status (switches the button back to green)
    state.set(HELIOS_RUNNING, "off", friendly_name=HELIOS_RUNNING_NAME)

##########################################################################################################################
# Asynchronous Home Assistant Write and Read FILE Functions:                                                             # 
# VERY IMPORTANT: Use these functions instead of synchronous read/write functions in the Home Assistant Main Loop !!!!!  #
# The raw read/write functions are moved to helios_common.py and are now PURE Python functions (outside HA PyScript)     #
# In HA PyScript these raw read/write functions would need a special compiler option (@pyscript_compile)                 #       
# since otherwise no blocking read/writes were allowed in the HA!                                                        #
##########################################################################################################################
# Write a message with an optional timestamp to a file and add a newline
async def async_write_message(path: str, message: str, add_ts: bool = False, add_nl: bool = True) -> int:
    """
    Write a message to a (log) file with an optional timestamp and followed by a newline.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA). 
    The file is blocked during write but data could get mixed up (lines can get shuffled occasionally).
    """        
    # Write the formatted message to the Task Executor (off-thread)
    log.debug(f"Writing message to file '{path}' ...")
    char_count, formatted_msg = 0, format_log_message(message, add_ts, add_nl)
    try: # Try running the Task Excecutor
        char_count = await task.executor(raw_text_writer, path, formatted_msg) # Use the task executor to run the raw_file_writer function
#   except (NameError, AttributeError) as e: # If the task or the task.executor does not exist (NOT NEEDED anymore since the task.excecutor() has been added to the HA Mock) 
#       raw_text_writer(file_name, formatted_msg) # Run the raw_text_writer function without the task executor
    except Exception as e: # Everything failed, could not write the message
        log.error(f"[{HELIOS_ASYNC_FF_NAME}-Write-Msg] Exception: {repr(e)}")

    return char_count    

# Write a dictionary as JSON to a file
async def async_write_dict_to_json_file(path: str, dict_data: dict, default_type = str, indent: int = 4):
    """
    Write a dictionary as JSON to a file.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA).
    """       
    # "Write the formatted json to a file using the executor (off-thread)
    log.debug(f"Writing JSON file {path} from dictionary ...")
    char_count, json_str = 0, format_dict_as_json(dict_data, indent=indent, default_type = default_type)
    try: # Try running the Task Excecutor:
        char_count = await task.executor(raw_file_writer, path, json_str) # Use the task executor to run the raw_file_writer function
    except Exception as e: # Task Executor failed, could not write the json string
        log.error(f"[{HELIOS_ASYNC_FF_NAME}-Write-JSON] Exception: {repr(e)}")

    return char_count

# Write a List of Row Dictionaries in CSV format to a file with the specified column delimiter
async def async_write_csv_file(path: str, row_list: list[dict], headers: list = None, row_key: str = None, column_delimiter = ';') -> int:
    line_count = 0
    log.debug(f"Writing CSV file {path} from a list ...")
    try: # Try running the Task Excecutor:
        line_count = await task.executor(raw_csv_writer, path, row_list=row_list, headers=headers, row_key = row_key, column_delimiter=column_delimiter) # Use the task executor to run the raw_csv_writer function
    except Exception as e: # Task Executor failed, could not write the csv file
        log.error(f"[{HELIOS_ASYNC_FF_NAME}-Write-CSV] Exception: {repr(e)}")
    return line_count

# Read a JSON file into a dictionary
# Returns a dictionary or None (file not found or contains invalid JSON)
async def async_read_dict_from_json_file(path: str) -> dict:
    """
    Read a JSON file into a dictionary.
    Executor handles this off-thread (so the file reading does not hold up the main loop of HA).
    """       
    # Read the file content into a string using the executor (off-thread)
    log.debug(f"Reading JSON file {path} into a dictionary ...") 
    try: # Try running the Task Excecutor
        json_str  = await task.executor(raw_file_reader, path) # Use the task executor to run the raw_file_writer function
        json_dict = convert_json_to_dict(json_str) # Convert the JSON string to a dictionary and return it (returns None when JSON string is None)
        if json_dict is None: # Conversion from JSON to Dictionary failed?
            log.error(f"Read JSON File Exception: JSON Conversion Failed, returning {json_dict}")
    except Exception as e: # Task Executor failed, could not read the json string
        log.error(f"[{HELIOS_ASYNC_FF_NAME}-Read-JSON] Exception: {repr(e)}")
        json_dict = None

    return json_dict # Return the dictionary or None when file not found or invalid

##########################################################################
# PyScript Home Assistant State Functions                                #
# Copied from _batmgt_util.py and modified for use in Helios             #
# Not yet applied to the Battery Management System (BMS)                 #
# Warning: Use hass (instead of state) for python and custom_components! #
##########################################################################
# Exist Home Assistant Entity
def ha_exist(entity_id: str) -> bool:
    """Check if a Home Assistant State exists."""
    return state.exist(entity_id) # Check if the state name exists in the Home Assistant state dictionary

def ha_is_unknown(entity_id: str): return state.is_unknown(entity_id)
def ha_is_unavailable(entity_id: str): return state.is_unavailable(entity_id)
def ha_has_value(entity_id: str): return state.has_value(entity_id)

def ha_as_dict(entity_id: str) -> dict: 
    """Built a dictionary for an entity within Pyscript."""
    # Warning: state.as_dict does not exist in PyScript!
    value = state.get(entity_id)
    if value is None: # Does Entity Exist?
        return None # Entity does not exist (return None)
        
    return { # Return the Entity as a Dictionary with a sub-dict for the attributes
        "entity_id": entity_id,
        "state": value, # Value of the Entity (can also be HA_UNKNOWN or HA_UNAVAIL)
        "attributes": state.getattr(entity_id) or {} # All Attributes as a Dictionary
    }

# Get Internal State from Home Assistant Entity State (copied from state_get_state in _batmgt_util.py).
# Internal State is a text value but represents the state of a Device or System.
# Home Assistant states (for 'unknown' and 'unavailable') are integrated as state values (UNKNOWN_STATE and UNAVAIL_STATE). 
# None is handled as equal to 'unknown' (Remark: None is not possible as a entity state value in HA).
# For an Entity Id of None a NONAME_STATE is returned. For an non existing Entity an error will occur.
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_get_state(entity_id: str, default_value: str = FAILED_STATE, ignore_undefined: bool = False, raise_error: bool = False) -> str: 
    """ 
    Get Internal State (Text field with State values) from Home Assistant State
    Convert HA unknown and unavailable to "Unknown" and "Unavailable" unless ignore undefined is True (then the default value (FAILED_STATE) is returned)
    Warning: Use ha_exist for separate handling of states that do not exist (this function will throw an exception)
    """
    state_value = NONAME_STATE # Initial value is not the default (NONAME_STATE will be returned when no entity id specified)
    try:
        if (entity_id != None): # Entity Id specified?
            state_value = state.get(entity_id) # Retrieve the state of the HA Entity

        if (state_value in HA_UN_LIST or state_value is None) and ignore_undefined:
            state_value = default_value # Default value is returned when ignore undefined and (value is HA unknown or unavailable or None)

        else: # Handle HA unknown and HA unavailable as separate state values
            if (state_value == HA_UNKNOWN) or (state_value is None):
                state_value = UNKNOWN_STATE # Set the "Unknown" state
            elif (state_value == HA_UNAVAIL):
                state_value = UNAVAIL_STATE # Set the "Unavailable" state
            
    except (Exception) as e: # An error occurred while retrieving the state
        if state.exist(entity_id): # Entity exist but State conversion failed (Remark: Not sure what can go wrong in state conversion)? 
            error_msg = f"State Conversion Failed for HA Entity '{entity_id}' with value '{state_value}': {repr(e)}"
        else: # Get performed but failed since entity does not exist
            error_msg = f"HA State Entity {entity_id} does NOT Exist!"
        if raise_error:
            raise ValueError(error_msg)
        log.error(f"[{HELIOS_SERVICE_NAME}-ha-get-state] Exception: {error_msg}")
        state_value = default_value # Usually: FAILED_STATE
            
    return str(state_value) if (state_value != None) else None # Always return as string unless None

# Get Text from Home Assistant Entity State 
# For an non existing Entity an error will occur.
def ha_get_text(entity_id, default_value: str = None, ignore_undefined: bool = True, raise_error: bool = False) -> str: 
    """ 
    Get Text from Home Assistant Entity State
    By default "unknown" or "unavailable" values will return None but when ignore undefined is False the values will be returned as-is.
    Warning: Use ha_exist for separate handling of states that do not exist (this function will throw an exception)
    """
    state_value = None
    try:
        if (entity_id != None): # Entity Id specified?
            state_value = state.get(entity_id) # Retrieve the state of the HA Entity

        if (state_value in HA_UN_LIST or state_value is None) and ignore_undefined:
            state_value = default_value # Default value is returned when ignore undefined and (value is HA unknown or unavailable or None)
            
    except (Exception) as e: # An error occurred while retrieving the entity state for the text field
        if state.exist(entity_id): # Entity exist but State conversion failed (Remark: Not sure what can go wrong in text conversion)? 
            error_msg = f"Text Retrieve Failed for HA Entity '{entity_id}': {repr(e)}"
        else: # Get performed but failed since entity does not exist
            error_msg = f"HA Text Entity {entity_id} does NOT Exist!"
        if raise_error:
            raise ValueError(error_msg)
        log.error(f"[{HELIOS_SERVICE_NAME}-ha-get-text] Exception: {error_msg}")
        state_value = default_value
            
    return str(state_value) if (state_value != None) else None # Always return as string unless None

# Get Float from Home Assistant Entity State (copied from state_get_float in _batmgt_util.py)
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_get_float(entity_id: str, default_value: float = None, ignore_undefined: bool = True, raise_error: bool = False) -> float:
    """
    Get a float value for a Home Assistant state value. 
    By default "unknown" or "unavailable" values will return None but when ignore undefined is False an exception will be thrown.
    Warning: For the Anker Output Preset value ignore_unknown MUST be enabled since this value is only used with mode "manual" and may be unknown for other modes.
    Warning: In general For HomeWizard and Anker attribute the state can be temporary unavailable (during startup or for communication errors).
    Returns Float Value or None when HA state is unavailable, unknown or for an invalid number (string)!
    """
    state_value, float_value = None, None
    try:
        if (entity_id != None): # Entity Id specified?
            state_value = state.get(entity_id) # Retrieve the state of the HA Entity (throws an exception when the entity does not exist)

        # float() works for numbers (e.g. 10 or 10.5) and string numbers (e.g. "10.5")
        # but fails for None, "unavailable" of "unknown"
        if (state_value in HA_UN_LIST or state_value is None) and ignore_undefined:
            state_value = default_value  # Return default_value when ignore undefined and (value is unknown or unavailable or None)

        # Try to convert the value to float (will fail with an exception when value is not a float or an integer (including for unknown and unavailable))
        float_value = float(state_value) if (state_value != None) else None # Convert from string to float unless None
    
    except (Exception) as e: # Conversion Error or Get Error (Remark: used for floats but also for integers)
        if state.exist(entity_id): # Entity exist but Float conversion failed?
            error_msg = f"Float or Integer Conversion Failed for HA Entity '{entity_id}' with value '{state_value}': {repr(e)}"
        else: # Get performed but failed since entity does not exist
            error_msg = f"HA Float or Integer Entity {entity_id} does NOT Exist!"
        if raise_error:
            raise ValueError(error_msg)
        log.error(f"[{HELIOS_SERVICE_NAME}-ha-get-float] Exception: {error_msg}")
        float_value = default_value

    return float_value

def ha_get_bool(entity_id: str, default_value: bool = False, ignored_undefined: bool = True) -> bool:
    state_value, bool_value = None, None
    try:
        if (entity_id != None): 
            state_value = state.get(entity_id) # Retrieve the state of the HA Entity

        if (state_value in HA_UN_LIST or state_value is None) and ignore_undefined:
            state_value = default_value # Return default_value when ignore undefined and (value is unknown or unavailable or None)

        # Convert the value to bool (only for state_value is 'on')
        bool_value = (state_value == HA_ON) if (state_value != None) else None # Convert from string to bool unless None

    except (Exception) as e: # Conversion Error for Boolean
        if state.exist(entity_id): # Entity exist but Boolean conversion failed?
            error_msg = f"Boolean Conversion Failed for HA Entity '{entity_id}' with value '{state_value}': {repr(e)}"
        else: # Get performed but failed since entity does not exist
            error_msg = f"HA Boolean Entity {entity_id} does NOT Exist!"
        if raise_error:
            raise ValueError(error_msg)
        log.error(f"[{HELIOS_SERVICE_NAME}-ha-get-bool] Exception: {error_msg}")
        bool_value = default_value

    return bool_value

# Get Integer from Home Assistant Entity State (copied from state_get_int in _batmgt_util.py)
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_get_int(entity_id: str, default_value: int = None, ignore_undefined: bool = True, raise_error: bool = False) -> int:
    float_value = None # Start with a Float (not with an integer)
    if (entity_id != None): # Entity Id defined?
        float_value = ha_get_float(entity_id, default_value, ignore_undefined, raise_error) # # Retrieve the state of the HA Entity as a float (only later convert to integer)
    return round(float_value) if (float_value != None) else None # Convert to an integer

# Get All the Attributes of a Home Assistant Entity
# Returns Dictonary with all Attribute or None when the Entity does not exist
def ha_get_all_attr(entity_id: str) -> dict:
    if ha_exist(entity_id): # Entity exist?
        return state.getattr(entity_id)
    else: # Entity does not exist
        return None

# Get the Attribute Value of a Home Assistant Entity
# Returns Value of the Attribute or None when the Entity does not exist or when the Entity does not have the Attribute
def ha_get_attr(entity_id: str, attr_name: str, default_value = None):
    value = default_value
    attributes = ha_get_all_attr(entity_id)
    if (attributes != None) and attr_name in attributes.keys(): 
        value = attributes[attr_name]
    return value

# Set Internal State in Home Assistant Entity State (copied from state_set_state in _batmgt_util.py) and optionally the related attributes
# Attributes can be combined in the new_attributes dictionary or specified separatedly (via **attribs) or both
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_set_state(entity_id: str, value: str = None, existing_only: bool = False, new_attributes: dict = None, **attribs) -> bool:
    updated = False
    if not existing_only or ha_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(value) # Replace a None value by HA 'unknown' ("Onbekend" in Nederlands)
            if (value == UNKNOWN_STATE): state_value = HA_UNKNOWN # Replace a "Unknown"     by HA 'unknown'
            if (value == UNAVAIL_STATE): state_value = HA_UNAVAIL # Replace a "Unavailable" by HA 'unavailable'
            if (new_attributes == None):
                state.set(entity_id, state_value, **attribs)
            else:    
                state.set(entity_id, state_value, new_attributes=new_attributes, **attribs)
            updated = True
    return updated # True when updated

# Set Text in Home Assistant Entity State (copied from state_set_state in _batmgt_util.py) and optionally the related attributes
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_set_text(entity_id: str, value: str = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(value) # Replace a None value by HA "unknown" ("Onbekend" in Nederlands)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Entity Attribute in Home Assistant Entity
def ha_set_attr(entity_id: str, attr_name: str, value):
    updated = False
    if ha_exist(entity_id): 
        state.setattr(entity_id+'.'+attr_name, value)
        updated = True
    return updated # True when updated

# Set Integer in Home Assistant Entity State (copied from state_set_int in _batmgt_util.py)
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_set_int(entity_id: str, value: int = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(int(value)) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Float in Home Assistant Entity State
def ha_set_float(entity_id: str, value: float = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(float(value)) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Boolean in Home Assistant Entity State
def ha_set_bool(entity_id: str, value: bool = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else (HA_ON if value else HA_OFF) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Delete a Home Assistant Entity
def ha_delete(entity_id: str) -> bool:
    deleted = False
    if ha_exist(entity_id):
        state.delete(entity_id)
        deleted = True
    return deleted # True when deleted