from crewai import Task


def create_passenger_audit_task(agent, metrics):
    # Handle the edge case where the simulation provided no data at all
    if not metrics:
        description_text = "No wait time data available for this simulation run."
    else:
        description_text = "Passenger Wait Time Audit Data:\n\n"

        # Parse the metrics and classify each neighborhood based on wait times
        for neighborhood, wait_time in metrics.items():
            if wait_time == 0.0:
                description_text += f"- No passengers logged for {neighborhood}\n"
            elif wait_time >= 10.0:
                description_text += f"- CRITICAL DELAY: {neighborhood} with {wait_time} mins\n"
            else:
                description_text += f"- Normal operation: {neighborhood} with {wait_time} mins\n"

        description_text += "\nReview this data and formulate a response."

    # Bind the dynamically generated description to the CrewAI task
    return Task(
        description=description_text,
        expected_output="A formal proposal identifying critical delays and suggesting frequency increases.",
        agent=agent
    )


def create_efficiency_review_task(agent, metrics):
    # Handle the edge case for missing data
    if not metrics:
        description_text = "No metrics available for efficiency review."
    else:
        description_text = "System Efficiency Review Data:\n\n"
        
        # Parse the metrics looking for waste and over-served areas
        for neighborhood, wait_time in metrics.items():
            if wait_time == 0.0:
                description_text += f"- Dead zone detected: {neighborhood} (0 passengers)\n"
            elif wait_time < 3.0:
                description_text += f"- OVERSERVED: {neighborhood} with {wait_time} mins\n"
            else:
                description_text += f"- Standard operation: {neighborhood} with {wait_time} mins\n"
                
        description_text += "\nReview this data and propose route or frequency reductions."

    # Bind the dynamically generated description to the CrewAI task
    return Task(
        description=description_text,
        expected_output="A list of proposed route cuts and frequency reductions to save costs.",
        agent=agent
    )