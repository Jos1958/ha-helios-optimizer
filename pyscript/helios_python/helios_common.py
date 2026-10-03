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
#   2026-08-29: JR  v0.78k Created a separate helios_common.py file with the common functions
#   2026-09-07: JR  v0.79o Added file handling functions for use in Visual Studio and support functions for asynch file handling in Home Assistant
#   2026-09-09: JR  v0.79o Moved helios_common.py from pyscript/modules/ to pyscript/helios_python/, all functions in this module are now pure python functions (NO longer handled by pyscript), @pyscript_compile directive is not needed/allowed any more
#   2026-09-09: JR  v0.79o Moved the raw file handling functions from helios_services.py to this module (disabled @pyscript_compile directive), Adapted all functions to use the Python _LOGGER instead of the PyScript log
#
#   Remark: For the full helios history see helios_main.py
#   
# Warning: In Visual Studio this module exists in the same folder as helios_main.py and home_assistant_mock.py, but in Home Assistant in the /config/pyscript/modules folder.

import os                                     # For file exist
#mport sys                                    # For sys.path.append() to add the Home Assistant Pyscript folder to the path
import json                                   # For writing a Dictionary Data Structue (e.g. payload output) to a json file
import time 
import csv                                    # For exporting data as a CSV file with DictWriter
import numpy as np                            # Numeric Pyscript Library (includes numeric array) 
import itertools                              # for zip_longest

from typing   import TextIO                   # For DictWriter 
from datetime import datetime, timedelta
from io       import TextIOWrapper

# Determine the environment (Visual Studio or Home Assistant):
try: # Assume we are running in Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
    # Do not add the home_assistant_mock.py to the Home Assistant pyscript/helios folder, it is only needed for testing in Visual Studio
    from home_assistant_mock import service, time_trigger, pyscript_compile, log, automation, task, state  # Include HA mock for testing outside of Home Assistant
    _LOGGER = log # Use the mock log for testing in Visual Studio

except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
    import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
    _LOGGER = logging.getLogger(__name__) # Get access to the Python Standard Logger in pure python functions when running in Home Assistant
#   if "/config/pyscript" not in sys.path: # Already in the search path for pure python modules in Home Assistant? - NOT NEEDED since helios_common.py does not need to import any other modules from the Helios Pure Python folder
#       sys.path.append("/config/pyscript") # Home Assistant Pyscript folder, will HA python modules be found here (e.g. helios_python/helios_common.py)
#   pass  # In Home Assistant no mock is needed since service/state/log etc already exist globally!

def get_scipy_version():
    """Get the current version of SciPy from the metadata."""
#   import scipy # import the entire scipy module
#   return scipy.__version__    
    from importlib.metadata import version # import the import library metadata 
    return version("scipy")

# Global Variables:
SCIPY_VERSION              = get_scipy_version() # Determine the SciPy version only once (at load of the module) for performance reasons
PERFORMANCE_ARRAY_MS: list = []                  # Global variable (is initialized for each run)
ROUND_TIME_MSEC            = 1                   # Round float values for performance time in milliseconds at 1 decimals
HELIOS_COMMON_NAME         = "Helios Common Functions"

RC_UNKNOWN                 = -1 # Nothing has happened yet, so no errors occured (initial value of the calculation code)   
RC_SUCCESS                 = 0  # The HiGHS solver found a feasible solution
RC_INFEASIBLE              = 1  # The HiGHS solver could not find a feasible solution within the specified boundaries and rules
RC_INVALID_COST            = 2  # Cost validation failed (fun cost output is checked and not valid, e.g. total cost != sum of step cost)
RC_INVALID_BALANCE         = 3  # Balance validation failed (overall sum of the energy balance is checked and not valid, e.g. overall balance != 0)
RC_VALIDATION_FAILED       = 6  # Cost Validation Exception (during invalid cost check an exception occured)
RC_OPTIMIZER_EXCEPTION     = 7  # helios_optimizer_calc_plan() Exception
RC_SERVICE_EXCEPTION       = 8  # helios_optimizer_service() Exception in the call to helios_optimizer_calc_plan()
RC_SETSTATE_EXCEPTION      = 9  # helios_optimizer_service() Exception in the call to HA state.set() 

