import pytest
from unittest.mock import patch
from crew.board import assemble_transit_board, run_board_meeting


def test_assemble_board_includes_both_agents():
    # Verify the orchestrator assembles a crew containing the exact required agents
    metrics = {"City_Center": 5.0}
    crew = assemble_transit_board(metrics)
    assert len(crew.agents) == 2


def test_assemble_board_includes_both_tasks():
    # Verify the orchestrator loads the required tasks for the board meeting
    metrics = {"City_Center": 5.0}
    crew = assemble_transit_board(metrics)
    assert len(crew.tasks) == 2


@patch('crewai.Crew.kickoff')
def test_run_board_meeting_returns_mocked_result(mock_kickoff):
    # Ensure the crew execution function returns the simulated LLM output safely
    mock_kickoff.return_value = "Mocked consensus: Increase frequency on Line 29"
    metrics = {"City_Center": 15.0}
    result = run_board_meeting(metrics)
    assert "Mocked consensus" in result
