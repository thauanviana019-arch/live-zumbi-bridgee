
import os
import threading
import asyncio
import time

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
def add_cors_headers(response):
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
        "tiktok_connected": connected,
        "message": "Conector da arena"
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
        return jsonify({"comments": list(last_comments[-30:])})


def start_tiktok_listener():
    global connected, connection_error

    if not USERNAME:
        connection_error = "Configure TIKTOK_USERNAME nas variáveis do serviço."
        return

    async def listen():
        global connected, connection_error

        client = TikTokLiveClient(unique_id=USERNAME)

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            global connected

            nickname = str(
                getattr(event.user, "nickname", "Visitante")
            )[:40]

            unique_id = str(
                getattr(event.user, "unique_id", nickname)
            )[:80]

            comment = str(getattr(event, "comment", "")).strip()
            if not comment:
                return

            with lock:
                connected = True
                last_comments.append({
                    "nickname": nickname,
                    "comment": comment,
                    "time": int(time.time())
                })

                if len(last_comments) > 100:
                    del last_comments[:-100]

                if comment.lower() in ("jogar", "!jogar"):
                    if unique_id not in players:
                        players[unique_id] = {
                            "id": unique_id,
                            "nickname": nickname,
                            "joined_at": int(time.time())
                        }

        try:
            await client.start()
        except Exception as exc:
            connection_error = str(exc)[:300]
            connected = False

    asyncio.run(listen())


@app.get("/status")
def status():
    return jsonify({
        "service": "LIVE ZUMBI BRIDGE",
        "username": USERNAME or None,
        "connected": connected,
        "error": connection_error
    })


if __name__ == "__main__":
    threading.Thread(
        target=start_tiktok_listener,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
          )
  
