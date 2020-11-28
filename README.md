# USE CASE: Maschinenfehler-Erkennung

> ## Aufgabenstellung und Bewertungskriterien Doku

> - Dokumentation der Anwendung ist vorhanden
> - Dokumentation enthält:
> - Idee der Anwendung
> - Architektur
> - Entwurf
> - Screencast der Demo
> - etc.

## Möglicher Aufbau der Doku / Readme

- [x] Idee der Anwendung
- [x] Anwendungsszenarien
- [ ] Architektur
- [ ] Entwurf
- [ ] Screencast
- [ ] etc.

# Idee der Anwendung

- Maschine(n) von Hersteller XY produziert Teile T
- Nach der Produktion wertet ein Arbeiter die Teile aus
- Mitarbeiter hat einen Bildschirm mit einem Bild des Teiles, über welches ein Raster gelegt ist
- Mitarbeiter klickt defekte Stelle an
  - optional: Fehlergrund wird mitangegeben

### Skizze

![Skizze](https://i.ibb.co/6mdw78w/Skizze.png)

_hier ggf. Späteres Frontend einfügen_

# Anwendungsszenarien

- Häufige Fehler erkennen
- Zusammenhänge von Fehler erkennen
  - Fehler immer zu bestimmter Uhrzeit / bestimmter Tag
  - Fehler geht von bestimmter Maschine aus
  - Fehler tritt in bestimmtem Werk auf

# Architektur

> Hier Text einfügen

![Skizze](https://i.ibb.co/85QTn3Z/Architektur.png)

# Entwurf

> Hier Text einfügen

# Screencast

> Video oder Link zum Video einfügen

# Sonstiges

> Befehle, wie man den Use-Case zum Laufen bekommt (siehe alte README)

---

---

# altes README

### Use Case: Popular NASA Shuttle Missions

```json
{
  "mission": "sts-10",
  "timestamp": 1604325221
}
```

### Prerequisites

A running Strimzi.io Kafka operator

```bash
helm repo add strimzi http://strimzi.io/charts/
helm install my-kafka-operator strimzi/strimzi-kafka-operator
```

A running Hadoop cluster with YARN (for checkpointing)

```bash
helm repo add stable https://kubernetes-charts.storage.googleapis.com/
helm install --namespace=default --set hdfs.dataNode.replicas=2 --set yarn.nodeManager.replicas=2 --set hdfs.webhdfs.enabled=true my-hadoop-cluster stable/hadoop
```

### Deploy

To develop using [Skaffold](https://skaffold.dev/), use `skaffold dev`.
