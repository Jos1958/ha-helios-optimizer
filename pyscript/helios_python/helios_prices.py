# Module: HELIOS Price Parser - Python Function to parse Dynamic Energy Prices from different Dutch Energy Providers and from HBC Price Data
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-08-16: JR: v0.76  Investigated Price Sources and conversion options (Created the EnergyPriceConversion Project)
#   2026-09-17: JR  v0.78r Renamed from Class GenericEnergyParser to HeliosEnergyPriceParser (and kept the Old version as HeliosEnergyPriceParserOld in helios_price_parser_old.py)
#   2026-09-18: JR  v0.78r Added HBC Prices as a generic source (based on different Energy Providers), Convert between different Price Types (Market, Import, Export)
#   2026-09-10: JR  v0.78s Included Support for Conversion from Source Price to Target Price, Group Steps and Average Price, Expand Steps (Repeat), Fill Gaps in Day(s), Fallback Days, 
#   
# Warning: In Visual Studio this module exists in the helios_python folder of the Helios Optimizer Project and in Home Assistant in the /config/pyscript/helios_python folder.
#
# TODO:
#  - Optional Separate Today and Tomorrow Price Arrays (Instead of Both or Single Day in one Price Array)
#  - Price Array without individual timestamps (an array with floats instead of a dictionary with ts and price) and a separate start timestamp and (optional) step size or steps per day
#  - Extend the number of supported energy providers (includes testing), currently only HBC and Frank Energy are tested with mockup data
#  - Test with life data with HBC and Frank Energy

import sys                                    # For sys.path.append() to add the Home Assistant Pyscript folder to the path

from collections import defaultdict
from datetime    import datetime, timedelta, time, timezone
from zoneinfo    import ZoneInfo, ZoneInfoNotFoundError
from typing      import List, Dict, Any, Union

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

