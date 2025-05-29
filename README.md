# RPC-System mit ZeroMQ

Diese Dokumentation beschreibt die Einrichtung und Nutzung eines skalierbaren RPC-Systems auf Basis von ZeroMQ (pyzmq) im Request–Reply-Modus mit einem ROUTER–DEALER-Broker und Worker-Pool.

## Inhalt

1. [Einführung](#einf%C3%BChrung)
2. [Architektur](#architektur)
3. [Voraussetzungen](#voraussetzungen)
4. [Installation](#installation)
5. [Konfiguration](#konfiguration)
6. [Server](#server)

   * [Aufbau](#aufbau)
   * [Beispiel ](#beispiel-serverpy)[`server.py`](#beispiel-serverpy)
7. [Client](#client)

   * [Aufbau](#aufbau-1)
   * [Beispiel ](#beispiel-clientpy)[`client.py`](#beispiel-clientpy)
8. [Sicherheit](#sicherheit)
9. [Tipps zur Produktion](#tipps-zur-produktion)
10. [Fehlerbehandlung](#fehlerbehandlung)
11. [Lizenz](#lizenz)

---

## Einführung

Dieses Dokument erklärt, wie du einen RPC-Server und -Client in Python mit ZeroMQ (pyzmq) erstellst. Ziel ist eine niedrige Latenz, horizontale Skalierbarkeit und einfache Erweiterbarkeit ohne `asyncio` und ohne gRPC.

## Architektur

* **Broker** (ROUTER–DEALER): Leitet Nachrichten zwischen Clients und Arbeitern weiter.
* **Worker-Pool**: Führen Anfragen parallel in Threads aus.
* **REQ-Client**: Sendet synchrone Anfragen an den Server.

## Voraussetzungen

* Python 3.7+
* Paket `pyzmq`
* Grundkenntnisse in Python und Netzwerk-Programmierung

## Installation

```bash
pip install pyzmq
```

## Konfiguration

* Standard-Host: `localhost`
* Standard-Port: `8421`
* Timeout: `5000` ms
* Worker-Anzahl: `4` (anpassbar)

Parameter werden beim Instanziieren der Klassen übergeben.

## Server

### Aufbau

Die Klasse `RPCServer` bietet:

* Initialisierung mit Pflicht- und optionalen Parametern
* Registrierung externer Funktionen unter Aliases
* Start des Brokers und Worker-Pools

**Konstruktor**:

```python
RPCServer(
    password: str,
    server_name: str,
    host: str = "localhost",
    port: int = 8421,
    timeout: int = 5000,
    workers: int = 4
)
```

**Methoden**:

* `add_external_function(func: Callable, alias: str)`: Registriert eine Funktion.
* `serve_forever()`: Startet Broker und Worker-Threads.

### Beispiel `server.py`

```python
import time
from rpc import RPCServer

# Beispiel-Funktionen
def add(a, b):
    """Addiert zwei Zahlen."""
    return a + b

def slow_multiply(a, b):
    """Multipliziert mit Verzögerung."""
    time.sleep(1)
    return a * b

if __name__ == "__main__":
    server = RPCServer(
        password="geheim",
        server_name="Rechner1",
        host="localhost",
        port=8421,
        timeout=5000,
        workers=4
    )

    server.add_external_function(add, "add")
    server.add_external_function(slow_multiply, "mul")

    print("Starte RPC-Server auf tcp://localhost:8421 …")
    server.serve_forever()
```

## Client

### Aufbau

Die Klasse `RPCClient` ermöglicht synchrone RPC-Aufrufe über Methoden-Dynamik.

**Konstruktor**:

```python
RPCClient(
    password: str,
    host: str = "localhost",
    port: int = 8421
)
```

**Dynamisches Attribut**:

* `__getattr__` erstellt eine Proxy-Methode, die JSON-Nachrichten sendet.

### Beispiel `client.py`

```python
from rpc import RPCClient

if __name__ == "__main__":
    client = RPCClient(
        password="geheim",
        host="localhost",
        port=8421
    )

    try:
        result_add = client.add(5, 7)
        print(f"5 + 7 = {result_add}")

        result_mul = client.mul(3, 4)
        print(f"3 * 4 = {result_mul}")

    except Exception as e:
        print(f"Fehler beim RPC-Aufruf: {e}")
```

## Sicherheit

* Passwort-Abfrage auf Serverseite
* Transport derzeit unverschlüsselt: **Empfehlung**: ØMQ CURVE (CurveZMQ) aktivieren
* Tipp: Umgebungsvariablen oder `.env`-Datei für sensible Daten

## Tipps zur Produktion

* **Logging** mit `logging`-Modul
* **Health-Check** (`ping()`-Funktion)
* **Retries** und Backoff auf Client-Seite
* **Prozess- oder Cluster-Modus** zur Skalierung über mehrere Maschinen

## Fehlerbehandlung

* Timeout-Fehler: `TimeoutError`
* Funktionsfehler: `RuntimeError` mit Server-Fehlermeldung
* Ungültige Funktion: `NameError`
* Ungültiges Passwort: `PermissionError`
