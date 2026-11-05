# Het Optimale Energieplan met Lineair Programmeren (LP)

In de energiesector staat dit probleem bekend als **Energy Asset Optimization** of **Economic Dispatch**. 
Het doel is om een slim energiesysteem (met bijvoorbeeld zonnepanelen en een thuisbatterij) zo aan te sturen dat de totale operationele kosten over een volledige dag (24 uur) worden geminimaliseerd, rekening houdend met dynamische stroomprijzen en fysieke beperkingen.

Lineair programmeren lost dit op door het energiesysteem op te knippen in drie vaste wiskundige bouwstenen: 
**Beslissingsvariabelen**, een **Doelfunctie** en **Beperkingen (Constraints)**.

Dit zijn de 'knoppen' waar de computer (de LP-solver) elk uur ($t$) aan kan draaien om tot het meest optimale plan te komen. We definiëren deze variabelen voor elk uur van de dag ($t = 1, 2, \dots, 24$):
* $P_{net,inkoop}(t)$: Het vermogen dat je inkoopt (afneemt/importeert) van het elektriciteitsnet ($\ge 0, \le P_{net,{max_{inkoop}}}$).

