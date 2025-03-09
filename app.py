from flask import Flask, jsonify, send_from_directory, request
import os
import json
from auth_server import setup_auth_routes

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

# Thiết lập các route cho xác thực và đồng bộ dữ liệu
setup_auth_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 