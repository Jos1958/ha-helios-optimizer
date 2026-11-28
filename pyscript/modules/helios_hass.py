# Module: HELIOS Hass - PyScript Functions used by Helios Services, Helios Forecast, Helios History, ...
# HELIOS is the Home Energy Linear Integrated Optimization Service which uses hass pyscript functions as defined in the Helios Hass Module. 
#
# High Level Description of the PyScript Functions:
# - File Handling Functions: Provide access asynchronous IO functions for PyScript (the pure python raw IO functions are in Helios Common but require a wrapper for pyscript access).
# - Home Assistant (HASS) Entity Access using the PyScript state facilities (in the future these methods need to migrate to use hass when used in a custom component environment)
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-11-23: JR: V0.9.6 Split of 'PyScript' functions that are used in multiple PyScript Services and moved them to this module (to be placed in the sub-folder modules)
#   2026-11-26: JR: V0.9.6 Added Home Assistant Datetime Utility functions to Helios Hass (ha_now_ts and ha_now_info), used by Helios Forecast and Helios Services
#   2026-11-27: JR  v0.96  Improved IO-handling (async_*) and error handling, including raise_error option and combine folder with path, create folder when needed (in raw_*)

from ast import Dict

# Check if imports are enabled (Only Applicable in the Home Assistant PyScript environment):
IMPORTS_FAILED_HASS, HOME_ASSISTANT_HASS = False, False # Imports Not failed yet, Not in HA environment
try:
    import sys  # For sys.path.append() to add the Home Assistant /config/pyscript folder to the path to allow /config/pyscript/helios_python to be found !!!

    try: # Assume we are running in MS Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
        # Home Assistant will not have the home_assistant_mock.py (and the import will FAIL): 
        from home_assistant_mock import * # Import the Home Assistant Mockup for Visual Studio (to allow PyScript testing in Visual Studio)
    except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
        HOME_ASSISTANT_HASS = True

except (ImportError, Exception) as e:
    IMPORTS_FAILED_HASS = True # Allow the helios_services.py to be loaded without imports and report the error later on
    HOME_ASSISTANT_HASS = True # Imports only fail in Home Assistant (usually)

# Determine the environment (Visual Studio or Home Assistant) by importing the Home Assistant Mockup:
dt_util = None # Home Assistant Datetime Utility not yet available
if not HOME_ASSISTANT_HASS:
    # Modules used by Visual Studio need to start with 'modules.' since they are always in a sub-folder 'modules'
    from modules.helios_hass import * # Import the Helios Home Assistant functions from folder ./modules/

else: # Assume we are in Home Assistant (since the mockup was not found or imports have failed)
    if not IMPORTS_FAILED_HASS: # Further imports and sys functions only when (HA PyScript) import did not fail
        try: # Use Home Assistant Datetime (very important in container environments since it provides timezone-aware datetime handling)
            import homeassistant.util.dt as dt_util # pyright: ignore[reportMissingImports] # Get the HA Datetime Utility (especially important for container environments)
        except:
            pass # use OS datetime 

        # Add for Home Assistant the Pyscript folder to the system path (not needed for MS Visual Studio since the main folder is already in the path)
        # Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)
        if "/config/pyscript" not in sys.path: # Pyscript Folder already in the search path?
            sys.path.append("/config/pyscript") # Add the Home Assistant Pyscript folder to the system path

# Pure Python Files must be in the sub-folder helios_python 
# In HA: pyscript/helios_python (/config/pyscript must have been appended to the sys.path),
# In VS: c:\$code\VisualStudio2026\HeliosOptimizer\helios_python)
if not IMPORTS_FAILED_HASS: 
    from helios_python.helios_common import * # Import helios_common.py 

HELIOS_HASS_NAME  = 'Helios Optimizer Hass'  # Name of the Helios Optimizer Hass Module
HELIOS_ASYNC_NAME = 'Helios Optimizer Async' # Name of the Helios Optimizer Async IO Functions in the Hass Module

