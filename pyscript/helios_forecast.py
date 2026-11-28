# Module: HELIOS Forecast - Python Function to Parse the |Forecast.Solar service output and generate a Solar Forecast Array (24h or 48h) for today and tomorrow.
# HELIOS is the Home Energy Linear Integrated Optimization Service which used the Helios Forecast data to calculate the Optimal Energy Plan.
#
# The forecast_solar.get_forecast is a service provided by the forecast.solar integration (which is a prerequisite for calling the service).
# The service requires a config_entry which is retrieved from hass. 
#
# Warning: The first config entry found for the forecast_solar domain will be used (typically only one will exists).
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-10-16: JR: v0.92a Create the Helios Solar Forecast parser
#   2026-10-19: JR  v0.92b Added Helios Forecast which calls the forecast_solar.get_forecast services to retrieve the forecast solar hours (not available in an entity of the forecast.solar integration), config entry retrieved from hass
#   2026-10-28: JR  v0.93  First public release with HBC Output (works together with Helios Strategy in HBC)
#   2026-11-04: JR  v0.94b Disabled the resolution="hourly" option of the get_forecast service of Forecast.solar since it is giving some weird results in the last hour of sun (combining two hours)
#   2026-11-05: JR  v0.94b Support for 15-min and 60-min forecasts in Forecast.Solar, so disabling the "hourly" option should not be a problem
#   2026-11-06: JR  v0.94b Improved error handling for Forecast.Solar (helios_forecast.py)
#   2026-11-14: RU  v0.96  Fixed the missing calculation of Total Tomorrow kWh (from Total Tomorrow Wh) in helios_forecast.py (Thanks Rubbere)
#   2026-11-23: JR: V0.96  Using helios_hass.py in /pyscript/modules for state functions (ha_set_state instead of state.set)
#   2026-11-26: JR: V0.96  Added support for Solcast and reorganized Forecast.Solar functions
#   2026-11-26: JR: V0.9.6 Added Home Assistant Datetime Utility functions to Helios Hass (ha_now_ts and ha_now_info), used by Helios Forecast and Helios Services

# Check if imports are enabled (Only Applicable in the Home Assistant PyScript environment):
IMPORTS_FAILED_FOR, HOME_ASSISTANT_FOR = False, False # Imports Not failed yet, Not in HA environment
try:
    import sys  # For sys.path.append() to add the Home Assistant /config/pyscript folder to the path to allow /config/pyscript/helios_python to be found !!!

    try: # Assume we are running in MS Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
        # Home Assistant will not have the home_assistant_mock.py (and the import will FAIL): 
        from home_assistant_mock import * # Import the Home Assistant Mockup for Visual Studio (to allow PyScript testing in Visual Studio)
    except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
        HOME_ASSISTANT_FOR = True
except (ImportError, Exception) as e:
    IMPORTS_FAILED_FOR = True # Allow the helios_services.py to be loaded without imports and report the error later on
    HOME_ASSISTANT_FOR = True # Imports only fail in Home Assistant (usually)

# Determine the environment (Visual Studio or Home Assistant) by importing the Home Assistant Mockup:
if not HOME_ASSISTANT_FOR:
    # Modules used by Visual Studio need to start with 'modules.' since they are always in a sub-folder 'modules'
    from modules.helios_hass import * # Import the Helios Home Assistant functions from folder ./modules/

else: # Assume we are in Home Assistant (since the mockup was not found or imports have failed)
    if not IMPORTS_FAILED_FOR: # Further imports and sys functions only when (HA PyScript) import did not fail
        # Modules used by Home Assistant with PyScript must be in the 'modules' folder of the Home Assistant configuration directory! 
        from helios_hass import * # pyright: ignore[reportMissingImports] # Import the Helios Home Assistant functions WITHOUT specifying the 'modules' folder

        # Add for Home Assistant the Pyscript folder to the system path (not needed for MS Visual Studio since the main folder is already in the path)
        # Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)
        if "/config/pyscript" not in sys.path: # Pyscript Folder already in the search path?
            sys.path.append("/config/pyscript") # Add the Home Assistant Pyscript folder to the system path

# Pure Python Files must be in the sub-folder helios_python 
# In HA: pyscript/helios_python (/config/pyscript must have been appended to the sys.path),
# In VS: c:\$code\VisualStudio2026\HeliosOptimizer\helios_python)
if not IMPORTS_FAILED_FOR: 
    from helios_python.helios_common import * # Import the Pure Python Helios Common Functions 

HELIOS_FORECAST_NAME       = 'Helios Optimizer Solar Forecast'                # Name of the Helios Optimizer Solar Forecast

HELIOS_FORECAST_SOLAR      = 'pyscript.helios_optimizer_forecast_solar_data' # Sensor filled from existing Forecast.Solar integration and service
HELIOS_FORECAST_SOLAR_NAME = 'Helios Optimizer Forecast.Solar Data (60-min) from Integration Service'
HELIOS_SOLCAST             = 'pyscript.helios_optimizer_solcast_data' # Sensor filled from existing Solcast integration and service
HELIOS_SOLCAST_NAME        = 'Helios Optimizer Solcast Data (30-min) from Integration Service' 

