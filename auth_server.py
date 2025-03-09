import os
import json
from flask import Flask, request, jsonify

# Đường dẫn đến tệp lưu thông tin đăng nhập
CREDENTIALS_FILE = os.path.join('translate', 'credentials.json')

# Đường dẫn đến tệp lưu thông tin người dùng
USER_DATA_FILE = os.path.join('translate', 'user_data.json')

# Biến để theo dõi phiên bản dữ liệu
current_data_version = 0

def load_credentials():
    """Hàm tải thông tin đăng nhập từ tệp"""
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_user_data():
    """Hàm tải dữ liệu người dùng từ file"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'Lỗi khi đọc file user_data.json: {e}')
            return {
                "usersWindows": [],
                "usersMacOS": [],
                "usersAndroid": [],
                "usersIOS": []
            }
    return {
        "usersWindows": [],
        "usersMacOS": [],
        "usersAndroid": [],
        "usersIOS": []
    }

def save_user_data(data):
    """Hàm lưu dữ liệu người dùng vào file"""
    # Tạo bản sao của dữ liệu để không ảnh hưởng đến dữ liệu gốc
    data_copy = json.loads(json.dumps(data))
    
    # Loại bỏ trường version nếu có
    if 'version' in data_copy:
        del data_copy['version']
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_copy, f, indent=2, ensure_ascii=False)
    
    print('Dữ liệu đã được lưu vào file user_data.json')
    
    # Đọc lại dữ liệu để xác nhận
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        print(f"Đã lưu {len(saved_data.get('usersWindows', []))} người dùng Windows, "
              f"{len(saved_data.get('usersMacOS', []))} người dùng MacOS, "
              f"{len(saved_data.get('usersAndroid', []))} người dùng Android, "
              f"{len(saved_data.get('usersIOS', []))} người dùng iOS")
    except Exception as e:
        print(f'Lỗi khi đọc lại dữ liệu: {e}')

def find_user_by_account(account):
    """Tìm người dùng theo tài khoản trong tất cả các hệ điều hành"""
    user_data = load_user_data()
    
    for os_type in ["usersWindows", "usersMacOS", "usersAndroid", "usersIOS"]:
        for user in user_data.get(os_type, []):
            if user.get('account') == account:
                # Đảm bảo user có các trường gps_info và wifi_name
                if 'gps_info' not in user:
                    user['gps_info'] = {
                        'x': '',
                        'y': '',
                        'address': 'Không có'
                    }
                if 'wifi_name' not in user:
                    user['wifi_name'] = 'Không xác định'
                if 'online_status' not in user:
                    user['online_status'] = 'Offline'
                return user, os_type
    
    return None, None

def setup_auth_routes(app):
    """Thiết lập các route cho xác thực và đồng bộ dữ liệu"""
    
    @app.route('/sync_status', methods=['GET'])
    def sync_status():
        try:
            user_data = load_user_data()
            stats = {
                "usersWindows": len(user_data.get("usersWindows", [])),
                "usersMacOS": len(user_data.get("usersMacOS", [])),
                "usersAndroid": len(user_data.get("usersAndroid", [])),
                "usersIOS": len(user_data.get("usersIOS", []))
            }
            return jsonify({
                "status": "success",
                "data_version": current_data_version,
                "stats": stats
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            })
    
    @app.route('/sync_data', methods=['POST'])
    def sync_data():
        global current_data_version
        try:
            data = request.json
            
            # Cập nhật phiên bản dữ liệu
            if 'version' in data:
                current_data_version = data['version']
            
            # Đảm bảo tất cả người dùng có trường gps_info và wifi_name
            for os_type in ["usersWindows", "usersMacOS", "usersAndroid", "usersIOS"]:
                if os_type in data:
                    for user in data[os_type]:
                        if 'gps_info' not in user:
                            user['gps_info'] = {
                                'x': '',
                                'y': '',
                                'address': 'Không có'
                            }
                        if 'wifi_name' not in user:
                            user['wifi_name'] = 'Không xác định'
                        if 'online_status' not in user:
                            user['online_status'] = 'Offline'
            
            # Lưu dữ liệu vào file
            save_user_data(data)
            
            return jsonify({
                "status": "success",
                "message": "Dữ liệu đã được đồng bộ thành công",
                "data_version": current_data_version
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            })
    
    @app.route('/users', methods=['GET'])
    def get_users():
        try:
            user_data = load_user_data()
            return jsonify(user_data)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "usersWindows": [],
                "usersMacOS": [],
                "usersAndroid": [],
                "usersIOS": []
            })
    
    @app.route('/update_user_info', methods=['POST'])
    def update_user_info():
        try:
            data = request.json
            account = data.get('account')
            ip_address = data.get('ip')
            gps_info = data.get('gps_info', {})
            wifi_name = data.get('wifi_name')
            online_status = data.get('online_status')
            
            if not account:
                return jsonify({"status": "error", "message": "Thiếu thông tin tài khoản"})
            
            # Tải dữ liệu người dùng
            user_data = load_user_data()
            
            # Cập nhật thông tin cho tài khoản
            updated = False
            for os_type in ["usersWindows", "usersMacOS", "usersAndroid", "usersIOS"]:
                for user in user_data.get(os_type, []):
                    if user.get('account') == account:
                        if ip_address:
                            user['ip'] = ip_address
                        if gps_info:
                            user['gps_info'] = gps_info
                        if wifi_name:
                            user['wifi_name'] = wifi_name
                        if online_status:
                            user['online_status'] = online_status
                        updated = True
            
            if updated:
                # Lưu dữ liệu người dùng
                save_user_data(user_data)
                return jsonify({"status": "success", "message": "Đã cập nhật thông tin người dùng thành công"})
            else:
                return jsonify({"status": "error", "message": "Không tìm thấy tài khoản"})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            })
    
    @app.route('/authenticate', methods=['POST'])
    def authenticate():
        try:
            data = request.json
            username = data.get('username')
            password = data.get('password')
            
            print(f"Yêu cầu xác thực cho tài khoản: {username}")
            
            # Kiểm tra thông tin đăng nhập admin
            credentials = load_credentials()
            
            # Nếu không có file credentials.json hoặc file trống, sử dụng thông tin mặc định
            if not credentials:
                if username == 'admin' and password == 'admin':
                    print("Xác thực admin thành công")
                    return jsonify({
                        "status": "success",
                        "message": "Đăng nhập thành công!",
                        "user": {"role": "admin"}
                    })
            else:
                # Kiểm tra thông tin đăng nhập admin từ file
                if username in credentials and credentials[username] == password:
                    print("Xác thực admin từ file thành công")
                    return jsonify({
                        "status": "success",
                        "message": "Đăng nhập thành công!",
                        "user": {"role": "admin"}
                    })
            
            # Nếu không phải admin, kiểm tra trong danh sách người dùng
            user, os_type = find_user_by_account(username)
            
            if user and user.get('password') == password:
                print(f"Xác thực người dùng thành công: {username} ({os_type})")
                return jsonify({
                    "status": "success",
                    "message": "Đăng nhập thành công!",
                    "user": user
                })
            
            print(f"Xác thực thất bại cho tài khoản: {username}")
            return jsonify({
                "status": "error",
                "message": "Tên đăng nhập hoặc mật khẩu không đúng!"
            })
        except Exception as e:
            print(f"Lỗi khi xác thực: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }) 