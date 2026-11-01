"""Gold benchmark meetings for evaluating minutes generation and action extraction.

Scripted benchmark: Contains 10 synthetic meeting scenarios designed to test specific edge cases:
1. GPU Cluster Budget (Clear single decision & action with exact deadline)
2. Quarterly Roadmap (Unowned action + owned action with relative day deadline)
3. Smartboards Discussion (Rejected idea, zero decisions, zero actions)
4. Equipment Closet Self-Correction (Speaker corrects deadline from Tuesday to Wednesday)
5. Unowned Infrastructure Task (Action item identified without explicit owner)
6. Mobile App Scope Rejection (Explicit discussion and rejection of mobile app, no action)
7. Relative Deadline Calculation ("by next Friday" relative timing)
8. Duplicate Task Mention (Task discussed by Alice, reiterated later by Bob - deduplication test)
9. Policy Change Decision Only (Consensus policy agreed upon with zero action items generated)
10. Informational Standup Sync (Status updates shared, zero decisions, zero actionable items)
"""
from typing import Any, Dict, List

GOLD_MEETINGS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "GPU Cluster Budget",
        "category": "standard",
        "raw_transcript": (
            "[00:00:10] Alice: Welcome everyone. Let us decide on the GPU cluster budget.\n"
            "[00:00:20] Bob: I suggest $50k.\n"
            "[00:00:30] Alice: Agreed, $50k is approved for the GPU cluster.\n"
            "[00:00:40] Bob: I will procure the GPU cluster by Friday."
        ),
        "gold_decisions": ["$50k approved for the GPU cluster"],
        "gold_actions": [
            {
                "title": "Procure GPU cluster",
                "owner": "Bob",
                "due": "by Friday",
                "quote": "I will procure the GPU cluster by Friday.",
            }
        ],
    },
    {
        "id": 2,
        "name": "Quarterly Roadmap",
        "category": "unowned_and_owned",
        "raw_transcript": (
            "[00:01:00] Charlie: We need to finalize the quarterly roadmap by next Friday.\n"
            "[00:01:10] David: I will draft the roadmap document and send it out for review by Wednesday."
        ),
        "gold_decisions": [],
        "gold_actions": [
            {
                "title": "Finalize quarterly roadmap",
                "owner": None,
                "due": "by next Friday",
                "quote": "We need to finalize the quarterly roadmap by next Friday.",
            },
            {
                "title": "Draft roadmap document",
                "owner": "David",
                "due": "by Wednesday",
                "quote": "I will draft the roadmap document and send it out for review by Wednesday.",
            },
        ],
    },
    {
        "id": 3,
        "name": "Smartboards Discussion",
        "category": "rejected_idea",
        "raw_transcript": (
            "[00:02:00] Elena: Should we buy additional smartboards for the lab? "
            "No, that is out of scope right now.\n"
            "[00:02:15] Frank: Just general discussion, nothing to take action on."
        ),
        "gold_decisions": [],
        "gold_actions": [],
    },
    {
        "id": 4,
        "name": "Self-Correction on Deadline",
        "category": "self_correction",
        "raw_transcript": (
            "[00:03:00] Grace: I will update the security audit report by Tuesday.\n"
            "[00:03:15] Grace: Actually, wait, the vulnerability scans take longer. Make that Wednesday instead.\n"
            "[00:03:30] Henry: Sounds good, Wednesday confirmed."
        ),
        "gold_decisions": [],
        "gold_actions": [
            {
                "title": "Update security audit report",
                "owner": "Grace",
                "due": "by Wednesday",
                "quote": "Make that Wednesday instead.",
            }
        ],
    },
    {
        "id": 5,
        "name": "Unowned Equipment Task",
        "category": "unowned_task",
        "raw_transcript": (
            "[00:04:00] Ian: The server rack wiring in Room 302 is hazardous.\n"
            "[00:04:15] Julia: Yes, someone needs to organize and label the rack cables by Thursday.\n"
            "[00:04:30] Ian: Agreed, let's make sure it gets assigned to whoever is on duty."
        ),
        "gold_decisions": [],
        "gold_actions": [
            {
                "title": "Organize and label server rack cables in Room 302",
                "owner": None,
                "due": "by Thursday",
                "quote": "someone needs to organize and label the rack cables by Thursday.",
            }
        ],
    },
    {
        "id": 6,
        "name": "Mobile App Scope Rejection",
        "category": "rejected_scope",
        "raw_transcript": (
            "[00:05:00] Kevin: Should we develop a native mobile app for student bookings this quarter?\n"
            "[00:05:15] Laura: We examined that proposal and voted no. The mobile app is officially rejected due to budget constraints.\n"
            "[00:05:30] Kevin: Understood, we will stick exclusively to the responsive web portal."
        ),
        "gold_decisions": ["Mobile app proposal is officially rejected"],
        "gold_actions": [],
    },
    {
        "id": 7,
        "name": "Relative Deadline Planning",
        "category": "relative_deadline",
        "raw_transcript": (
            "[00:06:00] Maya: Our accreditation package submission is coming up.\n"
            "[00:06:15] Neil: I will compile the faculty publication index by next Friday.\n"
            "[00:06:30] Maya: Great, that gives us the weekend to review before submission."
        ),
        "gold_decisions": [],
        "gold_actions": [
            {
                "title": "Compile faculty publication index",
                "owner": "Neil",
                "due": "by next Friday",
                "quote": "I will compile the faculty publication index by next Friday.",
            }
        ],
    },
    {
        "id": 8,
        "name": "Duplicate Task Mention Deduplication",
        "category": "duplicate_mention",
        "raw_transcript": (
            "[00:07:00] Olivia: I will order the backup HDMI and power cables this afternoon.\n"
            "[00:07:20] Peter: Good. Let's review the upcoming seminar agenda.\n"
            "[00:07:40] Olivia: Just reiterating what I said earlier, I will definitely order the backup HDMI and power cables today.\n"
            "[00:07:55] Peter: Perfect, thanks Olivia."
        ),
        "gold_decisions": [],
        "gold_actions": [
            {
                "title": "Order backup HDMI and power cables",
                "owner": "Olivia",
                "due": "this afternoon",
                "quote": "I will order the backup HDMI and power cables this afternoon.",
            }
        ],
    },
    {
        "id": 9,
        "name": "Policy Consensus (Decision Without Action)",
        "category": "decision_only",
        "raw_transcript": (
            "[00:08:00] Quinn: The current 8:30 AM departmental sync is too early for team members commuting.\n"
            "[00:08:15] Rachel: How about 10:00 AM instead?\n"
            "[00:08:30] Quinn: All faculty present vote in favor. The standing meeting time is changed to 10:00 AM on Tuesdays.\n"
            "[00:08:45] Rachel: Excellent, no other operational items for today."
        ),
        "gold_decisions": ["Standing meeting time changed to 10:00 AM on Tuesdays"],
        "gold_actions": [],
    },
    {
        "id": 10,
        "name": "Informational Status Standup",
        "category": "no_actionable_items",
        "raw_transcript": (
            "[00:09:00] Sam: Quick round-robin update. All current cloud services are running normally with 99.9% uptime.\n"
            "[00:09:15] Tina: The lab printers received fresh toner cartridges yesterday.\n"
            "[00:09:30] Sam: No new tickets, blockers, or pending actions. Meeting adjourned."
        ),
        "gold_decisions": [],
        "gold_actions": [],
    },
]