FORECAST_SOLAR_NAME        = 'forecast_solar' # Config Name Forecast.Solar Integration (used to retrieve the Config Entry ID for the forecast_solar.get_forecast service)
FORECAST_SOLAR_DATA_ATTR   = 'wh_period'  

SOLCAST_DATA_ATTR          = "data"
SOLCAST_START_ATTR         = "period_start"
SOLCAST_ESTIMATE_ATTR      = "pv_estimate"

FORECAST_MSG_ATTR          = "message"
FORECAST_RUN_ATTR          = "run_time"
FORECAST_DATA_ATTR         = "result"
FORECAST_PERIOD_ATTR       = "period_kwh"
FORECAST_START_ATTR        = "start"
FORECAST_END_ATTR          = "end"
FORECAST_DAYS_ATTR         = "days"
FORECAST_INTER_ATTR        = "interval"
FORECAST_TOT_WH_ATTR       = "days_wh"
FORECAST_TOT_KWH_ATTR      = "days_kwh"

# Retrieve the Solar Forecast per Period using a service (forecast_solar.get_forecast and Solcast.query_forecast_data).
# The service runs at the whole hour including at the start of the day. This way the forecast array from a previous day is always refreshed at the start of a new day.
# Helios requires the (simple) forecast array to start at today. By running Helios Optimizer Service at 1 min past the hour this is enforced.
# The forecasts are stored in two Helios Optimizer Entities for Forecast.Solar and Solcast.
# A message is available in the attributes of both the Forecast Entities (for success and for errors). 
# Helios will pass on the error message the Helios Dashboard when it finds no forecast while solar is enabled.
# Warning: An error in the forecast retrieval or parsing will only reset the forecast array when the estimates are not for today. 
# Note: The error message is available in the Entity but will not be displayed on the Helios Dashboard until the forecast is reset.
# Note: The state value of the Entity will be 'unavailable' for errors (but the forecast array may still be available).
@time_trigger("startup")
@time_trigger("cron(0 * * * *)") 
@service(supports_response="optional")
def helios_optimizer_retrieve_solar_forecasts(
    now_ts_str: str         = None               , # Timestamp to select the solar forecast data (Use default is None to retrieve data for today and tomorrow)
    config_entry_name: str  = FORECAST_SOLAR_NAME, # Forecast Solar Name (needed to retrieve the Config Entry Id)
    config_entry_id         = None               , # Forecast Solar Entry Id (when already an Entry Id is available)
    max_days: int           = 2                  , # Retrieve two days by default (today and tomorrow)
    return_response         = None               , # Return a result (Must be a dictionary!)
):
    # Determine which dates to use for today and tomorrow (using the Home Assistant Date Utility or regular datetime when in Visual Studio):
#   now_ts_str = '2026-11-27 23:23+01:00' # Testing a fixed date in Home Assistant (see also helios_main.py)
    today_ts = ha_now_ts(now_ts_str) # Get now from Home Assistant Datetime Utility (or from the regular Datetime when Datetime Utility is not available or fails)
#   today_ts, today_tz, today_off_min  = ha_now_info(now_ts_str) # Get Now, Timezone Info and Offset in Minutes from Home Assistant Datetime Utility (or from the regular Datetime when Datetime Utility is not available or fails)
    run_time_str = datetime_string(today_ts) # YYYY-MM-DD HH:MM:SS
    today_ts = today_ts.replace(tzinfo=None) # Remove timezone info (need local time)
    today_ts = today_ts.replace(hour=0, minute=0, second=0, microsecond=0) # Start of the day (today)
    tomorrow = today_ts + timedelta(days=1) # Start of the day (tomorrow)

    # Retrieve the forecasts from Forecast.Solar and Solcast using a Service provided by the Integrations:
    # Forecast.Solar will provide a forecast for today and optionally tomorrow and Solcast will provide a forecast for x days (default is 2 days: today and tomorrow)
    forecast_solar_response = retrieve_forecast_solar_data(today_ts, tomorrow, run_time_str, max_days=max_days, config_entry_name=config_entry_name, config_entry_id=config_entry_id) # Retrieve the Solar Forecast per Hour using a service (forecast_solar.get_forecast      ) of the Forecast.Solar Integration)
    solcast_response        = retrieve_solcast_data       (today_ts, tomorrow, run_time_str, max_days=max_days) # Retrieve the Solar Forecast per Hour using a service (solcast_solar.query_forecast_date) of the Solcast Integration)
    return {"forecast_solar": forecast_solar_response, "solcast": solcast_response}

