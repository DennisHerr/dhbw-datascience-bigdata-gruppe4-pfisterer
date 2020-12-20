# USE CASE: Maschinenfehler-Erkennung

> ## Aufgabenstellung und Bewertungskriterien Doku

> - Dokumentation der Anwendung ist vorhanden
> - Dokumentation enthält:
> - Idee der Anwendung
> - Architektur
> - Entwurf
> - Screencast der Demo
> - etc.

## Inhaltsverzeichnis

1. [Idee der Anwendung](#idee)
2. [Anwendungsszenarien](#anwendung)
3. [Architektur](#architektur)
4. [Frontend](#frontend)
5. [Starten der Anwendung](#start)
6. [Screencast](#screencast)
7. [Sonstiges](#sonstiges)

## Idee der Anwendung <a name="idee"></a>

- Ein Industrieunternehmen produziert in der Massenfertigung auf vielen Maschinen das selbe Teil
- Nach der Produktion wertet ein Arbeiter/eine Maschine die Teile aus
- Mitarbeiter hat einen Bildschirm mit einem Bild des Teiles, über welches ein Raster (x/y-Koordinaten) gelegt ist
- Mitarbeiter klickt defekte Stelle an
  - optional: Fehlergrund wird mitangegeben

### Skizze

![](docs/skizze.png)

_hier ggf. image der Weboberfläche einfügen_

## Anwendungsszenarien <a name="anwendung"></a>

- Häufige Fehler erkennen
- Zusammenhänge von Fehler erkennen
  - Fehler immer zu bestimmter Uhrzeit / bestimmter Tag
  - Fehler geht von bestimmter Maschine aus
  - Fehler tritt in bestimmtem Werk auf

## Architektur <a name="architektur"></a>

> einzelne Elemente noch genauer beschreiben

![](docs/architektur.png)

#### Load Balancer (Ingress)

-
-

#### Web Server (Node.js)
Der Web Server ist mit Node.js in JavaScript entwickelt. Er verarbeitet alle HTTP Anfragen der Clients und beantwortet diese. Beispielsweise wird entsprechender HTML Code an den Cient übermittelt, um die Website darzustellen.
Hierzu werden verschiedene Funktionen verwendet, um notwendige Daten für die Verarbeitung aus der Datenbank auszulesen oder im Cache zu sichern. Nachfolgend werden die vom Web Server verwendeten Funktionen beschrieben.
- getMachinesFromDatabaseOrCache
  - Liest die Daten aller Maschinen aus der Datenbank aus und speichert diese im Cache. Bei erneuter Verwendung werden die Daten aus dem Cache bezogen.
  - Parameter: -
  - Return Value: Array mit Maschinen Objekten im JSON Format
- getMachineFromDatabaseOrCache
  - Liest die Daten einer spezifischen Maschine aus der Datenbank aus und speichert diese im Cache. Bei erneuter Verwendung werden die Daten (wenn für diese Maschine vorhanden) aus dem Cache bezogen.
  - Parameter: id[int] -> Identifier der Maschine
  - Return Value: Maschinen Objekt im JSON Format
- getFailuresFromDatabaseOrCache
  - Liest die Daten aller Fehler aus der Datenbank aus und speichert diese im Cache. Bei erneuter Verwendung werden die daten aus dem Cache bezogen.
  - Parameter: -
  - Return Value: Array mit Fehler Objekten im JSON Format
- reportFailurePart
  - Sendet eine Tracking Nachricht für einen festgestellten Fehler. Dabei wird dem Fehler ein Zeitstempel vom Server mitgegeben.
  - Parameter: failurePart[JSON] -> Festgestellter Fehler im JSON Format
  - Return Value: -
- getFailurePartStatistic
  - Liest die erfassten Fehler-Statistiken für eine Schicht an einem bestimmten Datum aus.
  - Parameter: shift[int] -> Schicht, date[Date] -> Datum der Fehlererfassung
  - Return Value: Statistik Objekt im JSON Format

#### Cache Server (Memcached)
Hier werden statische Daten aus der Datenbank vom Web Server zwischengepeichert. Dies sind Daten zu den verfügbaren Maschinen und Fehlern.

#### Database Server (MySQL-Datenbank)
Die Datenbank besteht insgesamt aus vier Tabellen. Die einzelnen Felder der Tabllen können der nachfolgenden Abbildung entnommen werden.

![](docs/db_schema1.PNG)

- Maschines
  - Enthält die Daten aller Maschinen des Herstellers für die Fehler erhoben werden können, wie zum Beispiel den Namen der Maschine 
- Failures
  - Enthält die Daten aller Fehler, die potentiell auftreten können
- Fault_Parts
  - Enthält die Daten aller festgestellten Fehler, wie zum Beispiel das Erfassungsdatum oder die Id der Maschine, an welcher der Fehler festgestellt wurde
- Shift_Statistics
  - Enthält aufbereitete Daten, die darstellen, welche Fehler wie oft in welcher Schicht aufgetreten sind

#### Big Data&Science Processing (Spark)

-
-

#### Big Data Messaging (Kafka)

-
-

#### Data Lake (HHDFS)

-
-

## Anwendung
### Verzeichnisstruktur
- materialize -> enthält alle statischen Ressourcen, wie Stylesheets
  - css
  - js 
- views -> enthält alle Templates für dynamische Webseiten Inhalte
###Backend 
- Die Ressourcen im materialize Verzeichnis werden in der index.js (Node.js / Express) per <code>app.use(express.static('public'));</code> öffentlich gemacht
- Die Webseiten werden mit eds-Templates erzeugt

### Frontend <a name="frontend"></a>
Die Benutzeroberfläche der Anwendung wird im Webbrowser dargestellt. Dabei werden grundlegend zwei Funktionalitäten angeboten. Zum einen kann der Nutzer einen spezifischen Fehler dokumentieren, den er an einem von einer bestimmten Maschine erzeugtem Teil festgestellt hat. Des Weiteren kann der Nutzer Statistiken zu bestimmten Fehlern aufrufen.

## Starten der Anwendung <a name="start"></a>

Minikube start

```
minikube start --driver=docker
```

Enable Load Balancer (Ingress)

```
minikube addobs enable ingress
```

A running Strimzi.io Kafka operator

```bash
helm repo add strimzi http://strimzi.io/charts/
helm install my-kafka-operator strimzi/strimzi-kafka-operator
```

A running Hadoop cluster with YARN (for checkpointing)

```bash
helm repo add stable https://charts.helm.sh/stable
helm install --namespace=default --set hdfs.dataNode.replicas=2 --set yarn.nodeManager.replicas=2 --set hdfs.webhdfs.enabled=true my-hadoop-cluster stable/hadoop
```

To develop using [Skaffold](https://skaffold.dev/), use `skaffold dev`.

Webanwendung aufrufen

```
kubectl get ingress
```

liefert die IP-Adresse

## Screencast <a name="screencast"></a>

> Video oder Link zum Video einfügen

## Sonstiges <a name="sonstiges"></a>

> text...
