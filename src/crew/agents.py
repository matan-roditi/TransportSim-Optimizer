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


def create_efficiency_specialist():
    # Instantiate the specialist agent focused on budget and logistics
    return Agent(
        role='Efficiency Specialist',
        goal='Optimize routes to minimize operational costs and reduce empty bus miles',
        backstory='You are a seasoned logistics expert determined to improve system efficiency.',
        verbose=True,
        allow_delegation=False
    )