# General Defaults:
PRICE_PARSER_NAME   = 'Helios Price Parser'
TARGET_DT_KEY       = 'datetime'
TARGET_MP_KEY       = 'market_price'
TARGET_IP_KEY       = 'import_price'
TARGET_EP_KEY       = 'export_price'
PROVIDER_KEY_CUSTOM = 'custom' # Used for any invalid/unknown provider key
NO_TIME_ZONE        = None     # Use Local Timezone in constructor when no timezone is provided
TARGET_STEP_SIZE    = 15       # Default Step Size of 15 minutes for the Target (Market, Import and Export) Price Arrays
TS_FORMAT_LIST      = ['iso', 'unix', '%Y%m%d', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S'] # Possible values: 'iso' (Allows for TZ or Zulu), 'unix' (UTC) or a specific local (Without TimeZone) format as understood by ts_type of strptime()
PRICE_TYPE_LIST     = ['market', 'import', 'export'] # Price Types: Market Price (No VAT included), Import and Export Price (typically including Energy Tax and VAT)
ROUND_PRICES_EURO   = 5

class HeliosEnergyPriceParser:
    """Universal Energy Price parser with Provider profiles, 
    Support for multiple provider formats and a HBC format adapter,
    Price Unit (euros/cents/kWh/MWh), Energy Tax, VAT, Provider Markup (Opslag) transformations, strict day-alignment, and fallback handling.
    """

    # Generic Defaults for the Profiles, can be changed at Provider Profile level and in the Parse function:
    
    DEFAULT_DATA_PATH         = 'attributes.prices' # Default Path to the Price Data
    DEFAULT_TS_FORMAT         = 'iso'       # Default TimeStamp Format for the provider price info is ISO 
    DEFAULT_TS_KEY            = 'timestamp' # Default TimeStamp Format for the provider price info is ISO 
    DEFAULT_PRICE_KEY         = 'price'     # Default TimeStamp Format for the provider price info is ISO 
    DEFAULT_KEY_NONE          = None        # Default for Keys that are optional (e.g. start_key)            
    DEFAULT_ORG_PROV_NONE     = None        # Default Do NOT use an source provider for the Markup and Source Type (only applies to HBC Price Data)
    DEFAULT_SRCE_TYPE         = 'import'    # Default Source Price Type is Import Price
    DEFAULT_SRCE_PRICE_FACTOR = 1           # Default Source Price Factor to convert to euro/kWh (e.g. for source price in cents/kWh: 0.01 or for source in euro/MWh: 0.001)
    DEFAULT_SRCE_HAS_VAT      = True        # Default Source Price includes VAT
    DEFAULT_PROV_MARKUP       = 0.0200      # Default Provider Markup (Opslag) in euro before VAT, Applies to both Import and Export Prices 

    DEFAULT_VAT_RATE          = 0.21        # Default Dutch VAT (BTW) rate
    DEFAULT_ENERGY_TAX        = 0.1108      # Default Dutch Energy Tax (Nederlandse Energiebelasting voor 2026) without VAT (incl VAT: 0.134068 euro)
    DEFAULT_TARGET_NEEDS_VAT  = True        # Default Target (Import and Export) Prices need to include VAT (not applicable to Market Price)
    DEFAULT_MAX_FB_DAYS       = 1           # Default Maximum Number of Fallback Days when prices for the Lookup Day are not available in the Source Price

    DEFAULT_SOURCE_PRICE       = 0.30        # Default Input Price when no Hour Price and no First Price Found is (In principle this should not happen since a Day is not used when it has no price at all) 

    PRICE_PROFILES  = { # In future to be loaded from a JSON file (including the local tax rates which a generic for all providers, although overwrite is possible)
        # See above for more detailed descriptions of the profile defaults:
        "data_path"          : "attributes.values"      , # Path in the Dictonary with the Price Information
        "ts_format"          : DEFAULT_TS_FORMAT        , # ISO        , Standard Format which can include TZ information
        "ts_key"             : DEFAULT_TS_KEY           , # timestamp  , Standard key for the timestamp
        "price_key"          : DEFAULT_PRICE_KEY        , # price      , Standard key for the price value 
        "start_key"          : DEFAULT_KEY_NONE         , # None       , Timestamp of the First Price, Start key is only needed if the input is a simple array of prices without timestamps       
        "original_provider"  : DEFAULT_ORG_PROV_NONE    , # None       , Retrieve the 'Source Has VAT' and Markup (Opslag) from a different Source Provider (None=n/a)
        "source_type"        : DEFAULT_SRCE_TYPE        , # import     , Default Source Price Type is Import Price
        "source_price_factor": DEFAULT_SRCE_PRICE_FACTOR, # 1          , Convert the Source Price using this factor to euro/kWh
        "source_has_vat"     : DEFAULT_SRCE_HAS_VAT     , # True       , VAT Included in Source Price (Disable for Market Price as Source Type and Enable for Import or Export Prices as Source Type)
        "markup"             : DEFAULT_PROV_MARKUP      , # 0.02   euro, Provider Markup for Import and Export (only used when no provider markup specified, typically each provider has its own markups)
        
        # Following attributes are typically general defaults (not different per provider):
        # VAT Rate and Energy Tax may be defined in the provider profile but will only be used from converting the source prices (not for the target prices)
        "vat_rate"           : DEFAULT_VAT_RATE         , # 0.21   euro, Dutch Value 
        "energy_tax"         : DEFAULT_ENERGY_TAX       , # 0.1088 euro, Dutch Value for 2026
        "target_needs_vat"   : DEFAULT_TARGET_NEEDS_VAT , # True       , Tax included for Import and Export Prices in the Target Price Arrays
        "max_fallback_days"  : DEFAULT_MAX_FB_DAYS      , # 1          , Prices from 1 day back may be used when the prices for the lookup date are not available

        "providers": { 
            "hbc_marks": { # HBC Format (can be from different Original Providers, specify via original_provider)
                "name"               : "HBC (Marks)"      , # Provider Name
                "data_path"          : "marks"            , # Provider Data Path to the Prices 
                "ts_format"          : "iso"              , # Provider Timestamp Format
                "ts_key"             : "start"            , # Provider Timestamp Key, ts_end: "end"
                "price_key"          : "price"            , # Provider Price     Key
                "original_provider"  : "frank_energie"    , # Use Markup and Source Has VAT from Frank Energie (unless overruled in this profile, so do not specify source_has_vat and markup_import & _export)
                "source_type"        : "import"           , # Source Type for the Source Prices of the provider ("market", "import", "export"), determines how to convert to output prices
                "source_price_factor": 0.01               , # HBC Source Prices are in cents/kWh and need to be converted to euro
            },
            "nordpool": { # Provider Key (Generic Provider, you may need to overwrite the markup's when using a different energy provider)
                "name"               : "Nordpool Spot"    , # Provider Name
                "data_path"          : "raw_today"        , # Provider Data Path to the Prices for today (does not include raw_tomorrow!)
                "ts_format"          : "iso"              , # Provider Timestamp Format
                "ts_key"             : "start"            , # Provider Timestamp Key, ts_end: "end"
                "price_key"          : "value"            , # Provider Price     Key
                "source_type"        : "market"           , # Source Type for the Source Prices of the provider ("market", "import", "export"), determines how to convert to output prices
                "source_price_factor": 1.0                , # Conversion Factor for the Source Price to euro/kWh
                "source_has_vat"     : False              , # VAT excluded in the Source Prices of the provider 
                "markup_import"      : 0.0200             , # Provider Markup (Opslag) for the Import Price 
                "markup_export"      : 0.0200             , # Provider Markup (Opslag) for the Export Price (sometimes negative value)
            },
            "frank_energie": {
                "name"               : "Frank Energie (Import)",
                "data_path"          : "attributes.prices",
                "ts_format"          : "iso"              ,
                "ts_key"             : "from"             , # ts_end: "till"
                "price_key"          : "price"            , 
                "source_type"        : "import"           ,
                "source_price_factor": 1.0                , # Prices are in euro/kWh (Note: HBC converts the prices to cents/kWh)
                "source_has_vat"     : True               ,
                "markup_import"      : 0.01815            ,
                "markup_export"      : 0.01271            ,
            },
            "zonneplan": {
                "name"               : "Zonneplan"           ,
                "source_type"        : "import"           ,
                "source_has_vat"     : True               ,
                "markup_import"      : 0.0200             ,
                "markup_export"      : 0.0200             ,
            },
            "tibber": {
                "name"               : "Tibber"           ,
                "source_type"        : "import"           ,
                "source_has_vat"     : True               ,
                "markup_import"      : 0.0200             ,
                "markup_export"      : 0.0200             ,
            },
            "energy_zero": {
                "name"               : "EnergyZero / ANWB Energie",
                "source_type"        : "market"           ,
                "source_has_vat"     : False              ,
                "markup_import"      : 0.0175             ,
                "markup_export"      : 0.0175             ,
            },
            "custom": { # Default Provider (used when the provider key does not exist or when no provider key is specified)
                "name"               : "Custom Configuration",
                "source_type"        : "import"           , # Assuming Import Prices as Source Price
                "source_price_factor": 1.0                , # Assuming Source Prices are in euro/kWh
                "source_has_vat"     : True               , # Assuming Source Prices include VAT
                "markup_import"      : DEFAULT_PROV_MARKUP, # Estimated Provider (Import) Markup
                "markup_export"      : DEFAULT_PROV_MARKUP, # Estimated Provider (Export) Markup
            },
        }
    }
    def __init__(self, provider_key: str = "custom", config_override: dict = None, target_tz: Any = NO_TIME_ZONE, target_step_size: int = TARGET_STEP_SIZE, round_prices: int = ROUND_PRICES_EURO, raise_error: bool = True):
        """Initialize the parser using a provider key and optional custom overrides."""
        # Get the generic defaults for the price profiles (applicable to all providers when not specified in the provider profile):
        default_data_path        = self.PRICE_PROFILES.get('data_path'          , self.DEFAULT_DATA_PATH        )
        default_ts_format        = self.PRICE_PROFILES.get('ts_format'          , self.DEFAULT_TS_FORMAT        )
        default_ts_key           = self.PRICE_PROFILES.get('ts_key'             , self.DEFAULT_TS_KEY           )
        default_price_key        = self.PRICE_PROFILES.get('price_key'          , self.DEFAULT_PRICE_KEY        )
        default_org_provider     = self.PRICE_PROFILES.get('original_provider'  , self.DEFAULT_ORG_PROV_NONE   )
        default_srce_type        = self.PRICE_PROFILES.get('source_type'        , self.DEFAULT_SRCE_TYPE        )
        default_srce_price_factor= self.PRICE_PROFILES.get('source_price_factor', self.DEFAULT_SRCE_PRICE_FACTOR)
        default_srce_has_vat     = self.PRICE_PROFILES.get('source_has_vat'     , self.DEFAULT_SRCE_HAS_VAT     )
        default_markup_import    = self.PRICE_PROFILES.get('markup_import'      , self.DEFAULT_PROV_MARKUP      ) 
        default_markup_export    = self.PRICE_PROFILES.get('markup_export'      , self.DEFAULT_PROV_MARKUP      )

        default_vat_rate         = self.PRICE_PROFILES.get('vat_rate'           , self.DEFAULT_VAT_RATE         )
        default_energy_tax       = self.PRICE_PROFILES.get('energy_tax'         , self.DEFAULT_ENERGY_TAX       )
        default_target_needs_vat = self.PRICE_PROFILES.get('target_needs_vat'   , self.DEFAULT_TARGET_NEEDS_VAT )
        default_max_fb_days      = self.PRICE_PROFILES.get('max_fallback_days'  , self.DEFAULT_MAX_FB_DAYS      )

        providers = self.PRICE_PROFILES.get('providers', {}) # Get all Providers from the Price Profiles Dictionary
        base_profile = providers.get(provider_key.lower(), providers[PROVIDER_KEY_CUSTOM]) # Get the Price Profile for the specified Provider Key (Or use the Custom Profile when key not found)

        # Determine the Provider Profile (with optional overrrides) and Target Time Zone:
        config_override       = config_override or {} # Optional Provider Config override in the constructor
        self.config           = {**base_profile, **config_override} # Optionally Override the Provider Profile in the constructor
        self.target_tz        = self._resolve_timezone(target_tz)   # Resolve the specified Target Time Zone
        self.target_step_size = target_step_size  # Step Size of the Target Price Arrays
        self.round_prices     = round_prices      # Rounding of prices of the Target Price Arrays
        self.default_ts_key   = default_ts_key    # Default Timestamp key will also work (next to the Provider Timestamp key)
        self.default_price_key= default_price_key # Default Price     key will also work (next to the Provider Price     key)
        self.raise_error      = raise_error       # Raise an Exception when an error occurs in the parsing of the price data (if disabled an error will be logged and an empty price array will be returned)

        # Some Providers (like HBC) are sourced from another (Original) Provider
        # The Defaults for 'Source Has VAT', Provider Markup for Import and Export are retrieved from this other (Original) Provider:    
        # Warning: If the current provider (e.g. HBC) has these attributes specified then the original provider attributes are IGNORED (original_provider has no effect)!
        self.original_provider = self.config.get("original_provider", default_org_provider)
        if (self.original_provider != None): # Is another Orginal Provider Applicable (e.g. for HBC)?
            orginal_profile = providers.get(self.original_provider.lower(), providers[PROVIDER_KEY_CUSTOM]) # Get the Price Profile for the other Provider (or use the Custom)
            if (orginal_profile != None): # Other Provider Found?
                default_srce_has_vat  = orginal_profile.get("source_has_vat", default_srce_has_vat )
                default_markup_import = orginal_profile.get("markup_import" , default_markup_import)
                default_markup_export = orginal_profile.get("markup_export" , default_markup_export)

        # Use Source Provider Attributes from the Provider Profile (when not specified use the Generic Defaults)
        self.data_path                = self.config.get("data_path"            , default_data_path        )
        self.ts_format                = self.config.get("ts_format"            , default_ts_format        )
        self.ts_key                   = self.config.get("ts_key"               , default_ts_key           )
        self.price_key                = self.config.get("price_key"            , default_price_key        )
        self.source_type              = self.config.get("source_type"          , default_srce_type        )
        self.source_price_factor      = self.config.get("source_price_factor"  , default_srce_price_factor)
        self.source_vat_rate          = self.config.get("vat_rate"             , default_vat_rate         ) # Provider VAT only used with Source Price
        self.source_energy_tax        = self.config.get("energy_tax"           , default_energy_tax       ) # Provider Energy Tax only used with Source Price

        # Use Source Provider Attributes 'Source has VAT' and Markup for Import and Export when specified for this Provider 
        # When not specified use these Attributes from the Orginal Provider (or use the overall defaults)
        # Remark: Do NOT specify these attributes in the Provider when using the prices are sourced from an Original Provider!
        self.source_has_vat           = self.config.get("source_has_vat"       , default_srce_has_vat     ) 
        self.markup_import            = self.config.get("markup_import"        , default_markup_import    ) # Provider Markup (Opslag) for Import Prices (Default is a generic Markup)
        self.markup_export            = self.config.get("markup_export"        , default_markup_export    ) # Provider Markup (Opslag) for Export Prices (Default is a generic Markup)

        # Target and Fallback Attributes:
        self.target_vat_rate          = self.config.get("vat_rate"             , default_vat_rate         ) # General VAT used for Target Prices
        self.target_energy_tax        = self.config.get("energy_tax"           , default_energy_tax       ) # General Energy Tax used for Target Prices
        self.target_needs_vat         = self.config.get("target_needs_vat"     , default_target_needs_vat )
        self.max_fallback_days        = self.config.get("max_fallback_days"    , default_max_fb_days      ) 

    # Resolve the specified timezone configuration:
    def _resolve_timezone(self, tz_cfg: Any = None):
        """Resolve the timezone which can be None (for local system timezone), a TZ IANA string key or Time Delta in Minutes (compared to UTC).
        In all other cases the specified TZ configuration is assumed to be already a TimeZone and is returned as-is.
        """
        # 1. No timezone specified (None), use the Local System Timezone
        if not tz_cfg: # No TimeZone specified
            return datetime.now().astimezone().tzinfo # Get the local system timezone from the datetime (now)
    
        # 2. IAN TZ key specified as a TimeZone description (e.g. "Europe/Amsterdam")
        if isinstance(tz_cfg, str): # IANA Timezone string key specified?
            try:
                return ZoneInfo(tz_cfg) # Return the TimeZone based on the ZoneInfo key
            except ZoneInfoNotFoundError as e: # Warning: ZoneInfo does not work (ZoneInfo key is not found)
                # If IANA-database is missing (e.g. Windows), use the system-timezone
                _LOGGER.error(f"[{PRICE_PARSER_NAME}-Resolve-Timezone] Exception: {repr(e)}")
                return datetime.now().astimezone().tzinfo
        
        if isinstance(tz_cfg, int): # TimeZone Delta specified in Minutes (must be between -1440 (-24h) and +1440 (+24h))
            return timezone(timedelta(minutes=tz_cfg))

        return tz_cfg # Return the input when tz_cfg is already a ZoneInfo object

    # Parse the Timestamp Value (An Integer, Float or String in the Timestamp Format) with optional Timezone info into a Naive DateTime for the Target Timezone
    def _parse_timestamp(self, ts_val: Union[str, int, float], ts_format: str = None, target_tz: Any = NO_TIME_ZONE) -> datetime:
        """
        Parse the Timestamp Value into a Naive DateTime for the Target TimeZone.
        The Time will be shifted to the Target TimeZone when a Source TimeZone is available.
        The Timestamp Value can have different formats (with or without a TimeZone)
        - Unix Integer or Float Value with (always) UTC timezone, Time will be shifted from +00:00 to the Target Timezone 
        - ISO Timestamp String with a specific TimeZone (e.g. +02:00 or -04:00 or Z (+00:00) for Zulu time), Time will be shifted from the specified Timezone to the Target Timezone
        - Local Time with a specific format (e.g. "%Y-%m-%d %H:%M:%S" or "%Y%m%d"), no Timezone can be specified and no timeshift to the Target Timezone will occur
        Typically the Timestamp Format and Target Timezone of the EnergyPriceParser class are used but both variables can be specified as an argument for parse timestamp.
        The function will return a Naive Datetime for the Target Zone but WITHOUT a Timezone!
        """
        # Determine the Timestamp Format (for the Source) and the Target Timezone (from arguments or from provider settings):
        ts_format = ts_format                         if ts_format else self.ts_format  # Use the Timestamp Format of the Parser unless a different Timestamp Format is specified in the arguments
        target_tz = self._resolve_timezone(target_tz) if target_tz else self.target_tz  # Use the Target Timezone  of the Parser unless a different Target Timezone  is specified in the arguments
        
        # Convert the Timestamp Value to a Datetime (with an optional Timezone):
        try:
            if ts_format == "unix": # Unix timestamp format (integer count of seconds since 1970-01-01 00:00:00) (Timezone is ALWAYS UTC, will be shifted later to the Target Timezone)
                dt = datetime.fromtimestamp(float(ts_val), tz=timezone.utc) # Convert Timestamp Integer or Float to a Datetime with UTC Timezone
            elif ts_format == "iso": # ISO timestamp format (allows for specification of a Timezone which will be shifted later to the Target Timezone)
                dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00")) # Convert ISO Timestamp String to a Datetime with the specified but optional Timezone ("Z" is not supported by fromisoformat so is first replaced by UTC/+00:00 timezone)
            else: # Local Timezone in the specified format (e.g. ), No TimeZone in the format so assumed to be already in the TARGET timezone (no shift will be done)
                dt = datetime.strptime(str(ts_val), ts_format) # Convert Timestamp String to a Datetime without a Timezone
        
        except Exception as e:
            error_message = f"Invalid Timestamp {ts_val}: {repr(e)}!"
            if self.raise_error:
                raise ValueError(error_message)

            _LOGGER.error(f"[{PRICE_PARSER_NAME}-Parse-Timestamp] Exception: {error_message}")
            return None

        # Convert the Datetime to the Target Timezone:
        if dt.tzinfo is not None: # Timezone Aware Datetime?
            dt = dt.astimezone(target_tz) # Convert Datetime to the Target Timezone
        else: # Timezone Naive Datetime (No Timezone Info)!
            # Assume the Datetime is already in the Target Timezone (no timeshift needed)
            dt = dt.replace(tzinfo=target_tz) # Set the Target Timezone in the Datetime

        return dt.replace(tzinfo=None) # Return the Datetime but without Timezone information

   # Converts a Single Source Price (for a specific Price Type) into the Target Prices (All Types: Market, Import and Export Price).
    def _convert_price(self, step_ts, source_price, source_type=None, source_price_factor: float = None, source_has_vat: bool = None, target_needs_vat=None):
        """Converts a Single Source Price (for a specific Price Type) into the Target Prices (All Types: Market, Import and Export Price)."""

        market_price, import_price, export_price,  = 0.0, 0.0, 0.0 # Initialize Target Prices
        if source_price != None:
            # Determine the 'Source (Price) Type', 'Source Price Factor', 'Source Has VAT' and 'Target Needs VAT' (from arguments or from provider settings):
            src_type     = (source_type      if source_type         is not None else self.source_type        )
            price_factor = (price_factor     if source_price_factor is not None else self.source_price_factor)
            has_vat      = (source_has_vat   if source_has_vat      is not None else self.source_has_vat     ) # Make sure to disable source has vat for sources of market prices
            needs_vat    = (target_needs_vat if target_needs_vat    is not None else self.target_needs_vat   )

            price = price_factor * float(source_price)  # Make sure the Price is a float and convert to euro/kWH using the Source Price Factor
            source_vat_factor = (1.0 + self.source_vat_rate) # Determine the VAT factor from the VAT percentage
            price_ex_vat = price / source_vat_factor if has_vat else price # Remove the VAT from the price when included (this will also happen for market prices when 'Source Has VAT' is specified)

            # Depending on the Source Type: Determine the Market Price without VAT
            if src_type == "market": # Already a Market Price?
                market_price = price_ex_vat # Just copy the Price
            elif src_type == "import": # Import Price?
                market_price = price_ex_vat - self.source_energy_tax - self.markup_import # Deduct the Energy Tax and the Import Markup 
            elif src_type == "export": # Export Price?
                market_price = price_ex_vat + self.markup_export # Add the Export Markup
            
            else: # Invalid Source Type!
                error_message = f"Invalid Source Type {src_type}!"
                if self.raise_error:
                    raise TypeError(error_message)

                _LOGGER.error(f"[{PRICE_PARSER_NAME}-Convert_Price] Error: {error_message}")
                market_price = 0.0 # No price available

            # Calculate the Target (Market, Import and Export) Price:
            target_vat_factor = (1.0 + self.target_vat_rate) if needs_vat else 1.0 # Output VAT applicable? -> Use VAT Factor else 1.0
            import_price = target_vat_factor * (market_price + self.markup_import + self.target_energy_tax) # Import Price with optional VAT
            export_price = target_vat_factor * (market_price - self.markup_export                         ) # Export Price with optional VAT

        return { # Return a Dictionary with the Step Datetime and the 3 Target (Market, Import and Export) Prices
            TARGET_DT_KEY: step_ts                               , # Step Datetime 
            TARGET_MP_KEY: round(market_price, self.round_prices), # Market Price (never has VAT)
            TARGET_IP_KEY: round(import_price, self.round_prices), # Import Price including Import Markup, Energy Tax and optional VAT
            TARGET_EP_KEY: round(export_price, self.round_prices)  # Export Price including Export Markup and with optional VAT
        }

    # Retrieve Nested Data from the specified Data Dictionary using the specified Path:
    def _extract_nested_data(self, data_dict: Any, path: str) -> Any:
        """
        Retrieve the Nested Data from the Data Dictionary using the specified Path. 
        The path can have multiple levels divided by dots (e.g. 'attributes.data.prices') or can be None.
        The nested data is returned. If the path is not found [] is returned. 
        If the path is None then the orginal data is returned.
        """
        if not path: # No path provided?
            return data_dict # Just return the provided data dictionary

        # Search for the path in the provided data dictionary:
        for key in path.split('.'): # For each key in the path (from left to right)

            if isinstance(data_dict, dict): # Is the data a dictionary?
                if key in data_dict.keys(): # Does the key exist in the dictionary?
                    data_dict = data_dict.get(key, []) # Get the data below the key and goto the next key (if available)
                
                else: # Key does not exist
                    error_message = f"Key '{key}' does not exist, Path '{path}' not Found in Price Data!"
                    if self.raise_error:
                        raise KeyError(error_message)

                    _LOGGER.error(f"[{PRICE_PARSER_NAME}-Extract-Nested-Data]: {error_message}")
                    return [] # Key not found so return an empty list

            else: # Is the data not or no longer a dictionary
                error_message = f"Invalid Dictonary Structure for key '{key}', Path '{path}' not Found in Price Data!"
                if self.raise_error:
                    raise KeyError(error_message)

                _LOGGER.error(f"[{PRICE_PARSER_NAME}-Extract-Nested-Data]: {error_message}")
                return [] # Data not or no longer a dictionary so return an empty list

        return data_dict # Path has been found so return the data below the path   

    # Group Input Price Records (Items) by Step (e.g. 60, 30 or 15 min).
    def _group_by_step (self, source_price_list, target_step_size: int = None):
        """
        Retrieves the Timestamp and the Price from the Input Price Array
        Groups Input Price Records (Items) by Step in a Bucket.
        Compresses Records with a shorter step size to the required Step Size by averaging the Price within the Bucket.
        """
        if target_step_size is None: target_step_size = self.target_step_size # Use the Step Size from the constructor when not specified
        # Remark: Defaultdict adds a new key automatically when the key does not yet exist, Each record is a list to group prices for the same step
        grouped_step_prices: Dict[datetime, List[float]] = defaultdict(list) # Initialize the Grouped Step Prices Dictionary (empty)
        
        for item in source_price_list: # For each Price Record (Item) in the Source Price Array:
            if not isinstance(item, dict): # Price Record is not a dictionary?
                _LOGGER.warning(f"[{PRICE_PARSER_NAME}-Group-By-Step]: Invalid Price Record ({str(item)}) ignored!")
                continue # Ignore Items that are not a Dictionary

            # Determine the Raw Timestamp (ts) and the Raw Price Value (with Field Keys from Provider Settings and from Defaults)
            # Try both the json keys from the provider settings and if not found try the default keys to retrieve the timestamp and the price:
            ts_raw     = item.get(self.ts_key   ) if (item.get(self.ts_key   ) is not None) else item.get(self.default_ts_key   ) # Use Provider ts    key or default ts    key to retrieve the timestamp 
            price_raw  = item.get(self.price_key) if (item.get(self.price_key) is not None) else item.get(self.default_price_key) # Use Provider price Key or default price key to retrieve the price 

            if (ts_raw is not None) and (price_raw is not None): # Price Record contains a Timestamp and a Price Value?
                try:
                    # Parse the timestamp into a Naive Datetime for the Target Timezone (as specified in the __init__)
                    # Warning: Afterwards the Timezone info is REMOVED!
#                   dt_obj = datetime.fromisoformat(str(dt_raw)).replace(tzinfo=None) # JR2026-09-22 Replaced by _parse_timestamp
                    dt_obj  = self._parse_timestamp(ts_raw) 
                    
                    # Create a Bucket Datetime that fits the Step Size in minutes and add all Prices related to this Bucket (can be one or multiple)
                    # Multiple Price Records can result in the same bucket (e.g. for a Step Size of 60 min, all HH:00, HH:15, HH:30 and HH:45 min Price Records will have the same Bucket Time of HH:00)
                    bucket_ts = dt_obj.replace(minute=(dt_obj.minute // target_step_size) * target_step_size, second=0, microsecond=0)
                    grouped_step_prices[bucket_ts].append(price_raw) # Add the Provider Price for the Bucket Timestamp (The Bucket Timestamp is also automatically added when it does not yet exist)

                except (ValueError, TypeError) as e:
                    error_message = f"Invalid Price Record ({ts_raw},{price_raw}): {repr(e)}!"
                    _LOGGER.warning(f"[{PRICE_PARSER_NAME}-Group-By-Step] Exception: {error_message}")
                    continue # Continue with the next item in the price list
            
            else: # Price Record does not contain a Timestamp and a Price Value (one or both are missing):
                error_message = f"Invalid Price Record ({ts_raw},{price_raw}) ignored!"
                _LOGGER.warning(f"[{PRICE_PARSER_NAME}-Group-By-Step] Error: {error_message}")

        # Determine the Average Price per Step (Bucket) (handles 15 min -> 30 or 60 min conversion)
        bucket_prices: list[dict] = [ # Create a List with Dictionaries for the Price Records for all Buckets
            {self.default_ts_key: dt, self.default_price_key: sum(prices) / len(prices)} for dt, prices in grouped_step_prices.items() # Determine the Average Price per Bucket 
        ]

        if (len(bucket_prices) <= 0): # No Price Records found?
            error_message = f"Source Price List is Empty or All Records are Invalid (see Warnings)!"
            if self.raise_error:
                raise ValueError(error_message)

            _LOGGER.error(f"[{PRICE_PARSER_NAME}-Group-By-Step] Error: {error_message}")
            bucket_prices = [] # Empty Price List (no valid records found)

        return bucket_prices # Return the Bucket Datetimes with an (Average) Price per Target Step

    # Group Input Price Records (Items) strictly by Calendar Day (Date).
    def _group_by_day(self, price_list):
        """Groups Input Price Records (Items) by Calendar Day (Date).
        """
        grouped_days = {} # No Grouped Days for Price Records found yet
        for item in price_list:
            if not isinstance(item, dict):
                _LOGGER.warning(f"[{PRICE_PARSER_NAME}-Group-By-Date] Error: Invalid Price Record {str(item)}!")
                continue # Ignore Items that are not a Dictionary

            # Determine the Raw Timestamp and the Raw Price Value (with Field Keys from Provider Settings and from Defaults)
            # Try both the json keys from the provider settings and if not found try the default keys to retrieve the timestamp and the price:
            ts_raw     = item.get(self.ts_key   ) if (item.get(self.ts_key   ) is not None) else item.get(self.default_ts_key   ) # Use Provider ts    key or default ts    key to retrieve the timestamp 
            price_raw  = item.get(self.price_key) if (item.get(self.price_key) is not None) else item.get(self.default_price_key) # Use Provider price Key or default price key to retrieve the price 

            if (ts_raw is not None) and (price_raw is not None): # Item contains a Timestamp and a Price Value?
                try:
#                   dt_obj = datetime.fromisoformat(str(dt_raw)).replace(tzinfo=None) # JR2026-09-22 Replaced by _parse_timestamp
                    dt_obj  = self._parse_timestamp(ts_raw) # Parse the timestamp into a Naive Datetime for the Target Timezone (Warning: Afterwards the Timezone info is REMOVED)
                    day_key = dt_obj.date() # Get only the Date/Day from the Datetime Object

                    if day_key not in grouped_days: # If the Day not already in the Grouped Days
                        grouped_days[day_key] = {} # Add the new Day (without any Datetimes yet) to the Grouped Days
                    grouped_days[day_key][dt_obj] = float(price_raw) # Add the Datetime below its Day in the Grouped Days
                    
                except (ValueError, TypeError) as e:
                    error_message = f"Price Record Grouping Problem ({ts_raw},{price_raw}): {repr(e)}!"
                    if self.raise_error:
                        raise ValueError(error_message)

                    _LOGGER.error(f"[{PRICE_PARSER_NAME}-Group-By-Date] Exception: {error_message}")
                    continue # Continue with the next item in the price list

        return grouped_days # Return the Grouped Dates (Each Price Record found is as a Datetime below its own Date) 
    
    # Get the Prices for the Lookup Datetime (Prices for One or Two days when available):
    def get_day_prices(self, price_data, lookup_ts: datetime = None, target_step_size: int = None,
                       max_fallback_days: int = None, source_type=None, source_has_vat=None, target_needs_vat=None) -> list:
        """Processes and aligns price data for full calendar days with fallback handling."""
        last_valid_price = None
        if lookup_ts         is None: lookup_ts = datetime.now() # If no Lookup Datetime has been specified then use Now (can be tricky since in a container the OS timezone may not be equal to the HA timezone)
        if target_step_size  is None: target_step_size  = self.target_step_size  # Use the Step Size from the constructor when not specified
        if max_fallback_days is None: max_fallback_days = self.max_fallback_days # Use the maximum fallback days from the constructor when not specified
    
        lookup_ts.replace(tzinfo=None) # No Timezone Info needed/wanted in the Lookup Datetime since the Price Data will have been converted already to the required Target Timezone (see __init__)
        lookup_day = lookup_ts.date()  # Create Lookup Day from the Lookup Datetime (Time is not relevant we want all prices for today and perhaps tomorrow)
        
        source_prices = self._extract_nested_data(price_data, self.data_path) # Get all Price Items from the Price Data (can be nested in the Price Data Dictionary for certain providers)
        bucket_prices = self._group_by_step(source_prices, target_step_size)  # Group the Price Records per (Target) Step (so all Prices for a certain Step/Bucket together, The Bucket Price is the average of the individual Price Records)
        grouped_days  = self._group_by_day (bucket_prices) # Group the Price Records per Day (so all Prices for a certain Day/Date together)

        target_days = [] # Initialize the Target Days/Dates
        # Try to locate the Lookup Day(s) (or Fallback Day) in the Price Data:
        if lookup_day in grouped_days: # Does Lookup Day exists in Grouped Days (from the Input Price Data)?
            target_days.append(lookup_day) # Add Lookup Day to Target Days
            tomorrow_day = lookup_day + timedelta(days=1) # Create Lookup Day + 1 
            if tomorrow_day in grouped_days: # Does Lookup Day + 1 exist in Grouped Days (from the Input Price Data)?
                target_days.append(tomorrow_day) # Add Lookup Day + 1 to Target Days
        
        else: # Lookup Day not found in the Grouped Days (Perhaps a Fallback Day available within Max Fallback Days)
            found_fallback = False # No Fallback Day found yet
            for day_offset in range(1, max_fallback_days + 1): # For each allowed Fallback Day (Start -1 .. -Max Fallback Days)
                fallback_day = lookup_day - timedelta(days=day_offset) # Go back x day(s) (x = 1 to Max Fallback Days)
                if fallback_day in grouped_days: # Does fallback day exist in Grouped Days?
                    _LOGGER.warning(f"[{PRICE_PARSER_NAME}-Get-Day-Prices] Warning: Price Data missing for {lookup_day}, Using Fallback {fallback_day}!")
                    target_days.append(fallback_day) # Add Fallback Day to Target Days
                    found_fallback = True # Found Fallback day so search can stop
                    break # Stop search for Fallback Day

            if not found_fallback:
                error_message = f"Price Data missing for {lookup_day}, No Fallback available within {max_fallback_days} days!"
                if self.raise_error:
                    raise KeyError(error_message)

                _LOGGER.error(f"[{PRICE_PARSER_NAME}-Get-Day-Prices] Error: {error_message}")
                return [] # Return an empty Price Array

        processed_prices = [] # Initialize the Prices Array
        for target_day in target_days: # For each Target Day
            day_start = datetime.combine(target_day, datetime.min.time())
            day_prices = grouped_days[target_day]
            if last_valid_price is None: # Not yet a last valid price from the previous day?
                last_valid_price = next(iter(day_prices.values())) if len(day_prices) > 0 else self.DEFAULT_SOURCE_PRICE # Determine the first price record of the day and return its price value (or the default)
            steps_per_day = int(1440 / target_step_size) # Steps per Day is 24 hours * 60 minutes / Target Step Size in Min

            for step in range(steps_per_day): # For each Step of this Day
                step_ts = day_start + timedelta(minutes=step * target_step_size) # Determine the Step Datetime
                matching_price = day_prices.get(step_ts) # Get the Price for the Step Datetime from the Input Price Array

                if matching_price is None: # No Matching Price found for the Step Datetime? -> Use the Price from the Last Step Boundary
                    # For Source Prices in Hours the following will fill the Next Quarters (15, 30, 45) from the Hour Price, would also work for half hour prices
                    matching_price = last_valid_price # Use the last previous price (e.g. for hour prices this will set the same price for each following quarter until the next hour)
                else: # New Matching Price found!
                    last_valid_price = matching_price # Keep the matching price as the last valid price

                converted_price_record = self._convert_price(step_ts=step_ts, source_price=matching_price, source_type=source_type, source_has_vat=source_has_vat, target_needs_vat=target_needs_vat)
                processed_prices.append(converted_price_record)

        return processed_prices

    # Extracts and normalizes price records from the Simple HBC Price Data structure (a simple array of prices and a start timestamp and datapoints per hour).
    # Warning: This function is currently not used since the HBC Price Data is already normalized in the HBC Marks Provider Profile (see data_path, ts_key and price_key)
    # Todo: Testing !!!
    def parse_hbc_prices(self, hbc_price_data):
        """Extracts and normalizes price records from the Simple HBC Price Data structure.""" 

        # Fallback extraction: Reconstruct timestamps using 'start' and 'prices' list
        normalized_prices = [] # Initialize the Normalized Prices List
        prices_list    = hbc_price_data.get("prices")
        base_start_str = hbc_price_data.get("start")

        if isinstance(prices_list, list) and base_start_str:
            try:
#               base_ts = datetime.fromisoformat(str(base_start_str)) # JR2026-09-22 Replaced by _parse_timestamp
                base_ts = self._parse_timestamp(base_start_str)
                dph = int(hbc_price_data.get("datapoints_per_hour", 1))
                step_minutes = int(60 / max(dph, 1))

                for idx, val in enumerate(prices_list):
                    if val is None:
                        continue
                    
                    slot_ts = base_ts + timedelta(minutes=idx * step_minutes)
                    price_eur = float(val) * scale

                    normalized_prices.append({
                        "start": slot_ts.isoformat(),
                        "value": price_eur
                    })
            except Exception as e:
                error_message = f"HBC Simple Price Data Problem: {repr(e)}!"
                if self.raise_error:
                    raise ValueError(error_message)

                _LOGGER.error(f"[{PRICE_PARSER_NAME}-Parse-HBC-Prices] Exception: {error_message}")

        return normalized_prices

    # Convert the Processed Prices List (with timestamp and 3 prices) into a Simple Price List (without timestamps and with a specific price)
    def get_simple_price_list(self, processed_prices: list, price_key: str = TARGET_MP_KEY):
        """
        Convert the Processed Price record to a Simple Price List of the specified Price Type without datetimes/timestamps.
        Warning: When a day does not exist in the source price list then a fallback day can be used (after this function this cannot be recognized anymore since the timestamps are removed).
        """
        simple_price_list: list[float] = [ # Create a Simple List of Prices without datetime/timestamp info
            price_record.get(price_key, None) for price_record in processed_prices # Get the requested Price Type for the Price Record 
        ]
        return simple_price_list

#########################################################################################
# TEST FUNCTION for helios_main.py and for EnergyPriceConversion.py                     #
#########################################################################################
# Print the 60 min price array (market, import and export per line) and the 15 min prices (4 per line for one type) array next to each other:
def print_all_prices(title: str, market_prices_60min: list, prices_15min: list, import_prices_60min: list = None, export_prices_60min: list = None, dstr = '=>'):
    print(f"\n--- {title} ---")
    if (len(market_prices_60min) > 0) and (len(prices_15min) > 0):
        for hour, price in enumerate(market_prices_60min):
            start_time = f"{hour:02d}:00"
            end_time   = f"{(hour + 1):02d}:00"
            market_price = price
            import_price = import_prices_60min[hour] if import_prices_60min else 0
            export_price = export_prices_60min[hour] if export_prices_60min else 0
            price1 = prices_15min[4*hour + 0]
            price2 = prices_15min[4*hour + 1]
            price3 = prices_15min[4*hour + 2]
            price4 = prices_15min[4*hour + 3]
            print(f"{start_time} - {end_time} : € {market_price:7.4f},{import_price:7.4f},{export_price:7.4f} {dstr} 1={price1:7.4f}, 2={price2:7.4f}, 3={price3:7.4f}, 4={price4:7.4f}")    
    else:
        print(f"No prices available for 60 minutes list ({len(market_prices_60min)}) and/or 15 minutes list ({len(prices_15min)})!")    
    press_esc_or_key() # Wait for user input to continue (press ESC to exit or any key to continue)

#########################################################################################
# TEST DATA for helios_main.py and for EnergyPriceConversion.py                         #
#########################################################################################

# Testdata: HBC Price Sensor from Home Assistant
MOCK_HBC_IMPORT_PRICE_RESPONSE = {
    "unit_of_measurement": "cents/kWh",
    "friendly_name": "HBC energy prices data",
    "prices": [30.42,31.44,32.46,32.48,32.40,28.96], # Simple HBC Price Array
    "start": "2026-09-17T00:00:00+02:00",
    "datapoints_per_hour": 1,
    "marks": [ # Marks with the HBC Price Array:
        {"start": "2026-08-15T22:00:00.000Z", "price": 30.42, "end": "2026-09-16T23:00:00.000Z", "mark": "low", "is_now": False}, # Local 16-aug 00:00, Market: 0.1225, Import: 0.3042, Export: 0.1382 
        {"start": "2026-08-15T23:00:00.000Z", "price": 16.00}, # Local 16-aug 01:00                                                                   , Market: 0.0033, Import: 0.1600, Export:-0.0114   
        {"start": "2026-08-16T00:00:00.000Z", "price": 15.60}, # Local 16-aug 02:00                                                                   , Market: 0.0000, Import: 0.1560, Export:-0.0154
        {"start": "2026-08-16T01:00:00.000Z", "price": 15.20}, # Local 16-aug 03:00                                                                   , Market:-0.0033, Import: 0.1520, Export:-0.0194
        {"start": "2026-08-16T02:00:00.000Z", "price":  0.00}, # Local 16-aug 04:00                                                                   , Market:-0.1290, Import: 0.0000, Export:-0.1714
        {"start": "2026-08-16T20:00:00.000Z", "price": -2.40}, # Local 16-aug 22:00                                                                   , Market:-0.1488, Import:-0.0240, Export:-0.1954
        {"start": "2026-08-17T05:00:00.000Z", "price":-21.96}, # Local 17-aug 31:00                                                                   , Market:-0.3104, Import:-0.2196, Export:-0.3910
        {"start": "2026-08-17T08:00:00.000Z", "price": 15.00}, # Local 17-aug 34:00, Market Average 10:00-10:45 is 16.50 (4x quarter hours)           , Market: 0.0074, Import: 0.1650, Export:-0.0064 AVERAGE 4Q
                                                               #                                                                                      , Market:-0.0050, Import: 0.1500, Export:-0.0214 1Q
        {"start": "2026-08-17T08:15:00.000Z", "price": 16.00}, # Local 17-aug 34:15                                                                   , Market: 0.0033, Import: 0.1600, Export:-0.0114 2Q
        {"start": "2026-08-17T08:30:00.000Z", "price": 17.00}, # Local 17-aug 34:30                                                                   , Market: 0.0115, Import: 0.1700, Export:-0.0014 3Q
        {"start": "2026-08-17T08:45:00.000Z", "price": 18.00}, # Local 17-aug 34:45                                                                   , Market: 0.0198, Import: 0.1800, Export: 0.0086 4Q
        {"start": "2026-08-17T10:00:00.000Z", "price": 16.00}, # Local 17-aug 36:00, Back to 16.00 for 12:00                                          , Market: 0.0033, Import: 0.1600, Export:-0.0114 Hour
    ]
}

# Testdata: Frank Energie API Example
# sensor.frank_energie_prices_current_electricity_market_price (in UTC zone: +00:00)
# Let op: Frank geeft UTC tijden door dus 2026-08-15T22:00:00+00:00 is in de zomer  gelijk aan de start van 16-aug op 00:00 (ipv 15-aug 22:00)! 
# Let op: Frank geeft UTC tijden door dus 2026-11-15T23:00:00+00:00 is in de winter gelijk aan de start van 16-nov op 00:00 (ipv 15-nov 23:00)! 
MOCK_FRANK_MARKET_60min = { # Let op: 60 min prijzen maar met afwijkingen met 15 en 30 min prijzen en veel gaten
    "attributes": {
        "prices": [
            # Let op UTC: 15-aug 22:00 -> NL Zomertijd: 16-aug 00:00, maar in de winter UTC 15-nov 23:00 -> NL Wintertijd: 16-nov 00:00 !!!!
            # Kwartier prijzen 
            {"from": "2026-08-15T22:00:00+00:00", "till": "2026-08-15T22:15:00+00:00", "price": 0.0800}, # 16-aug 00:00 (UTC: 15-aug 22:00), Import: 0.2528 Export: 0.0814, Gemiddelde over 4 prijzen (0.1000, 02770, 0.1056) gebruikt voor uur prijzen
            {"from": "2026-08-15T22:15:00+00:00", "till": "2026-08-15T22:30:00+00:00", "price": 0.1200}, # 16-aug 00:00 (UTC: 15-aug 22:00), Import: 0.3012 Export: 0.1298 
            {"from": "2026-08-15T22:30:00+00:00", "till": "2026-08-15T22:45:00+00:00", "price": 0.1000}, # 16-aug 00:00 (UTC: 15-aug 22:00), Import: 0.2770 Export: 0.1056
            {"from": "2026-08-15T22:45:00+00:00", "till": "2026-08-15T23:00:00+00:00", "price": 0.1000}, # 16-aug 00:00 (UTC: 15-aug 22:00), Import: 0.2770 Export: 0.1056 

            # Half Uur prijzen
            {"from": "2026-08-15T23:00:00+00:00", "till": "2026-08-16T00:00:00+00:00", "price": 0.0400}, # 16-aug 01:00 - 02:00/01:15      , Import: 0.2044 Export: 0.0330, Gemiddelde over 2 prijzen (0.0800, 02528, 0.0814) gebruikt voor uur prijzen
            {"from": "2026-08-15T23:30:00+00:00", "till": "2026-08-16T00:00:00+00:00", "price": 0.1200}, # 16-aug 01:30        /02:45      , Import: 0.3012 Export: 0.1298

            # Uur prijzen maar wel met gaten tussen de uren die door de laatst beschikbare prijs moet worden opgevuld
            {"from": "2026-08-16T01:00:00+00:00", "till": "2026-08-16T02:00:00+00:00", "price":-0.0500}, # 16-aug 03:00 - 05:00            , Import: 0.0955 Export:-0.0759, Neg Market, Pos Import, Neg Export
            {"from": "2026-08-16T04:00:00+00:00", "till": "2026-08-16T05:00:00+00:00", "price":-0.3000}, # 16-aug 06:00 - 10:00            , Import:-0.2070 Export:-0.3784, Neg Market, Neg Import, Neg Export
            {"from": "2026-08-16T09:00:00+00:00", "till": "2026-08-16T10:00:00+00:00", "price": 0.0100}, # 16-aug 11:00 - 22:00            , Import: 0.1681 Export:-0.0033, Pos Market, Pos Import, Neg Export

            # Uur prijs voor 23:00 maar ook voor de volgende dag 00:00
            {"from": "2026-08-16T21:00:00+00:00", "till": "2026-08-16T22:00:00+00:00", "price": 0.1400}, # 16-aug 23:00 - 24:00/24:45 (UTC: 16-aug 21:00), Import: 0.3254 Export: 0.1540

            # Uur prijzen op de volgende dag (maar 00:00 ontbreekt en slecht 2 uren beschikbaar) => telt als een extra dag (voor morgen) en de rest wordt aangevuld
            # Geen prijs voor 00:00, daarvoor wordt de laatste prijs (0.1400) van vorige dag gebruikt, tenzij vorige dag niet wordt meegenomen, dan wordt de eerste prijs (0.04) van deze dag gebruikt
            {"from": "2026-08-16T23:00:00+00:00", "till": "2026-08-17T00:00:00+00:00", "price": 0.0400}, # 17-aug 25:00 - 29:00/29:45 (UTC: 16-aug 23:00), Import: 0.2044 Export: 0.0330
            {"from": "2026-08-17T04:00:00+00:00", "till": "2026-08-17T05:00:00+00:00", "price": 0.0800}, # 17-aug 30:00 - 37:00/38:00 (UTC: 17-aug 04:00), Import: 0.2528 Export: 0.0814

            # 3 Kwartier prijzen op de volgende dag (gemiddelde over 3 prijzen genomen voor uur prijs, begint niet op het hele uur, hiervoor vorige kwartier prijs 0.0800 genomen bij kwartier prijzen) 
            {"from": "2026-08-17T12:15:00+00:00", "till": "2026-08-17T12:30:00+00:00", "price": 0.1200}, # 17-aug 38:15 - 40:00       (UTC: 16-aug 12:15), Import: 0.3012 Export: 0.1298, Gemiddelde over 3 prijzen (0.1000, 0.2770, 0.1056) gebruikt voor uur prijzen
            {"from": "2026-08-17T12:30:00+00:00", "till": "2026-08-17T12:45:00+00:00", "price": 0.1000}, # 17-aug 38:30               (UTC: 17-aug 12:30), Import: 0.2770 Export: 0.1056
            {"from": "2026-08-17T12:45:00+00:00", "till": "2026-08-17T13:00:00+00:00", "price": 0.0800}, # 17-aug 38:45 -      /40:45 (UTC: 17-aug 12:45), Import: 0.2528 Export: 0.0814

            # 3 Kwartier prijzen op de volgende dag (gemiddelde over 3 prijzen genomen voor uur prijs, mist het 2e kwartier, hiervoor vorige kwartier prijs 0.1000 genomen bij kwartier prijzen) 
            {"from": "2026-08-17T15:00:00+00:00", "till": "2026-08-17T15:15:00+00:00", "price": 0.1400}, # 17-aug 41:00 - 47:00/41:15 (UTC: 16-aug 15:00), Import: 0.3254 Export: 0.1540, Gemiddelde over 3 prijzen (0.1200, 0.3012, 0.1298) gebruikt voor uur prijzen
            {"from": "2026-08-17T15:30:00+00:00", "till": "2026-08-17T15:45:00+00:00", "price": 0.1200}, # 17-aug 41:30               (UTC: 17-aug 15:30), Import: 0.3012 Export: 0.1298
            {"from": "2026-08-17T15:45:00+00:00", "till": "2026-08-17T16:00:00+00:00", "price": 0.1000}, # 17-aug 41:45 -      /47:45 (UTC: 17-aug 15:45), Import: 0.2770 Export: 0.1056              
        ]
    }
}
MOCK_FRANK_MARKET_60min_ZULU = { # Zelfde info als hierboven (Zulu is gelijk UTC zone: +00:00) maar alleen uren prijzen (geen kwartier prijzen die gemiddeld worden)
    "attributes": {
        "prices": [
            {"from": "2026-08-15T22:00:00Z", "till": "2026-08-15T23:00:00Z", "price": 0.1000}, # 16-aug 00:00 (UTC: 15-aug 22:00), Import: 0.2770 Export: 0.1056
            {"from": "2026-08-15T23:00:00Z", "till": "2026-08-16T00:00:00Z", "price": 0.0800}, # 16-aug 01:00                    , Import: 0.2528 Export: 0.0814
            {"from": "2026-08-16T01:00:00Z", "till": "2026-08-16T02:00:00Z", "price":-0.0500}, # 16-aug 03:00                    , Import: 0.0955 Export:-0.0759, Neg Market, Pos Import, Neg Export
            {"from": "2026-08-16T04:00:00Z", "till": "2026-08-16T05:00:00Z", "price":-0.3000}, # 16-aug 06:00                    , Import:-0.2070 Export:-0.3784, Neg Market, Neg Import, Neg Export
            {"from": "2026-08-16T09:00:00Z", "till": "2026-08-16T10:00:00Z", "price": 0.0100}, # 16-aug 11:00                    , Import: 0.1681 Export:-0.0033, Pos Market, Pos Import, Neg Export
            {"from": "2026-08-16T21:00:00Z", "till": "2026-08-16T22:00:00Z", "price": 0.1400}, # 16-aug 23:00 (UTC: 16-aug 21:00), Import: 0.3254 Export: 0.1540
                
            {"from": "2026-08-16T23:00:00Z", "till": "2026-08-17T00:00:00Z", "price": 0.0400}, # 17-aug 25:00 (UTC: 16-aug 23:00), Import: 0.2044 Export: 0.0330
            {"from": "2026-08-17T04:00:00Z", "till": "2026-08-17T05:00:00Z", "price": 0.0800}, # 17-aug 30:00 (UTC: 17-aug 04:00), Import: 0.2528 Export: 0.0814
            {"from": "2026-08-17T12:00:00Z", "till": "2026-08-17T13:00:00Z", "price": 0.1000}, # 17-aug 38:00 (UTC: 17-aug 12:00), Import: 0.2770 Export: 0.1056
            {"from": "2026-08-17T15:00:00Z", "till": "2026-08-17T16:00:00Z", "price": 0.1200}, # 17-aug 41:00 (UTC: 17-aug 15:00), Import: 0.3012 Export: 0.1298
        ]
    }
}
MOCK_FRANK_MARKET_60min_LT = { # Zelfde info als hierboven maar zonder timezone info (moet dus lokale tijd zijn)
    "attributes": {
        "prices": [
            {"from": "2026-08-16T00:00:00", "till": "2026-08-16T01:00:00", "price": 0.1000}, # 16-aug 00:00 (NL Local time), Import: 0.2770 Export: 0.1056
            {"from": "2026-08-16T01:00:00", "till": "2026-08-16T02:00:00", "price": 0.0800}, # 16-aug 01:00                , Import: 0.2528 Export: 0.0814
            {"from": "2026-08-16T03:00:00", "till": "2026-08-16T04:00:00", "price":-0.0500}, # 16-aug 03:00                , Import: 0.0955 Export:-0.0759, Neg Market, Pos Import, Neg Export
            {"from": "2026-08-16T06:00:00", "till": "2026-08-16T07:00:00", "price":-0.3000}, # 16-aug 06:00                , Import:-0.2070 Export:-0.3784, Neg Market, Neg Import, Neg Export
            {"from": "2026-08-16T11:00:00", "till": "2026-08-16T12:00:00", "price": 0.0100}, # 16-aug 11:00                , Import: 0.1681 Export:-0.0033, Pos Market, Pos Import, Neg Export
            {"from": "2026-08-16T23:00:00", "till": "2026-08-17T00:00:00", "price": 0.1400}, # 16-aug 23:00                , Import: 0.3254 Export: 0.1540
                
            {"from": "2026-08-17T01:00:00", "till": "2026-08-17T02:00:00", "price": 0.0400}, # 17-aug 25:00 / 00:01        , Import: 0.2044 Export: 0.0330
            {"from": "2026-08-17T06:00:00", "till": "2026-08-17T07:00:00", "price": 0.0800}, # 17-aug 30:00 / 00:06        , Import: 0.2528 Export: 0.0814
            {"from": "2026-08-17T14:00:00", "till": "2026-08-17T15:00:00", "price": 0.1000}, # 17-aug 38:00 / 14:00        , Import: 0.2770 Export: 0.1056
            {"from": "2026-08-17T17:00:00", "till": "2026-08-17T18:00:00", "price": 0.1200}, # 17-aug 41:00 / 17:00        , Import: 0.3012 Export: 0.1298
        ]
    }
}
MOCK_FRANK_MARKET_15min = {
    "attributes": {
        "prices": [ 
            # Warning: The old price parsing has a problem with the average hour price, 
            #   The last (15min) price found is used in the next steps but the average of the last hour found is also used in the next hours
            #   The average price is calculated with the available prices (so from 2 prices if only 2 15min prices are available, which can already be wrong when the 3e and 4e 15min price are missing)
            #   Even worse in the next hours without a 15min price the average is repeated while the last price is also repeated 4 times, so the average should be the last price
            {"from": "2026-08-15T22:00:00+00:00", "till": "2026-08-15T22:15:00+00:00", "price": 0.1000}, # 16-aug 00:00 (NL Summertime), wordt in de winter 23:00 - 23:15
            {"from": "2026-08-15T22:15:00+00:00", "till": "2026-08-15T22:30:00+00:00", "price": 0.0800}, # 16-aug 00:15 (15 min)
            {"from": "2026-08-15T22:30:00+00:00", "till": "2026-08-15T22:45:00+00:00", "price": 0.1000}, # 16-aug 00:30 (15 min)
            {"from": "2026-08-15T22:45:00+00:00", "till": "2026-08-15T23:00:00+00:00", "price": 0.1200}, # 16-aug 00:45 (15 min), Average  0.1000, Import: 0.2793 Export: 0.0944 

            {"from": "2026-08-15T23:00:00+00:00", "till": "2026-08-15T23:15:00+00:00", "price": 0.1000}, # 16-aug 01:00 (15 min), Warning: Missing periods will give an average of less prices (avg of 2 iso 4 prices), also for following periods !!!!!
            {"from": "2026-08-15T23:45:00+00:00", "till": "2026-08-16T00:00:00+00:00", "price": 0.0600}, # 16-aug 01:45 (45 min), Average  0.0800, Import: 0.2551 Export: 0.0702 

            {"from": "2026-08-16T01:00:00+00:00", "till": "2026-08-16T01:15:00+00:00", "price":-0.0700}, # 16-aug 03:00 (15 min)
            {"from": "2026-08-16T01:15:00+00:00", "till": "2026-08-16T01:30:00+00:00", "price":-0.0300}, # 16-aug 03:15 (15 min)
            {"from": "2026-08-16T01:30:00+00:00", "till": "2026-08-16T01:45:00+00:00", "price":-0.0400}, # 16-aug 03:30 (15 min)
            {"from": "2026-08-16T01:45:00+00:00", "till": "2026-08-16T02:00:00+00:00", "price":-0.0600}, # 16-aug 03:45 (15 min), Average -0.0500, Import: 0.0978 Export:-0.0871

            {"from": "2026-08-16T13:00:00+00:00", "till": "2026-08-16T14:00:00+00:00", "price": 0.0400}, # 16-aug 15:00 (60 min), Average  0.0400, Import: 0.2067 Export: 0.0218 - No Average just using the one price

            {"from": "2026-08-16T14:00:00+00:00", "till": "2026-08-16T15:00:00+00:00", "price": 0.0100}, # 16-aug 16:00 (60 min), Average  0.0100, Import: 0.1704 Export:-0.0145 - idem

            {"from": "2026-08-16T17:00:00+00:00", "till": "2026-08-16T17:15:00+00:00", "price": 0.1400}, # 16-aug 19:00 (15 min)
            {"from": "2026-08-16T17:15:00+00:00", "till": "2026-08-16T17:30:00+00:00", "price": 0.1800}, # 16-aug 19:15 (15 min)
            {"from": "2026-08-16T17:30:00+00:00", "till": "2026-08-16T17:45:00+00:00", "price": 0.1100}, # 16-aug 19:30 (15 min)
            {"from": "2026-08-16T17:45:00+00:00", "till": "2026-08-16T18:00:00+00:00", "price": 0.1300}, # 16-aug 19:45 (15 min), Average  0.1400, Import: 0.3277 Export: 0.1428
        ]
    }
}