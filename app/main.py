import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from app.ui.main_window import MainWindow
from app.config import Config
import asyncio
import threading

def run_async_loop(loop):
    """Запуск асинхронного цикла в отдельном потоке."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

def main():
    root = tk.Tk()
    loop = asyncio.new_event_loop()
    threading.Thread(target=run_async_loop, args=(loop,), daemon=True).start()
    app = MainWindow(root, Config(), loop)
    root.mainloop()

if __name__ == "__main__":
    main()