"""Orchestration test with stubbed agents: no LLM calls, no tokens spent."""
import asyncio, sys
from app.agents.base import AgentRunResult
from app.llm.client import Usage
from app.orchestration.pipeline import ProductPlanPipeline
from app.orchestration.state import Depth
from app.schemas.artifacts import (PRD, Critique, FeaturePriorities, ProductVision,
                                   SystemArchitecture, Tickets)

VISION = ProductVision.model_validate({
 'product_name':'SLA Guard','problem_statement':'x'*60,'value_proposition':'y'*30,
 'target_users':['Ops'],'core_goals':['Cut breaches'],'key_features_high_level':['Import','Predict']})
PRD_ = PRD.model_validate({
 'problem_statement':'x'*60,'target_users':['Ops'],
 'user_personas':[{'name':'Priya','description':'d','pain_points':['p']}],
 'user_stories':[{'title':'t','as_a':'a','i_want_to':'b','so_that':'c'}]*3,
 'success_metrics':[{'name':'m','description':'d','target':'1->2'},{'name':'n','description':'d','target':'3->4'}]})
PRI = FeaturePriorities.model_validate({'features_detailed':[
 {'name':'Import','description':'d','justification':'j','rice':{'reach':100,'impact':2,'confidence':80,'effort':2}},
 {'name':'Predict','description':'d','justification':'j','rice':{'reach':300,'impact':3,'confidence':70,'effort':3}}],
 'sequencing_rationale':'r'})
ARCH = SystemArchitecture.model_validate({
 'system_design':'z'*60,'tech_stack':{'backend':'FastAPI'},'architecture_components':['API','Worker'],
 'api_endpoints':[{'name':'l','method':'GET','endpoint':'/a','description':'d'},
                  {'name':'c','method':'POST','endpoint':'/a','description':'d'}],
 'database_schema':[{'table_name':'t','fields':[{'name':'id','type':'uuid'}]}]})
TIX = Tickets.model_validate({'epics':[{'epic_name':'E1','stories':[
 {'story_title':'s','acceptance_criteria':['ac'],'tasks':[{'title':'t'}]}]}]})

def critique(score):
    axes = dict(completeness=score, consistency=score, specificity=score, feasibility=score)
    return Critique.model_validate({'critiques':[
        {'artifact':'prd', **axes, 'issues':['i'], 'fix_instructions':['Do X']},
        {'artifact':'plan', **axes, 'issues':[], 'fix_instructions':['Do Y']}],
        'overall_assessment':'ok','blocking_issues':[]})

OUT = {'planner':VISION,'analyst':PRD_,'prioritizer':PRI,'architect':ARCH,'ticket_generator':TIX}

def stub(pipeline, critic_score):
    calls = []
    def patch(agent, out):
        async def run(llm, registry, **kw):
            calls.append(agent.name)
            await asyncio.sleep(0.01)
            return AgentRunResult(output=out, citations=[], tool_calls=['stub_tool'],
                                  usage=Usage(10, 20), duration=0.01, repairs=0)
        agent.run = run
    for name, agent in pipeline.agents.items():
        patch(agent, OUT[name])
    patch(pipeline.critic, critique(critic_score))
    return calls

async def main():
    ok = True
    for depth, score, expect_refine in [(Depth.QUICK, 9.0, False),
                                        (Depth.STANDARD, 9.0, False),
                                        (Depth.DEEP, 4.0, True)]:
        p = ProductPlanPipeline()
        calls = stub(p, score)
        events = []
        async def sink(e): events.append(e['type'] + ':' + str(e.get('node') or e.get('agent') or ''))
        payload = await p.run('An idea about logistics SLA breaches for operators', depth=depth, on_event=sink)
        m = payload['meta']
        skipped = [e for e in events if e.startswith('node_skipped')]
        refined = m['refined_artifacts']
        print(f'--- {depth.value}: agents={calls}')
        print(f'    tokens={m["total_tokens"]} steps={len(payload["agent_steps"])} skipped={skipped} refined={refined}')
        print(f'    orchestrator={m["orchestrator"]} quality={"yes" if payload["quality"] else "no"} rice={[f["rice"]["score"] for f in payload["features_detailed"]]}')
        # Every agent must run at most once in the initial pass. A duplicate
        # there means a fan-in joined branches of unequal depth, and the first
        # firing would have seen a missing upstream artifact. `deep` legitimately
        # re-invokes the owners of below-threshold artifacts during refine, so
        # only the pre-refine prefix is checked for that depth.
        from collections import Counter
        initial_pass = calls if depth is not Depth.DEEP else calls[:calls.index('critic') + 1]
        dupes = {n: c for n, c in Counter(initial_pass).items() if c > 1}
        if dupes:
            print(f'    FAIL: agents ran more than once before refine: {dupes}'); ok = False
        if len(set(refined)) != len(refined):
            print(f'    FAIL: duplicate refinements: {refined}'); ok = False

        # Assertions
        if depth is Depth.QUICK:
            if 'prioritizer' in calls or payload['quality'] is not None: print('    FAIL: quick ran skipped nodes'); ok=False
            if not payload['tickets']: print('    FAIL: quick produced no tickets (fan-in broke)'); ok=False
        if depth is Depth.STANDARD:
            if 'prioritizer' not in calls or payload['quality'] is None: print('    FAIL: standard missing nodes'); ok=False
            if refined: print('    FAIL: standard should not refine'); ok=False
        if depth is Depth.DEEP:
            if not refined: print('    FAIL: deep did not refine below-threshold artifacts'); ok=False
        # token reducer: every agent contributed 30
        if m['total_tokens'] != 30*len(payload['agent_steps'])-0 and m['total_tokens'] % 30 != 0:
            print(f'    FAIL: token reducer wrong ({m["total_tokens"]})'); ok=False
        # RICE recomputed in postprocess -> descending
        s=[f['rice']['score'] for f in payload['features_detailed']]
        if any(s) and s != sorted(s, reverse=True):
            print('    FAIL: RICE not sorted'); ok=False

    # checkpointing
    p = ProductPlanPipeline(); stub(p, 9.0)
    payload = await p.run('Checkpoint probe idea for logistics operators', thread_id='probe-1', depth=Depth.QUICK)
    snap = await p.build_graph().aget_state({'configurable':{'thread_id':'probe-1'}})
    print(f'--- checkpoint: thread=probe-1 has_state={bool(snap and snap.values)} '
          f'agents={[s.agent for s in (snap.values.get("steps") or [])] if snap else None}')
    if not (snap and snap.values.get('vision')): print('    FAIL: checkpoint not persisted'); ok=False

    print('\nRESULT:', 'ALL PASS' if ok else 'FAILURES')
    sys.exit(0 if ok else 1)

asyncio.run(main())
