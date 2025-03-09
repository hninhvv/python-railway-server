from flask import Flask, jsonify
import os

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 