# RETRIEVE Forecast.Solar Estimates using the 'Get Forecast' Service for a Configuration ID
def retrieve_forecast_solar_data(today: datetime, tomorrow: datetime, run_time_str: str = None, max_days: int = 2, config_entry_name: str = None, config_entry_id: str = None):
    """
    Retrieve Forecast Data from the Forecast.Solar Integration and built a standard response for Helios Optimizer.
    The Forecast.Solar integration provides entities with forecasts for today and tomorrow, this hour, next hour but does not have a entity with an solar forecast array with a forecast for each hour (or 15 min).
    This hour data is available locally but needs to be accessed via the service.
     Config Entry is required in the service call (we assume there is only one and use the first one provided by hass).
    Trigger every full hour and at startup of home assistant (Solar Forecast Output Entity needs to be recreated after a restart of pyscript)
    It is important to run on a new day at 00:00 before the Helios Optimizer since otherwise the Optimizer will use an incorrect day!
    https://www.home-assistant.io/actions/forecast_solar.get_forecast/ - Home Assistant Service to get the Hour Data from the Forecast.Solar Integration (entities only have limited data)
    https://www.home-assistant.io/integrations/forecast_solar - Home Assistant Forecast.Solar Integration that calls the forecast.solar API
    https://doc.forecast.solar/doku.php?id=api:estimate  - Documentation for forecast.solar API
    See (Development) Tools -> Actions, Select Action: forecast_solar.get_forecast, Select Integration (Service): e.g. My Home
    Display as YAML: This will show the config_entry_id !!!!
    """
    solar_response, forecast_response = None, None # Responses not yet available
    failed, silent, error_msg, entity_msg, today_total_kwh = False, False, None, None, 0.0

    # *** GET *** the Configuration ID for the Forecast.Solar Service
    # The Service (forecast_solar.get_forecast) requires an Config Entry Id
    # We retrieve it from the hass config entries for the forecast_solar entry name and take the first one 
    # This will then be using the Forecast.Solar configuration with Declination, Azimut and Total Peakpower of the solarpanels (as configured in HA Forecast.Solar)
    if not config_entry_id: # Not already a Config Entry Id?
        entries = hass.config_entries.async_entries(config_entry_name)   
        if entries and (len(entries) > 0):
            config_entry_id = entries[0].entry_id
        log.info(f"Found {len(entries)} Forecast.Solar Config Entry ID: '{config_entry_id}'") # Config Entry Found!

    if not config_entry_id: # No Config Entry ID found?
        error_msg = f"No active Forecast.Solar Config Entry ID found in Home Assistant for '{config_entry_name}'!" 
        silent = True # The User may not have configured the integration (no error in the log needed, message will be set in the forecast entity)
    
    # *** RETRIEVE *** the Forecast using the Forecast.Solar SERVICE:
    else: # Config Entry Found for Forecast Solar:
        # Call the Solar Forecast Service with the dynamically found Config Entry ID:
        # Returns periods with forecast (includes start of the period and a Watt Hours number), before HA2026.11 the end of the period was returned
        try:
            start_str = datetime_short(today                    , HA_TS_FORMAT) # YYYY-MM-DD 00:00:00 (today is already start of day)
            end_str   = datetime_short(today + timedelta(days=2), HA_TS_FORMAT) # YYYY-MM-DD 00:00:00 (two days later at 00:00)
            solar_response = forecast_solar.get_forecast(
                config_entry=config_entry_id,
        #       resolution="hourly", # Return hourly data (replaces sunrise with start of hour and removes sunset since it was 0 any way), Note before HA2026.11 this was different and sunset was combined in a strange way
        #       resolution="raw"   , # Default is raw. Free account only has hourly but a paid account could return 15-min
                start=start_str, # Default is today and tomorrow!
                end=end_str,
                return_response=True,
            )

            # PARSE the response from the Forecast.Solar Service:
            if solar_response: # Forecast.Solar Response available?
                forecasts_watt_hour, days_total_wh, available_days, step_size, found_today, found_tomorrow, error_msg = parse_forecast_solar(solar_response, today, tomorrow, max_days)
            else: # The Service Response is Empty (None): 
                error_msg = f"Forecast.Solar Get Forecast Service returned no response for {start_str}-{end_str}!" 

        except Exception as e: # Service Failed/Not Available or an other Exception during parsing
            error_msg = f"Get Forecast Service of Forecast.Solar failed: {repr(e)}"
            solar_response = None # Forecast data will not be procesed when the service call failed (error_msg will be set))

    # *** BUILT *** a single Forecast.Solar Array (for today and tomorrow):
    if error_msg is None: # No errors found?
        forecast_response, today_total_kwh = built_forecast_array(
            today, forecasts_watt_hour, days_total_wh, available_days, step_size
        )
        entity_msg = f"Forecast.Solar Data Retrieved for {datetime_short(today)}" # Success Message
    else: # Errors found (in retrieval or parsing):
        entity_msg = error_msg
        failed = True

    # *** UPDATE *** the Helios Forecast.Solar Sensor with the new Forecast Data (only when successfully retrieved and parsed):
    forecast_response = update_forecast_sensor(HELIOS_FORECAST_SOLAR, HELIOS_FORECAST_SOLAR_NAME, failed, silent, today_total_kwh, forecast_response, entity_msg, today, run_time_str)
#   return response # Return the parsed service response or an error message
#   return forecasts_watt_hour # Return the parsed service response or an error message
    return forecast_response # Return the parsed service response or an error message

