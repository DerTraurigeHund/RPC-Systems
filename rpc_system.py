import zmq
import threading
import json
from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import Base64Encoder
import contextvars

# ------------------------------
# Kontext für aktuellen Nutzer
# ------------------------------
rpc_context = contextvars.ContextVar("rpc_context", default={"user_id": None})


# ------------------------------
# Shared State
# ------------------------------
class SharedState:
    def __init__(self):
        self._vars = {}

    def set(self, key, value):
        self._vars[key] = value

    def get(self, key, default=None):
        return self._vars.get(key, default)

    def all(self):
        return dict(self._vars)


# ------------------------------
# RPC SERVER
# ------------------------------
class RPCServer:
    def __init__(self, api_keys, server_name, host="localhost", port=8421,
                 timeout=5000, workers=4, use_websocket=False):
        self._api_keys = {entry["api_key"]: entry["user_id"] for entry in api_keys}
        self._server_name = server_name
        self._host = host
        self._port = port
        self._timeout = timeout
        self._functions = {}
        self._public_functions = set()  # auth-freie Funktionen
        self._workers = workers
        self._use_websocket = use_websocket

        self._private_key = PrivateKey.generate()
        self._public_key = self._private_key.public_key

        self.shared = SharedState()

        self.add_external_function(self._update_shared_var, "__update_shared_var__")
        self.add_external_function(self._get_public_key, "__get_public_key__", public=True)

    def add_external_function(self, func, alias, public=False):
        self._functions[alias] = func
        if public:
            self._public_functions.add(alias)

    def _get_public_key(self):
        """Wird beim Handshake aufgerufen, um den Public Key zu bekommen."""
        return self._public_key.encode(encoder=Base64Encoder).decode()

    def _authenticate(self, request):
        key = request.get("api_key")
        if key not in self._api_keys:
            raise PermissionError("Ungültiger API-Key")
        return self._api_keys[key]

    def _handle_request(self, request, client_public_key):
        func_name = request["func"]
        args = request.get("args", [])
        kwargs = request.get("kwargs", {})

        if func_name not in self._functions:
            raise NameError(f"Funktion {func_name} nicht gefunden")

        # 🔒 Public-Funktion darf ohne Auth
        if func_name not in self._public_functions:
            user_id = self._authenticate(request)
        else:
            user_id = None

        token = rpc_context.set({"user_id": user_id})
        try:
            result = self._functions[func_name](*args, **kwargs)
        finally:
            rpc_context.reset(token)

        return {"status": "ok", "result": result}

    def _update_shared_var(self, key, value):
        self.shared.set(key, value)
        return True

    def _worker_routine(self, context):
        socket = context.socket(zmq.DEALER)
        socket.connect("inproc://workers")

        while True:
            client_id, empty, payload = socket.recv_multipart()

            try:
                request = json.loads(payload.decode())

                # --- Handshake ---
                if request.get("type") == "HELLO":
                    client_pubkey_b64 = request["client_pubkey"]
                    client_pubkey = PublicKey(client_pubkey_b64, encoder=Base64Encoder)
                    reply = {
                        "type": "HELLO_ACK",
                        "server_pubkey": self._public_key.encode(encoder=Base64Encoder).decode()
                    }
                    socket.send_multipart([client_id, b"", json.dumps(reply).encode()])
                    continue

                # --- Encrypted Message ---
                ciphertext_b64 = request["cipher"]
                client_pubkey_b64 = request["client_pubkey"]
                client_pubkey = PublicKey(client_pubkey_b64, encoder=Base64Encoder)

                box = Box(self._private_key, client_pubkey)
                plaintext = box.decrypt(ciphertext_b64.encode(), encoder=Base64Encoder)
                msg = json.loads(plaintext.decode())

                reply_data = self._handle_request(msg, client_pubkey)
                reply_json = json.dumps(reply_data).encode()
                reply_cipher = box.encrypt(reply_json, encoder=Base64Encoder).decode()

                socket.send_multipart([client_id, b"", reply_cipher.encode()])

            except Exception as e:
                err = {"status": "error", "error": str(e)}
                socket.send_multipart([client_id, b"", json.dumps(err).encode()])

    def _serve_zmq(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind(f"tcp://{self._host}:{self._port}")

        backend = context.socket(zmq.DEALER)
        backend.bind("inproc://workers")

        for _ in range(self._workers):
            threading.Thread(target=self._worker_routine, args=(context,), daemon=True).start()

        zmq.proxy(frontend, backend)

    def serve_forever(self):
        print(f"🔑 Server gestartet ({self._server_name}) auf tcp://{self._host}:{self._port}")
        self._serve_zmq()


# ------------------------------
# RPC CLIENT
# ------------------------------
class RPCClient:
    def __init__(self, api_key=None, host="localhost", port=8421):
        self._api_key = api_key
        self._host = host
        self._port = port
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.connect(f"tcp://{host}:{port}")

        # --- Keypair & Handshake ---
        self._private_key = PrivateKey.generate()
        self._public_key = self._private_key.public_key
        self._server_public_key = None
        self._handshake()

        self.shared = SharedProxy(self)

    def _handshake(self):
        """Schickt HELLO mit eigenem Public Key und empfängt Server-Key."""
        hello = {
            "type": "HELLO",
            "client_pubkey": self._public_key.encode(encoder=Base64Encoder).decode()
        }
        self._socket.send(json.dumps(hello).encode())
        reply = json.loads(self._socket.recv().decode())
        if reply.get("type") != "HELLO_ACK":
            raise ConnectionError("Handshake fehlgeschlagen")
        self._server_public_key = PublicKey(reply["server_pubkey"], encoder=Base64Encoder)

    def __getattr__(self, name):
        def remote_call(*args, **kwargs):
            request = {
                "api_key": self._api_key,
                "func": name,
                "args": args,
                "kwargs": kwargs
            }

            box = Box(self._private_key, self._server_public_key)
            cipher = box.encrypt(json.dumps(request).encode(), encoder=Base64Encoder).decode()

            envelope = {
                "type": "RPC",
                "client_pubkey": self._public_key.encode(encoder=Base64Encoder).decode(),
                "cipher": cipher
            }

            self._socket.send(json.dumps(envelope).encode())
            reply_raw = self._socket.recv()
            try:
                # Versuch zu entschlüsseln (normaler Reply)
                plaintext = box.decrypt(reply_raw, encoder=Base64Encoder)
                reply = json.loads(plaintext.decode())
            except Exception:
                # Oder JSON (Fehlerfall)
                reply = json.loads(reply_raw.decode())

            if reply["status"] == "ok":
                return reply["result"]
            else:
                raise RuntimeError(f"Server-Fehler: {reply['error']}")
        return remote_call


# ------------------------------
# Shared Proxy (Client)
# ------------------------------
class SharedProxy:
    def __init__(self, client):
        self._client = client
        self._cache = {}

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._cache[name] = value
            try:
                self._client.__getattr__("__update_shared_var__")(name, value)
            except Exception as e:
                print(f"Fehler beim Sync {name}: {e}")

    def __getattr__(self, name):
        if name in self._cache:
            return self._cache[name]
        raise AttributeError(f"Variable '{name}' nicht gefunden")
