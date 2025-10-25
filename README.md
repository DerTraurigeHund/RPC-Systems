# 🔐 Secure RPC Framework

Ein leichtgewichtiges, aber hochsicheres **Remote Procedure Call (RPC) Framework**,  
geschrieben in **Python** (Server + Client) und **JavaScript (Browser)**,  
mit automatischer **Ende-zu-Ende-Verschlüsselung**, **API-Key-Authentifizierung**  
und **synchronisierten Shared Variables**.

---

## 🚀 Features

| Kategorie | Beschreibung |
|------------|---------------|
| 🔑 **Authentifizierung** | API-Key pro Benutzer (`[{user_id, api_key}]`) |
| 🔒 **Sicherheit** | NaCl Public-Key-Verschlüsselung (Curve25519 + XSalsa20-Poly1305) |
| 🧩 **Transport** | ZeroMQ (Python) & WebSocket (Browser) |
| 🔄 **Shared Variables** | Variablen werden zwischen Client und Server synchronisiert |
| 🌐 **Web-Unterstützung** | JavaScript-Client für Browser mit automatischem Key-Exchange |
| ⚙️ **Threaded Server** | Worker-Pool zur parallelen Ausführung von RPC-Aufrufen |
| 💬 **Public RPCs** | Funktionen können ohne Authentifizierung verfügbar gemacht werden |
| 🧠 **Kontextvariable** | Serverseitig Zugriff auf die User-ID des aufrufenden Clients |

---

## 🧩 Projektstruktur

```

project/
├─ server/
│  ├─ rpc_server.py
│  └─ server.md
│
├─ client_python/
│  ├─ rpc_client.py
│  └─ PYClient.md
│
├─ client_js/
│  ├─ rpc_client.js
│  ├─ index.html
│  └─ JSClient.md
│
└─ README.md  ← (diese Datei)

````

---

## ⚙️ Installation

### 📦 Python Server

```bash
pip install pyzmq pynacl
````

### 💻 Browser Client

```html
<script type="module">
  import sodium from "https://cdn.jsdelivr.net/npm/libsodium-wrappers@0.7.11/dist/modules/libsodium-wrappers.js";
</script>
```

---

## 🔧 Schnellstart

### 1️⃣ Server starten

```python
from rpc_server import RPCServer

api_keys = [{"user_id": 1, "api_key": "abc123"}]
server = RPCServer(api_keys, server_name="MyRPCServer")

def add(a, b): return a + b
def ping(): return "pong"

server.add_external_function(add, "add")               # Auth erforderlich
server.add_external_function(ping, "ping", public=True)  # Öffentlich

server.serve_forever()
```

---

### 2️⃣ Python-Client

```python
from rpc_client import RPCClient

client = RPCClient(api_key="abc123")
print(client.ping())       # -> "pong"
print(client.add(10, 5))   # -> 15

client.shared.set("zahl", 42)
print(client.shared.get("zahl"))  # 42
```

---

### 3️⃣ JavaScript-Client (Browser)

```html
<script type="module">
  import sodium from "https://cdn.jsdelivr.net/npm/libsodium-wrappers@0.7.11/dist/modules/libsodium-wrappers.js";
  import { RPCClient } from "./rpc_client.js";

  const client = new RPCClient({
    apiKey: "abc123",
    websocketUrl: "ws://localhost:8421"
  });

  await client.init();

  console.log(await client.call("ping"));
  console.log(await client.call("add", 3, 4));

  await client.shared.set("score", 99);
  console.log(client.shared.get("score"));
</script>
```

---

## 🔑 Sicherheit

| Mechanismus                | Beschreibung                                       |
| -------------------------- | -------------------------------------------------- |
| **Handshake**              | Automatischer Public-Key-Austausch bei Verbindung  |
| **Verschlüsselung**        | NaCl `crypto_box` (Curve25519 + XSalsa20-Poly1305) |
| **Authentifizierung**      | API-Key-basiert pro Benutzer                       |
| **Öffentliche Funktionen** | explizit markiert mit `public=True`                |
| **Shared Vars**            | werden über sichere RPCs synchronisiert            |

---

## 🧠 Architekturüberblick

```
+-------------------------+      +--------------------------+
|     RPC Client (JS/Py)  | <--> |      RPC Server (Py)     |
|--------------------------|     |--------------------------|
| - Keypair erstellen      |     | - Keypair erstellen      |
| - Handshake via PubKey   |     | - Handshake akzeptieren   |
| - Nachricht verschlüsseln|     | - Nachricht entschlüsseln |
| - Funktionen aufrufen    |     | - Funktionen ausführen    |
| - Shared Vars sync       |     | - Shared Vars speichern   |
+--------------------------+     +--------------------------+
```

---

## 🧠 Shared Variables

Synchronisierte Variablen zwischen Client & Server.
Jede Änderung auf einer Seite wird über RPC übertragen.

| Seite             | Beispielcode                         |
| ----------------- | ------------------------------------ |
| **Python Client** | `client.shared.set("zahl", 7)`       |
| **JS Client**     | `await client.shared.set("zahl", 7)` |
| **Server**        | `server.shared.get("zahl")`          |

---

## 🧩 Öffentliche Funktionen

Funktionen können ohne API-Key aufgerufen werden:

```python
def ping(): return "pong"
server.add_external_function(ping, "ping", public=True)
```

Aufrufbar durch **alle Clients**, auch ohne Authentifizierung.

---

## 🔍 Kontextvariable (`rpc_context`)

Innerhalb registrierter Funktionen steht die User-ID des Aufrufers zur Verfügung:

```python
from rpc_server import rpc_context

def whoami():
    user = rpc_context.get()["user_id"]
    return f"Hallo, User {user}"
```

---

## 🧰 Technische Details

| Komponente        | Technologie                            |
| ----------------- | -------------------------------------- |
| Sprache           | Python 3.10+, JavaScript (ES6+)        |
| Transport         | ZeroMQ (Python) / WebSocket (Browser)  |
| Kryptografie      | libsodium / PyNaCl                     |
| Authentifizierung | API-Key mit User-ID                    |
| Synchronisierung  | Shared-State über RPC                  |
| Multi-Threading   | Worker-Pool über DEALER–ROUTER-Pattern |

---

## 📚 Weiterführende Dokumentation

* 📘 [Server Dokumentation](./server/server.md)
* 🐍 [Python Client Dokumentation](./client_python/PYClient.md)
* 🌐 [JavaScript Client Dokumentation](./client_js/JSClient.md)

---

## 💡 Ideen für zukünftige Erweiterungen

* 🔁 Echtzeit-Updates für Shared Variablen (Push an alle Clients)
* 🧩 Event Hooks (on_connect, on_disconnect, on_call)
* 🔍 Logging & Monitoring Interface
* 🔐 Token Refresh System
* 🌍 WebSocket/HTTP Hybrid Transport
