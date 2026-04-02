from crewai import Task


def create_passenger_audit_task(agent, metrics):
    if not metrics:
        description_text = "No wait time data available for this simulation run."
    else:
        # Initialize category lists
        critical_delays = []
        normal_ops = []
        no_passengers = []

        # Categorize each neighborhood and format the float to one decimal place
        for neighborhood, wait_time in metrics.items():
            if wait_time == 0.0:
                no_passengers.append(neighborhood)
            elif wait_time >= 10.0:
                critical_delays.append(f"{neighborhood} ({wait_time:.1f}m)")
            else:
                normal_ops.append(f"{neighborhood} ({wait_time:.1f}m)")

        # Build a concise markdown summary
        description_text = "Passenger Wait Time Audit Data:\n\n"

        if critical_delays:
            description_text += f"CRITICAL DELAYS (>10m): {', '.join(critical_delays)}\n"
        if normal_ops:
            description_text += f"Normal Operation (1-10m): {', '.join(normal_ops)}\n"
        if no_passengers:
            description_text += f"No Passengers Logged: {', '.join(no_passengers)}\n"

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
        # Initialize category lists
        dead_zones = []
        overserved = []
        standard = []

        # Parse metrics looking for waste
        for neighborhood, wait_time in metrics.items():
            if wait_time == 0.0:
                dead_zones.append(neighborhood)
            elif wait_time < 3.0:
                overserved.append(f"{neighborhood} ({wait_time:.1f}m)")
            else:
                standard.append(f"{neighborhood} ({wait_time:.1f}m)")

        # Build a concise markdown summary
        description_text = "System Efficiency Review Data:\n\n"

        if dead_zones:
            description_text += f"Dead Zones (0 pax): {', '.join(dead_zones)}\n"
        if overserved:
            description_text += f"OVERSERVED (<3m wait): {', '.join(overserved)}\n"
        if standard:
            description_text += f"Standard Operation: {', '.join(standard)}\n"

        description_text += "\nReview this data and propose route or frequency reductions."

    # Bind the dynamically generated description to the CrewAI task
    return Task(
        description=description_text,
        expected_output="A list of proposed route cuts and frequency reductions to save costs.",
        agent=agent
    )
