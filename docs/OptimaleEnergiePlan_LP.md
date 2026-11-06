---
layout: default
title: Het Optimale Energieplan met Lineair Programmeren
---

# Het Optimale Energieplan met Lineair Programmeren (LP) - v0.9.4

In de energiesector staat dit probleem bekend als **Energy Asset Optimization** of **Economic Dispatch**. 
Het doel is om een slim energiesysteem (met bijvoorbeeld zonnepanelen en een thuisbatterij) zo aan te sturen dat de totale operationele kosten over een volledige dag (24 uur) worden geminimaliseerd, rekening houdend met dynamische stroomprijzen en fysieke beperkingen.

Lineair programmeren lost dit op door het energiesysteem op te knippen in drie vaste wiskundige bouwstenen: 
**Beslissingsvariabelen**, een **Doelfunctie** en **Beperkingen (Constraints)**.

Voor de Helios Optimizer is gekozen voor een 48 uur horizon omdat daar dan altijd een volledige dag in valt (ook als we pas om 23:00 starten).

---
### Bouwsteen 1: De Beslissingsvariabelen
Dit zijn de 'knoppen' waar de Helios Optimizer (met de LP-solver) elk uur ($t$) aan kan draaien om tot het meest optimale energie plan te komen. 
*Opmerking:* De Optimizer kan ook met stappen van 15 minuten rekenen maar dat laten de rest van dit verhaal even buiten beschouwing.
Ook zal de Optimizer bij voorkeur rekenen vanaf nu tot eind volgende dag rekenen (een periode van 24 tot 48 uur) maar ook dat laten we hier buiten beschouwing.
We definiëren deze variabelen als het gemiddelde vermogen in kW voor elke stap (van 1 uur) van de dag ($t = 1, 2, \dots, 24$):

* $P_{net,inkoop}(t)$: Het vermogen dat je inkoopt (afneemt/importeert) van het elektriciteitsnet ($\ge 0, \le P_{net,{max_{inkoop}}}$).
* $P_{net,verkoop}(t)$: Het vermogen dat je verkoopt (teruglevert/exporteert) aan het net ($\ge 0, \le P_{net,{max_{verkoop}}}$).
* $P_{batterij,laad}(t)$: Het vermogen dat vanaf het interne net naar de batterij wordt gestuurd ($\ge 0, \le P_{batterij,{max_{laad}}}$).
* $P_{batterij,ontlaad}(t)$: Het vermogen dat intern uit de batterij wordt getrokken ($\ge 0, \le P_{batterij,{max_{ontlaad}}}$).

Uit deze power variabelen volgen de gebruikte energie variabelen per stap:
* $$E(t) = P(t) \times \Delta t$$ : Het vermogen in kWh 

Waarbij: 
* $P(t)$: Het gemiddelde vermogen tijdens die stap (uitgedruk in Kilo Watt ($\text{kW}$)).
* $\Delta t$: De lengte of duur van de stap (uitgedrukt in uren, bijvoorbeeld $1$ uur voor 60 minuten of $0,25$ uur voor 15 minuten).
* $E(t)$: De hoeveelheid energie in een tijdstap $t$ (uitgedrukt in Kilo Watt Uur ($\text{kWh}$)).

---
### Bouwsteen 2: De Doelfunctie (Kosten Minimaliseren)
Het hoofddoel is om de netto energiekosten over de gehele dag zo laag mogelijk te houden. 
Dit berekenen we door de kosten van inkoop te verminderen met de opbrengsten van verkoop. 

Als $C_{inkoop}(t)$ de actuele inkoopprijs voor een kWh is en $C_{verkoop}(t)$ de verkoopprijs (terugleververgoeding), dan ziet de formule er als volgt uit:

$$ \text{Minimaliseer } \sum_{t=1}^{24} \left( E_{net,inkoop}(t) \times C_{inkoop}(t) - E_{net,verkoop}(t) \times C_{verkoop}(t) \right) $$

---
### Bouwsteen 3: De Beperkingen (Constraints)
De solver mag de knoppen niet zomaar oneindig opendraaien; hij moet zich houden aan de wetten van de fysica en de limieten van de hardware.

#### A. De Energiebalans (Vraag = Aanbod op het net)
Elk afzonderlijk uur moet er een perfecte balans zijn op jouw interne elektriciteitsnet. Alles wat er binnenkomt (zon, inkoop, batterij-ontlading) moet exact gelijk zijn aan wat er verbruikt of weggestuurd wordt (vraag, batterij-lading, verkoop). 

Omdat de batterij bij ontladen te maken heeft met een ontlaadefficiëntie ($\eta_{ontlaad}$), komt er aan de aanbodzijde net iets minder bruikbare stroom uit de batterij dan er intern wordt onttrokken:

$$ P_{zon}(t) + P_{net,inkoop}(t) + \left( P_{batterij,ontlaad}(t) \times \eta_{ontlaad} \right) = Vraag(t) + P_{batterij,laad}(t) + P_{net,verkoop}(t) $$

#### B. De Batterijstatus (State of Charge - SoC)
De hoeveelheid energie die daadwerkelijk *in* de batterij zit (uitgedrukt in kWh), verandert elk uur op basis van het laad- en ontlaadgedrag. Hier passen we de laadefficiëntie ($\eta_{laad}$) toe:

$$ SoC(t) = SoC(t-1) + \left( E_{batterij,laad}(t) \times \eta_{laad} \right) - E_{batterij,ontlaad}(t) $$

De batterij is daarnaast gebonden aan (fysieke) grenzen:
* **Capaciteitsgrens:** De batterij kan nooit leger dan de minimum capaciteit en nooit voller dan de maximale capaciteit: 
  <br>$SoC_{min} \le SoC(t) \le SoC_{max}$
  <br>Hierbij is gelden de fysieke grenzen dat $SoC_{min} \ge 0$ en $SoC_{max} \le SoC_{capaciteit}$:
* **Snelheidsgrens:** De omvormer bepaalt hoe snel de batterij maximaal kan laden of ontladen: 
  <br>$0 \le P_{batterij,laad}(t) \le P_{batterij,{max_{laad}}}$ en $0 \le P_{batterij,ontlaad}(t) \le P_{batterij,{max_{ontlaad}}}$

#### C. Hardware- en Netaansluitingslimieten
Je fysieke hoofdzekering begrenst hoeveel stroom je maximaal gelijktijdig kunt inkopen (importeren) of verkopen (exporteren):
* $$0 \le P_{net,inkoop}(t) \le P_{net,{max_{inkoop}}}$$
* $$0 \le P_{net,export}(t) \le P_{net,{max_{export}}}$$

---
### Praktische Nuance: Voorkomen van Loze Arbitrage 
Dankzij de batterij **efficiëntiefactoren** voorkomt het model 'loze arbitrage' (stroom kopen en direct weer verkopen zonder echte winst). 
Als een batterij een totale *round-trip efficiency* heeft van bijvoorbeeld 81% ($\eta_{laad} = 0.90$ en $\eta_{ontlaad} = 0.90$), 
weet de solver dat handelen met de batterij pas zin heeft als het prijsverschil tussen de uren groter is dan het energieverlies van 19%.

