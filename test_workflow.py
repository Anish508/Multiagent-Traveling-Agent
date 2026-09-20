import time
import sys
import nest_asyncio

sys.stdout.reconfigure(encoding='utf-8')
nest_asyncio.apply()

from backend import run_travel_agent, resume_travel_agent


def test_guardrail():
    print("=== TEST 1: Input Guardrail Validation ===", flush=True)
    prompt = "Write a python script to implement merge sort algorithm."
    print(f"Prompt: {prompt}", flush=True)
    res = run_travel_agent(prompt)
    print(f"Guardrail Allowed: {res.get('guardrail_allowed')}", flush=True)
    print(f"Supervisor Reasoning: {res.get('supervisor_reasoning')}", flush=True)
    print(f"Requires Approval: {res.get('requires_approval')}", flush=True)
    print(f"Answer: {res.get('answer')[:150]}...", flush=True)
    assert res.get("guardrail_allowed") is False, "Guardrail should have blocked non-travel query!"
    print(">>> PASS: Guardrail successfully blocked unrelated query.\n", flush=True)


def test_travel_workflow():
    print("=== TEST 2: Multi-Agent Travel Planner & HITL ===", flush=True)
    prompt = "Plan a short 3-day budget trip to Tokyo, Japan with flight and top sight recommendations."
    print(f"Prompt: {prompt}", flush=True)

    start = time.time()
    res = run_travel_agent(prompt)
    duration = time.time() - start

    thread_id = res.get("thread_id")
    print(f"Completed in: {duration:.2f}s", flush=True)
    print(f"Thread ID: {thread_id}", flush=True)
    print(f"Guardrail Allowed: {res.get('guardrail_allowed')}", flush=True)
    print(f"Selected Agents: {res.get('selected_agents')}", flush=True)
    print(f"Requires Approval: {res.get('requires_approval')}", flush=True)
    print(f"Draft Itinerary Preview:\n{res.get('itinerary', '')[:300]}...\n", flush=True)

    assert res.get("requires_approval") is True, "Workflow should have paused at HITL step!"
    print(">>> PASS: Draft generated and paused for Human-In-The-Loop approval.\n", flush=True)

    print("=== TEST 3: Resuming Paused Thread with Approval Feedback ===", flush=True)
    feedback = "Approved! Please make sure to highlight vegetarian-friendly food options in Asakusa."
    print(f"Feedback: {feedback}", flush=True)

    resume_res = resume_travel_agent(thread_id, approved=True, feedback=feedback)
    print(f"Approved status: {resume_res.get('approved')}", flush=True)
    print(f"Final Response Preview:\n{resume_res.get('answer', '')[:350]}...\n", flush=True)

    assert resume_res.get("requires_approval") is False, "Resumed workflow should finish final response!"
    print(">>> PASS: Thread resumed and completed master travel plan.\n", flush=True)


def main():
    test_guardrail()
    test_travel_workflow()
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!", flush=True)


if __name__ == "__main__":
    main()
