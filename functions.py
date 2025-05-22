from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy import text
from db_config import get_db

# Map meal_plan_id to meal plan names
MEAL_PLAN_MAP = {
    1: 'normal',
    2: 'with_breakfast',
    3: 'with_map',
    4: 'with_all'
}

def get_date_range(start: str, end: str) -> List[str]:
    """Get a list of dates between start and end (exclusive)."""
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d') - timedelta(days=1)
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return date_range

def split_guests(n: int, k: int, m: int) -> List[List[int]]:
    """Split n guests into k rooms, each room max m, with minimum 1 guest per room."""
    results = []
    
    # If we have no guests, return array of zeros
    if n == 0:
        return [[0] * k]
    
    # If we have fewer guests than rooms, we need to allow empty rooms
    min_per_room = 0 if n < k else 1
    
    # Calculate base distribution (minimum guests per room)
    base_per_room = n // k
    extra_guests = n % k
    
    # Start with most even distribution
    current = [base_per_room] * k
    for i in range(extra_guests):
        current[i] += 1
    
    # If this distribution is valid, add it to results
    if max(current) <= m and min(current) >= min_per_room:
        results.append(current)
    
    # Generate other valid distributions
    generate_distributions(n, k, m, min_per_room, [], results)
    
    return results

def generate_distributions(n: int, k: int, m: int, min_per_room: int, 
                         current: List[int], results: List[List[int]]) -> None:
    """Helper function to generate all possible guest distributions."""
    if k == 1:
        if min_per_room <= n <= m:
            results.append(current + [n])
        return
    
    # Calculate bounds for this room
    max_for_this_room = min(m, n - (k - 1) * min_per_room)
    
    for i in range(min_per_room, max_for_this_room + 1):
        generate_distributions(
            n - i,
            k - 1,
            m,
            min_per_room,
            current + [i],
            results
        )