# RETRIEVE Solcast Estimates using the Get Forecast Service
def retrieve_solcast_data(today: datetime, tomorrow: datetime, run_time_str: str = None, max_days: int = 2):
    """
    Retrieve Forecast Data from the Solcast Integration and built a standard response for Helios Optimizer.
    Typically the Solcast data will be for 2 days (today and tomorrow) and will use an interval (step size) of 30 minutes.
    The Response is returned by the function but also stored in a PyScript Helios Optimizer Solcast Data Entity.
    The PyScript Entity is not predefined in yaml but created by the pyscript function when necessary (Entity is lost with a HA restart).
    The structure of the attributes of the Helios Entity is the same for the Forecast.Solar and the Solcast integrations.
    Warning: PyScript Entity Result Attribute is only reset to empty {} when an error occurs AND the existing result is NOT from today!
      However the PyScript Entity State will be set to 'unavailable', an Error Message in the Entity will be set and the Run Time is updated.
      The data from a previous successfull call is still available when for today: Helios will continue to run without an error (Message only available in the Entity).
    No specific handling of summertime/wintertime changes (shift of one hour: 25 hour or 23 hour day) are implemented at the moment (to be investigated how solcast handles this)!

    Test Cases: Using Mockup Data
    V Service returns data for today (2026-10-20) and tomorrow (2026-10-21) in 30-min steps with max_days=2, checked 08:00, 08:30 & 16:00 slot arrive correctly in Helios for both days (Helios 30-min steps), 2 days (30.7 and 26.0 kWh)
    V Service returns data for today (2026-10-20), tomorrow (2026-10-21) and day-after (2026-10-22) in 30-min steps with max_days=3, Power kW correctly converted to Energy kWh (x0.5 for 30-min slots), 3 days (30.7, 26.0, 2.2)
    V Service returns data for today (2026-10-21), 2 days (26.0, 2.2 kWh) since the mockup contains data for 20/21/22-okt, data for yesterday is correctly skipped when still present
    V Service returns data for today (2026-10-22), 1 day only (2.2 kWh) since the mockup contains data for 20/21/22-okt (and not for 23-okt), data for past days is correctly skipped when still present
    V Service returns data for today (2026-10-23), no data returned since only past data is available
    V Service returns data for today (2026-10-19), 3 days (0.0 (no data for 19-okt so all zero), 30.7 and 26.0)
    V Service 'Solcast - Query Forecast Data' is not available/defined -> Error Displayed to install the integration
    V Service is missing a parameter (e.g. end_date_time) -> Error: Parameter is missing
    V Parse of the Data fails ('data2', empty data, invalid structure) -> State: unavailable, Error: Invalid structure
    V Fields not found ('period_start2', 'pv_estimate2') -> State: unavailable, Error: no (valid) estimate records
    V Error and Start is today -> Existing Data remains but State: unavailable and Error Message in the Entity
    V Error and Start is not today -> Existing Data removed, unavailable and Error Message Displayed on Helios
    """
    solcast_response, forecast_response = None, None # Responses not yet available
    failed, silent, error_msg, entity_msg, today_total_kwh = False, False, None, None, 0.0

    try:
        # *** RETRIEVE *** the Forecast using the Solcast SERVICE:
        domain, service = 'solcast_solar', 'query_forecast_data' # Domain and Service (for the exist check)
        if ha_service_exist(domain, service): # Does the Service exist (is the Integration is installed)?
            # Solcast Service: Query Forecast Data for today 00:00 until today+2 00:00
            start_str = datetime_short(today                       , HA_TS_FORMAT) # YYYY-MM-DD 00:00:00 (today is already start of day)
            end_str   = datetime_short(today + timedelta(days=max_days), HA_TS_FORMAT) # YYYY-MM-DD 00:00:00 (two days later at 00:00)
            # hass.services.call(domain, service, data, blocking=True)
            solcast_response = solcast_solar.query_forecast_data(
                start_date_time=start_str, # Default is today and tomorrow!
                end_date_time=end_str,
                return_response=True,
            )

            # *** PARSE *** the response from the Solcast Service:
            if solcast_response: # Solcast Response available?
                forecasts_watt_hour, days_total_wh, available_days, step_size, found_today, found_tomorrow, error_msg = parse_solcast_forecast(solcast_response, today, tomorrow, max_days)
            else: # The Service Response is Empty (None): 
                error_msg = f"Solcast Query Forecast Data Service returned no response for {start_str}-{end_str}!" 
        else: # Service does not exist
            error_msg = "Solcast Integration Service (Query Forecast Data) does not exist. Select another Solar Forecast Source or install Solcast!"
            silent = True # The User may not have installed the integration (no error in the log needed, message will be set in the forecast entity)

    except Exception as e: # Service Failed/Not Available or an other Exception during parsing
        error_msg = f"Solcast Query Forecast Data Service failed with an Exception: {str(e)}"
        solcast_response = None # Forecast data will not be procesed when the service call failed (error_msg will be set))

    # *** BUILT *** a single Solcast Array (for today and later) and Update the Solar Forecast Sensor:
    if error_msg is None: # No errors found?
        forecast_response, today_total_kwh = built_forecast_array(
            today, forecasts_watt_hour, days_total_wh, available_days, step_size
        )
        entity_msg = f"Solcast Data Retrieved for {datetime_short(today)}" # Success Message
    else: # Errors found (in retrieval or parsing):
        entity_msg = error_msg
        failed = True

    # *** UPDATE *** the Helios Solcast Sensor with the new Forecast Data (only when successfully retrieved and parsed):
    forecast_response = update_forecast_sensor(HELIOS_SOLCAST, HELIOS_SOLCAST_NAME, failed, silent, today_total_kwh, forecast_response, entity_msg, today, run_time_str)
    return forecast_response # Return the parsed service response including a message and a run-time string

