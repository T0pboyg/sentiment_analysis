// ========================================
// Sentiment analysis elements
// ========================================

const textInput = document.getElementById("textInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const sentiment = document.getElementById("sentiment");
const confidence = document.getElementById("confidence");
const spinner = document.getElementById("spinner");
const errorMessage = document.getElementById("errorMessage");
const resultCard = document.getElementById("resultCard");


// ========================================
// Weather elements
// ========================================

const cityInput = document.getElementById("cityInput");
const weatherBtn = document.getElementById("weatherBtn");
const weatherCity = document.getElementById("weatherCity");

const weatherTemperature =
    document.getElementById("weatherTemperature");

const weatherDescription =
    document.getElementById("weatherDescription");

const weatherError =
    document.getElementById("weatherError");


// ========================================
// Places elements
// ========================================

const placesMessage =
    document.getElementById("placesMessage");

const placesContainer =
    document.getElementById("placesContainer");


// ========================================
// Analyze one text
// ========================================

analyzeBtn.addEventListener("click", async () => {
    errorMessage.textContent = "";

    const text = textInput.value.trim();

    if (!text) {
        errorMessage.textContent =
            "Το κείμενο είναι κενό.";

        return;
    }

    sentiment.textContent = "—";
    confidence.textContent = "—";

    analyzeBtn.disabled = true;
    spinner.style.display = "block";

    try {
        const response = await fetch(
            "http://127.0.0.1:8000/analyze",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    text: text
                })
            }
        );

        if (!response.ok) {
            const errorData = await response.json();

            throw new Error(
                errorData.detail ||
                `HTTP error: ${response.status}`
            );
        }

        const data = await response.json();

        sentiment.textContent = data.label;

        confidence.textContent =
            `${(data.score * 100).toFixed(2)}%`;

    } catch (error) {
        errorMessage.textContent =
            "Κάτι πήγε στραβά. Έλεγξε αν λειτουργεί το backend.";

        console.error(
            "Sentiment analysis error:",
            error
        );

    } finally {
        spinner.style.display = "none";
        analyzeBtn.disabled = false;
    }
});


// ========================================
// Weather and places search
// ========================================

weatherBtn.addEventListener("click", async () => {
    const city = cityInput.value.trim();

    weatherError.textContent = "";

    if (!city) {
        weatherError.textContent =
            "Γράψε το όνομα μιας πόλης.";

        return;
    }

    weatherBtn.disabled = true;
    weatherBtn.textContent = "Searching...";

    weatherCity.textContent = "—";

    weatherTemperature.textContent =
        "Temperature: —";

    weatherDescription.textContent =
        "Condition: —";

    placesContainer.textContent = "";

    placesMessage.textContent =
        "Waiting for weather information...";

    try {
        const weatherUrl =
            `http://127.0.0.1:8000/weather/${encodeURIComponent(city)}`;

        const response = await fetch(weatherUrl);

        if (!response.ok) {
            const errorData = await response.json();

            throw new Error(
                errorData.detail ||
                "Η αναζήτηση καιρού απέτυχε."
            );
        }

        const data = await response.json();

        weatherCity.textContent =
            `${data.city}, ${data.country}`;

        weatherTemperature.textContent =
            `Temperature: ${data.temperature}${data.temperature_unit}`;

        weatherDescription.textContent =
            `Condition: ${data.weather_description}`;

        // Μετά τον καιρό φορτώνουμε αυτόματα τα κοντινά μέρη.
        await loadPlaces(data.city);

    } catch (error) {
        weatherError.textContent = error.message;

        placesContainer.textContent = "";

        placesMessage.textContent =
            "Places could not be loaded.";

        console.error("Weather error:", error);

    } finally {
        weatherBtn.disabled = false;
        weatherBtn.textContent = "Search Weather";
    }
});


// ========================================
// Search when Enter is pressed
// ========================================

cityInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        weatherBtn.click();
    }
});

textInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        analyzeBtn.click();
    }
});


// ========================================
// Load nearby places
// ========================================

