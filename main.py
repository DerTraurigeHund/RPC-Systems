import zmq
import threading
import json
from concurrent.futures import ThreadPoolExecutor

class RPCServer:
    def __init__(self, password, server_name, host="localhost",
                 port=8421, timeout=5000, workers=4):
        """
        RPC-Server mit ROUTER–DEALER Setup und Worker-Pool.
        """
        self._password = password
        self._server_name = server_name
        self._host = host
        self._port = port
        self._timeout = timeout
        self._functions = {}  # Registrierte externe Funktionen
        self._workers = workers

    def add_external_function(self, func, alias):
        """
        Externe Funktion registrieren.
        alias: Name, unter dem der Client sie aufruft.
        """
        self._functions[alias] = func

    def _worker_routine(self, context):
        """Worker-Thread: empfängt Anfragen, führt Funktionen aus."""
        socket = context.socket(zmq.DEALER)
        socket.connect("inproc://workers")
        while True:
            # Frame 0: Client-ID, Frame 1: leer, Frame 2: Payload
            client_id, empty, payload = socket.recv_multipart()
            try:
                request = json.loads(payload.decode())
                # Security: Passwort prüfen
                if request.get("password") != self._password:
                    raise PermissionError("Ungültiges Passwort")
                func_name = request["func"]
                args = request.get("args", [])
                kwargs = request.get("kwargs", {})
                if func_name not in self._functions:
                    raise NameError(f"Funktion {func_name} nicht gefunden")
                result = self._functions[func_name](*args, **kwargs)
                reply = {"status": "ok", "result": result}
            except Exception as e:
                # Fehler abfangen und an Client zurückgeben
                reply = {"status": "error", "error": str(e)}
            socket.send_multipart([
                client_id, b"", json.dumps(reply).encode()
            ])

    def serve_forever(self):
        """Startet den Server mit Broker und Worker-Pool."""
        context = zmq.Context()
        # Frontend: Clients verbinden sich hier
        frontend = context.socket(zmq.ROUTER)
        frontend.bind(f"tcp://{self._host}:{self._port}")
        # Backend: Worker verbinden sich hier
        backend = context.socket(zmq.DEALER)
        backend.bind("inproc://workers")
        # Worker-Pool starten
        for _ in range(self._workers):
            threading.Thread(
                target=self._worker_routine, args=(context,), daemon=True
            ).start()
        # Broker: leitet zwischen Frontend und Backend weiter
        zmq.proxy(frontend, backend)
        # (wird blockierend ausgeführt)

class RPCClient:
    def __init__(self, password, host="localhost", port=8421):
        """
        Einfacher REQ-Client zur Verbindung mit unserem Server.
        """
        self._password = password
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.connect(f"tcp://{host}:{port}")

    def __getattr__(self, name):
        """
        Fängt Aufrufe wie client.irgendwas() ab und sendet sie per JSON.
        """
        def remote_call(*args, **kwargs):
            request = {
                "password": self._password,
                "func": name,
                "args": args,
                "kwargs": kwargs
            }
            self._socket.send(json.dumps(request).encode())
            if self._socket.poll(5000) == 0:
                raise TimeoutError("Keine Antwort vom Server")
            reply = json.loads(self._socket.recv().decode())
            if reply["status"] == "ok":
                return reply["result"]
            else:
                raise RuntimeError(f"Server-Fehler: {reply['error']}")
        return remote_call
