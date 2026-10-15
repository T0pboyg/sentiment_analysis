import os

import requests


FSQ_API_KEY = os.getenv("FSQ_API_KEY")

FSQ_BASE_URL = "https://places-api.foursquare.com"

FSQ_API_VERSION = "2025-06-17"


class FoursquareCreditsError(Exception):
    """
    Προκαλείται όταν το Foursquare επιστρέφει 429
    επειδή δεν υπάρχουν διαθέσιμα API credits.
    """

    pass


def get_headers():
    """
    Δημιουργεί τα headers που απαιτεί το Foursquare API.
    """

    if not FSQ_API_KEY:
        raise RuntimeError(
            "FSQ_API_KEY is not configured"
        )

    return {
        "Authorization": f"Bearer {FSQ_API_KEY}",
        "X-Places-Api-Version": FSQ_API_VERSION,
        "Accept": "application/json"
    }


def check_foursquare_response(response):
    """
    Ελέγχει την απάντηση του Foursquare.

    Το 429 αντιμετωπίζεται ξεχωριστά,
    ώστε το main.py να ενεργοποιεί fallback reviews.
    """

    if response.status_code == 429:
        raise FoursquareCreditsError(
            "Foursquare API credits exhausted"
        )

    response.raise_for_status()


def search_foursquare_place(
    name,
    latitude,
    longitude
):
    """
    Αναζητά ένα μέρος στο Foursquare με βάση
    το όνομα και τις συντεταγμένες του.

    Επιστρέφει το fsq_place_id ή None.
    """

    url = f"{FSQ_BASE_URL}/places/search"

    params = {
        "query": name,
        "ll": f"{latitude},{longitude}",
        "radius": 1000,
        "limit": 5
    }

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=15
        )

        check_foursquare_response(response)

    except FoursquareCreditsError:
        raise

    except requests.Timeout as error:
        raise RuntimeError(
            "Foursquare request timed out"
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            f"Foursquare place search failed: {error}"
        ) from error

    data = response.json()

    if isinstance(data, dict):
        results = data.get("results", [])
    else:
        results = []

    if not results:
        return None

    first_place = results[0]

    return first_place.get("fsq_place_id")


def get_place_tips(fsq_place_id):
    """
    Ζητά τα tips/reviews ενός συγκεκριμένου μέρους.

    Επιστρέφει λίστα που περιέχει μόνο
    τα κείμενα των tips.
    """

    if not fsq_place_id:
        return []

    url = (
        f"{FSQ_BASE_URL}/places/"
        f"{fsq_place_id}/tips"
    )

    params = {
        "limit": 20
    }

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=15
        )

        check_foursquare_response(response)

    except FoursquareCreditsError:
        raise

    except requests.Timeout as error:
        raise RuntimeError(
            "Foursquare tips request timed out"
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            f"Foursquare tips request failed: {error}"
        ) from error

    data = response.json()

    # Το API μπορεί να επιστρέψει είτε dictionary
    # με πεδίο results είτε απευθείας λίστα.
    if isinstance(data, dict):
        tips = data.get("results", [])
    elif isinstance(data, list):
        tips = data
    else:
        tips = []

    tip_texts = []

    for tip in tips:
        if not isinstance(tip, dict):
            continue

        text = tip.get("text")

        if isinstance(text, str) and text.strip():
            tip_texts.append(text.strip())

    return tip_texts