import os
from core.models import ModelManager
from core.database import Database
from core.utils import list_files_with_progress
from odf.opendocument import load
from odf.text import P

class TextProcessor:
    """Обработка текстовых данных для семантического поиска."""
    
    def __init__(self, model_manager: ModelManager, db_path: str):
        self.model = model_manager
        self.db = Database(db_path)
        self.default_extensions = [".odt", ".txt", ".docx", ".pdf", ".csv"]

    def extract_text_from_odt(self, file_path):
        """Извлечение текста из .odt файла."""
        try:
            doc = load(file_path)
            paragraphs = doc.getElementsByType(P)
            text = []
            for para in paragraphs:
                text_nodes = para.childNodes
                para_text = "".join([node.data for node in text_nodes if node.nodeType == node.TEXT_NODE])
                if para_text.strip():
                    text.append(para_text)
            return "\n".join(text)
        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")
            return ""

    def process_file(self, file_path):
        """Обработка одного текстового файла."""
        if file_path.lower().endswith(".odt"):
            text = self.extract_text_from_odt(file_path)
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"Ошибка чтения файла {file_path}: {e}")
                return
        
        sentences = [s.strip() for s in text.split("\n") if s.strip()]
        if sentences:
            embeddings = self.model.encode_text(sentences)
            for sentence, embedding in zip(sentences, embeddings):
                unique_path = f"{file_path}#{hash(sentence)}"
                self.db.add_entry(unique_path, sentence, embedding)

    def index_files(self, directory, extensions):
        """Индексация текстовых файлов в указанной директории."""
        files = list_files_with_progress(directory, extensions)
        for file_path in files:
            self.process_file(file_path)

    def list_files_with_progress(self, directory, extensions):
        """Список файлов с прогресс-баром."""
        return list_files_with_progress(directory, extensions)

    def search(self, query, top_k=5):
        """Поиск по текстовому запросу."""
        query_embedding = self.model.encode_text([query])[0]
        results = self.db.search(query_embedding, top_k)
        return [(path.split("#")[0], desc, sim, None) for path, desc, sim, _ in results]
    
    def get_snippet(self, file_path, matched_text, snippet_length=200):
        """Получение текстового фрагмента вокруг совпадения."""
        full_text = ""
        if file_path.lower().endswith(".odt"):
            full_text = self.extract_text_from_odt(file_path)
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    full_text = f.read()
            except Exception as e:
                full_text = matched_text
        
        pos = full_text.lower().find(matched_text.lower())
        if pos == -1:
            pos = 0
        start = max(0, pos - snippet_length // 2)
        end = min(len(full_text), pos + snippet_length // 2 + len(matched_text))
        snippet = full_text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(full_text):
            snippet += "..."
        return snippet