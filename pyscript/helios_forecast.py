# Module: HELIOS Solar Forecast Parser - Python Function to parse the forecast.solar service output and generate a Solar Forecast Array (24h or 48h) for today or tomorrow
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

import sys  # For sys.path.append() to add the Home Assistant /config/pyscript folder to the path to allow /config/pyscript/helios_python to be found !!!
from datetime    import datetime, timedelta, time, timezone

FORECAST_SOLAR_NAME         = 'forecast_solar'
HELIOS_SOLAR_FORECAST2      = 'pyscript.helios_optimizer_forecast_solar_hours' # Sensor filled from existing forecast.solar integration and service
HELIOS_SOLAR_FORECAST_NAME2 = 'Helios Optimizer Forecast Solar Hours from Integration Service'
HELIOS_FORECAST_NAME        = 'Helios Optimizer Solar Forecast'                # Name of the Helios Optimizer Solar Forecast

# Determine the environment (Visual Studio or Home Assistant):
dt_util = None # Home Assistant Datetime Utility not yet available
try: # Assume we are running in Visual Studio and not in Home Assistant (HA) and try to import the home_assistant_mock.py  
    # Do not add the home_assistant_mock.py to the Home Assistant pyscript/helios folder, it is only needed for testing in Visual Studio
    from home_assistant_mock import service, time_trigger, pyscript_compile, log, automation, task, state, hass, forecast_solar  # Include HA mock for testing outside of Home Assistant

except ImportError: # Mock Logger not found (hopefully we are running in Home Assistant)
    # Disabled _LOGGER: Using Home Assistant PyScript log in Helios Services:
#   import logging # Get the standard Python Logging Module (for Home Assistant Logging when the pyscript log is not available)
#   _LOGGER  = logging.getLogger(__name__) # Get access to the HomeAssistant Logger in standard python functions (not needed in helios_services since access to HA log is available)
#   pass  # In Home Assistant no mock is needed since service/state/log etc already exist globally!

    try: # Use Home Assistant Datetime for Price and Forecast Lookups
        import homeassistant.util.dt as dt_util # Get the HA Datetime Utility (especially important for container environments)
    except:
        pass # use OS datetime 
    
if "/config/pyscript" not in sys.path: # Already in the search path for pure python modules in Home Assistant? 
    sys.path.append("/config/pyscript") # Home Assistant Pyscript folder, Makes HA/PyScript search for pure python modules in (e.g. helios in /config/script/helios_python/helios_optimizer.py)

from helios_python.helios_common import * # Import the Pure Python Helios Common Functions 

# Retrieve the Solar Forecast per Hour using a service (forecast_solar.get_forecast) of the Forecast.Solar Integration)
# The Forecast.Solar integration provides entities with forecasts for today and tomorrow, this hour, next hour but does not have a entity with an solar forecast array with a forecast for each hour (or 15 min).
# This hour data is available locally but needs to be accessed via the service.
# A Config Entry is required in the service call (we assume there is only one and use the first one provided by hass).
# Trigger every full hour and at startup of home assistant (Solar Forecast Output Entity needs to be recreated after a restart of pyscript)
# It is important to run on a new day at 00:00 before the Helios Optimizer since otherwise the Optimizer will use an incorrect day!
# https://www.home-assistant.io/actions/forecast_solar.get_forecast/ - Home Assistant Service to get the Hour Data from the Forecast.Solar Integration (entities only have limited data)
# https://www.home-assistant.io/integrations/forecast_solar - Home Assistant Forecast.Solar Integration that calls the forecast.solar API
# https://doc.forecast.solar/doku.php?id=api:estimate  - Documentation for forecast.solar API
# See (Development) Tools -> Actions, Select Action: forecast_solar.get_forecast, Select Integration (Service): e.g. My Home
# Display as YAML: This will show the config_entry_id !!!!
@time_trigger("startup")
@time_trigger("cron(0 * * * *)") 
@service(supports_response="optional")
def helios_optimizer_retrieve_forecast_solar_hours(
    now_ts_str: str         = None               , # Timestamp to select the solar forecast data (Use default is None to retrieve data for today and tomorrow)
    solar_config_entry: str = FORECAST_SOLAR_NAME, # Forecast Solar Name (needed to retrieve the Config Entry Id)
    return_response         = None               , # Return a result (Must be a dictionary!)
):
    config_entry_id, response, error_msg = None, None, None
    forecast_response = {"result": {"hours_kwh": [], "start" : None, "end": None, "interval": None, "days_kw": {}, "days_kwh": {}, "message": None} }

    # The Service (forecast_solar.get_forecast) requires an Config Entry Id
    # We retrieve it from the hass config entries for the forecast_solar entry name and take the first one 
    # This will then be using the Forecast.Solar configuration with Declination, Azimut and Total Peakpower of the solarpanels (as configured in HA Forecast.Solar)
    if not config_entry_id:
        entries = hass.config_entries.async_entries(FORECAST_SOLAR_NAME)   
        if entries and (len(entries) > 0):
            config_entry_id = entries[0].entry_id
        log.info(f"Found {len(entries)} Forecast.Solar Config Entry ID: {config_entry_id}")