def allocate_rooms_and_calculate_price(room: Dict[str, Any], adults: int, 
                                     children_ages: List[int], check_in: str, 
                                     check_out: str, num_rooms: int, 
                                     meal_plan: str) -> Dict[str, Any]:
    """Main allocation and pricing logic."""
    print("\n=== Starting allocate_rooms_and_calculate_price ===")
    print(f"Room: {room['room_name']}")
    print(f"Adults: {adults}, Children: {children_ages}")
    print(f"Check-in: {check_in}, Check-out: {check_out}")
    print(f"Number of rooms: {num_rooms}")
    print(f"Meal plan: {meal_plan}")
    
    max_adults = room['max_adults']
    max_children = room['max_children']
    max_occupancy = room['max_occupancy']
    free_child_age = room['free_child_age']
    pricing = room['pricing']
    dates = get_date_range(check_in, check_out)
    # Convert string dates to datetime.date objects for comparison
    date_objects = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates]
    best_price = None
    best_allocation = None

    print(f"\nRoom limits:")
    print(f"Max adults: {max_adults}")
    print(f"Max children: {max_children}")
    print(f"Max occupancy: {max_occupancy}")
    print(f"Free child age: {free_child_age}")

    # Ensure at least one adult per room
    if adults < num_rooms:
        print("\nNot enough adults for rooms")
        return {
            'price': None,
            'allocation': None
        }

    # Check if pricing exists for all dates
    print("pricing", pricing)
    print("dates", date_objects)
    for date_obj in date_objects:
        if date_obj not in pricing:
            print(f"\nNo pricing for date: {date_obj}")
            return {
                'price': None,
                'allocation': None
            }

    # Get all possible ways to split adults into rooms
    adult_splits = split_guests(adults, num_rooms, max_adults)
    print(f"\nAdult splits: {adult_splits}")
    
    # Get all possible ways to split children into rooms
    child_splits = [[0]] if not children_ages else split_guests(len(children_ages), num_rooms, max_children)
    print(f"Child splits: {child_splits}")

    for adults_per_room in adult_splits:
        for children_per_room in child_splits:
            print(f"\nTrying allocation:")
            print(f"Adults per room: {adults_per_room}")
            print(f"Children per room: {children_per_room}")
            
            children_ages_copy = children_ages.copy()
            children_ages_rooms = []
            
            # If no children, create empty arrays for each room
            if not children_ages:
                children_ages_rooms = [[] for _ in range(num_rooms)]
            else:
                for num_children in children_per_room:
                    children_ages_rooms.append(children_ages_copy[:num_children])
                    children_ages_copy = children_ages_copy[num_children:]

            valid = True
            total_price = 0
            allocation = []

            for i in range(num_rooms):
                a = adults_per_room[i]
                c_ages = children_ages_rooms[i]
                c = len(c_ages)

                print(f"\nRoom {i+1}:")
                print(f"Adults: {a}, Children ages: {c_ages}")

                # Validate room occupancy
                if a < 1 or a + c > max_occupancy or a > max_adults or c > max_children:
                    print("Invalid room occupancy")
                    valid = False
                    break

                room_price = 0
                daily_prices = []

                for date_obj in date_objects:
                    print(f"\nDate: {date_obj}")
                    date_pricing = pricing[date_obj]
                    base_price = 0

                    # Calculate base price based on number of adults
                    if a == 1:
                        base_price = date_pricing['1A'][meal_plan]
                        print(f"Single adult price: {base_price}")
                    elif a == 2:
                        base_price = date_pricing['2A'][meal_plan]
                        print(f"Double adult price: {base_price}")
                    else:
                        # For more than 2 adults, use 2A price as base and add extra adult price
                        base_price = date_pricing['2A'][meal_plan]
                        extra_adults = a - 2
                        extra_price = extra_adults * date_pricing['EA'][meal_plan]
                        base_price += extra_price
                        print(f"Double adult base: {date_pricing['2A'][meal_plan]}")
                        print(f"Extra adults ({extra_adults}) price: {extra_price}")
                        print(f"Total base price: {base_price}")

                    # Calculate children price
                    paid_children = 0
                    free_children = 0
                    for age in c_ages:
                        if age > free_child_age:
                            paid_children += 1
                        else:
                            free_children += 1

                    print(f"Paid children: {paid_children}, Free children: {free_children}")

                    if paid_children > max_children:
                        print("Too many paid children")
                        valid = False
                        break

                    # Add price for paid children
                    children_price = paid_children * date_pricing['EC'][meal_plan]
                    print(f"Children price: {children_price}")
                    
                    # Calculate total price for this day
                    daily_price = base_price + children_price
                    print(f"Daily total: {daily_price}")
                    
                    # Add to room total
                    room_price += daily_price

                    daily_prices.append({
                        'date': date_obj.strftime('%Y-%m-%d'),  # Convert back to string for JSON
                        'base_price': base_price,
                        'children_price': children_price,
                        'total': daily_price,
                        'adults': a,
                        'paid_children': paid_children,
                        'free_children': free_children
                    })

                if not valid:
                    break

                print(f"\nRoom {i+1} total price: {room_price}")
                allocation.append({
                    'adults': a,
                    'children': c_ages,
                    'paid_children': paid_children,
                    'free_children': free_children,
                    'room_price': room_price,
                    'daily_prices': daily_prices,
                    'nights': len(dates),
                    'price_per_night': room_price / len(dates)
                })
                total_price += room_price

            if valid and (best_price is None or total_price < best_price):
                print(f"\nNew best price found: {total_price}")
                best_price = total_price
                best_allocation = allocation

    print("\n=== Finished allocate_rooms_and_calculate_price ===")
    print(f"Best price: {best_price}")
    return {
        'price': best_price,
        'allocation': best_allocation
    }

