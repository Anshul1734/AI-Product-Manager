import glob
import re
import os

agent_files = glob.glob(r'e:\Agentic PM\backend\agents\*.py')

for path in agent_files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Needs changes check
    if 'ChatOpenAI' not in content:
        continue

    # Replace imports
    content = re.sub(r'from langchain(_openai|\.chat_models) import ChatOpenAI', 
                     r'from langchain_google_genai import ChatGoogleGenerativeAI\nimport os\nfrom dotenv import load_dotenv\nload_dotenv()', 
                     content)
    
    # Replace instantiations
    # e.g. self.model = ChatOpenAI(model_name=model_name, temperature=0.1)
    # e.g. self.llm = ChatOpenAI(model_name=model_name, temperature=0.2)
    
    def replacer(match):
        pre = match.group(1) # self.model = 
        args = match.group(2) # model_name=model_name, temperature=0.1
        
        # fix model parameter name from model_name to model, and hardcode gemini-1.5-pro or gemini-1.5-flash
        args = re.sub(r'model_name=[^,]+', 'model="gemini-1.5-pro"', args)
        
        # inject google_api_key
        if 'google_api_key' not in args:
            args += ', google_api_key=os.getenv("GEMINI_API_KEY")'
            
        return f'{pre}ChatGoogleGenerativeAI({args})'

    content = re.sub(r'(.*?=\s*)ChatOpenAI\((.*?)\)', replacer, content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {path}")
