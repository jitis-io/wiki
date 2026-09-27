# Bestandsblatt – [Kunde / Standort]

| Dokument | Stand |
| --- | --- |
| Dokument-ID / Revision | [ID] / [Revision] |
| Zuletzt fachlich geprüft | [Datum · Name] |
| Status | [Entwurf oder bereitgestellter Stand] |

Der gültige Stand steht auf dieser Wiki-Seite. Eine Veröffentlichung ist keine
vertragliche Kundenabnahme; eine vereinbarte Abnahme wird separat dokumentiert.
Keine Passwörter, Zugangstoken oder Wiederherstellungsschlüssel eintragen.

## Geräte

Die Geräte-ID bezeichnet dauerhaft dasselbe Gerät und wird im Plan sowie in
Tickets verwendet. Bei einem Gerätetausch bekommt das Ersatzgerät eine neue ID.

| Geräte-ID | Funktion / Standort im Gebäude | Hersteller / Modell | Seriennummer |
| --- | --- | --- | --- |
| [stabile ID] | [Funktion · Raum / Schrank] | [Hersteller · Modell] | [Seriennummer] |

## Netzwerk und Adressen

| Netz / Zweck | Präfix / Netzmaske | VLAN-ID | IP-Adresse → Geräte-ID / Schnittstelle |
| --- | --- | --- | --- |
| [Bezeichnung · Zweck] | [Präfix oder Netzmaske] | [ID oder nicht verwendet] | [Adresse → Geräte-ID / Schnittstelle] |

Nur belegte oder ausdrücklich reservierte Zuordnungen eintragen. Ungeprüfte
Angaben als „ungeprüft“ kennzeichnen; keine Werte aus Vermutungen ergänzen.

## Ports und Gegenstellen

| Geräte-ID / Port | Gegenstelle / Port | Kabel- oder Dosenkennung | Nutzung |
| --- | --- | --- | --- |
| [Geräte-ID / Port] | [Geräte-ID, Patchfeld oder Dose / Port] | [Kennung] | [Zweck / VLAN-Zuordnung] |

## Plan und Änderungsbezug

- Übersichtsplan: [Plan · Dokument-ID und Revision](PLAN-URL)
- Anlass der letzten Änderung: [kurze Beschreibung]
- Zugehöriges Ticket / Auftrag: [Referenz](TICKET-URL)

Bei einem Gerätetausch, einer Verkabelungs- oder Adressänderung nur die
betroffenen Angaben prüfen und aktualisieren. Den Plan anpassen, wenn sich
die dargestellte Übersicht ändert.
