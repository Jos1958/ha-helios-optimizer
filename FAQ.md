- **Unexpected Selling/Discharging** of Energy from the Battery to the Grid
<br>The Model follows the rules you have set for the Maximum State of Charge of the Battery very strict.
If the Battery SoC is above the SoC-Max then it will start selling at any price.
Adapt the Helios input parameter for the SoC-Max or adapted the maximum SoC in HBC to be inline then this situation will no longer occur.

- **Unexpected Buying/Charging** of Energy from the Grid to the Battery
<br>The Model follows the rules you have set for the Minimum State of Charge of the Battery very strict.
If the Battery SoC is below the Soc-Min then it will start buying at any price.
Adapt the Helios input parameter for the SoC-Min or adapted the mininum SoC in HBC to be inline then this situation will no longer occur.

- **HBC stops** the charging or discharging despite the strategy in Helios

- **HBC Full stop** for the Helios Strategy:
<br>HBC goes to sub-strategy **Full stop**. 
This means that the Node-Red Helios Flow received no value from the Helios Optimizer (value: "unknown" or "undefined").
<br>This can have several reasons but the most main reason is that the Helios Optimizer failed to run. 
This can be due to input errors or due to installation errors.
Check the Helios Dashboard to find out if any errors are given in the "Results Summary" - "Solver Status" area and try to fix to cause of the error.

- Battery is enabled for the Battery Parameters but in the Output the Battery is not enabled
  - For a Battery Capacity of 0 the Battery will be disabled.
<br>You can verify using Insight Mode in the Derived Parameters section (field: Maximum Energy (All Batteries)) the value of Battery Capacity.