async function loadPlaces(city) {
    placesContainer.textContent = "";

    placesMessage.textContent =
        "Searching for nearby places...";

    try {
        /*
         * Χρησιμοποιούμε ακτίνα 2000 μέτρων,
         * επειδή η αναζήτηση ήταν πιο σταθερή
         * από τα 5000 μέτρα.
         */
        const placesUrl =
            `http://127.0.0.1:8000/places/${encodeURIComponent(city)}?radius=2000`;

        const response = await fetch(placesUrl);

        if (!response.ok) {
            const errorData = await response.json();

            throw new Error(
                errorData.detail ||
                "Η αναζήτηση μερών απέτυχε."
            );
        }

        const data = await response.json();

        if (!data.places || data.places.length === 0) {
            placesMessage.textContent =
                "No nearby places were found.";

            return;
        }

        placesMessage.textContent =
            `Found ${data.total_places} places near ${data.city}.`;

        data.places.forEach((place) => {
            createPlaceCard(place);
        });

    } catch (error) {
        placesContainer.textContent = "";
        placesMessage.textContent = error.message;

        console.error("Places error:", error);
    }
}


// ========================================
// Create one place card
// ========================================

function createPlaceCard(place) {
    const placeCard =
        document.createElement("div");

    placeCard.className = "place-card";


    // Place name
    const placeName =
        document.createElement("h3");

    placeName.textContent =
        place.name || "Unnamed place";

    placeCard.appendChild(placeName);


    // Category
    const category =
        document.createElement("span");

    category.className = "place-category";

    category.textContent =
        place.category || "other";

    placeCard.appendChild(category);


    // Address
    if (place.address) {
        const address =
            document.createElement("p");

        address.className = "place-info";

        address.textContent =
            `Address: ${place.address}`;

        placeCard.appendChild(address);
    }


    // Opening hours
    if (place.opening_hours) {
        const openingHours =
            document.createElement("p");

        openingHours.className = "place-info";

        openingHours.textContent =
            `Opening hours: ${place.opening_hours}`;

        placeCard.appendChild(openingHours);
    }


    // Website
    if (place.website) {
        const website =
            document.createElement("a");

        website.className = "place-link";

        /*
         * Αν το OpenStreetMap επιστρέψει website
         * χωρίς http:// ή https://, το προσθέτουμε.
         */
        if (
            place.website.startsWith("http://") ||
            place.website.startsWith("https://")
        ) {
            website.href = place.website;
        } else {
            website.href = `https://${place.website}`;
        }

        website.target = "_blank";
        website.rel = "noopener noreferrer";
        website.textContent = "Visit website";

        placeCard.appendChild(website);
    }


    // Reviews button
    const reviewsButton =
        document.createElement("button");

    reviewsButton.type = "button";
    reviewsButton.className = "reviews-button";
    reviewsButton.textContent = "View Reviews";


    // Store place data in the button
    reviewsButton.dataset.osmId =
        place.osm_id ?? "";

    reviewsButton.dataset.osmType =
        place.osm_type ?? "";

    reviewsButton.dataset.placeName =
        place.name ?? "";

    reviewsButton.dataset.latitude =
        place.latitude ?? "";

    reviewsButton.dataset.longitude =
        place.longitude ?? "";


    // Reviews container
    const reviewsContainer =
        document.createElement("div");

    reviewsContainer.className =
        "reviews-container";

    reviewsContainer.hidden = true;


    /*
     * Θυμόμαστε αν τα reviews έχουν ήδη φορτωθεί,
     * ώστε να μην κάνουμε νέο API request κάθε φορά
     * που πατιέται το κουμπί.
     */
    let reviewsLoaded = false;


    reviewsButton.addEventListener(
        "click",
        async () => {
            /*
             * Αν έχουν ήδη φορτωθεί, το κουμπί
             * απλώς εμφανίζει ή κρύβει τα reviews.
             */
            if (reviewsLoaded) {
                reviewsContainer.hidden =
                    !reviewsContainer.hidden;

                reviewsButton.textContent =
                    reviewsContainer.hidden
                        ? "View Reviews"
                        : "Hide Reviews";

                return;
            }

            const selectedPlace = {
                osmId:
                    reviewsButton.dataset.osmId,

                osmType:
                    reviewsButton.dataset.osmType,

                name:
                    reviewsButton.dataset.placeName,

                latitude:
                    reviewsButton.dataset.latitude,

                longitude:
                    reviewsButton.dataset.longitude
            };

            reviewsContainer.hidden = false;
            reviewsContainer.textContent =
                "Loading and analyzing reviews...";

            reviewsButton.disabled = true;
            reviewsButton.textContent = "Loading...";

            try {
                const queryParameters =
                    new URLSearchParams({
                        name: selectedPlace.name,
                        latitude: selectedPlace.latitude,
                        longitude: selectedPlace.longitude
                    });

                const reviewsUrl =
                    "http://127.0.0.1:8000/place-reviews" +
                    `?${queryParameters.toString()}`;

                const response = await fetch(reviewsUrl);

                if (!response.ok) {
                    let errorMessage =
                        `HTTP error: ${response.status}`;

                    try {
                        const errorData =
                            await response.json();

                        if (errorData.detail) {
                            errorMessage =
                                errorData.detail;
                        }
                    } catch (jsonError) {
                        console.error(
                            "Could not read error response:",
                            jsonError
                        );
                    }

                    throw new Error(errorMessage);
                }

                const data = await response.json();

                /*
                 * Το backend έχει ήδη περάσει όλα τα
                 * reviews από το sentiment model.
                 */
                displayReviews(
                    data,
                    reviewsContainer
                );

                reviewsLoaded = true;
                reviewsButton.textContent =
                    "Hide Reviews";

            } catch (error) {
                reviewsContainer.textContent = "";

                const reviewsError =
                    document.createElement("p");

                reviewsError.className =
                    "reviews-error";

                reviewsError.textContent =
                    `Reviews could not be loaded: ${error.message}`;

                reviewsContainer.appendChild(
                    reviewsError
                );

                reviewsButton.textContent =
                    "Try Again";

                console.error(
                    "Reviews error:",
                    error
                );

            } finally {
                reviewsButton.disabled = false;
            }
        }
    );


    placeCard.appendChild(reviewsButton);
    placeCard.appendChild(reviewsContainer);

    placesContainer.appendChild(placeCard);
}


