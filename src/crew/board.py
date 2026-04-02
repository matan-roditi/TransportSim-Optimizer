from crewai import Crew, Process
from crew.agents import create_neighborhood_advocate, create_efficiency_specialist
from crew.tasks import create_passenger_audit_task, create_efficiency_review_task


def assemble_transit_board(metrics):
    # Initialize the board members
    advocate = create_neighborhood_advocate()
    specialist = create_efficiency_specialist()

    # Initialize the tasks and inject the wait time data
    audit_task = create_passenger_audit_task(advocate, metrics)
    review_task = create_efficiency_review_task(specialist, metrics)

    # Bundle the agents and tasks into a cohesive crew
    # The sequential process ensures the advocate audits first before the specialist reviews
    return Crew(
        agents=[advocate, specialist],
        tasks=[audit_task, review_task],
        process=Process.sequential,
        verbose=True
    )


def run_board_meeting(metrics):
    # Assemble the crew and trigger the execution process
    transit_board = assemble_transit_board(metrics)

    # Start the LLM evaluation and return the final consensus
    result = transit_board.kickoff()
    return result
