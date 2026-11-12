# HA Helios Optimizer - Readme
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)
**README** - [Doc](DOC.md) - [Why LP](WHY.md) - [Install](INSTALL.md) - [Release Notes](RELEASE_NOTES.md)

## Intro 
For an Introduction to the Helios Optimizer: see [Helios Optimizer - Documentation](DOC.md#intro).

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Why Use a Linear Programming Energy Model:
See [Helios Optimizer Why LP](WHY.md)

## Installation:
- Prerequisites: 
  - **PyScript (Via HACS)**: Configuration with V Allow All Imports and V Hass Access (**VERY IMPORTANT**).
  - **Forecast.Solar** Integration: Configured Solar Panels (pane).
  - **Dynamic Price Integration** (working dynamic prices in HBC): Helios uses the **dynamic prices** of HBC!
  - **Additional Dashboard Cards (via HACS)**: ApexCharts, card-mod and button-card .
- **Download** the latest version from [GitHub](https://github.com/Jos1958/ha-helios-optimizer/releases).
- Create the **missing folders** in Home Assistant.
- Copy the **py files** to /pyscript and /pyscript/helios_python
- Copy the **configuration** file (helios_optimizer.yaml) to /packages
- Copy the **banner** file (HeliosOptimizerBanner.jpeg) to /www
- **Create** a new Home Assistant **Dashboard** for Helios (from helios_dashboard.yaml including the **views:** line at the top).
- Or **Add** the Helios Tabs to the HBC Dashboard yaml (from helios_dashboard.yaml but excluding the **views:** line).
- Import the **Helios Strategy Flow** (02 strategy-helios-vx.xx.x-vy.y.y.json) in Node-RED and [Deploy].
- **Add** the **"Helios"** strategy to the options of input_select.house_battery_strategy in the HBC configuration file (house_battery_control.yaml).
- **Restart** Home Assistant.
- Adapt the **parameters** on the Helios Dashboard (Controls Tab) but try using the defaults at first.
- For a **Dry Run:** Select the **"Dynamic"** Strategy in **HBC**.
  <br>HBC will follow the **Dynamic Strategy**, dynamic price info is refreshed and the Helios Optimizer produces an **Energy Plan**.
- For an **Update Run:** Select the **"Helios"** Strategy in **HBC** and HBC will follow the **Helios Strategy** according to the **Energy Plan**.
- Check the **Output** of the Helios Optimizer on the **Helios Dashboard** ('Controls' Tab and 'Detailed Results' Tab).
- For **advanced** configuration use the **'Helios Insights Mode'** button to make additional input parameters and output results visible (or to hide).
- Check your **Prices** in the Optimal Energy Plan Table.
If the price are not as expected then you may need to adapt price type, data provider and/or energy provider in the advanced parameters.
This is especially applicable when you are using a generic data provider with market prices.

For a **detailed** installation procedure see [Helios Optimizer Installation](INSTALL.md).

## Features 
- **LP/MILP Optimization:** Uses SciPy **Linear Programming** to **maximize** profit and **minimize** energy costs.
- **HBC Output Integration:** Helios Strategy as a **native HBC strategy** using the Helios Optimizer Output (Sub Strategy and Power).
- **HBC Input Integration:** Retrieves Parameters and Prices from **HBC** 
- **HA PyScript/Python Application:** Runs within **PyScript** and native **Python** and does not require an external engine.
- **Fast:** Lightweight execution that optimizes 192 steps of 15 minutes (for 2 days) within 500ms per Optimization Run.
- **Asynchronous:** Actual calculation is executed directly into the HA core **asynchronous** loop.
- **Zero-Config Setup:** Out-of-the-box **defaults** let you run a test optimization immediately without configuration.
- **Independent:** Open design compatible with any dynamic pricing, solar forecast and house usage forecast.
- **Flexible Horizon & Intervals:** Calculates the Optimal Energy Plan for one or two day(s) with 15-minute or 60-minute intervals (step sizes).
- **Dynamic Recalculation:** Runs automatically from the current timestamp (based on current state) or from a user-defined step (for testing).
- **Clean Data Structure:** Simple full-day input and output arrays (00:00-24:00/48:00).

## Roadmap (2026-2027)
- **Solar Forecast:** Support for **Solcast** as an additional Solar Production prediction.
- **Additional Models:** **Profit Optimization** is implemented, Additional models are **Cost Optimization** and **Self Consumption**.
- **Energy Providers:** Add additional **Energy Providers** with their related Provider Markups (Opslag) - ongoing.
- **House Usage History:"** Determine House Usage **Forecast** from House Usage **History**.
- **Limit Power in HBC:** Currently HBC will start charging/discharging at full power (independent of the Helios advice)
- **Device Support:** **EV** (highest priority), **Heat Pump**, and **Boiler** support (as **Deferrable** Devices).
- **Modular Connectors:** Dedicated modules for **Energy Providers**, **Solar Forecasts**, Battery and Solar Inverter **Integrations**.
- **Native HA Integration:** Pure Python Home Assistant **Custom Component** (HACS-ready), run without PyScript or external engines.

## Important Remark
Helios can derive Export Prices using Source Price Data (e.g. from HBC Price Data with Import Prices). 
The Import Price is based upon the Market and includes Energy Tax (Energiebelasting).
The Export Price is also based upon the Market Price and does not included Energy Tax.
Since the Net Metering (Nederlandse Salderingsregeling) is no longer applicable in 2027 this a future proof approach.
<b>However in 2026</b> the value of the export of energy can be <b>higher</b> than the export price.
As long as the total of exported energy is less than the total of imported energy the Energy Tax is compensated while exporting energy!
The Optimizer Model does not take this extra value into account.

## Inputs
- **Optimization Parameters** (Steps, Step size, Start Step, Grid Limits)
- **House Daily Energy Usage** (Forecast array or average House Daily Usage and Distribution)
- **Solar Parameters**  (Forecast array and Solar Mode)
- **Current Battery State** (Battery Capacity and Battery State of Charge) (From HBC)
- **Battery Parameters** (SOC Target, Min, Max, Charge/Discharge Limit, Charge/Discharge Efficiency)
- Grid **Import Prices** array (import price per step) or Source Price Data (From HBC)
- Grid **Export Prices** array (export price per step) or Source Price Data (Derived from HBC)
- Grid **Market Prices** array (market price per step) or Source Price Data (Derived from HBC)

## Optional deferrable loads (Future):
- **Electric Vehicle** (EV) charging profile
- **Heat Pump** (HP) operation parameters
- **Boiler** operation parameters

## What's New and Updating instructions:
See [Helios Optimizer Release Notes](RELEASE_NOTES.md)

## Documentation and Help
For a detailed **Documentation** of the application and for specification of the **Input Parameters** and the **Output Results** (Optimized Energy Plan)
see the [Helios Optimizer Documentation](DOC.md).

# Help and FAQ
For **help** on **specific** input **parameters** or output **results** use the links provided above **each section** of the dashboard 
to link directly to the applicable information in the documentation.

For configuration problems and other **frequently asked questions** see [Helios Optimizer FAQ](docs/FAQ.md).
For installation problems see the **detailed** [Helios Installation Instructions](INSTALL.md)

## Advanced
Some input parameters and output results are hidden to improve the usability of the Helios dashboard.
A button is available on the top of the dashboard tabs 'Helios Inside Mode'. 
Click this button to enable or disable the 'Helios Inside Mode'.
Additional input and output sections will become available in 'Helios Inside Mode'.

## Credits
I would like to thank all the testers that have been providing very useful feedback
for improving the application and the documentation.

## Contributing
At the moment it is not advised to develop additional features based on the current version.
The current code is not yet stable so your changes may not work on the next release.
Only small bug fixes will be accepted.
Please raise an issue to report a bug or to request for new functionality.

# FAQ and Help
**[Helios Optimizer Frequently Asked Questions](docs/FAQ.md)**
and **[Helios Optimizer Documentation](DOC.md)**

# Interest Poll (Dutch)
**[Helios Optimizer Interest Poll Results in Dutch](docs/PEILING_HELIOS.md)**

## License & Disclaimer
This project is licensed under the GNU General Public License v3.0 (GPLv3). 
As stated in the license, this software is provided "as is" without any warranty, 
and installation or use is entirely at your own risk.

A full description of the applicable license is available via this link:
**[Helios Optimizer License](https://github.com/Jos1958/ha-helios-optimizer/blob/main/LICENSE)**

The author(s) accept no responsibility or liability for any damage, financial loss, 
battery degradation, or system disruption resulting from the use or misuse of this application. 
Always verify system behavior and safety limits for your specific hardware setup.

**Keywords:** Battery Management System, Energy Management System, Optimize your Energy Plan, Solar Panels, Home and House Automation, Home Assistant, HBC, Linear Programming, Python, PyScript
