import os
import cv2
from PIL import Image
from core.models import ModelManager
from core.database import Database
from core.utils import list_files_with_progress

class VideoProcessor:
    """Обработка видео для семантического поиска."""
    
    def __init__(self, model_manager: ModelManager, db_path: str):
        self.model = model_manager
        self.db = Database(db_path)
        self.default_extensions = [".mp4"]

    def extract_keyframes(self, video_path, interval=1):
        """Извлечение ключевых кадров из видео."""
        output_folder = os.path.join(os.path.dirname(video_path), "keyframes")
        os.makedirs(output_folder, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        keyframe_paths = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % int(fps * interval) == 0:
                keyframe_path = os.path.join(output_folder, f"{os.path.basename(video_path)}_frame_{frame_count}.jpg")
                cv2.imwrite(keyframe_path, frame)
                keyframe_paths.append(keyframe_path)
            frame_count += 1
        cap.release()
        return keyframe_paths
    
    def generate_description(self, image_path):
        """Генерация описания для изображения (кадра)."""
        from processors.image_processor import ImageProcessor  # Локальный импорт
        temp_processor = ImageProcessor(self.model, self.db.db_path)
        return temp_processor.generate_description(image_path)

    def process_file(self, video_path):
        """Обработка одного видео."""
        keyframes = self.extract_keyframes(video_path)
        for keyframe in keyframes:
            description = self.generate_description(keyframe)
            embedding = self.model.encode_text([description])[0]
            self.db.add_entry(video_path, description, embedding, extra=keyframe)

    def index_files(self, directory):
        """Индексация видео в указанной директории."""
        files = list_files_with_progress(directory, self.default_extensions)
        for video_path in files:
            self.process_file(video_path)

    def list_files_with_progress(self, directory, extensions):
        """Список файлов с прогресс-баром."""
        return list_files_with_progress(directory, extensions)

    def search(self, query, top_k=5):
        """Поиск по текстовому запросу."""
        query_embedding = self.model.encode_text([query])[0]
        results = self.db.search(query_embedding, top_k * 2)
        
        video_results = {}
        for path, desc, sim, keyframe in results:
            if path not in video_results or video_results[path][2] < sim:
                video_results[path] = (path, desc, sim, keyframe)
        return list(video_results.values())[:top_k]