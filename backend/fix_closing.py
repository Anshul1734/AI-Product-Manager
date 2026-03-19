import glob

agent_files = glob.glob(r'e:\Agentic PM\backend\agents\*.py')

for path in agent_files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace double parentheses caused by os.getenv() closure
    content = content.replace('genai.GenerativeModel("gemini-1.0-pro"))', 'genai.GenerativeModel("gemini-1.0-pro")')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Syntax fixed across all agent files.')
