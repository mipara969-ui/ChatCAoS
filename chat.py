import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caos</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 h-dvh flex flex-col font-sans antialiased">

    <!-- Pantalla de ingreso (solo username) -->
    <div id="login-screen" class="fixed inset-0 bg-zinc-950/95 backdrop-blur-sm flex items-center justify-center p-4 z-50">
        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <div class="flex items-center gap-2 mb-2">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <h1 class="text-xl font-bold tracking-tight">Lo que quieras</h1>
            </div>
            <p class="text-zinc-400 text-sm mb-5">Sin registro, sin historial. Pon tu alias y entra.</p>
            <form id="login-form" class="space-y-4">
                <input id="username-input" type="text" maxlength="20" required autocomplete="off"
                    placeholder="Tu username..."
                    class="w-full bg-zinc-950 border border-zinc-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 transition">
                <button type="submit"
                    class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 rounded-xl text-sm transition cursor-pointer">
                    Entrar al chat
                </button>
            </form>
        </div>
    </div>

    <!-- Header -->
    <header class="bg-zinc-900/80 border-b border-zinc-800 px-4 py-3 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-2.5">
            <span id="status-dot" class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span class="font-semibold text-sm tracking-wide">CHAT PRIVADO</span>
        </div>
        <div class="flex items-center gap-3 text-xs text-zinc-400">
            <span id="my-alias" class="text-emerald-400 font-medium"></span>
            <span class="bg-zinc-800 px-2.5 py-1 rounded-full">
                Online: <strong id="online-count" class="text-zinc-100">0</strong>
            </span>
        </div>
    </header>

    <!-- Área de mensajes -->
    <main id="messages" class="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"></main>

    <!-- Input de mensaje -->
    <footer class="bg-zinc-900 border-t border-zinc-800 p-3 shrink-0">
        <form id="chat-form" class="max-w-4xl mx-auto flex gap-2">
            <input id="msg-input" type="text" maxlength="1000" autocomplete="off" disabled
                placeholder="Escribe lo que sea..."
                class="flex-1 bg-zinc-950 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50">
            <button id="send-btn" type="submit" disabled
                class="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition cursor-pointer">
                Enviar
            </button>
        </form>
    </footer>

    <script>
        let ws;
        let myUsername = "";

        const loginScreen = document.getElementById("login-screen");
        const loginForm = document.getElementById("login-form");
        const usernameInput = document.getElementById("username-input");
        const messagesBox = document.getElementById("messages");
        const chatForm = document.getElementById("chat-form");
        const msgInput = document.getElementById("msg-input");
        const sendBtn = document.getElementById("send-btn");
        const onlineCount = document.getElementById("online-count");
        const statusDot = document.getElementById("status-dot");
        const myAlias = document.getElementById("my-alias");

        function getLocalTime() {
            return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }

        function appendSystemMessage(text) {
            const div = document.createElement("div");
            div.className = "text-center text-xs text-zinc-500 my-1";
            div.textContent = text;
            messagesBox.appendChild(div);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }

        function appendChatMessage(user, text) {
            const isMe = user === myUsername;
            const wrapper = document.createElement("div");
            wrapper.className = `flex flex-col ${isMe ? "items-end" : "items-start"}`;

            const meta = document.createElement("span");
            meta.className = "text-[11px] text-zinc-400 mb-1 px-1";
            meta.textContent = `${isMe ? "Tú" : user} • ${getLocalTime()}`;

            const bubble = document.createElement("div");
            bubble.className = `max-w-[80%] sm:max-w-md px-3.5 py-2 rounded-2xl text-sm break-words ${
                isMe
                    ? "bg-emerald-600 text-white rounded-br-sm"
                    : "bg-zinc-800 text-zinc-100 rounded-bl-sm"
            }`;
            bubble.textContent = text;

            wrapper.appendChild(meta);
            wrapper.appendChild(bubble);
            messagesBox.appendChild(wrapper);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }

        function connect(username) {
            const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
            ws = new WebSocket(`${proto}//${window.location.host}/ws`);

            ws.onopen = () => {
                statusDot.classList.replace("bg-amber-500", "bg-emerald-500");
                statusDot.classList.replace("bg-red-500", "bg-emerald-500");
                msgInput.disabled = false;
                sendBtn.disabled = false;
                msgInput.focus();
                ws.send(JSON.stringify({ type: "join", username }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.online !== undefined) {
                    onlineCount.textContent = data.online;
                }
                if (data.type === "system") {
                    appendSystemMessage(data.text);
                } else if (data.type === "chat") {
                    appendChatMessage(data.user, data.text);
                }
            };

            ws.onclose = () => {
                statusDot.classList.replace("bg-emerald-500", "bg-red-500");
                msgInput.disabled = true;
                sendBtn.disabled = true;
                appendSystemMessage("Desconectado del servidor. Recarga para volver a entrar.");
            };
        }

        loginForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const val = usernameInput.value.trim();
            if (!val) return;
            myUsername = val;
            myAlias.textContent = `@${myUsername}`;
            loginScreen.classList.add("hidden");
            connect(myUsername);
        });

        chatForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const text = msgInput.value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
            ws.send(JSON.stringify({ type: "chat", text }));
            msgInput.value = "";
        });
    </script>
</body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def broadcast(self, payload: dict):
        payload["online"] = len(self.active)
        raw = json.dumps(payload)
        dead = []
        for connection in self.active:
            try:
                await connection.send_text(raw)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active.pop(d, None)

manager = ConnectionManager()

@app.get("/")
async def get_index():
    return HTMLResponse(HTML_PAGE)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = "Anónimo"
    try:
        join_raw = await websocket.receive_text()
        join_data = json.loads(join_raw)
        requested = str(join_data.get("username", "")).strip()[:20]
        if requested:
            # Si el nombre ya existe, le pega un sufijo corto para evitar choques
            existing = set(manager.active.values())
            username = requested if requested not in existing else f"{requested}_{len(existing)+1}"

        manager.active[websocket] = username
        await manager.broadcast({"type": "system", "text": f"{username} entró a la sala"})

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data.get("type") == "chat":
                msg = str(data.get("text", "")).strip()[:1000]
                if msg:
                    await manager.broadcast({
                        "type": "chat",
                        "user": username,
                        "text": msg
                    })
    except WebSocketDisconnect:
        left_user = manager.active.pop(websocket, None)
        if left_user:
            await manager.broadcast({"type": "system", "text": f"{left_user} salió de la sala"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)