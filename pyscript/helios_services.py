# Main: Helios Services - PyScript Home Assistant Services to publish the Helios Optimizer
# HELIOS is the Home Energy Linear Integrated Optimization Service which calls the Helios Optimizer to calculate the Optimal Energy Plan.
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
#   2026-10-21: JR  v0.92c Added a Helios Strategy to HBC that handles the output from Helios, Included error handling (if Helios fails the sub-strategy will be set to "Unknown", "unknown" in HA and the Helios Strategy will apply the "Full stop" strategy)
#   2026-10-26  JR  v0.93  Replaced the Helios Automation Task by a PyScript Service that runs every 15-min and retrieves Helios and HBC parameters from HA entities, Single Instance of Helios Service and Task (New Run Killed otherwise)
#   2026-10-28: JR  v0.93  First public release with HBC Output (works together with Helios Strategy in HBC)
#   2026-10-28: JR  v0.93a Initialized the step size for the House Daily Usage Distribution array (house_size), prevent an exception when distribution is empty, flat usage will be used
#   2026-10-28: JR  v0.93a Check HBC Price Data is available and return an error when no price data found (optimizer will NOT continue)
#   2026-10-29: JR  v0.93a Handle invalid PyScript Configuration ('Allow All Imports' and 'Access hass as a global variable') must be enabled
#   2026-10-31: JR  v0.94  Added Price Type, Source Provider and Target Provider for Price Conversions
#   2026-11-02: JR  v0.94  Introduced Horizon (in Days) as a input parameter replacing steps, steps will be calculated from horizon and step size, the steps entity will be updated after a optimization run
#   2026-11-03: JR  v0.94a Added a Net Metering Option in the advanced parameters (only for dutch Salderingregeling in 2026)
#   2026-11-07: JR  v0.94c Improved error handling for installation (pyscript import and hass)
#   2026-11-20: JR  v0.96  Adapted the run times for the Helios Optimizer Task (Triggered every 15 min at HH:01,HH:16,HH:31,HH:46), leaves enough time for completion of helios_forecast (and possible other data prepare jobs) (Thanks Rubbere)
#   2026-11-20: JR  v0.96  Removed the state trigger (HELIOS_FORECAST_SOLAR) which is triggered by the completion of helios_forecast.py running at the whole hour (HH:00), state trigger for REST API remains (HELIOS_FORECAST_SOLAR_ALT)
#   2026-11-20: JR  v0.96  Support for longer optimization periods (horizon of 3-7 days is allowed with a maximum of 644 steps (7 days x 24 hours x 4 steps of 15-min) - No change in helios_services (see helios_optimizer)
#   2026-11-22: JR: V0.96  Improved the Helios Hello World Service to use the pyscript state functions in a hass wrapper and report import and hass errors in the notification message
#   2026-11-23: JR  v0.96  Helios Optimizer Service now reports a count of initialized entities via a HA notification message (only for a helios version change or when the version entity is not available)
#   2026-11-23: JR: V0.96  Split of 'PyScript' functions that are used in multiple PyScript Services (introduced helios_hass.py in /pyscript/modules)
#   2026-11-26: JR: V0.9.6 Added Home Assistant Datetime Utility functions to Helios Hass (ha_now_ts and ha_now_info), used by Helios Forecast and Helios Services
#   2026-11-26: JR: V0.96  Added support for Helios Configuration File for Price Providers, Price Defaults and Helios to HBC Strategy Mapping
#   2026-11-27: JR: V0.96  Added the helios_optimizer folder and below that folder split into export (HA & MS VSs), test & results (MS VS Regression testing)
#
#   Remark: For a full history see helios_main.py 

# Check if imports are enabled (Only Applicable in the Home Assistant PyScript environment):
IMPORTS_FAILED_SERV, HOME_ASSISTANT_SERV = False, False # Imports Not failed yet, Not in HA environment
try:
    import sys  # For sys.path.append() to add the Home Assistant /config/pyscript folder to the path to allow /config/pyscript/helios_python to be found !!!
    import traceback # Traceback for Exception Handling (to get the full error message with line-nbr, etc)  

    try: # Assume we are running in MS Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
        # Home Assistant will not have the home_assistant_mock.py (and the import will FAIL): 
        from home_assistant_mock import * # Import the Home Assistant Mockup for Visual Studio (to allow PyScript testing in Visual Studio)
    except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
        HOME_ASSISTANT_SERV = True
except (ImportError, Exception) as e:
    IMPORTS_FAILED_SERV = True # Allow the helios_services.py to be loaded without imports and report the error later on
    HOME_ASSISTANT_SERV = True # Imports only fail in Home Assistant (usually)

    # Simplified version of helios_hass.py in case imports fail:
    def ha_entity_exist  (e_id: str): return state.exist(e_id)
    def ha_is_unavailable(e_id: str): return state.get(e_id).is_unavailable()
    def ha_set_state(e_id: str, value: str  = None, new_attributes = None, **attribs): state.set(e_id, value='unknown' if (value is None) or (value=='Unknown') else str(value), new_attributes=new_attributes, **attribs)
    def ha_set_int  (e_id: str, value: int  = None): state.set(e_id, value=('unknown' if value is None else str(int(value)) ))
    def ha_set_bool (e_id: str, value: bool = None): state.set(e_id, value=('unknown' if value is None else ('on' if value else 'off') ))

# IMPORTS_FAILED_SERV, Sys, traceback = True, None, None # Testing Imports Failed

# Setup the environment (Visual Studio or Home Assistant):
if not HOME_ASSISTANT_SERV:
    HELIOS_FOLDER  = 'helios_optimizer'               # Main Input/Output Folder of Helios Optimizer (contains the helios_optimizer_config.json and sub-folder(s))
    HELIOS_EXPORT  = 'helios_optimizer/export/'       # Used by Helios Services AND Helios Main (in Visual Studio)
    HELIOS_RESULTS = 'helios_optimizer/results/'      # Only used by Helios Main for test result (in Visual Studio)
    HELIOS_TEST    = 'helios_optimizer/test/'         # Only Used by Helios Main for input and expected test files (in Visual Studio)

    # Modules used by Visual Studio need to start with 'modules.' since they are always in a sub-folder 'modules'
    from modules.helios_hass import * # Import the Helios Home Assistant functions from folder ./modules/
else: # Assume we are in Home Assistant (since the mockup was not found or imports have failed)
    HELIOS_FOLDER = '/config/helios_optimizer/'       # Used by Helios Services for the configuration
    HELIOS_EXPORT = '/config/helios_optimizer/export' # Used by Helios Services for exports

    if not IMPORTS_FAILED_SERV: # Further imports and sys functions only when (HA PyScript) import did not fail
    #   import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
    #   _LOGGER  = logging.getLogger(__name__) # Get access to the HomeAssistant Logger in standard python functions (not needed in helios_services since access to HA log is available)

        # Modules used by Home Assistant with PyScript must be in the 'modules' folder of the Home Assistant configuration directory! 
        from helios_hass import * # pyright: ignore[reportMissingImports] # Import the Helios Home Assistant functions WITHOUT specifying the 'modules' folder

        # Add for Home Assistant the Pyscript folder to the system path (not needed for MS Visual Studio since the main folder is already in the path)
        # Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)
        if "/config/pyscript" not in sys.path: # Pyscript Folder already in the search path?
            sys.path.append("/config/pyscript") # Add the Home Assistant Pyscript folder to the system path
    
# Pure Python Files must be in the sub-folder helios_python 
# In HA: pyscript/helios_python (/config/pyscript must have been appended to the sys.path),
# In VS: c:\$code\VisualStudio2026\HeliosOptimizer\helios_python)
if not IMPORTS_FAILED_SERV: 
    from helios_python.helios_optimizer import * # Import helios_optimizer.py for the Helios Pure Python Calculate Plan function and other Optimize Energy functions (and Helios Common Functions via helios_common.py)
#   from helios_python.helios_common    import * # Import helios_common.py (Not needed since helios_optimizer also imports helios_common.py)

# Check if access to hass is available (via Home Assistant or via the Mockup)
HASS_NO_ACCESS_SERV = False # Hass Acess Not checked yet
try:
    # Check if access to hass.config_entries is available (needed for helios_forecast.py, otherwise no solar forecast will be available)
    config_entries = hass.config_entries
except NameError as e:
    HASS_NO_ACCESS_SERV = True # No Access to Hass available

# HASS_NO_ACCESS_SERV = True # Testing Hass no Access in Visual Studio (to test the error handling in helios_services.py)

HELIOS_SERVICE_NAME  = 'Helios Optimizer Service'                  # Name of the Helios Optimizer Service
HELIOS_TASK_NAME     = 'Helios Optimizer HBC Task'                 # Name of the Helios Optimizer HBC Task
HELIOS_MAIN_NAME     = 'Helios Optimizer Regression Test'          # Name of the Helios Optimizer Main Routine (Regression Test)

