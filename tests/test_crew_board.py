import pytest
import json
from unittest.mock import patch, MagicMock
from crew.board import run_topological_board_meeting


# Simple mock container to simulate the structure of a CrewAI result object.
class MockCrewResult:
    def __init__(self, raw_output):
        self.raw = raw_output


@pytest.fixture
def valid_inputs():
    # Return a consistent dictionary of valid input parameters for testing the board meeting logic.
    return {
        "current_lines": [{"name": "Line 1", "stops": ["ת. רכבת הרצליה"]}],
        "wait_time_metrics": {"ת. רכבת הרצליה": 12.0},
        "unserved_od_metrics": {"ת. רכבת הרצליה to מחלף הסירה": 5},
        "valid_stops_list": ["ת. רכבת הרצליה", "מחלף הסירה"]
    }


@pytest.fixture
def board_patches():
    """Patch all agent constructors and task factories so no real CrewAI/LLM calls are made.

    CrewAI's Task and Agent models use strict pydantic validation, so passing a plain
    MagicMock as an agent raises a ValidationError at Task construction time.  By mocking
    both the agent factories *and* the task factories we keep every test isolated from
    third-party pydantic models entirely.
    """
    with patch("crew.board.create_neighborhood_advocate") as mock_advocate, \
         patch("crew.board.create_demand_analyst") as mock_analyst, \
         patch("crew.board.create_route_architect") as mock_architect, \
         patch("crew.board.create_passenger_audit_task") as mock_audit_task, \
         patch("crew.board.create_demand_analysis_task") as mock_analysis_task, \
         patch("crew.board.create_topological_redesign_task") as mock_redesign_task:
        mock_advocate.return_value = MagicMock()
        mock_analyst.return_value = MagicMock()
        mock_architect.return_value = MagicMock()
        mock_audit_task.return_value = MagicMock()
        mock_analysis_task.return_value = MagicMock()
        mock_redesign_task.return_value = MagicMock()
        yield mock_advocate, mock_analyst, mock_architect, mock_audit_task, mock_analysis_task, mock_redesign_task


def test_board_meeting_db_error_exception(valid_inputs):
    # Verify that a RuntimeError is triggered if the database utility fails to provide data.
    with patch("crew.board.fetch_travel_times_summary") as mock_db:
        mock_db.return_value = "Travel time data unavailable."
        with pytest.raises(RuntimeError) as exc:
            run_topological_board_meeting(**valid_inputs)
    assert "travel time data is unavailable" in str(exc.value)


def test_board_meeting_invalid_json_exception(valid_inputs, board_patches):
    # Ensure a ValueError is raised when the AI returns output that cannot be parsed as JSON.
    with patch("crew.board.fetch_travel_times_summary") as mock_db, \
         patch("crew.board.Crew") as mock_crew_class:
        mock_db.return_value = "[ת. רכבת הרצליה] to [מחלף הסירה]: 4m"
        mock_crew_instance = mock_crew_class.return_value
        mock_crew_instance.kickoff.return_value = MockCrewResult("Bad Architect Output")

        with pytest.raises(ValueError) as exc:
            run_topological_board_meeting(**valid_inputs)
    assert "invalid JSON" in str(exc.value)


def test_board_meeting_successful_json_return(valid_inputs, board_patches):
    # Confirm the function returns the raw JSON string when the AI board succeeds.
    valid_json = '[{"name": "Line 1", "stops": ["ת. רכבת הרצליה", "מחלף הסירה"]}]'
    with patch("crew.board.fetch_travel_times_summary") as mock_db, \
         patch("crew.board.Crew") as mock_crew_class:
        mock_db.return_value = "Mock Travel Data"
        mock_crew_instance = mock_crew_class.return_value
        mock_crew_instance.kickoff.return_value = MockCrewResult(valid_json)

        result = run_topological_board_meeting(**valid_inputs)
    assert result == valid_json


def test_board_meeting_markdown_fence_stripped(valid_inputs, board_patches):
    # Confirm that markdown code-fence wrappers are stripped before the JSON is returned.
    inner_json = '[{"name": "Line 1", "stops": ["ת. רכבת הרצליה", "מחלף הסירה"]}]'
    fenced_output = f"```json\n{inner_json}\n```"
    with patch("crew.board.fetch_travel_times_summary") as mock_db, \
         patch("crew.board.Crew") as mock_crew_class:
        mock_db.return_value = "Mock Travel Data"
        mock_crew_instance = mock_crew_class.return_value
        mock_crew_instance.kickoff.return_value = MockCrewResult(fenced_output)

        result = run_topological_board_meeting(**valid_inputs)
    assert result == inner_json
    assert "```" not in result


def test_board_meeting_task_context_linkage(valid_inputs, board_patches):
    # Verify that the redesign task is correctly linked to exactly two prior tasks for context.
    # board_patches already mocks create_topological_redesign_task; here we re-patch it so we
    # can inspect call_args while still having Crew.kickoff return a valid result.
    valid_json = '[{"name": "Line 1", "stops": ["ת. רכבת הרצליה", "מחלף הסירה"]}]'
    with patch("crew.board.fetch_travel_times_summary") as mock_db, \
         patch("crew.board.create_topological_redesign_task") as mock_task_factory, \
         patch("crew.board.Crew") as mock_crew_class:
        mock_db.return_value = "Mock Data"
        mock_task_factory.return_value = MagicMock()
        mock_crew_instance = mock_crew_class.return_value
        mock_crew_instance.kickoff.return_value = MockCrewResult(valid_json)

        run_topological_board_meeting(**valid_inputs)
        _, kwargs = mock_task_factory.call_args
        assert len(kwargs.get("context", [])) == 2