def search_hotels(hotels: List[Dict[str, Any]], city: str, hotel_name: str, 
                 adults: int, children_ages: List[int], check_in: str, 
                 check_out: str, rooms_required: int) -> List[Dict[str, Any]]:
    """Main search function."""
    print("\n=== Starting search_hotels ===")
    print(f"Search parameters:")
    print(f"City: {city}")
    print(f"Hotel name: {hotel_name}")
    print(f"Adults: {adults}")
    print(f"Children ages: {children_ages}")
    print(f"Check-in: {check_in}")
    print(f"Check-out: {check_out}")
    print(f"Rooms required: {rooms_required}")
    print(f"Total hotels to process: {len(hotels)}")
    
    results = []
    dates = get_date_range(check_in, check_out)
    # Convert string dates to datetime.date objects for comparison
    date_objects = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates]
    grouped_hotels = {}
    
    for hotel in hotels:
        print(f"\nProcessing hotel: {hotel.get('hotel_name', 'Unknown')}")
        print(f"Hotel ID: {hotel.get('hotel_id', 'Unknown')}")
        print(f"City ID: {hotel.get('city_id', 'Unknown')}")
        
        # Filter by city if provided
        if city and (not hotel.get('city_id') or str(city).lower() not in str(hotel['city_id']).lower()):
            print(f"Skipping hotel - city mismatch: {hotel.get('city_id')} != {city}")
            continue
            
        # Filter by hotel name if provided
        if hotel_name and (not hotel.get('hotel_name') or hotel_name.lower() not in hotel['hotel_name'].lower()):
            print(f"Skipping hotel - name mismatch: {hotel.get('hotel_name')} != {hotel_name}")
            continue

        print("Hotel passed initial filters")
        
        # Calculate min rooms needed for this hotel
        max_adults_per_room = 0
        max_children_per_room = 0
        max_occupancy_per_room = 0
        
        print("\nCalculating room requirements:")
        for room in hotel['rooms']:
            print(f"\nRoom: {room.get('room_name', 'Unknown')}")
            print(f"Max adults: {room.get('max_adults', 0)}")
            print(f"Max children: {room.get('max_children', 0)}")
            print(f"Max occupancy: {room.get('max_occupancy', 0)}")
            
            max_adults_per_room = max(max_adults_per_room, room['max_adults'])
            max_children_per_room = max(max_children_per_room, room['max_children'])
            max_occupancy_per_room = max(max_occupancy_per_room, room['max_occupancy'])

        # Calculate minimum rooms needed
        min_rooms_for_adults = (adults + max_adults_per_room - 1) // max_adults_per_room if max_adults_per_room > 0 else 1
        min_rooms_for_children = (len(children_ages) + max_children_per_room - 1) // max_children_per_room if max_children_per_room > 0 else 1
        min_rooms_for_occupancy = ((adults + len(children_ages)) + max_occupancy_per_room - 1) // max_occupancy_per_room if max_occupancy_per_room > 0 else 1
        
        print("\nMinimum rooms calculation:")
        print(f"Min rooms for adults: {min_rooms_for_adults}")
        print(f"Min rooms for children: {min_rooms_for_children}")
        print(f"Min rooms for occupancy: {min_rooms_for_occupancy}")
        
        min_rooms_needed = max(min_rooms_for_adults, min_rooms_for_children, min_rooms_for_occupancy)
        print(f"Final minimum rooms needed: {min_rooms_needed}")

        # Create custom room message if needed
        custom_room_message = ''
        if rooms_required < min_rooms_needed:
            custom_room_message = f"To accommodate {adults} adult{'s' if adults > 1 else ''}" + \
                                (f" and {len(children_ages)} child{'ren' if len(children_ages) > 1 else ''}" if children_ages else "") + \
                                f", you need at least {min_rooms_needed} rooms at {hotel['hotel_name']}."
            print(f"\nCustom room message: {custom_room_message}")

        # Group hotels by hotel_id
        hotel_key = hotel['hotel_id']
        print(f"\nGrouping hotel with key: {hotel_key}")
        
        if hotel_key not in grouped_hotels:
            grouped_hotels[hotel_key] = {
                'hotel_id': hotel['hotel_id'],
                'hotel_name': hotel['hotel_name'],
                'city': hotel.get('city_id', ''),
                'check_in': check_in,
                'check_out': check_out,
                'nights': len(dates),
                'rooms_required': min_rooms_needed,
                'adults': adults,
                'children_ages': children_ages,
                'custom_room_message': custom_room_message,
                'rooms': []
            }
            print("Created new hotel group")

        # Process each room type
        print("\nProcessing room types:")
        for room in hotel['rooms']:
            print(f"\nRoom type: {room.get('room_name', 'Unknown')}")
            
            # Check if room has pricing for all required dates
            has_all_dates = True
            for date_obj in date_objects:
                print(f"Checking date: {date_obj}")
                print(f"Available dates: {list(room['pricing'].keys())}")
                
                if date_obj not in room['pricing'] or not room['pricing'][date_obj]:
                    print(f"Missing pricing for date: {date_obj}")
                    has_all_dates = False
                    break
                    
                # Check if all meal plans have prices for this date
                date_pricing = room['pricing'][date_obj]
                print(f"Date pricing structure: {date_pricing}")
                
                for occupancy_type in ['1A', '2A', 'EA', 'EC']:
                    if occupancy_type not in date_pricing:
                        print(f"Missing {occupancy_type} in pricing structure")
                        has_all_dates = False
                        break
                        
                    # Check if all meal plans have prices for this occupancy type
                    meal_plans = date_pricing[occupancy_type]
                    if not all(meal_plan in meal_plans for meal_plan in MEAL_PLAN_MAP.values()):
                        print(f"Missing meal plans for {occupancy_type}")
                        print(f"Available meal plans: {list(meal_plans.keys())}")
                        print(f"Required meal plans: {list(MEAL_PLAN_MAP.values())}")
                        has_all_dates = False
                        break

            # Skip room if not available for all dates
            if not has_all_dates:
                print("Skipping room - missing pricing data")
                continue

            print("Room has complete pricing data")

            # Try each meal plan
            meal_plan_results = {}
            print("\nProcessing meal plans:")
            for meal_plan_id, meal_plan in MEAL_PLAN_MAP.items():
                print(f"\nTrying meal plan: {meal_plan}")
                allocation_result = allocate_rooms_and_calculate_price(
                    room, adults, children_ages, check_in, check_out, 
                    min_rooms_needed, meal_plan
                )
                
                if allocation_result['price'] is not None:
                    print(f"Valid allocation found for {meal_plan}")
                    meal_plan_results[meal_plan] = allocation_result
                else:
                    print(f"No valid allocation for {meal_plan}")

            if meal_plan_results:
                print(f"Adding room with {len(meal_plan_results)} valid meal plans")
                grouped_hotels[hotel_key]['rooms'].append({
                    'room_type': room['room_type'],
                    'room_name': room['room_name'],
                    'meal_plans': meal_plan_results
                })
            else:
                print("No valid meal plans found for room")

    # Convert grouped hotels to list
    results = list(grouped_hotels.values())
    print("results", results)
    print(f"\n=== Finished search_hotels ===")
    print(f"Found {len(results)} hotels with valid rooms")
    return results

