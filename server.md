## ⚙️ Überblick

Der `RPCServer` ist ein **Ende-zu-Ende verschlüsselter Remote Procedure Call Server**,
der sowohl **ZeroMQ (ZMQ)** als auch optional **WebSocket**-Verbindungen unterstützt.

Er erlaubt:

* sichere Kommunikation mit **NaCl Public/Private-Key-Verschlüsselung**
* **automatischen Schlüsselaustausch** beim Verbindungsaufbau
* Authentifizierung über **API-Keys mit User-IDs**
* **öffentliche (nicht authentifizierte)** Funktionen
* **Shared Variables**, die zwischen Client und Server synchronisiert sind

---

## 🚀 Architekturüberblick

```
+----------------------+        +-----------------------+
|      RPC Client      |        |       RPC Server      |
|----------------------|        |-----------------------|
| - erzeugt Keypair    | <----> | - generiert Keypair   |
| - sendet HELLO       |        | - antwortet HELLO_ACK |
| - verschlüsselt Daten|        | - entschlüsselt Daten |
| - ruft Funktionen auf|        | - führt RPC-Funktion  |
| - shared vars        | <----> | - shared state global |
+----------------------+        +-----------------------+
```

### Kommunikationsschritte

1. 🔑 **Handshake**:
   Client sendet `HELLO` → Server antwortet mit `HELLO_ACK` (enthält Public Key)
2. 🔒 **Verschlüsselte RPCs**:
   Danach wird jede Nachricht mit `crypto_box_easy()` verschlüsselt.
3. ✅ **Authentifizierung (optional)**:
   Wenn die Funktion nicht als „public“ markiert ist, muss der Client einen gültigen API-Key senden.
4. 🔄 **Shared State**:
   Client kann Shared Variablen setzen; diese werden serverseitig gespeichert.

---

## 🧩 Klassenübersicht

### `RPCServer`

Der zentrale Server, der RPC-Anfragen entgegennimmt und verschlüsselt verarbeitet.

#### Initialisierung

```python
server = RPCServer(
    api_keys=[{"user_id": 1, "api_key": "abc123"}],
    server_name="MyServer",
    host="localhost",
    port=8421,
    timeout=5000,
    workers=4,
    use_websocket=False
)
```

| Parameter       | Typ          | Beschreibung                                                              |
| --------------- | ------------ | ------------------------------------------------------------------------- |
| `api_keys`      | `list[dict]` | Liste der erlaubten Clients. Format: `[{"user_id": 1, "api_key": "abc"}]` |
| `server_name`   | `str`        | Anzeigename des Servers                                                   |
| `host`          | `str`        | Host-Adresse                                                              |
| `port`          | `int`        | Portnummer                                                                |
| `timeout`       | `int`        | Timeout für Anfragen                                                      |
| `workers`       | `int`        | Anzahl paralleler Worker-Threads                                          |
| `use_websocket` | `bool`       | (optional) WebSocket-Modus statt ZMQ                                      |

---

### 🔧 Methoden

#### `add_external_function(func, alias, public=False)`

Registriert eine externe Funktion, die der Client aufrufen kann.

| Parameter | Typ        | Beschreibung                                                    |
| --------- | ---------- | --------------------------------------------------------------- |
| `func`    | `callable` | Die Python-Funktion                                             |
| `alias`   | `str`      | Der Funktionsname, unter dem sie aufgerufen wird                |
| `public`  | `bool`     | Wenn `True`, ist die Funktion ohne Authentifizierung erreichbar |

**Beispiel:**

```python
def add(a, b): return a + b
def ping(): return "pong"

server.add_external_function(add, "add")         # nur mit API-Key
server.add_external_function(ping, "ping", public=True)  # ohne Auth
```

---

#### `serve_forever()`

Startet den Server und blockiert den Hauptthread.
Eröffnet ZeroMQ-Sockets (`ROUTER` + `DEALER`) und startet Worker-Threads.

**Beispiel:**

```python
server.serve_forever()
```

---

### 🔐 Sicherheit & Authentifizierung

#### Handshake-Prozess

1. Client sendet:

   ```json
   {"type": "HELLO", "client_pubkey": "<Base64>"}
   ```
2. Server antwortet:

   ```json
   {"type": "HELLO_ACK", "server_pubkey": "<Base64>"}
   ```

Danach wird eine **sichere Box** aufgebaut:

```python
box = Box(server_private_key, client_public_key)
```

#### API-Key-Prüfung

Nur Funktionen, die **nicht** als `public=True` registriert wurden,
benötigen einen gültigen `api_key`.

Der Key wird mit der beim Server hinterlegten Liste verglichen:

```python
[{"user_id": 1, "api_key": "abc"}]
```

