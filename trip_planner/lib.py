import ast
import re

def parse_response(response: str):
  """Parse the response.

  Returns a parsed plan in a list of (city, stay_days) tuples.

  Args:
    response: Raw response from the model.

  Returns:
    Structured plan after parsing.
  """
  pattern_visit = r'\d+-\d+'
  pattern_flight = r'.*Day (\d+).*from (\w+) to (\w+)'
  pattern_days = r'European cities for (\d+) days'

  days, flights, flight_days = [], [], []
  total_days = None
  for piece in response.split('\n'):
    days_match = re.findall(pattern_days, piece)
    if days_match:
      total_days = int(days_match[0])

    visit_match = re.findall(pattern_visit, piece)
    if visit_match:
      days.append(visit_match[0])
      end_day = int(visit_match[0].split('-')[1])
      # Reach the end of the plan, stop to avoid parsing alternative plans.
      if end_day == total_days:
        break
    flight_match = re.findall(pattern_flight, piece)
    if flight_match:
      flights.append(flight_match[0])

  visit_cities, parsed_plan = [], []
  for flight_day, begin_city, end_city in flights:
    flight_days.append(int(flight_day))
    if not visit_cities:
      visit_cities.append(begin_city)
      visit_cities.append(end_city)
    else:
      visit_cities.append(end_city)

  if not days or not flights or not visit_cities:
    return []
  last_day = int(days[-1].split('-')[1])
  flight_days = [1] + flight_days + [last_day]
  for i, visit_city in enumerate(visit_cities):
    city_stay = flight_days[i + 1] - flight_days[i] + 1
    parsed_plan.append((visit_city, city_stay))

  return parsed_plan

def extract_constraints(task:str, client)->str:
    system = "You are an intelligent AI assistant."
    instruction = f"""
    We are creating a trip plan according to the following requirements.
    PROBLEM DESCRIPTION

    "{task}"

    END PROBLEM DESCRIPTION

    We now need to extract a dictionary of constraints.
    Produce a dictionary where the keys are the cities to be visited.
    The values in the dictionary should be num_days: days the city needs to be visited, flights:list of flights available from that city, day_constraints:list of specific days the city needs to be visited.

    Note for flights when a flight is listed as between city A AND city B, then it is a bidirectional flight.
    A flight listed as from city A TO city B is only a one directional flight.

    Here are example task descriptions and corresponding output:
    Input:
    You want to visit european cities for 10 days. You want to visit Amsterdam for 5 days, Berlin for 5 days and Rome for 2 days. You plan to meet a friend in Rome on days 9-10 of the trip.
    There are direct flights between Amsterdam and Berlin, Amsterdam and Rome.

    Find a trip plan of visiting the cities for 10 days by taking direct flights to commute between them.

    Output:
    {{
        "Amsterdam":{{"num_days":5, "flights":["Berlin", "Rome"], "day_constraints":[]}},
        "Berlin":{{"num_days":5, "flights":["Amsterdam"], "day_constraints":[]}},
        "Rome":{{"num_days":2, "flights":["Amsterdam"], "day_constraints":[9, 10]}}
    }}

    Input:
    You have been asked to solve the following trip planning task:
    You plan to visit 3 European cities for 11 days in total. You only take direct flights to commute between cities. You plan to stay in Prague for 6 days. You would like to visit Warsaw for 4 days. You would like to visit Toulouse for 3 days.

    Here are the cities that have direct flights:
    from Warsaw to Toulouse, Toulouse and Prague.

    Find a trip plan of visiting the cities for 11 days by taking direct flights to commute between them.
    
    Output:
    {{
        "Prague":{{"num_days":6, "flights":["Toulouse"], "day_constraints":[]}},
        "Warsaw":{{"num_days":4, "flights":["Toulouse"], "day_constraints":[]}},
        "Toulouse":{{"num_days":3, "flights":["Prague"], "day_constraints":[]}}
    }}

    Input:
    You have been asked to solve the following trip planning task:
    You plan to visit 3 European cities for 15 days in total. You only take direct flights to commute between cities. You want to spend 6 days in Athens. You want to spend 4 days in London. You want to spend 7 days in Madrid.

    Here are the cities that have direct flights:
    Madrid and London, from London to Athens.

    Find a trip plan of visiting the cities for 15 days by taking direct flights to commute between them.

    Output:
    {{
        "Athens":{{"num_days":6, "flights":[], "day_constraints":[]}},
        "London":{{"num_days":4, "flights":["Madrid", "Athens"], "day_constraints":[]}},
        "Madrid":{{"num_days":7, "flights":["London"], "day_constraints":[]}}
    }}
    
    Input:
    You plan to visit 8 European cities for 22 days in total. You only take direct flights to commute between cities. You would like to visit Vilnius for 4 days. You would like to visit Venice for 5 days. You plan to stay in Warsaw for 4 days. You want to meet a friend in Warsaw between day 14 and day 17. You want to spend 5 days in Mykonos. You plan to stay in Salzburg for 5 days. You plan to stay in Amsterdam for 2 days. You would like to meet your friends at Amsterdam between day 17 and day 18 to tour together. You plan to stay in Hamburg for 2 days. You would like to visit Copenhagen for 2 days.

    Here are the cities that have direct flights:
    Warsaw and Amsterdam, Hamburg and Venice, Hamburg and Warsaw, Venice and Warsaw, Hamburg and Amsterdam, Venice and Copenhagen, Vilnius and Amsterdam, Vilnius and Warsaw, Hamburg and Copenhagen, Salzburg and Hamburg, Copenhagen and Amsterdam, Copenhagen and Vilnius, Copenhagen and Warsaw, Venice and Amsterdam, Amsterdam and Mykonos.

    Find a trip plan of visiting the cities for 22 days by taking direct flights to commute between them.

    Output:
    {{
        "Vilnius":{{"num_days":4, "flights":["Amsterdam", "Warsaw", "Copenhagen"], "day_constraints":[]}},
        "Venice":{{"num_days":5, "flights":["Hamburg", "Warsaw", "Copenhagen", "Amsterdam"], "day_constraints":[]}},
        "Warsaw":{{"num_days":4, "flights":["Amsterdam", "Hamburg", "Venice", "Vilnius", "Copenhagen"], "day_constraints":[14, 15, 16, 17]}},
        "Mykonos":{{"num_days":5, "flights":["Amsterdam"], "day_constraints":[]}},
        "Salzburg":{{"num_days":5, "flights":["Hamburg"], "day_constraints":[]}},
        "Amsterdam":{{"num_days":2, "flights":["Warsaw", "Hamburg", "Vilnius", "Copenhagen", "Venice", "Mykonos"], "day_constraints":[17, 18]}},
        "Hamburg":{{"num_days":2, "flights":["Venice", "Warsaw", "Amsterdam", "Copenhagen", "Salzburg"], "day_constraints":[]}},
        "Copenhagen":{{"num_days":2, "flights":["Venice", "Hamburg", "Amsterdam", "Vilnius", "Warsaw"], "day_constraints":[]}},
    }}

    only output the dictionary, nothing else, do not enclose it in ```json tags
    """

    response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": instruction}
            ],
            temperature=0.2,  # Adjust as needed
            max_tokens=4096,   # Adjust as needed
            seed=0
        )

    resp = response.choices[0].message.content
    return resp

