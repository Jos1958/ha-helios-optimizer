# Installation of Home Assistant Helios Optimizer (ha-helios-optimizer)
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

## Installation
- **Prerequisites:**
  - HACS installation on your Home Assistant System
  - File Editor (or Samba) via HACS: to create folders and upload files
  - PyScript installation via HACS 
    - Integrations: Pyscript Python scripting - pyscript - <Configurate>
      V Allow All Imports?
      V Access hass as a global variable?
      _ Use legacy decorators? (Not required)
  - For the Helios Dashboard (UI-components)
    - ApexCharts Card (via HACS)
    - card-mod (via HACS)
    - Markdown Card (built-in)
    - Picture (built-in) for /local/HeliosOptimizerBanner.jpeg in www-folder
    
- **Installation of Helios Optimizer:**
  - Download and Unpack the HeliosOptimizer.zip file
  - Use the File Editor or Samba to copy the following files to Home Assistant
    Create the packages, pyscrip, modules (sub-folder), export and www folder when they do not yet exist
  - File Structure 
    [HomeAssistant] also called [config] folder
       [packages]
  V       helios_optimizer.yaml        - Helios Templates, Input Numbers and Selects
  V       helios_optimizer_config.yaml - forecast.solar REST API <== configure with your location and solar panels
       [pyscript]
  V       helios_services.py         - Helios Services file which defines the Helios Services for Home Assistant using PyScript
          [modules]
  V          helios_optimizer.py     - Optimizer with the Calculation of the Energy Plan (Pure Python functions)
  V          helios_common.py        - Common Python functions
  V          helios_prices.py        - Energy Price Parser Class (for HBC Price and Provider Price Data)
       [export]
  -       helios_optimizer_output.json (optional output file for debugging) 
       [www]
  V       HeliosOptimizerBanner.jpeg - banner picture for the Dashboard
  
  - helios_automation.yaml           - contains the automation.helios_optimizer_task 
  - configuration.yaml               - required already for HBC, not sure if /config/export as external dir is required
    homeassistant:
      packages: !include_dir_named packages
      allowlist_external_dirs:
        - /config/export    
    
- **Automation:**
  * todo

- **Dashboard:**
  * todo   

- **HACS:** 
  * Not supported yet (see Helios Calculator)