##########################################################################################################################
# Retrieve the current timestamp (datetime) from Home Assistant Datetime Utility                                         # 
# IMPORTANT: Use these functions instead of the regular datetime functions!                                              #
#            In a container installation the regular datetime may return the system time (e.g. UTC)                      #
#            which may be different from the user time as defined in Home Assistant.                                     #
#            As a backup the ha_ functions will return the regular time                                                  #
##########################################################################################################################
# Get the datetime (ts) and Timezone Info for today from the Home Assistant Date Time Utility
# If the HA Date Time Utility (dt_util) is not available (in MS Visual Studio) or it fails then use the regular Python Datetime
# For testing purpose an ISO Format datetime string can be provided (including a timezone)
# Return a tuple with datetime for now, a timezone and the timezine offset in minutes
def ha_now_info(now_ts_str: str  = None):
    if now_ts_str is None: # No specific date specified
        now_ts = datetime.now() # Regular Local Now (does not have a timezone yet)
    else:
        now_ts = datetime.fromisoformat(now_ts_str)

    # Get the Regular Timezone Info:
    now_tz  = now_ts.astimezone().tzinfo # Get Timezone info object from the datetime for now

    # Try to get the Home Assistant Now and Timezone Info (if not available or it fails then the regular now is already determined above)
    if (now_ts_str is None) and dt_util: # Home Assistant Datetime Utility available (and not a test timestamp string)?
        try: 
            now_ts  = dt_util.now() # Get the HA Datetime
            now_tz  = dt_util.get_time_zone(hass.config.time_zone) # Get the HA Timezone Info (requires a different method then the regular)
            log.debug(f"{HELIOS_HASS_NAME}: Home Assistant Datetime {datetime_string(now_ts)} (TZ={str(now_tz)}) retrieved.")
        except Exception as e: # HA Datetime or Timezone failed but we already have the regular datetime and timezone
            log.error(f"{HELIOS_HASS_NAME}: Home Assistant Datetime or Timezone retrieval failed: {repr(e)}")

    now_off = now_tz.utcoffset(now_ts) # Determine the offset for the timezone
    now_off_min = int(now_off.total_seconds() / 60) # Timezone offset in minutes (integer)
    log.info(f"{HELIOS_HASS_NAME}: Datetime {datetime_string(now_ts)} (Offset={now_off_min}min) retrieved.")
    return (now_ts, now_tz, now_off_min)

# Get the datetime (ts) for today from the Home Assistant Date Time Utility
# If the HA Date Time Utility (dt_util) is not available (in MS Visual Studio) or it fails then use the regular Python Datetime
# For testing purpose an ISO Format datetime string can be provided (including a timezone)
# Return datetime for now
def ha_now_ts(now_ts_str: str  = None):
    if now_ts_str is None: # No specific date specified
        now_ts = datetime.now() # Regular Now
        if dt_util:
            try:
                now_ts  = dt_util.now() # Get the HA Datetime
                log.debug(f"{HELIOS_HASS_NAME}: Home Assistant Datetime {datetime_string(now_ts)} retrieved.")
            except Exception as e:
                log.error(f"{HELIOS_HASS_NAME}: Home Assistant Datetime retrieval failed: {repr(e)}")
    else:
        now_ts = datetime.fromisoformat(now_ts_str)

    log.info(f"{HELIOS_HASS_NAME}: Datetime {datetime_string(now_ts)} retrieved.")
    return now_ts

##########################################################################################################################
# Asynchronous Home Assistant Write and Read FILE Functions:                                                             # 
# VERY IMPORTANT: Use these functions instead of synchronous read/write functions in the Home Assistant Main Loop !!!!!  #
# The raw read/write functions are moved to helios_common.py and are now PURE Python functions (outside HA PyScript)     #
# In HA PyScript these raw read/write functions would need a special compiler option (@pyscript_compile)                 #       
# since otherwise no blocking read/writes were allowed in the HA!                                                        #
##########################################################################################################################
# Append a Message to a file
async def async_write_message(path: str, message: str, folder: str = None, add_ts: bool = False, add_nl: bool = True) -> int:
    """
    Append a (formatted) Message to a (Log) File with an optional timestamp and followed by an optional newline.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA). 
    The file is blocked during write but data could get mixed up (lines can get shuffled occasionally) when multiple calls are active at the same time.
    """        
    # Append the formatted message to a file using the Task Executor (off-thread)
    log.debug(f"Append Message to File '{path}' ...")
    char_count = 0
    formatted_msg = format_log_message(message, add_ts, add_nl)
    try: # Try running the Task Excecutor
        char_count = await task.executor(raw_text_writer, path, text=formatted_msg, folder=folder) # Use the task executor to run the raw_file_writer function
#   except (NameError, AttributeError) as e: # If the task or the task.executor does not exist (NOT NEEDED anymore since the task.excecutor() has been added to the HA Mock) 
#       raw_text_writer(file_name, formatted_msg) # Run the raw_text_writer function without the task executor
    except Exception as e: # Everything failed, could not write the message
        log.error(f"[{HELIOS_ASYNC_NAME}-Write-Msg] Exception: {repr(e)}")
    return char_count    

