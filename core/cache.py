import os
import hashlib

class Cache:
    """Система кэширования для хранения результатов обработки."""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, file_path):
        """Генерация уникального ключа для файла."""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def load(self, file_path):
        """Загрузка данных из кэша."""
        cache_key = self.get_cache_key(file_path)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.txt")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def save(self, file_path, data):
        """Сохранение данных в кэш."""
        cache_key = self.get_cache_key(file_path)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.txt")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(data)