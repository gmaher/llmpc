import os
from tools import CodeGenerator
from openai import OpenAI

system_prompt ="""
You are an intelligent software engineering AI assistant.
You write clear, concise and modular maintainable code.

You have been asked to complete the following project:
{goal}

The previous actions you took are:
{actions}

The relevant project state context is:
{context}

"""

prompt_planner = """
Now plan the next {k} steps to achieve the goal.

Format your output as:

PLAN:
1. <first step>
2. <second step>
...
"""

prompt_executor = """
The next steps for you to execute are:
{plan}

You have access to the following tools:
- CREATE_FILE(filename): Creates a new empty file
- APPEND_TO_FILE(filename, content): Adds content to the end of a file
- MODIFY_FILE(filename, start_line, end_line, content): Replaces file content from start_line (inclusive) to end_line (inclusive) with supplied content
- REMOVE_FILE(filename): Moves a file to the removed folder

When using tools, wrap the tool call in <tool></tool> tags and format as JSON:
<tool>
{{
    "name": "CREATE_FILE",
    "arguments": {{
        "filename": "example.txt"
    }}
}}
</tool>

Only ever submit one MODIFY_FILE call per file. Submitting multiple MODIFY_FILE calls for the same file does not work.

Now please execute the plan.
"""

class LLMPC:
    def __init__(self, api_key: str, goal: str, output_log=None, seed=0):
        self.generator = CodeGenerator(api_key)
        self.goal = goal
        self.actions = []
        self.context = ""

        self.output_log = output_log
        self.seed=seed

    def update_context(self):
        files_context = []
        files_dir = "./files"
        
        if not os.path.exists(files_dir):
            return
            
        for filename in os.listdir(files_dir):
            file_path = os.path.join(files_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    numbered_lines = [f"{i} {line.rstrip()}" for i, line in enumerate(lines)]
                    files_context.append(f"File: {filename}\n" + "\n".join(numbered_lines))
        
        self.context = "\n\n".join(files_context)

    def get_system_prompt(self, template: str, **kwargs) -> str:
        self.update_context()  # Update context before generating prompt
        return template.format(
            goal=self.goal,
            actions="\n".join(f"- {action}" for action in self.actions),
            context=self.context,
            **kwargs
        ) 

    def plan(self, k: int = 3) -> list:
        prompt = self.get_system_prompt(system_prompt)
        instruction = prompt_planner.format(k=k)
        print(prompt, instruction)
        response = self.generator.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}, 
            {"role":"user", "content":instruction}],
            temperature=0.7,
            max_tokens=4096,
            seed=self.seed
        )
        
        # Extract plan steps from response
        content = response.choices[0].message.content

        if self.output_log is not None:
            f = open(self.output_log,'a')
            f.write("# Plan\n")
            #f.write(prompt + "\n")
            #f.write(instruction + "\n")
            #f.write(f"Assistant response:\n {content}\n")
            f.write(f"{content}\n")
            f.close()

        plan_section = content.split("PLAN:")[1].strip()
        steps = []
        for line in plan_section.split("\n"):
            if line.strip() and line[0].isdigit():
                steps.append(line.split(".", 1)[1].strip())
        return steps

    def execute(self, plan: list) -> None:
        plan_string ="\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
        prompt = self.get_system_prompt(system_prompt)
        instruction = prompt_executor.format(plan=plan_string)
        print(prompt, instruction)
        content = self.generator.generate(prompt, instruction, self.seed)

        if self.output_log is not None:
            f = open(self.output_log,'a')
            f.write("# Execute\n")
            #f.write(prompt + "\n")
            #f.write(instruction + "\n")
            #f.write(f"Assistant response:\n {content}\n")
            f.write(f"{content}\n")
            f.close()

        self.actions.extend(plan)

###########
# Main code
###########
# Clean and recreate files directory
if os.path.exists("./files"):
    import shutil
    shutil.rmtree("./files")
os.makedirs("./files")

api_key = os.getenv("OPENAI_KEY")
if not api_key:
    raise ValueError("OPENAI_KEY environment variable not set")

goal = "create flappy bird using html javascript and css"

output_log = "./output/llmpc.md"
f = open(output_log,'w')
f.write("")
f.close()

seed=42

llmpc = LLMPC(api_key, goal, output_log=output_log, seed=seed)

# Run multiple iterations of planning and execution
for iteration in range(3):
    print(f"\nIteration {iteration + 1}")
    print("Planning...")
    plan = llmpc.plan(k=3)  # Get next 3 steps
    
    print("\nGenerated Plan:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step}")
        
    print("\nExecuting plan...")
    llmpc.execute(plan)
    
    # Optional: Add a pause between iterations
    if iteration < 2:
        input("\nPress Enter to continue to next iteration...")
