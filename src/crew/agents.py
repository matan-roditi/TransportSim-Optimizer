from crewai import Agent


def create_neighborhood_advocate():
    # Instantiate the advocate agent with the required configuration
    return Agent(
        role='Neighborhood Advocate',
        goal='Ensure minimal wait times and optimal coverage for all passengers',
        backstory='You are a passionate community leader in Herzliya fighting for better transit.',
        verbose=True,
        allow_delegation=False
    )
