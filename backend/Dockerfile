FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# CPU-only PyTorch, χωρίς CUDA/NVIDIA
RUN pip install --no-cache-dir torch==2.12.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY model.py .
COPY places_service.py .
COPY foursquare_service.py .
COPY fallback_reviews.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]