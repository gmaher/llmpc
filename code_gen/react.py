import os
from tools import CodeGenerator
from openai import OpenAI

def main():
    system_prompt = """You are an expert code generation AI that creates high quality, clean, modular maintainable code.

    You will be given a software project from a client, and you should produce the complete finished code in its entirety.
    When you are done the code should be in a state where it is presentable to the client and the project would be considered complete.
    Fill out all details, do not leave unfinished or placeholder code in your final output.
    You are allowed to produce multiple files and organize the code however you see fit.
    
    When completing the code you are allowed to perform a number of thinking, designing and prototyping steps before producing the final output.
    At each step first output a section header, e.g. # Thinking, then produce the output for that section, finally decide on what the next step will be, e.g. "I need to do some prototyping now" or "I am now ready to produce the final output".
    You can go back and forth between thinking, designing and prototyping, use as many steps as you need.
    The final output section should have a header # Final Output, it should be the last step and should contain the finished code.
    The first section of your output should always be a # Thinking step.

    Here is an example template of what your output could look like:

    # Thinking
    <insert reasoning and thinking about the client project>

    Now I will do some designing

    # Designing
    <Insert design for the project based on previous thoughts>

    Since I have a design I will now do some prototyping
    
    # Prototyping
    <Insert generated code prototype based on design>

    Now let me analyze the prototype and see if it meets the requirements

    # Analysis
    <Analyze prototype, did it satisfy the client request?>

    The prototype is almost there but missing a few requirements namely ..., let me do some more prototyping

    # Prototyping
    <Create v2 prototype with missing requirements>

    The prototype looks good, let me now produce the final output

    # Final Output
    <Produce final output files>

    """

    api_key = os.getenv("OPENAI_KEY")
    if not api_key:
        raise ValueError("OPENAI_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    instruction = """The client has asked you to complete the following project:
    
    Create Flappy Bird in javascript, html and css
    
    Now complete the project while following the instructions in the system prompt."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages = [{"role":"system","content":system_prompt},
                    {"role":"user","content":instruction}],
        temperature=0.5,
        max_tokens=8192
    )

    content = response.choices[0].message.content

    f = open("zeroshot.md",'w')
    f.write(content)
    f.close()

if __name__ == "__main__":
    main()