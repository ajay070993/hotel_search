# Hotel Room Search API

This is a Python-based hotel room search API that allows users to search for available hotel rooms based on various criteria such as city, hotel name, check-in/check-out dates, number of adults, children, and rooms.

## Features

- Search hotels by city and hotel name
- Support for multiple rooms
- Support for adults and children with age-based pricing
- Automatic room allocation based on occupancy limits
- Meal plan options
- Detailed pricing breakdown
- CORS support for web applications

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database connection:
   - Update the `get_hotels_structured` function in `functions.py` with your database connection details
   - The function should return a list of hotels with their room information and pricing

## Running the API

Start the Flask development server:
```bash
python search_api.py
```

The API will be available at `http://localhost:5000/search`

## API Usage

### Endpoint: POST /search

#### Request Parameters

- `city` (required): City name to search in
- `hotel_name` (optional): Specific hotel name to search for
- `checkIn` (required): Check-in date (YYYY-MM-DD)
- `checkOut` (required): Check-out date (YYYY-MM-DD)
- `adults` (optional, default: 1): Number of adults
- `rooms` (optional, default: 1): Number of rooms
- `children` (optional, default: 0): Number of children
- `childrenAges` (optional): Array of children ages

#### Example Request

```json
{
    "city": "Mumbai",
    "hotel_name": "Grand Hotel",
    "checkIn": "2024-03-20",
    "checkOut": "2024-03-25",
    "adults": 2,
    "rooms": 1,
    "children": 1,
    "childrenAges": [8]
}
```

#### Example Response

```json
{
    "error": false,
    "data": {
        "results": [
            {
                "hotel": {
                    "hotel_name": "Grand Hotel",
                    "city_id": "Mumbai",
                    "rooms": [...]
                },
                "room": {
                    "room_type": "Deluxe",
                    "max_adults": 2,
                    "max_children": 1,
                    "max_occupancy": 3,
                    "pricing": {...}
                },
                "meal_plan": "with_breakfast",
                "price": 15000,
                "allocation": [...]
            }
        ],
        "autoRoomMessage": "",
        "allocation": [
            {
                "adults": 2,
                "children": 1
            }
        ],
        "valid": true,
        "searchParams": {...}
    }
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- 400: Missing required parameters
- 500: Server error

## Notes

- The API automatically calculates the minimum number of rooms needed based on occupancy limits
- Children under a certain age (defined in room configuration) are free
- Prices are calculated per night and include meal plan costs
- Room allocation ensures at least one adult per room 