Bei Erfolg steht die User-ID während des Aufrufs im globalen Kontext:

```python
from rpc_server import rpc_context

def whoami():
    return rpc_context.get()["user_id"]
```

---

### 🧠 Shared Variables

Server und Clients teilen Variablen im gemeinsamen Zustand (`server.shared`).

#### Beispiel

```python
# Client setzt:
client.shared.zahl = 5

# Server sieht:
print(server.shared.get("zahl"))  # -> 5

# Server setzt:
server.shared.set("status", "OK")
```

Intern werden Updates über eine RPC-Funktion `__update_shared_var__` synchronisiert.

---

### 🔧 Interner Ablauf (ZeroMQ-Variante)

| Phase                   | Beschreibung                                       |
| ----------------------- | -------------------------------------------------- |
| **Router-Frontend**     | nimmt Client-Verbindungen entgegen                 |
| **Dealer-Backend**      | verteilt Arbeit an Worker-Threads                  |
| **Worker-Routine**      | entschlüsselt, authentifiziert, führt Funktion aus |
| **Box-Verschlüsselung** | Nachrichten mit `nacl.public.Box` geschützt        |
| **SharedState**         | hält globale Werte synchron über alle Threads      |

---

### 📤 Logging & Fehlerbehandlung

Alle Fehler werden als strukturierte JSON-Fehlerantwort an den Client gesendet:

```json
{"status": "error", "error": "Ungültiger API-Key"}
```

---

## 🧪 Beispiel-Komplettsystem

```python
from rpc_server import RPCServer, rpc_context
import threading

# API-Keys definieren
api_keys = [{"user_id": 1, "api_key": "abc"}]

# Server erstellen
server = RPCServer(api_keys, "TestServer")

# Funktionen registrieren
def add(a, b): return a + b
def ping(): return "pong"
def whoami(): return f"Ich bin User {rpc_context.get()['user_id']}"

server.add_external_function(add, "add")
server.add_external_function(ping, "ping", public=True)
server.add_external_function(whoami, "whoami")

# Server starten (im Hintergrund)
threading.Thread(target=server.serve_forever, daemon=True).start()

print("Server läuft...")
```

---

## 🔗 Integration mit dem JavaScript-Client

Der Browser-Client (`client.html`):

* führt denselben Handshake aus,
* verschlüsselt alle Nachrichten mit `libsodium`,
* ruft Funktionen über `call("funktionsname", args)` auf,
* synchronisiert Shared Variablen mit `client.shared.set("x", 42)`.

---

## 🧩 Kontextvariablen

Der aktuelle Nutzerkontext wird pro RPC-Aufruf in einem **thread-sicheren ContextVar** gespeichert:

```python
from rpc_server import rpc_context

def whoami():
    user = rpc_context.get()["user_id"]
    return f"User-ID: {user}"
```

Dies funktioniert auch, wenn mehrere Clients gleichzeitig verbunden sind.

---

## 🔒 Verschlüsselungsdetails

| Komponente    | Beschreibung                                                   |
| ------------- | -------------------------------------------------------------- |
| Algorithmus   | NaCl (libsodium) `crypto_box` (Curve25519 + XSalsa20-Poly1305) |
| Key-Austausch | Public/Private über Base64                                     |
| Sicherheit    | Authenticated Encryption (MAC-verifiziert)                     |
| Transport     | ZeroMQ oder WebSocket                                          |

---

## 🧩 Erweiterbar für die Zukunft

Der Server ist vorbereitet auf:

* 🔁 Echtzeit-Broadcast von Shared-Variable-Änderungen an alle Clients
* 🌍 WebSocket-Unterstützung für Browser-Clients
* 🧩 Plug-in-System (z. B. für automatisches RPC-Discovery oder Event Hooks)
* 🪶 Logging / Monitoring / Auditing

---

## 📚 Zusammenfassung

| Feature                   | Beschreibung                         |
| ------------------------- | ------------------------------------ |
| 🔐 **Verschlüsselung**    | Public-Key (NaCl Box) – Ende-zu-Ende |
| 🔑 **Authentifizierung**  | API-Key pro User                     |
| 🧩 **Public RPCs**        | Aufrufbar ohne Authentifizierung     |
| 🧠 **Shared Variables**   | Synchron zwischen Server & Clients   |
| ⚙️ **ContextVar**         | Zugriff auf aktuelle User-ID in RPCs |
| 🧵 **Multithreading**     | Worker-Thread-Pool via ZeroMQ        |
| 🔄 **Handshake**          | Automatisch bei Verbindungsaufbau    |
| 💻 **Browser-kompatibel** | WebSocket + JS-Client verfügbar      |
