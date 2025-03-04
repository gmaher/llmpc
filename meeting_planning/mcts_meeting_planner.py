import os
import math
import random
import time
import json
from openai import OpenAI
from evaluate_meeting_planning_llmpc import process_constraints, parse_text_plan, validate_constraints
from collections import defaultdict

# Configuration
NUM_SIMULATIONS = 20  # Number of MCTS simulations to run
EXPLORATION_WEIGHT = 1.0  # Controls exploration vs exploitation
MAX_DEPTH = 5  # Maximum depth of exploration in the tree
OUTPUT_DIR = "./output/meeting_mcts"
SEED = 42
MODEL = "gpt-4o"
random.seed(SEED)

# System prompt for meeting planning
system_prompt = """
You are an expert meeting planner assistant. Your goal is to create and refine plans to meet friends at different places in the city, taking into account travel times and meeting time constraints.
Your job is to iteratively create and modify a plan that maximizes the number of friends that can be met given the constraints. 

You will be asked to create and modify meeting plans to maximize the number of friends you can meet in a day.

When no plan is given you should start by planning meetings with the first few required people.
When an existing plan is given you should consider adding more meetings or modifying the plan so that more meetings can be added.
If you believe you have the best possible plan make no modifications and simply output the existing plan.
Do not propose meeting with imaginary friends. 
Only propose meetings with friends mentioned in the task description.
Do not propose multiple meetings with the same friend, e.g. DO NOT say 'You meet <friend_name> again for ... .
If the plan already includes all mentioned friends, do not make any modifications or propose additional meetings.

PLAN FORMAT:
A plan includes a start, meeting, traveling and waiting steps.
* The start of a plan should be phrased as 'You start at <location> at <start_time>'
* A meeting step should be phrased as 'You meet <friend_name> for <time_spent> minutes from <start_time> to <end_time>.'
* A travel step should be phrased as 'You travel to <location> in <travel_time> minutes and arrive at <arrival_time>.'
* A waiting step should be phrased as 'You wait until <end_time>.'

Only use the above phrasing, e.g. do not mention 'You travel back to...' only mention 'You travel to...'

EXAMPLES:
Here are example input task descriptions and output plans:
You are visiting San Francisco for the day and want to meet as many friends as possible. Solve the problem by considering various different schedules and picking the best one to optimize your goals.

Travel distances (in minutes):
Marina District to Alamo Square: 15.
Marina District to Fisherman's Wharf: 10.
Marina District to Union Square: 16.
Alamo Square to Marina District: 15.
Alamo Square to Fisherman's Wharf: 19.
Alamo Square to Union Square: 14.
Fisherman's Wharf to Marina District: 9.
Fisherman's Wharf to Alamo Square: 20.
Fisherman's Wharf to Union Square: 13.
Union Square to Marina District: 18.
Union Square to Alamo Square: 15.
Union Square to Fisherman's Wharf: 15.

CONSTRAINTS: You arrive at Marina District at 9:00AM. Jessica will be at Alamo Square from 2:30PM to 8:15PM. You'd like to meet Jessica for a minimum of 75 minutes. Ronald will be at Fisherman's Wharf from 3:15PM to 6:30PM. You'd like to meet Ronald for a minimum of 60 minutes. Mary will be at Union Square from 7:00PM to 10:00PM. You'd like to meet Mary for a minimum of 45 minutes.

SOLUTION:You start at Marina District at 9:00AM. You travel to Alamo Square in 15 minutes and arrive at 9:15AM. You wait until 2:30PM. You meet Jessica for 75 minutes from 2:30PM to 3:45PM. You travel to Fisherman's Wharf in 19 minutes and arrive at 4:04PM. You meet Ronald for 60 minutes from 4:04PM to 5:04PM. You travel to Union Square in 13 minutes and arrive at 5:17PM. You wait until 7:00PM. You meet Mary for 45 minutes from 7:00PM to 7:45PM.

OUTPUT FORMAT:

For your response only output the keyword SOLUTION and the plan, do not output anything else:

SOLUTION:
<your complete meeting plan here>
"""

# Create output directory
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Load meeting planning data
with open("./data/meeting_planning_reduced.json", 'r') as f:
    planning_data = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state  # Current meeting plan
        self.parent = parent  # Parent node
        self.action = action  # Action that led to this state
        self.children = []  # Child nodes
        self.visits = 0  # Number of visits to this node
        self.value = 0  # Value of this node
        self.untried_actions = self._get_untried_actions()
        
    def _get_untried_actions(self):
        # For meeting planning, we'll use different action types:
        # 1. Add new meeting
        # 2. Reorder meetings
        # 3. Adjust meeting durations
        # 4. Change meeting times
        # 5. Full reorganization
        return ["add_meeting", "reorder_meetings", "adjust_durations", "change_times", "full_reorganization"]
        
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


