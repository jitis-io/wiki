# Kundendokumentation: einfacher Ablauf

Der gültige, kundenfreigegebene Stand steht im privaten Kunden-Wiki. Bearbeitbare
Quellen und Originalunterlagen bleiben im internen SharePoint-Kundenordner.
OneNote dient für Fotos, Skizzen und offene Fragen vor Ort; es wird keine zweite
dauerhaft gepflegte Inventarliste. ERPNext hält Ticket, Auftrag, Zeit und Belege.
NetBox ist kein Bestandteil dieses Arbeitsablaufs. Es gibt keinen zusätzlichen Sync.

## Ein Space je Kunde, wenige Seiten

Der **Space-Name ist frei wählbar**, zum Beispiel `Musterfirma GmbH`. Die
**Route bleibt die Kundennummer**, zum Beispiel `k-2601999`. Der Firmenname darf
sich ändern, ohne Links oder Kundenrechte umzubauen. Ein Präfix `Portal` ist
nicht nötig. Bereits verteilte Routen nicht allein aus optischen Gründen ändern;
eine Titeländerung bewegt keine Seiten.

Als Anfang genügen drei Seiten nebeneinander:

- **Übersicht:** Standort, Ansprechpartner, betreute Systeme und wichtige Links.
- **Bestandsblatt:** Geräte, IPs/VLANs, Ports und der eingebettete Netzplan.
- **Betrieb:** die tatsächlich benötigten Anleitungen, Sicherung und Wiederanlauf.

Erst bei Bedarf einzelne Anleitungen oder Standorte in eine Gruppe verschieben.
Eine, höchstens zwei Ebenen reichen normalerweise. Keine leeren Kapitel auf
Vorrat anlegen. Inhalts-Tabs sind im aktuellen Wiki v3 bereits entfallen;
die alten Datenfelder dienen nur der Kompatibilität mit vorhandenen Revisionen.

Du bearbeitest unter `/wiki-app/spaces/<interne-ID>/…`. Diese technische URL
ist normal und bleibt beim Original. Kunden öffnen im Portal
`/documentation/<Kundennummer>`; die ausgewählte Unterseite steht in `?page=…`.
Der native Wiki-Pfad `/<Kundennummer>/…` ist deshalb kein Ersatz für den
Kundenportal-Link. Titel, Route und interne ID sind keine Berechtigungen.

## Einen Kunden sicher einrichten

1. Den Space mit Firmennamen und Kundennummer als Route anlegen. Ab Wiki
   `3.2.1+jitis.3` ist **Portal Only** im Erstelldialog vorausgewählt. Für
   Kundendokumentation eingeschaltet lassen; die Gastrolle wird dann nicht
   hinzugefügt.
2. Bei bestehenden Spaces und **bis zum Rollout dieser Version** zuerst im
   ERP-Desk den zugehörigen **Wiki Space** öffnen und **Portal Only** setzen,
   bevor Kundendaten eingefügt werden. Der bisherige Upstream-Dialog legt
   veröffentlichte Spaces mit `Guest: Read` an. Portal Only sperrt den nativen
   Kundenzugriff; interne Wiki-Verwalter können weiter bearbeiten. `Published`
   ersetzt diesen Schutz nicht.
3. In **JITIS Portal Tenant** den vorhandenen ERP-Kunden genau diesem Space
   zuordnen und aktivieren. Ein Space gehört genau einem Kunden. Keine
   zusätzlichen Frappe-Rollen je Kunde erzeugen.