# Constant values for the Home Assistant Entities and Automations used by the Helios Service
# Home Assistant Entities used by the Helios Optimizer Service (these entities must be created in Home Assistant before the service can be used)
HELIOS_ENERGY_PLAN       = 'input_number.helios_optimizer_energy_plan'          # Sensor Helios Optimizer Result with Status, Current and Plan in the attributes
HELIOS_ENERGY_PLAN_OLD   = 'pyscript.helios_energy_plan'                        # Sensor Helios Result with Status, Current and Plan in the attributes
HELIOS_BAT_STRAT         = 'input_select.helios_optimizer_battery_strategy'     # Sensor Helios BatteryStrategy for the current step
HELIOS_HBC_SUB_STRAT     = 'input_select.helios_optimizer_hbc_sub_strategy'     # Sensor Helios Sub Strategy for HBC
HELIOS_HBC_NET_POWER     = 'input_number.helios_optimizer_hbc_net_power'        # Sensor Helios Net Battery Power for HBC (Charge is Positive, Discharge is Negative), Translated later to Charge and Discharge Power (both Positive)
HELIOS_RUNNING           = 'input_boolean.helios_optimizer_running'             # Sensor Helios Automation is running (True/False) for the UI Button to show the service is running (extra second added for short service calls)
HELIOS_AUTOMATION        = 'automation.helios_optimizer_automation_task'        # Sensor Helios Optimizer Automation Task that calls the Helios Optimizer Service to calculate the Optimal Energy Plan

# Home Assisant Entities (a copy in home_assistant_mock.py and the original in helios_services.py):
HELIOS_INPUT_VERSION     = 'input_text.helios_optimizer_version'                # Sensor Helios Optimizer Version 
HELIOS_INPUT_HORIZON     = 'input_select.helios_optimizer_horizon'              # Sensor Helios Optimizer Horizon in Days (0=Disabled, 1=Today, 2=Today and Tomorrow)
HELIOS_INPUT_STEPS       = 'input_number.helios_optimizer_steps'                # Sensor Helios Optimizer Steps (24, 48, 96 or 192 steps of 60 or 15 minutes), This is no longer an input and will now be derived from the Step Size and Horizon
HELIOS_INPUT_STEP_SIZE   = 'input_select.helios_optimizer_step_size'            # Sensor Helios Optimizer Step Size (Dropdown Select for 60 or 15 minutes)
HELIOS_INPUT_START_STEP  = 'input_number.helios_optimizer_start_step'           # Sensor Helios Optimizer Start Step (0=Automatic, 1-192 is manual for testing)
HELIOS_INPUT_MAX_GRID_IMP= 'input_number.helios_optimizer_max_grid_import'      # Sensor Helios Optimizer Maximum Grid Import in kW
HELIOS_INPUT_MAX_GRID_EXP= 'input_number.helios_optimizer_max_grid_export'      # Sensor Helios Optimizer Maximum Grid Export in kW
HELIOS_INPUT_HOUSE_USAGE = 'input_number.helios_optimizer_house_daily_usage'    # Sensor Helios Optimizer House Daily Usage over the Day in kWh
HELIOS_INPUT_HOUSE_DISTR = 'input_text.helios_optimizer_house_daily_distr'      # Sensor Helios Optimizer House Daily Distribution of the House Usage over the Day as a list of 24 or 96 relative values for each hour or quarter of an hour of the day
HELIOS_INPUT_NET_METERING= 'input_boolean.helios_optimizer_net_metering_enabled'# Sensor Helios Optimizer Net Metering Enabled (True/False, On/Off) - Salderingsregeling Enabled (only for 2026, includes Energy Tax in Export Price)

HELIOS_INPUT_BAT_ENABLED = 'input_boolean.helios_optimizer_battery_enabled'     # Sensor Helios Optimizer Battery Enabled (True/False, On/Off)
HELIOS_INPUT_SOC_TARGET  = 'input_number.helios_optimizer_soc_target_pct'       # Sensor Helios Optimizer Battery Target SOC (State of Charge) in % for the Optimization (for End of Optimizaton Period/Horizon)
HELIOS_INPUT_SOC_MIN     = 'input_number.helios_optimizer_soc_min_pct'          # Sensor Helios Optimizer Battery Minimum SOC (State of Charge) in % for the Optimization (Overall Minimum for ALL Steps / full Period)
HELIOS_INPUT_SOC_MAX     = 'input_number.helios_optimizer_soc_max_pct'          # Sensor Helios Optimizer Battery Maximum SOC (State of Charge) in % for the Optimization (Overall Maximum for ALL Steps / full Period)
HELIOS_INPUT_CHARGE_LIMIT= 'input_number.helios_optimizer_charge_limit'         # Sensor Helios Optimizer Maximum Battery Charge    Limit in kW   (all batteries together) 
HELIOS_INPUT_DISCH_LIMIT = 'input_number.helios_optimizer_discharge_limit'      # Sensor Helios Optimizer Maximum Battery Discharge Limit in kW   (all batteries together) 
HELIOS_INPUT_CHARGE_EFF  = 'input_number.helios_optimizer_charge_efficiency'    # Sensor Helios Optimizer Battery Charge    Efficiency Percentage (all batteries together) 
HELIOS_INPUT_DISCH_EFF   = 'input_number.helios_optimizer_discharge_efficiency' # Sensor Helios Optimizer Battery Discharge Efficiency Percentage (all batteries together) 

HELIOS_INPUT_SOLAR_MODE  = 'input_select.helios_optimizer_solar_mode'           # Input Select Helios Optimizer Solar Mode            (Dropdown with SOLAR_ALL, SOLAR_MOD, SOLAR_BIN or SOLAR_DIS)
HELIOS_INPUT_SOLAR_SOURCE= 'input_select.helios_optimizer_solar_source'         # Input Select Helios Optimizer Solar Forecast Source (Dropdown with FORECAST_FS_INTEGR and FORECAST_FS_REST)

HELIOS_INPUT_PRICE_SENSOR= 'input_select.helios_optimizer_price_entity_id'      # Input Select Helios Optimizer Price Sensor          (Dropdown with Source Price Data Sensors, currently not used)
HELIOS_INPUT_PRICE_TYPE  = 'input_select.helios_optimizer_price_type'           # Input Select Helios Optimizer Price Type            (Dropdown with PT_IMPORT, PT_EXPORT and PT_MARKET)
HELIOS_INPUT_SOURCE_PROV = 'input_select.helios_optimizer_source_provider'      # Input Select Helios Optimizer Source Provider       (Dropdown with Source Provider Names)
HELIOS_INPUT_TARGET_PROV = 'input_select.helios_optimizer_target_provider'      # Input Select Helios Optimizer Target Provider       (Dropdown with Target Provider Names)

HELIOS_TEMPL_HBC_MAX_CAP = 'sensor.helios_template_hbc_maximum_energy'          # Sensor Helios Template with HBC Total Maximum   Energy for all of the Batteries
HELIOS_TEMPL_HBC_REM_ENGY= 'sensor.helios_template_hbc_remaining_energy'        # Sensor Helios Template with HBC Total Remaining Energy for all of the Batteries
HELIOS_TEMPL_HBC_TOT_SOC = 'sensor.helios_template_hbc_total_soc'               # Sensor Helios Template with HBC Total SOC Percentage   for all of the Batteries (derived from Maximum and Remaining above)
HELIOS_TEMPL_HBC_MAX_CHG = 'sensor.helios_template_hbc_max_charge_power'        # Sensor Helios Template with HBC Maximum Battery Charge    Power
HELIOS_TEMPL_HBC_MAX_DIS = 'sensor.helios_template_hbc_max_discharge_power'     # Sensor Helios Template with HBC Maximum Battery Discharge Power

HELIOS_SOLCAST           = 'pyscript.helios_optimizer_solcast_data'             # Pyscript Entity filled from existing Solcast integration and the related Query Forecast Data Service
HELIOS_FORECAST_SOLAR    = 'pyscript.helios_optimizer_forecast_solar_data'      # Pyscript Entity filled from existing Forecast.Solar integration and the related Get Forecast Service
HELIOS_FORECAST_SOLAR_ALT= 'sensor.helios_optimizer_forecast_solar_hours'       # Sensor filled by REST API and Template

HBC_STRAT_SELL_TARGET_SOC = 'input_number.house_battery_strategy_sell_target_soc'     # Sensor HBC Strategy Sell (Discharge) Target SOC Percentage
HBC_STRAT_BUY_TARGET_SOC  = 'input_number.house_battery_strategy_charge_target_soc'   # Sensor HBC Strategy Buy  (Charge   ) Target SOC Percentage
HBC_PRICE_DATA_SOURCE     = 'input_select.house_battery_strategy_dynamic_data_source' # Sensor HBC Price Data Source for Dynamic Strategy
HBC_ENERGY_PRICE_DATA     = 'sensor.hbc_energy_prices_data'                           # Sensor HBC Energy Price Data (Generated only for strategies: Dynamic and Helios!)

