import os

class Config:
    """Централизованная конфигурация для приложения семантического поиска."""
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    DATA_DIR = os.path.join(BASE_DIR, "data")
    INDEX_FILE = os.path.join(DATA_DIR, "indexed_data.pkl")
    IMAGE_DB = os.path.join(DATA_DIR, "images.db")
    VIDEO_DB = os.path.join(DATA_DIR, "videos.db")
    MUSIC_DB = os.path.join(DATA_DIR, "music.db")
    CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
    HISTORY_FILE = os.path.join(DATA_DIR, "search_history.json")
    CACHE_DIR = os.path.join(DATA_DIR, "cache")
    
    TEXT_EXTENSIONS = [".docx", ".odt", ".txt", ".pdf", ".csv"]
    IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"]
    VIDEO_EXTENSIONS = [".mp4"]
    MUSIC_EXTENSIONS = [".mp3"]
    
    MODEL_NAMES = {
        "text": "roberta-base-nli-stsb-mean-tokens",
        "image": "Salesforce/blip-image-captioning-base",
        "whisper": "base"
    }
    
    os.makedirs(DATA_DIR, exist_ok=True)