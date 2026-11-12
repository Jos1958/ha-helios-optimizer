# HA Helios Optimizer - Release Notes
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)
[README](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - [Install](INSTALL.md) - **Release Notes** - [License](LICENSE "GitHub Docs")

## 0.9.5 (2026-11-12) Installation Improvements and Net Metering Mode (Salderingsregeling)
- Graphs did not always use full width (especially in Windows), added update_interval: 5s to the apexcharts-card (Thanks to Gerrit_18808).
- Improved Installation (Thanks Martijn), Handling PyScript Imports and Hass configuration errors.
- Added a Net Metering Option in the advanced parameters (only for dutch Salderingregeling in 2026).
- Disabled the resolution="hourly" option of the get_forecast service of Forecast.solar since it is giving some weird results in the last hour of sun (combining two hours).
- Support for 15-min and 60-min forecasts in Forecast.Solar, so disabling the "hourly" option should not be a problem.
- Improved error handling for Forecast.Solar (helios_forecast.py).
- Simplified the Node-Red Helios Strategy Flow, Disabled Dynamic Price Sections, Relies now fully on the Dynamic Strategy Flow for dynamic price retrieval (Thanks Rubbere).
- Alternative Banner with a height of 70% (now used on the Detailed Results Tab, Let me know which one you prefer).
- Extra fields on the Dashboard for Helios Battery Strategy, HBC Sub Strategy, Price Profiles (3x) and Keys (3x).
- Improved Documentation (Thanks Mike Da Spike), Readme, Installation Guide and a new Frequently Asked Questions (FAQ).
- **Updated files (ALL Files are Updated!):** 
  - Package (yaml), 
  - All PyScript (*.py), 
  - Alternative Banner 70% (jpeg),
  - Dashboard (yaml), 
  - Node-Red Helios Strategy Flow (json), 
  - Documentation (available online).
- **Not updated since 0.9.4:** Banner File (jpeg), Automation is Obsolete!
- See For **upgrade instructions** see [Helios Optimizer Installation - Upgrade](INSTALL.md#upgrade).

## 0.9.4 (2026-11-03) Improved Data and Energy Provider Handling 
- Energy Provider split into a target and source provider which can be both different from the main provider (which determines the Source Price Data format)
- Improved handling of price conversions to support Belgium Tax, Markup and Loss Factors
- Temporary solution for handling "Grid Clock" and Engie Providers for Belgium
- Introduced a Horizon (in Days) parameter (replacing the Steps parameter on the Dashboard), Model will calculated with Steps value derived from Horizon and Step Size
- Steps is 0 (specify via Horizon is 0) disables the Optimization Model, No Calculation will be done
- Introduced an Advanced Parameters section (only in insight mode) with Horizon, House Daily Usage Distribution and Price parameters 
- **Updated files:** All PyScript (*.py), Dashboard (yaml), Package (yaml), Documentation
- **Not updated since 0.9.3:** Node-Red Helios Strategy Flow (json), Banner File (jpeg), Automation is Obsolete!

## 0.9.3b (2026-10-29) Minor Fixes
- Initialized the step size for the House Daily Usage Distribution array (house_size), prevent an exception when distribution is empty, flat usage will be used, improved the error message for invalid sizes
- Check Solar Energy Forecast is available before converting to floats
- For Solar Enabled a Solar Energy Forecast must be available, raise an error when not available (optimizer will NOT continue)
- Check HBC Price Data is available and return an error when no price data found (optimizer will NOT continue)
- Check that All Imports are allowed for PyScript and give an error message when the PyScript Configuration needs to be adapted
- Check that Hass is accessable by PyScript as a global variable and give an error message when the PyScript Configuration needs to be adapted
- Fixed issue with initial empty helios version number entity, is now handled as 0.0.0, all applicable entities will be initialized
- **Updated files:** Only the PyScript files are updated (*.py)

## 0.9.3 (2026-10-28) HBC Output and Prices and Strategy Graph
- Added Helios Forecast PyScript which calls the forecast_solar.get_forecast service to retrieve the forecast solar hours, the required config entry is retrieved from hass
<br>Hours info is not available via an entity of the forecast.solar integration (only via the service)
- Added the Prices and Strategy Graph with Prices (Import, Export and Market) and the HBC Sub Strategy per step
- Timestamp in a Graph is now in the middle of the step (iso at the start of a step) 
- Added the Strategy as a Serie to the Prices Graph (now in the tooltip as a number, added the numbers in the legenda)
- Split the Helios Dashboard into two tabs and introduced optional sections using the (HBC) "insight" button (this simplifies the default dashboard tabs)
- Improved the Helios Optimizer documentation and added more direct links to the sections on the Helios dashboard
- Added a Helios Strategy Flow to HBC that handles the Output (Sub-Strategy and Power) from the Helios Optimizer for the current step
- Included error handling in the HBC interface (if Helios fails the sub-strategy will be set to HA "unknown")
- For errors the Helios Strategy will apply in HBC the "Full stop" strategy
- Replaced the Helios Automation Task by a PyScript Service that runs every 15-min and retrieves Helios and HBC parameters from HA entities
- Allow only a single running instance of the Helios Automation Task and the Helios Automation Service 

## 0.9.2 (2026-10-12) Fixed special characters on dashboard
- Invalid codepage for helios_dashboard.yaml, changed from ANSI to UTF-8

## 0.9.1 (2026-10-12) Initialize Input Entities
- Initializes Helios Optimizer Input Entities depending on the previous helios release version
- For some initial values of Input Entities HBC values are used (sell/charge target, max discharge/charge power)
- Update Files: 
  - All pyscript files    (initialize input entities, state functions added)
  - helios_dashboard.yaml (updates on graph and table, shorter text since info now available in the documentation, fixed problem with battery disabled)
  - helios_optimizer.yaml (small typos and descriptions)
  - Several documentation files (*.md), Use the links on the dashboard to access the DOC.md !
- Reboot after installation of the pyscript files since pure python files are not refreshed automatically

## 0.9.0 (2026-10-07) First Public Version (PyScript and Python)
- First public version 
- Support for reading input parameters from HBC
- Uses a PyScript Service and a calculation in Pure Python (with SciPy Linear Programming)
- This Calculation is started from the Home Assistant Loop as an asychronous (Pure Python) function
- See v 0.7.8 and lower for details
- **WARNING:** 0.8.x Custom Component functions are not included! 

## 0.8.x (2026-08-15) Custom Component and HACS support (Proof of Concept) - 
- Proof of concept for a version that runs as a Home Assistant Custom Component (simple model but using LP) (__init__.py)
- Brand files in sub folder of the custom component (with icon.png and logo.png)
- Call the SciPy Linear Programming function with the HiGHS solver
- Update Home Assistant Entity in the custom component
- Import several libraries including linprog (scipy.optimize)
- Home Assistant Manifest file (manifest.json) for custom component with version number and scipy dependency 
- Home Assistant Setup file (config_flow.py) to allow installation/configuration of the integration (otherwise component needs to be added to configuration.yaml)
- Home Assistant Service file (service.yaml), required for the interface of the service helios_calculator.optimize_schedule) 
- Home Assistant strings.json (with additional text for the config flow) and translations/nl.json with dutch translations)
- Created a README.md (directly linked by HACS) and a RELEASE_NOTES.md (v0.1.0-v0.8.0), created an empty DOC.md file
- Created the GitHub GNUv3 License file (automatically filled when type of license selected)
- Simple Installation flow for the integration (config_flow.py)
- Investigated and Implemented the HACS requirements for a custom component that is available in the HACS repository: 
  - Note: The custom component could already be added to my HA installation via the custom repository option in HACS
  - Created the hacs.json with the custom component, render_readme: true, home assistant min release version 
  - Added the document link and the github issue link to the manifest.json
  - Added two workflows: .github/workflow/hacs.yaml & hassfest.yaml, checked results under actions (corrected errors)
  - Created a release in github (v0.8.0 with tag 0.8.0) with the same number as used in the manifest.json
  - Forked from hacs/default (hacs repository), created a separate branch, updated the file integration. with "Jos1958/ha-helios-calculator" (alphabetic order)
  - Commit the change (in integration.) to a new branch
  - Create Pull Request and Fill the related checklist (links to release, hacs and hassfest workflow results) for the pull request (Do not the: Merge Pull Request)
    Make sure the Pull Request is done to the hacs/default (and not to my own master)! Resubmitted the request on 2026-08-17

