# Why use LP (EN)?

## Explanation of Linear Programming (LP) 
Finding the cheapest way to control a battery might seem simple, but with 24 to 48 hours of fluctuating electricity prices, unpredictable solar production, battery loss, and changing household demand, the number of possible decisions is massive.
Trying to figure this out with basic "if/then" rules or by testing every possible scenario takes a lot of computing power and often misses the best setup.
Linear Programming (LP) solves this instantly by using smart mathematics:
 * Guaranteed **Best Result** (Global Optimum): LP doesn't guess or use trial-and-error. Mathematically, it guarantees the absolute cheapest plan for your complete 48-hour timeline based on your limits and prices.
 * **Lightning Fast**: Instead of taking minutes or hours to test all combinations, LP solves the entire 48-hour plan in less than 1 second on lightweight hardware (like a Raspberry Pi or NUC).
 * Handles **Multi-Variable Rules** Effortlessly: LP easily balances multiple rules at the same time — such as "never discharge below 10%", "minimize export to the grid during negative prices", and "charge the battery before peak prices hit" — without getting confused.
In short: LP turns a complex puzzle with thousands of choices into a split-second math calculation, ensuring you always save or earn the maximum amount of money possible.

## LP vs. Traditional Rule-Based Automation
Most home battery systems rely on rule-based planners. They use simple "If/Then" logic (like "If price < €0.10, charge battery") or 
look ahead at today's prices to pick a fixed number of the cheapest hours to charge and the most expensive hours to discharge.
While this works fine for basic situations, it requires constant tweaking of fixed rules and hours. 
Because these systems only look at one rule at a time, they struggle to find the absolute lowest energy bill over a full day.
Helios Optimizer uses Linear Programming (LP) to replace rigid rules with smart, mathematical planning. 
Instead of guessing fixed hours, it continuously calculates the exact charging, discharging, and solar production values
needed to achieve the lowest possible costs for the entire day.

## Compare

| Feature | Traditional If/Then Rules | Helios LP Optimization |
|---|---|---|
| Price Selection | Fixed Hours/Thresholds: Selects a predetermined number of cheapest/most expensive hours. | Dynamic & Variable: Calculates exact charge/discharge durations and power levels down to the minute. |
| Solar & Load Awareness | Hard to combine solar forecasts, house load, and dynamic rates without creating dozens of complex rules. | Balances all solar, load, price, and efficiency variables simultaneously in one mathematical equation. |
| Partial Charging / Efficiency | Treats hours binary (100% charge or 0%). | Proportional Control: Can partially charge (e.g., 40% power) if full charging exceeds capacity or causes losses. |
| Negative Price & Curtailment | Relies on hard cut-offs or manual overrides to stop export/charging. | Built-in Economics: Automatically determines exact solar curtailment and zero-export limits based on net cost. |
| Financial Outcome | Sub-optimal savings due to missed opportunities and rigid thresholds. | Guaranteed global optimum—mathematically the cheapest possible execution plan. |
| Mathematical Goal | Executes a pre-configured heuristic schedule. | Guaranteed Global Optimum: Solves the entire 48-hour timeline to guarantee the lowest absolute energy bill. |

## Key Takeaway
A dynamic rule planner asks: "Which are the 3 cheapest hours to charge today?"
Helios LP asks: "Given the next 48 hours of prices, solar yield, house load, and battery efficiency, what exact power schedule results in the lowest total cost?

# Waarom LP gebruiken (NL)?

