from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Đường dẫn đến tệp lưu thông tin đăng nhập
CREDENTIALS_FILE = "credentials.json"

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as file:
            return json.load(file)
    return {}

@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    credentials = load_credentials()

    if credentials.get('username') == username and credentials.get('password') == password:
        return jsonify({"status": "success", "message": "Xác thực thành công"}), 200
    else:
        return jsonify({"status": "failure", "message": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "success", "message": "Server đang hoạt động"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