4. Den Kundenkontakt mit seiner bestätigten Portalidentität und dem passenden
   **JITIS Portal Access Grant** einrichten. Für reine Dokumentation genügt
   `Documentation`. Die vollständige Einrichtung beschreibt
   [JPI](https://github.com/jitis-io/jitis-platform-integration/blob/main/docs/deployment.md#customer-onboarding-and-service-capabilities).
5. Erst jetzt Inhalte schreiben und freigeben. Mit dem berechtigten Kunden
   prüfen: Seite, Bild, PDF. Mit einem anderen Kunden muss derselbe Zugriff
   abgewiesen werden. Die interne Administratoransicht beweist keine
   Kundentrennung.

`Published` an Space und Seite bedeutet, dass der freigegebene Stand lesbar ist.
Bei **Portal Only** bleibt er auf berechtigte Portalkunden beschränkt. Bearbeitungen
werden im nativen Änderungsentwurf gespeichert; erst dessen Veröffentlichung
übernimmt sie in den Kundenstand. Die Vorschau und der Editor sind interne
Arbeitsflächen, das Portal zeigt den freigegebenen Inhalt.

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
jeweils 10 MiB. SVG und `.drawio` bleiben intern. Der Umfang ist bewusst kleiner
als der interne Wiki-Editor:

| Inhalt | Kundenportal |
| --- | --- |
| Text, Überschriften, Listen, Tabellen, Codeblöcke | Lesbar, einschließlich Inhaltsverzeichnis und Sprungmarken |
| Seiten und Gruppen | Baumansicht; Suche nach Seitentitel und Route, keine Volltextsuche |
| Private PNG/JPEG/WebP-Bilder | Anzeige und vergrößerte Ansicht über den geprüften Dateizugriff |
| PDF | Download; keine zweite interaktive PDF-Anwendung im Portal |
| Externe Webseiten | Normaler Link; keine eingebetteten Fremdskripte, Videos oder iframes |
| Redaktion, Versionsvergleich, Änderungsfreigabe, Git Sync | Interne Wiki-Funktionen, keine Kundenoberfläche |

PDF-Dateien lassen sich über die native Editor-Funktion einfügen. Der
Portal-Review ergänzt dafür einen sichtbaren Downloadlink in der PDF-Karte;
bis diese Portal-Version ausgerollt ist, einen normalen beschrifteten PDF-Link
verwenden. Maßgeblich sind JPI `attachments.py` und `portal_api/wiki.py` sowie
Portal `app/portal/_lib/documentation-content.ts`.

Beim PNG-Export **„Include a copy of my diagram“ ausschalten**: sonst kann die
bearbeitbare Zeichnung in der Bilddatei enthalten sein. PDF lokal über Drucken/PDF
oder die Desktop-App erzeugen. Siehe [PNG-Export](https://www.drawio.com/docs/manual/export/export-to-png/)
und [PDF-Export](https://www.drawio.com/docs/manual/export/export-to-pdf/).

Wiki-Revisionen bewahren Seiteninhalt mit Dateiverweisen, keine vollständige
Binärdatei-Historie. Neue Exporte deshalb als neue Datei hochladen; benötigte
alte Anlagen und interne Quellen erhalten. Kundenrechte verwaltet JPI; diese
Vorlagen ändern oder ersetzen keine Berechtigungsprüfung.

## Draw.io: zuerst ein zuverlässiger Plan

Für den Start bleibt die `.drawio`-Quelle im internen Kundenordner und ein
PNG-Export auf der passenden Wiki-Seite. Das nutzt den vorhandenen privaten
Bildzugriff, die Vergrößerung und die Seitenrevisionen ohne zusätzliche App.
Eine SVG-Datei allein löst das Bearbeiten nicht; eine `.drawio`-Datei allein
wird vom Wiki nicht als Zeichnung dargestellt.

Direktes Bearbeiten im Wiki ist technisch möglich: Der offizielle
[draw.io-Einbettungsmodus](https://www.drawio.com/docs/reference/embed-mode/)
tauscht Zeichnungsdaten und Exportbilder über `postMessage` mit einem Editor
im iframe aus. Dafür müsste die Integration Quelle und Vorschaubild gemeinsam
privat speichern, Speicherfehler behandeln, Nachrichtenherkunft prüfen und
den freigegebenen Stand von Entwürfen trennen. Ein bloßer iframe-Link erledigt
das nicht. Im Kundenportal wäre weiterhin nur die freigegebene Vorschau nötig.

Diese Erweiterung erst angehen, wenn der manuelle Export im tatsächlichen
Alltag regelmäßig stört. Dann einen kleinen Editor-Baustein mit automatischem
PNG-Export bauen, keine neue Diagrammverwaltung oder Synchronisation. Bis dahin
bleiben Wiki-Updates und die Kundentrennung leichter überprüfbar.
