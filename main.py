
import os
import time
import asyncio
import threading
import traceback

from flask import Flask, jsonify
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent

app = Flask(__name__)

USERNAME = os.getenv("TIKTOK_USERNAME", "").strip().lstrip("@")

players = {}
last_comments = []
connected = False
connection_error = None
lock = threading.Lock()


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.get("/")
def home():
    return jsonify({
        "service": "LIVE ZUMBI BRIDGE",
        "status": "online",
        "tiktok_username_configured": bool(USERNAME),
        "tiktok_connected": connected
    })


@app.get("/status")
def status():
    with lock:
        return jsonify({
            "service": "LIVE ZUMBI BRIDGE",
            "username": USERNAME or None,
            "connected": connected,
            "error": connection_error
        })


@app.get("/players")
def get_players():
    with lock:
        return jsonify({
            "players": list(players.values()),
            "count": len(players)
        })


@app.get("/comments")
def get_comments():
    with lock:
        return jsonify({"comments": last_comments[-30:]})


def start_tiktok_listener():
    global connected, connection_error

    if not USERNAME:
        with lock:
            connection_error = "TIKTOK_USERNAME não foi configurado."
        print("ERRO: TIKTOK_USERNAME não foi configurado.", flush=True)
        return

    async def listen():
        global connected, connection_error

        print(
            f"Iniciando conexão com a LIVE pública: @{USERNAME}",
            flush=True
        )

        try:
            client = TikTokLiveClient(unique_id=USERNAME)

            @client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                global connected

                nickname = str(
                    getattr(event.user, "nickname", "Visitante")
                )[:40]

                user_id = str(
                    getattr(event.user, "unique_id", nickname)
                )[:80]

                comment = str(
                    getattr(event, "comment", "")
                ).strip()

                with lock:
                    connected = True
                    connection_error = None

                    last_comments.append({
                        "nickname": nickname,
                        "comment": comment,
                        "time": int(time.time())
                    })

                    del last_comments[:-100]

                    if comment.lower() in ("jogar", "!jogar"):
                        if user_id not in players:
                            players[user_id] = {
                                "id": user_id,
                                "nickname": nickname,
                                "joined_at": int(time.time())
                            }
                            print(
                                f"Participante entrou: {nickname}",
                                flush=True
                            )

            await client.start()

        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"

            with lock:
                connected = False
                connection_error = message

            print(f"ERRO NA CONEXÃO TIKTOK: {message}", flush=True)
            traceback.print_exc()

    asyncio.run(listen())


if __name__ == "__main__":
    threading.Thread(
        target=start_tiktok_listener,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )
