from datasets import load_dataset

# Load the SWE-bench Lite dataset (e.g., "train", "validation", or "test" split)
# Adjust split as appropriate for your experiments
dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="dev")


for i, instance in enumerate(dataset):
    print(instance['instance_id'])
    print(instance['repo'])
    print(instance['problem_statement'])
    print(instance['base_commit'])
    print("\n\n")
