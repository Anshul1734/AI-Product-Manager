import glob
import re

agent_files = glob.glob(r'e:\Agentic PM\backend\agents\*.py')

for path in agent_files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Imports
    content = re.sub(r'from langchain_google_genai import ChatGoogleGenerativeAI\n', '', content)
    content = re.sub(r'from langchain_core\.messages import.*?\n', '', content)
    if 'import google.generativeai as genai' not in content:
        content = content.replace('import os\n', 'import os\nimport google.generativeai as genai\n', 1)

    # 2. Instantiations
    # e.g. self.llm = ChatGoogleGenerativeAI(...)
    # e.g. self.model = ChatGoogleGenerativeAI(...)
    content = re.sub(r'self\.(llm|model)\s*=\s*ChatGoogleGenerativeAI\([^)]*\)', r'genai.configure(api_key=os.getenv("GEMINI_API_KEY"))\n        self.\1 = genai.GenerativeModel("gemini-1.0-pro")', content)

    # 3. Message arrays and invocations
    # Case A: messages = [SystemMessage(content=self.prompt), HumanMessage(content=prompt)]
    content = re.sub(r'messages\s*=\s*\[\s*SystemMessage\(content=self\.prompt\),\s*HumanMessage\(content=(.*?)\)\s*\]', r'full_prompt = f"{self.prompt}\\n\\n{\1}"', content, flags=re.DOTALL)
    
    # Case B: messages = [HumanMessage(content=...)]
    content = re.sub(r'messages\s*=\s*\[\s*HumanMessage\(content=(.*?)\)\s*\]', r'full_prompt = \1', content, flags=re.DOTALL)

    # 4. Invocations
    # e.g. response = self.llm.invoke(messages)
    # e.g. response = self.model(messages)
    content = re.sub(r'response\s*=\s*self\.(llm|model)\.invoke\(messages\)', r'response = self.\1.generate_content(full_prompt)', content)
    content = re.sub(r'response\s*=\s*self\.(llm|model)\(messages\)', r'response = self.\1.generate_content(full_prompt)', content)

    # 5. Output extraction
    # response.content.strip() or response.content
    content = re.sub(r'response\.content', r'response.text', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Stripped all Langchain wrappers from Agents and flattened prompts.")
