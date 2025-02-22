from openai import OpenAI
import os
import json

OPENAI_KEY = os.environ['OPENAI_KEY']
openai = OpenAI(api_key=OPENAI_KEY)

# Constants
K_PROPOSALS = 3
SEED = 42
OPENAI_MODEL = "gpt-4o-mini"

PLANNER_SYSTEM_PROMPT = """
You are an expert trip planner. Your task is to generate multiple diverse trip plans that satisfy the given constraints.
You should generate exactly {k} different valid plans.

For each plan:
- Follow all specified constraints around cities, durations, and direct flight requirements
- Remember that flying between cities counts as a day in both cities
- Format the plan exactly like the examples

Present your {k} proposals clearly numbered from 1 to {k}.
""".format(k=K_PROPOSALS)

JUDGE_SYSTEM_PROMPT = """
You are a meticulous trip plan validator and judge. You will be given multiple trip proposals and need to:

1. Validate each plan meets all requirements:
   - Correct total trip duration
   - Required days in each city
   - Direct flight constraints
   - Special timing requirements (e.g. attending events)
   - Flight days counting for both cities

2. For valid plans, assess their quality based on:
   - Efficient use of travel days
   - Logical ordering of cities
   - Meeting timing constraints comfortably

3. Select the best plan and explain why it's optimal.

Provide your analysis in a structured format:
- Validation of each plan
- Comparison of valid plans
- Final selection with reasoning
"""

def get_trip_proposals(prompt):
    response = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,  # Higher temperature for diversity
        max_tokens=1500,
        seed=SEED
    )
    return response.choices[0].message.content

def judge_proposals(original_prompt, proposals):
    judge_prompt = f"""
Original Trip Requirements:
{original_prompt}

Proposed Plans:
{proposals}

Please analyze these proposals and select the best one following the criteria in your instructions.
"""
    
    response = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": judge_prompt}
        ],
        temperature=0.2,  # Lower temperature for consistent judgment
        max_tokens=1500,
        seed=SEED
    )
    return response.choices[0].message.content

def process_trips(data_path):
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    solutions = {}
    
    for k, d in list(data.items())[:10]:
        print(f"Processing trip {k}...")
        
        # Get multiple proposals
        proposals = get_trip_proposals(d['prompt_5shot'])
        
        # Judge proposals and select best
        judgment = judge_proposals(d['prompt_0shot'], proposals)
        
        # Store results
        solutions[k] = {
            'proposals': proposals,
            'judgment': judgment,
            'cities': d['cities'],
            'durations': d['durations']
        }
        
        print(f"Completed trip {k}")
    
    return solutions

if __name__ == "__main__":
    input_path = "/home/gabriel/projects/natural-plan/ground_truth_data/trip_planning.json"
    solutions = process_trips(input_path)
    
    with open("./output/solution.json", 'w') as f:
        json.dump(solutions, f, indent=1)