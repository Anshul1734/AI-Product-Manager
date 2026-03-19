import re

wf_path = r'e:\Agentic PM\backend\orchestrator\langgraph_workflow.py'
with open(wf_path, 'r', encoding='utf-8') as f:
    wf = f.read()

# Replace state.X with state['X']
wf = re.sub(r'state\.([a-zA-Z_]\w*)', r'state["\1"]', wf)

# Fix back 'state.values' in get_workflow_state
wf = wf.replace('state["values"] if state', 'state.values if state')

# Fix initial_state initialization block
old_init = '''            initial_state = WorkflowState(
                product_idea=product_idea,
                current_step="start"
            )'''

new_init = '''            initial_state = {
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

# Fix the dict calls since we already made initial_state a dict
wf = wf.replace('initial_state.dict()', 'initial_state')

with open(wf_path, 'w', encoding='utf-8') as f:
    f.write(wf)

print("Refactor complete.")
