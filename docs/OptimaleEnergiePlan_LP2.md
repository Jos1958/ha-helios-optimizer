# Het Optimale Energieplan met Lineair Programmeren (LP)

In de energiesector staat dit probleem bekend als **Energy Asset Optimization** of **Economic Dispatch**. 
Het doel is om een slim energiesysteem (met bijvoorbeeld zonnepanelen en een thuisbatterij) zo aan te sturen dat de totale operationele kosten over een volledige dag (24 uur) worden geminimaliseerd, rekening houdend met dynamische stroomprijzen en fysieke beperkingen.

* $P_{net,inkoop}(t)$ 

# Het Optimale Energieplan met Lineair Programmeren (LP)

In de energiesector staat dit probleem bekend als **Energy Asset Optimization** of **Economic Dispatch**. 
Het doel is om een slim energiesysteem (met bijvoorbeeld zonnepanelen en een thuisbatterij) zo aan te sturen dat de totale operationele kosten over een volledige dag (24 uur) worden geminimaliseerd, rekening houdend met dynamische stroomprijzen en fysieke beperkingen.

Lineair programmeren lost dit op door het energiesysteem op te knippen in drie vaste wiskundige bouwstenen: 
**Beslissingsvariabelen**, een **Doelfunctie** en **Beperkingen (Constraints)**.

Voor de Helios Optimizer is gekozen voor een 48 uur horizon omdat daar dan altijd een volledige dag in valt (ook als we pas om 23:00 starten).

---
### Bouwsteen 1: De Beslissingsvariabelen
* $P_{net,inkoop}(t)$ 