# PARSE Forecast.Solar Response:
def parse_forecast_solar(response, today: datetime, tomorrow: datetime, max_days: int = 2):
    """
    Parse the response from Forecast.Solar:
    The Solar Forecast response only contains hours (or 15-min periods) with sun
    The Solar Forecast REST API returns the first slot starting at sunrise (e.g. 08:19 instead of 08:00) for sun between 08:00-08:19, usually 0, next slot is 09:00 for sun between 08:19-09:00
    The Solar Forecast REST API returns the last slot starting at sunset   (e.g. 18:29 instead of 19:00) for sun between 18:00-19:00
    WARNING: In mode "hourly" the sunrise hour is changed to the start of the hour (e.g. from 08:19 to 08:00) and the sunset hour is combined with the previous hour (e.g. 18:00 and 18:29 are now both in 18:00, makes sense since 18:29 should be 0)
    """
    found_today, found_tomorrow, available_days, step_size = False, False, 0, None # No days found yet, step size unknown
    forecasts_watt_hour, days_total_wh = {}, [] # Start with an empty Dictionary for the forecast array, totals (Wh) empty
    error_msg = None

    if not response:
        error_msg = f"Forecast.Solar Response is empty!" 
    elif not isinstance(response, dict):
        error_msg = f"Forecast.Solar Response is invalid (Not a Dictionary)!" 
    else: # Response is valid?
        entries = response.get(FORECAST_SOLAR_DATA_ATTR, None) # Limit the response handling to the Watt Hours per Hour
        if entries is not None and isinstance(entries, dict) and len(entries) > 0: # wh_period is valid?
            try:
                ts_keys, prev_period_ts = list(entries.keys()), None
                if len(ts_keys) >= 3: # Enough forecast periods to determine the step size
                    step_size = int((datetime.fromisoformat(ts_keys[2]) - datetime.fromisoformat(ts_keys[1])).total_seconds() / 60) # Step Size in Minutes (comparing the 3rd and 2nd timestamp in the forecast)
                else: # Should not happen but assume default of 60 min as step size
                    step_size = 60
                
                for ts_str in ts_keys: # For each timestamp_str of the forecast keys
                    try:
                        period_ts = datetime.fromisoformat(ts_str) # Get the datetime for the key (which is the datetime START of the period), JR2026-11-13: Input now has START of period instead of END of period!
                        period_ts = period_ts.replace(tzinfo=None) # Remove the timezone
                    except Exception as e:
                        raise ValueError(f"Forecast.Solar Period '{ts_str}' is invalid!'")
                    
                    base_ts = period_ts.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of the day
                    dt_index = int((period_ts - base_ts).total_seconds() / 60) // step_size # Determine the index of the period in the day (from the timestamp at the START of the period), JR2026-11-13: Removed -1 (forecast now has timestamp of start of the period)
                    period_start_ts = base_ts + timedelta(minutes=dt_index * step_size)    # Determine the start of the period for the dt (dt - step_size, adapted for sunset and sunrise periods)
                    if (period_start_ts == prev_period_ts): # for sunset the period start is the same as the previous period
                        period_start_ts = period_start_ts + timedelta(minutes=step_size) # Add an additional period for sunset (e.g. sunset at 18:29 and step size is 60min then next period start is 19:00), JR2026-11-20: This extra period should no longer occur from the HA 2026.11 release
                    
                    # Convert the Solcast Power Estimate (in kW) to Energy for the Period (in Wh):
                    try:
                        estimate_wh_str = entries.get(ts_str, None)
                        forecast_wh = float(estimate_wh_str) if estimate_wh_str else 0.0 # Convert to float (simple since already in Wh)
                    except Exception as e:
                        raise ValueError(f"Forecast.Solar Estimate {estimate_wh_str} for period '{datetime_short(period_start_ts)}' is invalid!'")
                    
                    # Determine the day index (compared to today, today is 1)
                    # For a new day: Append a new day total and initialize the day total to 0.0 (initialize multiple totals when days are skipped)
                    day_index = (period_start_ts.date() - today.date()).days + 1 # Day index 1, 2, 3, ... (Day 0 is yesterday)
                    if available_days < day_index <= max_days: # Found a new day (only for today and later)
                        for day in range(available_days+1, day_index+1): # once for each extra day (usually only one day) 
                            days_total_wh.append(0.0) # initialize a new day total
                            available_days += 1 # Increase the available days when day index is higher

                    if period_start_ts.date() == today.date(): # Is this a forecast for today? 
                        found_today = True 
                    elif period_start_ts.date() == tomorrow.date(): # Is this a forecast for tomorrow? 
                        found_tomorrow = True 

                    # For days at or after today: Add the energy estimate to the total for the day and add the forecast to the forecasts
                    if (0 < day_index <= max_days): # Today or Tomorrow (Ignore Days in the past)
                        days_total_wh[day_index - 1] += forecast_wh # Sum the total for the day (today and tomorrow)
                        forecasts_watt_hour[period_start_ts] = forecast_wh # Built an dictionary with key Timestamp and value Estimate (Wh instead of Watt)

                    prev_period_ts = period_start_ts
    #               print(f"Price {period_start_ts}: {forecasts_watt_hour[period_start_ts]}")

                if len(forecasts_watt_hour) <= 0: # No valid estimates found
                    error_msg = "Forecast.Solar Data has no (valid) estimates!"

            except Exception as e: # Exception (e.g. invalid date or float)
                error_msg = f"Forecast.Solar parsing failed: {str(e)}!" 
                forecasts_watt_hour = {}
                found_today, found_tomorrow, today_total_wh, tomorrow_total_wh = False, False, 0.0, 0.0

        else:
            error_msg = f"Forecast.Solar '{FORECAST_SOLAR_DATA_ATTR}' does not exist, has invalid structure (not a dictionary) or is empty!"

    return (forecasts_watt_hour, days_total_wh, available_days, step_size, found_today, found_tomorrow, error_msg)

