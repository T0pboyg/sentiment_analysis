from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import httpx

from model import classifier
from places_service import get_nearby_places
from foursquare_service import (
    FoursquareCreditsError,
    get_place_tips,
    search_foursquare_place,
)
from fallback_reviews import get_fallback_reviews


app = FastAPI()


# ========================================
# CORS
# ========================================

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ========================================
# Weather descriptions
# ========================================

weather_descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",

    45: "Fog",
    48: "Depositing rime fog",

    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",

    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",

    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",

    66: "Light freezing rain",
    67: "Heavy freezing rain",

    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",

    77: "Snow grains",

    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",

    85: "Slight snow showers",
    86: "Heavy snow showers",

    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# ========================================
# Request models
# ========================================

class AnalyzeRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=1000,
    )


class ReviewsRequest(BaseModel):
    reviews: list[str] = Field(
        min_length=1,
    )


# ========================================
# Home endpoint
# ========================================

@app.get("/")
def home():
    return {
        "message": "API is running"
    }


# ========================================
# Analyze one text
# ========================================

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    result = classifier(request.text)[0]

    return {
        "label": result["label"],
        "score": result["score"],
    }


# ========================================
# Weather endpoint
# ========================================

@app.get("/weather/{city}")
async def get_weather(city: str):
    city = city.strip()

    if not city:
        raise HTTPException(
            status_code=400,
            detail=(
                "Το όνομα της πόλης "
                "δεν μπορεί να είναι κενό."
            ),
        )

    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    try:
        async with httpx.AsyncClient(
            timeout=15.0
        ) as client:

            geocoding_response = await client.get(
                geocoding_url,
                params={
                    "name": city,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
            )

            geocoding_response.raise_for_status()

            geocoding_data = (
                geocoding_response.json()
            )

            locations = geocoding_data.get(
                "results"
            )

            if not locations:
                raise HTTPException(
                    status_code=404,
                    detail="Η πόλη δεν βρέθηκε.",
                )

            location = locations[0]

            latitude = location["latitude"]
            longitude = location["longitude"]

            weather_response = await client.get(
                weather_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": (
                        "temperature_2m,"
                        "weather_code"
                    ),
                    "timezone": "auto",
                },
            )

            weather_response.raise_for_status()

            weather_data = (
                weather_response.json()
            )

    except HTTPException:
        raise

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Η εξωτερική υπηρεσία καιρού "
                "επέστρεψε σφάλμα "
                f"{error.response.status_code}."
            ),
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Δεν ήταν δυνατή η σύνδεση "
                "με την υπηρεσία καιρού."
            ),
        ) from error

    current_weather = weather_data.get(
        "current"
    )

    if not current_weather:
        raise HTTPException(
            status_code=502,
            detail=(
                "Δεν επιστράφηκαν "
                "δεδομένα καιρού."
            ),
        )

    weather_code = current_weather.get(
        "weather_code"
    )

    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "latitude": latitude,
        "longitude": longitude,

        "temperature": current_weather.get(
            "temperature_2m"
        ),

        "temperature_unit": weather_data.get(
            "current_units",
            {},
        ).get(
            "temperature_2m",
            "°C",
        ),

        "weather_code": weather_code,

        "weather_description":
            weather_descriptions.get(
                weather_code,
                "Unknown weather condition",
            ),

        "time": current_weather.get("time"),
    }


# ========================================
# Analyze a list of reviews
# ========================================

@app.post("/analyze-reviews")
def analyze_reviews(
    request: ReviewsRequest
):
    positive_count = 0
    negative_count = 0
    review_results = []

    for review in request.reviews:
        result = classifier(review)[0]

        label = result["label"]

        review_results.append(
            {
                "review": review,
                "label": label,
                "confidence": round(
                    result["score"] * 100,
                    2,
                ),
            }
        )

        if label == "POSITIVE":
            positive_count += 1
        else:
            negative_count += 1

    total_reviews = len(
        request.reviews
    )

    positive_percentage = round(
        (
            positive_count /
            total_reviews
        ) * 100,
        2,
    )

    negative_percentage = round(
        (
            negative_count /
            total_reviews
        ) * 100,
        2,
    )

    if positive_count > negative_count:
        overall_sentiment = "POSITIVE"

    elif negative_count > positive_count:
        overall_sentiment = "NEGATIVE"

    else:
        overall_sentiment = "MIXED"

    return {
        "total_reviews": total_reviews,
        "positive_reviews": positive_count,
        "negative_reviews": negative_count,
        "positive_percentage":
            positive_percentage,
        "negative_percentage":
            negative_percentage,
        "overall_sentiment":
            overall_sentiment,
        "review_results": review_results,
    }


# ========================================
# Places endpoint
# ========================================

