import os
import time
from tqdm import tqdm

def timing_decorator(func):
    """Декоратор для замера времени выполнения функции."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Время выполнения {func.__name__}: {end_time - start_time:.4f} секунд")
        return result
    return wrapper

def list_files_by_extension(start_path, extensions):
    """Список файлов с указанными расширениями в директории."""
    all_files = []
    for root, _, files in os.walk(start_path):
        for file in files:
            if file.lower().endswith(tuple(extensions)):
                all_files.append(os.path.join(root, file))
    return sorted(all_files)

def list_files_with_progress(start_path, extensions):
    """Список файлов с прогресс-баром."""
    all_files = []
    file_count = sum(
        len([f for f in files if f.lower().endswith(tuple(extensions))])
        for _, _, files in os.walk(start_path)
    )
    with tqdm(total=file_count, desc="Сканирование файлов", unit="file") as pbar:
        for root, _, files in os.walk(start_path):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    all_files.append(os.path.join(root, file))
                    pbar.update(1)
    return sorted(all_files)