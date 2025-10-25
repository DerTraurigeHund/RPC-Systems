# 🌐 JavaScript Client – Dokumentation

## 📘 Überblick

Der **Browser-fähige JS-Client** erlaubt es, direkt aus dem Webbrowser verschlüsselte RPC-Aufrufe
an den Python-Server zu senden – über **WebSockets** und **libsodium** (NaCl)-Verschlüsselung.

Funktionen können:

* 🔐 mit API-Key (geschützt)
* 🔓 oder öffentlich (ohne Auth)
  aufgerufen werden.

Er unterstützt außerdem:

* 🧠 Shared Variables (Client ↔ Server synchron)
* 🔑 automatischen Key-Handshake

---

## 🚀 Einbindung

```html
<script type="module">
  import sodium from "https://cdn.jsdelivr.net/npm/libsodium-wrappers@0.7.11/dist/modules/libsodium-wrappers.js";
</script>
```

---

## 🔧 Initialisierung

```js
const client = new RPCClient({
  apiKey: "abc",               // optional
  websocketUrl: "ws://localhost:8421"
});

await client.init();
```

| Parameter      | Typ       | Beschreibung                      |
| -------------- | --------- | --------------------------------- |
| `apiKey`       | `string?` | API-Key (falls Auth erforderlich) |
| `websocketUrl` | `string`  | Serveradresse im WebSocket-Format |

---

## 🔐 Handshake

Beim `init()`-Aufruf:

1. generiert der Client ein Keypair (Curve25519)
2. sendet seinen Public Key (`HELLO`)
3. erhält vom Server den Public Key (`HELLO_ACK`)
4. ab diesem Punkt werden alle Nachrichten mit `crypto_box_easy()` verschlüsselt

Der Prozess ist **vollautomatisch** und transparent.

---

## ⚙️ RPC-Aufrufe

### Öffentliche Funktion:

```js
const pong = await client.call("ping");
console.log(pong);  // -> "pong"
```

### Authentifizierte Funktion:

```js
const result = await client.call("add", 5, 8);
console.log(result); // -> 13
```

### Mit Keyword-Argumenten (optional):

```js
await client.call("calc", 10, 20, {mode: "fast"});
```

---

## 🧠 Shared Variables

Alle Werte werden lokal gecached und beim Setzen sofort an den Server synchronisiert:

```js
// setzen
await client.shared.set("zahl", 99);

// auslesen
console.log(client.shared.get("zahl")); // 99

// synchronisiert mit Server.shared["zahl"]
```

---

## ⚡ Fehlermanagement

Wenn der Server einen Fehler zurücksendet, wird dieser als JS-`Error` ausgelöst:

```js
try {
  await client.call("divide", 5, 0);
} catch (err) {
  console.error("Serverfehler:", err.message);
}
```

---

## 📡 Vollständiges Beispiel

```html
<script type="module">
  import sodium from "https://cdn.jsdelivr.net/npm/libsodium-wrappers@0.7.11/dist/modules/libsodium-wrappers.js";

  const client = new RPCClient({
    apiKey: "abc",
    websocketUrl: "ws://localhost:8421"
  });

  await client.init();

  console.log(await client.call("ping"));
  console.log(await client.call("add", 10, 15));

  await client.shared.set("counter", 5);
  console.log("Counter:", client.shared.get("counter"));
</script>
```

---

## 🧩 Technische Details

| Feature      | Beschreibung                       |
| ------------ | ---------------------------------- |
| Transport    | WebSocket (binary / JSON)          |
| Encryption   | libsodium `crypto_box_easy()`      |
| Handshake    | automatischer Public-Key-Austausch |
| Auth         | optional via API-Key               |
| Shared Vars  | synchronisiert                     |
| Dependencies | `libsodium-wrappers`               |

---

## 🧠 Architektur

```
+-----------------+        +--------------------+
| JS RPC Client   | <----> | Python RPC Server  |
|-----------------|        |--------------------|
| WebSocket       |        | asyncio/ws / ZMQ   |
| crypto_box      |        | NaCl Box           |
| SharedProxy     |        | SharedState        |
+-----------------+        +--------------------+
```

---

## 🧩 Erweiterbar

Der JS-Client ist so gestaltet, dass du ihn leicht erweitern kannst, z. B.:

* Realtime-Sync aller Shared-Variablen (Server → Clients)
* Event-Listener für Änderungen
* lokale Cache-Persistenz (IndexedDB / LocalStorage)

---

## 🧩 API Zusammenfassung

| Methode                   | Beschreibung                                    |
| ------------------------- | ----------------------------------------------- |
| `init()`                  | Verbindet sich mit Server & führt Handshake aus |
| `call(name, ...args)`     | Ruft eine RPC-Funktion auf                      |
| `shared.set(name, value)` | Setzt synchronisierte Variable                  |
| `shared.get(name)`        | Gibt letzten bekannten Wert zurück              |

---

## 📁 Beispiel-Projektstruktur

```
webclient/
├─ index.html
├─ rpc_client.js
└─ libsodium-wrappers.js (CDN)
```

---

## 🔒 Sicherheit

| Aspekt       | Beschreibung                         |
| ------------ | ------------------------------------ |
| Algorithmus  | Curve25519 + XSalsa20 + Poly1305     |
| Schutz       | Authenticated Encryption             |
| Key Exchange | automatisch beim Verbindungsaufbau   |
| API-Key      | optionaler Token für geschützte RPCs |

---

## ✅ Kompatibilität

| Client       | Transport | Kompatibel mit              |
| ------------ | --------- | --------------------------- |
| Python       | ZeroMQ    | RPCServer                   |
| JS (Browser) | WebSocket | RPCServer (WebSocket-Modus) |
