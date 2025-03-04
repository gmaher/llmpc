from openai import OpenAI
import os
import json

OPENAI_KEY = os.environ['OPENAI_KEY']

openai = OpenAI(api_key=OPENAI_KEY)

fn = "/home/gabriel/projects/llmpc/trip_planner/data/trip_planning_reduced.json"
f = open(fn, 'r')
data = json.load(f)

solutions = {}

SEED = 42
system_prompt = """
You are a diligent AI assistant solving trip planning problems. You will be given constraints on the number of days, flights, and order of locations to visit.
Remember: When flying from city A to city B on day X, that day counts for both cities.

Follow this step-by-step reasoning process (ReAct approach) to find a valid solution:

1. UNDERSTAND: First, clearly identify all the constraints from the problem.
   - List all cities that must be visited
   - Note the required number of days for each city
   - Identify any ordering constraints (which cities must be visited before others)
   - Determine the total trip duration (if specified)

2. PLAN: Create a step-by-step plan for solving the problem.
   - Consider the order of cities based on constraints
   - Consider what flights are needed
   - Remember that flight days count as days spent in both departure and arrival cities

3. EXECUTE: Work through your plan, tracking:
   - Current day counter
   - Current city
   - Days spent in each city so far
   - Which cities have been fully visited

4. VERIFY: Double-check your solution against all constraints.
   - Ensure all cities are visited for the required number of days
   - Confirm all ordering constraints are satisfied
   - Verify the total trip duration meets requirements

5. ANSWER: Provide the final trip itinerary in the exact format shown in examples.

For your final output first print OUTPUT then the final answer (we need this to parse the plan properly), e.g.

OUTPUT
<final trip itinerary>
"""
openai_model = "gpt-4o"

for k, d in list(data.items()):
    print(k)
    prompt = d['prompt_5shot']

    response = openai.chat.completions.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,  # Increased to allow for detailed reasoning
        seed=SEED
    )

    # Extract the assistant's reply
    resp = response.choices[0].message.content
    print(resp)
    
    # Store results
    solutions[k] = {}
    solutions[k]['num_cities'] = d['num_cities']
    solutions[k]['pred_5shot_react'] = resp  # Changed key to reflect ReAct approach
    solutions[k]['cities'] = d['cities']
    solutions[k]['durations'] = d['durations']

with open("./output/solution_react.json", 'w') as f:
    json.dump(solutions, f, indent=1)