def parse_constraints(resp:str):
    if "```json" in resp:
        resp = resp.replace("```json\n","").replace("```","")

    if "```python" in resp:
        resp = resp.replace("```python\n","").replace("```","")

    try:
        return ast.literal_eval(resp)
    except:
        print(f"failed to parse {resp}")
        return None

def check_trip_constraints(constraints, trip):
    """
    Checks whether a trip defined by a list of (city, num_days) tuples
    satisfies the constraints given in the constraints dictionary.

    :param constraints: Dict of the form
        {
          city_name: {
            'num_days': int,
            'flights': List[str],
            'day_constraints': List[int]
          },
          ...
        }
    :param trip: List of (city, num_days) tuples in the order of visitation.
    :return: List of strings describing any violations of the constraints.
    """

    errors = []
    current_day = 1  # We assume day counting starts at 1

    for i, (city, days) in enumerate(trip):
        # 1) Check that the city is defined in constraints
        if city not in constraints:
            errors.append(f"City '{city}' not found in constraints.")
            # Skip further checks for this city
            current_day += days
            continue

        city_constraints = constraints[city]

        # 2) Check number of days matches
        expected_days = city_constraints['num_days']
        if days != expected_days:
            errors.append(
                f"City '{city}' days mismatch: expected {expected_days}, got {days}"
            )

        # 3) Check day constraints (if non-empty, the start day must be in them)
        if city_constraints['day_constraints']:
            allowed_days = city_constraints['day_constraints']
            if current_day not in allowed_days:
                errors.append(
                    f"City '{city}' start day {current_day} not in allowed days {allowed_days}"
                )

        # 4) Check flight connectivity from the previous city
        if i > 0:
            prev_city = trip[i - 1][0]
            if city not in constraints[prev_city]['flights']:
                errors.append(
                    f"City '{city}' is not reachable from '{prev_city}'. "
                    f"Allowed flights from '{prev_city}' are {constraints[prev_city]['flights']}."
                )

        # Advance the current day counter by the number of days spent in this city
        current_day += days-1

    return errors