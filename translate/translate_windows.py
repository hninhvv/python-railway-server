import sys
import os
import json
import requests
import platform
import socket
import subprocess
import random
import string
import re
import uuid
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QFrame, QMessageBox, QCheckBox, QStackedWidget,
                            QGraphicsOpacityEffect)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QBrush, QPen, QLinearGradient, QPainterPath
from PyQt5.QtCore import Qt, QSize, QRect, QPropertyAnimation, QEasingCurve, pyqtProperty, QPoint, QParallelAnimationGroup, QSequentialAnimationGroup, QTimer, QCoreApplication

# Thiết lập thuộc tính chia sẻ OpenGL contexts trước khi tạo QApplication
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Hàm kiểm tra và cài đặt thư viện
def install_and_import(package):
    """Hàm kiểm tra và cài đặt thư viện nếu chưa có"""
    try:
        __import__(package)
        return True
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Đã cài đặt thư viện {package}")
            try:
                __import__(package)
                return True
            except ImportError:
                print(f"Không thể import thư viện {package} sau khi cài đặt")
                return False
        except Exception as e:
            print(f"Không thể cài đặt thư viện {package}: {str(e)}")
            return False

# Cài đặt các thư viện cần thiết
install_and_import('geocoder')
install_and_import('geopy')
install_and_import('requests')

# Kiểm tra và cài đặt PyQtWebEngine
try:
    install_and_import('PyQtWebEngine')
    HAS_WEB_ENGINE = True
except Exception:
    print("Không thể cài đặt PyQtWebEngine. Sẽ sử dụng phương pháp thay thế để lấy vị trí GPS.")
    HAS_WEB_ENGINE = False

# Tiếp tục với các import khác
import geocoder

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json().get('ip', '')
    except requests.RequestException:
        return 'Không thể lấy IP'

def get_device_info():
    return platform.node() or socket.gethostname()

def get_os_info():
    return platform.system() + " " + platform.release()

