import tkinter as tk
from tkinter import font

class SimpleApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Học Online Tiếng Anh')
        self.root.geometry('300x200')
        self.root.configure(bg='#f0f0f0')  # Màu nền

        # Tạo font chữ
        self.custom_font = font.Font(family='Helvetica', size=12, weight='bold')

        self.button = tk.Button(self.root, text='Click Me!', command=self.on_button_click,
                                 bg='#4CAF50', fg='white', font=self.custom_font, padx=10, pady=5)
        self.button.pack(pady=50)

    def on_button_click(self):
        print('Button clicked!')

if __name__ == '__main__':
    root = tk.Tk()
    app = SimpleApp(root)
    root.mainloop()