# Write a List of Rows (Dictionaries) to a CSV File
async def async_write_csv_file(path: str, row_list: list[dict], headers: list = None, row_key: str = None, folder: str = None, column_delimiter = ';') -> int:
    """
    Write a List of Rows (Dictionaries) in CSV Format to a File using the specified column delimiter and include a Header line
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA).
    """       
    line_count = 0
    log.debug(f"Writing CSV File {path} from a List of Rows ...")
    try: # Try running the Task Excecutor:
        line_count = await task.executor(raw_csv_writer, path, row_list=row_list, headers=headers, row_key=row_key, folder=folder, column_delimiter=column_delimiter) # Use the task executor to run the raw_csv_writer function
    except Exception as e: # Task Executor failed, could not write the csv file
        log.error(f"[{HELIOS_ASYNC_NAME}-Write-CSV] Exception: {repr(e)}")
    return line_count

# Write a dictionary to a JSON File
async def async_write_dict_to_json_file(path: str, dict_data: dict, folder: str = None, indent: int = 4, default_type = str):
    """
    Write a dictionary in JSON Format to a File using the specified indentation and default type.
    Executor handles this off-thread (so the file writing does not hold up the main loop of HA).
    """       
    log.debug(f"Writing JSON File {path} from a Dictionary ...")
    char_count = 0
    try: # Try running the Task Excecutor:
        # "Write the formatted json to a file using the executor (off-thread)
        char_count = await task.executor(raw_json_writer, path, dict_data = dict_data, folder=folder, indent = indent, default_type = default_type) # Use the task executor to run the raw_json_writer function
    except Exception as e: # Task Executor failed, could not write the json string
        log.error(f"[{HELIOS_ASYNC_NAME}-Write-JSON] Exception: {repr(e)}")
    return char_count

# Read a JSON file into a Dictionary
async def async_read_dict_from_json_file(path: str, folder: str = None, raise_error: bool = False) -> dict:
    """
    Read a JSON file into a dictionary.
    Returns a dictionary or None (when the file is not found or contains invalid JSON).
    Executor handles this off-thread (so the file reading does not hold up the main loop of HA).
    """       
    # Read the file content into a dictionary using the executor (off-thread)
    json_dict = None
    log.debug(f"Reading JSON File {path} into a dictionary ...") 
    try: # Try running the Task Excecutor
        json_dict  = await task.executor(raw_json_reader, path, folder=folder) # Use the task executor to run the raw_json_reader function

    except Exception as e: # Task Executor failed, could not read the json string
        if raise_error:
            raise ValueError(str(e))
        else:
            log.error(f"[{HELIOS_ASYNC_NAME}-Read-JSON] Exception: {repr(e)}")
    return json_dict # Return the Dictionary or None when file not found or invalid

# Read a Configuration File into a Dictionary 
async def async_load_config(path: str, folder: str = None, raise_error: bool = False) -> Dict:
    """
    Read a JSON Configuration File into a Dictionary.
    Returns a dictionary or None (when the file is not found or contains invalid JSON).
    Executor handles this off-thread (so the file reading does not hold up the main loop of HA).
    """       
    config_dict = None
    log.debug(f"Reading JSON Configuration File {path} into a dictionary ...") 
    try: # Try running the Task Excecutor
        config_dict  = await task.executor(raw_load_config, path, folder=folder, raise_error=raise_error) # Use the task executor to run the raw_load_config function

    except Exception as e: # Task Executor failed, could not parse the json string or another error
        if raise_error:
            raise ValueError(str(e))
        else:
            log.error(f"[{HELIOS_ASYNC_NAME}-Read-JSON] Exception: {repr(e)}")
    return config_dict # Return the Configuration Dictionary or None when file not found or invalid

##########################################################################
# PyScript Home Assistant State Functions                                #
# Copied from _batmgt_util.py and modified for use in Helios             #
# Not yet applied to the Battery Management System (BMS)                 #
# Warning: Use hass (instead of state) for python and custom_components! #
##########################################################################
# Abnormal State Internal Values (applicable to Battery States and House Power Surplus State, copied from _batmgt_config.py):
INITIAL_STATE   = "Initial"     # Initial version of a state at load of the pyscript or before retrieval from Home Assistant
UNKNOWN_STATE   = "Unknown"     # Unknown state  (Used when the SOC of a battery or the House Power Surplus are temporary not available)
UNAVAIL_STATE   = "Unavailable" # Unavailable state (Serious problem with getting access)
FAILED_STATE    = "Failed"      # Failed state   (Used when an exception occurs while calculating the state)
NOT_FOUND_STATE = "NotFound"    # Not Found      (Set at the start of the calculation/lookup, indicates that no valid state has been found)
NONAME_STATE    = "NoStateName" # No Name        (Set when a state is retrieved for a state name of None, only allowed for optional states/results)

