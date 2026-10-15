print("Loading model...")

from transformers import pipeline

classifier = pipeline("sentiment-analysis",
model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")

print("Model loaded!")