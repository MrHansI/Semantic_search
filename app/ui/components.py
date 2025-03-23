import tkinter as tk
from tkinter import scrolledtext

class HistoryComponent:
    """Компонент истории поиска."""
    
    def __init__(self, parent, theme, on_select_callback):
        self.theme = theme
        self.on_select_callback = on_select_callback
        self.history = []
        
        self.frame = tk.Frame(parent, bg=theme.get_bg_color())
        tk.Label(
            self.frame,
            text="История поиска:",
            font=("Arial", 12),
            bg=theme.get_bg_color(),
            fg=theme.get_fg_color()
        ).pack(anchor=tk.NE)
        
        self.listbox = tk.Listbox(
            self.frame,
            height=5,
            width=30,
            font=("Arial", 12),
            bg=theme.get_result_bg(),
            fg=theme.get_result_fg()
        )
        self.listbox.pack(pady=2)
        self.listbox.bind("<Double-1>", self._on_double_click)
        
        self.buttons_frame = tk.Frame(self.frame, bg=theme.get_bg_color())
        self.buttons_frame.pack(fill=tk.X)
        
        self.count_label = tk.Label(
            self.buttons_frame,
            text="Всего запросов: 0",
            font=("Arial", 10),
            bg=theme.get_bg_color(),
            fg=theme.get_fg_color()
        )
        self.count_label.pack(side=tk.LEFT)
        
        self.view_all_button = tk.Button(
            self.buttons_frame,
            text="Все",
            command=self._show_full_history,
            bg=theme.get_button_bg(),
            fg=theme.get_button_fg(),
            font=("Arial", 10)
        )
        self.view_all_button.pack(side=tk.RIGHT, padx=2)
        
        self.clear_button = tk.Button(
            self.buttons_frame,
            text="Очистить",
            command=self.clear,
            bg=theme.get_button_bg(),
            fg=theme.get_button_fg(),
            font=("Arial", 10)
        )
        self.clear_button.pack(side=tk.RIGHT, padx=2)

    def update(self, history):
        """Обновление списка истории."""
        self.history = history
        self.listbox.delete(0, tk.END)
        for query in history[:5]:
            self.listbox.insert(tk.END, query)
        self.count_label.config(text=f"Всего запросов: {len(history)}")

    def clear(self):
        """Очистка истории."""
        self.history = []
        self.update([])

    def _on_double_click(self, event):
        """Обработка двойного клика по элементу истории."""
        selection = self.listbox.curselection()
        if selection:
            query = self.listbox.get(selection[0])
            self.on_select_callback(query)

    def _show_full_history(self):
        """Показ полной истории в новом окне."""
        window = tk.Toplevel()
        window.title("Полная история поиска")
        window.geometry("400x500")
        
        text = scrolledtext.ScrolledText(
            window,
            wrap=tk.WORD,
            font=("Arial", 12),
            bg=self.theme.get_result_bg(),
            fg=self.theme.get_result_fg()
        )
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for i, query in enumerate(self.history, 1):
            text.insert(tk.END, f"{i}. {query}\n")
        
        tk.Button(
            window,
            text="Закрыть",
            command=window.destroy,
            bg=self.theme.get_button_bg(),
            fg=self.theme.get_button_fg()
        ).pack(pady=5)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)