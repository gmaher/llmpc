import os
import re
import json
from openai import OpenAI
from typing import List, Tuple

class FileTools:
    def __init__(self, base_dir: str = "./"):
        self.base_dir = os.path.join(base_dir, "files")
        self.removed_dir = os.path.join(base_dir, "removed")
        os.makedirs(self.removed_dir, exist_ok=True)

    def create_file(self, filename: str) -> bool:
        try:
            filepath = os.path.join(self.base_dir, filename)
            with open(filepath, 'w') as f:
                pass
            return True
        except Exception as e:
            print(f"Error creating file: {e}")
            return False

    def append_to_file(self, filename: str, content: str) -> bool:
        try:
            filepath = os.path.join(self.base_dir, filename)
            with open(filepath, 'a') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error appending to file: {e}")
            return False

    def modify_file(self, filename: str, start_line: int, end_line: int, content: str) -> bool:
        try:
            filepath = os.path.join(self.base_dir, filename)
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Convert content to lines
            new_lines = content.split('\n')
            if not new_lines[-1].strip():
                new_lines = new_lines[:-1]
            
            # Replace lines
            lines[start_line:end_line+1] = [line + '\n' for line in new_lines]
            
            with open(filepath, 'w') as f:
                f.writelines(lines)
            return True
        except Exception as e:
            print(f"Error modifying file: {e}")
            return False

    def remove_file(self, filename: str) -> bool:
        try:
            source = os.path.join(self.base_dir, filename)
            destination = os.path.join(self.removed_dir, filename)
            os.rename(source, destination)
            return True
        except Exception as e:
            print(f"Error removing file: {e}")
            return False

class CodeGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.tools = FileTools()
        
    def parse_tool_calls(self, text: str) -> List[Tuple[str, dict]]:
        # Regular expression to match tool calls
        pattern = r'<tool>(.*?)</tool>'
        tool_calls = re.findall(pattern, text, re.DOTALL)
        
        parsed_calls = []
        for call in tool_calls:
            try:
                call_data = json.loads(call)
                parsed_calls.append((call_data['name'], call_data['arguments']))
            except:
                print(f"Failed to parse tool call: {call}")
                
        return parsed_calls

    def execute_tool_calls(self, tool_calls: List[Tuple[str, dict]]) -> List[bool]:
        results = []
        for tool_name, args in tool_calls:
            if tool_name == "CREATE_FILE":
                result = self.tools.create_file(args['filename'])
            elif tool_name == "APPEND_TO_FILE":
                result = self.tools.append_to_file(args['filename'], args['content'])
            elif tool_name == "MODIFY_FILE":
                result = self.tools.modify_file(
                    args['filename'],
                    args['start_line'],
                    args['end_line'],
                    args['content']
                )
            elif tool_name == "REMOVE_FILE":
                result = self.tools.remove_file(args['filename'])
            else:
                print(f"Unknown tool: {tool_name}")
                result = False
            results.append(result)
        return results

    def generate(self, system_prompt:str, prompt: str, seed=0) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            seed=seed
        )

        # Get the response content
        content = response.choices[0].message.content

        # Parse and execute tool calls
        tool_calls = self.parse_tool_calls(content)
        results = self.execute_tool_calls(tool_calls)

        # Print the response and results
        print("Assistant response:")
        print(content)
        print("\nTool execution results:")
        for (tool_name, args), result in zip(tool_calls, results):
            print(f"{tool_name}: {'Success' if result else 'Failed'}")

        return content