HELIOS_PLAN_NAME     = 'Helios Optimizer Energy Plan'              # Friendly Name for the Helios Result Entity
HELIOS_RUNNING_NAME  = 'Helios Optimizer Running'                  # Friendly Name for the Helios Running Entity  

HELIOS_CONFIG_FNAME  = 'helios_optimizer_config.json'              # JSON Configuration file with the user overwrites of Helios Parameters (Price Providers and Defaults, ....)
HELIOS_OUTPUT_FNAME  = 'helios_optimizer_output.json'              # JSON Output file with the output results   for testing purposes (see main), renamed to _expected_xxx for validation
HELIOS_PLAN_FNAME    = 'helios_optimizer_plan.csv'                 # CSV  Output file with the plan variables as a spreadsheet table (value for each step), used in main    (see alos TABLE)
HELIOS_PARAMS_FNAME  = 'helios_optimizer_params.json'              # JSON Output file with the input parameters for the optimizer
HELIOS_PAYLOAD_FNAME = 'helios_optimizer_payload.json'             # JSON Output file with the output (payload) of  the optimizer
HELIOS_TABLE_FNAME   = 'helios_optimizer_table.csv'                # CSV  Output file with the plan variables as a spreadsheet table (value for each step), used in service (see also PLAN)
HELIOS_PROFILE_FNAME = 'helios_optimizer_profile.csv'              # JSON file with the Helios Profile (includes price profiles)
HELIOS_INPUT_FNAME5  = 'helios_optimizer_input_ha_192s15i81.json'  # JSON Input file  with the input parameters for testing purposes (see main), only for run type 0 (others use the base parameters from main)
HELIOS_INPUT_FNAME6  = 'helios_optimizer_input_ha_price_test.json' # JSON Input file  with the input parameters for testing purposes (see main), only for run type 0 (others use the base parameters from main)
HELIOS_RESULTS_FNAME = 'helios_test_results_{date}.csv'            # CSV  Output file with the results summary  for multiple test runs (date is replaced by current date)

SERVICE_PERFORMANCE_MS: list = [] # Global variable for Performance of all runs (collecting performance results for multiple runs)

FORECAST_SC_INTEGR  = 'Solcast Integration'        # Retrieved from the Integration with a Service and stored into HELIOS_SOLCAST        (see helios_forecast.py)
FORECAST_FS_INTEGR  = 'Forecast.Solar Integration' # Retrieved from the Integration with a Service and stored into HELIOS_FORECAST_SOLAR (see helios_forecast.py)   
FORECAST_FS_REST    = 'Forecast.Solar REST api'    # Retrieved from a REST api and converted with a template  into HELIOS_FORECAST_SOLAR_ALT (see helios_optimizer_forecast.yaml)
HBC_DATA_SOURCE     = "HBC Data Source" # Use HBC Price (Tariff) Data Source for the Source and/or Target Provider instead of a specific provider 
DEFAULT_HORIZON     = 2 # Default Horizon in Days (1=Today, 2=Today and Tomorrow)

IMPORTS_FAILED_MSG  = "PyScript Imports Failed! Helios needs 'Allow all imports' to be enabled. ADAPT the PyScript configuration and restart HA."
HASS_NO_ACCESS_MSG  = "Hass is NOT accessable by PyScript! Helios needs 'Access Hass as a global variable' to be enabled. ADAPT the PyScript configuration and restart HA."

