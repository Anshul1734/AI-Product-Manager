import glob

agent_files = glob.glob(r'e:\Agentic PM\backend\agents\*.py')

for path in agent_files:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    
    # We want to remove any line that just contains a closing parenthesis `)` 
    # immediately following the `gemini-1.0-pro` initialization.
    
    for i in range(len(lines)):
        line = lines[i]
        if line.strip() == ')' and i > 0 and 'genai.GenerativeModel("gemini-1.0-pro")' in lines[i-1]:
            continue
        new_lines.append(line)
        
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

print("Syntax fixed")
