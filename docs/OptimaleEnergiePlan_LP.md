# Het Optimale Energieplan met Lineair Programmeren (LP)

In de energiesector staat dit probleem bekend als **Energy Asset Optimization** of **Economic Dispatch**. Het doel is om een slim energiesysteem (met bijvoorbeeld zonnepanelen en een thuisbatterij) zo aan te sturen dat de totale operationele kosten over een volledige dag (24 uur) worden geminimaliseerd, rekening houdend met dynamische stroomprijzen en fysieke beperkingen.

Lineair programmeren lost dit op door het energiesysteem op te knippen in drie vaste wiskundige bouwstenen: **Beslissingsvariabelen**, een **Doelfunctie** en **Beperkingen (Constraints)**.

---

### Bouwsteen 1: De Beslissingsvariabelen
Dit zijn de 'knoppen' waar de computer (de LP-solver) elk uur ($t$) aan kan draaien om tot het meest optimale plan te komen. We definiëren deze variabelen voor elk uur van de dag ($t = 1, 2, \dots, 24$):

* $P_{net\_inkoop}(t)$: Het vermogen dat je inkoopt van het elektriciteitsnet ($\ge 0$).
* $P_{net\_export}(t)$: Het vermogen dat je teruglevert (exporteert) aan het net ($\ge 0$).
* $P_{batterij\_laad}(t)$: Het vermogen dat vanaf het interne net naar de batterij wordt gestuurd ($\ge 0$).
* $P_{batterij\_ontlaad}(t)$: Het vermogen dat intern uit de batterij wordt getrokken ($\ge 0$).

---

### Bouwsteen 2: De Doelfunctie (Kosten Minimaliseren)
Het hoofddoel is om de netto energiekosten over de gehele dag zo laag mogelijk te houden. Dit berekenen we door de kosten van inkoop te verminderen met de opbrengsten van export. 

Als $C_{inkoop}(t)$ de actuele inkoopprijs per uur is en $C_{export}(t)$ de terugleververgoeding, dan ziet de formule er als volgt uit:

$$ \text{Minimaliseer } \sum_{t=1}^{24} \left( P_{net\_inkoop}(t) \times C_{inkoop}(t) - P_{net\_export}(t) \times C_{export}(t) \right) $$

---

### Bouwsteen 3: De Beperkingen (Constraints)
De solver mag de knoppen niet zomaar oneindig opendraaien; hij moet zich houden aan de wetten van de fysica en de limieten van de hardware.

#### A. De Energiebalans (Vraag = Aanbod op het net)
Elk afzonderlijk uur moet er een perfecte balans zijn op jouw interne elektriciteitsnet. Alles wat er binnenkomt (zon, inkoop, batterij-ontlading) moet exact gelijk zijn aan wat er verbruikt of weggestuurd wordt (vraag, batterij-lading, export). 

Omdat de batterij bij ontladen te maken heeft met een ontlaadefficiëntie ($\eta_{ontlaad}$), komt er aan de aanbodzijde net iets minder bruikbare stroom uit de batterij dan er intern wordt onttrokken:

$$ P_{zon}(t) + P_{net\_inkoop}(t) + \left( P_{batterij\_ontlaad}(t) \times \eta_{ontlaad} \right) = Vraag(t) + P_{batterij\_laad}(t) + P_{net\_export}(t) $$

#### B. De Batterijstatus (State of Charge - SoC)
De hoeveelheid energie die daadwerkelijk *in* de batterij zit (uitgedrukt in kWh), verandert elk uur op basis van het laad- en ontlaadgedrag. Hier passen we de laadefficiëntie ($\eta_{laad}$) toe:

$$ SoC(t) = SoC(t-1) + \left( P_{batterij\_laad}(t) \times \eta_{laad} \right) - P_{batterij\_ontlaad}(t) $$

De batterij is daarnaast gebonden aan fysieke grenzen:
* **Capaciteitsgrens:** De batterij kan nooit leger dan nul en nooit voller dan zijn maximale capaciteit: $0 \le SoC(t) \le SoC_{max}$
* **Snelheidsgrens:** De omvormer bepaalt hoe snel de batterij maximaal kan laden of ontladen: $0 \le P_{batterij\_laad}(t) \le P_{laad\_max}$ en $0 \le P_{batterij\_ontlaad}(t) \le P_{ontlaad\_max}$

#### C. Hardware- en Netaansluitingslimieten
Je fysieke hoofdzekering begrenst hoeveel stroom je maximaal gelijktijdig kunt importeren of exporteren:
$$0 \le P_{net,inkoop}(t) \le P_{net,max}$$

$$0 \le P_{net,export}(t) \le P_{net,max}$$

---

### Praktische Nuance: Voorkomen van Loze Arbitrage 
Dankzij de toegeegde **efficiëntiefactoren** voorkomt het model 'loze arbitrage' (stroom kopen en direct weer verkopen zonder echte winst). Als een batterij een totale *round-trip efficiency* heeft van bijvoorbeeld 81% ($\eta_{laad} = 0.90$ en $\eta_{ontlaad} = 0.90$), weet de solver dat handelen met de batterij pas zin heeft als het prijsverschil tussen de uren groter is dan het energieverlies van 19%.
