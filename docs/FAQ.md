# HA Helios Optimizer - Frequently Asked Questions

## Strange Behaviour of the Strategy in Helios Optimizer
- **Unexpected Selling/Discharging** of Energy from the Battery to the Grid
<br>The Model follows the rules you have set for the Maximum State of Charge of the Battery very strict.
If the Battery SoC is above the SoC-Max then it will start selling at any price.
<br>Adapt the Helios input parameter for the SoC-Max or adapted the maximum SoC in HBC to be inline then this situation will no longer occur.

- **Unexpected Buying/Charging** of Energy from the Grid to the Battery
<br>The Model follows the rules you have set for the Minimum State of Charge of the Battery very strict.
If the Battery SoC is below the Soc-Min then it will start buying at any price.
<br>Adapt the Helios input parameter for the SoC-Min or adapted the mininum SoC in HBC to be inline then this situation will no longer occur.

- Battery is **enabled** for in the Input Parameters for the Battery but in the Output the Battery is **disabled**.
<br>For a Battery Capacity of 0 the Battery will be disabled.
<br>You can verify using Insight Mode in the Derived Parameters section (field: Maximum Energy (All Batteries)) the value of Battery Capacity.

- **Not Selling at the Highest Price**
<br>When using the HBC dynamic strategy you may be used to selling at the highest price. 
However when calculated over a two day period it may be cheaper to keep the energy in the battery for a later moment.
Especially when the Energy Tax is no longer compensated in the Netherlands in 2027.
For 2026 you can enable 'Net Metering' in the advanced parameters (Helios Insight Mode).
As a result the difference between import and export price will be much smaller and the Optimizer will buy and sell more often.
When disabled you will notice that 'Self consumption' becomes a more preferred strategy.

- **Unexpected Strategy selected by Helios**
<br>Helios uses a different approach for determining the best strategy for the optimization period than you may be used to.
There are no rules in the model that define which strategy must be selected (no if-then-else logic based on lowest or highest prices). Instead, the model only contains the physical limits (max grid import/export, max battery charge/discharge, battery capacity, min/max SoC%) and the current system state (battery SoC%).
It calculates a solution for the variables (grid power and battery power) that yields the lowest total cost for the entire 24–48 hour horizon. Its inputs are the solar production forecast, the house demand forecast, and the dynamic price data.
Rather than guessing, it uses an open-source Linear Programming module specifically designed to solve these complex mathematical problems globally.
While you might sometimes question why a specific strategy is chosen for a single hour, you should always look at the bigger picture—what is cheapest over the full 24–48 hour period. The best way to verify if the model is making the right choice is to construct an alternative strategy and calculate the total grid cost for it under the exact same circumstances (same forecasts and prices). If your alternative results in a lower total cost, your approach is better; otherwise, the model has found the true mathematical optimum.

## Strange Behaviour of the Helios Strategy (Flow) in HBC 
- **HBC Sub-strategy 'Charge PV' is** is selected during the night (no solar).
<br>'Zero export' would be a better name for this strategy but this is how it is called in HBC.
The 'Charge PV' strategy has been selected by the Helios Optimizer since it prefers to use Grid Power instead of Battery Power.
The Battery will not discharge to compensate a demand of energy in the house but it
will charge when there is surplus energy available.
Of course this will not happen during the night but as soon as the sun start shining it may become applicable.
Effectively during the night (without solar power) it will be the same as 'Standby'. 
 
- **HBC stops Charging or Discharging** despite the strategy in Helios
<br>HBC always follows the limitations you have set in HBC despite what the Helios Optimizer has decided.
Make sure that your State of Charge (SoC) Minimum and Maximum for your Batteries and the 'Charge until SoC' and 'Sell until SoC'.
Be aware that Helios calculates with one big battery when you have multiple batteries.
Use the sum of the Capacity of all batteries and the sum of the SoC Minimum and SoC Maximum values to calculate an overall SoC Minimum and Maximum.
See the Derived Parameters section (Helios Insight Mode) for the (overall) Maximum Capacity, Remaining Energy and current SoC as calculated by Helios.
HBC uses a 'Available Energy' field but this value has already been compensated for the minimum and maximum SoC and is not used in Helios.

- **HBC Sub-strategy 'Full stop'** for the Helios Strategy:
<br>HBC goes to Sub-strategy **Full stop**. 
This means that the Node-Red Helios Flow received no value from the Helios Optimizer (value: "unknown" or "undefined").
<br>This can have several reasons but the main reason is that the Helios Optimizer failed to run. 
This can be due to input errors or due to installation errors.
Check the Helios Dashboard to find out if any errors are given in the "Results Summary" - "Solver Status" area and try to fix to cause of the error.
<br><br>If on the Helios Dashboard the Solver Status is "Optimization terminated successfully" then the error is not in the Helios Optimizer:
However the Helios Strategy flow could not retrieve the HBC sub-strategy from the Helios Optimizer HBC Sub Strategy
(input_select.helios_optimizer_hbc_sub_strategy). Check that this entity has the expected sub strategy value.
If the Sub Strategy value is correct then the Node-Red Flow (Strategy Helios) failed to retrieve the value.
Make sure the Helios Flow is deployed and check the status and timestamps below the individual nodes of the flow.  
Are there any errors? Which Node has the error in which section has the error?