## Uitleg Lineair Programmeren (LP) 
Het vinden van de goedkoopste manier om een batterij aan te sturen lijkt op het eerste gezicht eenvoudig. Maar met 24 tot 48 uur aan schommelende elektriciteitsprijzen, onvoorspelbare zonne-energie, batterijverliezen en een wisselend huisverbruik is het aantal mogelijke beslissingen reusachtig.
Dit proberen op te lossen met simpele "als/dan"-regels of door elke mogelijke situatie uit te proberen kost enorm veel rekenkracht en mist vaak de meest optimale instelling.
Lineair Programmeren (LP) lost dit direct op met slimme wiskunde:
1. Gegarandeerd het beste resultaat (Globaal Optimum): LP gokt niet en werkt niet via 'trial-and-error'. Wiskundig gezien garandeert het het allergoedkoopste plan voor je volledige 48-uurs planning, rekening houdend met al jouw limieten en prijzen.
2. Zeer snel: In plaats van minuten of uren nodig te hebben om alle combinaties door te rekenen, lost LP het complete 48-uurs plan op in minder dan 1 seconde op lichte hardware (zoals een Raspberry Pi of Mini-PC).
3. Verwerkt moeiteloos meerdere regels tegelijk: LP balanceert eenvoudig diverse randvoorwaarden tegelijkertijd—zoals "ontlaad nooit onder de 10%", "minimaliseer teruglevering aan het net bij negatieve prijzen" en "laad de batterij op vóór de avondpiek"—zonder ooit vast te lopen.
Kortom: LP verandert een ingewikkelde puzzel met duizenden keuzes in een bliksemsnelle wiskundige berekening, zodat je altijd het maximale bedrag bespaart of verdient.

## LP vs. Traditionele Regelgebaseerde Automatisering
De meeste thuisbatterij-systemen vertrouwen op regelgebaseerde planners. 
Ze gebruiken eenvoudige "Als/Dan"-logica (zoals "Als prijs < € 0,10, laad batterij") of kijken vooruit naar de dagprijzen 
om een vast aantal goedkoopste uren te kiezen om te laden en de duurste uren om te ontladen.
Hoewel dit prima werkt voor basissituaties, vraagt het om het continu aanpassen van vaste regels en uren. 
Omdat deze systemen slechts naar één regel tegelijk kijken, hebben ze moeite om over een hele dag de absoluut laagste energierekening te vinden.
Helios Optimizer gebruikt Lineair Programmeren (LP) om vaste regels te vervangen door slimme, wiskundige planning. 
In plaats van te gokken op vaste uren, berekent het continu de exacte waarden voor laden, 
ontladen en zonne-energie die nodig zijn om de laagst mogelijke kosten voor de hele dag te bereiken.

## Vergelijking

| Functie | Traditionele Als/Dan-regels | Helios LP-Optimalisatie |
|---|---|---|
| Prijsselectie | Vaste Uren/Drempels: Kiest een vooraf ingesteld aantal goedkoopste/duurste uren. | Dynamisch & Variabel: Berekent exact hoe lang en met welk vermogen er geladen/ontladen moet worden. |
| Zon & Gebruik Bewust | Zonnevoorspellingen, huisgebruik en dynamische tarieven vereisen tientallen ingewikkelde regels. | Balanceert alle variabelen (zon, verbruik, prijs en verliezen) gelijktijdig in één wiskundige formule. |
| Partieel Laden & Efficiëntie | Werkt vaak binair (100% vermogen laden of 0%). | Proportionele Sturing: Kan ook gedeeltelijk laden (bijv. op 40% vermogen) als vol laden tot verliezen leidt. |
| Negatieve Prijzen & Curtailment | Vertrouwt op harde limieten of handmatige regels om teruglevering/laden te stoppen. | Ingebouwde Economie: Berekent automatisch de exacte zonne-curtailment en 'no-export' limieten op basis van netto kosten. |
| Financieel Resultaat | Suboptimale besparingen door gemiste kansen en vaste drempelwaardes. | Gegarandeerd globaal optimum—wiskundig gezien het allergoedkoopste uitvoeringsplan. |
| Wiskundig Doel | Voert een vooraf geconfigureerd logisch schema uit. | Gegarandeerd Globaal Optimum: Lost de complete 48-uurs horizon op om de allerlaagste energierekening te garanderen. |

## Belangrijkste Inzicht
Een dynamische regel-planner vraagt: "Wat zijn vandaag de 3 goedkoopste uren om te laden?"
Helios LP vraagt: "Gegeven de komende 48 uur aan prijzen, zonopbrengst, huisverbruik en batterij-efficiëntie: welk exacte vermogensprofiel leidt tot de laagste totale energiekosten?"

[Readme](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - [Install](INSTALL.md) - [Release Notes](RELEASE_NOTES.md) - [License](LICENSE "GitHub Docs")