// ========================================
// Display analyzed reviews
// ========================================

function displayReviews(data, reviewsContainer) {
    reviewsContainer.textContent = "";

    /*
     * Περίπτωση στην οποία το μέρος βρέθηκε
     * στο Foursquare αλλά δεν έχει tips/reviews.
     */
    if (
        !data.reviews ||
        data.reviews.length === 0
    ) {
        const noReviewsMessage =
            document.createElement("p");

        noReviewsMessage.className =
            "no-reviews-message";

        noReviewsMessage.textContent =
            data.message ||
            "No reviews were found for this place.";

        reviewsContainer.appendChild(
            noReviewsMessage
        );

        return;
    }


    // Overall summary
    const reviewsSummary =
        document.createElement("div");

    reviewsSummary.className =
        "reviews-summary";


    const summaryTitle =
        document.createElement("h4");

    summaryTitle.textContent =
        "Sentiment Summary";


    const overallSentiment =
        document.createElement("p");

    overallSentiment.textContent =
        `Overall sentiment: ${data.overall_sentiment}`;


    const totalReviews =
        document.createElement("p");

    totalReviews.textContent =
        `Total reviews: ${data.total_reviews}`;


    const positiveReviews =
        document.createElement("p");

    positiveReviews.textContent =
        `Positive: ${data.positive_count} (${data.positive_percentage}%)`;


    const negativeReviews =
        document.createElement("p");

    negativeReviews.textContent =
        `Negative: ${data.negative_count} (${data.negative_percentage}%)`;


    reviewsSummary.appendChild(summaryTitle);
    reviewsSummary.appendChild(overallSentiment);
    reviewsSummary.appendChild(totalReviews);
    reviewsSummary.appendChild(positiveReviews);
    reviewsSummary.appendChild(negativeReviews);

    reviewsContainer.appendChild(reviewsSummary);


    // Individual analyzed reviews
    data.reviews.forEach((review, index) => {
        const reviewCard =
            document.createElement("div");

        reviewCard.className = "review-card";


        const reviewNumber =
            document.createElement("h5");

        reviewNumber.textContent =
            `Review ${index + 1}`;


        const reviewText =
            document.createElement("p");

        reviewText.className = "review-text";
        reviewText.textContent = review.text;


        const reviewSentiment =
            document.createElement("p");

        reviewSentiment.className =
            "review-sentiment";

        reviewSentiment.textContent =
            `Sentiment: ${review.label}`;


        const reviewConfidence =
            document.createElement("p");

        reviewConfidence.className =
            "review-confidence";

        reviewConfidence.textContent =
            `Confidence: ${review.confidence}%`;


        reviewCard.appendChild(reviewNumber);
        reviewCard.appendChild(reviewText);
        reviewCard.appendChild(reviewSentiment);
        reviewCard.appendChild(reviewConfidence);

        reviewsContainer.appendChild(reviewCard);
    });
}