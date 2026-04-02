from crewai import Agent
from crew.agents import create_neighborhood_advocate, create_efficiency_specialist


def test_advocate_is_crewai_agent_instance():
    # Verify the factory returns a usable CrewAI Agent without crashing
    agent = create_neighborhood_advocate()
    assert isinstance(agent, Agent)


def test_specialist_is_crewai_agent_instance():
    # Verify the factory returns a usable CrewAI Agent without crashing
    agent = create_efficiency_specialist()
    assert isinstance(agent, Agent)


def test_advocate_returns_independent_instances():
    # Each call must produce a separate object — no shared mutable state
    a1 = create_neighborhood_advocate()
    a2 = create_neighborhood_advocate()
    assert a1 is not a2


def test_specialist_returns_independent_instances():
    # Each call must produce a separate object — no shared mutable state
    s1 = create_efficiency_specialist()
    s2 = create_efficiency_specialist()
    assert s1 is not s2
