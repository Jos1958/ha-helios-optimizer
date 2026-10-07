# Uitkomsten interessepeiling voor Helios
Bedankt voor alle reacties op de peiling! De inzichten geven een goed beeld van de configuraties, wensen en verwachtingen binnen de community.

## De belangrijkste resultaten op een rij:
 * Interesse & Testbereidheid: Het overgrote deel ziet de LP-optimizer als een waardevolle uitbreiding op de huidige HBC-strategieën. Meer dan de helft meldt zich aan voor de eerste testgroep!
 * Ecosystemen & Hardware: Niet onverwacht maar 100% van de respondenten gebruikt HBC, waarbij de Marstek Venus (v1/v2/v3) uiteraard veruit de populairste batterij is. Slechts een derde heeft één batterij en maar liefst twee derde beschikt al over 2 of meer batterijen.
 * Prijs-integraties: De dynamische prijs-integraties lopen sterk uiteen. Zonneplan, Frank Energie, Nordpool en Tibber komen het meest voor.
 * Zonne-energie: Meer dan de helft kan de zonne-omvormer(s) dimmen of uitschakelen, via zeer diverse omvormer-integraties. 
 * P1-meters: Hier valt op dat HomeWizard de absolute koploper is.
 * EV's & Laadpalen: Maar liefst 75% beschikt over een elektrische auto en 60% kan deze ook aansturen vanuit Home Assistant.
 * Huisgebruik & Voorspelling: Het inzicht in het eigen historisch huisgebruik is nog niet overal goed beschikbaar, 
 * Zon Voorspelling: Er wordt nog weinig gebruik gemaakt van een uur- of kwartier voorspelling (alleen een dagvoorspelling met Forecast.solar) van de zon-opbrengst. Solcast wordt hiervoor het meest gebruikt.
 * PyScript: Bij 30% is PyScript al geinstalleerd en de rest is bereid om PyScript te installeren om Helios te kunnen gebruiken.

## Belangrijke wensen & inzichten voor de roadmap:
 * Meerdere systemen aansturen: Er is een duidelijke wens om meerdere batterijen en zelfs meerdere zonne-omvormers tegelijk te kunnen beheren.
 * Nul op de meter / Zonder teruglevering: Niet iedereen wil puur winst maken op teruglevering. Er is vraag naar het optimaliseren van de eigen kosten zonder stroom te verkopen aan het net. Het aankomende vervallen van de salderingsregeling maakt een goede strategie extra urgent.
 * Uitleg & Transparantie: Het voordeel van een wiskundige LP-optimizer is nog niet voor iedereen meteen helder. Transparante uitleg over de exacte werking en de financiële voordelen is dus een belangrijk.
 Zie hiervoor [Waarom LP gebruiken?](WHY.md#waarom-lp-gebruiken-nl).

## Vervolgstappen:
Met deze data kan ik gerichter aan de slag met de juiste koppelingen (zoals de Marstek/HBC-integraties en ondersteuning van apparatuur). De eerste kandidaten voor de testgroep ontvangen binnenkort bericht!

Gebaseerd op deze uitkomsten heb ik een aantal concrete conclusies en vervolgstappen:
 * Architectuur & Aansturing: Helios wordt gekoppeld als een extra strategie binnen HBC. Hierdoor maakt de optimizer direct gebruik van de al aanwezige batterij-aansturing van HBC.
 * Energieprijzen: Voor de dynamische prijzen sluit de optimizer aan op de importprijzen van HBC. Omdat exportprijzen daarin nog niet direct beschikbaar zijn, wordt hiervoor een conversie ingezet.
 * Zonvoorspelling: Aangezien HBC nog geen uurbasis-voorspelling voor zonne-energie bevat, wordt er een koppeling gemaakt met de Forecast.Solar REST API.
 * Huisverbruik: Een dynamische voorspelling van het verbruik vergt nog extra ontwikkeltijd. Dit wordt in eerste instantie opgelost met een handmatig aanpasbare vaste voorspelling met verdeling over de uren van de dag.
 * Implementatie (PyScript vs Custom Component): Gezien de grote bereidheid om PyScript te installeren, wordt de ontwikkeling van een eigen Custom Component uitgesteld. De eerste versie draait volledig via PyScript.
 * Zonne-energie & Omvormers: Uit het rekenmodel rolt een specifieke zonne-energiestrategie. Hiermee kan de omvormer via een eigen automatisering worden aangestuurd of gedimd.
 * Toekomstige prioriteiten: Kost-optimalisatie (zoals nul op de meter zonder teruglevering), Solcast (meest gebruikt) en de integratie van EV's/laadpalen staan bovenaan de verlanglijst voor opvolgende updates.
