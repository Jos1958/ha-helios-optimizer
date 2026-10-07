# HA Helios Optimizer - Release Notes
![Helios Calculator](images/HeliosOptimizerBanner.jpeg)

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
  - Created a release in github (v0.8.0) with the same number as used in the manifest.json
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

[README](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - [Install](INSTALL.md) - **Release Notes** - [License](LICENSE "GitHub Docs")