# Helios Optimizer Service with a return response (payload with the results of the calculation)
# Definition of the Home Assistant Service that calculates an Optimized Energy Plan
# The Service handles only the Home Assistant specific calls
# The actual calculation is done by helios_optimizer_calc_plan() and runs using pure python (without HA specific pyscript functions)
@service(supports_response="optional") 
async def helios_optimizer_service(
    steps=None,      # Optimization Steps:     24 steps for 60 minutes is one day,  48 steps is two days
    step_size=None,  # Optimization Step Size: 96 steps for 15 minutes is one day, 192 steps is two days
    start_step=None, # Optimization Starts at Start Step (1..steps), 0 = Determine start step automatically using current time

    price_size=None, # None when resample of price          array is not needed, price step size when step size of price          input array is not equal to the optimization step size
    house_size=None, # None when resample of house forecast array is not needed, house step size when step size of house forecast input array is not equal to the optimization step size
    solar_size=None, # None when resample of solar forecast array is not needed, solar step size when step size of solar forecast input array is not equal to the optimization step size
    price_factor=None,           # 1.0 (default) or 0.01 (convert from cents to euro), NOT applicable to Source Price Data (see the provider profiles)

    max_grid_import_kw=None,     # Maximum Grid Import Power (kW) for the Optimization
    max_grid_export_kw=None,     # Maximum Grid Export Power (kW) for the Optimization

    # Use House Energy Forecast or House Daily Usage and Distribution:
    house_daily_usage_kwh=None,  # House Daily Usage (kWh) as a total value, Alternative when house forecast array is not available, will be spread over the day using house_daily_distr
    house_daily_distr=None,      # House Daily Distribution of the House Usage over the Day as a list of 24 or 96 relative values for each hour or quarter of an hour of the day
    net_metering_enabled=False,  # Net Metering Enabled (True/False, On/Off) - Salderingsregeling Enabled (only for 2026, includes Energy Tax in Export Price)

    main_provider=None,          # Main Provider Key (used to retrieve the provider profile to calculate the Import/Export Prices from the Source Price Data), Not needed when import_prices and export_prices are provided directly
    price_type=None,             # Price Type are Market, Import or Export for the source_price_data
    source_provider=None,        # Source (Energy) Provider, Needed when the Source Price Data is provided indirectly by the Energy Provider (e.g. for HBC Price Data which is retrieved from original Provider Price Data using Cheapest Hours)
    target_provider=None,        # Target (Energy) Provider, Needed when the Source Price Data is provided by a different Provider then the Provider used for Providing Energy
    source_price_sensor=None,    # Source Price Sensor (Entity ID), Needed since the Home Assistant automation cannot pass the attributes of an Entity as a dictionary to the service via source_price_data

    max_time=None,               # Maximum Time for the Linear Programming Module (HiGHS Solver of SciPy)
    max_iterations=None,         # Maximum Iterations for the LP Module
    insight=None,                # Debug level
    write_files=True,            # Write the Helios Optimizer Input Parameters and Output Payload to export files for debugging and regression testing purposes (only applies to services output files not to VS Main)
    export_folder=None,          # Output folder for the export files  
    
    now_ts=None,                 # Ignored and retrieved again (now)
    now_tz=None,                 # Ignored and retrieved again (timezone)
    now_off_min=None,            # Ignored and calculated again (offset in minutes)
    optimize_ts_str=None,        # Optimization Timestamp String (ts), for (regression) testing/debugging, typically this will be None and the Current (HA) Timestamp will be used
    optimize_off_min=None,       # Optimization Timestamp Timezone Offset in Minutes
    earlier_message=None,        # An earlier error occurred (e.g. in HBC Task), the service is only called to report the error to the user interface

    battery=None,                # Battery Parameters (dict)
    solar=None,                  # Solar Parameters (dict)
    ev=None,                     # Future
    heat_pump=None,              # Future
    boiler=None,                 # Future

    house_energy_forecast=None,  # Simple House Energy Usage Forecast Array with list of usage values per step (per hour or per 15 minutes)
    market_prices=None,          # Simple Grid Market Prices (€/kWh) as a list of prices per step (per hour or per 15 minutes), optional and not used in calculations
    import_prices=None,          # Simple Grid Import Prices (€/kWh) as a list of prices per step (per hour or per 15 minutes)
    export_prices=None,          # Simple Grid Export Prices (€/kWh) as a list of prices per step (per hour or per 15 minutes)
    source_price_data=None,      # Source Price Data (e.g. €/kWh or cents/kWh or €/kWh), A Dictionary with timestamps and prices (per hour or per 15 minutes), alternative when import and export prices are not available, can be HBC Price Data or Provider Price Data

    helios_config=None,          # Helios Configuration (allows certain parameters to be user specific, e.g. Price Provider Profiles and Defaults but also Home Assistant Entities which are not applicable in the Optimizer (see the Helios Services))

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
        task.unique("helios_optimizer_service_lock", kill_me=True)  # This will kill this new instance (of the helios_optimizer_service_lock) immediately when another instance of the service is already running
#       log.error(f"Steps 2 = {steps}")
#       log.error(f"Net metering enabled2={net_metering_enabled}")

        service_error_message = None
        service_begin_ts, service_computed_ts, service_end_ts = None, None, None
        calc_code, calc_result, total_fun_cost = 0, None, None # calc_code is changed to RC_SUCCESS below
        export_folder = export_folder if export_folder else HELIOS_EXPORT # Make sure the input/output folder is filled (with default when None specified)

        # Check if "Allow all imports?" is enabled in the PyScript Configuration:
        if IMPORTS_FAILED_SERV: # Report the import error that occured at the top of the helios_services.py (and/or in helios_common.py)
            raise ImportError(IMPORTS_FAILED_MSG)

        service_begin_ts = datetime.now() 
        calc_code = RC_SUCCESS # Default to success, will be changed if an exception occurs
        log.info(f"{HELIOS_SERVICE_NAME}: Started at {service_begin_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

        # Check if "Access Hass as a global variable?" is enabled in the PyScript Configuration:
        if HASS_NO_ACCESS_SERV: # Report the hass access error that occured at the top of the helios_services.py 
            raise NameError(HASS_NO_ACCESS_MSG)

        # Get Now Information from Home Assistant Datetime Utility (or from the regular Datetime when Datetime Utility is not available or fails):
        now_ts, now_tz, now_off_min  = ha_now_info() # Get Now, Timezone Info and Offset in Minutes from Home Assistant Datetime Utility 
        now_ts =  now_ts.replace(tzinfo=None) # Use internally a naive (no timezone info) timestamp (from HA when available) for lookups in price arrays
        
        battery_info = battery if battery else {}
        solar_info   = solar   if solar   else {}

        # Initialize the Helios Optimizer Entities (executed only once until new entities are added in the next release)
#       helios_optimizer_init() # MOVED to helios_optimizer_hbc_task

        # Home Assistant refuses to pass all attributes of an entity as a dictionary to the service (from the automation), instead it converts it to a json structure
        # Warning: The source price data is retrieved from HA when a source_price_sensor is specified and REPLACES the source_price_data that was sent as an argument
        # REMARK: Only used by the HA Helios Automation not by the new Helios HBC Automation Service !!!!! This data retrieval will become obsolete soon (when the automation is no longer used)
        # NO LONGER NEEDED SINCE HBC_TASK also receives the source_price_data from the entity (was needed for the home assistant automation)
#       if (source_price_data == None) and source_price_sensor and state.exist(source_price_sensor): # Source Price Id specified and the entity exists in Home Assistant, retrieve the attributes of the entity as a dictionary
#           source_price_data2 = state.getattr(source_price_sensor) # Get the attributes of the source price entity as a dictionary (this is a Home Assistant specific function, not available in Visual Studio)       
    #       source_price_type1 = type(source_price_data)
    #       source_price_type2 = type(source_price_data2)
    #       await async_write_message('test.log', f"Testing to write a file with steps={steps}, size={step_size}, start={start_step}, soc={battery_info.get('soc_start_pct', None)}, solar_info='{solar_info.get('mode', 'unknown')}', price size={price_size}, source price id={source_price_sensor}, type={source_price_type1}, type2={source_price_type2}")
    #       await async_write_message('test.log', f"source price data={source_price_data}")
    #       await async_write_message('test.log', f"source price data={source_price_data2}")
#           source_price_data = source_price_data2

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

            "house_daily_usage_kwh": house_daily_usage_kwh, # Optional House Daily Usage in kWh as a total value
            "house_daily_distr"    : house_daily_distr,     # Optional House Daily Distribution of the House Usage over the Day

            "main_provider"        : main_provider,         # Main Provider Key (used to retrieve the provider profile to calculate the Import/Export Prices from the Source Price Data)
            "price_type"           : price_type,            # Price Types are Market, Import or Export
            "source_provider"      : source_provider,       # Optional Source (Energy) Provider (Only applicable when the Price Provider is not the Original Source for the Price Data) 
            "target_provider"      : target_provider,       # Optional Target (Energy) Provider (Only applicable when the Price Provider is not the Target for the Price Data) 
            "source_price_sensor"  : source_price_sensor,   # Source Price Sensor (Entity ID) (info only since the service already retrieved the related source price data)
            "net_metering_enabled" : net_metering_enabled,  # Optional Net Metering Enabled - Salderingsregeling Enabled (only for 2026, includes Energy Tax in Export Price)

            "max_time"             : max_time,
            "max_iterations"       : max_iterations,
            "insight"              : insight,
            "write_files"          : write_files,     # Writing Files, Info only (used in the service but not by the calculator, not applicable to VS Main during testing)
            "export_folder"        : export_folder,   # Input and Output Folder, Info only (used in the service but not by the calculator)

            "now_ts"               : now_ts,          # Naive Datetime for Now (from Home Assistant when available, especially important in container environments)
            "now_tz"               : now_tz,          # Timezone Used for the Naive Datetime Now
            "now_off_min"          : now_off_min,     # Offset in Minutes of the Timezone Used for the Naive Datetime Now
            "optimize_ts_str"      : optimize_ts_str, # Optimize Datetime String (for (regression) testing only)
            "optimize_off_min"     : optimize_off_min if optimize_off_min else 0, # Offset in minutes to UTC for the Timezone of the Optimize Timestamp

            "battery"              : battery,               # Battery Parameters (dict): Battery Enabled, Capacity, SOC%-s (Start, Target, Min, Max), Max Charge/Discharge Power, Charge/Discharge Efficiency, Charge/Discharge Cost 
            "solar"                : solar,                 # Solar Parameters (dict): Solar Enabled, Solar Mode, Solar Energy Forecast in kWh per step
            "ev"                   : ev,                    # Electric Vehicle Parameters (dict) - Future
            "heat_pump"            : heat_pump,             # Heat Pump Parameters (dict)        - Future
            "boiler"               : boiler,                # Boiler Parameters (dict)           - Future

            "house_energy_forecast": house_energy_forecast, # Simple House Usage Energy Forecast Array in kWh per step
            "market_prices"        : market_prices,         # Simple Market Price Array in euro per step, optional and not used in calculations
            "import_prices"        : import_prices,         # Simple Import Price Array in euro per step
            "export_prices"        : export_prices,         # Simple Export Price Array in euro per step
            "source_price_data"    : source_price_data,     # Source Price Data, Dictionary with Price Info (alternative to Simple Import/Export Price Arrays)

            "helios_config"        : helios_config,         # Helios Configuration (allows certain parameters to be user specific, e.g. Price Provider Profiles and Defaults but also Home Assistant Entities which are not applicable in the Optimizer (see the Helios Services))
        }

        # WRITE INPUT PARAMETERS FILE: 
        # JR2026-11-27: First write the input file before raising an error for invalid keys, disabled model or earlier (error) message
        if write_files: # Write the input parameters to a JSON file for debugging and regression testing purposes
            adapted_params = optimizer_params if optimize_ts_str else {**optimizer_params, "optimize_ts_str": datetime_isoformat(now_ts, timespec="seconds"), "optimize_off_min": now_off_min} # Replace in the parameters the optimizer timestamp with now in isoformat when no timestamp provided
            await async_write_dict_to_json_file(HELIOS_PARAMS_FNAME, adapted_params, folder=export_folder) # Write the input parameters to a JSON file for debugging and regression testing purposes

        # CHECK on Unexpected arguments parameters (all supported keyword arguments have a default value and are optional):
        if kwargs: # Unexpected keyword argument(s) received?
            unknown_keys = list(kwargs.keys())
            raise TypeError(f"Unexpected keyword argument(s) received by helios_optimizer_service(): {', '.join(unknown_keys)}")

        # Handle disabled Helios Optimizer:
        if (steps == 0): # Is the Model disabled?
            raise ValueError(f"The Optimization Model is DISABLED with a horizon of zero days!")

        # Handle Earlier Errors (error is displayed on the Helios Dashboard but the Optimizer will not be called)
        if earlier_message: # An error occured earlier in helios_optimizer_hbc_task()
            raise ValueError(earlier_message)

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

    # HANDLE SERVICE EXCEPTIONS 
    # Remark: Exceptions are more likely to be handled by the Exception handler of the helios_optimizer_calc_plan:
    # Exceptions in helios_optimizer_hbc_task() are handled here aswell using the earlier_message (no error_stack will be available)
    except Exception as e:
        error_stack = None
        if not (IMPORTS_FAILED_SERV or HASS_NO_ACCESS_SERV) : # Imports and Hass access are required for the following info
            if earlier_message: # Earlier Exception/Error in helios_optimizer_hbc_task()?
                error_stack = None # Trace from helios_service() is not applicable
                calc_code = RC_TASK_EXCEPTION
                calc_result = "Task Exception"
                service_error_message = earlier_message
            else:
                error_stack = traceback.format_exc() # Retrieve the python error stack from traceback
                calc_code = RC_SERVICE_EXCEPTION
                calc_result = "Service Exception" if steps > 0 else "Service Disabled"
                service_error_message = repr(e) # Only for a service exception we use the message from the current exception
            helios_version = HELIOS_VERSION
            scipy_version  = SCIPY_VERSION
        
        else: # Import(s) Failed or No Hass Access: PyScript configuration must be adapted by the user!
            error_stack = None
            calc_code      = 10 # RC_PYSCRIPT_FAILED is not available when imports have failed (since it is defined in import helios_common.py)
            if IMPORTS_FAILED_SERV: # PyScript Imports Failed
                calc_result = "Import(s) Failed"
            else: # HASS_NO_ACCESS_SERV: # HASS not accessible
                calc_result = "HASS not accessible"
            service_error_message = str(e) # Only need the exception message 
            helios_version = "Unknown"
            scipy_version  = "Unknown"

        log.error(f"[{HELIOS_SERVICE_NAME}] Exception: {service_error_message}")
        if error_stack: # Error stack only applicable for local errors
            log.error(f"Full Exception Message for [{HELIOS_SERVICE_NAME}]:")
            log.error(error_stack + "\n")

        payload = { # Construct a simple version of the payload for the service exception
            "success"                 : False, 
            "calc_code"               : calc_code, 
            "calc_result"             : calc_result, 
            "version"                 : helios_version,
            "scipy"                   : scipy_version,

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
            "solver_message"          : service_error_message, # Calculation did not complete (no solver message available, an error message will be returned instead)
            "error_trace"             : error_stack,   # exception stack, for debugging only
        } 
  
    # SET Home Assistant STATE for the Helios Optimizer Energy Plan (with the payload in the attributes):
    # REMARK: This section is executed when imports failed and will use in this case a simple version of the ha_* functions (as defined above) since the import of helios_hass.py did not happen
    try:    
        # Store the optimization result in the Home Assistant Helios Optimizer Energy Plan Entity and its attributes 
        if ha_entity_exist(HELIOS_ENERGY_PLAN) and not ha_is_unavailable(HELIOS_ENERGY_PLAN):
            # Entity already exist and has a value: Status and Attributes can be updated
            ha_set_state(
                HELIOS_ENERGY_PLAN,
                value=total_fun_cost if total_fun_cost else 0, # Use the Total Cost from the payload as the main value of the entity, so it can be used in automations and templates and graphs
                friendly_name=HELIOS_PLAN_NAME,
                unit_of_measurement="€", # Use the Euro sign as the unit of measurement for the Total Cost
                min=-1000, max=1000, step=0.01, initial=None, # Use a reasonable range for the Total Cost (in Euro) and a step size of 1 cent and no initial value (since the value is set by the optimizer)
                new_attributes=payload
            )

            # The Helios Optimizer Energy Plan Entity is now updated with the new payload (two fields from this payload also have their own Home Assistant Entities)
            # The HBC Sub Strategy and Net Battery Power are also updated in their respective entities for use in the Home Assistant Node-Red Flow for the Helios Strategy:
            current = payload.get('current', None)
            if ha_entity_exist(HELIOS_BAT_STRAT): # The Helios Battery Strategy Entity and payload['current'] must exist?
                helios_battery_strategy = current.get('battery_strategy', 'unknown') if current else 'unknown' # Get the Helios Battery Strategy from the payload (use  HELIOS_STR_UNK='Unknown'->'unknown' when not available)
                ha_set_state(HELIOS_BAT_STRAT, value=helios_battery_strategy) # Set the Helios Battery Strategy in the HA Entity
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_BAT_STRAT} does not exist!")    

            if ha_entity_exist(HELIOS_HBC_SUB_STRAT): # The HBC Sub Strategy Entity and payload['current'] must exist?
                hbc_sub_strategy = current.get('hbc_sub_strategy', 'unknown') if current else 'unknown' # Get the HBC Sub Strategy from the payload (use HBC_SS_UNK='Unknown'->'unknown' when not available)
                ha_set_state(HELIOS_HBC_SUB_STRAT, value=hbc_sub_strategy) # Set the HBC Sub Strategy in the HA Entity
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_HBC_SUB_STRAT} does not exist!")

            if ha_entity_exist(HELIOS_HBC_NET_POWER): # The HBC Net Battery Power Entity and payload['current'] must exist 
                hbc_net_battery_power = current.get('battery_net_power_w', None) if current else None # Get the Net Battery Power in Watt from the payload
                ha_set_int(HELIOS_HBC_NET_POWER, value=int(hbc_net_battery_power) if hbc_net_battery_power != None else None) # Set the Net Battery Power for HBC (Charge is Positive, Discharge is Negative) in Watt
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_HBC_NET_POWER} does not exist!")    

            if state.exist(HELIOS_INPUT_STEPS): # The Helios Optimizer Steps Entity must exist
                steps = payload.get('steps', None) if payload else None # Get the Number of Steps used by the Optimizer
                ha_set_int(HELIOS_INPUT_STEPS, value=int(steps) if steps != None else None) # Set the Steps field (since it is now derived from horizon and step size)
            else: log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_INPUT_STEPS} does not exist!")    

        else: # The entity must already exist before we write to it (since otherwise a pyscript entity would be created)!
            log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_ENERGY_PLAN} does not exist or is unavailable!")    

    #   task.sleep(1)
    #   task.sleep(0.001)
        if service_begin_ts:
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
        if (calc_code == 0): # Only set the calc_code, calc_result and solver_message when they are not already set by previous errors (calc_code = RC_SUCCESS)
            payload['calc_code']      = RC_SETSTATE_EXCEPTION  # adapt the calc_code to indicate that the state.set failed after a successful calculation
            payload['calc_result']    = "State Set Exception" 
            payload['solver_message'] = error_message

    # WRITE OUTPUT (RESULT) FILES
    try:
        if write_files and not IMPORTS_FAILED_SERV: # Write the input parameters to a JSON file for debugging and regression testing purposes
            # WRITE PAYLOAD FILE (All Results) to JSON:
            char_count = await async_write_dict_to_json_file(HELIOS_PAYLOAD_FNAME, payload, folder=export_folder) # Write the output to a JSON file for debugging and regression testing purposes
    
            # WRITE ENERGY PLAN FILE to CVS File (Only the Optimized Energy Plan Arrays as a Table):
            headers, row_list = convert_dictoflists_to_listofdicts(payload.get('plan', {}))
            if len(row_list) > 0: # Anything to write?
                line_count = await async_write_csv_file(HELIOS_TABLE_FNAME, row_list=row_list, headers=headers, row_key=None, folder=export_folder)
    
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}] Exception in Write Output Files: {error_message}")

    return payload # Return the payload to the Home Assistant Automation in the return_response (see the automation trace for details)

