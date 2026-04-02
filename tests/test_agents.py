import pytest
from crewai import Agent
from crew.agents import create_neighborhood_advocate, create_efficiency_specialist


def test_advocate_is_crewai_agent_instance():
    # Verify the factory function returns a valid CrewAI Agent object
    agent = create_neighborhood_advocate()
    assert isinstance(agent, Agent)


def test_advocate_role_exact_match():
    # Verify the exact role title for the advocate
    agent = create_neighborhood_advocate()
    assert agent.role == 'Neighborhood Advocate'


def test_advocate_goal_focus_wait_times():
    # Ensure the goal explicitly targets wait times
    agent = create_neighborhood_advocate()
    assert 'wait times' in agent.goal.lower()


def test_advocate_backstory_context_herzliya():
    # Confirm the backstory is localized to the specific city
    agent = create_neighborhood_advocate()
    assert 'herzliya' in agent.backstory.lower()


def test_advocate_delegation_rule_is_false():
    # Confirm the agent processes tasks independently without delegation
    agent = create_neighborhood_advocate()
    assert agent.allow_delegation is False


def test_advocate_verbosity_is_enabled():
    # Ensure verbose mode is on for debugging the agent reasoning
    agent = create_neighborhood_advocate()
    assert agent.verbose is True


def test_specialist_is_crewai_agent_instance():
    # Verify the factory function returns a valid CrewAI Agent object
    agent = create_efficiency_specialist()
    assert isinstance(agent, Agent)


def test_specialist_goal_focus_costs():
    # Ensure the goal explicitly targets operational costs and empty miles
    agent = create_efficiency_specialist()
    assert 'costs' in agent.goal.lower()


def test_specialist_backstory_context_efficiency():
    # Confirm the backstory focuses on logistics and waste reduction
    agent = create_efficiency_specialist()
    assert 'efficiency' in agent.backstory.lower() or 'logistics' in agent.backstory.lower()


def test_specialist_delegation_rule_is_false():
    # Confirm the agent processes tasks independently without delegation
    agent = create_efficiency_specialist()
    assert agent.allow_delegation is False


def test_specialist_verbosity_is_enabled():
    # Ensure verbose mode is on for debugging the agent reasoning
    agent = create_efficiency_specialist()
    assert agent.verbose is True
