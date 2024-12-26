# LLMPC: Large Language Model Predictive Control

This repository contains experiments comparing Large Language Models (LLMs) with Model Predictive Control (MPC) and ReAct approaches on two different domains:

1. Spring-mass system control
2. Code generation

## Project Structure

```

llmpc/
├── spring/ # Spring-mass control experiments
│ ├── mpc.py # Traditional MPC implementation
│ └── llmpc.py # LLM-based control implementation
├── code_gen/ # Code generation experiments
│ ├── react.py # ReAct implementation
│ └── llmpc.py # LLM planning implementation
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

### Code Generation

The code generation experiments compare ReAct with an LLM planning approach for generating code (Flappy Bird implementation).

1. Run ReAct-based generation:

```bash
cd code_gen
python react.py
```

This will save the generation process in `zeroshot.md`

2. Run LLM planning-based generation:

```bash
cd code_gen
python llmpc.py
```

This will save the generation process in `output/llmpc.md`

## Implementation Details

### Spring-Mass Control

- `mpc.py`: Implements traditional Model Predictive Control using cvxpy for optimization
- `llmpc.py`: Uses GPT-4o-mini to generate control sequences, simulates them, and picks the best one

### Code Generation

- `react.py`: Implements the ReAct approach with a single-shot generation
- `llmpc.py`: Implements an iterative planning and execution loop for code generation

## Output

All experiment results are saved in the `output/` directory:

- `mpc.csv` and `llmpc.csv`: Spring-mass control trajectories and costs
- `llmpc.md`: Code generation process logs
- `zeroshot.md`: ReAct generation process logs

## Notes

- The spring-mass experiments include visualizations using matplotlib
- The code generation experiments use GPT-4 with different prompting strategies
- Both experiments use a seed for reproducibility
