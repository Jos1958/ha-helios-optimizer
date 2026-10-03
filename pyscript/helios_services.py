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
#   Remark: For a full history see helios_main.py


# Modules used by Home Assistant must be in the "modules" folder of the Home Assistant configuration directory. 
# Modules used by Visual Studio Code must be in the same folder as the Main Python script.
import sys                                    # For sys.path.append() to add the Home Assistant Pyscript folder to the path

#from http import server
#from re   import A 
from io   import TextIOWrapper

# Determine the environment (Visual Studio or Home Assistant):
try: # Assume we are running in Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
    HELIOS_FOLDER  = 'export/'  # Used by Helios Services AND Helios Main (in Visual Studio)
    HELIOS_RESULTS = 'results/' # Only used by Helios Main (in Visual Studio)

    # Do not add the home_assistant_mock.py to the Home Assistant pyscript/helios folder, it is only needed for testing in Visual Studio
    from home_assistant_mock import service, time_trigger, pyscript_compile, log, automation, task, state  # Include HA mock for testing outside of Home Assistant
#   _LOGGER = log # Use the mock log for testing in Visual Studio

except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
    HELIOS_FOLDER = '/config/export/'

    import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
#   _LOGGER  = logging.getLogger(__name__) # Get access to the HomeAssistant Logger in standard python functions (not needed in helios_services since access to HA log is available)
    if "/config/pyscript" not in sys.path: # Already in the search path for pure python modules in Home Assistant? 
        sys.path.append("/config/pyscript") # Home Assistant Pyscript folder, Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)
#   pass  # In Home Assistant no mock is needed since service/state/log etc already exist globally!

from helios_python.helios_optimizer import * # Import the Helios Pure Python Calculate Plan function and other Optimize Energy functions

# Constant values for the Home Assistant Entities and Automations used by the Helios Service
HELIOS_OPTIM_PLAN    = 'input_number.helios_optimizer_energy_plan' # Helios Result with Status, Current and Plan in the attributes
HELIOS_OPTIM_PLAN_OLD= 'pyscript.helios_energy_plan'               # Helios Result with Status, Current and Plan in the attributes
HELIOS_AUTOMATION    = 'automation.helios_optimizer_task'          # Helios Automation that calls the Helios Service to calculate the Optimal Energy Plan
HELIOS_RUNNING       = 'input_boolean.helios_optimizer_running'    # Helios Automation is running (True/False) for the UI Button to show the service is running (extra second added for short service calls)
HELIOS_RUNNING_OLD   = 'pyscript.helios_optimizer_running'         # Helios Automation is running (True/False) for the UI Button to show the service is running (extra second added for short service calls)
HELIOS_PLAN_NAME     = 'Helios Optimizer Energy Plan'              # Friendly Name for the Helios Result Entity
HELIOS_RUNNING_NAME  = 'Helios Optimizer Running'                  # Friendly Name for the Helios Running Entity  
HELIOS_SERVICE_NAME  = 'Helios Optimizer Service'                  # Name of the Helios Optimizer Service
HELIOS_MAIN_NAME     = 'Helios Optimizer Regression Test'          # Name of the Helios Optimizer Main Routine (Regression Test)

