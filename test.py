from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)

# 不指定 async_mode，讓 SocketIO 自動選擇
socketio = SocketIO(app)

print(f"選擇的 async_mode: {socketio.async_mode}")