# Home Assistant Service to Start the Helios Automation and Show the Running Status in the UI
# This service is called by the Home Assistant Button in the UI and triggers the Helios Automation to calculate the optimized energy plan
# All the input parameters for the optimization are provided by the Home Assistant Helios Automation, so this service does not need any input parameters
# Warning: This service cannot be started in Visual Studio since it has no access to the HA Automation!
@service
def helios_optimizer_automation():
#   state.delete(HELIOS_ENERGY_PLAN) # Removes the Optimized Energy Plan (disable the automation.trigger since otherwise a new plan is created as a pyscript entity)

    # 1. Turn on the helios optimizer running status (switches the button to orange)
    ha_set_state(HELIOS_RUNNING, "on", friendly_name=HELIOS_RUNNING_NAME)
    
    # 2. Start/Trigger the HA Automation (which also provides the input parameters for the above service)
    automation.trigger(entity_id=HELIOS_AUTOMATION)
    
    # 3. Wait an extra 1 second otherwise the color change of the start button will not be visible if the optimization is very fast (e.g. less than 200 millisecond)
    task.sleep(1)
    
    # 4. Turn off the helios optimizer running status (switches the button back to green)
    ha_set_state(HELIOS_RUNNING, "off", friendly_name=HELIOS_RUNNING_NAME)

# Helios Optimizer HBC Automation is triggered every 15 minutes and at startup of Home Assistant and when solar forecast is updated
# The Task starts on purpose at 1, 16, 31, 46 since it is a longer running task with LP calculations and should not be started at the same time as other tasks (e.g. the helios_forecast.py which retrieves the new solar forecast every whole hour)
# The service retrieves the input parameters from the Helios Dashboard, Helios Templates and HBC Entities and calls the Helios Optimizer Service to calculate the optimized energy plan
# The service can also be called from the Helios Optimizer Dashboard using the "Start Helios Optimizer Task"
@time_trigger("startup") # Triggered at startup of Home Assistant (after all other pyscripts have completed, e.g. helios_forecast.py which retrieves the new forecast at startup)
@time_trigger("cron(1,16,31,46 * * * *)") # Triggered every 15 minutes at 1, 16, 31 and 46 minutes past the hour (to avoid conflicts with other tasks that run on the whole hour)
@state_trigger(f"{HELIOS_FORECAST_SOLAR_ALT}") # Triggered when the alternative solar forecast (retrieved via a REST API is updated 
@service
async def helios_optimizer_hbc_task(optimize_ts_str: str = None, optimize_off_min: int = 120, trigger_type=None, trigger_time=None):
    task.unique("helios_optimizer_task_lock", kill_me=True)  # This will kill this new instance (of the helios_optimizer_task_lock) immediately when another instance of the task is already running
