import asyncio

import httpx


# ========================================
# Public Overpass servers
# ========================================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


# HTTP codes for which another server will be tried.
RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


# Temporary in-memory cache.
# It is cleared when the backend container restarts.
PLACES_CACHE = {}


# ========================================
# Main function
# ========================================

async def get_nearby_places(
    latitude: float,
    longitude: float,
    radius: int = 5000
) -> list[dict]:

    query = build_overpass_query(
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    headers = {
        "User-Agent": "TravelSentimentApp/1.0",
        "Accept": "application/json"
    }

    cache_key = create_cache_key(
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    last_error_message = (
        "Δεν ήταν δυνατή η σύνδεση "
        "με το Overpass API."
    )

    timeout = httpx.Timeout(
        timeout=35.0,
        connect=10.0
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True
    ) as client:

        for index, overpass_url in enumerate(
            OVERPASS_URLS
        ):
            try:
                print(
                    "Trying Overpass server:",
                    overpass_url
                )

                response = await client.post(
                    overpass_url,
                    data={
                        "data": query
                    }
                )

                # Successful response
                if response.status_code == 200:
                    data = response.json()

                    places = extract_places(
                        data
                    )

                    # Save successful results in cache.
                    if places:
                        PLACES_CACHE[cache_key] = (
                            places
                        )

                    print(
                        "Overpass request succeeded:",
                        overpass_url
                    )

                    return places[:30]

                # Temporary server problem:
                # try the next Overpass instance.
                if (
                    response.status_code
                    in RETRYABLE_STATUS_CODES
                ):
                    last_error_message = (
                        "Το Overpass API "
                        f"{overpass_url} "
                        "επέστρεψε σφάλμα "
                        f"{response.status_code}."
                    )

                    print(last_error_message)

                else:
                    # Non-temporary HTTP problem,
                    # such as an invalid query.
                    raise RuntimeError(
                        "Το Overpass API επέστρεψε "
                        "μη αναμενόμενο σφάλμα "
                        f"{response.status_code}."
                    )

            except httpx.TimeoutException:
                last_error_message = (
                    "Η αναζήτηση μερών "
                    f"στο {overpass_url} "
                    "άργησε υπερβολικά."
                )

                print(last_error_message)

            except httpx.RequestError as error:
                last_error_message = (
                    "Δεν ήταν δυνατή η σύνδεση "
                    f"με το {overpass_url}: "
                    f"{error}"
                )

                print(last_error_message)

            except ValueError:
                last_error_message = (
                    "Το Overpass API επέστρεψε "
                    "μη έγκυρη JSON απάντηση."
                )

                print(last_error_message)

            # Wait before trying the next server.
            if index < len(OVERPASS_URLS) - 1:
                wait_seconds = index + 1

                print(
                    "Trying another Overpass "
                    f"server in {wait_seconds} second(s)..."
                )

                await asyncio.sleep(
                    wait_seconds
                )

    # ========================================
    # Cache fallback
    # ========================================

    cached_places = PLACES_CACHE.get(
        cache_key
    )

    if cached_places:
        print(
            "All Overpass servers failed. "
            "Returning cached places."
        )

        return cached_places[:30]

    # There is no cache because this location
    # has never been loaded successfully.
    raise RuntimeError(
        last_error_message
    )


# ========================================
# Build Overpass query
# ========================================

def build_overpass_query(
    latitude: float,
    longitude: float,
    radius: int
) -> str:

    return f"""
    [out:json][timeout:20];

    (
        nwr
            ["tourism"~"^(museum|attraction|viewpoint|gallery)$"]
            ["name"]
            (around:{radius},{latitude},{longitude});

        nwr
            ["historic"~"^(monument|memorial|castle|archaeological_site)$"]
            ["name"]
            (around:{radius},{latitude},{longitude});

        nwr
            ["amenity"~"^(restaurant|cafe)$"]
            ["name"]
            (around:{radius},{latitude},{longitude});

        nwr
            ["leisure"="park"]
            ["name"]
            (around:{radius},{latitude},{longitude});
    );

    out center 60;
    """


# ========================================
# Create cache key
# ========================================

def create_cache_key(
    latitude: float,
    longitude: float,
    radius: int
) -> tuple:

    return (
        round(latitude, 4),
        round(longitude, 4),
        radius
    )


# ========================================
# Extract places from Overpass JSON
# ========================================

def extract_places(
    data: dict
) -> list[dict]:

    places = []

    if not isinstance(data, dict):
        return places

    elements = data.get(
        "elements",
        []
    )

    for element in elements:
        if not isinstance(element, dict):
            continue

        tags = element.get(
            "tags",
            {}
        )

        if not isinstance(tags, dict):
            continue

        name = tags.get("name")

        if not name:
            continue

        place_latitude = element.get(
            "lat"
        )

        place_longitude = element.get(
            "lon"
        )

        # Ways and relations usually store
        # coordinates inside the center field.
        if (
            place_latitude is None
            or place_longitude is None
        ):
            center = element.get(
                "center",
                {}
            )

            place_latitude = center.get(
                "lat"
            )

            place_longitude = center.get(
                "lon"
            )

        if (
            place_latitude is None
            or place_longitude is None
        ):
            continue

        category = get_place_category(
            tags
        )

        address = build_address(
            tags
        )

        website = (
            tags.get("website")
            or tags.get("contact:website")
        )

        places.append(
            {
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "name": name,
                "category": category,
                "latitude": place_latitude,
                "longitude": place_longitude,
                "address": address,
                "website": website,
                "opening_hours": tags.get(
                    "opening_hours"
                )
            }
        )

    return remove_duplicate_places(
        places
    )


# ========================================
# Find category
# ========================================

def get_place_category(
    tags: dict
) -> str:

    amenity = tags.get("amenity")
    tourism = tags.get("tourism")
    historic = tags.get("historic")
    leisure = tags.get("leisure")

    if amenity == "restaurant":
        return "restaurant"

    if amenity == "cafe":
        return "cafe"

    if tourism == "museum":
        return "museum"

    if tourism == "gallery":
        return "gallery"

    if tourism == "viewpoint":
        return "viewpoint"

    if tourism == "attraction":
        return "attraction"

    if historic:
        return historic

    if leisure == "park":
        return "park"

    return "other"


# ========================================
# Build address
# ========================================

def build_address(
    tags: dict
) -> str | None:

    street = tags.get(
        "addr:street"
    )

    house_number = tags.get(
        "addr:housenumber"
    )

    city = tags.get(
        "addr:city"
    )

    address_parts = [
        part
        for part in [
            street,
            house_number,
            city
        ]
        if part
    ]

    if not address_parts:
        return None

    return " ".join(
        address_parts
    )


# ========================================
# Remove duplicate places
# ========================================

def remove_duplicate_places(
    places: list[dict]
) -> list[dict]:

    unique_places = []
    seen_places = set()

    for place in places:
        unique_key = (
            place.get("name", "").strip().lower(),
            round(
                place.get("latitude", 0),
                5
            ),
            round(
                place.get("longitude", 0),
                5
            )
        )

        if unique_key in seen_places:
            continue

        seen_places.add(
            unique_key
        )

        unique_places.append(
            place
        )

    return unique_places