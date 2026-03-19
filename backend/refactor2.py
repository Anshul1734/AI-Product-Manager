import re

wf_path = r'e:\Agentic PM\backend\orchestrator\workflow.py'
with open(wf_path, 'r', encoding='utf-8') as f:
    wf = f.read()

# Replace state.X with state.get('X') or state['X']
wf = re.sub(r'state\.([a-zA-Z_]\w*)', r'state["\1"]', wf)

# In legacy workflow, we need to fix object initialization:
# state = WorkflowState(product_idea=product_idea)
old_init = '''        state = WorkflowState(
            product_idea=product_idea,
            current_step="start"
        )'''

new_init = '''        state = {
            "product_idea": product_idea,
            "plan": None,
            "prd": None,
            "architecture": None,
            "tickets": None,
            "current_step": "start",
            "errors": {},
            "execution_time": {},
            "completed_steps": [],
            "is_complete": False
        }'''
wf = wf.replace(old_init, new_init)

with open(wf_path, 'w', encoding='utf-8') as f:
    f.write(wf)

# Also fix langgraph_workflow.py result.current_step
lg_path = r'e:\Agentic PM\backend\orchestrator\langgraph_workflow.py'
with open(lg_path, 'r', encoding='utf-8') as f:
    lg = f.read()

lg = lg.replace('result.current_step', 'result["current_step"]')

with open(lg_path, 'w', encoding='utf-8') as f:
    f.write(lg)

print("Workflow refactor complete.")
