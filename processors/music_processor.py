import os
from mutagen.mp3 import MP3
from core.models import ModelManager
from core.database import Database
from core.utils import list_files_with_progress
from sentence_transformers import InputExample

class MusicProcessor:
    """Обработка музыкальных файлов для семантического поиска."""
    
    def __init__(self, model_manager: ModelManager, db_path: str):
        self.model = model_manager
        self.db = Database(db_path)
        self.default_extensions = [".mp3"]

    def extract_metadata(self, mp3_path):
        """Извлечение метаданных из mp3."""
        try:
            audio = MP3(mp3_path)
            return {
                "title": str(audio.get("TIT2", "Unknown Title")),
                "artist": str(audio.get("TPE1", "Unknown Artist")),
                "album": str(audio.get("TALB", "Unknown Album")),
                "genre": str(audio.get("TCON", "Unknown Genre"))
            }
        except Exception as e:
            print(f"Ошибка обработки метаданных {mp3_path}: {e}")
            return {"title": "Unknown Title", "artist": "Unknown Artist", "album": "Unknown Album", "genre": "Unknown Genre"}
    
    def generate_description(self, mp3_path):
        """Генерация описания музыкального трека."""
        metadata = self.extract_metadata(mp3_path)
        lyrics = self.model.transcribe_audio(mp3_path)
        base_desc = f"{metadata['title']} by {metadata['artist']} from the album {metadata['album']} in the genre {metadata['genre']}"
        full_desc = f"{base_desc}. Lyrics: {lyrics[:400]}..." if lyrics else base_desc
        return full_desc, lyrics

    def process_file(self, mp3_path):
        """Обработка одного музыкального файла."""
        description, lyrics = self.generate_description(mp3_path)
        embedding = self.model.encode_text([description])[0]
        self.db.add_entry(mp3_path, description, embedding, extra=lyrics)

    def index_files(self, directory):
        """Индексация музыкальных файлов в указанной директории."""
        files = list_files_with_progress(directory, self.default_extensions)
        for mp3_path in files:
            self.process_file(mp3_path)

    def list_files_with_progress(self, directory, extensions):
        """Список файлов с прогресс-баром."""
        return list_files_with_progress(directory, extensions)

    def search(self, query, top_k=5):
        """Поиск по текстовому запросу."""
        query_embedding = self.model.encode_text([query])[0]
        return self.db.search(query_embedding, top_k)
    
    def fine_tune(self, directory, output_path="fine_tuned_model"):
        """Дообучение модели на текстах песен."""
        files = list_files_with_progress(directory, self.default_extensions)
        train_examples = []
        for mp3_path in files:
            _, lyrics = self.generate_description(mp3_path)
            if lyrics and len(lyrics) > 50:
                short_lyrics = lyrics[:200]
                train_examples.append(InputExample(texts=[lyrics, short_lyrics], label=1.0))
        
        if not train_examples:
            print("Недостаточно данных для дообучения.")
            return
        self.model.fine_tune_text_model(train_examples, output_path)