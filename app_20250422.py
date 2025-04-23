from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# 使用者、訊息模型
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100))
    username = db.Column(db.String(100))
    msg = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

online_users = set()
group_rooms = set()

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/get_rooms')
def get_rooms():
    return {'rooms': list(group_rooms)}

@socketio.on('login')
def handle_login(data):
    username = data['username']
    session['username'] = username
    online_users.add(username)
    emit('update_users', list(online_users), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username in online_users:
        online_users.remove(username)
        emit('update_users', list(online_users), broadcast=True)

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
def handle_message(data):
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

@socketio.on('create_group')
def handle_create_group(data):
    room = data['name']
    if room in group_rooms:
        return
    group_rooms.add(room)
    emit('group_created', {'name': room}, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)