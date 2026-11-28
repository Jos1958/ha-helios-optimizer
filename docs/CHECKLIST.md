## Release Activities (Checklist)
- _ **Git Folder** c:\$code\GitHeliosOptimizer

- _ Run the **Single** and **Multiple** **Regression** Test Cases with Visual Studio (helios_main)
  - _ Single Run with Run Types (1..7) - Check Expected Costs and Energy Plans (differences?)
  - _ Multiple Run (92x) with Run Types (1..4) - Check Expected Costs 

- _ Home **Testing** on **Home Assistant**
    - _ Make sure that Home Assistant is the latest release level (Core: 2026.11.3 OS 18.4)
    - _ Install the latest helios version on Home Assistant
    - _ Restart Home Assistant
    - _ Verify that within 10s the Optimizer runs successful
    - _ Try different options on the Helios Dashboard (steps, days, target provider, ..)
    - _ Check that HBC receives and activates the correct sub-strategy (now on the Helios Dashboard)
    - _ Check a Price Example (e.g. Frank Energie Import and Market Price)
    - _ Check the Node-Red flows for errors 
    - _ Check that new parameters got the correct initial value
    - _ Check the HA System Log for Helios Optimizer Errors (Warnings: resample, extend, startup)
    - _ Select an invalid start step (> steps with step size is 60min) and check the error message
    - _ Check that the configuration file is loaded and applied (e.g. with target provider: Custom)
    - _ Disable the "Allow All Import" and check that the correct error message is displayed
    - _ Disable the "Access hass as a global variable" and check that the correct error message is displayed

- _ **Testing with earlier adapters**

- _ Adapt the **RELEASE_NODES.md** 
  - _ Add thenew Release as a release version at the top
  - _ Add the New Functions
  - _ Add the Important Fixes (add references/help/support)
  - _ List the **Changed** Files
  - _ Remainder Files in the **Not changed** Files 

- _ Adapt the **other** documentation 
  - _ README.md - new/adapted features, simple installation, roadmap
  - _ INSTALL.md - changes in the installation procedure
  - _ DOC.md - new/adapted functionality
  - _ FAQ - new findings/repoorts
  
- _ **Dashboard**
  - _ Adapt the **Release#** on both Tabs
  - _ **Copy** the **latest yaml** from the helios dashboard 
  - _ **Open** the \dashboard\helios_dashboard.yaml file and **past** the yaml
  - _ Make sure to include the **first** dashboard line: **views:**
  
- _ **PyScript** from c:\$code\VisualStudio2026\HeliosOptimizer\
  - _ Adapt the **Release#** of Helios Optimizer  (helios_optimizer.py)
  - _ Add new UI fields to the **initialisation** (helios_service.py  )
  - _ Copy 2 py files to the **\pyscript** git folder
      - helios_services.py
      - helios_forecast.py       
  - _ Copy 1 py files to the **\pyscript\modules** git folder
      - helios_hass.py       
  - _ Copy 3 py files to the **\pyscript\helios_python** git folder
      - helios_common.py
      - helios_optimizer.py
      - helios_prices.py
  
- _ **Packages** from x:\packages\
  - _ Copy the helios_optimizer.yaml file          to the \packages git folder
  - _ Copy the helios_optimizer_forecast.yaml file to the \packages git folder as **(optional)**

- _ **Node Red Strategy Flow**
  - _ Adapt the HBC version in the Helios flow name (e.g. Strategy Helios v4.15.1)
  - _ Export the flow 'Strategy Helios v4.xx.x) to \node-red\ git folder
  - _ Save as NR Flow file name: 02 strategy-helios-v4.xx.x vy.y.y.json (v4.15.1 v0.9.6) 

- _ **Banner** (seldom, only when changed)
  - _ Copy the HeliosOptimizerBanner.jpeg   to the \www git folder
  - _ Copy the HeliosOptimizerBanner70.jpeg to the \www git folder

- _ **Push** the new/changed/delete files to **GitHub **
  - _ c:\> cd \$code\GitHeliosOptimizer
  - _ git add .     
  - _ git commit -m "vy.y.y Helios Optimizer Release (First Public Release, Solcast, ...)"
  - _ git push 

- _ **GitHub Release** (https://github.com/Jos1958/ha-helios-optimizer)
  - _ [Releases] - [Draft a new release]
  - _ [Select tag] - [Create new tag] - y.y.y (without the version v)
  - _ Specify Release Title: Helios Optimizer Release vy.y.y (First Public Release)
  - _ Release Notes: Copy/Paste the (simplified) release description from RELEASE_NOTES.md
  - _ Release label: * Latest
  - _ [Publish release]
  
- _ **Announce** the new Release
  - _ HBC Discord (strategies)