#   if not config_entry_id:
#       # DID NOT WORK !!!!!!
#       # Search dynamically for the config_entry_id of forecast_solar in the domains of hass.data
#       for domain, data in hass.data.items():
#           if domain == "forecast_solar":
#               # The keys in hass.data["forecast_solar"] are the config_entry IDs!
#               for entry_id in data.keys():
#                   config_entry_id = entry_id
#                   break
#           if config_entry_id:
#               break

#   if not config_entry_id:
#       # DID NOT WORK !!!!!!
#       # Get the state object from hass for an entity of forecast.solar (can be any of the entities)
#       # (For example the sensor for the exepcted production for this day or this month)     
#       target_entity = "sensor.power_production_next_hour"
    
#       # Request the Entity registry via hass
#       state_obj = hass.states.get(target_entity) # Use the registry helper
#       config_entry_id = getattr(state_obj, "config_entry_id", None)
#       if not config_entry_id:
#           attributes = state_obj.attributes or {}
#           config_entry_id = attributes.get("config_entry_id")  

    if not config_entry_id: # No Config Entry ID found?
        error_msg = f"No active Forecast.Solar Config Entry ID found in Home Assistant for {FORECAST_SOLAR_NAME}!" 
    
    else: # Config Entry Found for Forecast Solar:
        # Call the Solar Forecast Service with the dynamically found Config Entry ID:
        response = forecast_solar.get_forecast(
            config_entry=config_entry_id,
            resolution="hourly", # Return hourly data (removes sunrise and sunset times, combines sunset with previous hour)
    #       resolution="raw"   , # Free account only has hourly but a paid account could return 15-min so we ask specically for hour resolution
    #       start="2026-10-13 00:00:00", # Default is today and tomorrow!
    #       end="2026-10-15 00:00:00",
            return_response=True,
        )

        # Determine which dates to use for today and tomorrow:
        if now_ts_str is None: # No specific date specified
            if dt_util is None: # Not in Home Assistant?
                today = datetime.now() # Regular Now
            else: # Home Assistant Environment?
                today = dt_util.now() # Home Assistant Now (Important for container environments)
        else:
            today = datetime.fromisoformat(now_ts_str)
        today = today.replace(tzinfo=None)   
        tomorrow = today + timedelta(days=1)

        # Parse the response from forecast.solar:
        # The Solar Forecast response only contains hours with sun
        # The Solar Forecast REST API returns the first slot starting at sunrise (e.g. 08:19 instead of 08:00) for sun between 08:00-08:19, usually 0, next slot is 09:00 for sun between 08:19-09:00
        # The Solar Forecast REST API returns the last slot starting at sunset   (e.g. 18:29 instead of 19:00) for sun between 18:00-19:00
        # WARNING: In mode "hourly" the sunrise hour is changed to the start of the hour (e.g. from 08:19 to 08:00) and the sunset hour is combined with the previous hour (e.g. 18:00 and 18:29 are now both in 18:00)
        found_today, found_tomorrow, total_today_wh, total_tomorrow_wh = False, False, 0.0, 0.0
        forecasts_watt_hour = {}
        if response != None and isinstance(response, dict): # response is valid?
            response = response.get('wh_period', None) # Limit the response to the Watt Hours per Hour
            if response != None and isinstance(response, dict): # wh_period is valid?
                try:
                    ts_keys, dt_prev_period = list(response.keys()), None
                    if len(ts_keys) >= 3: # Enough forecast periods to determine the step size
                        step_size = int((datetime.fromisoformat(ts_keys[2]) - datetime.fromisoformat(ts_keys[1])).total_seconds() / 60) # Step Size in Minutes (comparing the 3rd and 2nd timestamp in the forecast)
                    else: # Should not happen but assume default of 60 min as step size
                        step_size = 60
                    for ts_str in ts_keys: # For each timestamp_str of the forecast keys
                        dt = datetime.fromisoformat(ts_str) # Get the datetime for the key (which is the datetime END of the period)
                        dt = dt.replace(tzinfo=None) # Remove the timezone
                        base_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0) # Start of the day
                        dt_index = int((dt - base_dt).total_seconds() / 60) // step_size - 1 # Determine the index of the period in the day (from the timestamp at the end of the period)
                        dt_period = base_dt + timedelta(minutes=dt_index * step_size) # Determine the start of the period for the dt (dt - step_size, adapted for sunset and sunrise periods)
                        if (dt_period == dt_prev_period): # for sunset the period start is the same as the previous period
                            dt_period = dt_period + timedelta(minutes=step_size) # Add an additional period for sunset (e.g. sunset at 18:29 and step size is 60min then next period start is 19:00)
                        forecast_wh = float(response.get(ts_str, None)) # Convert the forecast (wh) into a float
                        if dt.date() == today.date(): # Is this a forecast for today? 
                            found_today = True 
                            total_today_wh += forecast_wh # Add to the today total (wh)
                        elif dt.date() == tomorrow.date(): # Is this a forecast for tomorrow? 
                            found_tomorrow = True 
                            total_tomorrow_wh += forecast_wh # Add to the tomorrow total (wh)
                        forecasts_watt_hour[dt_period] = forecast_wh
                        dt_prev_period = dt_period
        #               print(f"Price {dt}: {forecasts_watt_hour[dt]}")
                except Exception as e: # Exception (e.g. invalid date or float)
                    error_msg = f"Parsing of data from Forecast.Solar failed {repr(e)}!" 
                    response = None
            else:
                error_msg = f"Watt Hours does not exist or contains no valid data from Forecast.Solar!" 
                response = None
        else:
            error_msg = f"No valid data from Forecast.Solar!" 
            response = None

        # Built a single Solar Forecast Array (for today and tomorrow) and Update the Solar Forecast Sensor:
        # Additional Attributes are Totals for today and tomorrow in Wh and in kWh, Start and End Datetime of the Forecast
        # The array will have 24 elements when only today is available and 48 when both today and tomorrow are available
        # The array will be empty when both today and tomorrow are not available
        # When only tomorrow is available the array will have 48 hours and the first 24 will all be zero
        if response != None: # Valid response found
            # Totals for Today:
            if found_today or found_tomorrow: # Save the today totals (in kW and kWh), if today not available but tomorrow is then today will be zero-s
                forecast_response["result"]["days_kw" ][today.strftime("%Y-%m-%d")] = int(total_today_wh) # Total Wh today (integer)
                forecast_response["result"]["days_kwh"][today.strftime("%Y-%m-%d")] = round(total_today_wh / 1000, 1) # Total kWh today (float, 1 decimal)
            # Totals for Tomorrow:
            if found_tomorrow: # Save the tomorrow totals (in kW and kWh)
                forecast_response["result"]["days_kw" ][tomorrow.strftime("%Y-%m-%d")] = int(total_tomorrow_wh)
                forecast_response["result"]["days_kwh"][tomorrow.strftime("%Y-%m-%d")] = round(total_tomorrow_wh / 1000, 1)
    
            # Built a Forecast Array for today and optionaly tomorrow (1 or 2 days):
            if found_today or found_tomorrow: # Remark: If only tomorrow found then today will be zero's
                start_time = today.replace(hour=0, minute=0, second=0, microsecond=0) # Start of today (00:00)
                forecast_response["result"]["interval"] = step_size
                forecast_response["result"]["start"]    = start_time.strftime("%Y-%m-%d %H:%M")
                available_days = (2 if found_tomorrow else (1 if found_today else 0)) # Tomorrow found: 2 days else Today found 1 else 0           
                end_time = start_time + timedelta(days = available_days) # 1 or 2 days (or 0 when forecast for incorrect days)

                current_time = start_time # Start at the first hour of today (00:00)
                while current_time < end_time: # For each period (hour or 15min) of today and optionally tomorrow
                    forecast_kwh = forecasts_watt_hour.get(current_time, 0.0) / 1000 # Get the forecast for the hour (or 0 when not available in the early or late hours)
                    forecast_response["result"]["hours_kwh"].append(forecast_kwh)
                    current_time += timedelta(minutes=step_size) # Next period

                forecast_response["result"]["end"] = current_time.strftime("%Y-%m-%d %H:%M")

            # Update the Entity (if it does not exist it will be created)
            state.set( # Update the status and attributes of the Forecast Entity
                HELIOS_SOLAR_FORECAST2,
                value=0, # State value is not used
                friendly_name=HELIOS_SOLAR_FORECAST_NAME2,
                unit_of_measurement="kWh", # Kilo Watt Hour
                device_class="energy",
                new_attributes=forecast_response
            )

    if error_msg != None: 
        log_error(f"[{HELIOS_FORECAST_NAME}] Error: {error_message}")
        forecast_response["message"] = error_msg
#   return response # Return the parsed service response or an error message
#   return forecasts_watt_hour # Return the parsed service response or an error message
    return forecast_response # Return the parsed service response or an error message