## 0.7.8 (2026-09-30) Hardening of the Optimization Model
- Included Support for Conversion from Source Price to Target Price, Group Steps and Average Price, Expand Steps (Repeat), Fill Gaps in Day(s), Fallback Days, 
- Added Source Price Data and improved Helios Energy Price Parser with HBC support (and original Provider)
- Added house_daily_usage and house_daily_distr arguments as an alternative for house_energy_forecast (since no house energy usage history available yet)
- Corrected errors in the optimization model related to the difference in power and energy rules for steps smaller than 1 hour (e.g. 15 min), 
- The Helios Optimizer Calculate Plan now runs asynchronous using pure python, dramatic performance improvement
- Added input and output files (in the helios service) for validation and regression test purposes
- Create asynchronouos versions of file handling functions for use in Home Assistant
- Added Sum (Totals) of Input Arrays and Output Arrays for validation purposes (only at maximum insight level), error in validation when overall_sum above the threshold
- Allow arrays that are too long (e.g. 48 steps for 2 days while the optimization period is only 24 steps for 1 day), the extra steps will be ignored
- Separate input step sizes for import/export prices, house forecast and solar forecast arrays instead of a single input step size to allow for different resampling conversions
- Handing invalid arguments in the service call, this allows the HA Automation to report the error, return invalid argument in payload
- Added input parameters to the dashboard, improved output markdown cards, adapted the payload  
- Split off the common functies into a helios_common.py separate from the helios_optimizer.py
- Improved (PyScript) Performance for the Index in the Variable Array, Vectorized Assignments
- Included performance measurements (from 12.5s to <800ms for 192 steps (15min) and to 150-250ms for 48 steps (60min)
- Interpolate (explode or implode) the input arrays to adapt the data to the required step size
- Extend input arrays when one or more days can be added to the array by reusing the last day
- Investigated Price Sources and conversion options (see EnergyPriceConversion)
- Introduce Try/Except to handle errors (with traceback) and return message in the payload
- Created a Visual Code Version that is compatible with the Home Assistant Pyscript version (for debugging and testing), multiple run option for testing

## 0.7.0 (2026-09-xx) Hardening of the Optimization Model
- Improved Home Assistant Mockup that allows the code to be developed and tested in Visual Studio
- Added additional comment in the code and replaced all dutch comments by english
- Protect agains infeasible solution with invalid SoC Start (outside SoC Min and Max)
- Protect against infeasible solution with unreachable SoC Min End for remaining steps and max charge power
- Extended validation of input parameters and extra output arrays and parameters
- Extended error handling for exceptions (Try/Except, Traceback, Initialize all payload variables)
- Validate Costs (total cost = sum of step costs) and return as calc_result 
- Generate 92 Test Scenarios with an expected result for regression testing
- Write the run results to an (csv) export file in Visual Studio with a summary of the input and outputs 

## 0.6.0 (2026-08-01) Solar Production Optimization
- Added Solar Mode, solar production optimization (Solar modes: enabled, modulating/dimming, binary, disabled)
- Split the code into a Helios Calculator (HA Service) and Helios Module (Actual Solver) for testing in Visual Studio
- Note: Helios Module contains most of the earlier history and Helios Calculator now contains new code
- Warning: pyscript runs the Helios Calculator and includes the Helios Module from the modules folder (in VS: both are in the same folder)

## 0.5.0 (2026-06-28) Home Assistant Dashboard for Helios
- Extended the payload and the related output entity for presentation on a Home Assistant Dashboard
- Created HBC lab page with plan results (status, graph, table) using apexchart and markdown cards
- Helios Calculator Banner

## 0.4.0 (2026-06-24) Battery Strategy and Payload 
- Input parameters now include a dictionary for the Battery Configuration
- Return payload to the Home Assistant automation
- Use current time as starting step when start_step is 0 (e.g. at 15:23 start at 15:00 with step 16)
- Calculate a battery strategy from the optimization results (concept version)

## 0.3.0 (2026-06-23) Optimization of the Energy Plan
- Added Input arrays (prices, house and solar forecast) as parameters to the calculation/optimization service
- Home Assistant Automation calls the service with these parameters

## 0.2.0 (2026-05-20) Prototype of an LP solver
- Introduced the Energy Balance Rule 

## 0.1.1 (2026-05-19)
- **Features:** 
  * No changes

- **Fixes:**
  * Renamed the py file to lower case with underscore

- **Documentation:**
  * Added a RELEASE_NOTES_md

- **Files Changed:**
  - `pyscript/helios_calculator.py` (was HeliosCalculator.py)

## 0.1.0 (2026-05-19) 
- Initial commit with the first implementation of a LP call in pyscript
- The functionality is started from an HA automation
- Errors in the compilation or runtime can be found in the Home Assistant System Log

[Readme](README.md) - [Doc](DOC.md) - **Why LP (EN)** - [Why LP (NL)](WHY.md#waarom-lp-gebruiken-nl) - [Install](INSTALL.md) - [Release Notes](RELEASE_NOTES.md) - [License]