# PARSE Solcast Response:
def parse_solcast_forecast(response, today: datetime, tomorrow: datetime, max_days: int = 2, estimate_key: str = SOLCAST_ESTIMATE_ATTR):
    """
    Parse the solar forecast data returned from the Solcast Service 
    Stop processing when there is no response or an invalid response (not a dictionary)
    Stop processing when when data attribute is missing, data has invalid structure (not a tuple) or has no entries
    Determine the step size based upon the time difference between the first two entries in the response.
    For each entry in the data:
    - An entry is skipped: when it is not a dictionary and/or the required attributes are missing
    - Processing is stopped when an entry contains invalid data (invalid timestamp or estimate)
    - Period start time is determined (and rounded down to a step start time when needed)
    - Power Estimate (kW) is converted to Energy (Wh) by multiple with 1000 and by hours_factor (= step_size / 60), e.g. for 30 min: Wh = 1000 * 0.5 kW = 500 * kW
    - Total Wh is counted per day (for each day a separate counter is initialized)
    - Entries in the past are ignored/surpressed and no totals are calculated for these days (only today and later are valid entries)
    Typically the data should contain entries for today and later but when only later entries are available this is allowed (in a later process entries with zeros will be inserted for days before the first entry)
    An error message is set when processing is stopped (invalid structure or invalid entry) or when no entries exist or no valid entries are found
    If an error is found the forecast is empty and the error message is set 
    If no errors are found the error message will be None and the forecast will be filled (with at least one entry for today or later)
    Return a dictionary with the forecast (timestamps with energy estimate), day totals, available days (today and later), boolean for today and tomorrow found and optional error message
    """
    found_today, found_tomorrow, found_extra_days, found_old = False, False, False, False
    available_days, step_size = 0, None # No days found yet, step size unknown
    forecasts_watt_hour, days_total_wh = {}, [] # Start with an empty Dictionary for the forecast array, totals (Wh) empty
    error_msg = None

    if not response:
        error_msg = "Solcast Response is empty!" # Should not happen since this is already handled earlier
    elif not isinstance(response, dict):
        error_msg = "Solcast Response is invalid (not a dictionary)!"
    else:
        entries = response.get(SOLCAST_DATA_ATTR, None)
        if entries is not None and isinstance(entries, tuple) and len(entries) > 0:
            try:
                # Determine the step size in minutes based on the first two items:
                step_size = 30 # Default step size
                if len(entries) >= 2:
                    try:
                        period_start0 = entries[0][SOLCAST_START_ATTR]
                        period_start1 = entries[1][SOLCAST_START_ATTR]
                        ts_0 = datetime.fromisoformat(period_start0) if not isinstance(period_start0, datetime) else period_start0
                        ts_1 = datetime.fromisoformat(period_start1) if not isinstance(period_start1, datetime) else period_start1
                        step_size = int((ts_1 - ts_0).total_seconds() / 60)
                        if step_size <= 0: step_size = 30
                    except Exception as e: # Failed to determine the step size
                        pass # Use the default step size in case of step size calculation errors

                hours_factor = step_size / 60.0  # Hours for a step (e.g. 0.5 for 30 min, 1.0 for 60 min)
                for item in entries: # For each estimate in the forecast entries:
                    if not isinstance(item, dict) or (SOLCAST_START_ATTR not in item) or (estimate_key not in item):
                        continue # Skip an invalid item and go to the next item

                    # Parse the Period start timestamp: 
                    try:
                        period_ts_str = item.get(SOLCAST_START_ATTR, None)
                        if not isinstance(period_ts_str, datetime): # Not yet a datetime (mockup returns a date string)
                            period_ts = datetime.fromisoformat(period_ts_str) # convert from iso datetime format to datetime
                        else: # Already a datetime (Solcast service returns datetimes, not strings)
                            period_ts = period_ts_str # Already a datetime
                        period_ts = period_ts.replace(tzinfo=None)
                    except Exception as e:
                        raise ValueError(f"Solcast Period Start '{period_ts_str}' is invalid!'")
                        
                    # Convert the period start timestamp to a timestap at the start of a step (usually this will be the same):
                    base_ts = period_ts.replace(hour=0, minute=0, second=0, microsecond=0)  # Calculate start of the day for the period start
                    dt_index = int((period_ts - base_ts).total_seconds() / 60) // step_size # Calculate the day index for the period start (rounds down to a step size start)
                    period_start_ts = base_ts + timedelta(minutes=dt_index * step_size)     # Move to a step size start of the period (usually this is the same as the period start)

                    # Convert the Solcast Power Estimate (in kW) to Energy for the Period (in Wh):
                    try:
                        estimate_kw_str = item.get(estimate_key, None)
                        forecast_wh = (float(estimate_kw_str) if estimate_kw_str else 0.0) * 1000.0 * hours_factor # Convert to float and from kw to Wh (e.g. for 30-min and 1.0 kW -> 1.0 kW * 1000 * 0.5h = 500 Wh)
                    except Exception as e:
                        raise ValueError(f"Solcast Estimate {estimate_kw_str} for period '{datetime_short(period_start_ts)}' is invalid!'")

                    # Determine the day index (compared to today, today is 1)
                    # For a new day: Append a new day total and initialize the day total to 0.0 (initialize multiple totals when days are skipped)
                    day_index = (period_start_ts.date() - today.date()).days + 1 # Day index 1, 2, 3, ... (Day 0 is yesterday)
                    if available_days < day_index <= max_days: # Found a new day (only for today and later)
                        for day in range(available_days+1, day_index+1): # once for each extra day (usually only one day) 
                            days_total_wh.append(0.0) # initialize a new day total
                            available_days += 1 # Increase the available days when day index is higher
                    
                    # Determine the day type (today, tomorrow, later or earlier):
                    if period_start_ts.date() == today.date():
                        found_today = True
                    elif period_start_ts.date() == tomorrow.date():
                        found_tomorrow = True
                    elif period_start_ts.date() > tomorrow.date():
                        found_later = True
                    else: # period_start_ts.date < today.date()
                        found_old = True # Note: These entries will be skipped

                    # For days at or after today: Add the energy estimate to the total for the day and add the forecast to the forecasts
                    if (0 < day_index <= max_days): # Today or later? (Ignore Days in the past)
                        days_total_wh[day_index - 1] += forecast_wh # Sum the total for the day (today, tomorrow but also extra days)
                        forecasts_watt_hour[period_start_ts] = forecast_wh # Built an dictionary with key Timestamp and value Estimate (Wh instead of Watt)

                if len(forecasts_watt_hour) <= 0: # No valid estimates found
                    error_msg = "Solcast Data has no (valid) estimates!"

            except Exception as e: # Reset any intermediate result
                error_msg = f"Solcast Data parsing failed: {str(e)}!"
                found_today, found_tomorrow, available_days, step_size = False, False, 0, None
                forecasts_watt_hour, days_total_wh = {}, []
                
        else:
            error_msg = f"Solcast '{SOLCAST_DATA_ATTR}' does not exist, has invalid structure (not a tuple) or is empty!"

    return (forecasts_watt_hour, days_total_wh, available_days, step_size, found_today, found_tomorrow, error_msg)

