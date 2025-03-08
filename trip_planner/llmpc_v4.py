import os
from openai import OpenAI
import json
from lib import parse_response, check_trip_constraints
import re

system_prompt = """
You are an expert travel planner assistant. Your goal is to create and refine travel plans that satisfy all given constraints.
Your only job is to focus on the constraints around cities to visit, number of days and ordering of the trip.
You do not need to investigate activities, accommodation etc, only focus on satisfying the stated trip constraints.

Specifically you will be asked to propose a trip plan given constraints on the number of days, flights and order of locations to visit.
Note that when flying from one city to another it counts as a day spent in both cities and will count towards the number of days required to visit both of those cities. Take this into account when making your plan.
For example if we fly from city A to city B on day 7, the visit to city B will start on day 7 and the visit to city A will end on day 7.

Here are example Task descriptions and solutions:
EXAMPLE TASK 1:
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

EXAMPLE TASK 2:
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

EXAMPLE TASK 3:
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

OUTPUT INSTRUCTIONS

When revising plans, consider using the following actions:
1. Change starting city - Start the trip from a different city
2. Reorder cities - Change the sequence of city visits
3. Adjust visit durations - Modify how many days are spent in each city
4. Fix flight connections - Ensure direct flights exist between consecutive cities
5. Align with meeting constraints - Ensure scheduled meetings are accommodated
6. Balance time allocation - Distribute days more evenly across cities

Example action sequence to fix a plan:
1. Change starting city from Rome to Amsterdam
2. Reorder to visit Amsterdam, then Rome, then Paris
3. Adjust Rome visit from 4 days to 5 days
4. Ensure Paris visit includes day 9 for friend meeting

Remember that the sum of days spent in all cities must match the total trip duration, accounting for days when flying counts for both departure and arrival cities.
"""

initial_plans_prompt = """You have been asked to solve the following trip planning task:
TASK:
{task}

Your job is to propose {k} different trip plans. For each plan:
1. First, generate a clear sequence of planning actions that will structure your approach
2. Then, based on those actions, create a complete trip plan

Make sure each plan is different from the others. Be creative in how you order the cities and structure the itinerary. Do not be afraid to completely change or try a new plan if a previous one is not working.

Generate {k} distinct plans, formatted exactly like this:

PLAN 1:
ACTIONS:
1. [First action]
2. [Second action]
...

ITINERARY:
**Day X-Y:** [First part of plan]
**Day Y:** [Travel details]
...

PLAN 2:
ACTIONS:
1. [First action]
2. [Second action]
...

ITINERARY:
**Day X-Y:** [First part of plan]
**Day Y:** [Travel details]
...

...and so on until PLAN {k}.
"""

refinement_prompt = """You have been asked to solve the following trip planning task:
TASK:
{task}

Your current best trip plan is:
{current_plan}

The plan has the following issues that need to be fixed:
{error_list}

Please propose {k} different ways to improve this plan. For each improvement:
1. First, identify a specific sequence of actions to fix the issues (like "Change starting city", "Reorder cities", etc.)
2. Then, based on those actions, provide a complete revised trip plan

IMPROVEMENT 1:
ACTIONS:
1. [First action to fix the issues]
2. [Second action to fix the issues]
...

ITINERARY:
**Day X-Y:** [First part of improved plan]
**Day Y:** [Travel details]
...

IMPROVEMENT 2:
ACTIONS:
1. [First action to fix the issues]
2. [Second action to fix the issues]
...

ITINERARY:
**Day X-Y:** [First part of improved plan]
**Day Y:** [Travel details]
...

...and so on until IMPROVEMENT {k}.
"""

# Parameters
NUM_PLANNING_STEPS = 7
NUM_PLANS_PER_ITERATION = 3
SEED = 42

# Clean and recreate output directory
output_dir = "./output/llmpc_action"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load trip planning data
with open("./data/trip_planning_reduced.json", 'r') as f:
    trip_data = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
solutions = {}

def extract_plans(content, k, prefix="PLAN"):
    """Extract multiple plans from the LLM response"""
    plans = []
    actions = []
    
    for i in range(1, k+1):
        # Pattern to match the entire plan entry
        plan_pattern = f"{prefix} {i}:(.*?)(?:{prefix} {i+1}:|$)"
        plan_match = re.search(plan_pattern, content, re.DOTALL)
        
        if plan_match:
            full_plan_text = plan_match.group(1).strip()
            
            # Extract actions and itinerary separately
            action_pattern = r"ACTIONS:(.*?)(?:ITINERARY:|$)"
            action_match = re.search(action_pattern, full_plan_text, re.DOTALL)
            
            itinerary_pattern = r"ITINERARY:(.*?)$"
            itinerary_match = re.search(itinerary_pattern, full_plan_text, re.DOTALL)
            
            if itinerary_match:
                itinerary = itinerary_match.group(1).strip()
                plans.append(itinerary)
                
                if action_match:
                    action_list = action_match.group(1).strip()
                    actions.append(action_list)
                else:
                    actions.append("No explicit actions provided")
    
    # If we didn't find any plans with the pattern, try more lenient extraction
    if not plans:
        if "ITINERARY:" in content:
            plans = [content.split("ITINERARY:")[1].strip()]
            if "ACTIONS:" in content:
                actions = [content.split("ACTIONS:")[1].split("ITINERARY:")[0].strip()]
            else:
                actions = ["No explicit actions provided"]
        elif "**Day" in content:
            plans = [content.strip()]
            actions = ["No explicit actions provided"]
    
    return plans, actions

