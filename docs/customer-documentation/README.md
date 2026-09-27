# Kundendokumentation: einfacher Ablauf

Der gültige, kundenfreigegebene Stand steht im privaten Kunden-Wiki. Bearbeitbare
Quellen und Originalunterlagen bleiben im internen SharePoint-Kundenordner.
OneNote dient für Fotos, Skizzen und offene Fragen vor Ort; es wird keine zweite
dauerhaft gepflegte Inventarliste. ERPNext hält Ticket, Auftrag, Zeit und Belege.
NetBox ist kein Bestandteil dieses Arbeitsablaufs. Es gibt keinen zusätzlichen Sync.

## Drei Bausteine genügen

1. **[Bestandsblatt](vorlagen/Bestandsblatt.md):** Geräte mit stabiler ID,
   IP/VLAN und Port ↔ Gegenstelle. Diese Tabellen sind die führende gepflegte
   Quelle der technischen Angaben. Seriennummern der tatsächlichen Geräte
   eintragen; kaufmännische Lieferbelege bleiben in ERPNext.
2. **[Übersichtsplan](vorlagen/JITIS-Netzplan-A4-Vorlage.drawio):** wichtige
   Geräte und Verbindungen mit denselben Geräte-IDs. Die vollständige
   Portbelegung bleibt im Bestandsblatt, nicht zusätzlich im Bild.
3. **[Betriebsanleitung](vorlagen/Betriebsanleitung.md):** Zweck, Bedienung,
   systemspezifisch geprüfter Wiederanlauf, typische Fehler und Ansprechpartner.
   Nur erstellen, wenn sie dem Kunden tatsächlich hilft.

Das [Planbeispiel](vorlagen/JITIS-Netzplan-A4-Beispiel.drawio) enthält ausschließlich
erfundene Demonstrationsdaten. Kunde/Standort, Dokument-ID, Revision, Status und
Blatt stehen im Plankopf. Das ist eine praktische Vorlage, keine DIN-Zertifizierung.
SVG/PNG sind Vorschauen; die `.drawio`-Datei ist die bearbeitbare Quelle. Die native
Darstellung in draw.io vor dem ersten Kundeneinsatz prüfen.

## Ports und mehrere Racks

Auch die vollständige Portbelegung gehört in die Wiki-Tabelle. Pro Verbindung
eine Zeile; Patchpanel-Vorder-/Rückseite, Kabel und Dosen eindeutig benennen.
Für mehrere Racks pro Rack einen Abschnitt mit Gerät und Höheneinheit sowie
einen gemeinsamen Verbindungsplan verwenden. Ein Beispiel für den Kabelweg ist
`SW-R01-01 / 12 → PP-R01-01 / 12 → D-EG-012 → AP-EG-01`.
Benötigte Reserven ausdrücklich kennzeichnen; keine ungeprüften Werte ergänzen.

draw.io zeigt Topologie oder Rackanordnung. Es ersetzt keine echte Schaltplan-
oder CAD-Quelle für Hardwareentwicklung. Tabellen liefern keine automatische
Kabelverfolgung oder IP-Plausibilitätsprüfung; das bleibt eine bewusste Grenze.

## Nach einer konkreten Änderung

1. Vor Ort nur Nötiges aufnehmen: Foto/Skizze, offene Frage und Ticketbezug.
2. Bestätigte Änderungen in der betroffenen Wiki-Tabelle oder Anleitung
   nachziehen. Unsichere Angaben kennzeichnen; nicht jede Arbeitsnotiz übertragen.
3. Den Plan nur bei geänderten dargestellten Zusammenhängen anpassen. Quelle
   beispielsweise unter `05 Betrieb und Dokumentation/Quellen/[Plan-ID].drawio`
   im internen Kundenordner halten und dessen vorhandene Versionshistorie nutzen.
4. Neuen PNG/WebP-Export als neue private Datei hochladen, im Wiki-Entwurf
   einsetzen, Stand/Revision und Ticketbezug ergänzen und den Kundenstand
   veröffentlichen. Eine Veröffentlichung ersetzt keine vertragliche Abnahme;
   eine benötigte Abnahme bezieht sich separat auf die konkrete Revision.
5. Arbeitsnotiz auf den gültigen Wiki-Stand verweisen lassen. Kein Tagesabschluss
   und keine zusätzliche tägliche Dokumentationspflicht.

Keine Passwörter, Zugangstoken oder Wiederherstellungsschlüssel in Seiten,
Pläne, Kundentexte oder Vorlagen schreiben. Pro Kunde getrennte Quellen nutzen;
ausgeblendete Ebenen ersetzen keine Kundentrennung.

## Sichere Veröffentlichung im bestehenden Portal

Der Kundenpfad unterstützt private PNG/JPEG/WebP-Dateien sowie PDF und TXT bis
jeweils 10 MiB. SVG und `.drawio` bleiben intern. PDF als normalen Downloadlink
anbieten: Die native Wiki-PDF-Karte benötigt Inhalte, die der Portal-Sanitizer
entfernt. Maßgeblich sind JPI `attachments.py` und `portal_api/wiki.py` sowie
Portal `app/portal/_lib/documentation-content.ts`.

Beim PNG-Export **„Include a copy of my diagram“ ausschalten**: sonst kann die
bearbeitbare Zeichnung in der Bilddatei enthalten sein. PDF lokal über Drucken/PDF
oder die Desktop-App erzeugen. Siehe [PNG-Export](https://www.drawio.com/docs/manual/export/export-to-png/)
und [PDF-Export](https://www.drawio.com/docs/manual/export/export-to-pdf/).

Wiki-Revisionen bewahren Seiteninhalt mit Dateiverweisen, keine vollständige
Binärdatei-Historie. Neue Exporte deshalb als neue Datei hochladen; benötigte
alte Anlagen und interne Quellen erhalten. Kundenrechte verwaltet JPI; diese
Vorlagen ändern oder ersetzen keine Berechtigungsprüfung.
