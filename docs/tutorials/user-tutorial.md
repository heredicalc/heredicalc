# User Tutorial: Kosegregationsanalyse mit BRCA2

Dieses Tutorial führt Sie Schritt für Schritt durch eine vollständige
Kosegregationsanalyse mit einem Gen, das nicht als Built-in enthalten ist.
Als durchgängiges Beispiel dient **BRCA2**.

---

## Voraussetzungen

- HerediCalc ≥ 4.1.0 installiert — prüfen mit:
  ```bash
  heredicalc --version
  ```
- R ≥ 4.2 mit den Paketen `segregatr` und `kinship2`:
  ```r
  install.packages("kinship2")
  install.packages("segregatr")
  ```
- Eine Pedigree-Datei im COOL3-TSV-Format

---

## Schritt 1 — Orientierung: Was ist bereits eingebaut?

Verschaffen Sie sich zunächst einen Überblick über die verfügbaren Plugins:

```bash
heredicalc plugins list --kind phenotype_model
heredicalc plugins list --kind trait_mapper
```

HerediCalc enthält für **BRCA1** eine vollständige Built-in-Konfiguration
(RR-Tabelle + CRHF-Wert). Für **BRCA2** ist der CRHF-Wert (0,0013) eingebaut,
die RR-Tabelle fehlt jedoch — sie muss vom Nutzer bereitgestellt werden.

---

## Schritt 2 — RR-Tabelle vorbereiten

### Format

Die RR-Tabelle ist eine CSV-Datei mit folgenden Spalten:

| Spalte | Beschreibung |
|--------|-------------|
| `gene` | Name der genetischen Entität, z. B. `BRCA2` |
| `gender` | `F` (weiblich) oder `M` (männlich) |
| `age_from` | Untere Altersgrenze des Bandes (inklusiv) |
| `age_to` | Obere Altersgrenze (inklusiv); **leer** = offenes Ende |
| `phenotype` | Kanonischer Phänotyp-Name (s. u.) |
| `heterozygous_rr` | Relatives Risiko für Heterozygote |
| `homozygous_rr` | Relatives Risiko für Homozygote (bei dominanten Genen = `heterozygous_rr`) |

**Kanonische Phänotypnamen** des `hbopc_prca`-Modells:
`BreastCancer`, `OvarianCancer`, `PancreaticCancer`, `ProstateCancer`

### Template generieren

Falls Sie noch keine RR-Datei haben, erzeugt HerediCalc ein vorausgefülltes
Template mit allen Standardaltersbändern und RR = 1.0:

```bash
heredicalc add trait BRCA2
```

Der Wizard fragt nach CRHF, Kind und optionalen Metadaten. Da kein `--rr-file`
angegeben wurde, wird das Template geschrieben und der Pfad angezeigt:

```
No --rr-file provided. A template has been written to:
  ~/Library/Application Support/heredicalc/traits/rr/BRCA2_template.csv
```

Öffnen Sie die Datei, tragen Sie Ihre RR-Werte ein und fahren Sie mit
Schritt 3 fort.

### Beispielwerte für BRCA2

!!! warning "Nur zur Illustration"
    Die folgenden Werte sind vereinfachte Schätzungen nach Antoniou et al. (2003)
    und dienen ausschließlich als Tutorial-Beispiel. Verwenden Sie für produktive
    Analysen validierte RR-Schätzungen aus aktueller Fachliteratur.

```csv
gene,gender,age_from,age_to,phenotype,heterozygous_rr,homozygous_rr
BRCA2,F,0,29,BreastCancer,7.5,7.5
BRCA2,F,30,39,BreastCancer,11.0,11.0
BRCA2,F,40,49,BreastCancer,6.5,6.5
BRCA2,F,50,59,BreastCancer,4.5,4.5
BRCA2,F,60,69,BreastCancer,3.8,3.8
BRCA2,F,70,79,BreastCancer,2.8,2.8
BRCA2,F,80,,BreastCancer,1.0,1.0
BRCA2,M,0,79,BreastCancer,6.0,6.0
BRCA2,M,80,,BreastCancer,1.0,1.0
BRCA2,F,0,29,OvarianCancer,1.0,1.0
BRCA2,F,30,39,OvarianCancer,4.0,4.0
BRCA2,F,40,49,OvarianCancer,8.5,8.5
BRCA2,F,50,59,OvarianCancer,7.0,7.0
BRCA2,F,60,69,OvarianCancer,5.0,5.0
BRCA2,F,70,79,OvarianCancer,2.5,2.5
BRCA2,F,80,,OvarianCancer,1.0,1.0
BRCA2,M,0,,OvarianCancer,1.0,1.0
BRCA2,F,0,49,PancreaticCancer,3.5,3.5
BRCA2,F,50,79,PancreaticCancer,2.0,2.0
BRCA2,F,80,,PancreaticCancer,1.0,1.0
BRCA2,M,0,49,PancreaticCancer,3.5,3.5
BRCA2,M,50,79,PancreaticCancer,2.0,2.0
BRCA2,M,80,,PancreaticCancer,1.0,1.0
BRCA2,M,0,49,ProstateCancer,2.5,2.5
BRCA2,M,50,69,ProstateCancer,4.5,4.5
BRCA2,M,70,79,ProstateCancer,2.0,2.0
BRCA2,M,80,,ProstateCancer,1.0,1.0
```

