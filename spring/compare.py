import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lib import solve_mpc, simulate_sequence, get_best_llm_plan

# System parameters
m = 1.0       # mass
k_spring = 5.0  # spring stiffness
dt = 0.1      # time step
x_goal = 2.0  # target length

# MPC parameters
H = 3  # horizon length
M = 2   # number of steps to apply before replanning
Qx = 100.0  # state error weight for position
Qv = 100.0   # state error weight for velocity
Qu = 0.1   # control effort weight

# Number of candidate sequences from LLM
K = 15

# Simulation parameters
T = 50

# Initial conditions
x0 = 1.0
v0 = 0.0

def compare_planners():
    # Grid of initial states to test
    x_test = np.linspace(0, 3, 10)
    v_test = np.linspace(-1, 1, 10)
    
    mpc_costs = []
    llm_costs = []
    
    for x in x_test:
        for v in v_test:
            # Get MPC plan and cost
            x_plan, v_plan, u_plan = solve_mpc(x, v, H, dt, m, k_spring, x_goal, Qx, Qv, Qu)
            mpc_cost = simulate_sequence(x, v, u_plan, dt, m, k_spring, x_goal, Qx, Qv, Qu)
            mpc_costs.append(mpc_cost)
            
            # Get LLM plan and cost 
            llm_plan = get_best_llm_plan(x, v, H, K, dt, m, k_spring, x_goal, Qx, Qv, Qu)
            llm_cost = simulate_sequence(x, v, llm_plan, dt, m, k_spring, x_goal, Qx, Qv, Qu)
            llm_costs.append(llm_cost)
            
    # Plot histogram of costs
    plt.figure()
    plt.hist(mpc_costs, alpha=0.5, label='MPC', bins=20)
    plt.hist(llm_costs, alpha=0.5, label='LLM-PC', bins=20)
    plt.xlabel('Cost')
    plt.ylabel('Count') 
    plt.title('Distribution of Planning Costs')
    plt.legend()
    plt.savefig('./output/cost_comparison.png')
    plt.close()
    
    # Save costs to CSV
    df = pd.DataFrame({
        'mpc_costs': mpc_costs,
        'llm_costs': llm_costs
    })
    df.to_csv(f'./output/planner_comparison_K{K}_H{H}.csv')
    
    return np.mean(mpc_costs), np.mean(llm_costs)

if __name__ == "__main__":
    # Run regular simulation
    # ... existing code ...
    
    # Run comparison
    mpc_mean, llm_mean = compare_planners()
    print(f"Mean MPC cost: {mpc_mean}")
    print(f"Mean LLM cost: {llm_mean}")