# Helios Optimizer - Battery Strategy Selection
[Readme](../README.md) - [Documentation](../DOC.md) - [Why LP](WHY.md) - **STRATEGY** - [Install](../INSTALL.md) - [Release Notes](../RELEASE_NOTES.md) - [License](../LICENSE "GitHub Docs")
<br>![Helios Optimizer](../images/HeliosOptimizerBanner.jpeg)

This document describes how the **Helios Optimizer** determines the active Helios Battery Strategy and the corresponding Home Battery Control Sub-strategy  for each time step (`t`) based on calculated power flows and battery State of Charge (SoC).

## Strategy Determination Overview

| Main Category / Condition | Specific Condition | Helios Battery Strategy | HBC Sub-strategy | Purpose / Explanation | 
| ----- | ----- | ----- | ----- | ----- | 
| **Past (before Now)** | `t < start_index` | `Skipped` | *N/A* | Steps in the past are skipped. | 
| **Discharging**  | `disch > house demand + 100W` **and** battery **not** too full | `Sell` | `Sell` | Feeding power into the grid for profit/market value. | 
| (`bat_disch_kw ≥ 100W`) | `disch > house demand + 100W` **and** battery **is** too full | `Discharge` | `Sell` | Forced discharging to get below the maximum SoC limit. | 
|  | `disch ≤ house demand + 100W` | `NOM` | `Self-consumption` | Discharging purely for household consumption (no grid export). | 
| **Charging**  | `charge > solar surplus + 100W` **and** battery **not** empty | `Buy` | `Charge` | Buying power from the grid (for later sale or favorable rates). | 
| (`bat_charge_kw ≥ 100W`) | `charge > solar surplus + 100W` **and** battery **is** empty | `Charge` | `Charge` | Forced charging to get above the minimum SoC limit. | 
|  | `charge < solar surplus - 100W` | `Charge Solar` | `Charge PV` | Charging partially or exclusively with excess solar energy. | 
|  | `charge ≈ solar surplus` (within 100W) | `NOM` | `Self-consumption` | Charging to prevent unwanted grid export. | 
| **Battery not active ,  grid active**  | Battery is empty (`battery_low`) + grid import | `NOM-C` | `Charge PV` | Only charge (discharging is not allowed due to low battery) | 
| (\`net_grid_kw≥ 100W\`) | Battery is full (`battery_high`) + grid export | `NOM-D` | `Zero import` | Only discharge (charging is now allowed due to high battery). | 
|  | Otherwise (disabled by optimizer) | `Standby` | `Standby / peak shave` | Battery intentionally in standby; grid power is cheaper or more efficient. | 
| **No activity** (Idle state) | Battery is empty (`battery_low`) | `NOM-C` | `Charge PV` | Keep in standby focusing on zero-export when battery is empty. | 
|  | Battery is full (`battery_high`) | `NOM-D` | `Zero import` | Keep in standby focusing on zero-import when battery is full. | 
|  | Battery is normal (not empty/full) | `NOM` | `Self-consumption` | Neutral status; battery steps in as soon as the power balance changes. | 

## Detailed Explanation per Branch

Each bullet starts with the **Helios Battery Strategy (HBC Sub Strategy)** and is followed by an **explanation** of the situation in which these strategies are selected.\
The HBC Sub strategy is directly mapped from the Helios Battery Strategy and in some cases multiple Helios Strategies are mapped to the same HBC strategy.

### 1. Historical Steps (`t < start_index`)

* **Skipped (n/a):** The time step lies in the past (). \
  **Details:** For intervals that have already occurred, no active optimization strategy needs to be calculated. These steps are assigned `Skipped` by default. An HBC sub-strategy is not applicable in this case since it will never be assigned.

### 2. Battery Discharging (`bat_disch_kw ≥ 100W`)

* **Sell (Sell):** The battery delivers significant power and discharges more than the house directly demands, meaning power is exported to the grid. \
  **Details:** As long as the battery is not exceeding its upper limit, this behavior is driven purely by favorable market prices (`Sell`).

* **Discharge (Sell):** If the battery threatens to exceed its upper SoC bound (`battery_too_high`), the optimizer forces a discharge to bring the battery back below the maximum SoC limit, regardless of immediate market conditions.

* **NOM (Self-consumption):** The discharge is minor or matches the household demand precisely. \
  **Details:** No power is exported to the grid; the battery solely supports the local household load.

### 3. Battery Charging (`bat_charge_kw ≥ 100W`)

* **Buy (Charge):** More power is charged than the current solar surplus provides, meaning power is drawn from the grid to fill the battery (e.g., in anticipation of price spikes later in the day).

* **Charge (Charge):** The battery is below its minimum limit (`battery_too_low`). \
  **Details:** Charging is required to protect battery health or maintain the minimum operational reserve.

* **Charge Sol (Charge PV):** The charging power is lower than the available solar surplus. \
  **Details:** The battery is fed exclusively with excess solar energy.

* **NOM (Self-consumption):** The charging power matches the solar surplus within a `100W` margin to prevent power from exporting to the grid unnecessarily.

### 4. No Significant Battery Activity, Active Grid (`net_grid_kw ≥ 100W`)

* **NOM-C (Charge PV):** When the battery itself is barely charging or discharging, yet there is net grid import because the battery is low or empty (`battery_low`), the mode is restricted to charging only. \
  **Details:** Further discharging is not allowed, so the system focuses solely on preventing export (zero-export) as soon as (solar) power becomes available.

* **NOM-D (Zero import):** When there is net grid export because the battery is high or full (`battery_high`), the mode is restricted to discharging only. \
  **Details:** Further charging is not allowed, so the system focuses solely on preventing grid import (zero-import) when household demand rises.

* **Standby (Standby / peak shave):** The optimizer deliberately chooses to disable the battery (putting it in standby) and use the grid instead. \
  **Details:** The decision to use the grid is is based on cost optimization: drawing directly from the grid is cheaper or more efficient than cycling the battery. HBC also will be in Standby mode but may activate the battery when peak shaving is required and enabled.

### 5. Complete Idle State (No Battery or Grid Activity)

When no notable power flows are occurring, the system evaluates the battery's current State of Charge:

* **NOM-C (Charge PV):** If the battery is low or empty (`battery_low`), `NOM-C` is selected to be ready for solar intake without exporting.

* **NOM-D (Zero import):** If the battery is high or full (`battery_high`), `NOM-D` is selected to be ready for household demand without importing.

* **NOM (Self-consumption):** If the battery status is normal, the system defaults to `NOM` (`Self Consumption`), remaining passive until the power balance in the house or on the grid shifts.