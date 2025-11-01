from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.get("/")
def root():
    return "OK", 200

@app.get("/health")
def health():
    return {"status": "up"}, 200

def _run():
    # Render fournit le port via la var d'env PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def start_web():
    Thread(target=_run, daemon=True).start()