#   task.unique("helios_optimizer_task_lock", kill_me=False) # This will not kill this instance (of the helios_optimizer_task_lock) but will kill another (earlier) instance of the task that is still running, use this when using long sleeps in the optimizer

    if trigger_time == "startup": # Triggered by startup 
        log.warning(f"[{HELIOS_SERVICE_NAME}]-HBC-Task: Trigger Time={trigger_time}: Waiting 10 seconds ...")
        task.sleep(10) # Wait 10 seconds (this should be sufficient for the other pyscripts to complete, especially helios_forecast.py which retrieves the new forecast at startup)
    log.info(f"[{HELIOS_SERVICE_NAME}]-HBC-Task: Started after trigger type={trigger_type} at time={trigger_time}")

    # 1. Turn on the helios optimizer running status (switches the button to orange)
#   ha_set_bool(HELIOS_RUNNING, True, existing_only = True) # Set the Helios Running entity On (only when it exists)
    state.set  (HELIOS_RUNNING, 'on')                       # Set the Helios Running entity On 

    # Initialize all parameters (making a call to the service possible without an exception, independent of availability of entities):
    task_error_message = None # No Errors yet
    steps, step_size, start_step, price_size, house_size, solar_size = None, None, None, None, None, None
    house_daily_usage_kwh, house_daily_distr, max_grid_import_kw, max_grid_export_kw = None, None, None, None
    source_price_sensor, source_price_data, main_provider, price_type, source_provider, target_provider, net_metering_enabled = None, None, None, None, None, None, None
    solar_config, battery_config, helios_config = None, None, None

    if IMPORTS_FAILED_SERV:
        task_error_message = IMPORTS_FAILED_MSG # Further handling in helios_optimizer_service()
    
    else: # Import of other modules did not fail (processing can continue)
        # Load the Helios Configuration which currently only overrides some of the Price Providers and Price Defaults and the Strategy Mapping
        try:
            helios_config = await async_load_config(HELIOS_CONFIG_FNAME, HELIOS_FOLDER, raise_error=True) # Asynchronous load of the Helios Configuration File (raises an exception when json parsing fails and returns None when file does not exist)

            # Initialize the Helios Optimizer Entities (executed only once until new entities are added in the next release)
            helios_optimizer_init()

            payload = None
            raise_error = True # For all input parameters: An exception is thrown when an entity does not exist or contains an invalid format (e.g. not float) 
            # 2a. Retrieve the input parameters for the Helios Optimizer from the Helios Dashboard
            days                  = ha_get_int  (HELIOS_INPUT_HORIZON     , default_value=None , raise_error=raise_error) 
    #       steps                 = ha_get_int  (HELIOS_INPUT_STEPS       , default_value=None , raise_error=raise_error) 
            step_size             = ha_get_int  (HELIOS_INPUT_STEP_SIZE   , default_value=None , raise_error=raise_error) 
            start_step            = ha_get_int  (HELIOS_INPUT_START_STEP  , default_value=None , raise_error=raise_error) 
            steps =  days * int(24 * 60 / step_size) if (days and step_size and (step_size > 0)) else 0 # Calculate the number of steps from the number of days and the step size (when both are available)
    #       log.error(f"The values of steps {steps} size {step_size} start {start_step} have been retrieved!")

            max_grid_import_kw    = ha_get_float(HELIOS_INPUT_MAX_GRID_IMP, default_value=None , raise_error=raise_error) 
            max_grid_export_kw    = ha_get_float(HELIOS_INPUT_MAX_GRID_EXP, default_value=None , raise_error=raise_error) 
            house_daily_usage_kwh = ha_get_float(HELIOS_INPUT_HOUSE_USAGE , default_value=None , raise_error=raise_error) 
            house_daily_distr     = ha_get_text (HELIOS_INPUT_HOUSE_DISTR , default_value=None , raise_error=raise_error) 
            net_metering_enabled  = ha_get_bool (HELIOS_INPUT_NET_METERING, default_value=False, raise_error=False) # Net Metering Enabled (Salderingsregeling) is optional and defaults to False when not specified, since it is only applicable for 2026 
    #       log.error(f"Net metering enabled1={net_metering_enabled}")

            # 2b. Check that house daily usage distribution is not an empty string (replace by None if so):
            house_size = None
            if isinstance(house_daily_distr, str) and (house_daily_distr.strip(' ') == ''): # Nothing specified (empty string) for the house usage distribution
                house_daily_distr = None # Disable the distribution (house daily usage will be divided evenly over the day)
            else:
                # Do a dummy generate of the forecast to determine the house forecast step size (but just send the house daily distribution!)
                house_energy_forecast = generate_forecast_for_distribution(house_daily_usage_kwh, house_daily_distr, expected_sizes=[24,48,96], name="house_daily_distr", decimals=ROUND_ENERGY_KWH2, raise_error=False)
                if len(house_energy_forecast) > 0:
                    house_size = int(24 * MINUTES_PER_HOUR / len(house_energy_forecast)) # Daily forecast length determines number of steps per day for the house daily usage distribution array

            # 2c. Determine the Solar Settings:
            solar_forecast_sensor, solar_energy_forecast, solar_size = None, None, None
            solar_mode    = ha_get_state(HELIOS_INPUT_SOLAR_MODE, default_value=None, raise_error=raise_error) 
            solar_enabled = solar_mode != "disabled" # SOLAR_DIS (cannot use this constant when helios_common.py is not available due to import problems)
            if (solar_enabled): # Solar Mode Enabled (not Disabled)?
                solar_forecast_srce = ha_get_text (HELIOS_INPUT_SOLAR_SOURCE, default_value=None, raise_error=raise_error) 
                if solar_forecast_srce == FORECAST_SC_INTEGR: # Solcast REST api?
                    solar_forecast_sensor = HELIOS_SOLCAST # Sensor filled with template after retrieval via Solcast REST api
                elif solar_forecast_srce == FORECAST_FS_INTEGR: # Forecast.Solar Integration
                    solar_forecast_sensor = HELIOS_FORECAST_SOLAR # Sensor filled with Pyscript (helios_forecast.py) after retrieval via service of Forecast.Solar Integration
                elif solar_forecast_srce == FORECAST_FS_REST: # Forecast.Solar REST api?
                    solar_forecast_sensor = HELIOS_FORECAST_SOLAR_ALT # Sensor filled with template after retrieval via Forecast.Solar REST api 
            
                if solar_forecast_sensor: # Solar Forecast Sensor available
                    if ha_entity_exist(solar_forecast_sensor):
                        solar_forecast_result = ha_get_attr(solar_forecast_sensor, 'result', None) # Get the result attribute for the sensor
        #               log.error(f"Solar Forecast {solar_forecast_result}")
                        if solar_forecast_result and len(solar_forecast_result) > 0: # Result attribute available and is not empty?
                            solar_energy_forecast = solar_forecast_result.get('period_kwh', None)
                            solar_size            = solar_forecast_result.get('interval'  , None) # step size for the solar forecast
                        else:
                            forecast_message = ha_get_attr(solar_forecast_sensor, 'message', None)
                            raise ValueError(forecast_message if forecast_message else "Solar is Enabled but a Solar Forecast Array is not available")
                    else:
                        raise ValueError("Solar is Enabled but the Solar Forecast Sensor does not exist")
                else:
                    raise ValueError("Solar is Enabled but the Solar Forecast Sensor is not defined")

    #           solar_energy_forecast = None # Testing what happens with an empty forecast array (same as when helios_forecast.py fails to write to the forecast entity)
                solar_config = {
                    "enabled": solar_enabled, "mode": solar_mode, "energy_forecast": solar_energy_forecast, "forecast_source": solar_forecast_srce
                }