INSIGHT_LEVEL       = 9         # Default Insight Level (0=No Calculation, 1=Optimize, 5=Create Plan Arrays, 9=Maximum Info)
INSIGHT_PLAN        = 5         # Plan Arrays are calculated (from the solver variables) and published when insight is at or above this level
INSIGHT_MAX         = 9         # Maximum Insight Level (All debug info is created)

# -------------------------------------------------------------------
# 99. HELIOS COMMON FUNCTIONS:            
# -------------------------------------------------------------------
def performance_count(t_prev: float = None, t_begin: float = None, index: any = '?') -> tuple[float, int, int]: 
    t_next = time.perf_counter() # End of LP run
    if (t_prev is None):
        phase_time, total_time = 0, 0
        _LOGGER.debug(f"Starting Process Steps")
    else:
        phase_time = round((t_next - t_prev ) * 1000, ROUND_TIME_MSEC) # calculate step  execution time in milliseconds
        total_time = round((t_next - t_begin) * 1000, ROUND_TIME_MSEC) # calculate total execution time in milliseconds
        _LOGGER.debug(f"{HELIOS_COMMON_NAME}: Time for Step[{str(index):>6s}]={phase_time:4.1f}, Total Time={total_time:4.1f}")
        PERFORMANCE_ARRAY_MS.append(f"{index}={phase_time:.1f}")
    #   _LOGGER.warning(f"Added: {PERFORMANCE_ARRAY_MS}")
    return t_next, phase_time, total_time

def convert_ts(value: str, field: str = 'unknown', default_ts: datetime = None) -> datetime:
    """Validate a datetime string value and return the default if invalid."""
    if ((value is not None) and isinstance(value, str)):
        try:
            return datetime.fromisoformat(value) # Conversion from string
        except Exception as e: # timestamp conversion failed
            _LOGGER.error(f"{HELIOS_COMMON_NAME}: Timestamp is invalid {repr(e)}, using default {str(default_ts)}")
            return default_ts # Conversion failed so returning the default timestamp
    else: # no timestamp string provided
        return default_ts # No value provide so return the default timestamp

def convert_int(value, field: str = 'unknown', min: int = None, max: int = None, allowed_values = None, allow_none = False) -> int:
    """Validate an integer value and raise an error if invalid. When specified check the minimum and maxium value and/or the allowed values."""
    if (allow_none) and value is None:
        return None
    if not str(value).isdecimal(): 
        raise TypeError(f"Invalid integer value={value} for {field}!")
    else:
        int_value = int(value)
        if (min != None) and (int_value < min):
            raise TypeError(f"Integer value={value} for {field} is below the minimum value of {min}!")
        elif (max != None) and (int_value > max):
            raise TypeError(f"Integer value={value} for {field} is above the maximum value of {max}!")
        elif (allowed_values is not None) and isinstance(allowed_values, (list, tuple, set)) and (int_value not in allowed_values):
            raise TypeError(f"Integer value={value} for {field} does not exist in the list of allowed values {allowed_values}!")
        else:
            return int_value

def convert_float(value, field: str = 'unknown', min: float = None, max: float = None, allow_none = False, factor: float = 1.0, decimals: int = None) -> float:
    """Validate a float value and raise an error if invalid. When specified check the minimum and maxium."""
    if (allow_none) and value is None:
        return None
    if not is_float(str(value)):
        raise TypeError(f"Invalid float value={value} for {field}!")
    else:
        float_value = float(value) if factor is None else factor * float(value) # convert to a float and apply the optional factor
        if (min != None) and (float_value < min):
            raise TypeError(f"Float value={value} for {field} is below the minimum value of {min}!")
        elif (max != None) and (float_value > max):
            raise TypeError(f"Float value={value} for {field} is above the maximum value of {max}!")
        else:
            if decimals is not None:
                float_value = round(float_value, decimals)
            return float_value

