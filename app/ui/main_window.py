import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from app.ui.theme import Theme
from app.ui.components import HistoryComponent
from core.models import ModelManager
from processors.text_processor import TextProcessor
from processors.image_processor import ImageProcessor
from processors.video_processor import VideoProcessor
from processors.music_processor import MusicProcessor
import json
import os
import asyncio
from queue import Queue
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

class MainWindow:
    """Основное окно приложения семантического поиска с асинхронной обработкой."""
    
    def __init__(self, root, config, async_loop):
        self.root = root
        self.config = config
        self.async_loop = async_loop  # Цикл asyncio для асинхронных задач
        self.root.title("Semantic Search")
        self.root.geometry("1300x800")
        
        self.theme = Theme(self._load_theme_config())
        self.model_manager = ModelManager(config)
        
        self.text_processor = TextProcessor(self.model_manager, config.INDEX_FILE)
        self.image_processor = ImageProcessor(self.model_manager, config.IMAGE_DB)
        self.video_processor = VideoProcessor(self.model_manager, config.VIDEO_DB)
        self.music_processor = MusicProcessor(self.model_manager, config.MUSIC_DB)
        
        self.scan_dirs = {"text": "", "image": "", "video": "", "music": ""}
        self.image_buttons = []
        self.task_queue = Queue()  # Очередь для обновления UI из асинхронных задач
        
        self.setup_ui()
        self.root.after(100, self._check_queue)  # Периодическая проверка очереди

    def _load_theme_config(self):
        if os.path.exists(self.config.CONFIG_FILE):
            with open(self.config.CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("is_dark_mode", False)
        return False

    def _save_theme_config(self):
        config = {"is_dark_mode": self.theme.is_dark_mode}
        with open(self.config.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def setup_ui(self):
        self.root.configure(bg=self.theme.get_bg_color())
        
        # Header
        self.header_frame = tk.Frame(self.root, bg=self.theme.get_accent_color(), height=60)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        tk.Label(
            self.header_frame,
            text="Semantic Search",
            font=("Arial", 20, "bold"),
            bg=self.theme.get_accent_color(),
            fg=self.theme.get_fg_color()
        ).pack(side=tk.LEFT, padx=20)
        self.theme_button = tk.Button(
            self.header_frame,
            text="Светлая тема" if self.theme.is_dark_mode else "Тёмная тема",
            command=self._toggle_theme,
            bg=self.theme.get_button_bg(),
            fg=self.theme.get_button_fg(),
            font=("Arial", 12),
            relief=tk.FLAT
        )
        self.theme_button.pack(side=tk.RIGHT, padx=20)
        
        # Body
        self.body_frame = tk.Frame(self.root, bg=self.theme.get_bg_color())
        self.body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Query Section
        self.query_section = tk.Frame(self.body_frame, bg=self.theme.get_bg_color())
        self.query_section.pack(fill=tk.X, pady=10)
        
        self.history_component = HistoryComponent(self.query_section, self.theme, self._use_history_query)
        self.history_component.pack(side=tk.RIGHT, padx=10)
        self.history_component.update(self._load_search_history())
        
        tk.Label(
            self.query_section,
            text="Введите поисковой запрос:",
            font=("Arial", 14),
            bg=self.theme.get_bg_color(),
            fg=self.theme.get_fg_color()
        ).pack(side=tk.LEFT, padx=10)
        
        self.query_entry = tk.Entry(
            self.query_section,
            width=50,
            font=("Arial", 14),
            relief=tk.FLAT,
            borderwidth=2
        )
        self.query_entry.pack(side=tk.LEFT, padx=10, ipady=5)
        
        self.search_buttons = []
        for text, cmd in [
            ("Поиск текста", lambda: self._perform_async_search(self.text_processor, self._display_text_results)),
            ("Поиск изображений", lambda: self._perform_async_search(self.image_processor, self._display_images)),
            ("Поиск видео", lambda: self._perform_async_search(self.video_processor, self._display_videos)),
            ("Поиск музыки", lambda: self._perform_async_search(self.music_processor, self._display_music_results))
        ]:
            btn = tk.Button(
                self.query_section,
                text=text,
                command=cmd,
                bg=self.theme.get_button_bg(),
                fg=self.theme.get_button_fg(),
                font=("Arial", 12),
                relief=tk.FLAT,
                padx=15,
                pady=5
            )
            btn.pack(side=tk.LEFT, padx=10)
            self.search_buttons.append(btn)
        
        # Results Section
        self.results_section = tk.Frame(self.body_frame, bg=self.theme.get_bg_color())
        self.results_section.pack(fill=tk.BOTH, expand=True)
        self.results_text = scrolledtext.ScrolledText(
            self.results_section,
            wrap=tk.WORD,
            font=("Arial", 14),
            bg=self.theme.get_result_bg(),
            fg=self.theme.get_result_fg(),
            relief=tk.FLAT,
            borderwidth=5
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Progress Bar
        self.progress_frame = tk.Frame(self.body_frame, bg=self.theme.get_bg_color())
        self.progress_frame.pack(fill=tk.X, pady=5)
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Прогресс:",
            bg=self.theme.get_bg_color(),
            fg=self.theme.get_fg_color(),
            font=("Arial", 12)
        )
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            length=400,
            mode="determinate"
        )
        self.progress_bar.pack(side=tk.LEFT, padx=10)
        
        # Script Section
        self.script_section = tk.Frame(self.body_frame, bg=self.theme.get_bg_color())
        self.script_section.pack(fill=tk.X, pady=10)
        
        self.param_frames = {}
        self.dir_buttons = {}
        self.run_buttons = {}
        for name, title, select_cmd, run_cmd in [
            ("text", "Параметры текстовых файлов", self._select_text_dir, lambda: self._run_async_indexing(self.text_processor, "text")),
            ("image", "Параметры изображений", self._select_image_dir, lambda: self._run_async_indexing(self.image_processor, "image")),
            ("video", "Параметры видео", self._select_video_dir, lambda: self._run_async_indexing(self.video_processor, "video")),
            ("music", "Параметры музыки", self._select_music_dir, lambda: self._run_async_indexing(self.music_processor, "music"))
        ]:
            frame = tk.LabelFrame(
                self.script_section,
                text=title,
                bg=self.theme.get_bg_color(),
                fg=self.theme.get_fg_color(),
                font=("Arial", 12)
            )
            frame.pack(fill=tk.X, pady=5, padx=5)
            self.param_frames[name] = frame
            
            dir_btn = tk.Button(
                frame,
                text=f"Выбрать директорию для {name}",
                command=select_cmd,
                bg=self.theme.get_button_bg(),
                fg=self.theme.get_button_fg(),
                font=("Arial", 12)
            )
            dir_btn.pack(side=tk.LEFT, padx=10, pady=5)
            self.dir_buttons[name] = dir_btn
            
            setattr(self, f"{name}_dir_label", tk.Label(
                frame,
                text="Директория не выбрана",
                bg=self.theme.get_bg_color(),
                fg=self.theme.get_fg_color(),
                font=("Arial", 12)
            ))
            getattr(self, f"{name}_dir_label").pack(side=tk.LEFT, padx=10)
            
            if name == "text":
                self.text_ext_label = tk.Label(
                    frame,
                    text="Расширения (через запятую):",
                    bg=self.theme.get_bg_color(),
                    fg=self.theme.get_fg_color(),
                    font=("Arial", 12)
                )
                self.text_ext_label.pack(side=tk.LEFT, padx=10)
                self.text_ext_entry = tk.Entry(frame, width=30, font=("Arial", 12))
                self.text_ext_entry.pack(side=tk.LEFT, padx=10)
                self.text_ext_entry.insert(0, ",".join(self.config.TEXT_EXTENSIONS))
            
            run_btn = tk.Button(
                frame,
                text=f"Запустить индексирование {name}",
                command=run_cmd,
                bg=self.theme.get_button_bg(),
                fg=self.theme.get_button_fg(),
                font=("Arial", 12)
            )
            run_btn.pack(side=tk.LEFT, padx=10, pady=5)
            self.run_buttons[name] = run_btn
        
        # Footer
        self.footer_frame = tk.Frame(self.root, bg=self.theme.get_accent_color(), height=40)
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.footer_label = tk.Label(
            self.footer_frame,
            text="© 2025 Semantic Search",
            font=("Arial", 10),
            bg=self.theme.get_accent_color(),
            fg=self.theme.get_fg_color()
        )
        self.footer_label.pack(side=tk.RIGHT, padx=20)

    def _check_queue(self):
        """Проверка очереди для обновления UI."""
        while not self.task_queue.empty():
            action, value = self.task_queue.get()
            if action == "progress":
                self.progress_bar["value"] = value
            elif action == "complete":
                messagebox.showinfo("Информация", value)
                self.progress_bar["value"] = 0
            elif action == "search_results":
                value[0](value[1])  # Вызов функции отображения с результатами
        self.root.after(100, self._check_queue)

    def _toggle_theme(self):
        self.theme.toggle()
        self.theme_button.config(text="Светлая тема" if self.theme.is_dark_mode else "Тёмная тема")
        self._update_theme()
        self._save_theme_config()

    def _update_theme(self):
        self.root.configure(bg=self.theme.get_bg_color())
        for frame in [self.header_frame, self.footer_frame]:
            frame.configure(bg=self.theme.get_accent_color())
        for frame in [self.body_frame, self.query_section, self.results_section, self.progress_frame, self.script_section]:
            frame.configure(bg=self.theme.get_bg_color())
        self.results_text.configure(bg=self.theme.get_result_bg(), fg=self.theme.get_result_fg())
        
        for btn in self.search_buttons:
            btn.configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())
        
        for name in self.param_frames:
            self.param_frames[name].configure(bg=self.theme.get_bg_color(), fg=self.theme.get_fg_color())
            self.dir_buttons[name].configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())
            getattr(self, f"{name}_dir_label").configure(bg=self.theme.get_bg_color(), fg=self.theme.get_fg_color())
            self.run_buttons[name].configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())
        
        if hasattr(self, "text_ext_label"):
            self.text_ext_label.configure(bg=self.theme.get_bg_color(), fg=self.theme.get_fg_color())
        
        self.theme_button.configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())
        self.footer_label.configure(bg=self.theme.get_accent_color(), fg=self.theme.get_fg_color())
        self.progress_label.configure(bg=self.theme.get_bg_color(), fg=self.theme.get_fg_color())
        
        self.history_component.frame.configure(bg=self.theme.get_bg_color())
        self.history_component.listbox.configure(bg=self.theme.get_result_bg(), fg=self.theme.get_result_fg())
        self.history_component.buttons_frame.configure(bg=self.theme.get_bg_color())
        self.history_component.count_label.configure(bg=self.theme.get_bg_color(), fg=self.theme.get_fg_color())
        self.history_component.view_all_button.configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())
        self.history_component.clear_button.configure(bg=self.theme.get_button_bg(), fg=self.theme.get_button_fg())

    def _select_dir(self, name):
        dir_path = filedialog.askdirectory(title=f"Выберите директорию для {name}")
        if dir_path:
            self.scan_dirs[name] = dir_path
            getattr(self, f"{name}_dir_label").config(text=dir_path)

    _select_text_dir = lambda self: self._select_dir("text")
    _select_image_dir = lambda self: self._select_dir("image")
    _select_video_dir = lambda self: self._select_dir("video")
    _select_music_dir = lambda self: self._select_dir("music")

    async def _async_index(self, processor, name, directory, extensions=None):
        """Асинхронная индексация файлов."""
        files = processor.list_files_with_progress(directory, extensions or processor.default_extensions)
        total_files = len(files)
        for i, file_path in enumerate(files):
            processor.process_file(file_path)
            progress = (i + 1) / total_files * 100
            self.task_queue.put(("progress", progress))
            await asyncio.sleep(0.01)  # Позволяет UI обновляться
        self.task_queue.put(("complete", f"Индексация {name} завершена."))

    def _run_async_indexing(self, processor, name):
        if not self.scan_dirs[name]:
            messagebox.showwarning("Предупреждение", f"Сначала выберите директорию для {name}")
            return
        extensions = None
        if name == "text":
            extensions = [ext.strip() for ext in self.text_ext_entry.get().split(",")]
        asyncio.run_coroutine_threadsafe(
            self._async_index(processor, name, self.scan_dirs[name], extensions),
            self.async_loop
        )

    async def _async_search(self, processor, query, display_method, top_k=5):
        """Асинхронный поиск."""
        results = processor.search(query, top_k)
        self.task_queue.put(("search_results", (display_method, results)))

    def _perform_async_search(self, processor, display_method):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Предупреждение", "Введите поисковой запрос.")
            return
        self._save_search_history(query)
        asyncio.run_coroutine_threadsafe(
            self._async_search(processor, query, display_method),
            self.async_loop
        )

    def _load_search_history(self):
        if os.path.exists(self.config.HISTORY_FILE):
            with open(self.config.HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_search_history(self, query):
        history = self._load_search_history()
        if query and query not in history:
            history.insert(0, query)
            with open(self.config.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f)
        self.history_component.update(history)

    def _use_history_query(self, query):
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, query)

    def _display_text_results(self, results):
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, "Результаты поиска текста:\n\n")
        for i, (path, sentence, score, _) in enumerate(results, 1):
            score_percent = score * 100
            similarity_level = (
                "очень высокая" if score_percent > 90 else
                "высокая" if score_percent > 80 else
                "средняя" if score_percent > 70 else
                "низкая"
            )
            info_text = (f"{i}. Файл: {path}\n"
                        f"   Предложение: \"{sentence}\"\n"
                        f"   Схожесть: {score_percent:.2f}% ({similarity_level})\n")
            self.results_text.insert(tk.END, info_text)
            btn = tk.Button(
                self.results_text,
                text="Открыть",
                command=lambda s=sentence, p=path: self._open_text_window(s, p),
                bg=self.theme.get_button_bg(),
                fg=self.theme.get_button_fg()
            )
            self.results_text.window_create(tk.END, window=btn)
            self.results_text.insert(tk.END, "\n\n")

    def _display_music_results(self, results):
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, "Результаты поиска музыки:\n\n")
        for i, (path, desc, sim, _) in enumerate(results, 1):
            info_text = (f"{i}. Файл: {path}\n"
                        f"   Описание: {desc}\n"
                        f"   Схожесть: {sim:.2%}\n")
            self.results_text.insert(tk.END, info_text)
            btn = tk.Button(
                self.results_text,
                text="Открыть папку",
                command=lambda p=path: os.startfile(os.path.dirname(p)) if os.name == "nt" else os.system(f"open {os.path.dirname(p)}"),
                bg=self.theme.get_button_bg(),
                fg=self.theme.get_button_fg()
            )
            self.results_text.window_create(tk.END, window=btn)
            self.results_text.insert(tk.END, "\n\n")

    def _display_images(self, results):
        self.image_buttons = []
        fig = plt.figure(figsize=(15, 10))
        for i, (path, desc, sim, _) in enumerate(results):
            ax = fig.add_subplot(2, 3, i+1)
            try:
                img = plt.imread(path)
                ax.imshow(img)
                ax.set_title(f"{desc[:30]}...\n(Схожесть: {sim:.2%})", fontsize=10)
                ax.axis("off")
                ax_button = ax.inset_axes([0.75, 0.8, 0.25, 0.15])
                btn = Button(ax_button, "Папка", color="lightgray", hovercolor="gray")
                btn.on_clicked(lambda event, p=path: self._open_directory(p))
                self.image_buttons.append(btn)
            except Exception as e:
                print(f"Ошибка отображения {path}: {e}")
        plt.tight_layout()
        plt.show()

    def _display_videos(self, results):
        self.image_buttons = []
        fig = plt.figure(figsize=(15, 10))
        for i, (path, desc, sim, keyframe) in enumerate(results):
            ax = fig.add_subplot(2, 3, i+1)
            try:
                img = plt.imread(keyframe)
                ax.imshow(img)
                ax.set_title(f"{desc[:30]}...\n(Схожесть: {sim:.2%})", fontsize=10)
                ax.axis("off")
                ax_button = ax.inset_axes([0.75, 0.8, 0.25, 0.15])
                btn = Button(ax_button, "Папка", color="lightgray", hovercolor="gray")
                btn.on_clicked(lambda event, p=path: self._open_directory(p))
                self.image_buttons.append(btn)
            except Exception as e:
                print(f"Ошибка отображения {path}: {e}")
        plt.tight_layout()
        plt.show()

    def _open_text_window(self, sentence, file_path):
        snippet = self.text_processor.get_snippet(file_path, sentence)
        window = tk.Toplevel(self.root)
        window.title(f"Фрагмент из {os.path.basename(file_path)}")
        window.geometry("800x600")
        text = scrolledtext.ScrolledText(window, wrap=tk.WORD, font=("Arial", 14))
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, snippet)
        text.tag_config("highlight", background="yellow")
        pos = "1.0"
        query = self.query_entry.get().strip()
        while True:
            idx = text.search(query, pos, tk.END, nocase=1)
            if not idx:
                break
            lastidx = f"{idx}+{len(query)}c"
            text.tag_add("highlight", idx, lastidx)
            pos = lastidx
        tk.Button(
            window,
            text="Закрыть",
            command=window.destroy,
            bg=self.theme.get_button_bg(),
            fg=self.theme.get_button_fg()
        ).pack(pady=5)

    def _open_directory(self, path):
        directory = os.path.dirname(os.path.abspath(path))
        window = tk.Toplevel(self.root)
        window.title("Путь к файлу")
        window.geometry("600x100")
        tk.Label(
            window,
            text=f"Путь: {directory}",
            font=("Arial", 14),
            bg=self.theme.get_bg_color(),
            fg=self.theme.get_fg_color()
        ).pack(padx=20, pady=20)
        tk.Button(
            window,
            text="Закрыть",
            command=window.destroy,
            bg=self.theme.get_button_bg(),
            fg=self.theme.get_button_fg()
        ).pack(pady=10)