
from flask import Flask, render_template, request, session, redirect, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import time

app = Flask(__name__)
app.secret_key = 'secret-key'
socketio = SocketIO(app)

def get_db():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('index.html', login_required=True)
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=? AND password=?', (data['username'], data['password']))
    user = cur.fetchone()
    if user:
        session['username'] = user['username']
        return jsonify(success=True)
    return jsonify(success=False, message='帳號或密碼錯誤')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (data['username'], data['password']))
        conn.commit()
        return jsonify(success=True)
    except sqlite3.IntegrityError:
        return jsonify(success=False, message='帳號已存在')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=?', (data['username'],))
    if cur.fetchone():
        cur.execute('UPDATE users SET password=? WHERE username=?', (data['new_password'], data['username']))
        conn.commit()
        return jsonify(success=True)
    return jsonify(success=False, message='帳號不存在')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@socketio.on('connect')
def connect():
    if 'username' not in session:
        return False
    emit('connected', {'user': session['username']}, broadcast=True)

@socketio.on('send_message')
def handle_send(data):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    emit('message', {
        'user': session['username'],
        'msg': data['msg'],
        'timestamp': timestamp
    }, to=data['room'])

@socketio.on('join_room')
def handle_join(data):
    join_room(data['room'])

if __name__ == '__main__':
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')
    conn.commit()
    socketio.run(app, debug=True)