def is_float(value):
    """Validate a float value."""
    try:
        float(value)
        return True # float provided
    except: # conversion failed
        return False # Not a float

# Format the datetime using a format string:
def datetime_string(dt: datetime = datetime.now(), dt_format: str = "%Y-%m-%d %H:%M"):
    return dt.strftime(dt_format)

# Format the datetime using iso format with the specified timespec (minutes, seconds, )
def datetime_isoformat(dt: datetime = datetime.now(), timespec: str = "minutes", separator: str = ' '):
    return dt.isoformat(timespec=timespec, sep=separator)
def datetime_isoformat_sec(dt: datetime = datetime.now(), timespec: str = "seconds", separator: str = ' '):
    return dt.isoformat(timespec=timespec, sep=separator)
def datetime_isoformat_msec(dt: datetime = datetime.now(), timespec: str = "milliseconds", separator: str = ' '):
    return dt.isoformat(timespec=timespec, sep=separator)

def is_size_correct(array, expected_size, name):
    """Validate the size of an array and raise an error if invalid."""
    array_size = len(array)
    if array_size != expected_size:
        raise ValueError(f"Invalid size for {name} array: expected {expected_size}, got {array_size}")

def check_and_multiply_size(data_array: list, expected_size: int, name: str, expand = False, max_mult: int = 4) -> list:
    """Validate and optionally expand the Data array by multiplying it to match the expected size."""
    array_size = len(data_array)

    # 1. Data array already has the correct size:
    if array_size == expected_size:
        return data_array # return the original data_array

    # 2. Check if expected size can be divided exactly by the array_size, the factor is limited (e.g. number of days only)
    factor = expected_size // array_size
    if expand and (array_size > 0) and (expected_size % array_size == 0) and (factor <= max_mult):
        # Repeat the data array (e.g. each day or days the same values) factor x
#       return [item for item in data_array for _ in range(factor)]
        return data_array * factor # return the multiplied data array 

    # 3. For an invalid data array size
    raise ValueError(
        f"Invalid size for {name} array: expected {expected_size}, got {array_size}"
    )

def check_and_extend_size(
    data_array   : list,         # The data array to be checked for its size 
    expected_size: int,          # Expected size of the array
    name         : str  = "unknown-array",  # a name for the array
    expand       : bool = False, # By default do not extend the array
    steps_per_day: int  = 24,    # If extending is needed it must be a multiple of steps per day 
    max_days     : int  = 4      # Add no more then max_days to the array
) -> list:
    """Validate and optionally expand the array by extending it with the last day's values (1 or more times). When the array size is too large the extra values will be ignored!"""
    array_size = len(data_array)

    # 1. Check if data array already has the correct size (or larger) or is empty:
    if (data_array is None) or (len(data_array) == 0) or (array_size >= expected_size):
        return data_array # No changes required 

    # 2. Check if data array can be expanded with whole days:
    if expand and array_size >= steps_per_day:
        missing_steps = expected_size - array_size

        # Check if the missing steps are exactly a number of days
        if missing_steps > 0 and missing_steps % steps_per_day == 0:
            added_days = missing_steps // steps_per_day

            if added_days <= max_days: # Check that not to many days need to be added
                # Take the steps from the last day in the data array (last 'steps_per_day' elements)
                last_day = data_array[-steps_per_day:]
                # Add the last day x times to the existing array
                extended_array = data_array + (last_day * added_days)
                _LOGGER.warning(f"{HELIOS_COMMON_NAME}: Extended the {name} array with {added_days} day(s) (={steps_per_day * added_days} steps), New Length={len(extended_array)} steps!")
                return extended_array

    # 3. For an invalid array size: raise an error
    raise ValueError(
        f"Invalid size for {name} array: expected {expected_size}, got {array_size}"
    )