---

## Schritt 3 — Trait anlegen

Importieren Sie die ausgefüllte RR-Datei zusammen mit CRHF-Wert und optionalen
Metadaten:

```bash
heredicalc add trait BRCA2 \
  --crhf 0.0013 \
  --kind gene \
  --meta "locus=13q12.3" \
  --meta "omim_nr=600185" \
  --rr-file BRCA2_rr.csv
```

Wenn der Import erfolgreich war:

```
✓ RR table imported from BRCA2_rr.csv
✓ Trait 'BRCA2' added (CRHF=0.0013, kind=gene).
```

Die Daten werden lokal gespeichert unter:

- **macOS:** `~/Library/Application Support/heredicalc/traits/`
- **Linux:** `~/.local/share/heredicalc/traits/`

---

## Schritt 4 — Phenotyp-Modell wählen

HerediCalc kennt zwei eingebaute Phenotyp-Modelle:

| Modell | Phenotypen | Geeignet für |
|--------|-----------|--------------|
| `hbopc` | Breast, Ovarian, Pancreatic | BRCA1, PALB2, … |
| `hbopc_prca` | Breast, Ovarian, Pancreatic, **Prostate** | **BRCA2**, HOXB13, … |

Da BRCA2 mit Prostatakrebs assoziiert ist, verwenden wir `hbopc_prca` und den
passenden Mapper `ci5_ix_hbopc_prca` (für CI5-Edition IX).

---

## Schritt 5 — Konfigurationsdatei erstellen

Statt alle Parameter bei jedem Aufruf einzeln anzugeben, speichern Sie sie in
einer YAML-Datei:

```bash
heredicalc add config
```

Der interaktive Wizard fragt nach genetischer Entität, Allelfrequenz,
Inzidenzquelle und Population. Geben Sie am Ende einen Dateinamen an
(z. B. `brca2_latvia.yml`). Das Ergebnis:

```yaml
computation:
  genetic_entity: BRCA2
  allele_freq: 0.0013

plugins:
  incidence_source: ci5_ix
  phenotype_model: hbopc_prca
  trait_mapper: ci5_ix_hbopc_prca
  params:
    population: "Latvia"
    age_bands: [30, 40, 50, 60, 65, 70, 80]
```

!!! note "Phenotyp-Modell manuell eintragen"
    Der Wizard leitet den Mapper automatisch aus der Inzidenzquelle ab
    (`ci5_ix` → `ci5_ix_hbopc`). Für `hbopc_prca` müssen Sie `phenotype_model`
    und `trait_mapper` in der YAML-Datei manuell auf `hbopc_prca` bzw.
    `ci5_ix_hbopc_prca` ändern.

---

## Schritt 6 — Analyse ausführen

```bash
heredicalc run pedigree.ped --config brca2_latvia.yml
```

Ausgabe:

```
FLB = 12.3450  (pedigree.ped)
```

Für maschinell verarbeitbaren JSON-Output:

```bash
heredicalc run pedigree.ped --config brca2_latvia.yml --format json
# {"pedigree": "pedigree.ped", "flb": 12.345}
```

Mehrere Pedigrees auf einmal:

```bash
heredicalc batch ./pedigrees/ --config brca2_latvia.yml
```

---

## Schritt 7 — Ergebnis interpretieren

Der FLB-Wert quantifiziert die Kosegregations-Evidenz:

| FLB | Interpretation |
|-----|----------------|
| < 1 | Gegen Kosegregation |
| 1–8 | Schwache bis moderate Evidenz |
| ≥ 8 | Starke Evidenz für Pathogenität |
| ≥ 350 | Sehr starke Evidenz (ACMG/InSiGHT PP1_Strong) |

Die genauen Schwellenwerte hängen vom verwendeten Klassifikationsrahmen ab
(ACMG, InSiGHT, ClinGen). Konsultieren Sie die einschlägigen Leitlinien.

Für die mathematischen Grundlagen des FLB-Algorithmus siehe
[FLB Computation](../algorithms/flb-computation.md).

---

## Trait verwalten

```bash
# Überblick über alle eigenen Traits
cat "$(python -c 'import platformdirs; print(platformdirs.user_data_dir("heredicalc"))')/traits/traits.yaml"

# RR-Werte nachträglich ersetzen
heredicalc edit trait BRCA2 --rr-file updated_brca2.csv

# BRCA2 als Basis für ein neues Gen klonen
heredicalc clone trait BRCA2 PALB2 --crhf 0.0003

# Trait wieder entfernen
heredicalc remove trait BRCA2
```
