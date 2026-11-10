# CALVIN Failure Analysis

[简体中文](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/README.md) · [English](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.ja.md) · **Deutsch** · [Français](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.es.md) · [Português](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.pt.md)

An welchem Schritt scheitert ein Roboter, wenn keine der fünfstufigen Sequenzen gelingt? Mit dem CALVIN-Simulator und einem öffentlich verfügbaren MCIL-Modell untersuche ich Abweichungen bei den Aktionen und die Wiederaufnahme nach Fehlern. Mit Abbildungen, Daten und einem Bericht auf Chinesisch.

Python · CALVIN · MCIL · [Experimentbericht anzeigen](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/report.pdf)

Dies ist ein kleines Forschungsprojekt, das auf der Simulationsumgebung [CALVIN](https://github.com/mees/calvin) und dem offiziellen MCIL-Vortrainingsmodell basiert.

Das Projekt konzentriert sich auf die folgenden Fragen: **Wenn die Erfolgsrate einer Langstrecken-Roboteraufgabe 0 ist, wo genau versagt der Roboter, warum versagt er und ob er sich nach einem Versagen erholen kann?**

Die herkömmliche Erfolgsquote auf Aufgabenebene berücksichtigt nur den endgültigen Erfolg oder Misserfolg und kann nicht zwischen den folgenden Situationen unterscheiden:

- Das Modell beginnt nicht mit dem ersten Schritt;
- Das Modell kann einige Schritte ausführen, bei nachfolgenden Aufgaben häufen sich jedoch Fehler.
- Das Modell versteht die Aufgabe, aber die kontinuierliche Kontrolle lässt nach und nach nach;
- Das Modell ist nur in wenigen Ausgangszuständen erfolgreich;
- Das Modell kann sich nach einem Ausfall nicht selbstständig erholen.

## Experimenteller Prozess

1. Spielen Sie den realen Demonstrationsverlauf ab, um die Umgebung, das Aktionsformat und die Erfolgsbestimmung zu überprüfen.
2. Getestet wurden jeweils drei Einzelaufgaben: Öffnen der LED, Bewegen der Schiebetür nach links und Öffnen der Schublade.
3. Führen Sie 100 feste Fünf-Schritte-Programmsequenzen aus und zeichnen Sie SR@1 bis SR@5 auf.
4. Ersetzen Sie die direkte Fehlerverbindung der Positionierung durch Position, Haltung und Greiferwirkung.
5. Es wurde ein Fehler behoben, bei dem nach einem Fehler erneut versucht und die Diagnose fortgesetzt werden konnte.

## Hauptergebnisse

| experimentieren | Ergebnis |
|---|---:|
| LED einschalten | 2/9 |
| Schiebetür links | 0/9 |
| offene Schublade | 0/9 |
| 100 Fünf-Schritte-Sequenzen erfolgreich abgeschlossen | 0/100 |
| SR@1 | 1% |
| SR@2—SR@5 | 0% |
| Wiederherstellungswiederholung behoben | 0/10 |
| Setzen Sie die Ausführung nach einem Fehler fort | 0/50 Schritte |

Eine LED-Erfolgsbedingung wird beim 94. Aktionsschritt nach der unabhängigen Ausführung immer noch erfüllt, was darauf hinweist, dass das Modell nicht völlig unfähig ist, aber empfindlich auf den Anfangszustand reagiert. Der Vergleich der Aktionskomponenten zeigte, dass alle drei Aufgabentypen fehlschlugen, nachdem nur die Positionsaktion ersetzt wurde; Bei freier Ausführung vergrößerte sich der Abstand zwischen der Positionsaktion und der Demonstrationsflugbahn auf 72,9–194,2 mm. Das LED-Gehäuse zeigte außerdem an wichtigen Stellen eine inkonsistente Greiferausrichtung.

![experimentelle Ergebnisse auf Prozessebene](../../figures/process_level_results.png)

## Erfolgs- und Misserfolgsfälle

| LED-Erfolgsgeschichten: Erste Schritte | LED-Erfolgsgeschichte: Ende |
|---|---|
| ![](../../figures/led_success_start.png) | ![](../../figures/led_success_end.png) |

| LED-Ausfallfall: Erste Schritte | LED-Ausfallfall: nach der Ausführung von 360 Schritten |
|---|---|
| ![](../../figures/led_failure_start.png) | ![](../../figures/led_failure_end.png) |

## Fazit

Dieses Experiment zeigt, dass die Erfolgsrate auf Aufgabenebene zur Messung des endgültigen Abschlusses geeignet ist, aber nicht ausreicht, um den langfristigen Prozess des Scheiterns einer Aufgabe zu erklären. Zumindest sollten auch der erste fehlgeschlagene Schritt, die kontinuierliche Abschlussdauer, die Abweichung der Bewegungskomponente und die Wiederherstellungsergebnisse aufgezeichnet werden.

Aktuelle Erkenntnisse belegen, dass „die Positionsabweichung im geschlossenen Regelkreis eine direkte Fehlerverbindung ist, die allen drei Arten von Aufgaben gemeinsam ist“, sie kann jedoch nicht zur Bestimmung der einzigen Ursache innerhalb des Modells verwendet werden. Diese Schlussfolgerung gilt nur für die in diesem Projekt verwendeten öffentlichen Gewichte, Debug-Daten und Versuchsbedingungen.

## Projektstruktur

```text
.
├── README.md
├── docs/
│   ├── report.pdf                  # Chinesischer Laborbericht
│   └── internship-summary.md       # Zusammenfassung des wissenschaftlichen Forschungspraktikums
├── figures/                        # Zusammenfassendes Diagramm und Fall-Screenshots
├── results/                        # JSON vs. CSV-Experimentergebnisse
└── src/                            # Evaluierungs- und Diagnosecode
```

Vollständiger chinesischer Bericht: [docs/report.pdf](../../docs/report.pdf)

Informationen zur Auswahl der Forschungsfragen, der von mir abgeschlossenen Arbeiten, des Debugging-Prozesses und der Forschungsbeschränkungen während des wissenschaftlichen Forschungspraktikums finden Sie unter: [docs/internship-summary.md](../../docs/internship-summary.md)

## Reproduktionsanleitung

Der Code muss in der offiziellen CALVIN-Umgebung ausgeführt werden und Folgendes vorbereiten:

- CALVIN-Umgebung mit `calvin_models`;
- Umgebungs-D-Daten oder offizielle Debug-Daten;
- Offizieller `D_D_static_rgb_baseline` MCIL-Kontrollpunkt;
- Python 3.8, PyTorch 1.13.1, PyTorch Lightning 1.8.6 und Hydra 1.1.1.

Haupteingang:

```bash
python src/run_calvin_mcil_cpu.py \
  --dataset-path /path/to/calvin_dataset \
  --train-folder /path/to/D_D_static_rgb_baseline \
  --checkpoint /path/to/mcil_baseline.ckpt \
  --num-sequences 100 \
  --output results/evaluation.json
```

Informationen zur Einzelaufgabenauswertung und verschiedenen Diagnoseskripts finden Sie unter [src/README.md](../../src/README.md). Dieses Repository verteilt den CALVIN-Datensatz oder die Modellgewichte nicht weiter.

## Forschungsgrenzen

- Es wurde nur ein öffentlicher MCIL-Kontrollpunkt getestet;
- Verwendet ca. 1,3 GB Debug-Daten, nicht den vollständigen Datensatz;
- Unter Verwendung der CPU-Inferenz wurden keine echten Roboterexperimente durchgeführt;
- Bei den Ergebnissen handelt es sich um reproduzierbare Studien und nicht um die offiziellen Ranking-Ergebnisse von CALVIN.

## Danksagungen

Dieses Projekt nutzt die CALVIN-Benchmark-Umgebung und ihre öffentlichen Modelle. Bitte halten Sie sich an die ursprüngliche Projektlizenz und zitieren Sie das CALVIN-Papier, wenn Sie relevante Daten, Umgebungen oder Modelle verwenden:

> Mees et al., *CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks*, IEEE Robotics and Automation Letters, 2022.