def resample(data_array: list, step_in: int, step_out: int, name: str = "unknown-array" , kind='linear', conserve_sum: bool = False, dtype=float, decimals=None) -> list:
    """
    Resamples a data series from any 'step_in' interval to 'step_out'.

    Parameters:
        data_array (list | np.ndarray): Input data series.
        step_in  (int | float): Original step size in minutes (e.g., 60, 30, 15).
        step_out (int | float): Desired  step size in minutes (e.g., 15, 5, 60).
        kind (str): 
            - 'linear'  : Linear interpolation between points (e.g., SoC, kW power).
            - 'zero'    : Step-wise / constant block (ideal for hourly electricity prices).
            - 'cubic'   : Smooth cubic spline curve (e.g., solar irradiance).
            - 'nearest' : Nearest neighbor interpolation.
        conserve_sum (bool): If True, scales the output to conserve the total sum of the input series (e.g. for quantities per interval (e.g. kWh), not applicable to prices
        decimals (int | None): Number of decimal places to round to. Default is None (no rounding).
    """
    from scipy.interpolate import interp1d

    # 1. Data array already has the correct size or is empty:
    if (data_array is None) or (len(data_array) == 0) or (step_in is None) or (step_in == step_out):
        return list(data_array) # No changes required

    # 2. Convert the incoming array to a np array:
    np_data_array = np.array(data_array, dtype=dtype)
    total_duration = len(np_data_array) * step_in

    if conserve_sum:
        _LOGGER.debug(f"Resample Original Sum: {np_data_array.sum()}")
    
    # 3. Build the original time axis: e.g. [0, 60, 120, ..., 1380] (60min, 24 steps, total time 1440)
    x_old = np.arange(0, total_duration, step_in)    # 1. Build the original time axis (e.g., [0, 60, 120, 180] minutes)

    # 4. Build the new time axis: e.g. [0, 15, 30, 45, 60, ..., 1425] (15 min, 96 steps, total time 1440 min)
    x_new = np.arange(0, total_duration, step_out)    
    
    # 5. Create interpolation function with edge-value padding
    f = interp1d(
        x_old, 
        np_data_array, 
        kind=kind, 
        bounds_error=False, 
        fill_value=(np_data_array[0], np_data_array[-1])  # Hold edge values outside boundary range
    )
    result_array = f(x_new)

    # Scale if the total sum of the interval must remain the same
    if conserve_sum:
        result_array *= (step_out / step_in)
        _LOGGER.debug(f"Resample Result Sum: {result_array.sum()}")

    # Round result if decimals is specified
    if decimals is not None:
        result_array = np.round(result_array, decimals)

    _LOGGER.warning(f"{HELIOS_COMMON_NAME}: Resampled the {name} array[{len(data_array)}] from step size {step_in} to {step_out}, New Length={len(result_array)} steps!")

    return result_array.tolist()

# Compare difference between 2 Lists using the List INDEX to compare
# WARNING: For now nesting in lists is not supported!
def list_index_diff(list1, list2, path = None):
    _LOGGER.warning("Comparing Index List" + (f" for {path}:" if path else ":"))
#   _LOGGER.warning(f"Comparing2 list:\n{list1}\n{list2}")
    diff = {}
    max_len = max(len(list1), len(list2))
    for i in range(max_len):
        if i >= len(list2): # not in list2:
            diff[i] = ("Added in List", list1[i])
        elif i >= len(list1): # not in list1
            diff[i] = ("Removed from List", list2[i])
        elif list1[i] != list2[i]:
            diff[i] = ("Changed List Value", list2[i], "->", list1[i])
#   if diff != {}: _LOGGER.debug(diff)
    return diff

# Compare difference between 2 Lists using the List VALUES as KEYS
# WARNING: For now nesting in lists is not supported!
def list_key_diff(list1, list2, path = None):
    _LOGGER.warning("Comparing Key List" + (f" for {path}:" if path else ":"))
