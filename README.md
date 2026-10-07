# HA Helios Optimizer - Readme
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

## Intro 
The **HELIOS Optimizer Service** is a **H**ome **A**ssistant **PyScript** Application designed to calculate a Mathematically **Optimal Energy Plan**.
The calculation uses **SciPy Linear/Mixed-Integer Linear Programming (LP/MILP)** 
to find the financially **Optimal** Energy Management **Strategy** for Charging, Discharging and Solar Production
based on dynamic Electricity Prices, Solar Forecasts, Battery storage and expected Household Energy Usage.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Why Use a Linear Programming Energy Model:
See [Helios Optimizer Why LP](WHY.md)

## Features
- **LP/MILP Optimization:** Uses SciPy **Linear Programming** to **maximize** profit and **minimize** energy costs.
- **HBC Ready:** Retrieves Parameters and Prices from **HBC** and creates output for HBC (Sub Strategy and Power)
- **HA PyScript/Python Application:** Runs within **PyScript** and native **Python** and does not require an external engine.
- **Fast:** Lightweight execution that optimizes 192 steps of 15 minutes (for 2 days) within 500ms per Optimization Run.
- **Asynchronous:** Actual calculation is executed directly into the HA core **asynchronous** loop.
- **Zero-Config Setup:** Out-of-the-box **defaults** let you run a test optimization immediately without configuration.
- **Independent:** Open design compatible with any dynamic pricing, solar forecast and house usage forecast.
- **Flexible Horizon & Intervals:** Calculates the Optimal Energy Plan for one or two day(s) with 15-minute or 60-minute intervals (step sizes).
- **Dynamic Recalculation:** Runs automatically from the current timestamp (based on current state) or from a user-defined step (for testing).
- **Clean Data Structure:** Simple full-day input and output arrays (00:00-24:00/48:00).

## Roadmap (2026-2027)
- **Energy Providers:** Add additional **Energy Providers** with their related Provider Markups (Opslag).
- **HBC Integration:** Helios Strategy as a **native HBC strategy** using the Helios Optimizer Output.
- **House Usage History:"** Determine House Usage **Forecast** from House Usage **History**.
- **Solar Forecast:** Support for **Solcast** as an additional Solar Production prediction.
- **Additional Models:** Profit Optimization is implemented, Additional models are **Cost Optimization** and **Self Consumption**.
- **Device Support:** **EV** (highest priority), **Heat Pump**, and **Boiler** support (as **Deferrable** Devices).
- **Native HA Integration:** Pure Python Home Assistant **Custom Component** (HACS-ready), run without PyScript or external engines.
- **Modular Connectors:** Dedicated modules for **Energy Providers**, **Solar Forecasts**, Battery and Solar Inverter **Integrations**.

## Required inputs
- **Configuration Input** (Steps, Step size, Start Step, Solver Time/Iteration limits, Grid Limits)
- Grid **Import Prices** array (import price per step) or Source Price Data or Sensor
- Grid **Export Prices** array (export price per step) or Source Price Data or Sensor
- House Energy **Usage Forecast** (without deferrable loads) array or average House Daily Usage and Distribution
 
## Optional inputs
- **Solar Forecast**  array and other **Solar Parameters**
- **Battery Parameters**
 
## Optional deferrable loads (Future):
- **Electric Vehicle** (EV) charging profile
- **Heat Pump** (HP) operation parameters
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

# Interest Poll (Dutch)
**[Helios Optimizer Interest Poll Results in Dutch](HELIOS_PEILING.md)**

# License
**[Helios Optimizer License](https://github.com/Jos1958/ha-helios-optimizer/blob/main/LICENSE)**

# FAQ and Help

**Keywords:** Battery Management System, Energy Management System, Optimize your Energy Plan, Solar Panels, Home and House Automation, Home Assistant, HBC, Linear Programming, Python, PyScript

**README** - [Doc](DOC.md) - [Why LP](WHY.md) - [Install](INSTALL.md) - [Release Notes](RELEASE_NOTES.md)
