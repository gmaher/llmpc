import os
from openai import OpenAI
import json
from lib import parse_response, check_trip_constraints

system_prompt = """
You are an expert travel planner assistant. Your goal is to create and refine travel plans that satisfy all given constraints.
Your only job is to focus on the constraints around cities to visit, number of days and ordering of the trip.
You do not need to investigate activities, accomodation etc, only focus on satisfying the stated trip constraints.
If you are revising an existing plan, don't forget to consider changing the starting city of the trip or reordering the cities visited.

Specifically you will be asked to propose a trip plan given constraints on the number of days, flights and order of locations to visit.
Note that when flying from one city to another it counts as a day spent in both cities and will count towards the number of days required to visit both of those cities. Take this into account when making your plan.
For example if we fly from city A to city B on day 7 the visit to city B will start on day 7 and the visit to city A will end on day 7.

Here are example Task descriptions and solutions:
TASK:
You plan to visit european cities for 10 days. You want to spend 5 days in Rome, 4 days in Amsterdam and 3 days in Paris.
You plan to meet a friend in Paris on the 9th day of the trip.
There are direct flights between Rome and Paris, Rome and Amsterdam.

Find a trip plan of visiting the cities for 10 days by taking direct flights to commute between them.

PLAN:
**Day 1-4:** Visit Amsterdam for 4 days.
**Day 4:** Fly from Rome to Amsterdam.
**Day 4-8:** Visit Rome for 5 days.
**Day 8:** Fly from Rome to Paris.
**Day 8-10:** Visit Paris for 3 days, spend the 9th day with your friend as planned.

TASK:
You have been asked to solve the following trip planning task:
You plan to visit 3 European cities for 15 days in total. You only take direct flights to commute between cities. You want to spend 6 days in Athens. You want to spend 4 days in London. You want to spend 7 days in Madrid.

Here are the cities that have direct flights:
Madrid and London, from London to Athens.

Find a trip plan of visiting the cities for 15 days by taking direct flights to commute between them.

Output:
**Day 1-7:** Visit Madrid for 7 days.
**Day 7:** Fly from Madrid to London.
**Day 7-10:** Visit London for 4 days.
**Day 10:** Fly from London to Athens.
**Day 10-15:** Visit Athens for 6 days.

TASK:
You plan to visit 8 European cities for 22 days in total. You only take direct flights to commute between cities. You would like to visit Vilnius for 4 days. You would like to visit Venice for 5 days. You plan to stay in Warsaw for 4 days. You want to meet a friend in Warsaw between day 14 and day 17. You want to spend 5 days in Mykonos. You plan to stay in Salzburg for 5 days. You plan to stay in Amsterdam for 2 days. You would like to meet your friends at Amsterdam between day 17 and day 18 to tour together. You plan to stay in Hamburg for 2 days. You would like to visit Copenhagen for 2 days.

Here are the cities that have direct flights:
Warsaw and Amsterdam, Hamburg and Venice, Hamburg and Warsaw, Venice and Warsaw, Hamburg and Amsterdam, Venice and Copenhagen, Vilnius and Amsterdam, Vilnius and Warsaw, Hamburg and Copenhagen, Salzburg and Hamburg, Copenhagen and Amsterdam, Copenhagen and Vilnius, Copenhagen and Warsaw, Venice and Amsterdam, Amsterdam and Mykonos.

Find a trip plan of visiting the cities for 22 days by taking direct flights to commute between them.

Output:
**Day 1-5:** Visit Salzburg for 5 days.
**Day 5:** Fly from Salzburg to Hamburg.
**Day 5-6:** Visit Hamburg for 2 days.
**Day 6:** Fly from Hamburg to Venice.
**Day 6-10:** Visit Venice for 5 days.
**Day 10:** Fly from Venice to Copenhagen.
**Day 10-11:** Visit Copenhagen for 2 days.
**Day 11:** Fly from Copenhagen to Vilnius.
**Day 11-14:** Visit Vilnius for 4 days.
**Day 14:** Fly from Vilnius to Warsaw.
**Day 14-17:** Visit Warsaw for 4 days.
**Day 17:** Fly from Warsaw to Amsterdam.
**Day 17-18:** Visit Amsterdam for 2 days.
**Day 18:** Fly from Amsterdam to Mykonos.
**Day 18-22**: Visit Mykonos for 5 days.

Always format your response using the following template:

PLAN:
<your complete trip plan here>
"""

instruction_prompt = """You have been asked to solve the following trip planning task:
TASK:
{task}

Your current trip plan is:
{current_plan}

{feedback_string}
"""

# Parameters
NUM_PLANNING_STEPS = 7  
SEED = 42

# Clean and recreate output directory
output_dir = "./output/llmpc"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load trip planning data
with open("/home/gabriel/projects/llmpc/trip_planner/data/trip_planning_reduced.json", 'r') as f:
    trip_data = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
solutions = {}

# Run planner for each test example
for k, d in list(trip_data.items()):
    print(f"\nProcessing example {k}")
    
    output_log = f"{output_dir}/trip_plan_{k}.md"
    with open(output_log, 'w') as f:
        f.write(f"{d['prompt_0shot']}\n\n")

    current_plan = ""
    constraints_dict = d['constraints']

    # Run iterations of planning
    for iteration in range(NUM_PLANNING_STEPS):
        print(f"\nIteration {iteration + 1}")
        
        feedback_string = ""
        if current_plan:
            plan = parse_response(current_plan)
            errors = check_trip_constraints(constraints_dict, plan)

            if len(errors) == 0:
                print(f"Plan {plan} satisfies the constraints, terminating")
                break
            else:
                feedback_string = f"There are errors in the plan, please fix them: {'\n*'.join(errors)}"

        prompt = instruction_prompt.format(
            task=d['prompt_0shot'],
            current_plan=current_plan if current_plan else "No plan created yet.",
            feedback_string=feedback_string
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt},
                      {"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=4096,
            seed=SEED
        )

        content = response.choices[0].message.content
        
        with open(output_log, 'a') as f:
            f.write(f"\nIteration {iteration + 1}\n")
            f.write(f"{prompt}\n\n")
            f.write(f"{content}\n")

        if "PLAN:" in content:
            current_plan = content.split("PLAN:")[1].strip()
        else:
            current_plan = content.strip()

    solutions[k] = {
        'num_cities':d['num_cities'],
        'pred_5shot_pro': current_plan,
        'cities': d['cities'],
        'durations': d['durations']
    }

# Save solutions
with open(f"./output/llmpc_solution_{NUM_PLANNING_STEPS}.json", 'w') as f:
    json.dump(solutions, f, indent=1)

print("\nCompleted all examples!")