# Home Assistant Entity values (copied from _batmgt_config.py):
HA_ON        = "on"             # Home Assistant switch value for On
HA_OFF       = "off"            # Home Assistant switch value for Off
HA_UNK       = "Unk"            # Home Assistant switch value not yet retrieved
HA_UNKNOWN   = "unknown"        # Home Assistant Stae is temporary not known (e.g. at startup), processing can continue because the value may come available later
HA_UNAVAIL   = "unavailable"    # Home Assistant State is unavailable due to a connection error with the device or other more serious problem, perhaps better stop processing
HA_UN_LIST   = [HA_UNKNOWN, HA_UNAVAIL] # Home Assistant List of Undefined States (unknown or unavailable)
HA_FRNAME    = "friendly_name"  # Home Assistant attribute name for Friendly (Alternative) Name of a state 
MAX_DELAY_VALUE = 99999         # Prevent overflow of timestamp delta's by replacing it by this value for delta's since fromtimestamp(0)

def ha_service_exist(domain: str, service: str) -> bool:
    try:
        return hass.services.has_service(domain, service)
    except NameError:
        # Fallback when has_service is not available
        return False

# Exist Home Assistant Entity
def ha_entity_exist(entity_id: str) -> bool:
    """Check if a Home Assistant State exists."""
    return state.exist(entity_id) # Check if the state name exists in the Home Assistant state dictionary

# Check if a Home Assistant State is unknown (or does not exist)
def ha_is_unknown(entity_id: str): 
    if state.exist(entity_id): # State exists?
        return state.get(entity_id).is_unknown() # Check if the state is unknown (or None)
    else:
        return False # State does not exist so it is not unknown (return False)

# Check if a Home Assistant State is unavailable (or does not exist)
def ha_is_unavailable(entity_id: str):
    if state.exist(entity_id): # State exists?
        return state.get(entity_id).is_unavailable() # Check if the state is unavailable (or None)
    else:
        return False # State does not exist so it is NOT unavailable (return False)

def ha_has_value(entity_id: str): 
    if state.exist(entity_id): # State exists?
        return state.get(entity_id).has_value() # Check if the state has a value (not unknown and not unavailable)
    else:
        return False # State does not exist so it has no value (return False)