# BUILT the Forecast Array for the forecast estimates from Forecast.Solar and Solcast:
def built_forecast_array(today: datetime, forecasts_watt_hour: dict, days_total_wh: list, available_days: int, step_size: int) -> dict:
    """
    Built a single Solar Forecast Array from the parsed data (assumes that data from yesterday and earlier is already removed in the parsing).
    Additional Attributes are Totals per day in Wh and in kWh, Start and End Datetime of the Forecast
    The array will have elements per step for each of the available days (e.g. for today and tomorrow with step size of 30 min: 96 = 2 days x 24 hours * 2 steps per hour)
    The array will be empty when only data before today is available!
    When only future days (after today) are available then the array will have zeros from today until the available day.
    Typically only 2 days will be available but for example solcast can provide more days (which can be usefull when a longer optimization period is used, not used yet).
    """
    forecast_response = {
#       FORECAST_MSG_ATTR: None, FORECAST_RUN_ATTR: None, # These attributes will be added to the response later since they are handled differently (especially when the service or parsing has failed)
        FORECAST_DATA_ATTR: {FORECAST_PERIOD_ATTR: [], FORECAST_START_ATTR : None, FORECAST_END_ATTR: None, FORECAST_DAYS_ATTR: 0, FORECAST_INTER_ATTR: None, FORECAST_TOT_WH_ATTR: {}, FORECAST_TOT_KWH_ATTR: {} }
    }

    # Totals for available days:
    today_total_kwh = 0
    for day_index in range(1, available_days + 1):
        day = today + timedelta(days=day_index-1)
        day_str = date_string(day)
        day_total_wh  = days_total_wh[day_index-1]
        day_total_kwh = day_total_wh / 1000 # Convert from Wh to kWh
        if (day_index == 1): today_total_kwh = day_total_kwh # Keep the total for today (will be stored in the state value)
        forecast_response[FORECAST_DATA_ATTR][FORECAST_TOT_WH_ATTR ][day_str] = int  (day_total_wh    ) # Total Wh today (integer)
        forecast_response[FORECAST_DATA_ATTR][FORECAST_TOT_KWH_ATTR][day_str] = round(day_total_kwh, 1) # Total kWh today (float, 1 decimal)
   
    # Built a Forecast Array for today and optionaly future days:
    if available_days > 0: # Remark: If only tomorrow found then today will be zero's
        start_time = today.replace(hour=0, minute=0, second=0, microsecond=0) # Start of today (00:00)
        forecast_response[FORECAST_DATA_ATTR][FORECAST_INTER_ATTR] = step_size
        forecast_response[FORECAST_DATA_ATTR][FORECAST_START_ATTR] = datetime_short(start_time)
        end_time = start_time + timedelta(days = available_days) # 1 or 2 days (or 0 when forecast for incorrect days)

        current_time = start_time # Start at the first hour of today (00:00)
        while current_time < end_time: # For each period (hour, 60min or 15min) of today and optionally tomorrow
            forecast_kwh = round(forecasts_watt_hour.get(current_time, 0.0) / 1000, 5) # Get the forecast for the hour (or 0 when not available in the early or late hours)
            forecast_response[FORECAST_DATA_ATTR][FORECAST_PERIOD_ATTR].append(forecast_kwh)
            current_time += timedelta(minutes=step_size) # Next period
            
        forecast_response[FORECAST_DATA_ATTR][FORECAST_END_ATTR ] = datetime_short(current_time)  
        forecast_response[FORECAST_DATA_ATTR][FORECAST_DAYS_ATTR] = available_days
    
    return (forecast_response, today_total_kwh)

