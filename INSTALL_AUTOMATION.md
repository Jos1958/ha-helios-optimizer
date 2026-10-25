- **Helios Optimizer Automation:** Create a new Automation that runs the Helios Optimizer
  - Home Assistant - Settings (Instellingen) - Automations - [Add Automation] from scratch
  - Edit the automation in YAML mode
  - Open automation/helios_automation.yaml in your local Editor 
  - Select all content of the helios_automation.yaml file
  - Copy/Paste all of the content to the Yaml editor (replace all existing lines of the automation)
  - [Save] the Automation yaml
  - Check in the settings of the new Automation the Entity-ID of the automation:
    automation.helios_optimizer_automation_task
  - Make sure your entity id is exactly the same and if not rename the entity id and press <Update>
    Warning: The Start Button on the Helios Dashboard will NOT work when the entity id is not correct!
  - This automation will now run every 15 minutes and we notify you when an error occurs (see Notificaton menu item)

  -   [automation]                     - this is NOT a Home Assistant Folder (see below what to do with it)
  -    helios_automation.yaml        - contains the automation.helios_optimizer_task 