#   _LOGGER.warning(f"Comparing list:\n{l1}\n{l2}")
    diff = {}
    for key in set(list1) | set(list2):
        if key not in list2:
            diff[key] = "Added in List"
        elif key not in list1:
            diff[key] = "Removed from List"
#   if diff != {}: _LOGGER.debug(diff)
    return diff

# Determine differences between 2 dictionaries (compare dict-s)
# dict1 is the newer dictionary and dict2 is the old dictionary
# Excluded keys typically contain fields like start_date or execution_time
def dict_diff(dict1, dict2, excluded_keys = [], list_type = "list", path = None):
    _LOGGER.warning("Comparing Dictionary" + (f" for {path}:" if path is not None else " for Root:"))
    diff = {}
    for k in dict1.keys() | dict2.keys():
        prefix = f"{path}-{k}" if path is not None else f"{k}"
        if k not in dict2:
            diff[k] = ("Added in Dict", dict1[k])
        elif k not in dict1:
            diff[k] = ("Removed in Dict", dict2[k])
        elif dict1[k] != dict2[k]:
            if not k in excluded_keys:
                if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                    nested_diff = dict_diff(dict1[k], dict2[k], excluded_keys, list_type, prefix)
                    if nested_diff:
                        diff[k] = nested_diff
                elif isinstance(dict1[k], list) and isinstance(dict2[k], list):
                    if (list_type == 'list'):
                        nested_list = list_index_diff(dict1[k], dict2[k], prefix)
                    else:    
                        nested_list = list_key_diff(dict1[k], dict2[k], prefix)
                    diff[k] = nested_list
                else:
                    diff[k] = ("Changed Dict Value", dict1[k], "->", dict2[k])
    
#   if diff != {}: _LOGGER.debug(diff)
    return diff

# Check if the file with the specified file name already exists
def exist_file(file_name: str) -> bool:
    return os.path.isfile(file_name)            

# Format a log message with an optional timestamp and an optional new line
def format_log_message(message: str, add_ts: bool = True, add_nl: bool = True) -> str:
    timestamp = '' if not add_ts else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' '
    newline   = '' if not add_nl else "\n"
    return f"{timestamp}{message}{newline}" # formatted the message with an optional timestamp and an optional new line

# Convert ISO formatted datetime strings to datetime objects
# Used as hook when reading json strings into a dictionary
def datetime_parser(json_dict):
    for key, value in json_dict.items():
        if isinstance(value, str) and (len(value) >= 23): # Only 23-size date strings are converted back to a real date
            try:
                # Try to recognize a ISO-geformatted date-string
                json_dict[key] = datetime.fromisoformat(value)
            except ValueError:
                pass
    return json_dict

# Format a dictionary as a JSON string with optional indentation and default type for non-serializable objects
def format_dict_as_json(dict_data: dict, indent: int = 4, default_type = str) -> str:
    """Format a dictionary as a JSON string with optional indentation and default type for non-serializable objects."""
    return json.dumps(dict_data, indent=indent, default=default_type)  

# Convert a JSON string back to a dictionary and 
# Datetime objects are represented as string in the file (and will be converted to datatime objects when recognized as iso formatted string)
def convert_json_to_dict(json_str: str) -> dict:
    """Convert a JSON string string back to a dictionary."""
    try:
        dict_data = json.loads(json_str, object_hook=datetime_parser) if json_str else None
    except Exception as e:
        _LOGGER.error(f"Exception in converting JSON to Dictionary: {repr(e)}")
        dict_data = None

    return dict_data

# Convert a Dictionary of Lists (e.g. Energy Plan) into a list of rows (each row is a dictionary of fields in the row)
# This conversion is needed to save an energy plan (list of variables with values for each step) into a csv file
def convert_dictoflists_to_listofdicts(data_dict: dict[list], column_delimiter = ';') -> list[dict]:
    # All keys that do not have a value of None (The value is none when the list of step values is not available)
    # e.g. { timestamp[..], 'strategy': [..], ev_charge_kw: None, 'boiler_charge_kw': [..] } -> ['timestamp', 'strategy', 'boiler_charge_kw']
    headers = [key for key, val in data_dict.items() if val is not None] # Only the array keys which have an array