# UPDATE the Forecast Sensor (for Forecast.Solar and Solcast):
def update_forecast_sensor(entity_id: str, friendly_name: str, failed: bool, silent: bool, today_total_kwh, forecast_response: dict, entity_msg: str, today: datetime, run_time_str: str): 
    """
    Update the Forecast Sensor: State Value and Attributes (Message, Run-Time and Result)
    Special processing will occur when the retrieval or parsing of the forecast data has failed
    The Forecast Result will be reset ONLY when the existing data is no longer for today!
    This will the Helios Optimizer to continue when the forecast service is temporarily not available.
    The Message and Run-Time will always be updated and will reflect the lastest retrieval and parsing status!
    """
    # Check if Retrieval or Parsing of the Forecast has failed: Log the Error, Reset the Forecast Array but only
    update_previous_forecast = True # Only disabled in case of errors when the previous forecast is still valid (for today)
    if failed: # Errors found (in retrieval or parsing):
       forecast_response = {FORECAST_DATA_ATTR: {} } # Reset the current forecast array (unless previous forecast is for today)
        
       # If the existing data is from today then we will keep the data until the end of the day:
       if ha_entity_exist(entity_id): # Earlier Forecast result available in the entity?
            current_result = ha_get_attr(entity_id, FORECAST_DATA_ATTR, None) # Retrieve the existing forecast result attribute (can this still be used for today?)
            current_start  = current_result.get(FORECAST_START_ATTR, None) if current_result else None # Get the current start of the existing forecast result
            try:
#               current_result, current_start = {"some_dummy_result": 'whatever'}, "2026-10-19 00:00" # Dummy previous forecast for testing
                current_start_ts = datetime.fromisoformat(current_start)
                if (current_result and current_start and (current_start_ts.date() == today.date())): # Is current start equal to today?
                    update_previous_forecast = False # Keep the previous forecast result (Do not yet reset the forecast array)!
                    entity_msg += f" Previous forecast for today {datetime_short(today)} is not yet removed!"
                elif current_result: # Previous forecast still available?
                    entity_msg += f" Old forecast for {datetime_short(current_start_ts)} has been removed!"
            except:
                pass # Failed to check if current data is from today       
        
       if silent: # No Config ID found for Forecast.Solar or no Service found for Solcast
           log.info (f"[{HELIOS_FORECAST_NAME}] Info: {entity_msg}" ) # Log info  message (including the info about keeping or removing the previous forecast)
       else: # All other errors will be reported at the error level:
           log.error(f"[{HELIOS_FORECAST_NAME}] Error: {entity_msg}") # Log error message (including the info about keeping or removing the previous forecast)

    # Update the Helios Forecast.Solar (PyScript) Entity (if it does not exist it will be created)
    # Note: The entity is always updated (but under certain conditions the result from the previous forecast will be kept until it is no longer valid)
    ha_set_state( # Update the status and attributes of the Forecast Entity
        entity_id,
        value=round(today_total_kwh, 1) if not failed else HA_UNAVAIL, # State value is total for today in kwh or 'unavailable' when error occured (Warning: previous data may still be available!)
        friendly_name=friendly_name,
        unit_of_measurement="kWh", # Kilo Watt Hour
        device_class="energy",
        message=entity_msg,
        run_time=run_time_str,
        # New Forecast Response (or None when an error occured and previous forecast is for today or {} when previous forecast is old):
        new_attributes=forecast_response if update_previous_forecast else None # New forecast (None will not update the other attributes)
    )

    # For the return response add also the message and the run time string to the response
    # Warning: Forecast Response contains the parsed data from the service (which may be empty when the service or the parsing failed), 
    # The Helios Solcast Entity (as updated above) may still contain a forecast from a previous successfull call
    forecast_response[FORECAST_RUN_ATTR] = run_time_str # Add the run time string also to the forecast response
    forecast_response[FORECAST_MSG_ATTR] = entity_msg   # Add the (entity) message also to the forecast response (can be a error or success message)
    return forecast_response # Return the (adapted) response (includes now run-time and message)
