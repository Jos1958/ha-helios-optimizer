# Readme for Home Assistant Helios Optimizer (ha-helios-optimizer)
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

## Intro
The **HELIOS Optimizer** Service is a Home Assistant PyScript Application designed to calculate mathematically an optimal energy plan.
The calculation uses **SciPy Linear/MILP Programming** to optimize the Energy Plan 
for **Dynamic** Prices, **Solar** Production, **Battery** Charging/Discharging and **House** Energy Usage.

**WARNING:** The Current Version is PyScript Service that is installed in the pyscript folder.
For optimal performance the PyScript Service calls the Helios Optimizer Calculate Plan function which runs in an asynchronous native python thread.
In the future the Helios Service will be migrated to a Home Assistant Custom Component.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Features
- **LP/MILP Optimization:** Uses SciPy linear programming to maximize profit and minimize energy costs.
- **HBC Ready:** Retrieves Parameters and Prices from HBC and creates output for HBC (Sub Strategy and Power)
- **HA PyScript/Python Application:** Runs within PyScript and native Python and does not require an external engine.
- **Fast:** Lightweight execution that optimizes 192 steps of 15 minutes (for 2 days) within 500ms per run
- **Asynchronous & Fast:** Lightweight execution built directly into the HA core asynchronous loop.
- **Zero-Config Setup:** Out-of-the-box defaults let you run a test optimization immediately without configuration.
- **Independent:** Open design compatible with any dynamic priced, solar, battery and house usage forecast.
- **Flexible Horizon & Intervals:** Calculates the energy plan for one or two day(s) with 15-minute or 60-minute intervals (step size).
- **Dynamic Recalculation:** Runs automatically from the current timestamp or from a user-defined step.
- **Clean Data Structure:** Simple full-day input and output arrays (00:00-24:00/48:00).

## Roadmap
- **HBC Integration:** Helios Strategy as a native HBC strategy using the Helios Output 
- **Native HA Integration:** Pure Python custom component (HACS-ready), runs without PyScript or external engines.
- **Device Support:** EV, Heat Pump, and Boiler integration (deferrable devices).
- **Modular Connectors:** Dedicated modules for energy providers, solar forecasts, battery integrations and solar inverter integrations.

## Description
Helios calculates an optimized energy plan for a specified horizon (typically 1 to 2 days)
by finding the optimal power setpoints (for battery charge/discharge, grid import/export and solar production) for each step in the optimization period.
 
The planning horizon is defined by the number of steps and the step duration in minutes.
For example: 24 steps of 60 minutes optimizes a 1-day period.
 
Grid import/export prices and house load forecasts must be provided as input arrays,
containing values for every step in the period.
 
Total Energy Cost is the sum of energy costs per step (calculated from grid import and export power).
The optimizer aims to MINIMIZE the Total Energy Cost over the entire horizon.
Note: Negative costs may occur when exporting energy to the grid or during negative import prices.
 
Note: Without a battery or deferrable loads, optimization opportunities are limited
since a strict power balance between consumption, import, and export must be met in each step.
 
The optimization horizon always starts today (and optionally extends to following days).
By default, the active start step is calculated based on the current time.
Optionally, a specific start step can be defined (e.g., step 1 to start at 00:00).
All input arrays must start at 00:00 today so the optimizer can align prices and forecasts correctly.
 
The resulting Optimized Energy Plan determines the active strategy for the current step
(e.g., NOM, Buy, Sell, Charge, Discharge, Disabled) and provides real-time setpoints
to steer the battery and (TODO) deferrable loads.
 
## Required inputs
- Configuration (steps, step size, start step, solver time/iteration limits, grid limits)
- Grid import prices array (import price per step)
- Grid export prices array (export price per step)
- House consumption forecast (without deferrable loads) array 
 
## Optional inputs
- Solar production forecast array
- Battery parameters
 
## Optional deferrable loads (Future):
- Electric Vehicle (EV) charging profile
- Heat Pump (HP) operation parameters
- Boiler operation parameters

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
       automation.yaml               - contains the automation.helios_optimizer_task 
       configuration.yaml
       
  - configuration.yaml
    - 
    
- **HACS:** 
  * On the HACS Dashboard: **Search** for "Helios Optimizer"
  * Click the **"Helios Calculator"** to open the Helios README page with the <Download> button
  * Press the **"Download"** button to download the Helios Calculator (to /config/custom_components/helios_calculator)
  * **Herstart** Home Assistant

- **Integration:**
  * Open the Integration Page (**Settings** -> **Devices and Services** - **[Integrations]**)
  * Press the **+ Add Integration** button
  * Search for "Helios Calculator"
  * Click the "Helios Calculator"
  * A Popup appears for the Helios Calculator with a "Send" button
  * Press **Send** to add the integration 
  * A popup appears: "Configuration created for Helios Calculator" with a "Complete" button
  * Press **Complete** to close the popup
  * **Note:** All further configuration is done in the call to Helios Calculator Service  

- **Automation:**
  * todo

- **Dashboard:**
  * todo   

## What's New:
?? **[Release Notes](RELEASE_NOTES.md)**
-- **Proof of Concept**:

## Documentation
?? **[Helios Calculator Documentation](DOC.md)**

## Advanced

## Updating

## Credits

## Contributing
At the moment it is not advised to develop additional features based on the current version.
The current code is not very stable yet so your changes may not work on the next release.
Only small bug fixes will be accepted.
Please raise an issue to report a bug or to request for new functionality.

# License

# Help

**Keywords:** Solar Panels, Battery, Home Automation, Home Assistant, Optimize your Energy Plan
