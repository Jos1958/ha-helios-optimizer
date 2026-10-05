English Version

# Why Linear Programming (LP)?
## Explanation
Finding the cheapest way to control a battery might seem simple, but with 24 to 48 hours of fluctuating electricity prices, unpredictable solar production, battery loss, and changing household demand, the number of possible decisions is massive.
Trying to figure this out with basic "if/then" rules or by testing every possible scenario takes a lot of computing power and often misses the best setup.
Linear Programming (LP) solves this instantly by using smart mathematics:
 * Guaranteed **Best Result** (Global Optimum): LP doesn't guess or use trial-and-error. Mathematically, it guarantees the absolute cheapest plan for your complete 48-hour timeline based on your limits and prices.
 * **Lightning Fast**: Instead of taking minutes or hours to test all combinations, LP solves the entire 48-hour plan in less than 1 second on lightweight hardware (like a Raspberry Pi or NUC).
 * Handles **Multi-Variable Rules** Effortlessly: LP easily balances multiple rules at the same time — such as "never discharge below 10%", "minimize export to the grid during negative prices", and "charge the battery before peak prices hit" — without getting confused.
In short: LP turns a complex puzzle with thousands of choices into a split-second math calculation, ensuring you always save or earn the maximum amount of money possible.

## LP vs. Traditional Rule-Based Automation
Most home battery automations rely on static "If/Then" rules (e.g., "If dynamic price < €0.10, then charge battery"). While simple, rule-based systems struggle to make truly cost-optimal decisions over a full day.
Helios Optimizer uses Linear Programming (LP) to replace rigid logic with holistic, mathematical forecasting.

## Compare
| Feature | Traditional If/Then Rules | Helios LP Optimization |
|---|---|---|
| Decision Horizon | Reactive: Responds only to the current price or battery status right now. | Proactive: Evaluates the full 24–48 hour horizon at once to plan ahead. |
| Peak Price Strategy | May fully discharge early during a medium-price hour, leaving nothing for the actual highest peak later. | Reserves battery capacity specifically for the most expensive hours of the day. |
| Solar & Usage Integration | Hard to combine solar forecasts, house load, and dynamic rates without creating dozens of complex rules. | Balances all solar, load, price, and efficiency variables simultaneously in one mathematical equation. |
| Negative Price Handling | Requires manual overrides to prevent charging from grid or exporting solar at a loss. | Automatically calculates solar curtailment and optimal grid charging down to the cent. |
| Financial Outcome | Sub-optimal savings due to missed opportunities and rigid thresholds. | Guaranteed global optimum—mathematically the cheapest possible execution plan. |

## Key Takeaway
Rule-based automations ask: "Is power cheap right now?"
Helios LP asks: "Given the next 48 hours of prices, solar, and household demand, what is the single most profitable schedule for every 15-minute block?"

Nederlandse Versie

# Waarom Lineair Programmeren (LP)?
## Uitleg
Het vinden van de goedkoopste manier om een batterij aan te sturen lijkt op het eerste gezicht eenvoudig. Maar met 24 tot 48 uur aan schommelende elektriciteitsprijzen, onvoorspelbare zonne-energie, batterijverliezen en een wisselend huisverbruik is het aantal mogelijke beslissingen reusachtig.
Dit proberen op te lossen met simpele "als/dan"-regels of door elke mogelijke situatie uit te proberen kost enorm veel rekenkracht en mist vaak de meest optimale instelling.
Lineair Programmeren (LP) lost dit direct op met slimme wiskunde:
1. Gegarandeerd het beste resultaat (Globaal Optimum): LP gokt niet en werkt niet via 'trial-and-error'. Wiskundig gezien garandeert het het allergoedkoopste plan voor je volledige 48-uurs planning, rekening houdend met al jouw limieten en prijzen.
2. Redsnel: In plaats van minuten of uren nodig te hebben om alle combinaties door te rekenen, lost LP het complete 48-uurs plan op in minder dan 1 seconde op lichte hardware (zoals een Raspberry Pi of Mini-PC).
3. Verwerkt moeiteloos meerdere regels tegelijk: LP balanceert eenvoudig diverse randvoorwaarden tegelijkertijd—zoals "ontlaad nooit onder de 10%", "minimaliseer teruglevering aan het net bij negatieve prijzen" en "laad de batterij op vóór de avondpiek"—zonder ooit vast te lopen.
Kortom: LP verandert een ingewikkelde puzzel met duizenden keuzes in een bliksemsnelle wiskundige berekening, zodat je altijd het maximale bedrag bespaart of verdient.

## LP vs. Traditionele Regelgebaseerde Automatisering
De meeste thuisbatterij-automatiseringen vertrouwen op statische "Als/Dan"-regels (bijv. "Als de dynamische prijs < € 0,10 is, laad dan de batterij op"). Hoewel dit eenvoudig is, schieten regelgebaseerde systemen tekort als het gaat om echt kostenefficiënte beslissingen over een hele dag.
Helios Optimizer gebruikt Lineair Programmeren (LP) om starre logica te vervangen door een holistische, wiskundige voorspelling.

## Vergelijking
| Functie | Traditionele Als/Dan-regels | Helios LP-Optimalisatie |
|---|---|---|
| Beslissingshorizon | Reactief: Reageert alleen op de actuele prijs of batterijstatus van dit moment. | Proactief: Evalueert de volledige 24–48 uurs horizon in één keer om vooruit te plannen. |
| Piekprijsstrategie | Ontlaadt vaak te vroeg tijdens een matig dure periode, waardoor er niks overblijft voor de echte avondpiek. | Reserveert batterijcapaciteit specifiek voor de allerduurste uren van de dag. |
| Zon- & Verbruiksintegratie | Zonnevoorspellingen, huisverbruik en dynamische tarieven vereisen tientallen ingewikkelde regels. | Balanceert alle variabelen (zon, verbruik, prijs en verliezen) gelijktijdig in één wiskundige formule. |
| Omgaan met Negatieve Prijzen | Vereist handmatige correcties om laden van het net of terugleveren met verlies te voorkomen. | Berekent automatisch zonne-curtailment en de optimale laadmomenten tot op de cent nauwkeurig. |
| Financieel Resultaat | Suboptimale besparingen door gemiste kansen en vaste drempelwaardes. | Gegarandeerd globaal optimum—wiskundig gezien het allergoedkoopste uitvoeringsplan. |

## Belangrijkste Inzicht
Regelgebaseerde automatiseringen vragen: "Is stroom NU goedkoop?"
Helios LP vraagt: "Gegeven de komende 48 uur aan prijzen, zonne-energie en huisverbruik: wat is het meest winstgevende schema voor elk individueel kwartier?"
