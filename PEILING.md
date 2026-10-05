# Uitkomsten interessepeiling voor Helios Optimizer
Bedankt voor alle reacties op de peiling! De inzichten geven een heel helder beeld van de hardware-opstellingen, wensen en verwachtingen binnen de community.

## De belangrijkste resultaten op een rij:
 * Interesse & Testbereidheid: Het overgrote deel ziet de LP-optimizer als een waardevolle uitbreiding op de huidige HBC-strategieën. Meer dan de helft meldt zich aan voor de eerste testgroep!
 * Ecosystemen & Hardware: 100% van de respondenten gebruikt HBC, waarbij de Marstek Venus (v1/v2/v3) veruit de populairste batterij is. Slechts een derde heeft één batterij; maar liefst twee derde beschikt al over 2 of meer batterijen.
 * Prijs-integraties: De dynamische prijs-integraties lopen sterk uiteen. Zonneplan, Nordpool en Tibber vormen samen de top 3.
 * Zonne-energie & P1: Meer dan de helft kan de zonne-omvormer(s) dimmen of uitschakelen, via zeer diverse omvormer-integraties. Bij de P1-meters valt op dat HomeWizard de absolute koploper is.
 * EV's & Laadpalen: Maar liefst 67% beschikt over een elektrische auto en een aanstuurbare laadpaal.
 * Data & Voorspellingen: Het inzicht in het eigen historisch huisverbruik is nog niet overal goed beschikbaar, en de meeste respondenten hebben op dit moment nog geen uur- of kwartier-voorspelling voor hun zon-opbrengst ingesteld.
 * PyScript: Bij 30% staat PyScript al te draaien in Home Assistant. De overige respondenten geven aan dit prima te willen installeren om Helios te kunnen gebruiken.

## Belangrijke wensen & inzichten voor de roadmap:
 * Meerdere systemen aansturen: Er is een duidelijke wens om meerdere batterijen en zelfs meerdere zonne-omvormers tegelijk te kunnen beheren.
 * Nul op de meter / Zonder teruglevering: Niet iedereen wil puur winst maken op teruglevering; er is veel vraag naar het optimaliseren van de eigen kosten zonder stroom te verkopen aan het net. Het aankomende vervallen van de salderingsregeling maakt dit voor velen extra urgent.
 * Uitleg & Transparantie: Het voordeel van een wiskundige LP-optimizer is nog niet voor iedereen meteen helder. Transparante uitleg over de exacte werking en de financiële voordelen wordt dus een belangrijk onderdeel van het project.

## Vervolgstappen:
Met deze data kan ik gerichter aan de slag met de juiste koppelingen (zoals de Marstek/HBC-integraties en ondersteuning voor meerdere batterijen). De eerste kandidaten voor de testgroep ontvangen binnenkort bericht!

Gebaseerd op deze uitkomsten heb ik een aantal concrete conclusies en vervolgstappen:
 * Architectuur & Aansturing: Helios wordt gekoppeld als een extra strategie binnen HBC. Hierdoor maakt de optimizer direct gebruik van de al aanwezige batterij-aansturing van HBC.
 * Energieprijzen: Voor de dynamische prijzen sluit de optimizer aan op de importprijzen van HBC. Omdat exportprijzen daarin nog niet direct beschikbaar zijn, wordt hiervoor een conversie ingezet.
 * Zonvoorspelling: Aangezien HBC nog geen uurbasis-voorspelling voor zonne-energie bevat, wordt er een koppeling gemaakt met de Forecast.Solar REST API.
 * Huisverbruik: Een dynamische voorspelling van het verbruik vergt nog extra ontwikkeltijd. Dit wordt in eerste instantie opgelost met een handmatig aanpasbare vaste voorspelling per uur/kwartier.
 * Implementatie (PyScript vs Custom Component): Gezien de grote bereidheid om PyScript te installeren, wordt de ontwikkeling van een eigen Custom Component uitgesteld. De eerste versie draait volledig via PyScript.
 * Zonne-energie & Omvormers: Uit het rekenmodel rolt een specifieke zonne-energiestrategie. Hiermee kan de omvormer via een eigen automatisering worden aangestuurd of gedimd.
 * Toekomstige prioriteiten: Kost-optimalisatie (zoals nul op de meter zonder teruglevering) en de integratie van EV's/laadpalen staan bovenaan de verlanglijst voor opvolgende updates.
