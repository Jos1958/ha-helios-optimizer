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

# Key Takeaway
Rule-based automations ask: "Is power cheap right now?"
Helios LP asks: "Given the next 48 hours of prices, solar, and household demand, what is the single most profitable schedule for every 15-minute block?"

## LP vs. Rule-Based Dynamic Planners 2
Smart control strategies—like HBC's Dynamic Charge—look ahead at daily prices to select a fixed number of the cheapest hours to charge and the most expensive hours to discharge.
While this works well for simple price-arbitrage, rule-based planners rely on fixed parameters (e.g., "always charge for 3 hours"). Helios LP Optimization replaces fixed thresholds with mathematical, multi-variable balancing.

## Compare 2
| Feature | Dynamic Rule-Based Planning (e.g., HBC) | Helios LP Optimization |
|---|---|---|
| Price Selection | Fixed Hours/Thresholds: Selects a predetermined number of cheapest/most expensive hours. | Dynamic & Variable: Calculates exact charge/discharge durations and power levels down to the minute. |
| Solar & Load Awareness | Usually plans charging based only on electricity prices, independent of expected solar or house load. | Integrated Model: Balances dynamic prices, solar forecasts, house demand, and battery losses simultaneously. |
| Partial Charging / Efficiency | Treats hours binary (100% charge or 0%). | Proportional Control: Can partially charge (e.g., 40% power) if full charging exceeds capacity or causes losses. |
| Negative Price & Curtailment | Relies on hard cut-offs or manual overrides to stop export/charging. | Built-in Economics: Automatically determines exact solar curtailment and zero-export limits based on net cost. |
| Mathematical Goal | Executes a pre-configured heuristic schedule. | Guaranteed Global Optimum: Solves the entire 48-hour timeline to guarantee the lowest absolute energy bill. |

## Key Takeaway 2
A dynamic rule planner asks: "Which are the 3 cheapest hours to charge today?"
Helios LP asks: "Given the next 48 hours of prices, solar yield, house load, and battery efficiency, what exact power schedule results in the lowest total cost?

Nederlandse Versie

# Waarom LP gebruiken (NL)?

## Uitleg Lineair Programmeren (LP) 
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

## LP vs. Regelgebaseerde Dynamische Planners 2
Slimme stuurstrategieën—zoals HBC's Dynamic Charge—kijken vooruit naar de dagprijzen om een vast aantal van de goedkoopste uren te kiezen om te laden en de duurste uren om te ontladen.
Hoewel dit prima werkt voor eenvoudige prijsarbitrage, vertrouwen regelgebaseerde planners op vaste parameters (bijv. "laad altijd gedurende 3 uur"). Helios LP-Optimalisatie vervangt deze vaste drempels door een wiskundige afweging tussen alle variabelen tegelijk.

## Vergelijking 2
| Functie | Dynamische Regel-Planner (bijv. HBC) | Helios LP-Optimalisatie |
|---|---|---|
| Prijsselectie | Vaste Uren/Drempels: Kiest een vooraf ingesteld aantal goedkoopste/duurste uren. | Dynamisch & Variabel: Berekent exact hoe lang en met welk vermogen er geladen/ontladen moet worden. |
| Zon & Verbruik | Plant het laden meestal alleen op basis van stroomprijzen, los van verwachte zonopbrengst of huisverbruik. | Geïntegreerd Model: Balanceert dynamische prijzen, zonvoorspellingen, huisverbruik én batterijverliezen gelijktijdig. |
| Partieel Laden & Efficiëntie | Werkt vaak binair (100% vermogen laden of 0%). | Proportionele Sturing: Kan ook gedeeltelijk laden (bijv. op 40% vermogen) als vol laden tot verliezen leidt. |
| Negatieve Prijzen & Curtailment | Vertrouwt op harde limieten of handmatige regels om teruglevering/laden te stoppen. | Ingebouwde Economie: Berekent automatisch de exacte zonne-curtailment en 'no-export' limieten op basis van netto kosten. |
| Wiskundig Doel | Voert een vooraf geconfigureerd logisch schema uit. | Gegarandeerd Globaal Optimum: Lost de complete 48-uurs horizon op om de allerlaagste energierekening te garanderen. |

## Belangrijkste Inzicht 2
Een dynamische regel-planner vraagt: "Wat zijn vandaag de 3 goedkoopste uren om te laden?"
Helios LP vraagt: "Gegeven de komende 48 uur aan prijzen, zonopbrengst, huisverbruik en batterij-efficiëntie: welk exacte vermogensprofiel leidt tot de laagste totale energiekosten?"
