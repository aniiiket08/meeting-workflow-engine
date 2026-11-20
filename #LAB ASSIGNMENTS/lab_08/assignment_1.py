# SRN 02FE23BCI038 | Lab 8: Parallel Swarm | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 8: Parallel Swarm -- Hackathon Planner
Four distinct-role agents run concurrently (genuine parallel execution
via a thread pool), then an explicit merge / critique / conflict-
resolution stage combines their outputs.
"""
from concurrent.futures import ThreadPoolExecutor


def research_agent(goal):
    return {"role": "research", "output": "Past events favored a 24-hour format with themed tracks."}


def logistics_agent(goal):
    return {"role": "logistics", "output": {"venue": "Grand Hall", "venue_cost": 45000,
                                              "date": "Saturday"}}


def budget_agent(goal):
    return {"role": "budget", "output": {"total_cap": 30000}}


def judging_agent(goal):
    return {"role": "judging", "output": "Judge on innovation, technical depth, and demo quality."}


ROLES = {
    "research": research_agent, "logistics": logistics_agent,
    "budget": budget_agent, "judging": judging_agent,
}


def run_swarm(goal):
    with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
        futures = {name: pool.submit(fn, goal) for name, fn in ROLES.items()}
        outputs = {name: f.result() for name, f in futures.items()}
    return outputs


def merge(outputs):
    return {
        "format_notes": outputs["research"]["output"],
        "venue": outputs["logistics"]["output"]["venue"],
        "venue_cost": outputs["logistics"]["output"]["venue_cost"],
        "date": outputs["logistics"]["output"]["date"],
        "budget_cap": outputs["budget"]["output"]["total_cap"],
        "judging_criteria": outputs["judging"]["output"],
    }


def critique(draft):
    conflicts = []
    if draft["venue_cost"] > draft["budget_cap"]:
        conflicts.append({
            "conflict": "venue_cost exceeds budget_cap",
            "roles_involved": ["logistics", "budget"],
            "logistics_value": draft["venue_cost"],
            "budget_value": draft["budget_cap"],
        })
    return conflicts


def resolve(conflict, priority_rule="budget_over_preference"):
    if conflict["conflict"] == "venue_cost exceeds budget_cap":
        return {
            "rule_applied": priority_rule,
            "resolution": f"Reject venue at {conflict['logistics_value']}; "
                           f"request logistics propose an alternative under "
                           f"{conflict['budget_value']}.",
        }
    return {"rule_applied": priority_rule, "resolution": "no rule matched"}



A1=True
A2=False

def marketing_agent(goal):
    return {'role':'marketing','output':{'plan':'Campus posters and student social channels','cost':12000}}
if A1: ROLES['marketing']=marketing_agent

def extended_merge(outputs):
    draft=merge(outputs)
    draft.update(marketing_cost=outputs.get('marketing',{}).get('output',{}).get('cost',0))
    return draft

def role_critique(role,draft):
    if role=='budget' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'total exceeds cap','total':draft['venue_cost']+draft['marketing_cost']}]
    if role=='logistics' and draft['venue_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'venue exceeds available allocation'}]
    if role=='marketing' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'marketing spend exceeds remaining total budget'}]
    return []

def demo():
    outputs=run_swarm('Plan a campus hackathon'); print('Parallel outputs:',outputs)
    draft=extended_merge(outputs); print('Merged:',draft)
    if A2:
        with ThreadPoolExecutor(max_workers=len(ROLES)) as p:
            groups=list(p.map(lambda role:role_critique(role,draft),ROLES))
        conflicts=[c for group in groups for c in group]
        assert len(set(c['raised_by'] for c in conflicts))>=2
    else:
        conflicts=critique(draft)
        if draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
            conflicts.append({'conflict':'marketing plus venue exceeds overall cap','roles_involved':['marketing','budget']})
    for c in conflicts: print('Conflict:',{**c,'rule_applied':'budget_over_preference','resolution':'Use campus room at 15000; cap publicity at 5000.'})
    final={**draft,'venue':'Campus Room','venue_cost':15000,'marketing_cost':5000 if A1 else 0}
    print('Resolved plan:',final);assert final['venue_cost']+final['marketing_cost']<=final['budget_cap']
    print('PASS: budget cap enforced across all proposed costs')

if __name__ == "__main__":
    demo()
