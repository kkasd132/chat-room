from flask import Flask, render_template, request, session, redirect, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

socketio = SocketIO(app, cors_allowed_origins='*')

online_users = set()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class UserSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    bg_color = db.Column(db.String(10), default='#ffffff')
    font_color = db.Column(db.String(10), default='#000000')
    blur = db.Column(db.Integer, default=0)
    custom_bg = db.Column(db.String(200))  

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    
# 訊息模型
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100))
    username = db.Column(db.String(100))
    msg = db.Column(db.String(500))
    image = db.Column(db.String(500))  # 新增圖片網址欄位
    timestamp = db.Column(db.DateTime, default=datetime.now)

@app.route('/')
def index():
    if "username" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session['username']).first()
    setting = UserSetting.query.filter_by(user_id=user.id).first()

    style = {
        'bg_color': setting.bg_color if setting else '#ffffff',
        'font_color': setting.font_color if setting else '#000000',
        'blur': setting.blur if setting else 0,
        'custom_bg': setting.custom_bg if setting and setting.custom_bg else ''
    }

    return render_template("index.html", username=user.username, style=style)

@app.route('/login', methods=['GET'])
def login_page():
    if "username" in session:
        return redirect("/")
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        session['username'] = user.username
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
    if User.query.filter_by(username=data['username']).first():
        return jsonify(success=False, message='帳號已存在')

    user = User(username=data['username'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(success=True)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user:
        user.set_password(data['new_password'])
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False, message='帳號不存在')
@app.route('/setting', methods=['GET'])
def setting():
    if "username" not in session:
        return redirect("/login")
    return render_template("setting.html", username=session["username"])

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

@app.route('/rename_room', methods=['POST'])
def rename_room():
    data = request.json
    old = data.get('old_name')
    new = data.get('new_name')

    if not old or not new:
        return jsonify(success=False, message='缺少名稱')

    # 檢查新名稱是否已存在
    if Room.query.filter_by(name=new).first():
        return jsonify(success=False, message='新名稱已存在')

    # 更新 room 表
    room = Room.query.filter_by(name=old).first()
    if not room:
        return jsonify(success=False, message='聊天室不存在')
    room.name = new

    # 同步更新 message 裡的 room 名稱
    Message.query.filter_by(room=old).update({'room': new})

    db.session.commit()
    return jsonify(success=True)

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_image', methods=['POST'])
def upload_image():
    file = request.files.get('image')
    if not file or file.filename == '':
        return jsonify(success=False, message="No selected file")
    if file and allowed_file(file.filename):
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        ext = os.path.splitext(file.filename)[1]
        username = session.get('username', 'anonymous')
        unique_name = f"{username}_{timestamp}_{uuid.uuid4().hex}{ext}"
        safe_name = secure_filename(unique_name)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        return jsonify(success=True, url=f"/static/uploads/{safe_name}")
    return jsonify(success=False, message="Invalid file type")
@app.route('/save_settings', methods=['POST'])
def save_settings():
    if "username" not in session:
        return jsonify(success=False)

    user = User.query.filter_by(username=session['username']).first()
    setting = UserSetting.query.filter_by(user_id=user.id).first()
    data = request.json
    print(f'data:{data}')
    if not setting:
        setting = UserSetting(user_id=user.id)

    setting.bg_color = data.get('bg_color', '#ffffff')
    setting.font_color = data.get('font_color', '#000000')
    setting.blur = data.get('blur', 0)
    setting.custom_bg = data.get('custom_bg', '')

    db.session.add(setting)
    db.session.commit()
    return jsonify(success=True)

@app.route('/upload_bg_image', methods=['POST'])
def upload_bg_image():
    if 'image' not in request.files:
        return jsonify(success=False, message="No image part")

    file = request.files['image']
    if file.filename == '':
        return jsonify(success=False, message="No selected file")

    if file and allowed_file(file.filename):
        user = User.query.filter_by(username=session['username']).first()
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"user_{user.id}.{ext}"
        folder = os.path.join(app.static_folder, 'uploads', 'user_bg')
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        file.save(filepath)

        return jsonify(success=True, url=f"/static/uploads/user_bg/{filename}")

    return jsonify(success=False, message="Invalid file type")

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
            'image': m.image,
            'room': m.room,
            'timestamp': m.timestamp.strftime('%H:%M')
        })
    emit('joined', {'room': room})

@socketio.on('send_message')
def handle_send(data):
    room = data['room']
    msg = data.get('msg', '')
    image = data.get('image', '')
    username = session['username']
    m = Message(room=room, username=username, msg=msg, image=image)
    db.session.add(m)
    db.session.commit()
    emit('message', {
        'user': username,
        'msg': msg,
        'image': image,
        'room': room,
        'timestamp': m.timestamp.strftime('%H:%M')
    }, room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=8081)
