import json
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

print("Начинаем обучение модели")

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

texts = [item['text'] for item in data]
intents = [item['intent'] for item in data]

model = make_pipeline(TfidfVectorizer(), LogisticRegression())

model.fit(texts, intents)

with open('intent_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Модель успешно обучена и сохранена в 'intent_model.pkl")