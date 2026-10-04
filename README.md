# HA Helios Optimizer - Readme
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

## Intro
The **HELIOS Optimizer** Service is a Home Assistant PyScript Application designed to calculate mathematically an optimal energy plan.
The calculation uses **SciPy Linear/MILP Programming** to optimize the Energy Plan 
for **Dynamic** Prices, **Solar** Production, **Battery** Charging/Discharging and **House** Energy Usage.
<br><br>
The Helios Optimizer calculates for each step in the optimization period the optimal value of power variables

**Remark:** The Current Version is PyScript Service that is installed in the pyscript folder.
For optimal performance the PyScript Service calls the Helios Optimizer Calculate Plan function which runs in an asynchronous native python thread.
In the future the Helios Service will be migrated to a Home Assistant Custom Component.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Features
- **LP/MILP Optimization:** Uses SciPy linear programming to maximize profit and minimize energy costs.
- **HBC Ready:** Retrieves Parameters and Prices from HBC and creates output for HBC (Sub Strategy and Power)
- **HA PyScript/Python Application:** Runs within PyScript and native Python and does not require an external engine.
- **Fast:** Lightweight execution that optimizes 192 steps of 15 minutes (for 2 days) within 500ms per Optimization Run.
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
Helios calculates an optimized energy plan for a specified horizon (typically 2 days)
by finding the optimal power setpoints (for battery charge/discharge, grid import/export and solar production) for each step in the optimization period.
The most important optimization rule defines that the incoming power (Discharge, Import and Solar Production) and the outgoing power (Charge, Export and House Usage) must always be equal. 
In addition the model will keep the Charge/Discharging Power below the Battery Charge/Discharge Limit values and the Import/Export Power below the Maximum Grid Import/Export values.
Solar Production will be equal to the Solar Forecast unless the Solar Inverter can be modulated (dimmed) or turned on and off.
 
The planning horizon is defined by the number of steps and the step duration in minutes.
For example: 48 steps of 60 minutes or 192 steps of 15 minutes both optimize a 2-day period.
 
Grid Import and Export Prices, Solar Energy Forecast and House Energy Forecasts are needed as Input Arrays, containing values for every step in the period.
HBC Price Data can be used as an alternative source for the Import and Export Price arrays.
House Daily Usage and Distribution can be provided as an alternative source for the House Energy Forecast array.
 
Total Energy Cost is the sum of energy costs per step (calculated for Grid Import and Export Power).
To compensate for battery depreciation cost a discharge (default 0.01 euro) and charge cost (default 0.00) is included in the Total Energy Cost.
A cost for charging and/or discharging will also prevent the model from charging and discharging at the same time.
The optimizer aims to MINIMIZE the Total Energy Cost over the entire horizon.
Note: Negative costs may occur when exporting energy to the grid or during negative import prices.
 
Note: Without a battery or deferrable loads, optimization opportunities are limited
since a strict power balance between consumption, import, and export must be met in each step.
 
The optimization horizon always starts today (and optionally extends to the following days).
By default (with a start step of 0), the active start step is calculated based on the current time.
Optionally, a specific start step can be defined (e.g., step 1 to start at 00:00) but this is mainly meant for (regression) testing.
All input arrays must start at 00:00 today so the optimizer can align prices and forecasts correctly.
Again for (regression) testing purposes a specific optimizer timestamp can be provided that runs the optimizer for a specific date and time (instead of for the current date and time).
 
The resulting Optimized Energy Plan determines the active strategy for the current step
(e.g., NOM, Buy, Sell, Charge, Discharge, Disabled) and provides real-time setpoints
to steer the Battery Charge/Discharge, the Solar Production and (in the future) the Deferrable Loads.
 
## Required inputs
- Configuration (steps, step size, start step, solver time/iteration limits, grid limits)
- Grid Import Prices array (import price per step) or Source Price Data or Sensor
- Grid Export Prices array (export price per step) or Source Price Data or Sensor
- House Energy Consumption Forecast (without deferrable loads) array or House Daily Usage and Distribution
 
## Optional inputs
- Solar Forecast array and other Solar parameters
- Battery parameters
 
## Optional deferrable loads (Future):
- Electric Vehicle (EV) charging profile
- Heat Pump (HP) operation parameters
- Boiler operation parameters

## What's New:
See [Helios Optimizer Release Notes](RELEASE_NOTES.md)

## Documentation with Input and Output
For a detailed specification of the Input Parameters and the Output Results (Optimized Energy Plan)
see [Helios Optimizer Documentation](DOC.md).

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

**README** - [Documentation](DOC.md) - [Installation](INSTALL.md) - [Release Notes](RELEASE_NOTES.md) - [License](LICENSE "GitHub Docs")