def ha_has_value_extra(entity_id: str): 
    if state.exist(entity_id): # State exists?
        value = state.get(entity_id) 
        if isinstance(value, str): value = value.strip() # remove leading and trailing spaces
        return value not in ["unknown", "unavailable", ""] # Check if the state has a value (not unknown and not unavailable and not blank)
    else:
        return False # State does not exist so it has no value (return False)

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
    Warning: Use ha_entity_exist for separate handling of entities that do not exist (this function will throw an exception or return the default when raise_error is False)
    """
    state_value, error_msg = NONAME_STATE, None # Initial value is not the default (NONAME_STATE will be returned when no entity id specified)
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

        log.error(f"[{HELIOS_HASS_NAME}-HA-Get-State] Exception: {error_msg}")
        state_value = default_value # Usually: FAILED_STATE
    
    if error_msg and raise_error:
        raise ValueError(error_msg) # Raise a (new) exception with the error message (instead of returning the default value)
        
    return str(state_value) if (state_value != None) else None # Always return as string unless None

# Get Text from Home Assistant Entity State 
# For an non existing Entity an error will occur.
def ha_get_text(entity_id, default_value: str = None, ignore_undefined: bool = True, raise_error: bool = False) -> str: 
    """ 
    Get Text from Home Assistant Entity State
    By default "unknown" or "unavailable" values will return None but when ignore undefined is False the values will be returned as-is.
    Warning: Use ha_entity_exist for separate handling of entities that do not exist (this function will throw an exception or return the default when raise_error is False)
    """
    state_value, error_msg = None, None
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

        log.error(f"[{HELIOS_HASS_NAME}-HA-Get-Text] Exception: {error_msg}")
        state_value = default_value
            
    if error_msg and raise_error:
        raise ValueError(error_msg) # Raise a (new) exception with the error message (instead of returning the default value)

    return str(state_value) if (state_value != None) else None # Always return as string unless None

# Get Float from Home Assistant Entity State (copied from state_get_float in _batmgt_util.py)
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_get_float(entity_id: str, default_value: float = None, ignore_undefined: bool = True, raise_error: bool = False) -> float:
    """
    Get a float value for a Home Assistant state value. 
    By default "unknown" or "unavailable" values will return None but when ignore undefined is False an exception will be thrown.
    Warning: For the Anker Output Preset value ignore_undefined MUST be enabled since this value is only used with mode "manual" and may be unknown for other modes.
    Warning: In general For HomeWizard and Anker attribute the state can be temporary unavailable (during startup or for communication errors).
    Warning: Use ha_entity_exist for separate handling of entities that do not exist (this function will throw an exception or return the default when raise_error is False)
    Returns Float Value or None when HA state is unavailable, unknown or for an invalid number (string)!
    """
    state_value, float_value, error_msg = None, None, None
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

        log.error(f"[{HELIOS_HASS_NAME}-HA-Get-Float] Exception: {error_msg}")
        float_value = default_value

    if error_msg and raise_error:
        raise ValueError(error_msg) # Raise a (new) exception with the error message (instead of returning the default value)

    return float_value

def ha_get_bool(entity_id: str, default_value: bool = False, ignore_undefined: bool = True, raise_error: bool = False) -> bool:
    """
    Get a boolean value for a Home Assistant state value. 
    Warning: Use ha_entity_exist for separate handling of entities that do not exist (this function will throw an exception or return the default when raise_error is False)
    """
    state_value, bool_value, error_msg = None, None, None
    try:
        if (entity_id != None): 
            state_value = state.get(entity_id) # Retrieve the state of the HA Entity

        if (state_value in HA_UN_LIST or state_value is None) and ignore_undefined:
            state_value = default_value # Return default_value when ignore undefined and (value is unknown or unavailable or None)

        # Convert the value to bool (only for state_value is 'on')
        bool_value = (state_value == HA_ON) if (state_value != None) else None # Convert from string to bool unless None
#       log.info(f"[{HELIOS_SERVICE_NAME}-ha-get-bool] Boolean Value: {state_value} -> {bool_value}")

    except (Exception) as e: # Conversion Error for Boolean
        if state.exist(entity_id): # Entity exist but Boolean conversion failed?
            error_msg = f"Boolean Conversion Failed for HA Entity '{entity_id}' with value '{state_value}': {repr(e)}"
        else: # Get performed but failed since entity does not exist
            error_msg = f"HA Boolean Entity {entity_id} does NOT Exist!"

        log.error(f"[{HELIOS_HASS_NAME}-HA-Get-Bool] Exception: {error_msg}")
        bool_value = default_value

    if error_msg and raise_error:
        raise ValueError(error_msg) # Raise a (new) exception with the error message (instead of returning the default value)

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
    if ha_entity_exist(entity_id): # Entity exist?
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
def ha_set_state(entity_id: str, value: str = None, new_attributes: dict = None, existing_only: bool = False, **attribs) -> bool:
    updated = False
    if not existing_only or ha_entity_exist(entity_id):
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
    if not existing_only or ha_entity_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(value) # Replace a None value by HA "unknown" ("Onbekend" in Nederlands)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Entity Attribute in Home Assistant Entity
def ha_set_attr(entity_id: str, attr_name: str, value):
    updated = False
    if ha_entity_exist(entity_id): 
        state.setattr(entity_id+'.'+attr_name, value)
        updated = True
    return updated # True when updated

# Set Integer in Home Assistant Entity State (copied from state_set_int in _batmgt_util.py)
# Warning: Battery Management is not yet migrated to helios common functions!
def ha_set_int(entity_id: str, value: int = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_entity_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(int(value)) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Float in Home Assistant Entity State
def ha_set_float(entity_id: str, value: float = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_entity_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else str(float(value)) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Set Boolean in Home Assistant Entity State
def ha_set_bool(entity_id: str, value: bool = None, existing_only: bool = False) -> bool:
    updated = False
    if not existing_only or ha_entity_exist(entity_id):
        if (entity_id != None):
            state_value = HA_UNKNOWN if (value == None) else (HA_ON if value else HA_OFF) # Replace a None value by HA "unknown" ("Onbekend" in NL)
            state.set(entity_id, state_value)
            updated = True
    return updated # True when updated

# Delete a Home Assistant Entity
def ha_delete(entity_id: str) -> bool:
    deleted = False
    if ha_entity_exist(entity_id):
        state.delete(entity_id)
        deleted = True
    return deleted # True when deleted