#               log.debug(f"Solar Config: {solar_config}")
            else:
                solar_config = None

            # 2d. Determine the Battery Settings:
            battery_enabled = ha_get_bool(HELIOS_INPUT_BAT_ENABLED, default_value=False, raise_error=raise_error) 
            if battery_enabled: # Battery Enabled?
                capacity_kwh           = ha_get_float(HELIOS_TEMPL_HBC_MAX_CAP , default_value=None, raise_error=raise_error)
                soc_start_pct          = ha_get_float(HELIOS_TEMPL_HBC_TOT_SOC , default_value=None, raise_error=raise_error)
                soc_target_pct         = ha_get_float(HELIOS_INPUT_SOC_TARGET  , default_value=None, raise_error=raise_error)
                soc_min_pct            = ha_get_float(HELIOS_INPUT_SOC_MIN     , default_value=None, raise_error=raise_error)
                soc_max_pct            = ha_get_float(HELIOS_INPUT_SOC_MAX     , default_value=None, raise_error=raise_error)
                max_charge_power_kw    = ha_get_float(HELIOS_INPUT_CHARGE_LIMIT, default_value=None, raise_error=raise_error)
                max_discharge_power_kw = ha_get_float(HELIOS_INPUT_DISCH_LIMIT , default_value=None, raise_error=raise_error)
                charge_efficiency      = ha_get_float(HELIOS_INPUT_CHARGE_EFF  , default_value=None, raise_error=raise_error)
                discharge_efficiency   = ha_get_float(HELIOS_INPUT_DISCH_EFF   , default_value=None, raise_error=raise_error)
    #           capacity_kwh, soc_start_pct = 0, "unknown" # Testing templates unavailable
                battery_config = {
                    "enabled": battery_enabled,
                    "capacity_kwh": capacity_kwh, "soc_start_pct": soc_start_pct,
                    "soc_target_pct": soc_target_pct, "soc_min_pct": soc_min_pct, "soc_max_pct": soc_max_pct,
                    "max_charge_power_kw": max_charge_power_kw, "max_discharge_power_kw": max_discharge_power_kw, 
                    "charge_efficiency": charge_efficiency, "discharge_efficiency": discharge_efficiency,
                    "charge_cost": None, "discharge_cost": None, # Using the default charge cost (when None specified)
                }
            else:
                battery_config = None

            # 2e. Determine Source Price Data by reading the HBC Energy Price Data Entity:
            price_type      = ha_get_state(HELIOS_INPUT_PRICE_TYPE , default_value=None, raise_error=raise_error) # Get the Source Price Type ('market', 'import' or 'export')
            source_provider = ha_get_state(HELIOS_INPUT_SOURCE_PROV, default_value=None, raise_error=raise_error) # Get the Data   Provider of the Price (Tariff) Data
            target_provider = ha_get_state(HELIOS_INPUT_TARGET_PROV, default_value=None, raise_error=raise_error) # Get the Energy Provider (Contract)
            source_price_sensor = HBC_ENERGY_PRICE_DATA
            if ha_entity_exist(source_price_sensor): # HBC Price Data exists in Home Assistant, retrieve the attributes of the entity as a dictionary
                hbc_price_data_source = ha_get_state(HBC_PRICE_DATA_SOURCE  , default_value=None, raise_error=raise_error) # Get the Source Provider used in HBC to retrieve the Source Price Data
                source_price_data     = ha_get_all_attr(source_price_sensor) # Get the attributes of the Source Price Data Entity as a dictionary 

                # Convert All 'Grid Clock XX' Price Data Sources to 'Grid Clock'
                if (hbc_price_data_source.startswith("Grid Clock")): # HBC Price Source (provider) Key starts with Grid Clock?
                    hbc_price_data_source = 'Grid Clock' # Convert all Grid Clock countries to the General Grid Clock Provider Profile (no taxes or markups involved and all are market prices without vat)

                # User already has selected the Data and/or Energy Provider in HBC as the Price (Tariff) Data Source
                # Note: HBC Data Source are not exactly the same as the Helios Profile keys but a Conversion Table is used when the (HBC) profile key is not found in the Helios Profiles
                if source_provider == HBC_DATA_SOURCE: source_provider = hbc_price_data_source # Use the HBC Data Source as the Source (Data  ) Provider in Helios
                if target_provider == HBC_DATA_SOURCE: target_provider = hbc_price_data_source # Use the HBC Data Source as the Target (Energy) Provider in Helios

                # Determine the steps size (in minutes) for the Price Data (convert HBC Datapoints per hour to step size: 60 / datapoints_per_hour)
                try: 
                    hbc_datapoints_per_hour = convert_int(source_price_data.get('datapoints_per_hour', None), "HBC Price Data: Datapoints per Hour", default_int = None, allow_none=True)
                except:
                    hbc_datapoints_per_hour = None
                price_size = int(round(60 / hbc_datapoints_per_hour, 0)) if hbc_datapoints_per_hour else None
            else:
                source_price_data, price_size = {}, None # Optimizer will fail without price data, JR2026-10-28 JR: replace None by {}, optimizer will report that no price info available

        except Exception as e:
            # An error occured while reading the input parameters
            task_error_message = str(e)
            log.error(f"[{HELIOS_TASK_NAME}] Exception: {task_error_message}")
            error_stack = traceback.format_exc() # Retrieve the python error stack from traceback
#           log.error(f"Full Exception Message for [{HELIOS_TASK_NAME}]:")
#           log.error(error_stack + "\n")

    # Whatever happened we will call the Helios Optimizer Service 
    # Note: An earlier error message will be passed so the user interface can be updated in helios optimizer service (in this case no further action will be taken by the service)
    try:
        # 3. Call the HA Service with the input parameters
        payload = await helios_optimizer_service(
            steps=steps, step_size=step_size, start_step=start_step, price_size=price_size, house_size=house_size, solar_size=solar_size,
            house_daily_usage_kwh=house_daily_usage_kwh, house_daily_distr=house_daily_distr,
            max_grid_import_kw=max_grid_import_kw, max_grid_export_kw=max_grid_export_kw,
            source_price_sensor=source_price_sensor, main_provider='hbc_marks', price_type=price_type, source_provider=source_provider, target_provider=target_provider, # Price configuration info
            source_price_data=source_price_data, # HBC Price Data (Provider is HBC)
            net_metering_enabled=net_metering_enabled, # Net Metering Enabled (True/False) 
            optimize_ts_str=optimize_ts_str, optimize_off_min=optimize_off_min, # Use only for simulation purposes (Helios Optimizer service will add the current time and offset)
            earlier_message=task_error_message, # Earlier Error Message (no actual calculation will be done by the helios optimizer service when an error message is specified!)
            solar=solar_config, 
            battery=battery_config,
            helios_config=helios_config,
        )

    except Exception as e:
        # An error occured in calling the Helios Optimizer Service
        # The output is currently not applied to the Helios Output entity (and not visible on the user interface)
        # A Notification will be sent to the HA Persistent Notification Framework
        error_message = e
        log.error(f"[{HELIOS_TASK_NAME}]-Service] Exception: {error_message}")
        if not IMPORTS_FAILED_SERV:
            error_stack = traceback.format_exc() # Retrieve the python error stack from traceback
#           log.error(f"Full Exception Message for [{HELIOS_SERVICE_NAME}]:")
#           log.error(error_stack)        
        else:
            error_stack = None
        persistent_notification.create(title='Helios Optimizer HBC Task Failed',
            message=f"{error_message}", notification_id="helios_optimizer_task"
        )
        payload = {"success": False, "automation_message": error_message, "error_trace": error_stack} # Simplified payload for errors

    # 4. Wait an extra 1 second otherwise the color change of the start button will not be visible if the optimization is very fast (e.g. less than 200 millisecond)
    task.sleep(1)
    
    # 5. Turn off the helios optimizer running status (switches the button back to green)
#   ha_set_bool(HELIOS_RUNNING, False, existing_only = True)
    state.set  (HELIOS_RUNNING, 'off')

    return payload

def helios_optimizer_init():
    """
    Helios Optimizer Initialisation of (new) Home Assistant Helios Optimizer Entities.
    Depending on the Helios Optimizer Version the HA Entities will be initialized.
    Typically Entities already initialized in an earlier version will not be initialized again.
    """ 
    init_count = -2 # Initialize the count of initialized entities to -2 (initialization not possible)
    if ha_entity_exist(HELIOS_INPUT_VERSION) and not ha_is_unavailable(HELIOS_INPUT_VERSION): # Does the HA Helios Optimizer Version Entity Exist and not Unavailable?
        init_count = -1 # Initialize the count of initialized entities to -1 (initialization not needed)
        previous_version_tuple = parse_version(ha_get_text(HELIOS_INPUT_VERSION, "0.0.0"))
        current_version_tuple  = parse_version(HELIOS_VERSION)
        if (current_version_tuple > previous_version_tuple): # Helios Current Version is higher than the Previous Version (Warning: 0.9.1a and 0.9.1b are not different versions, version will not be updated!)
            init_count = 0 # Initialize the count of initialized entities to 0 (initialization needed)
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
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_CHARGE_LIMIT, hbc_max_charge    / 1000) # Convert from W to kW
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_DISCH_LIMIT , hbc_max_discharge / 1000) # Convert from W to kW 
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_CHARGE_EFF  , BAT_EFF   )
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_DISCH_EFF   , BAT_EFF   )

                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOLAR_MODE  , SOLAR_MODE) 

            if (previous_version_tuple < (0,9,3)): # Below v0.9.3 initialize the solar forecast Resource
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOLAR_SOURCE, FORECAST_FS_INTEGR)

            if (previous_version_tuple < (0,9,4)): # Below v0.9.4 initialize the price data and Horizon
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_PRICE_TYPE  , PT_IMPORT)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_SOURCE_PROV , HBC_DATA_SOURCE)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_TARGET_PROV , HBC_DATA_SOURCE)
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_HORIZON     , DEFAULT_HORIZON)

            if (previous_version_tuple < (0,9,5)): # Below v0.9.5 initialize the Net Metering 
                init_count += helios_optimizer_init_entity(HELIOS_INPUT_NET_METERING, False)

            # Update the Helios Optimizer Version (above initializations will not happen again afterwards until the version is increased):
            ha_set_text(HELIOS_INPUT_VERSION, HELIOS_VERSION) # Store the latest version in HA Entity 

    if (init_count != 0): # Initialization of Entities was needed or not possible
        try: # Create a Home Assistant Persistent Notification
            if (init_count <= -2): # Version Entity does not exist
                title   = "Helios Optimizer Initialization Failed"
                message = f"Helios Optimizer version entity is not available and no entities are initialized for version '{HELIOS_VERSION}'."
            elif (init_count > 0):
                title   = "Helios Optimizer Initialized"
                message = f"Helios Optimizer has been upgraded to version '{HELIOS_VERSION}'."
                message += f"\nHelios Optimizer Initialized {init_count} Entities."
            else: # (init_count == -1): # Version Entity exists but no initialization needed
                title   = "Helios Optimizer Initialization Not Needed"
                message = f"Helios Optimizer is already initialized with version '{HELIOS_VERSION}'."
                title = None # Disable the notification when no initialization was needed (otherwise it will be shown for every run)

            if title: # Only when entities are initialized or version entity does not exist
                persistent_notification.create( # Only in HA!
                    title=title,
                    message=message,
                    notification_id="helios_optimizer_init"
                )
        except: # Not Possible outside Home Assistant!
            if title: log.warning(f"{title}: {message}")

