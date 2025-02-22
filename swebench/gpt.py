#!/usr/bin/env python3

import os
import json
import openai
from datasets import load_dataset

# Set your OpenAI API key via env var or directly here:
# openai.api_key = "sk-XXXX"
openai.api_key = os.getenv("OPENAI_API_KEY")

# A system prompt that guides the model to produce only a valid patch.
SYSTEM_PROMPT = """\
You are an AI coding assistant. You will be given:
1. A description of the issue to be fixed.
2. A codebase reference (repository name, base commit, and relevant code snippets).

Your job is to generate a unified diff patch (in .patch format) that resolves the described issue. 
Please observe the following requirements:
- Return only the patch content (no extra markdown, no explanations).
- The patch should begin with the standard 'diff --git' line, followed by file paths, indices, etc., 
  in valid unified diff form.
- Ensure the patch is syntactically correct so it can be applied using `git apply`.
"""

# A user prompt template that injects the problem statement and code context
USER_PROMPT_TEMPLATE = """\
Issue Description:
{problem_statement}

Repository: {repo}
Base Commit: {base_commit}

Please produce a unified diff patch that fixes the issue above. 
"""

def generate_patch_for_instance(instance, openai_model="gpt-4"):
    """
    Given a single SWE-bench instance and a model name, query OpenAI to produce a patch.
    """
    # Extract the relevant fields from the dataset instance
    problem_statement = instance["problem_statement"]
    repo = instance["repo"]
    base_commit = instance["base_commit"]
    # You could extract additional fields or code context if desired

    user_prompt = USER_PROMPT_TEMPLATE.format(
        problem_statement=problem_statement,
        repo=repo,
        base_commit=base_commit
    )

    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,  # Adjust as needed
        max_tokens=1500   # Adjust as needed
    )

    # The patch is in the assistant's reply
    patch_text = response["choices"][0]["message"]["content"]
    return patch_text.strip()

def main():
    # Load the SWE-bench Lite dataset (e.g., "train", "validation", or "test" split)
    # Adjust split as appropriate for your experiments
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    
    predictions = []

    for i, instance in enumerate(dataset):
        try:
            # Generate the patch
            patch = generate_patch_for_instance(
                instance,
                openai_model="gpt-4"  # or "gpt-3.5-turbo" or any other ChatCompletion model
            )
            
            # Build a single prediction record
            prediction_record = {
                "instance_id": instance["instance_id"],
                "model_patch": patch,
                "model_name_or_path": "OpenAI GPT-4"
            }
            
            predictions.append(prediction_record)
            
            # Print or log progress as needed
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1} instances...")
            
        except Exception as e:
            print(f"Error processing instance {instance['instance_id']}: {e}")

    # Write out predictions to a JSON file
    output_filename = "predictions_swebench.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    print(f"Finished! Wrote {len(predictions)} predictions to {output_filename}")

if __name__ == "__main__":
    main()