def generate_plan_variation(task, current_plan, action, start_location, initial_time, constraints, dist_matrix):
    """Use LLM to generate a variation of the current meeting plan based on the action"""
    
    action_prompts = {
        "add_meeting": "Try to add one more meeting with a friend you haven't met yet.",
        "reorder_meetings": "Try reordering the meetings to fit more friends into your schedule.",
        "adjust_durations": "Adjust the duration of meetings (keep them at or above the minimum required time) to create space for more meetings.",
        "change_times": "Adjust when meetings begin and end to optimize the schedule.",
        "full_reorganization": "Completely reorganize the meeting schedule to try to include more friends."
    }
    
    instruction = f"""
You have been asked to solve the following meeting planning task:
TASK:
{task}

Your current meeting plan is:
{current_plan if current_plan else "No plan created yet."}

Please create a new variation of this plan by: {action_prompts[action]}
Make sure your plan follows the correct format for start, meeting, travel, and waiting steps.
Try to meet as many friends as possible within the given constraints.
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
    
    if "SOLUTION:" in content:
        new_plan = content.split("SOLUTION:")[1].strip()
    else:
        new_plan = content.strip()
    
    return new_plan


def evaluate_plan(plan, start_location, initial_time, constraints, dist_matrix):
    """Evaluate the quality of a meeting plan"""
    try:
        parsed_plan = parse_text_plan(plan)
        failed_constraints = validate_constraints(parsed_plan, constraints, start_location, initial_time, dist_matrix)
        
        # Count the number of valid meetings in the plan
        meeting_count = sum(1 for step in parsed_plan if step[0] == 'meeting')
        
        # If there are constraint failures, penalize the score
        if failed_constraints:
            return meeting_count / (len(failed_constraints) + 10.0)  # Penalize failures
        
        # Return the number of meetings as the score
        return meeting_count
    except Exception as e:
        # If plan parsing fails, return a very low score
        print(f"Error evaluating plan: {e}")
        return 0.01


def run_mcts(task, start_location, initial_time, constraints, dist_matrix, num_simulations):
    """Run Monte Carlo Tree Search for meeting planning"""
    # Initialize with empty plan
    root = MCTSNode(state="")
    
    # Log file
    log_path = f"{OUTPUT_DIR}/mcts_log_{int(time.time())}.md"
    
    with open(log_path, 'w') as log_file:
        log_file.write(f"# MCTS Meeting Planning\n\n**Task:**\n{task}\n\n")
        
        best_plan = ""
        best_score = -1
        
        for i in range(num_simulations):
            log_file.write(f"\n## Simulation {i+1}\n\n")
            
            # Selection phase - traverse tree to find leaf node
            node = root
            depth = 0
            
            while node.is_fully_expanded() and node.children and depth < MAX_DEPTH:
                node = node.select_child(EXPLORATION_WEIGHT)
                depth += 1
                
            log_file.write(f"Selected node at depth {depth}\n")
            if node.state:
                log_file.write(f"Current plan:\n{node.state}\n\n")
            
            # Expansion phase - if possible, expand node
            if not node.is_fully_expanded() and depth < MAX_DEPTH:
                action = random.choice(node.untried_actions)
                new_plan = generate_plan_variation(
                    task, 
                    node.state, 
                    action, 
                    start_location, 
                    initial_time, 
                    constraints, 
                    dist_matrix
                )
                child_node = node.expand(action, new_plan)
                log_file.write(f"Expanded with action: {action}\nNew plan:\n{child_node.state}\n\n")
                
                # Use the child node for evaluation
                eval_node = child_node
            else:
                # Use the selected node for evaluation
                eval_node = node
            
            # Simulation phase - evaluate the node
            current_score = evaluate_plan(eval_node.state, start_location, initial_time, constraints, dist_matrix)
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
        
        # Final results
        log_file.write(f"\n\n# Final Results\n\nBest plan (score: {best_score}):\n{best_plan}\n")
    
    return best_plan, best_score, log_path


def main():
    solutions = {}
    
    for k, d in list(planning_data.items()):
        print(f"\nProcessing example {k}")
        
        start_location, initial_time = d["constraints"][0]
        constraints = process_constraints(d["constraints"][1:])
        dist_matrix = d["dist_matrix"]
        
        # Run MCTS
        best_plan, score, log_path = run_mcts(
            task=d['prompt_0shot'],
            start_location=start_location,
            initial_time=initial_time,
            constraints=constraints,
            dist_matrix=dist_matrix,
            num_simulations=NUM_SIMULATIONS
        )
        
        print(f"Best plan found with score {score}")
        print(f"Log written to {log_path}")
        
        # Store solution
        solutions[k] = {
            'example_id': k,
            'pred_mcts': best_plan,
            'score': score,
            'constraints': d['constraints'],
            'prompt_0shot': d['prompt_0shot']
        }
        
    # Save all solutions
    with open(f"./output/meeting_mcts_solutions.json", 'w') as f:
        json.dump(solutions, f, indent=2)
    
    print("\nCompleted all examples!")


if __name__ == "__main__":
    main()
