from flask import Flask, render_template, request, session, redirect, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

online_users = set()

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    
# 訊息模型
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100))
    username = db.Column(db.String(100))
    msg = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.now())

@app.route('/')
def index():
    if "username" not in session:
        return redirect("/login")
    return render_template("index.html", username=session["username"], login_required=False)

@app.route('/login', methods=['GET'])
def login_page():
    if "username" in session:
        return redirect("/")
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=? AND password=?', (data['username'], data['password']))
    user = cur.fetchone()
    if user:
        session['username'] = data['username']
        return jsonify(success=True)
    return jsonify(success=False, message='帳號或密碼錯誤')

@app.route('/register', methods=['GET'])
def register_page():
    if "username" in session:
        return redirect("/")
    return render_template("register.html")

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = db.engine.raw_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (data['username'], data['password']))
        conn.commit()
        return jsonify(success=True)
    except Exception:
        return jsonify(success=False, message='帳號已存在')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    conn = db.engine.raw_connection()
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

@app.route('/get_rooms')
def get_rooms():
    # 從資料庫中讀取聊天室名稱
    rooms = Room.query.all()
    room_names = [room.name for room in rooms]
    return {'rooms': room_names}

@app.route('/delete_room', methods=['POST'])
def delete_room():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify(success=False, message='聊天室名稱缺失')

    # 確認聊天室是否存在
    room = Room.query.filter_by(name=name).first()
    if not room:
        return jsonify(success=False, message='聊天室不存在')

    # 刪除聊天室相關訊息
    Message.query.filter_by(room=name).delete()
    db.session.delete(room)
    db.session.commit()

    return jsonify(success=True)

@socketio.on('connect')
def connect():
    if 'username' not in session:
        return False
    emit('connected', {'user': session['username']}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username and username in online_users:
        online_users.remove(username)
        emit('update_users', list(online_users), broadcast=True)

@socketio.on('login')
def handle_login(data):
    username = data['username']
    session['username'] = username
    online_users.add(username)
    emit('update_users', list(online_users), broadcast=True)

@socketio.on('create_group')
def handle_create_group(data):
    room_name = data['name']
    
    # 檢查聊天室是否已經存在
    existing_room = Room.query.filter_by(name=room_name).first()
    print(existing_room)
    if existing_room:
        return  # 如果聊天室已經存在，則不再創建
    
    # 儲存聊天室至資料庫
    new_room = Room(name=room_name)
    db.session.add(new_room)
    db.session.commit()
    
    # 廣播聊天室創建事件
    emit('group_created', {'name': room_name}, broadcast=True)

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    messages = Message.query.filter_by(room=room).order_by(Message.timestamp).all()
    for m in messages:
        emit('message', {
            'user': m.username,
            'msg': m.msg,
            'room': m.room,
            'timestamp': m.timestamp.strftime('%H:%M')
        })
    emit('joined', {'room': room})

@socketio.on('send_message')
def handle_send(data):
    room = data['room']
    msg = data['msg']
    username = session['username']
    m = Message(room=room, username=username, msg=msg)
    db.session.add(m)
    db.session.commit()
    emit('message', {
        'user': username,
        'msg': msg,
        'room': room,
        'timestamp': m.timestamp.strftime('%H:%M')
    }, room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