@app.get("/places/{city}")
async def get_places(
    city: str,
    radius: int = 5000,
):
    city = city.strip()

    if not city:
        raise HTTPException(
            status_code=400,
            detail=(
                "Το όνομα της πόλης "
                "δεν μπορεί να είναι κενό."
            ),
        )

    if radius < 500 or radius > 10000:
        raise HTTPException(
            status_code=400,
            detail=(
                "Η ακτίνα πρέπει να είναι "
                "μεταξύ 500 και 10000 μέτρων."
            ),
        )

    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    try:
        async with httpx.AsyncClient(
            timeout=15.0
        ) as client:

            response = await client.get(
                geocoding_url,
                params={
                    "name": city,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
            )

            response.raise_for_status()

            geocoding_data = response.json()

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Η υπηρεσία αναζήτησης "
                "πόλης επέστρεψε σφάλμα."
            ),
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Δεν ήταν δυνατή η σύνδεση "
                "με την υπηρεσία πόλεων."
            ),
        ) from error

    locations = geocoding_data.get(
        "results"
    )

    if not locations:
        raise HTTPException(
            status_code=404,
            detail="Η πόλη δεν βρέθηκε.",
        )

    location = locations[0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    try:
        places = await get_nearby_places(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "total_places": len(places),
        "places": places,
    }


# ========================================
# Place reviews with fallback
# ========================================

@app.get("/place-reviews")
def get_place_reviews(
    name: str,
    latitude: float,
    longitude: float,
):
    place_name = name.strip()

    if not place_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Το όνομα του μέρους "
                "δεν μπορεί να είναι κενό."
            ),
        )

    fsq_place_id = None

    reviews_source = "foursquare"

    source_message = None

    try:
        # Search for the place on Foursquare
        fsq_place_id = (
            search_foursquare_place(
                place_name,
                latitude,
                longitude,
            )
        )

        # Place not found on Foursquare
        if not fsq_place_id:
            tips = get_fallback_reviews(
                place_name
            )

            reviews_source = "fallback"

            source_message = (
                "The place was not found "
                "on Foursquare. "
                "Demo reviews are being used."
            )

        else:
            # Get real Foursquare tips
            tips = get_place_tips(
                fsq_place_id
            )

            # Place found, but no tips exist
            if not tips:
                tips = get_fallback_reviews(
                    place_name
                )

                reviews_source = "fallback"

                source_message = (
                    "No Foursquare reviews "
                    "were available. "
                    "Demo reviews are being used."
                )

    except FoursquareCreditsError:
        # Foursquare returned status 429
        tips = get_fallback_reviews(
            place_name
        )

        reviews_source = "fallback"

        source_message = (
            "Foursquare API credits "
            "are unavailable. "
            "Demo reviews are being used."
        )

    except RuntimeError as error:
        # Foursquare timeout or other error
        tips = get_fallback_reviews(
            place_name
        )

        reviews_source = "fallback"

        source_message = (
            "Foursquare is temporarily "
            "unavailable. "
            "Demo reviews are being used."
        )

        print(
            f"Foursquare error: {error}"
        )

    if not tips:
        return {
            "place_name": place_name,
            "fsq_place_id": fsq_place_id,
            "reviews_source":
                reviews_source,
            "total_reviews": 0,
            "positive_count": 0,
            "negative_count": 0,
            "positive_percentage": 0.0,
            "negative_percentage": 0.0,
            "overall_sentiment":
                "NO_REVIEWS",
            "reviews": [],
            "message":
                "No reviews are available.",
        }

    review_results = []

    # Analyze every review automatically
    for tip in tips:
        result = classifier(tip)[0]

        review_results.append(
            {
                "text": tip,
                "label": result["label"],
                "confidence": round(
                    result["score"] * 100,
                    2,
                ),
            }
        )

    total_reviews = len(
        review_results
    )

    positive_count = sum(
        1
        for review in review_results
        if review["label"] == "POSITIVE"
    )

    negative_count = sum(
        1
        for review in review_results
        if review["label"] == "NEGATIVE"
    )

    positive_percentage = round(
        (
            positive_count /
            total_reviews
        ) * 100,
        2,
    )

    negative_percentage = round(
        (
            negative_count /
            total_reviews
        ) * 100,
        2,
    )

    if positive_count > negative_count:
        overall_sentiment = "POSITIVE"

    elif negative_count > positive_count:
        overall_sentiment = "NEGATIVE"

    else:
        overall_sentiment = "MIXED"

    return {
        "place_name": place_name,
        "fsq_place_id": fsq_place_id,

        "reviews_source":
            reviews_source,

        "total_reviews":
            total_reviews,

        "positive_count":
            positive_count,

        "negative_count":
            negative_count,

        "positive_percentage":
            positive_percentage,

        "negative_percentage":
            negative_percentage,

        "overall_sentiment":
            overall_sentiment,

        "reviews":
            review_results,

        "message":
            source_message,
    }