HELIOS_INPUT_FNAME   = 'helios_optimizer_input_ha.json'            # JSON Input file  with the input parameters for testing purposes (see main), only for run type 0 (others use the base parameters from main)
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
    insight=INSIGHT_LEVEL,       # Debug level
    output_files=False,          # Write the Helios Optimizer Input Parameters and Output Payload to export files for debugging and regression testing purposes
    output_folder=None,          # Output folder for the export files  
    optimize_ts=None,            # Optimization Day and Time (ts), only for regression testing and debugging, typically this will be None and the current date and time will be used
    max_time=MAX_TIME,           # Maximum Time for the Linear Programming Module (HiGHS Solver of SciPy)
    max_iterations=MAX_ITER,     # Maximum Iterations for the LP Module
    max_grid_import_kw=MAX_GRID,
    max_grid_export_kw=MAX_GRID,
    import_prices=None,
    export_prices=None,
    house_forecast=None,
    solar=None,
    battery=None,
    ev=None,        # future
    heat_pump=None, # future
    boiler=None,    # future
    # Following parameters are automatically provided by Home Assistant when the service is called, but are not used in the service itself
    # WARNING: If these parameters are not included in the service definition, the check on kwargs will throw an TypeError
    #    Any new parameters added by Home Assistant in the future need to be added here, otherwise the service will fail with a TypeError !!!
    return_response=None, # Return a result
    trigger_type=None, # Trigger type (time_trigger, state_trigger, event_trigger) for the service call
    context=None, # Context of the service call (used for logging and debugging)

    **kwargs  # <--- Catches all unknown parameters (MUST be EMPTY for correct calls, otherwise the service cannot check for unexpected parameters, so add any new HA parameters in the parameter list above)
):
    """
    Home Energy Linear Integrated Optimization Service: Helios Optimizer Service
    A Home Assistant PyScript Calculate Energy Plan Service that uses SciPy Linear/MILP Programming.
    """
    try:
        calc_code, calc_result, total_fun_cost = RC_SUCCESS, None, "unavailable" # Default to success, will be changed if an exception occurs
        service_start_dt, service_calc_dt, service_end_dt = datetime.now(), None, None
        log.info(f"{HELIOS_SERVICE_NAME}: Started at {service_start_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    
        # CHECK on Unexpected arguments parameters (all supported keyword arguments have a default value and are optional):
        if kwargs: # Unexpected keyword argument(s) received?
            unknown_keys = list(kwargs.keys())
            raise TypeError(
                f"Unexpected keyword argument(s) received by helios_optimizer_service(): {', '.join(unknown_keys)}"
            )
        output_folder = output_folder if output_folder else HELIOS_FOLDER # Make sure the output folder is filled (with default when None specified)

        battery_info = battery if battery else {}
        solar_info   = solar   if solar   else {}
        await async_write_message('test.log', f"Testing to write a file with steps={steps}, size={step_size}, start={start_step}, soc={battery_info.get('soc_start_pct', None)}, solar_info='{solar_info.get('mode', 'unknown')}' and price size={price_size}")

        # OPTIMIZER INPUT PARAMETERS:    
        optimizer_params = {
            "steps": steps,
            "step_size": step_size,
            "start_step": start_step,
            "price_size": price_size,
            "house_size": house_size,
            "solar_size": solar_size,
            "price_factor": price_factor,
            "insight": insight,
            "output_files": output_files,   # Info only (not used by the calculator)
            "output_folder": output_folder, # Info only (not used by the calculator)
            "optimize_ts": optimize_ts,
            "max_time": max_time,
            "max_iterations": max_iterations,
            "max_grid_import_kw": max_grid_import_kw,
            "max_grid_export_kw": max_grid_export_kw,
            "import_prices": import_prices,
            "export_prices": export_prices,
            "house_forecast": house_forecast,
            "solar": solar,
            "battery": battery,
            "ev": ev,
            "heat_pump": heat_pump,
            "boiler": boiler
        }

        # WRITE INPUT PARAMETERS FILE:
        if output_files: # Write the input parameters to a JSON file for debugging and regression testing purposes
            adapted_params = optimizer_params if optimize_ts else {**optimizer_params, "optimize_ts": datetime_isoformat(timespec="seconds")} # Replace in the parameters the optimizer timestamp with now when no timestamp provided
            await async_write_dict_to_json_file(output_folder + HELIOS_PARAMS_FNAME, adapted_params) # Write the input parameters to a JSON file for debugging and regression testing purposes

        # CALL the HELIOS OPTIMIZER CALCulate PLAN function with the parameters as provided in the Helios Optimizer Service:
        # The Helios Optimizer Calculate Plan function is designed to be independent of Home Assistant, allowing for easier testing and debugging in Visual Studio.
#       payload = helios_optimizer_calc_plan(**optimizer_params) # Run the Helios Optimizer Calculate Plan function with the provided parameters (Synchronous call, be very careful with blocking functions like file io and logging)
        payload = await task.executor(helios_optimizer_calc_plan, **optimizer_params) # Asynchronous Call to the Helios Optimizer Calculation Plan (Pure Python) Function, Waiting (await) for the result, performance seems much better  
#       calc_code      = payload.get('calc_code'     , -1  )
        calc_result    = payload.get('calc_result'   , None)
        total_fun_cost = payload.get('total_fun_cost', None)

        # ADD the service EXECUTION TIME to the payload for logging and debugging purposes:
        service_calc_dt = datetime.now()
        service_calc_ms = round(1000*(service_calc_dt - service_start_dt).total_seconds(), 1) # Performance of the calculation of the plan in ms
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Calculation Time (excluding state.set)={service_calc_ms:.1f}ms")
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Calculated at {service_calc_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} with result '{calc_result}'")
        SERVICE_PERFORMANCE_MS.append(service_calc_ms) # Append this runs calculation time (without state.set)
        payload['service_calc_time_ms'] = round(service_calc_ms,1) # Add Total Calculation Execution Time for the Calculation to the payload (without the state.set)

    # HANDLE SERVICE EXCEPTIONS (Remark: Exceptions are more likely to be handled by the Exception handler of the helios_optimizer_calc_plan):
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}]: Exception: {error_message}")
        payload = { # Construct a simple version of the payload for the service exception
            "success"         : False, 
            "calc_code"       : RC_SERVICE_EXCEPTION, 
            "calc_result"     : "Service Exception", 
            "version"         : HELIOS_VERSION,
            "scipy"           : SCIPY_VERSION,
            "last_run_started": datetime_isoformat_msec(service_start_dt) if service_start_dt is not None else None, # Start of the Run (YYYY:MM:DD HH:MM:SS:TTT)
            "last_run_stopped": datetime_isoformat_msec(service_calc_dt ) if service_calc_dt  is not None else None, # End   of the Run (YYYY:MM:DD HH:MM:SS:TTT)
            "solver_message"  : error_message
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
        else: # The entity must already exist before we write to it (since otherwise a pyscript entity would be created)!
            log.error(f"[{HELIOS_SERVICE_NAME}]: Entity {HELIOS_OPTIM_PLAN} does not exist!")    

    #   task.sleep(1)
    #   task.sleep(0.001)
        service_end_dt = datetime.now()
        service_end_ms = round(1000*(service_end_dt - service_start_dt).total_seconds(), 1) # Performance of the calculation and the state.set:
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Run Time (including state.set)={service_end_ms:.1f}ms")
        log.debug(f"[{HELIOS_SERVICE_NAME}]: Run Finished at {service_end_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} with result '{calc_result}'")
    
    # HANDLE SET STATE EXCEPTIONS:
    except Exception as e:
        error_message = repr(e)
        log.error(f"[{HELIOS_SERVICE_NAME}]: Exception in HA Set State: {error_message}")
        if (calc_code == RC_SUCCESS): # Only set the calc_code, calc_result and solver_message when they are not already set by previous errors
            payload['calc_code']      = RC_SETSTATE_EXCEPTION  # adapt the calc_code to indicate that the state.set failed after a successful calculation
            payload['calc_result']    = "State Set Exception" 
            payload['solver_message'] = error_message

    # WRITE OUTPUT (RESULT) FILES
    try:
        if output_files: # Write the input parameters to a JSON file for debugging and regression testing purposes
            # WRITE PAYLOAD FILE (All Results) to JSON:
            char_count = await async_write_dict_to_json_file(output_folder + HELIOS_PAYLOAD_FNAME, payload) # Write the output to a JSON file for debugging and regression testing purposes
    
            # WRITE ENERGY PLAN FILE to CVS File (Only the Optimized Energy Plan Arrays as a Table):
            headers, row_list = convert_dictoflists_to_listofdicts(payload.get('plan', {}))
            line_count = await async_write_csv_file(output_folder + HELIOS_TABLE_FNAME, row_list=row_list, headers=headers, row_key=None)
    
    except Exception as e:
        error_message = repr(e)
        log.error(f"Exception in Write Output Files for {HELIOS_SERVICE_NAME}: {error_message}")

    return payload # Return the payload to the Home Assistant Automation in the return_response (see the automation trace for details)

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

# Home Assistant Write and Read Functions:
# VERY IMPORTANT: Use these functions instead of synchronous read/write functions in the Home Assistant Main Loop !!!!!
# The async read/write functions are defined above (top of the file) and use special compiler options since otherwise no blocking read/writes are allowed in Home Assistant!
# Write a message with an optional timestamp to a file and add a newline
async def async_write_message(file_name: str, message: str, add_ts: bool = False, add_nl: bool = True) -> int:
    """
    Write a message to a (log) file with an optional timestamp and followed by a newline.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA). 
    The file is blocked during write but data could get mixed up (lines can get shuffled occasionally).
    """        
    # Write the formatted message to the Task Executor (off-thread)
    log.debug(f"Writing message to file '{file_name}'")
    char_count, formatted_msg = 0, format_log_message(message, add_ts, add_nl)
    try: # Try running the Task Excecutor
        char_count = await task.executor(raw_text_writer, file_name, formatted_msg) # Use the task executor to run the raw_file_writer function
#   except (NameError, AttributeError) as e: # If the task or the task.executor does not exist (NOT NEEDED anymore since the task.excecutor() has been added to the HA Mock) 
#       raw_text_writer(file_name, formatted_msg) # Run the raw_text_writer function without the task executor
    except Exception as e: # Everything failed, could not write the message
        log.error(f"Write Message Exception: Write Failed: {repr(e)}") 

    return char_count    

# Write a dictionary as JSON to a file
async def async_write_dict_to_json_file(file_name: str, dict_data: dict, default_type = str, indent: int = 4):
    """
    Write a dictionary as JSON to a file.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA).
    """       
    # "Write the formatted json to a file using the executor (off-thread)
    log.debug(f"Writing JSON file '{file_name}' from a dictionary")
    char_count, json_str = 0, format_dict_as_json(dict_data, indent=indent, default_type = default_type)
    try: # Try running the Task Excecutor:
        char_count = await task.executor(raw_file_writer, file_name, json_str) # Use the task executor to run the raw_file_writer function
    except Exception as e: # Task Executor failed, could not write the json string
        log.error(f"Write JSON File Exception: Write Failed: {repr(e)}")    

    return char_count

# Write a List of Row Dictionaries in CSV format to a file with the specified column delimiter
async def async_write_csv_file(path: str, row_list: list[dict], headers: list = None, row_key: str = None, column_delimiter = ';') -> int:
    line_count = 0
    try: # Try running the Task Excecutor:
        line_count = await task.executor(raw_csv_writer, path, row_list=row_list, headers=headers, row_key = row_key, column_delimiter=column_delimiter) # Use the task executor to run the raw_csv_writer function
    except Exception as e: # Task Executor failed, could not write the csv file
        log.error(f"Write CSV File Exception: Write Failed: {repr(e)}")    
    return line_count

# Read a JSON file into a dictionary
# Returns a dictionary or None (file not found or contains invalid JSON)
async def async_read_dict_from_json_file(path: str) -> dict:
    """
    Read a JSON file into a dictionary.
    Executor handles this off-thread (so the file reading does not hold up the main loop of HA).
    """       
    # Read the file content into a string using the executor (off-thread)
    log.debug(f"Reading JSON file '{path}' into a dictionary") 
    try: # Try running the Task Excecutor
        json_str  = await task.executor(raw_file_reader, path) # Use the task executor to run the raw_file_writer function
        json_dict = convert_json_to_dict(json_str) # Convert the JSON string to a dictionary and return it (returns None when JSON string is None)
        if json_dict is None: # Conversion from JSON to Dictionary failed?
            log.error(f"Read JSON File Exception: JSON Conversion Failed, returning {json_dict}")
    except Exception as e: # Task Executor failed, could not read the json string
        log.error(f"Read JSON File Exception: Read Failed: {repr(e)}")
        json_dict = None

    return json_dict # Return the dictionary or None when file not found or invalid
