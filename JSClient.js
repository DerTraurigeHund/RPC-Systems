<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>RPC Browser Client (mit Key-Exchange & Shared Vars)</title>
  <script type="module">
    import sodium from "https://cdn.jsdelivr.net/npm/libsodium-wrappers@0.7.11/dist/modules/libsodium-wrappers.js";

    class RPCClient {
      constructor({ apiKey = null, websocketUrl }) {
        this.apiKey = apiKey;
        this.websocketUrl = websocketUrl;
        this.socket = null;
        this.shared = new SharedProxy(this);
      }

      async init() {
        await sodium.ready;

        // Client Keypair
        const kp = sodium.crypto_box_keypair();
        this.clientPrivateKey = kp.privateKey;
        this.clientPublicKey = kp.publicKey;

        // WebSocket verbinden
        this.socket = new WebSocket(this.websocketUrl);
        this.socket.binaryType = "arraybuffer";

        await new Promise((resolve, reject) => {
          this.socket.onopen = () => resolve();
          this.socket.onerror = reject;
        });

        // Handshake starten
        const clientPubB64 = sodium.to_base64(this.clientPublicKey, sodium.base64_variants.ORIGINAL);
        this.socket.send(JSON.stringify({
          type: "HELLO",
          client_pubkey: clientPubB64
        }));

        // Antwort (Server Public Key)
        const helloAck = await this._recv();
        const reply = JSON.parse(helloAck);
        if (reply.type !== "HELLO_ACK") throw new Error("Handshake fehlgeschlagen");

        this.serverPublicKey = sodium.from_base64(reply.server_pubkey, sodium.base64_variants.ORIGINAL);
        console.log("🔑 Handshake abgeschlossen, Server Public Key empfangen");
      }

      async _recv() {
        return await new Promise((resolve, reject) => {
          const onMessage = (msg) => {
            this.socket.removeEventListener("message", onMessage);
            resolve(msg.data);
          };
          this.socket.addEventListener("message", onMessage);
          this.socket.addEventListener("error", reject, { once: true });
        });
      }

      async call(func, ...args) {
        return await this._sendRPC({ func, args, kwargs: {} });
      }

      async _sendRPC(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
          throw new Error("WebSocket nicht verbunden");
        }

        // optional API-Key hinzufügen
        if (this.apiKey) payload.api_key = this.apiKey;

        const jsonPayload = JSON.stringify(payload);
        const nonce = sodium.randombytes_buf(sodium.crypto_box_NONCEBYTES);

        // Verschlüsseln mit Server-PublicKey
        const cipher = sodium.crypto_box_easy(
          new TextEncoder().encode(jsonPayload),
          nonce,
          this.serverPublicKey,
          this.clientPrivateKey
        );

        const combined = new Uint8Array(nonce.length + cipher.length);
        combined.set(nonce);
        combined.set(cipher, nonce.length);

        const cipherB64 = sodium.to_base64(combined, sodium.base64_variants.ORIGINAL);
        const clientPubB64 = sodium.to_base64(this.clientPublicKey, sodium.base64_variants.ORIGINAL);

        const envelope = {
          type: "RPC",
          client_pubkey: clientPubB64,
          cipher: cipherB64
        };

        this.socket.send(JSON.stringify(envelope));

        // Antwort empfangen
        const replyRaw = await this._recv();
        let replyData;
        try {
          // Base64 dekodieren + entschlüsseln
          const dataBytes = sodium.from_base64(replyRaw, sodium.base64_variants.ORIGINAL);
          const nonceR = dataBytes.slice(0, sodium.crypto_box_NONCEBYTES);
          const ciphertextR = dataBytes.slice(sodium.crypto_box_NONCEBYTES);

          const decrypted = sodium.crypto_box_open_easy(
            ciphertextR,
            nonceR,
            this.serverPublicKey,
            this.clientPrivateKey
          );
          replyData = JSON.parse(new TextDecoder().decode(decrypted));
        } catch (err) {
          // falls unverschlüsselte Antwort (Fehler)
          replyData = JSON.parse(replyRaw);
        }

        if (replyData.status === "ok") {
          return replyData.result;
        } else {
          throw new Error("Serverfehler: " + replyData.error);
        }
      }
    }

    // ------------------------------
    // Shared Variable Proxy
    // ------------------------------
    class SharedProxy {
      constructor(client) {
        this._client = client;
        this._cache = {};
      }

      async set(name, value) {
        this._cache[name] = value;
        try {
          await this._client.call("__update_shared_var__", name, value);
        } catch (e) {
          console.warn("Fehler beim Sync:", e);
        }
      }

      get(name) {
        return this._cache[name];
      }
    }

    // ------------------------------
    // Beispielnutzung
    // ------------------------------
    (async () => {
      const client = new RPCClient({
        apiKey: "abc", // optional
        websocketUrl: "ws://localhost:8421"
      });

      await client.init();

      // öffentliche Funktion ohne Auth
      console.log(await client.call("ping"));

      // auth-pflichtige Funktion
      console.log(await client.call("add", 10, 20));

      // Shared Variablen
      await client.shared.set("zahl", 77);
      console.log("Shared gesetzt:", client.shared.get("zahl"));
    })();
  </script>
</head>
<body class="bg-gray-100 p-4">
  <h2 class="text-xl font-semibold">RPC Browser Client (WebSocket + Key Exchange + Shared)</h2>
  <p>Öffne die Browser-Konsole für die Ausgabe.</p>
</body>
</html>