def helios_optimizer_init_entity(entity_id: str, value: any, raise_error = True) -> int:
    """Initialize an Entity State with the (default) value (Integer, Float, Boolean or String)."""
    entity_count = 0
    if ha_entity_exist(entity_id) and not ha_is_unavailable(entity_id):
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
        error_message = f"Helios Optimizer Entity '{entity_id}' does not exist or is unavailable!"
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
    results, message, error_message = {"Entity_id": entity_id, "Attr_Name": attr_name, "State": None, "Attr_Count": None, "message": None}, None, None
    try:
        if (entity_id is None) or (entity_id == ""): # Entity Id not specified?
            entity_id = HELIOS_ENERGY_PLAN # Use the default Helios Optimizer Energy Plan Entity Id

#       value = state.get(entity_id) # Get Entity using State (throws an exception when entity id does not exist)
        if not state.exist(entity_id): # Does the Entity Exist?
            error_message = f"Entity Id '{entity_id}' does not exist!"
        elif IMPORTS_FAILED_SERV:
            error_message = IMPORTS_FAILED_MSG
        elif HASS_NO_ACCESS_SERV: # Report the hass access error that occured at the top of the helios_services.py 
            error_message = HASS_NO_ACCESS_MSG

        else: # Entity exists (so we can retrieve the value and attributes)
#           state_value= state.get(entity_id) # Get Entity using State
#           attributes = state.getattr(entity_id) or {} # Get Entity Attributes using state.getattr (returns a Dictionary or None when entity does not exist, so use {} as default)
#           if state_value is None: # Entity has no value (but can still have attributes, None is not an expected value for Home Assistant)
#               message = f"Entity Id '{entity_id}' is None!"
#           elif not state_value.has_value(): # Entity has no value (unknown or unavailable)!
#               message = f"Entity Id '{entity_id}' has no value!"
#           elif state_value.is_unknown(): # Entity value is unknown!
#               message = f"Entity Id '{entity_id}' is UNKNOWN!"
#           elif state_value.is_unavailable(): # Entity value is unavailable!
#               message = f"Entity Id '{entity_id}' is UNAVAILABLE!"
#           else: # Entity has a value and may have attributes
#               message = f"Entity Id '{entity_id}' has State Value '{state_value}' and has {len(attributes)} attributes."                      

            str_value  = ha_get_state(entity_id) # Get Entity Value as a String using State
            attributes = ha_get_all_attr(entity_id) or {} # Get Entity Attributes using state.getattr (returns a Dictionary or None when entity does not exist, so use {} as default)
            if str_value is None: # Entity has no value (but can still have attributes, None is not an expected value for Home Assistant)
               message = f"Entity Id '{entity_id}' is None!"
            elif not ha_has_value(entity_id): # Warning: This catches but unknown and unavailable already!
                message = f"Entity Id '{entity_id}' has NO Value"
            elif ha_is_unknown(entity_id):
                message = f"Entity Id '{entity_id}' is unknown!"
            elif ha_is_unavailable(entity_id):
                message = f"Entity Id '{entity_id}' is unavailable!"
            elif not ha_has_value_extra(entity_id):
                message = f"Entity Id '{entity_id}' has NO Value or is Blank"
            else: # Entity has a value and may have attributes
                message = f"Entity Id '{entity_id}' has State='{str_value}' and has {len(attributes)} attributes."                      

            results['State'     ] = str(str_value) # Convert the state value to a string (is_unknown, is_unavailable, has_value are not longer possible on a string)
            results['Attr_Count'] = len(attributes)
            results['Message'   ] = message # Set the message (may be replaced later when an error occurs)

            log.info(f"[{HELIOS_SERVICE_NAME}]: Get Entity({entity_id}): '{str_value}'")
#           log.error(f"[{HELIOS_SERVICE_NAME}]: Get Entity-Attrs({entity_id}): {attributes}") # Warning: Can be a lot of data in the log for large attributes
            log.info(f"[{HELIOS_SERVICE_NAME}]: Get Entity-Attrs({entity_id})-Length: {len(attributes)}") # Return the number of attributes for the entity (can be 0 when no attributes exist)           

            if (attr_name != None): # Attribute name specified, retrieve the attribute value
                if attr_name in attributes.keys(): # Does the attribute exist?
                    attr1_value = ha_get_attr(entity_id, attr_name, None)
                    if isinstance(attr1_value, str): # String? (Only print when attribute is a string, not dictionaries or lists)
                        log.info(f"[{HELIOS_SERVICE_NAME}]: Get1 Entity-Attr({entity_id},{attr_name}): '{attr1_value}'")

                    attr2_value = attributes.get(attr_name, 'onbekend2') # Use state.getattr with entity_id and get with attr_name
                    if isinstance(attr1_value, str): # String? (Only print when attribute is a string, not dictionaries or lists)
                        log.info(f"[{HELIOS_SERVICE_NAME}]: Get2 Entity-Attr({entity_id},{attr_name}): '{attr2_value}'")
                
                    attr3_value = state.get(f"{entity_id}.{attr_name}") # Use state.get with entity_id.attr_name
                    if isinstance(attr2_value, str): # String? (Only print when attribute is a string, not dictionaries or lists)
                        log.info(f"[{HELIOS_SERVICE_NAME}]: Get3 Entity-Attr({entity_id},{attr_name}): '{attr3_value}'")

                    message = f"Entity Id '{entity_id}' has State='{str_value}' and Attribute {attr_name}='{attr1_value}'."                      
                    results['Message'] = message # Overwrite the State Value message with a State Value and Attribute Value message
                    results[attr_name] = attr1_value # Return the attribute value (value or dict) as a dictionary with the attribute name as key 
                
                else: # Attribute (or Attribute Path does not exist!
                    error_message = f"Attribute '{attr_name}' for Entity Id '{entity_id}' does NOT exist!"               
                
            else: # No Attribute name specified (return All Attributes)!
                results['attributes'] = attributes # Add the Attributes as a dictionary to the results
   
    except Exception as e:
        error_message = f"Exception for Entity '{entity_id}' with Attribute '{attr_name}': {repr(e)}"

    try: # Create a Home Assistant Persistent Notification
        if error_message is None: # No message yet so built one with the Entity Info (without all attributes)
            title   = "Helios Optimizer Hello World is Ready"
            notification_message = f"Entity '{entity_id}' has State Value '{str_value}' and has {len(attributes)} attributes."
        else: # Error message already exists (error or exception), so use it as the notification message
            title   = "Helios Optimizer Hello World has an Error"
            notification_message = error_message

        persistent_notification.create( # Only in HA and in Mockup!
            title=title,
            message=notification_message,
            notification_id="helios_hello_world"
        )
    except: # Notification not possible outside Home Assistant and without a Mockup Instance!
        log.warning(f"{title}: {message}") # Log the message instead of creating a notification

    if error_message: # An error occurred (entity or attribute does not exist or an exception was thrown)
        log.error(f"[{HELIOS_SERVICE_NAME}-Hello-World] Error: {error_message}")
        results['Message'] = error_message # Replace an existing message with the error message

    return results # Return always a dictionary 
