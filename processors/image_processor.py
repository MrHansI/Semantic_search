import os
from PIL import Image
import sqlite3
import numpy as np
from core.models import ModelManager
from core.database import Database
from core.cache import Cache
from core.utils import list_files_with_progress
from pdf2image import convert_from_path
from deep_translator import GoogleTranslator
from numba import njit
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer

@njit
def fast_cosine_similarity(a, b):
    """Быстрое вычисление косинусного сходства с Numba."""
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b)

class ImageProcessor:
    """Обработка изображений для семантического поиска с улучшенной точностью."""
    
    def __init__(self, model_manager: ModelManager, db_path: str):
        self.model = model_manager
        self.db = Database(db_path)
        self.cache = Cache(db_path.replace(".db", "_cache"))
        self.default_extensions = [".png", ".jpg", ".jpeg", ".pdf"]
        self.translator = GoogleTranslator(source='auto', target='en')

    def resize_image(self, image, max_size=512):
        """Изменение размера изображения."""
        width, height = image.size
        if width > max_size or height > max_size:
            image.thumbnail((max_size, max_size))
        return image
    
    def split_image(self, image):
        """Разделение изображения на 4 части."""
        width, height = image.size
        return [
            image.crop((0, 0, width // 2, height // 2)),
            image.crop((width // 2, 0, width, height // 2)),
            image.crop((0, height // 2, width // 2, height)),
            image.crop((width // 2, height // 2, width, height))
        ]
    
    def generate_description(self, image_path):
        """Генерация описания изображения."""
        cached_desc = self.cache.load(image_path)
        if cached_desc:
            return cached_desc
        
        image = self.resize_image(Image.open(image_path).convert("RGB"))
        areas = self.split_image(image)
        captions = self.model.generate_image_captions(areas, max_length=100, num_beams=5)
        description = " ".join(captions)
        self.cache.save(image_path, description)
        return description

    def pdf_to_images(self, pdf_path, output_folder="temp_images"):
        """Конвертация PDF в изображения."""
        os.makedirs(output_folder, exist_ok=True)
        images = convert_from_path(pdf_path)

        def process_image(i, image):
            image_path = os.path.join(output_folder, f"{os.path.basename(pdf_path)}_page_{i + 1}.jpg")
            image.save(image_path, "JPEG")
            return image_path

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_image, i, image) for i, image in enumerate(images)]
            output_paths = [future.result() for future in futures]
        return output_paths

    def process_file(self, file_path):
        """Обработка одного файла (изображение или PDF)."""
        if file_path.lower().endswith(".pdf"):
            pdf_images = self.pdf_to_images(file_path)
            for img_path in pdf_images:
                description = self.generate_description(img_path)
                # Используем roberta-base-nli-stsb-mean-tokens для точности
                embedding = SentenceTransformer('roberta-base-nli-stsb-mean-tokens').encode([description])[0]
                self.db.add_entry(img_path, description, embedding)
        else:
            description = self.generate_description(file_path)
            embedding = SentenceTransformer('roberta-base-nli-stsb-mean-tokens').encode([description])[0]
            self.db.add_entry(file_path, description, embedding)

    def index_files(self, directory):
        """Индексация файлов в указанной директории."""
        files = list_files_with_progress(directory, self.default_extensions)
        for file_path in files:
            self.process_file(file_path)

    def list_files_with_progress(self, directory, extensions):
        """Список файлов с прогресс-баром."""
        return list_files_with_progress(directory, extensions)

    def search(self, query, top_k=5):
        """Поиск по текстовому запросу с переводом на английский."""
        translated_query = self.translator.translate(query)
        query_embedding = SentenceTransformer('roberta-base-nli-stsb-mean-tokens').encode([translated_query])[0]
        
        # Ручной поиск для использования fast_cosine_similarity
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT path, description, embedding FROM entries")
            results = []
            for path, desc, emb_bytes in cursor.fetchall():
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                similarity = fast_cosine_similarity(query_embedding, emb)
                results.append((path, desc, similarity, None))
            return sorted(results, key=lambda x: x[2], reverse=True)[:top_k]