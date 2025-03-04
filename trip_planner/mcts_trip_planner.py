import os
import math
import random
import time
import json
from openai import OpenAI
from lib import parse_response, check_trip_constraints
from collections import defaultdict

# Configuration
NUM_SIMULATIONS = 20  # Number of MCTS simulations to run
EXPLORATION_WEIGHT = 1.0  # Controls exploration vs exploitation
MAX_DEPTH = 5  # Maximum depth of exploration in the tree
OUTPUT_DIR = "./output/llm_mcts"
SEED = 42
MODEL = "gpt-4o"
random.seed(SEED)

# System prompt remains largely the same
system_prompt = """
You are an expert travel planner assistant. Your goal is to create and refine travel plans that satisfy all given constraints.
Your only job is to focus on the constraints around cities to visit, number of days and ordering of the trip.
You do not need to investigate activities, accomodation etc, only focus on satisfying the stated trip constraints.

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

# Create output directory
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Load trip planning data
with open("./data/trip_planning_reduced.json", 'r') as f:
    trip_data = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state  # Current trip plan
        self.parent = parent  # Parent node
        self.action = action  # Action that led to this state
        self.children = []  # Child nodes
        self.visits = 0  # Number of visits to this node
        self.value = 0  # Value of this node
        self.untried_actions = self._get_untried_actions()
        
    def _get_untried_actions(self):
        # For trip planning, we'll use a few different action types:
        # 1. Change starting city
        # 2. Reorder cities
        # 3. Adjust durations
        # 4. Combine multiple changes
        return ["modify_starting_city", "reorder_cities", "adjust_durations", "combine_changes"]
        
    def is_fully_expanded(self):
        return len(self.untried_actions) == 0
    
    def select_child(self, exploration_weight):
        # Upper Confidence Bound (UCB) formula for selection
        return max(self.children, key=lambda c: 
                  c.value / (c.visits or 1) + 
                  exploration_weight * math.sqrt(2 * math.log(self.visits) / (c.visits or 1)))
    
    def expand(self, action, new_state):
        child = MCTSNode(new_state, self, action)
        self.untried_actions.remove(action)
        self.children.append(child)
        return child
    
    def update(self, result):
        self.visits += 1
        self.value += result


def generate_plan_variation(task, current_plan, action, constraints):
    """Use LLM to generate a variation of the current plan based on the action"""
    
    action_prompts = {
        "modify_starting_city": "Consider changing the starting city of the trip.",
        "reorder_cities": "Try reordering the cities visited to better satisfy the constraints.",
        "adjust_durations": "Adjust the duration spent in each city while maintaining the total trip length.",
        "combine_changes": "Make multiple changes to the plan, including potentially changing the starting city, reordering cities, and adjusting durations."
    }
    
    instruction = f"""
You have been asked to solve the following trip planning task:
TASK:
{task}

Your current trip plan is:
{current_plan}

Please create a new variation of this plan by: {action_prompts[action]}
Make sure all the constraints are satisfied, especially direct flight connections and required meetings.
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction}
        ],
        temperature=0.7,
        max_tokens=2048,
        seed=SEED
    )
    
    content = response.choices[0].message.content
    
    if "PLAN:" in content:
        new_plan = content.split("PLAN:")[1].strip()
    else:
        new_plan = content.strip()
    
    return new_plan


def evaluate_plan(plan, constraints):
    """Evaluate the quality of a plan by checking constraints"""
    parsed_plan = parse_response(plan)
    errors = check_trip_constraints(constraints, parsed_plan)
    
    # Score is inverse to number of errors (0 errors = perfect score)
    return 1.0 / (1 + len(errors))


def run_mcts(task, constraints, num_simulations):
    """Run Monte Carlo Tree Search for trip planning"""
    # Initialize with empty plan
    root = MCTSNode(state="No plan created yet.")
    
    # Log file
    log_path = f"{OUTPUT_DIR}/mcts_log_{int(time.time())}.md"
    
    with open(log_path, 'w') as log_file:
        log_file.write(f"# MCTS Trip Planning\n\n**Task:**\n{task}\n\n")
        
        best_plan = None
        best_score = -1
        
        for i in range(num_simulations):
            log_file.write(f"\n## Simulation {i+1}\n\n")
            
            # Selection phase - traverse tree to find leaf node
            node = root
            depth = 0
            
            while node.is_fully_expanded() and node.children and depth < MAX_DEPTH:
                node = node.select_child(EXPLORATION_WEIGHT)
                depth += 1
                
            log_file.write(f"Selected node at depth {depth} with plan:\n{node.state}\n\n")
            
            # Expansion phase - if possible, expand node
            if not node.is_fully_expanded() and depth < MAX_DEPTH:
                action = random.choice(node.untried_actions)
                new_plan = generate_plan_variation(task, node.state, action, constraints)
                child_node = node.expand(action, new_plan)
                log_file.write(f"Expanded with action: {action}\nNew plan:\n{child_node.state}\n\n")
                
                # Use the child node for evaluation
                eval_node = child_node
            else:
                # Use the selected node for evaluation
                eval_node = node
            
            # Simulation phase - evaluate the node
            current_score = evaluate_plan(eval_node.state, constraints)
            log_file.write(f"Evaluation score: {current_score}\n\n")
            
            # Backpropagation phase - update statistics up the tree
            backprop_node = eval_node
            while backprop_node:
                backprop_node.update(current_score)
                backprop_node = backprop_node.parent
                
            # Track best plan found so far
            if current_score > best_score:
                best_score = current_score
                best_plan = eval_node.state
                log_file.write(f"**New best plan found!** Score: {best_score}\n")
                
            log_file.write("---\n")
            
            # If we found a perfect plan, we can stop early
            if best_score == 1.0:
                log_file.write("\n**Perfect plan found! Stopping search.**\n")
                break
        
        # Final results
        log_file.write(f"\n\n# Final Results\n\nBest plan (score: {best_score}):\n{best_plan}\n")
    
    return best_plan, best_score, log_path


def main():
    solutions = {}
    
    #k = "trip_planning_example_1419"
    #d = trip_data[k]
    for k, d in list(trip_data.items()):
        print(f"\nProcessing example {k}")
        constraints_dict = d['constraints']
        
        # Run MCTS
        best_plan, score, log_path = run_mcts(
            task=d['prompt_0shot'],
            constraints=constraints_dict,
            num_simulations=NUM_SIMULATIONS
        )
        
        print(f"Best plan found with score {score}")
        print(f"Log written to {log_path}")
        
        # Store solution
        solutions[k] = {
            'num_cities': d['num_cities'],
            'pred_mcts': best_plan,
            'score': score,
            'cities': d['cities'],
            'durations': d['durations']
        }
        
    # Save all solutions
    with open(f"./output/mcts_solutions.json", 'w') as f:
        json.dump(solutions, f, indent=2)
    
    print("\nCompleted all examples!")


if __name__ == "__main__":
    main()
