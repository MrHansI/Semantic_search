from sentence_transformers import SentenceTransformer
from transformers import BlipProcessor, BlipForConditionalGeneration
import whisper
import torch

class ModelManager:
    def __init__(self, config):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Используемое устройство: {self.device}")
        
        self.text_model = SentenceTransformer(config.MODEL_NAMES["text"]).to(self.device)
        self.blip_processor = BlipProcessor.from_pretrained(config.MODEL_NAMES["image"])
        self.blip_model = BlipForConditionalGeneration.from_pretrained(config.MODEL_NAMES["image"]).to(self.device)
        self.whisper_model = whisper.load_model(config.MODEL_NAMES["whisper"])
    
    def encode_text(self, texts, batch_size=32):
        return self.text_model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
    
    def generate_image_captions(self, images, max_length=100, num_beams=5):
        inputs = self.blip_processor(images=images, return_tensors="pt").to(self.device)
        outputs = self.blip_model.generate(**inputs, max_length=max_length, num_beams=num_beams, early_stopping=True)
        return self.blip_processor.batch_decode(outputs, skip_special_tokens=True)
    
    def transcribe_audio(self, audio_path):
        return self.whisper_model.transcribe(audio_path, language="ru")["text"]
    
    def fine_tune_text_model(self, examples, output_path, epochs=1, batch_size=8):
        from sentence_transformers import InputExample, losses
        from torch.utils.data import DataLoader
        
        train_dataloader = DataLoader(examples, shuffle=True, batch_size=batch_size)
        train_loss = losses.CosineSimilarityLoss(self.text_model)
        
        self.text_model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=50,
            output_path=output_path
        )
        self.text_model = SentenceTransformer(output_path).to(self.device)
        return self.text_model