#   # Swap the columns and rows (but only when the column has content): dict[list] -> list[dict]
    # e.g. { timestamp['2026-09-08 12:00', '2026-09-8 12:15'], 'strategy': ['sell', 'charge'], ev_charge_kw: None } -> [{'timestamp': '2026-09-08 12:00', 'strategy': 'sell'}, {'timestamp': '2026-09-08 12:15', 'strategy': 'charge'}]
    dict_rows = [
        dict(zip(headers, row_values)) 
        for row_values in itertools.zip_longest(
            *[list(val) for val in data_dict.values() if val is not None],
            fillvalue=None  # Fills shorter arrays with None
        )
    ]

    return (headers, dict_rows) # Return the headers and the d

#################################################################################################
#### WARNING: Following File Functions cannot be executed in the main loop in Home Assistant ####
#### WARNING: Use the Async version in Helios Services instead                               ####
####          The Async version will call the related raw versions as defined below          ####
#################################################################################################

# These sub-functions do the heavy (blocking) work for handling files. 
# During the read or write other threads trying to access the same file will block.
# By calling these functions using an executor the function will run on a separate thread so that the HA loop does not block.
# The function has been placed on purpose on top of the py file (see google gemini conversation) to activate the compile decorator.
# The pyscript compile decorator forces pyscript to compile the function as standard python (instead of HomeAssistant python with access to HA states) since this is mandatory in an executor.
# Raw file writer appends a text to a file. 
# @pyscript_compile # Not needed anymore since the helios_common.py is now in /pyscript/helios_python/ (pure python) folder and not in the /pyscript/ or /pyscript/modules/ (pyscript) folders, it is compiled and imported  
def raw_text_writer(path: str, text: str, newline = "", encoding = "utf-8") -> int:
    char_count = 0
    try:
        # 'a' is for append, existing file are opened for writing at the end of the file. If the file does not exist, it will be created.
#       with open(path, "a", newline="", encoding="utf-8") as f: # Open for append ("a")
        with raw_open_file_for_append(path, newline=newline, encoding=encoding) as f: # Open for append ("a")
            char_count = f.write(text) # append the text to the file but do not yet close
    except Exception as e:
        # log.error is not allowed within an executor, warning: this log message does not have the ERROR level (enable logging with info level) 
#       log.error(f"Pyscript Log Error: Could not write to log file {path}: {e}") # Not possible in an executor, log is unknown!
#       print(f"Pyscript Log Error: Could not write to file {path}: {e}")         # Python print is not visible in Home Assistant
        _LOGGER.error(f"Pyscript Raw Text Writer Error for {path}: {repr(e)}") 

    return char_count # Number of characters written (0 when failed)

# Raw file writer replaces the content of a file with the new text. 
# @pyscript_compile # Not needed anymore (see above)
def raw_file_writer(path: str, text: str, newline = "", encoding = "utf-8") -> int:
    char_count = 0
    try:
        # 'w' is for write/replace, existing file are opened for writing at the start of the file. 
#       with open(path, "w", newline="", encoding="utf-8") as f: # Open for replace ("w")
        with raw_open_file_for_replace(path, newline=newline, encoding=encoding) as f: # Open for replace ("w")
            char_count = f.write(text) # replace the content of the file with the new text
            f.close() # close the file to ensure the content is written to disk
    except Exception as e:
        _LOGGER.error(f"Pyscript Raw File Writer Error for {path}: {repr(e)}") 
    
    return char_count # Number of characters written (0 when failed)

