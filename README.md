# LLMPC: Large Language Model Predictive Control

This repository contains experiments comparing Large Language Models (LLMs) with classic planning and control approaches across three domains:

1. Spring-mass system control
2. Trip planning
3. Meeting scheduling

## Project Structure

```

llmpc/
├── spring/ # Spring-mass control experiments
│ ├── mpc.py # Traditional MPC implementation
│ ├── llmpc.py # LLM-based predictive control
│ └── lib.py # Shared utilities
│
├── trip_planner/ # Trip planning experiments
│ ├── run.py # Baseline implementation
│ ├── llmpc_v2.py # LLM-based planning with constraints
│ ├── mcts_trip_planner.py # MCTS-guided planning
│ └── lib.py # Shared utilities
│
├── meeting_planning/ # Meeting scheduling experiments
│ ├── run.py # Baseline implementation
│ ├── llmpc.py # Sequential LLM-based planning
│ ├── llmpc_multi.py # Multi-plan variant of LLMPC
│ ├── mcts_meeting_planner.py # MCTS-guided meeting planning
│ └── evaluate_meeting_planning_llmpc.py # Evaluation utilities
│
└── README.md # This file

```

## Requirements

You'll need Python 3.8+ and the following libraries:

```bash
pip install numpy matplotlib cvxpy pandas openai
```

You'll also need an OpenAI API key. Set it as an environment variable:

```bash
export OPENAI_KEY='your-api-key-here'
```

## Running Experiments

### Spring-Mass Control

The spring-mass experiments compare traditional MPC with an LLM-based controller.

1. Run traditional MPC:

```bash
cd spring
python mpc.py
```

This will generate an animation of the spring-mass system and save results in `output/mpc.csv`

2. Run LLM-based control:

```bash
cd spring
python llmpc.py
```

This will generate an animation and save results in `output/llmpc.csv`

### Trip Planning

The trip planning experiments compare different approaches for planning multi-city visits:

1. Run baseline approach:

```bash
cd trip_planner
python run.py
```

2. Run LLMPC-based trip planning:

```bash
cd trip_planner
python llmpc_v2.py
```

3. Run MCTS-guided trip planning:

```bash
cd trip_planner
python mcts_trip_planner.py
```

Results will be stored in the `output/` directory.

### Meeting Planning

The meeting planning experiments compare different approaches for scheduling meetings:

1. Run baseline approach:

```bash
cd meeting_planning
python run.py
```

2. Run sequential LLMPC-based planning:

```bash
cd meeting_planning
python llmpc.py
```

3. Run multi-plan variant of LLMPC:

```bash
cd meeting_planning
python llmpc_multi.py
```

4. Run MCTS-guided meeting planning:

```bash
cd meeting_planning
python mcts_meeting_planner.py
```

Results will be stored in the `output/` directory.

## Implementation Details

### Spring-Mass Control

- `mpc.py`: Implements traditional Model Predictive Control using cvxpy for optimization
- `llmpc.py`: Uses GPT-4o to generate control sequences, simulates them, and picks the best one
- `lib.py`: Contains shared utilities for both implementations

### Trip Planning

- `run.py`: Baseline implementation using straightforward LLM prompting
- `llmpc_v2.py`: Implements iterative planning with constraint feedback
- `mcts_trip_planner.py`: Uses Monte Carlo Tree Search to guide LLM planning

### Meeting Planning

- `run.py`: Baseline implementation using straightforward LLM prompting
- `llmpc.py`: Implements sequential planning with constraint feedback
- `llmpc_multi.py`: Extends LLMPC to consider multiple plans at each iteration
- `mcts_meeting_planner.py`: Uses Monte Carlo Tree Search to guide meeting planning
- `evaluate_meeting_planning_llmpc.py`: Utilities for evaluating meeting plans

## Output

All experiment results are saved in the `output/` directory, with specific subfolders for each approach:

- Spring control: `mpc.csv`, `llmpc.csv`, and GIF animations
- Trip planning: JSON files with solution plans and detailed logs
- Meeting planning: JSON files with solution plans and detailed logs

## Notes

- All experiments use GPT-4o with different prompting strategies
- The Monte Carlo Tree Search implementations balance exploration vs. exploitation
- All experiments use seeds for reproducibility
