import pytest
from crewai import Agent, Task
from crew.tasks import (
    create_demand_analysis_task,
    create_passenger_audit_task,
    create_topological_redesign_task,
)


@pytest.fixture
def dummy_agent():
    return Agent(
        role="Test Agent",
        goal="Help run unit tests",
        backstory="Just a test mock",
    )


def test_passenger_audit_task_returns_task_instance(dummy_agent):
    # Verify the passenger audit factory returns a CrewAI Task object.
    task = create_passenger_audit_task(dummy_agent, {})
    assert isinstance(task, Task)


def test_passenger_audit_task_handles_empty_data(dummy_agent):
    # Ensure empty wait-time input produces a safe fallback description.
    task = create_passenger_audit_task(dummy_agent, {})
    assert "No wait time data available" in task.description


def test_passenger_audit_task_includes_critical_delay_section(dummy_agent):
    # Confirm high wait times are grouped into the critical delays section.
    task = create_passenger_audit_task(dummy_agent, {"City_Center": 11.5})
    assert "CRITICAL DELAYS" in task.description


def test_passenger_audit_task_includes_critical_neighborhood(dummy_agent):
    # Check that the delayed neighborhood and its formatted wait time appear in the prompt.
    task = create_passenger_audit_task(dummy_agent, {"City_Center": 11.5})
    assert "City_Center (11.5m)" in task.description


def test_passenger_audit_task_includes_normal_operation_section(dummy_agent):
    # Verify moderate wait times are labeled as normal operation.
    task = create_passenger_audit_task(dummy_agent, {"Marina": 5.0})
    assert "Normal Operation" in task.description


def test_passenger_audit_task_includes_no_passengers_section(dummy_agent):
    # Ensure zero-demand neighborhoods are called out in their own section.
    task = create_passenger_audit_task(dummy_agent, {"Neve_Amirim": 0.0})
    assert "No Passengers Logged" in task.description


def test_passenger_audit_task_includes_expected_output_contract(dummy_agent):
    # Validate that the task advertises the intended audit deliverable.
    task = create_passenger_audit_task(dummy_agent, {"Marina": 5.0})
    assert "underserved neighborhoods" in task.expected_output


def test_demand_analysis_task_returns_task_instance(dummy_agent):
    # Verify the demand analysis factory returns a CrewAI Task object.
    task = create_demand_analysis_task(dummy_agent, {})
    assert isinstance(task, Task)


def test_demand_analysis_task_handles_empty_data(dummy_agent):
    # Ensure empty OD-failure input results in a clear fallback description.
    task = create_demand_analysis_task(dummy_agent, {})
    assert "No Origin-Destination failure data available." in task.description


def test_demand_analysis_task_includes_failed_connection_label(dummy_agent):
    # Confirm failed OD pairs are introduced with the expected label.
    task = create_demand_analysis_task(dummy_agent, {"Neve_Amal to Marina": 45})
    assert "Failed Connection:" in task.description


def test_demand_analysis_task_includes_od_pair(dummy_agent):
    # Verify the actual origin-destination pair is embedded in the prompt.
    task = create_demand_analysis_task(dummy_agent, {"Neve_Amal to Marina": 45})
    assert "Neve_Amal to Marina" in task.description


def test_demand_analysis_task_includes_stranded_passenger_count(dummy_agent):
    # Check that stranded passenger counts are surfaced for prioritization.
    task = create_demand_analysis_task(dummy_agent, {"Neve_Amal to Marina": 45})
    assert "45 passengers stranded" in task.description


def test_demand_analysis_task_includes_expected_output_contract(dummy_agent):
    # Validate that the task describes the intended analytical output.
    task = create_demand_analysis_task(dummy_agent, {"Neve_Amal to Marina": 45})
    assert "lack bus coverage" in task.expected_output


def test_topological_redesign_task_returns_task_instance(dummy_agent):
    # Verify the redesign factory returns a CrewAI Task object.
    task = create_topological_redesign_task(dummy_agent, [], [], "")
    assert isinstance(task, Task)


def test_topological_redesign_task_includes_baseline_lines(dummy_agent):
    # Ensure the current line layout is included for redesign context.
    lines = [{"name": "Line 1", "stops": ["ת. רכבת הרצליה"]}]
    task = create_topological_redesign_task(dummy_agent, lines, [], "")
    assert '"name": "Line 1"' in task.description


def test_topological_redesign_task_includes_valid_stops_list(dummy_agent):
    # Verify the prompt includes the allowed stop set for route redesign.
    task = create_topological_redesign_task(dummy_agent, [], ["ת. רכבת הרצליה", "מחלף הסירה"], "")
    assert "מחלף הסירה" in task.description


def test_topological_redesign_task_includes_travel_time_summary(dummy_agent):
    # Check that travel-time guidance is present to constrain redesign choices.
    task = create_topological_redesign_task(
        dummy_agent,
        [],
        ["ת. רכבת הרצליה", "מחלף הסירה"],
        "[ת. רכבת הרצליה] to [מחלף הסירה]: 5m",
    )
    assert "5m" in task.description


def test_topological_redesign_task_requires_raw_json_output(dummy_agent):
    # Ensure the prompt explicitly requires raw JSON-only output.
    task = create_topological_redesign_task(dummy_agent, [], [], "")
    assert "ONLY raw valid JSON" in task.description


def test_topological_redesign_task_includes_expected_output_contract(dummy_agent):
    # Validate that the expected output specifies the required bus-line payload.
    task = create_topological_redesign_task(dummy_agent, [], [], "")
    assert "exactly 4 bus line objects" in task.expected_output