def format_inr(amount: float) -> str:
    """Format amount in INR currency format."""
    return f"₹{amount:,.2f}"

def matches_search(hotel: Dict[str, Any], search_key: str) -> bool:
    """Check if hotel matches search criteria."""
    search_key = search_key.lower()
    return (
        search_key in hotel.get('hotel_name', '').lower() or
        search_key in hotel.get('city_id', '').lower()
    )

def get_hotels_structured(city_id: Optional[str] = None, 
                         hotel_name: Optional[str] = None,
                         check_in: Optional[str] = None,
                         check_out: Optional[str] = None,
                         distributor_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get structured hotel data from database."""
    try:
        db = next(get_db())
        
        # Base query
        query = """
            SELECT 
                h.id AS hotel_id,
                h.hotel_name,
                h.city_id,
                dhl.id AS dist_hotel_id,
                r.id AS room_id,
                r.room_name,
                r.room_type,
                r.max_adults,
                r.max_children,
                r.max_occupancy,
                r.free_child_age_limit,
                p.date,
                p.price_adult_1,
                p.price_adult_2,
                p.extra_adult,
                p.extra_child,
                p.meal_plan_id
            FROM anh_hotels h
            JOIN anh_distributor_hotels_list dhl ON h.id = dhl.hotel_id
            JOIN anh_hotel_rooms r ON h.id = r.hotel_id
            JOIN anh_room_pricing p ON dhl.id = p.dist_hotel_id AND p.dist_room_id = r.id
            WHERE h.is_active = 1 AND h.is_delete = 0
              AND r.is_active = 1 AND r.is_delete = 0
              AND dhl.is_active = 1 AND dhl.is_delete = 0
        """
        
        params = {}
        
        # Add filters
        if city_id:
            query += " AND dhl.city_id = :city_id"
            params['city_id'] = city_id
            
        if hotel_name:
            query += " AND h.hotel_name LIKE :hotel_name"
            params['hotel_name'] = f"%{hotel_name}%"
            
        if check_in and check_out:
            query += " AND p.date BETWEEN :check_in AND :check_out"
            params['check_in'] = check_in
            params['check_out'] = check_out
            
        if distributor_id:
            query += " AND dhl.distributor_id = :distributor_id"
            params['distributor_id'] = distributor_id

        query += " ORDER BY h.hotel_name, r.room_name, p.date"
            
        # Execute query
        result = db.execute(text(query), params)
        rows = result.fetchall()
        
        # Process results
        hotels = {}
        for row in rows:
            hotel_id = row.hotel_id
            room_id = row.room_id
            date = row.date
            meal_plan = MEAL_PLAN_MAP.get(row.meal_plan_id, 'normal')

            if hotel_id not in hotels:
                hotels[hotel_id] = {
                    'hotel_id': row.dist_hotel_id,
                    'hotel_name': row.hotel_name,
                    'city_id': row.city_id,
                    'rooms': {}
                }

            if room_id not in hotels[hotel_id]['rooms']:
                hotels[hotel_id]['rooms'][room_id] = {
                    'room_name': row.room_name,
                    'room_type': row.room_type,
                    'max_adults': row.max_adults,
                    'max_children': row.max_children,
                    'max_occupancy': row.max_occupancy,
                    'free_child_age': row.free_child_age_limit,
                    'pricing': {}
                }

            if date not in hotels[hotel_id]['rooms'][room_id]['pricing']:
                hotels[hotel_id]['rooms'][room_id]['pricing'][date] = {
                    '1A': {},
                    '2A': {},
                    'EA': {},
                    'EC': {}
                }

            # Fill pricing for each occupancy type and meal plan
            hotels[hotel_id]['rooms'][room_id]['pricing'][date]['1A'][meal_plan] = row.price_adult_1
            hotels[hotel_id]['rooms'][room_id]['pricing'][date]['2A'][meal_plan] = row.price_adult_2
            hotels[hotel_id]['rooms'][room_id]['pricing'][date]['EA'][meal_plan] = row.extra_adult
            hotels[hotel_id]['rooms'][room_id]['pricing'][date]['EC'][meal_plan] = row.extra_child

        # Re-index for compatibility with previous JSON structure
        for hotel in hotels.values():
            hotel['rooms'] = list(hotel['rooms'].values())
            for room in hotel['rooms']:
                room['pricing'] = dict(sorted(room['pricing'].items()))

        return list(hotels.values())
        
    except Exception as e:
        print(f"Database error: {str(e)}")
        return []
    finally:
        db.close()

def split_children_into_rooms(total_children: int, room_count: int, 
                            max_children_per_room: int) -> List[int]:
    """Split children into rooms."""
    if total_children == 0:
        return [0] * room_count
    
    base_children = total_children // room_count
    extra_children = total_children % room_count
    
    distribution = [base_children] * room_count
    for i in range(extra_children):
        distribution[i] += 1
    
    return distribution

def split_adults_into_rooms(total_adults: int, room_count: int, 
                          max_adults_per_room: int) -> List[int]:
    """Split adults into rooms."""
    if total_adults == 0:
        return [0] * room_count
    
    base_adults = total_adults // room_count
    extra_adults = total_adults % room_count
    
    distribution = [base_adults] * room_count
    for i in range(extra_adults):
        distribution[i] += 1
    
    return distribution 