# Sentiment Analysis Tool

A web application for classifying English text as positive or negative using a pretrained DistilBERT model. It also provides city weather, nearby places, and sentiment analysis of place reviews.

## Features

- Analyze English text and display the predicted sentiment and model confidence.
- Analyze multiple reviews through the API and return a sentiment summary.
- Search for a city and retrieve current weather through Open-Meteo.
- Discover nearby attractions, museums, restaurants, cafes and parks using OpenStreetMap data through Overpass.
- Request place tips from Foursquare and classify their sentiment.
- Display clearly labeled demo reviews when Foursquare data is unavailable.
- Run the backend and frontend with Docker Compose.

## Technologies

| Component | Technologies |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| NLP | Hugging Face Transformers, PyTorch, pretrained DistilBERT |
| Frontend | HTML, CSS, JavaScript |
| External services | Open-Meteo, OpenStreetMap / Overpass, Foursquare |
| Containers | Docker Compose, Nginx |

The model is `distilbert/distilbert-base-uncased-finetuned-sst-2-english`. This project uses pretrained model inference; it does not train a new model.

## Run locally

Prerequisites: Git and Docker with Docker Compose. On Windows, start Docker Desktop before running the commands. An internet connection is needed to download dependencies and model files, and to access external services.

```powershell
git clone https://github.com/T0pboyg/sentiment_analysis.git
cd sentiment_analysis
Copy-Item backend/.env.example backend/.env
docker compose up --build
```

If you already have a configured `backend/.env`, keep it instead of copying over it.

Open:

- Application: http://localhost:5500
- API documentation: http://localhost:8000/docs

The first startup downloads the model and may take longer. Model files are cached in the `huggingface-cache` Docker volume.

To stop the containers from a second terminal in the project directory:

```powershell
docker compose down
```

After editing frontend files, rebuild and refresh your browser:

```powershell
docker compose up -d --build
```

### Optional Foursquare configuration

Set your own key in `backend/.env` to request Foursquare place tips:

```dotenv
FSQ_API_KEY=your_foursquare_api_key
```

The `.env` file is excluded from Git. Never commit a real API key.

Without a configured key, or when suitable Foursquare tips cannot be retrieved, the application uses generated sample review texts. These are labeled as demo reviews in the interface and must not be interpreted as actual customer feedback. Weather and nearby-place searches still depend on their external services.

## Try it

Enter these examples separately and select **Analyze**:

- `I really enjoyed this experience. Everything was excellent!`
- `This was a terrible experience. I am very disappointed.`

Search for a city such as `Athens` to load weather and nearby places, then select **View Reviews** on a place card.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Basic API response |
| POST | `/analyze` | Classify one text; JSON body: `{"text":"I enjoyed it."}` |
| POST | `/analyze-reviews` | Analyze a list; JSON body: `{"reviews":["Great!","Disappointing."]}` |
| GET | `/weather/{city}` | Retrieve current weather |
| GET | `/places/{city}?radius=2000` | Find nearby places |
| GET | `/place-reviews?name=...&latitude=...&longitude=...` | Retrieve and analyze real or demo reviews |

## Project structure

```text
sentiment_analysis/
├── backend/
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── main.py
│   ├── model.py
│   ├── places_service.py
│   ├── foursquare_service.py
│   ├── fallback_reviews.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── app.js
│   └── style.css
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Scope and limitations

- The model is intended for English and predicts positive or negative sentiment. `MIXED` in a review summary means equal positive and negative counts, not a separate model class.
- Confidence is a model score, not a guarantee of correctness. Sarcasm and domain-specific language may be misclassified.
- External services may be unavailable, rate-limited, or return incomplete data. Matching a place to Foursquare may select an incorrect result.
- The frontend currently calls a backend on `127.0.0.1:8000`; the configuration targets local use.
- This is a portfolio prototype. Public hosting would require additional work, including deployment configuration, request limits, and authentication where appropriate.

## Data and model credits

- DistilBERT sentiment model: https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english
- Open-Meteo: https://open-meteo.com/
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright
- Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API
- Foursquare: https://foursquare.com/
