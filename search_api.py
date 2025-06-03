from flask import Flask, request, jsonify
from datetime import datetime
from flask_cors import CORS
import logging
from functions import (
    get_hotels_structured,
    search_hotels,
    split_children_into_rooms,
    split_adults_into_rooms
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    return response

@app.route('/api/search', methods=['POST', 'GET', 'OPTIONS'])
def search():
    logger.debug(f"Request Method: {request.method}")
    logger.debug(f"Request Headers: {dict(request.headers)}")
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200

    # Get request data
    if request.is_json:
        data = request.get_json()
        logger.debug(f"JSON Data: {data}")
    else:
        data = request.form
        logger.debug(f"Form Data: {data}")

    # Extract parameters with defaults
    city_id = data.get('city_id', '')
    hotel_id = data.get('hotel_id', '')
    brand_id = data.get('brand_id', '')
    check_in = data.get('checkIn', datetime.now().strftime('%Y-%m-%d'))
    check_out = data.get('checkOut', (datetime.now().strftime('%Y-%m-%d')))
    adults = int(data.get('adults', 1))
    rooms = int(data.get('rooms', 1))
    children = int(data.get('children', 0))
    children_ages = []

    logger.debug(f"Extracted Parameters:")
    logger.debug(f"City ID: {city_id}")
    logger.debug(f"Hotel ID: {hotel_id}")
    logger.debug(f"Brand ID: {brand_id}")
    logger.debug(f"Check In: {check_in}")
    logger.debug(f"Check Out: {check_out}")
    logger.debug(f"Adults: {adults}")
    logger.debug(f"Rooms: {rooms}")
    logger.debug(f"Children: {children}")

    # Process children ages
    if 'childrenAges' in data and isinstance(data['childrenAges'], list):
        children_ages = [int(age) for age in data['childrenAges'] if age is not None and age != '']
        logger.debug(f"Children Ages: {children_ages}")

    # Validate required parameters - either city or hotel must be provided
    if not city_id and not hotel_id and not brand_id:
        error_response = {
            'error': True,
            'message': 'Either city or hotel or brand must be provided'
        }
        logger.error(f"Validation Error: {error_response}")
        return jsonify(error_response), 400

    if not check_in or not check_out:
        error_response = {
            'error': True,
            'message': 'Check-in and check-out dates are required'
        }
        logger.error(f"Validation Error: {error_response}")
        return jsonify(error_response), 400

    # Fetch hotels from DB
    logger.debug("Fetching hotels from database...")
    hotels = get_hotels_structured(city_id, hotel_id, brand_id, check_in, check_out)
    logger.debug(f"Found {len(hotels)} hotels")

    if not hotels:
        response = {
            'error': False,
            'data': {
                'results': [],
                'message': 'No hotels found matching your criteria'
            }
        }
        return jsonify(response)

    # Calculate minimum rooms needed
    max_adults_per_room = 0
    max_children_per_room = 0
    max_occupancy_per_room = 0
    
    for hotel in hotels:
        for room in hotel['rooms']:
            max_adults_per_room = max(max_adults_per_room, room['max_adults'])
            max_children_per_room = max(max_children_per_room, room['max_children'])
            max_occupancy_per_room = max(max_occupancy_per_room, room['max_occupancy'])

    logger.debug(f"Room Limits:")
    logger.debug(f"Max Adults per Room: {max_adults_per_room}")
    logger.debug(f"Max Children per Room: {max_children_per_room}")
    logger.debug(f"Max Occupancy per Room: {max_occupancy_per_room}")

    # Calculate minimum rooms needed
    min_rooms_for_adults = (adults + max_adults_per_room - 1) // max_adults_per_room if max_adults_per_room > 0 else 1
    min_rooms_for_children = (len(children_ages) + max_children_per_room - 1) // max_children_per_room if max_children_per_room > 0 else 1
    min_rooms_for_occupancy = ((adults + len(children_ages)) + max_occupancy_per_room - 1) // max_occupancy_per_room if max_occupancy_per_room > 0 else 1

    # The real minimum rooms needed is the max of all constraints
    min_rooms_needed = max(min_rooms_for_adults, min_rooms_for_children, min_rooms_for_occupancy)
    logger.debug(f"Minimum Rooms Needed: {min_rooms_needed}")

    # Determine rooms to allocate - respect user's room request if it's valid
    if rooms < min_rooms_needed:
        rooms_to_allocate = min_rooms_needed
        auto_room_message = f"To accommodate {adults} adults" + (f" and {len(children_ages)} children" if children_ages else "") + f", you need at least {min_rooms_needed} rooms."
    else:
        # Use the user's requested number of rooms, but ensure it's not less than minimum needed
        rooms_to_allocate = max(rooms, min_rooms_needed)
        auto_room_message = ''

    logger.debug(f"Rooms to Allocate: {rooms_to_allocate}")
    logger.debug(f"Auto Room Message: {auto_room_message}")

    # Split guests into rooms
    adults_per_room = split_adults_into_rooms(adults, rooms_to_allocate, max_adults_per_room)
    children_per_room = split_children_into_rooms(len(children_ages), rooms_to_allocate, max_children_per_room)
    logger.debug(f"Adults per Room: {adults_per_room}")
    logger.debug(f"Children per Room: {children_per_room}")

    # Validate each room
    valid = True
    for i in range(rooms_to_allocate):
        if (adults_per_room[i] > max_adults_per_room or
            children_per_room[i] > max_children_per_room or
            (adults_per_room[i] + children_per_room[i]) > max_occupancy_per_room):
            valid = False
            break

    logger.debug(f"Room Allocation Valid: {valid}")

    # Build allocation result
    allocation = []
    if valid:
        for i in range(rooms_to_allocate):
            allocation.append({
                'adults': adults_per_room[i],
                'children': children_per_room[i]
            })

    # Perform search
    logger.debug("Performing hotel search...")
    search_results = search_hotels(hotels, city_id, hotel_id, brand_id, adults, children_ages, check_in, check_out, rooms_to_allocate)
    logger.debug(f"Found {len(search_results)} search results")

    # Prepare response
    response = {
        'error': False,
        'data': {
            'results': search_results,
            'autoRoomMessage': auto_room_message,
            'allocation': allocation,
            'valid': valid,
            'searchParams': {
                'city_id': city_id,
                'hotel_id': hotel_id,
                'brand_id': brand_id,
                'checkIn': check_in,
                'checkOut': check_out,
                'adults': adults,
                'rooms': rooms,
                'children': children,
                'childrenAges': children_ages,
                # 'maxAdultsPerRoom': max_adults_per_room,
                # 'maxChildrenPerRoom': max_children_per_room,
                # 'maxOccupancyPerRoom': max_occupancy_per_room,
                # 'minRoomsNeeded': min_rooms_needed,
                # 'roomsToAllocate': rooms_to_allocate
            }
        }
    }

    logger.debug("Sending response...")
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 