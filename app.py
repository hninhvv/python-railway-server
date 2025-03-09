from flask import Flask, jsonify, send_from_directory, request
import os
import json

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Xin chào! Đây là server Python của bạn trên Railway",
        "status": "success"
    })

@app.route('/api/info')
def info():
    return jsonify({
        "app_name": "Python Server",
        "version": "1.0.0",
        "author": "Railway User"
    })

# Phục vụ file @key.html khi truy cập /key
@app.route('/key')
def key_html():
    return send_from_directory('translate', '@key.html')

# Phục vụ file sync_data.html khi truy cập /sync
@app.route('/sync')
def sync_data_html():
    return send_from_directory('translate', 'sync_data.html')

# Phục vụ file key.css
@app.route('/key.css')
def key_css():
    return send_from_directory('translate', 'key.css')

# Phục vụ file auth_server.js
@app.route('/auth_server.js')
def auth_server_js():
    return send_from_directory('translate', 'auth_server.js')

# Phục vụ file ip_storage.js
@app.route('/ip_storage.js')
def ip_storage_js():
    return send_from_directory('translate', 'ip_storage.js')

# Phục vụ các file CSS
@app.route('/<path:filename>.css')
def serve_css(filename):
    return send_from_directory('translate', f'{filename}.css')

# Phục vụ các file JavaScript
@app.route('/<path:filename>.js')
def serve_js(filename):
    return send_from_directory('translate', f'{filename}.js')

# API endpoint để đồng bộ dữ liệu
@app.route('/sync_data', methods=['POST'])
def sync_data():
    data = request.json
    # Lưu dữ liệu vào file user_data.json
    with open('translate/user_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, indent=2, ensure_ascii=False, fp=f)
    return jsonify({"status": "success", "message": "Dữ liệu đã được đồng bộ"})

# API endpoint để kiểm tra trạng thái đồng bộ
@app.route('/sync_status', methods=['GET'])
def sync_status():
    try:
        with open('translate/user_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({"status": "success", "data_version": data.get("version", 0)})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Chưa có dữ liệu đồng bộ"})

# API endpoint để lấy dữ liệu người dùng
@app.route('/users', methods=['GET'])
def get_users():
    try:
        with open('translate/user_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"usersWindows": [], "usersMacOS": [], "usersAndroid": [], "usersIOS": []})

# API endpoint để xác thực người dùng
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Kiểm tra thông tin đăng nhập (đơn giản)
    if username == 'admin' and password == 'admin':
        return jsonify({"status": "success", "message": "Đăng nhập thành công!"})
    else:
        return jsonify({"status": "error", "message": "Tên đăng nhập hoặc mật khẩu không đúng!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 