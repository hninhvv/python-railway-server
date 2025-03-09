import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
import time

class BotMD5(QThread):
    new_result_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.last_result = None
        self.running = True
        
    def get_latest_result(self):
        """Lấy kết quả mới nhất từ website"""
        try:
            with open('md5.txt', 'r') as file:
                url = file.read().strip()
            
            results = pd.read_html(url, match="Kỳ mở thưởng")[0]
            latest = results.iloc[0]
            
            dice_result = str(latest.iloc[1]).strip()
            time_result = str(latest.iloc[2]).strip()
            
            try:
                total = sum(int(num) for num in dice_result.split())
                tai_xiu = "Tài" if total >= 11 else "Xỉu"
            except:
                total = "N/A"
                tai_xiu = "N/A"
            
            return {
                'dice': dice_result,
                'total': total,
                'tai_xiu': tai_xiu,
                'time': time_result
            }
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu mới: {e}")
            return None
            
    def run(self):
        while self.running:
            try:
                current_result = self.get_latest_result()
                
                if current_result:
                    if (self.last_result is None or 
                        current_result['time'] != self.last_result['time']):
                        self.last_result = current_result
                        self.new_result_signal.emit(current_result)
            except Exception as e:
                print(f"Lỗi trong vòng lặp bot: {e}")
            
            time.sleep(1)
            
    def stop(self):
        self.running = False