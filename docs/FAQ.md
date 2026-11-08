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

## Strange Behaviour of the Helios Strategy (Flow) in HBC 
- **HBC stops** the charging or discharging despite the strategy in Helios
<br>HBC always follows the limitations you have set in HBC despite what the Helios Optimizer has decided.
Make sure that your State of Charge (SoC) Minimum and Maximum for your Batteries and the 'Charge until SoC' and 'Sell until SoC'.
Be aware that Helios calculates with one big battery when you have multiple batteries.
Use the sum of the Capacity of all batteries and the sum of the SoC Minimum and SoC Maximum values to calculate an overall SoC Minimum and Maximum.
See the Derived Parameters section (Helios Insight Mode) for the (overall) Maximum Capacity, Remaining Energy and current SoC as calculated by Helios.
HBC uses a 'Available Energy' field but this value has already been compensated for the minimum and maximum SoC and is not used in Helios.

- **HBC Full stop** for the Helios Strategy:
<br>HBC goes to sub-strategy **Full stop**. 
This means that the Node-Red Helios Flow received no value from the Helios Optimizer (value: "unknown" or "undefined").
<br>This can have several reasons but the main reason is that the Helios Optimizer failed to run. 
This can be due to input errors or due to installation errors.
Check the Helios Dashboard to find out if any errors are given in the "Results Summary" - "Solver Status" area and try to fix to cause of the error.

