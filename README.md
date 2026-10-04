# HA Helios Optimizer - Readme
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

## Intro
The **HELIOS Optimizer** Service is a Home Assistant PyScript Application designed to calculate mathematically an optimal energy plan.
The calculation uses **SciPy Linear/MILP Programming** to optimize the Energy Plan 
for **Dynamic** Prices, **Solar** Production, **Battery** Charging/Discharging and **House** Energy Usage.
<br><br>
The Optimizer calculates for each step in the optimization period the optimal value of power variables

?? **[Helios Optimizer - Readme](README.md)**
?? **[Helios Optimizer - Documentation](DOC.md)**
?? **[Helios Optimizer - Installation](INSTALL.md)**
?? **[Helios Optimizer - Release Notes](RELEASE_NOTES.md)**

**Remark:** The Current Version is PyScript Service that is installed in the pyscript folder.
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
HBC Price Data can be used as an alternative source for the import and export price arrays.

 
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
- Grid import prices array (import price per step) or Source Price Data or Sensor
- Grid export prices array (export price per step) or Source Price Data or Sensor
- House consumption forecast (without deferrable loads) array or House Dialy Usage and Distribution
 
## Optional inputs
- Solar production forecast array
- Battery parameters
 
## Optional deferrable loads (Future):
- Electric Vehicle (EV) charging profile
- Heat Pump (HP) operation parameters
- Boiler operation parameters

## What's New:
?? **[Helios Optimizer Release Notes](RELEASE_NOTES.md)**
-- **Proof of Concept**:

## Documentation
?? **[Helios Optimizer Documentation](DOC.md)**

## Advanced

## Updating

## Credits

## Contributing
At the moment it is not advised to develop additional features based on the current version.
The current code is not very stable yet so your changes may not work on the next release.
Only small bug fixes will be accepted.
Please raise an issue to report a bug or to request for new functionality.

# License
?? **[Helios Optimizer License](LICENSE.)**

# Help

**Keywords:** Battery Management System, Energy Management System, Optimize your Energy Plan, Solar Panels, Home Automation, Home Assistant
