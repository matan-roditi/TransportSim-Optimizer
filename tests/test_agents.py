from crewai import Agent
from crew.agents import (
    create_demand_analyst,
    create_neighborhood_advocate,
    create_route_architect,
)


def test_neighborhood_advocate_returns_agent_instance():
    # Verify the neighborhood advocate factory returns a CrewAI Agent.
    agent = create_neighborhood_advocate()
    assert isinstance(agent, Agent)


def test_neighborhood_advocate_role():
    # Ensure the neighborhood advocate keeps the expected role identity.
    agent = create_neighborhood_advocate()
    assert agent.role == "Neighborhood Advocate"


def test_neighborhood_advocate_is_verbose():
    # Confirm the neighborhood advocate is configured for verbose execution.
    agent = create_neighborhood_advocate()
    assert agent.verbose is True


def test_neighborhood_advocate_disables_delegation():
    # Verify the neighborhood advocate cannot delegate work to other agents.
    agent = create_neighborhood_advocate()
    assert agent.allow_delegation is False


def test_neighborhood_advocate_goal_mentions_wait_times():
    # Check that the advocate goal stays focused on passenger wait times.
    agent = create_neighborhood_advocate()
    assert "wait time" in agent.goal.lower()


def test_neighborhood_advocate_backstory_mentions_transit_access():
    # Ensure the advocate backstory reflects transit-equity concerns.
    agent = create_neighborhood_advocate()
    assert "transit access" in agent.backstory.lower()


def test_neighborhood_advocate_returns_independent_instances():
    # Confirm each factory call creates a fresh advocate agent instance.
    first = create_neighborhood_advocate()
    second = create_neighborhood_advocate()
    assert first is not second


def test_demand_analyst_returns_agent_instance():
    # Verify the demand analyst factory returns a CrewAI Agent.
    agent = create_demand_analyst()
    assert isinstance(agent, Agent)


def test_demand_analyst_role():
    # Ensure the demand analyst keeps the expected role identity.
    agent = create_demand_analyst()
    assert agent.role == "Demand and Flow Analyst"


def test_demand_analyst_is_verbose():
    # Confirm the demand analyst is configured for verbose execution.
    agent = create_demand_analyst()
    assert agent.verbose is True


def test_demand_analyst_disables_delegation():
    # Verify the demand analyst cannot delegate work to other agents.
    agent = create_demand_analyst()
    assert agent.allow_delegation is False


def test_demand_analyst_goal_mentions_origin_destination_data():
    # Check that the analyst goal references origin-destination analysis.
    agent = create_demand_analyst()
    assert "origin-destination" in agent.goal.lower()


def test_demand_analyst_backstory_mentions_missing_connections():
    # Ensure the analyst backstory emphasizes finding missing links in the network.
    agent = create_demand_analyst()
    assert "missing" in agent.goal.lower() or "stranded" in agent.backstory.lower()


def test_demand_analyst_returns_independent_instances():
    # Confirm each factory call creates a fresh demand analyst instance.
    first = create_demand_analyst()
    second = create_demand_analyst()
    assert first is not second


def test_route_architect_returns_agent_instance():
    # Verify the route architect factory returns a CrewAI Agent.
    agent = create_route_architect()
    assert isinstance(agent, Agent)


def test_route_architect_role():
    # Ensure the route architect keeps the expected role identity.
    agent = create_route_architect()
    assert agent.role == "Chief Route Architect"


def test_route_architect_is_verbose():
    # Confirm the route architect is configured for verbose execution.
    agent = create_route_architect()
    assert agent.verbose is True


def test_route_architect_disables_delegation():
    # Verify the route architect cannot delegate work to other agents.
    agent = create_route_architect()
    assert agent.allow_delegation is False


def test_route_architect_goal_mentions_stop_redesign():
    # Check that the architect goal remains focused on redesigning stop sequences.
    agent = create_route_architect()
    assert "sequence of stops" in agent.goal.lower()


def test_route_architect_backstory_mentions_avoiding_schedule_changes():
    # Ensure the architect backstory keeps topology separate from scheduling changes.
    agent = create_route_architect()
    assert "scheduling or frequency changes" in agent.backstory.lower()


def test_route_architect_returns_independent_instances():
    # Confirm each factory call creates a fresh route architect instance.
    first = create_route_architect()
    second = create_route_architect()
    assert first is not second