def evaluate_plan(plan, constraints_dict):
    """Evaluate a plan based on the number of errors"""
    try:
        parsed_plan = parse_response(plan)
        errors = check_trip_constraints(constraints_dict, parsed_plan)
        return len(errors), errors
    except Exception as e:
        return float('inf'), [f"Failed to parse plan: {str(e)}"]

# Run planner for each test example
for k, d in list(trip_data.items()):
    print(f"\nProcessing example {k}")
    
    output_log = f"{output_dir}/trip_plan_{k}.md"
    with open(output_log, 'w') as f:
        f.write(f"{d['prompt_0shot']}\n\n")

    best_plan = ""
    best_error_count = float('inf')
    best_errors = []
    best_actions = ""
    constraints_dict = d['constraints']
    
    # Run iterations of planning
    for iteration in range(NUM_PLANNING_STEPS):
        print(f"\nIteration {iteration + 1}")
        
        # First iteration: generate multiple initial plans
        if iteration == 0:
            prompt = initial_plans_prompt.format(
                task=d['prompt_0shot'],
                k=NUM_PLANS_PER_ITERATION
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.7,  # Higher temperature for more diverse plans
                max_tokens=4096,
                seed=SEED
            )
            
            content = response.choices[0].message.content
            
            # Extract all plans and their associated actions
            plans, actions_list = extract_plans(content, NUM_PLANS_PER_ITERATION, prefix="PLAN")
            
            with open(output_log, 'a') as f:
                f.write(f"\nIteration {iteration + 1} - Generating {NUM_PLANS_PER_ITERATION} initial plans\n")
                f.write(f"{prompt}\n\n")
                f.write(f"{content}\n\n")
        
        # Subsequent iterations: generate multiple improvements to the best plan
        else:
            error_list = "\n".join([f"* {error}" for error in best_errors])
            prompt = refinement_prompt.format(
                task=d['prompt_0shot'],
                current_plan=best_plan,
                error_list=error_list,
                k=NUM_PLANS_PER_ITERATION
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.7,  # Moderate temperature for refinements
                max_tokens=4096,
                seed=SEED
            )
            
            content = response.choices[0].message.content
            
            # Extract all improved plans and their associated actions
            plans, actions_list = extract_plans(content, NUM_PLANS_PER_ITERATION, prefix="IMPROVEMENT")
            
            with open(output_log, 'a') as f:
                f.write(f"\nIteration {iteration + 1} - Generating {NUM_PLANS_PER_ITERATION} improvement plans\n")
                f.write(f"{prompt}\n\n")
                f.write(f"{content}\n\n")
        
        # Evaluate each plan/improvement
        plan_evaluations = []
        for i, (plan, actions) in enumerate(zip(plans, actions_list)):
            error_count, errors = evaluate_plan(plan, constraints_dict)
            plan_evaluations.append((plan, error_count, errors, actions))
            print(f"Plan {i+1} has {error_count} errors")
        
        # Sort plans by error count (ascending)
        plan_evaluations.sort(key=lambda x: x[1])
        
        # Select the best plan from this iteration
        if plan_evaluations:
            current_best_plan, current_best_error_count, current_best_errors, current_best_actions = plan_evaluations[0]
            
            # Update overall best plan if this iteration found a better one
            if current_best_error_count < best_error_count:
                best_plan = current_best_plan
                best_error_count = current_best_error_count
                best_errors = current_best_errors
                best_actions = current_best_actions
        
            with open(output_log, 'a') as f:
                f.write(f"Plan evaluations:\n")
                for i, (plan, errors_count, errors_list, actions) in enumerate(plan_evaluations):
                    f.write(f"Plan {i+1}: {errors_count} errors\n")
                    f.write(f"Actions: {actions}\n")
                    if errors_list:
                        f.write(f"Errors: {', '.join(errors_list)}\n")
                f.write(f"\nBest plan of this iteration: Plan with {current_best_error_count} errors\n")
                f.write(f"Actions: {current_best_actions}\n")
                f.write(f"Overall best plan: Plan with {best_error_count} errors\n")
                f.write(f"Overall best actions: {best_actions}\n")
        
        # If the best plan has no errors, we're done
        if best_error_count == 0:
            print(f"Found plan with 0 errors, terminating")
            break

    solutions[k] = d
    
    solutions[k]['num_cities'] = d['num_cities']
    solutions[k]['pred_5shot_pro'] = best_plan
    solutions[k]['best_actions'] = best_actions
    solutions[k]['cities'] = d['cities']
    solutions[k]['durations']= d['durations']
    

# Save solutions
with open(f"./output/llmpc_action_solution_{NUM_PLANNING_STEPS}.json", 'w') as f:
    json.dump(solutions, f, indent=1)

print("\nCompleted all examples!")
