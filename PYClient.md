# 🐍 Python Client – Dokumentation

## 📘 Überblick

Der **`RPCClient`** ermöglicht eine **sichere, verschlüsselte Kommunikation** mit einem kompatiblen
`RPCServer`, der Ende-zu-Ende-Verschlüsselung und API-Key-Authentifizierung nutzt.

Unterstützt werden:

* 🔑 **API-Key Authentifizierung**
* 🔒 **Automatischer Public/Private-Key Austausch (Handshake)**
* 🧠 **Shared Variables** (synchron zwischen Client & Server)
* 🧩 **Öffentliche Funktionen (ohne Auth)**
* ⚙️ **ZeroMQ** als Transport

---

## 🚀 Initialisierung

```python
from rpc_client import RPCClient

client = RPCClient(
    api_key="abc",          # oder None, falls nur öffentliche Funktionen genutzt werden
    host="localhost",
    port=8421
)
```

| Parameter | Typ            | Beschreibung                                                     |
| --------- | -------------- | ---------------------------------------------------------------- |
| `api_key` | `str` | `None` | Der API-Key aus der Serverliste `[{"user_id": …, "api_key": …}]` |
| `host`    | `str`          | Serveradresse                                                    |
| `port`    | `int`          | Serverport (Default: 8421)                                       |

---

## 🔐 Handshake (automatisch)

Beim Start verbindet sich der Client mit dem Server und führt **automatisch** einen
**Public-Key-Austausch** durch.
Danach werden **alle Nachrichten verschlüsselt** (NaCl Box, Curve25519 / XSalsa20-Poly1305).

Der Ablauf:

1. Client sendet `HELLO` mit seinem Public Key
2. Server antwortet mit `HELLO_ACK` + Server Public Key
3. Beide Seiten erzeugen ein gemeinsames Secret für alle Nachrichten

---

## ⚙️ Verwendung

### Funktionen aufrufen

Funktionen werden dynamisch durch Attributzugriff aufgerufen:

```python
result = client.add(2, 3)
print(result)  # -> 5
```

### Öffentliche Funktionen (ohne Auth)

```python
print(client.ping())  # z.B. 'pong'
```

### Mit Argumenten und Keyword-Args

```python
result = client.calc_sum(5, 10, mode="fast")
```

---

## 🧠 Shared Variables

Der Client kann Variablen setzen oder abrufen, die auf dem Server gespiegelt werden.

```python
# Variable setzen (synchronisiert mit Server)
client.shared.set("counter", 42)

# Lokalen Wert auslesen
print(client.shared.get("counter"))

# Server liest dieselbe Variable synchron
# server.shared.get("counter") == 42
```

---

## 🔄 Fehlerbehandlung

Fehler werden als `RuntimeError` ausgelöst, wenn der Server eine Fehlermeldung zurückgibt.

```python
try:
    client.divide(1, 0)
except RuntimeError as e:
    print("Serverfehler:", e)
```

---

## 📡 Beispiel

```python
from rpc_client import RPCClient

client = RPCClient(api_key="abc")

print(client.ping())           # öffentliche Funktion
print(client.add(10, 20))      # API-geschützt
client.shared.set("zahl", 77)  # Shared Variable
```

---

## 🧩 Technische Details

| Feature                | Beschreibung                |
| ---------------------- | --------------------------- |
| Transport              | ZeroMQ (REQ-Socket)         |
| Sicherheit             | NaCl Box Encryption         |
| Authentifizierung      | API-Key (User-ID Lookup)    |
| Öffentliche Funktionen | ohne Auth aufrufbar         |
| Shared Vars            | bidirektional synchron      |
| Timeout                | 5 Sekunden (konfigurierbar) |

---

## 📁 Beispielstruktur

```
project/
├─ rpc_server.py
├─ rpc_client.py
└─ run_client.py
```

---

## 💬 Kontext-Variable

Bei Aufrufen, die Authentifizierung erfordern, stellt der Server die aktuelle `user_id` im Funktionskontext bereit.
Das ist für den Client transparent – er muss lediglich den richtigen API-Key nutzen.
