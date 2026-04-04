import json
import re
from crewai import Crew, Process
from crew.agents import (
    create_neighborhood_advocate,
    create_demand_analyst,
    create_route_architect
)
from crew.tasks import (
    create_passenger_audit_task,
    create_demand_analysis_task,
    create_topological_redesign_task
)
from database.db_utils import fetch_travel_times_summary


def run_topological_board_meeting(current_lines, wait_time_metrics, unserved_od_metrics, valid_stops_list):
    # Fetch geographic constraints early — fail fast if the DB is unavailable
    travel_times_string = fetch_travel_times_summary()
    if travel_times_string == "Travel time data unavailable.":
        raise RuntimeError(
            "Cannot run board meeting: travel time data is unavailable. "
            "Check the database connection and environment variables."
        )

    # Initialize the three agents for the transit committee
    advocate = create_neighborhood_advocate()
    analyst = create_demand_analyst()
    architect = create_route_architect()

    # Create the specialized tasks with simulation and geographic data
    audit_task = create_passenger_audit_task(advocate, wait_time_metrics)
    analysis_task = create_demand_analysis_task(analyst, unserved_od_metrics)

    # Pass prior task outputs as context so the architect benefits from the
    # advocate's pain-point audit and the analyst's missing-link findings
    redesign_task = create_topological_redesign_task(
        architect,
        current_lines,
        valid_stops_list,
        travel_times_string,
        context=[audit_task, analysis_task]
    )

    # Define the crew with a sequential process to ensure logical hand-offs
    topological_crew = Crew(
        agents=[advocate, analyst, architect],
        tasks=[audit_task, analysis_task, redesign_task],
        process=Process.sequential,
        verbose=False  # Set to True for detailed logs of the board meeting
    )

    # Execute the board meeting
    result = topological_crew.kickoff()

    # Validate that the architect returned parseable JSON before handing it back.
    # LLMs sometimes wrap output in markdown code blocks (```json ... ```) even
    # when instructed not to — strip those before attempting to parse.
    raw = result.raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    try:
        json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(
            f"Board meeting completed but the architect returned invalid JSON: {e}\n"
            f"Raw output was:\n{raw}"
        )

    return cleaned
