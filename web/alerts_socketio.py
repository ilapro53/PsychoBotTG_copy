from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os
import pickle
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

CACHE_FILE = os.path.join(os.path.dirname(__file__), '../bot/cache/history_cache.pkl')

last_alerts = set()

def load_alerts():
    alerts = []
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            for user_id, history in data.items():
                for entry in history:
                    if entry["role"] == "user":
                        text = entry["content"].lower()
                        if any(x in text for x in ["суицид", "убийство", "наркотики", "самоубийство", "убить", "покончить с собой", "смерть"]):
                            alerts.append((str(user_id), entry["content"]))
    return alerts

@app.route("/")
def index():
    return render_template("index.html")

def alert_watcher():
    global last_alerts
    while True:
        current = set(load_alerts())
        new_alerts = current - last_alerts
        for user_id, message in new_alerts:
            socketio.emit("new_alert", {"user_id": user_id, "message": message})
        last_alerts = current
        time.sleep(3)

@socketio.on("connect")
def handle_connect():
    print("Client connected")

if __name__ == '__main__':
    threading.Thread(target=alert_watcher, daemon=True).start()
    socketio.run(app, debug=True, port=5001)
