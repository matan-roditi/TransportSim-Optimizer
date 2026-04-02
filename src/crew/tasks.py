from crewai import Task
import json


def create_demand_analysis_task(agent, unserved_od_metrics):
    # This task maps where people wanted to go vs where the buses actually went
    if not unserved_od_metrics:
        description_text = "No Origin-Destination failure data available."
    else:
        description_text = "Unserved Passenger Origin-Destination Data:\n\n"
        for od_pair, count in unserved_od_metrics.items():
            description_text += f"Failed Connection: {od_pair} ({count} passengers stranded)\n"

        description_text += "\nAnalyze this data and point out the biggest missing links in the current network topology."

    return Task(
        description=description_text,
        expected_output="An analytical report listing the specific origin-destination pairs that lack bus coverage.",
        agent=agent
    )


def create_topological_redesign_task(agent, current_lines, valid_stops_list, travel_times_summary):
    # This core task redraws the map using only the allowed stops and travel times
    description_text = f"""
    The human planner created these baseline bus lines:
    {json.dumps(current_lines, indent=2, ensure_ascii=False)}

    Review the missing links identified by the Analyst.
    Your task is to REDESIGN the sequence of stops for these 4 lines to fix the geographic failures. 
    You must physically change the stops lists to create better, more direct routes.

    CRITICAL GEOGRAPHY CONSTRAINTS:
    You may ONLY use these exact valid stops:
    {valid_stops_list}

    Consider these travel times to ensure your routes flow logically and do not zigzag randomly:
    {travel_times_summary}

    CRITICAL FORMAT INSTRUCTION: 
    You must output ONLY raw valid JSON. Do not include markdown code blocks, greetings, or conversational text. 
    Your output must be a LIST of 4 objects with name and stops keys.

    Example Format:
    [
      {{
        "name": "Line 1",
        "stops": ["ת. רכבת הרצליה", "מחלף הסירה"]
      }}
    ]
    """

    return Task(
        description=description_text,
        expected_output="A raw JSON list containing exactly 4 bus line objects with their new stop sequences. No other text.",
        agent=agent
    )