def get_wifi_name():
    """Hàm lấy tên mạng WiFi đang kết nối"""
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'], shell=True, text=True)
            for line in result.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    return line.split(':')[1].strip()
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.check_output(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I'], shell=True, text=True)
            for line in result.split('\n'):
                if " SSID" in line:
                    return line.split(':')[1].strip()
        elif platform.system() == "Linux":
            result = subprocess.check_output(['iwgetid', '-r'], shell=True, text=True)
            return result.strip()
    except:
        pass
    return "Không xác định"

def get_detailed_gps_location():
    """Hàm lấy dữ liệu GPS từ thiết bị với độ chính xác cao"""
    # Khởi tạo location_data
    location_data = {
        'x': None,
        'y': None,
        'address': 'Không xác định'
    }
    
    # Kiểm tra xem có thể import QtWebEngineWidgets không
    has_web_engine_widgets = False
    if HAS_WEB_ENGINE:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
            from PyQt5.QtCore import QUrl, QEventLoop
            from PyQt5.QtWidgets import QApplication
            has_web_engine_widgets = True
            print("Đã import thành công PyQt5.QtWebEngineWidgets")
        except ImportError as e:
            print(f"Không thể import PyQt5.QtWebEngineWidgets: {str(e)}. Sẽ sử dụng phương pháp thay thế.")
    
    # Nếu có QtWebEngineWidgets, sử dụng HTML5 Geolocation API
    if has_web_engine_widgets:
        import json
        import os
        import time
        
        try:
            class GPSWebPage(QWebEnginePage):
                def __init__(self):
                    super().__init__()
                    self.location_data = None
                    self.loadFinished.connect(self._on_load_finished)
                    self.loop = QEventLoop()
                    
                def _on_load_finished(self):
                    self.runJavaScript("""
                        var sendLocation = function(position) {
                            var coords = position.coords;
                            var locationData = {
                                latitude: coords.latitude,
                                longitude: coords.longitude,
                                accuracy: coords.accuracy,
                                altitude: coords.altitude,
                                altitudeAccuracy: coords.altitudeAccuracy,
                                heading: coords.heading,
                                speed: coords.speed
                            };
                            window.location_data = JSON.stringify(locationData);
                        };
                        
                        var handleError = function(error) {
                            window.location_data = JSON.stringify({
                                error: error.message,
                                code: error.code
                            });
                        };
                        
                        if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(
                                sendLocation, 
                                handleError,
                                {
                                    enableHighAccuracy: true,
                                    timeout: 10000,
                                    maximumAge: 0
                                }
                            );
                        } else {
                            window.location_data = JSON.stringify({
                                error: 'Geolocation is not supported by this browser.'
                            });
                        }
                        
                        // Kiểm tra kết quả sau 1 giây
                        setTimeout(function() {
                            return window.location_data;
                        }, 1000);
                    """, self._handle_location)
                    
                def _handle_location(self, result):
                    if result:
                        try:
                            self.location_data = json.loads(result)
                        except:
                            self.location_data = {"error": "Không thể parse dữ liệu JSON"}
                    else:
                        # Thử lại sau 1 giây nếu chưa có kết quả
                        self.runJavaScript("return window.location_data;", self._handle_location)
                        return
                        
                    self.loop.quit()
            
            # Tạo HTML file tạm thời để lấy vị trí
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Lấy vị trí GPS</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 20px;
                        background: linear-gradient(135deg, #6a11cb, #2575fc);
                        color: white;
                        height: 100vh;
                        margin: 0;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .container {
                        background-color: rgba(255, 255, 255, 0.1);
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        max-width: 500px;
                        width: 100%;
                    }
                    h1 {
                        margin-bottom: 20px;
                    }
                    p {
                        font-size: 16px;
                        line-height: 1.6;
                    }
                    .loader {
                        border: 5px solid #f3f3f3;
                        border-top: 5px solid #3498db;
                        border-radius: 50%;
                        width: 50px;
                        height: 50px;
                        animation: spin 2s linear infinite;
                        margin: 20px auto;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Đang lấy vị trí GPS</h1>
                    <div class="loader"></div>
                    <p>Vui lòng chờ trong giây lát...</p>
                    <p>Hệ thống đang xác định vị trí chính xác của bạn.</p>
                    <p>Nếu trình duyệt hỏi quyền truy cập vị trí, vui lòng chọn "Cho phép".</p>
                </div>
            </body>
            </html>
            """
            
            temp_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_gps.html")
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Khởi tạo ứng dụng Qt nếu chưa có
            app = QApplication.instance()
            if not app:
                app = QApplication([])
            
            # Tạo cửa sổ web để lấy vị trí
            view = QWebEngineView()
            page = GPSWebPage()
            view.setPage(page)
            view.setWindowTitle("Đang lấy vị trí GPS")
            view.resize(600, 400)
            
            # Load file HTML
            view.load(QUrl.fromLocalFile(temp_html_path))
            view.show()
            
            # Chờ tối đa 15 giây để lấy vị trí
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(page.loop.quit)
            timer.start(15000)
            
            # Chạy event loop
            page.loop.exec_()
            
            # Đóng cửa sổ web
            view.close()
            
            # Xóa file HTML tạm
            try:
                os.remove(temp_html_path)
            except:
                pass
            
            # Xử lý kết quả
            if page.location_data:
                if 'error' not in page.location_data:
                    # Lấy vị trí thành công từ HTML5 Geolocation API
                    lat = page.location_data.get('latitude')
                    lng = page.location_data.get('longitude')
                    
                    if lat and lng:
                        location_data['x'] = lng
                        location_data['y'] = lat
                        
                        # Sử dụng Nominatim để lấy địa chỉ từ tọa độ
                        try:
                            from geopy.geocoders import Nominatim
                            geolocator = Nominatim(user_agent="translate_app")
                            location = geolocator.reverse(f"{lat}, {lng}")
                            if location and location.address:
                                # Rút gọn địa chỉ
                                address_parts = location.address.split(', ')
                                if len(address_parts) > 3:
                                    # Lấy thành phố, tỉnh/bang, quốc gia
                                    location_data['address'] = ', '.join(address_parts[-3:])
                                else:
                                    location_data['address'] = location.address
                            else:
                                location_data['address'] = f"{lat}, {lng}"
                        except Exception as e:
                            print(f"Lỗi khi lấy địa chỉ từ tọa độ: {str(e)}")
                            location_data['address'] = f"{lat}, {lng}"
                        
                        print(f"Lấy vị trí thành công từ HTML5 Geolocation API với độ chính xác: {page.location_data.get('accuracy', 'không xác định')} mét")
                else:
                    print(f"Lỗi khi lấy vị trí từ HTML5 Geolocation API: {page.location_data.get('error')}")
        except Exception as e:
            print(f"Lỗi khi sử dụng HTML5 Geolocation API: {str(e)}")
            print("Chuyển sang phương pháp thay thế...")
    else:
        print("Sử dụng phương pháp thay thế để lấy vị trí GPS...")
    
    # Nếu không lấy được vị trí từ HTML5 Geolocation API, thử các phương pháp khác
    if location_data['x'] is None:
        # Phương pháp 1: Sử dụng geocoder với nhiều providers
        providers = ['ipinfo', 'geonames', 'arcgis', 'w3w', 'osm']
        
        for provider in providers:
            try:
                if provider == 'ipinfo':
                    g = geocoder.ipinfo('me')
                elif provider == 'geonames':
                    g = geocoder.geonames('me')
                elif provider == 'arcgis':
                    g = geocoder.arcgis('me')
                elif provider == 'w3w':
                    g = geocoder.w3w('me')
                elif provider == 'osm':
                    g = geocoder.osm('me')
                
                if g.ok:
                    # Rút gọn địa chỉ
                    if hasattr(g, 'address') and g.address:
                        address = g.address
                    elif hasattr(g, 'city') and hasattr(g, 'country') and g.city and g.country:
                        address = f"{g.city}, {g.country}"
                    else:
                        address = "Không xác định"
                    
                    location_data = {
                        'x': g.lng,
                        'y': g.lat,
                        'address': address
                    }
                    print(f"Lấy vị trí thành công từ provider: {provider}")
                    break
            except Exception as e:
                print(f"Lỗi khi sử dụng provider {provider}: {str(e)}")
        
        # Phương pháp 2: Sử dụng IP-API nếu các providers trên không hoạt động
        if location_data['x'] is None:
            try:
                response = requests.get('http://ip-api.com/json/')
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        # Rút gọn địa chỉ
                        city = data.get('city', '')
                        region = data.get('regionName', '')
                        country = data.get('country', '')
                        address_parts = [part for part in [city, region, country] if part]
                        address = ', '.join(address_parts) if address_parts else "Không xác định"
                        
                        location_data = {
                            'x': data.get('lon'),
                            'y': data.get('lat'),
                            'address': address
                        }
                        print("Lấy vị trí thành công từ IP-API")
            except Exception as e:
                print(f"Lỗi khi sử dụng IP-API: {str(e)}")
        
        # Phương pháp 3: Sử dụng ipapi.co nếu các phương pháp trên không hoạt động
        if location_data['x'] is None:
            try:
                response = requests.get('https://ipapi.co/json/')
                if response.status_code == 200:
                    data = response.json()
                    # Rút gọn địa chỉ
                    city = data.get('city', '')
                    region = data.get('region', '')
                    country = data.get('country_name', '')
                    address_parts = [part for part in [city, region, country] if part]
                    address = ', '.join(address_parts) if address_parts else "Không xác định"
                    
                    location_data = {
                        'x': data.get('longitude'),
                        'y': data.get('latitude'),
                        'address': address
                    }
                    print("Lấy vị trí thành công từ ipapi.co")
            except Exception as e:
                print(f"Lỗi khi sử dụng ipapi.co: {str(e)}")
    
    # Định dạng thông tin vị trí theo yêu cầu
    location_str = f"Thông tin vị trí: {location_data['y']}, {location_data['x']} - {location_data['address']}"
    print(location_str)
    
    # Thêm thuộc tính location_str vào location_data
    location_data['location_str'] = location_str
    
    return location_data

class CurvedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Tạo gradient màu cho nền
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#6a11cb"))  # Màu tím đậm
        gradient.setColorAt(1, QColor("#2575fc"))  # Màu xanh dương
        
        # Vẽ hình chữ nhật bo cong với gradient
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 0, 0)  # Bo cong góc phải
        
        # Vẽ đường cong
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(self.width() - 80, 0)
        path.cubicTo(self.width() - 40, self.height() / 3, 
                    self.width(), self.height() / 2, 
                    self.width() - 40, self.height())
        path.lineTo(0, self.height())
        path.closeSubpath()
        
        painter.fillPath(path, QBrush(gradient))
        
        # Vẽ đường viền trang trí màu vàng
        pen = QPen(QColor("#FFD700"), 3)  # Màu vàng gold
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        
        curve_path = QPainterPath()
        curve_path.moveTo(self.width() - 80, 0)
        curve_path.cubicTo(self.width() - 40, self.height() / 3, 
                          self.width(), self.height() / 2, 
                          self.width() - 40, self.height())
        
        painter.drawPath(curve_path)

class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        self._color = QColor(41, 128, 185)
        self._radius = 22
        
        # Hiệu ứng hover với gradient
        self.setStyleSheet("""
            QPushButton {
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 14px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a11cb, stop:1 #2575fc);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8e2de2, stop:1 #4a00e0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5614b0, stop:1 #1a53ff);
            }
        """)

class CustomLineEdit(QLineEdit):
    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(45)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 22px;
                padding: 0 15px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #6a11cb;
            }
        """)

class PasswordLineEdit(QWidget):
    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        
        # Layout chính
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Ô nhập mật khẩu
        self.password_input = CustomLineEdit(placeholder)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 22px;
                padding: 0 45px 0 15px;  /* Thêm padding bên phải để chừa chỗ cho nút */
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #6a11cb;
            }
        """)
        
        # Container cho ô nhập và nút
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Thêm ô nhập vào container
        container_layout.addWidget(self.password_input)
        
        # Nút hiển thị/ẩn mật khẩu
        self.toggle_button = QPushButton("👁️")
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: #7f8c8d;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #6a11cb;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_password_visibility)
        
        # Thêm nút vào layout
        layout.addWidget(self.password_input)
        
        # Thiết lập vị trí của nút
        self.toggle_button.setParent(self.password_input)
        self.toggle_button.move(self.password_input.width() - 40, 8)
        self.password_input.resizeEvent = self.on_resize
        
        # Trạng thái hiển thị mật khẩu
        self.password_visible = False
    
    def on_resize(self, event):
        # Cập nhật vị trí của nút khi ô nhập thay đổi kích thước
        self.toggle_button.move(self.password_input.width() - 40, 8)
        QLineEdit.resizeEvent(self.password_input, event)
    
    def toggle_password_visibility(self):
        # Chuyển đổi trạng thái hiển thị mật khẩu
        self.password_visible = not self.password_visible
        
        if self.password_visible:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_button.setText("🔒")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_button.setText("👁️")
    
    def text(self):
        return self.password_input.text()
    
    def setText(self, text):
        self.password_input.setText(text)
    
    def clear(self):
        self.password_input.clear()

# Thêm lớp SlideStackedWidget để tạo hiệu ứng trượt ngang
class SlideStackedWidget(QStackedWidget):
    SLIDE_HORIZONTAL = 1
    SLIDE_VERTICAL = 2
    FADE = 3
    ROTATE = 4
    ZOOM = 5
    
    def __init__(self, parent=None):
        super(SlideStackedWidget, self).__init__(parent)
        
        self.m_direction = Qt.Horizontal
        self.m_speed = 500
        self.m_animationtype = QEasingCurve.OutCubic
        self.m_now = 0
        self.m_next = 0
        self.m_wrap = False
        self.m_pnow = QPoint(0, 0)
        self.m_active = False
        self.m_effects = {}  # Lưu trữ hiệu ứng cho mỗi widget
        
    def setDirection(self, direction):
        self.m_direction = direction
        
    def setSpeed(self, speed):
        self.m_speed = speed
        
    def setAnimation(self, animationtype):
        self.m_animationtype = animationtype
        
    def setWrap(self, wrap):
        self.m_wrap = wrap
        
    def slideInPrev(self):
        now = self.currentIndex()
        if self.m_wrap or now > 0:
            self.slideInIdx(now - 1)
            
    def slideInNext(self):
        now = self.currentIndex()
        if self.m_wrap or now < (self.count() - 1):
            self.slideInIdx(now + 1)
            
    def slideInIdx(self, idx, effect_type=SLIDE_HORIZONTAL):
        if idx > (self.count() - 1):
            idx = idx % self.count()
        elif idx < 0:
            idx = (idx + self.count()) % self.count()
            
        self.slideInWgt(self.widget(idx), effect_type)
        
    def slideInWgt(self, newwidget, effect_type=SLIDE_HORIZONTAL):
        if self.m_active:
            return
            
        self.m_active = True
        
        _now = self.currentIndex()
        _next = self.indexOf(newwidget)
        
        if _now == _next:
            self.m_active = False
            return
        
        # Lưu trữ hiệu ứng cho widget này
        self.m_effects[_next] = effect_type
        
        if effect_type == self.SLIDE_HORIZONTAL or effect_type == self.SLIDE_VERTICAL:
            self._slideEffect(_now, _next, effect_type)
        elif effect_type == self.FADE:
            self._fadeEffect(_now, _next)
        elif effect_type == self.ROTATE:
            self._rotateEffect(_now, _next)
        elif effect_type == self.ZOOM:
            self._zoomEffect(_now, _next)
    
    def _slideEffect(self, _now, _next, direction):
        offsetx, offsety = self.frameRect().width(), self.frameRect().height()
        self.widget(_next).setGeometry(self.frameRect())
        
        if direction == self.SLIDE_VERTICAL:
            if _now < _next:
                offsetx, offsety = 0, -offsety
            else:
                offsetx, offsety = 0, offsety
        else:  # SLIDE_HORIZONTAL
            if _now < _next:
                offsetx, offsety = -offsetx, 0
            else:
                offsetx, offsety = offsetx, 0
                
        pnext = self.widget(_next).pos()
        pnow = self.widget(_now).pos()
        self.m_pnow = pnow
        
        offset = QPoint(offsetx, offsety)
        self.widget(_next).move(pnext - offset)
        self.widget(_next).show()
        self.widget(_next).raise_()
        
        anim_group = QParallelAnimationGroup(self)
        
        for index, start, end in zip(
            (_now, _next), (pnow, pnext - offset), (pnow + offset, pnext)
        ):
            animation = QPropertyAnimation(self.widget(index), b"pos")
            animation.setDuration(self.m_speed)
            animation.setEasingCurve(self.m_animationtype)
            animation.setStartValue(start)
            animation.setEndValue(end)
            anim_group.addAnimation(animation)
            
        anim_group.finished.connect(self.animationDoneSlot)
        self.m_next = _next
        self.m_now = _now
        self.m_active = True
        anim_group.start(QPropertyAnimation.DeleteWhenStopped)
    
    def _fadeEffect(self, _now, _next):
        self.widget(_next).setGeometry(self.frameRect())
        
        # Tạo hiệu ứng opacity cho cả hai widget
        effect_now = QGraphicsOpacityEffect(self.widget(_now))
        effect_next = QGraphicsOpacityEffect(self.widget(_next))
        
        self.widget(_now).setGraphicsEffect(effect_now)
        self.widget(_next).setGraphicsEffect(effect_next)
        
        # Thiết lập opacity ban đầu
        effect_now.setOpacity(1.0)
        effect_next.setOpacity(0.0)
        
        self.widget(_next).show()
        self.widget(_next).raise_()
        
        # Tạo animation cho hiệu ứng fade
        anim_group = QParallelAnimationGroup(self)
        
        # Animation cho widget hiện tại (fade out)
        anim_now = QPropertyAnimation(effect_now, b"opacity")
        anim_now.setDuration(self.m_speed)
        anim_now.setStartValue(1.0)
        anim_now.setEndValue(0.0)
        anim_now.setEasingCurve(QEasingCurve.OutCubic)
        
        # Animation cho widget tiếp theo (fade in)
        anim_next = QPropertyAnimation(effect_next, b"opacity")
        anim_next.setDuration(self.m_speed)
        anim_next.setStartValue(0.0)
        anim_next.setEndValue(1.0)
        anim_next.setEasingCurve(QEasingCurve.InCubic)
        
        anim_group.addAnimation(anim_now)
        anim_group.addAnimation(anim_next)
        
        anim_group.finished.connect(self.animationDoneSlot)
        self.m_next = _next
        self.m_now = _now
        self.m_active = True
        anim_group.start(QPropertyAnimation.DeleteWhenStopped)
    
    def _rotateEffect(self, _now, _next):
        # Thiết lập vị trí và hiển thị widget tiếp theo
        self.widget(_next).setGeometry(self.frameRect())
        self.widget(_next).show()
        self.widget(_next).raise_()
        
        # Tạo hiệu ứng opacity cho cả hai widget
        effect_now = QGraphicsOpacityEffect(self.widget(_now))
        effect_next = QGraphicsOpacityEffect(self.widget(_next))
        
        self.widget(_now).setGraphicsEffect(effect_now)
        self.widget(_next).setGraphicsEffect(effect_next)
        
        # Thiết lập opacity ban đầu
        effect_now.setOpacity(1.0)
        effect_next.setOpacity(0.0)
        
        # Tạo animation cho hiệu ứng xoay và mờ dần
        anim_group = QSequentialAnimationGroup(self)
        
        # Animation cho widget hiện tại (fade out và xoay)
        fade_out_group = QParallelAnimationGroup()
        
        # Opacity animation
        anim_now_opacity = QPropertyAnimation(effect_now, b"opacity")
        anim_now_opacity.setDuration(self.m_speed // 2)
        anim_now_opacity.setStartValue(1.0)
        anim_now_opacity.setEndValue(0.0)
        anim_now_opacity.setEasingCurve(QEasingCurve.OutCubic)
        
        fade_out_group.addAnimation(anim_now_opacity)
        
        # Animation cho widget tiếp theo (fade in và xoay)
        fade_in_group = QParallelAnimationGroup()
        
        # Opacity animation
        anim_next_opacity = QPropertyAnimation(effect_next, b"opacity")
        anim_next_opacity.setDuration(self.m_speed // 2)
        anim_next_opacity.setStartValue(0.0)
        anim_next_opacity.setEndValue(1.0)
        anim_next_opacity.setEasingCurve(QEasingCurve.InCubic)
        
        fade_in_group.addAnimation(anim_next_opacity)
        
        # Thêm các nhóm animation vào nhóm tuần tự
        anim_group.addAnimation(fade_out_group)
        anim_group.addAnimation(fade_in_group)
        
        anim_group.finished.connect(self.animationDoneSlot)
        self.m_next = _next
        self.m_now = _now
        self.m_active = True
        anim_group.start(QPropertyAnimation.DeleteWhenStopped)
    
    def _zoomEffect(self, _now, _next):
        # Thiết lập vị trí và hiển thị widget tiếp theo
        self.widget(_next).setGeometry(self.frameRect())
        
        # Tạo hiệu ứng opacity cho widget tiếp theo
        effect_next = QGraphicsOpacityEffect(self.widget(_next))
        self.widget(_next).setGraphicsEffect(effect_next)
        effect_next.setOpacity(0.0)
        
        self.widget(_next).show()
        self.widget(_next).raise_()
        
        # Tạo animation cho hiệu ứng zoom và mờ dần
        anim_group = QParallelAnimationGroup(self)
        
        # Animation cho opacity của widget tiếp theo
        anim_opacity = QPropertyAnimation(effect_next, b"opacity")
        anim_opacity.setDuration(self.m_speed)
        anim_opacity.setStartValue(0.0)
        anim_opacity.setEndValue(1.0)
        anim_opacity.setEasingCurve(QEasingCurve.InOutCubic)
        
        anim_group.addAnimation(anim_opacity)
        
        anim_group.finished.connect(self.animationDoneSlot)
        self.m_next = _next
        self.m_now = _now
        self.m_active = True
        anim_group.start(QPropertyAnimation.DeleteWhenStopped)
        
    def animationDoneSlot(self):
        self.setCurrentIndex(self.m_next)
        self.widget(self.m_now).hide()
        self.widget(self.m_now).move(self.m_pnow)
        self.m_active = False
        
        # Xóa hiệu ứng đồ họa sau khi hoàn thành
        self.widget(self.m_now).setGraphicsEffect(None)
        self.widget(self.m_next).setGraphicsEffect(None)

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Đăng Nhập - Ứng Dụng Dịch")
        self.setFixedSize(900, 600)
        self.setWindowIcon(QIcon("icon.png"))  # Thêm icon nếu có
        
        # Đường dẫn file lưu thông tin đăng nhập
        self.credentials_file = "credentials.json"
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Stacked Widget để chuyển đổi giữa đăng nhập và đăng ký với nhiều hiệu ứng
        self.stacked_widget = SlideStackedWidget()
        self.stacked_widget.setSpeed(500)  # Tốc độ animation (ms)
        self.stacked_widget.setAnimation(QEasingCurve.OutCubic)  # Kiểu animation
        
        # Layout chính
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)
        
        # Tạo widget đăng nhập
        self.login_widget = QWidget()
        self.create_login_ui()
        
        # Tạo widget đăng ký
        self.register_widget = QWidget()
        self.create_register_ui()
        
        # Thêm các widget vào stacked widget
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.register_widget)
        
        # Hiển thị màn hình đăng nhập đầu tiên
        self.stacked_widget.setCurrentIndex(0)
        
        # Biến để theo dõi hiệu ứng hiện tại
        self.current_effect = 0
        self.effects = [
            SlideStackedWidget.SLIDE_HORIZONTAL,
            SlideStackedWidget.SLIDE_VERTICAL,
            SlideStackedWidget.FADE,
            SlideStackedWidget.ROTATE,
            SlideStackedWidget.ZOOM
        ]
        
        # Tải thông tin đăng nhập nếu có
        self.load_credentials()
        
    def load_credentials(self):
        # Tải thông tin đăng nhập từ file
        if os.path.exists(self.credentials_file):
            with open(self.credentials_file, 'r') as file:
                credentials = json.load(file)
                self.username_input.setText(credentials.get('username', ''))
                self.password_input.setText(credentials.get('password', ''))
                self.remember_checkbox.setChecked(True)

    def save_credentials(self):
        # Lưu thông tin đăng nhập vào file
        if self.remember_checkbox.isChecked():
            credentials = {
                'username': self.username_input.text(),
                'password': self.password_input.text()
            }
            with open(self.credentials_file, 'w') as file:
                json.dump(credentials, file)
        else:
            # Xóa thông tin nếu không chọn "Nhớ mật khẩu"
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)

    def create_login_ui(self):
        # Layout chính cho widget đăng nhập
        login_main_layout = QHBoxLayout(self.login_widget)
        login_main_layout.setContentsMargins(0, 0, 0, 0)
        login_main_layout.setSpacing(0)
        
        # Panel bên trái (hình ảnh) với đường cong
        left_panel = CurvedPanel()
        left_panel.setFixedWidth(450)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignCenter)
        left_layout.setContentsMargins(30, 50, 80, 50)  # Tăng margin bên phải để tránh text bị che bởi đường cong
        
        # Logo hoặc hình ảnh
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        logo_label.setText("TRANSLATE APP")
        
        # Mô tả ứng dụng
        desc_label = QLabel("Ứng dụng dịch thuật thông minh\nvới công nghệ AI tiên tiến")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: white; font-size: 16px;")
        
        left_layout.addStretch()
        left_layout.addWidget(logo_label)
        left_layout.addSpacing(20)
        left_layout.addWidget(desc_label)
        left_layout.addStretch()
        
        # Panel bên phải (đăng nhập)
        right_panel = QWidget()
        right_panel.setStyleSheet("""
            background-color: white;
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(50, 50, 50, 50)
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignCenter)
        
        # Tiêu đề đăng nhập
        login_title = QLabel("ĐĂNG NHẬP")
        login_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #6a11cb; margin-bottom: 5px;")
        login_title.setAlignment(Qt.AlignCenter)
        
        # Mô tả
        login_desc = QLabel("Vui lòng đăng nhập để sử dụng dịch vụ")
        login_desc.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 20px;")
        login_desc.setAlignment(Qt.AlignCenter)
        
        # Form đăng nhập
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # Tên đăng nhập
        self.username_input = CustomLineEdit("Tên đăng nhập")
        
        # Mật khẩu
        self.password_input = PasswordLineEdit("Mật khẩu")
        
        # Nhớ mật khẩu
        remember_layout = QHBoxLayout()
        self.remember_checkbox = QCheckBox("Nhớ mật khẩu")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #7f8c8d;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #6a11cb;
                border: none;
                border-radius: 4px;
            }
            QCheckBox:hover {
                color: #6a11cb;
            }
            QCheckBox::indicator:hover:unchecked {
                border: 2px solid #2575fc;
            }
            QCheckBox::indicator:hover:checked {
                background-color: #8e2de2;
            }
        """)
        
        # Quên mật khẩu
        forgot_password = QPushButton("Quên mật khẩu?")
        forgot_password.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6a11cb;
                font-size: 14px;
                text-align: right;
                background-color: transparent;
            }
            QPushButton:hover {
                color: #4a00e0;
                text-decoration: underline;
            }
        """)
        forgot_password.setCursor(Qt.PointingHandCursor)
        
        remember_layout.addWidget(self.remember_checkbox)
        remember_layout.addStretch()
        remember_layout.addWidget(forgot_password)
        
        # Nút đăng nhập
        self.login_button = RoundedButton("ĐĂNG NHẬP")
        self.login_button.clicked.connect(self.login)
        
        # Đăng ký
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignCenter)
        
        register_label = QLabel("Chưa có tài khoản?")
        register_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        
        register_button = QPushButton("Đăng ký ngay")
        register_button.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6a11cb;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }
            QPushButton:hover {
                color: #4a00e0;
                text-decoration: underline;
            }
        """)
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.clicked.connect(self.show_register)
        
        register_layout.addWidget(register_label)
        register_layout.addWidget(register_button)
        
        # Thêm các widget vào form
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_input)
        form_layout.addLayout(remember_layout)
        form_layout.addWidget(self.login_button)
        form_layout.addSpacing(20)
        form_layout.addLayout(register_layout)
        
        # Thêm các widget vào layout bên phải
        right_layout.addStretch()
        right_layout.addWidget(login_title)
        right_layout.addWidget(login_desc)
        right_layout.addWidget(form_widget)
        right_layout.addStretch()
        
        # Thêm các panel vào layout chính
        login_main_layout.addWidget(left_panel)
        login_main_layout.addWidget(right_panel)
    
    def create_register_ui(self):
        # Layout chính cho widget đăng ký
        register_main_layout = QHBoxLayout(self.register_widget)
        register_main_layout.setContentsMargins(0, 0, 0, 0)
        register_main_layout.setSpacing(0)
        
        # Panel bên trái (hình ảnh) với đường cong - đảo ngược so với đăng nhập
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            background-color: white;
        """)
        left_panel.setFixedWidth(450)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(50, 50, 50, 50)
        left_layout.setSpacing(20)
        left_layout.setAlignment(Qt.AlignCenter)
        
        # Tiêu đề đăng ký
        register_title = QLabel("ĐĂNG KÝ")
        register_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #6a11cb; margin-bottom: 5px;")
        register_title.setAlignment(Qt.AlignCenter)
        
        # Mô tả
        register_desc = QLabel("Tạo tài khoản mới để sử dụng dịch vụ")
        register_desc.setStyleSheet("font-size: 14px; color: #7f8c8d; margin-bottom: 20px;")
        register_desc.setAlignment(Qt.AlignCenter)
        
        # Form đăng ký
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # Họ tên
        self.fullname_input = CustomLineEdit("Họ và tên")
        
        # Email
        self.email_input = CustomLineEdit("Email")
        
        # Tên đăng nhập
        self.new_username_input = CustomLineEdit("Tên đăng nhập")
        
        # Mật khẩu
        self.new_password_input = PasswordLineEdit("Mật khẩu")
        
        # Xác nhận mật khẩu
        self.confirm_password_input = PasswordLineEdit("Xác nhận mật khẩu")
        
        # Điều khoản
        terms_layout = QHBoxLayout()
        self.terms_checkbox = QCheckBox("Tôi đồng ý với các điều khoản dịch vụ")
        self.terms_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #7f8c8d;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #6a11cb;
                border: none;
                border-radius: 4px;
            }
            QCheckBox:hover {
                color: #6a11cb;
            }
            QCheckBox::indicator:hover:unchecked {
                border: 2px solid #2575fc;
            }
            QCheckBox::indicator:hover:checked {
                background-color: #8e2de2;
            }
        """)
        
        terms_layout.addWidget(self.terms_checkbox)
        terms_layout.addStretch()
        
        # Nút đăng ký
        self.register_button = RoundedButton("ĐĂNG KÝ")
        self.register_button.clicked.connect(self.register)
        
        # Quay lại đăng nhập
        login_again_layout = QHBoxLayout()
        login_again_layout.setAlignment(Qt.AlignCenter)
        
        login_again_label = QLabel("Đã có tài khoản?")
        login_again_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        
        login_again_button = QPushButton("Đăng nhập")
        login_again_button.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6a11cb;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }
            QPushButton:hover {
                color: #4a00e0;
                text-decoration: underline;
            }
        """)
        login_again_button.setCursor(Qt.PointingHandCursor)
        login_again_button.clicked.connect(self.show_login)
        
        login_again_layout.addWidget(login_again_label)
        login_again_layout.addWidget(login_again_button)
        
        # Thêm các widget vào form
        form_layout.addWidget(self.fullname_input)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.new_username_input)
        form_layout.addWidget(self.new_password_input)
        form_layout.addWidget(self.confirm_password_input)
        form_layout.addLayout(terms_layout)
        form_layout.addWidget(self.register_button)
        form_layout.addSpacing(20)
        form_layout.addLayout(login_again_layout)
        
        # Thêm các widget vào layout bên trái
        left_layout.addStretch()
        left_layout.addWidget(register_title)
        left_layout.addWidget(register_desc)
        left_layout.addWidget(form_widget)
        left_layout.addStretch()
        
        # Panel bên phải với đường cong ngược
        class ReverseCurvedPanel(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setAutoFillBackground(False)
                
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Tạo gradient màu cho nền
                gradient = QLinearGradient(0, 0, self.width(), self.height())
                gradient.setColorAt(0, QColor("#2575fc"))  # Màu xanh dương
                gradient.setColorAt(1, QColor("#6a11cb"))  # Màu tím đậm
                
                # Vẽ đường cong
                path = QPainterPath()
                path.moveTo(self.width(), 0)
                path.lineTo(80, 0)
                path.cubicTo(40, self.height() / 3, 
                            0, self.height() / 2, 
                            40, self.height())
                path.lineTo(self.width(), self.height())
                path.closeSubpath()
                
                painter.fillPath(path, QBrush(gradient))
                
                # Vẽ đường viền trang trí màu vàng
                pen = QPen(QColor("#FFD700"), 3)  # Màu vàng gold
                pen.setStyle(Qt.SolidLine)
                painter.setPen(pen)
                
                curve_path = QPainterPath()
                curve_path.moveTo(80, 0)
                curve_path.cubicTo(40, self.height() / 3, 
                                0, self.height() / 2, 
                                40, self.height())
                
                painter.drawPath(curve_path)
        
        right_panel = ReverseCurvedPanel()
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setContentsMargins(80, 50, 30, 50)  # Tăng margin bên trái để tránh text bị che bởi đường cong
        
        # Logo hoặc hình ảnh
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        logo_label.setText("TRANSLATE APP")
        
        # Mô tả ứng dụng
        desc_label = QLabel("Tham gia cùng cộng đồng\ndịch thuật thông minh")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: white; font-size: 16px;")
        
        right_layout.addStretch()
        right_layout.addWidget(logo_label)
        right_layout.addSpacing(20)
        right_layout.addWidget(desc_label)
        right_layout.addStretch()
        
        # Thêm các panel vào layout chính
        register_main_layout.addWidget(left_panel)
        register_main_layout.addWidget(right_panel)
    
    def show_register(self):
        # Chuyển đến màn hình đăng ký với hiệu ứng trượt sang phải
        self.stacked_widget.slideInWgt(self.register_widget, SlideStackedWidget.FADE)
    
    def show_login(self):
        # Chuyển đến màn hình đăng nhập với hiệu ứng trượt sang trái
        self.stacked_widget.slideInWgt(self.login_widget, SlideStackedWidget.ZOOM)
    
    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Lỗi đăng nhập", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return
        
        self.login_button.setEnabled(False)
        self.login_button.setText("ĐANG XỬ LÝ...")
        
        try:
            api_url = 'https://web-production-baac.up.railway.app/authenticate'
            
            response = requests.post(api_url, json={
                'username': username,
                'password': password
            }, timeout=10)
            
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'success':
                QMessageBox.information(self, "Thành công", data.get('message', 'Đăng nhập thành công!'))
                
                # Lưu thông tin người dùng nếu cần
                if self.remember_checkbox.isChecked():
                    self.save_credentials()
                
                # Lưu thông tin người dùng để sử dụng trong ứng dụng
                self.user_info = data.get('user', {})
                
                # Lấy thông tin thiết bị
                ip_address = get_public_ip()
                device_info = get_device_info()
                os_info = get_os_info()
                wifi_name = get_wifi_name()
                
                # Lấy thông tin GPS
                gps_info = get_detailed_gps_location()
                
                # Xác định hệ điều hành hiện tại
                current_os = platform.system()
                os_type = ""
                
                if current_os == "Windows":
                    os_type = "Windows"
                elif current_os == "Darwin":
                    os_type = "MacOS"
                elif current_os == "Linux":
                    # Kiểm tra thêm để phân biệt giữa Android và Linux
                    if "android" in os_info.lower():
                        os_type = "Android"
                    else:
                        os_type = "Android"  # Mặc định Linux là Android cho mục đích này
                elif "iphone" in device_info.lower() or "ipad" in device_info.lower() or "ios" in os_info.lower():
                    os_type = "IOS"
                else:
                    # Kiểm tra thêm thông tin thiết bị
                    if "android" in device_info.lower():
                        os_type = "Android"
                    else:
                        os_type = "IOS"  # Mặc định là IOS nếu không xác định được
                
                # Lưu thông tin thiết bị vào user_info
                self.user_info['device_info'] = device_info
                self.user_info['os_info'] = os_info
                self.user_info['os_type'] = os_type
                self.user_info['wifi_name'] = wifi_name
                self.user_info['gps_info'] = gps_info
                
                # Gửi địa chỉ IP và thông tin GPS đến máy chủ
                requests.post('https://web-production-baac.up.railway.app/update_user_info', json={
                    'account': username, 
                    'ip': ip_address,
                    'gps_info': gps_info,
                    'wifi_name': wifi_name,
                    'online_status': 'Online'
                })
                
                # In ra thông tin
                print(f"Địa chỉ IP: {ip_address}")
                print(f"Thiết bị: {device_info}")
                print(f"Hệ điều hành: {os_info}")
                print(f"Loại hệ điều hành: {os_type}")
                print(f"Tên WiFi: {wifi_name}")
                print(f"Thông tin GPS: {gps_info}")
                
                # Chuyển đến màn hình chính
                self.show_main_app()
            else:
                error_message = data.get('message', 'Tên đăng nhập hoặc mật khẩu không chính xác!')
                QMessageBox.critical(self, "Lỗi đăng nhập", error_message)
        
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Lỗi kết nối", "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối internet!")
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "Lỗi kết nối", "Kết nối đến máy chủ quá thời gian. Vui lòng thử lại sau!")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Lỗi kết nối", f"Lỗi không xác định: {str(e)}")
        except ValueError:
            QMessageBox.critical(self, "Lỗi xử lý", "Phản hồi từ máy chủ không hợp lệ!")
        finally:
            self.login_button.setEnabled(True)
            self.login_button.setText("ĐĂNG NHẬP")
    
    def register(self):
        fullname = self.fullname_input.text()
        email = self.email_input.text()
        username = self.new_username_input.text()
        password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Kiểm tra các trường dữ liệu
        if not fullname or not email or not username or not password or not confirm_password:
            QMessageBox.warning(self, "Lỗi đăng ký", "Vui lòng điền đầy đủ thông tin!")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Lỗi đăng ký", "Mật khẩu xác nhận không khớp!")
            return
        
        if not self.terms_checkbox.isChecked():
            QMessageBox.warning(self, "Lỗi đăng ký", "Vui lòng đồng ý với điều khoản dịch vụ!")
            return
        
        # Hiển thị thông báo đang xử lý
        self.register_button.setEnabled(False)
        self.register_button.setText("ĐANG XỬ LÝ...")
        
        try:
            # Xác định hệ điều hành hiện tại một cách chính xác hơn
            current_os = platform.system()
            os_type = ""
            device_info = get_device_info()
            os_info = get_os_info()
            
            if current_os == "Windows":
                os_type = "Windows"
            elif current_os == "Darwin":
                os_type = "MacOS"
            elif current_os == "Linux":
                # Kiểm tra thêm để phân biệt giữa Android và Linux
                if "android" in os_info.lower():
                    os_type = "Android"
                else:
                    os_type = "Android"  # Mặc định Linux là Android cho mục đích này
            elif "iphone" in device_info.lower() or "ipad" in device_info.lower() or "ios" in os_info.lower():
                os_type = "IOS"
            else:
                # Kiểm tra thêm thông tin thiết bị
                if "android" in device_info.lower():
                    os_type = "Android"
                else:
                    os_type = "IOS"  # Mặc định là IOS nếu không xác định được
            
            print(f"Thiết bị được xác định là: {os_type}")
            print(f"Thông tin thiết bị: {device_info}")
            print(f"Thông tin hệ điều hành: {os_info}")
            
            # Lấy địa chỉ IP
            ip_address = get_public_ip()
            
            # Tạo dữ liệu người dùng mới
            new_user = {
                "name": fullname,
                "email": email,
                "account": username,
                "password": password,
                "limited": "Unlimited",  # Mặc định là không giới hạn
                "status": "Active",
                "ip": ip_address,
                "mac": self.generate_random_mac(),
                "device_info": device_info,
                "os_info": os_info,
                "os_type": os_type  # Lưu loại hệ điều hành để sử dụng sau này
            }
            
            print(f"Đang tạo người dùng mới: {new_user}")
            
            # Đầu tiên, lấy dữ liệu người dùng hiện tại từ server
            response = requests.get('https://web-production-baac.up.railway.app/users', timeout=10)
            if response.status_code != 200:
                QMessageBox.critical(self, "Lỗi kết nối", "Không thể kết nối đến máy chủ để lấy dữ liệu người dùng!")
                return
            
            user_data = response.json()
            print(f"Đã nhận dữ liệu từ server: {len(user_data.get('usersWindows', []))} người dùng Windows, {len(user_data.get('usersMacOS', []))} người dùng MacOS, {len(user_data.get('usersAndroid', []))} người dùng Android, {len(user_data.get('usersIOS', []))} người dùng iOS")
            
            # Kiểm tra xem tài khoản đã tồn tại chưa
            all_users = []
            for os_users in [user_data.get('usersWindows', []), user_data.get('usersMacOS', []), 
                            user_data.get('usersAndroid', []), user_data.get('usersIOS', [])]:
                if os_users:  # Kiểm tra xem os_users có tồn tại không
                    all_users.extend(os_users)
            
            if any(user.get('account') == username for user in all_users if user):
                QMessageBox.warning(self, "Lỗi đăng ký", "Tên đăng nhập đã tồn tại!")
                return
            
            # Đảm bảo tất cả các danh sách người dùng đều tồn tại
            if 'usersWindows' not in user_data:
                user_data['usersWindows'] = []
            if 'usersMacOS' not in user_data:
                user_data['usersMacOS'] = []
            if 'usersAndroid' not in user_data:
                user_data['usersAndroid'] = []
            if 'usersIOS' not in user_data:
                user_data['usersIOS'] = []
            
            # Thêm người dùng mới vào danh sách người dùng tương ứng với hệ điều hành
            if os_type == "Windows":
                user_data['usersWindows'].insert(0, new_user)
            elif os_type == "MacOS":
                user_data['usersMacOS'].insert(0, new_user)
            elif os_type == "Android":
                user_data['usersAndroid'].insert(0, new_user)
            else:  # IOS
                user_data['usersIOS'].insert(0, new_user)
            
            print(f"Đã thêm người dùng mới vào {os_type}")
            
            # Đồng bộ tất cả dữ liệu để đảm bảo server có đầy đủ thông tin
            sync_data = {
                'usersWindows': user_data['usersWindows'],
                'usersMacOS': user_data['usersMacOS'],
                'usersAndroid': user_data['usersAndroid'],
                'usersIOS': user_data['usersIOS'],
                'version': 1
            }
            
            print(f"Đang đồng bộ dữ liệu với server...")
            
            # Đồng bộ dữ liệu với server
            sync_response = requests.post(
                'https://web-production-baac.up.railway.app/sync_data', 
                json=sync_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"Phản hồi từ server: {sync_response.status_code}")
            
            if sync_response.status_code != 200:
                print(f"Lỗi đồng bộ: {sync_response.text}")
                QMessageBox.critical(self, "Lỗi đồng bộ", f"Không thể đồng bộ dữ liệu với máy chủ! Mã lỗi: {sync_response.status_code}")
                return
            
            # Lưu thông tin thiết bị để sử dụng sau khi đăng nhập
            self.device_info = {
                'os_type': os_type,
                'device_info': device_info,
                'os_info': os_info
            }
            
            # Đăng ký thành công
            QMessageBox.information(self, "Thành công", f"Đăng ký tài khoản thành công! Bạn có thể đăng nhập ngay bây giờ.")
            
            # Tự động điền thông tin đăng nhập
            self.username_input.setText(username)
            self.password_input.setText(password)
            
            # Chuyển về màn hình đăng nhập
            self.show_login()
            
        except requests.exceptions.ConnectionError as e:
            print(f"Lỗi kết nối: {str(e)}")
            QMessageBox.critical(self, "Lỗi kết nối", "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối internet!")
        except requests.exceptions.Timeout as e:
            print(f"Lỗi timeout: {str(e)}")
            QMessageBox.critical(self, "Lỗi kết nối", "Kết nối đến máy chủ quá thời gian. Vui lòng thử lại sau!")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi request: {str(e)}")
            QMessageBox.critical(self, "Lỗi kết nối", f"Lỗi không xác định: {str(e)}")
        except ValueError as e:
            print(f"Lỗi giá trị: {str(e)}")
            QMessageBox.critical(self, "Lỗi xử lý", f"Phản hồi từ máy chủ không hợp lệ: {str(e)}")
        except Exception as e:
            print(f"Lỗi không xác định: {str(e)}")
            QMessageBox.critical(self, "Lỗi không xác định", f"Đã xảy ra lỗi: {str(e)}")
        finally:
            self.register_button.setEnabled(True)
            self.register_button.setText("ĐĂNG KÝ")
    
    def generate_random_mac(self):
        """Tạo địa chỉ MAC ngẫu nhiên"""
        import random
        return ":".join(["{:02x}".format(random.randint(0, 255)) for _ in range(6)]).upper()
    
    def show_main_app(self):
        # Tạo và hiển thị màn hình chính của ứng dụng
        self.main_app = MainApp(self.user_info)
        self.main_app.show()
        self.close()

class MainApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.setWindowTitle("Ứng Dụng Dịch")
        self.setMinimumSize(1000, 700)
        self.user_info = user_info or {}
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout chính
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Tạo sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            background-color: #1a1a1a;
            padding: 20px;
            color: white;
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)
        
        # Tiêu đề sidebar
        sidebar_title = QLabel("TRANSLATE APP")
        sidebar_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #6a11cb; margin-bottom: 20px;")
        sidebar_title.setAlignment(Qt.AlignCenter)
        
        # Tạo các nút cho sidebar
        self.windows_button = QPushButton("Windows")
        self.macos_button = QPushButton("MacOS")
        self.android_button = QPushButton("Android")
        self.ios_button = QPushButton("IOS")
        
        # Thiết lập style cho các nút
        button_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: none;
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:checked {
                background-color: #6a11cb;
            }
        """
        
        self.windows_button.setStyleSheet(button_style)
        self.macos_button.setStyleSheet(button_style)
        self.android_button.setStyleSheet(button_style)
        self.ios_button.setStyleSheet(button_style)
        
        # Kết nối các nút với hàm xử lý
        self.windows_button.clicked.connect(lambda: self.show_content("Windows"))
        self.macos_button.clicked.connect(lambda: self.show_content("MacOS"))
        self.android_button.clicked.connect(lambda: self.show_content("Android"))
        self.ios_button.clicked.connect(lambda: self.show_content("IOS"))
        
        # Thêm các nút vào sidebar
        sidebar_layout.addWidget(sidebar_title)
        sidebar_layout.addWidget(self.windows_button)
        sidebar_layout.addWidget(self.macos_button)
        sidebar_layout.addWidget(self.android_button)
        sidebar_layout.addWidget(self.ios_button)
        
        # Thêm khoảng trống
        sidebar_layout.addStretch()
        
        # Hiển thị thông tin người dùng
        if self.user_info:
            user_info_label = QLabel(f"Xin chào, {self.user_info.get('name', 'Người dùng')}")
            user_info_label.setStyleSheet("color: white; font-size: 14px; margin-top: 20px;")
            sidebar_layout.addWidget(user_info_label)
            
            # Hiển thị loại thiết bị
            device_info_label = QLabel(f"Thiết bị: {self.user_info.get('os_type', 'Không xác định')}")
            device_info_label.setStyleSheet("color: #aaa; font-size: 12px;")
            sidebar_layout.addWidget(device_info_label)
        
        # Nút đăng xuất
        logout_button = QPushButton("Đăng xuất")
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                padding: 10px;
                margin-top: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        logout_button.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_button)
        
        # Tạo khu vực nội dung
        self.content_area = QWidget()
        self.content_area.setStyleSheet("""
            background-color: #121212;
            padding: 20px;
        """)
        
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Thêm sidebar và khu vực nội dung vào layout chính
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)
        
        # Hiển thị nội dung dựa trên loại thiết bị
        os_type = self.user_info.get('os_type', 'Windows')
        self.show_content(os_type)
    
    def show_content(self, content_type):
        # Xóa nội dung hiện tại
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Đặt trạng thái cho các nút
        self.windows_button.setChecked(content_type == "Windows")
        self.macos_button.setChecked(content_type == "MacOS")
        self.android_button.setChecked(content_type == "Android")
        self.ios_button.setChecked(content_type == "IOS")
        
        # Tiêu đề
        title_label = QLabel(f"{content_type}")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #6a11cb; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Nội dung
        content_label = QLabel(f"Đây là nội dung cho {content_type}")
        content_label.setStyleSheet("font-size: 18px; color: white;")
        content_label.setAlignment(Qt.AlignCenter)
        
        # Thêm các widget vào layout
        self.content_layout.addWidget(title_label)
        self.content_layout.addWidget(content_label)
        self.content_layout.addStretch()
    
    def logout(self):
        # Xử lý đăng xuất
        reply = QMessageBox.question(self, 'Đăng xuất', 
                                     'Bạn có chắc chắn muốn đăng xuất?',
                                     QMessageBox.Yes | QMessageBox.No, 
                                     QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Cập nhật trạng thái offline
            if hasattr(self, 'user_info') and self.user_info and 'account' in self.user_info:
                try:
                    requests.post('https://web-production-baac.up.railway.app/update_user_info', json={
                        'account': self.user_info['account'],
                        'online_status': 'Offline'
                    })
                    print(f"Đã cập nhật trạng thái offline cho tài khoản: {self.user_info['account']}")
                except Exception as e:
                    print(f"Lỗi khi cập nhật trạng thái offline: {str(e)}")
            
            # Quay lại màn hình đăng nhập
            from translate_windows import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Thiết lập font chung
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Thiết lập style chung
    app.setStyle("Fusion")
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec_())