# Raw file writer replaces the content of a file with the csv data from the input table (list of row dictionaries). 
# Uses a Dictionary Writer for the specified file to write a header and a line for each row in the table
# Each Row is a Dictionary with as keys the header fields
# The header is automatically built from the first row but when specified it defines which fields are included (extrasaction='ignore') and in which order they appear
# With extrasaction is 'raise' the writer will throw an error when the headers list does not contain all fields that occur
# The Dictonary to be written for a row, can be one level down if you specify a row key
# @pyscript_compile # Not needed anymore (see above)
def raw_csv_writer(path: str, row_list: list[dict], headers: list = None, row_key: str = None, newline = "", encoding = "utf-8", column_delimiter: str = ';', extrasaction = 'ignore') -> int:
    row_count = 0
    try:
        if isinstance(row_list, list) and (headers is None or type(headers) is list):
            if (headers is None or len(headers) == 0) and len(row_list) > 0: # No headers specified, try to built an header list from the first row
               first_row = row_list[0][row_key] if row_key else row_list[0] # Get the first row
               headers = first_row.keys() # Use the first row to get the headers 

            if headers is not None:
                # 'w' is for write/replace, existing file are opened for writing at the start of the file. 
#               with open(path, "w", newline=newline, encoding=encoding) as f: # Open for replace ("w")
                with raw_open_file_for_replace(path, newline=newline, encoding=encoding) as f: # Open for replace ("w")
                    writer = csv.DictWriter(f, fieldnames=headers, delimiter=column_delimiter, extrasaction=extrasaction) # Create the Dictionary Writer for the file with the field names
    
                    if headers is not None:
                        writer.writeheader() # Write the header based upon the fieldnames
                        row_count += 1
    
                    if len(row_list) > 0:
                        # Write a line for each row (=dictionary) in the table (=list of rows)
                    #   writer.writerows(row_list)
                        for row in row_list:
                            writer.writerow(row[row_key] if row_key is not None else row) # write the table row
                            row_count += 1
                    else:
                        f.write('No Data Available')
                        _LOGGER.error(f"Pyscript Raw CSV Writer has NO Data!") 

                    f.close() # Close the file

            else: # No headers specified: Headers are mandatory
                _LOGGER.error(f"Pyscript Raw CSV Writer has NO Headers!") 
        else:
             _LOGGER.error(f"Pyscript Raw CSV Writer received invalid headers {headers} or data {row_list}!") 
    except Exception as e:
        _LOGGER.error(f"Pyscript Raw CSV Writer Error for {path}: {repr(e)}") 

    return row_count

# Raw file reader reads the content of a file and returns the content as a text. 
# @pyscript_compile # Not needed anymore (see above)
def raw_file_reader(path: str, newline = "", encoding = "utf-8") -> str:
    try:
        # 'r' is for read, existing file are opened for reading at the start of the file. 
#       with open(path, "r", newline = "", encoding="utf-8") as f: # Open for read ("r")
        with raw_open_file_for_read(path, newline=newline, encoding=encoding) as f: # Open for read ("r")
            text = f.read()
            f.close()
            return text
    except Exception as e:
        _LOGGER.error(f"Pyscript Raw File Reader Error for {path}: {repr(e)}") 
        return None # Return None if the file could not be read

# Open a file in Replace ("w") Mode at the start of the file with the specified newline and encoding 
# @pyscript_compile # Not needed anymore (see above)
def raw_open_file_for_replace(path: str, newline: str = "", encoding = "utf-8") -> TextIOWrapper:
    return open(path, "w", newline=newline, encoding=encoding) # "w"=Write/Replace (overwrite the file for each run)

# Open a file in Append ("a") Mode at the end of the file with the specified newline and encoding
# If the file does not exist, it will be created.
# @pyscript_compile # Not needed anymore (see above)
def raw_open_file_for_append(path: str, newline: str  = "", encoding = "utf-8") -> TextIOWrapper:
    return open(path, "a", newline=newline, encoding=encoding) # "a"=Append (multiple runs in the same file)

# Open a file in Read ("r") Mode at the start of the file with the specified new line and encoding 
# @pyscript_compile # Not needed anymore (see above)
def raw_open_file_for_read(path: str, newline = "", encoding = "utf-8") -> TextIOWrapper:
    return open(path, "r", newline=newline, encoding=encoding) # "r"=Read Only
