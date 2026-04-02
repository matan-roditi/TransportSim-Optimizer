from crewai import Task
from crew.agents import create_efficiency_specialist
from crew.agents import create_neighborhood_advocate
from crew.tasks import create_passenger_audit_task
from crew.tasks import create_efficiency_review_task


def test_audit_task_is_crewai_task_instance():
    # Verify the factory returns a usable CrewAI Task without crashing
    advocate = create_neighborhood_advocate()
    task = create_passenger_audit_task(advocate, {})
    assert isinstance(task, Task)


def test_audit_task_description_contains_metrics_data():
    # Verify the injected metrics dict is actually interpolated into the description
    advocate = create_neighborhood_advocate()
    mock_metrics = {"Green_Herzliya": 15.0}
    task = create_passenger_audit_task(advocate, mock_metrics)
    assert "Green_Herzliya" in task.description


def test_audit_task_flags_critical_delays():
    # Validate that the task logic explicitly highlights neighborhoods exceeding the wait time threshold
    advocate = create_neighborhood_advocate()
    metrics = {"Green_Herzliya": 15.0, "City_Center": 5.0}
    task = create_passenger_audit_task(advocate, metrics)
    assert "CRITICAL DELAYS (>10m): Green_Herzliya" in task.description


def test_audit_task_identifies_unvisited_neighborhoods():
    # Ensure the task logic explicitly notes areas with zero passengers to inform the agent of dead zones
    advocate = create_neighborhood_advocate()
    metrics = {"Neve_Amirim": 0.0}
    task = create_passenger_audit_task(advocate, metrics)
    assert "No Passengers Logged: Neve_Amirim" in task.description


def test_audit_task_handles_empty_metrics_gracefully():
    # Ensure the task handles an empty metrics dictionary safely without generating a broken prompt
    advocate = create_neighborhood_advocate()
    task = create_passenger_audit_task(advocate, {})
    assert "No wait time data available" in task.description


def test_review_task_flags_overserved_areas():
    # Validate that the task logic highlights neighborhoods with suspiciously low wait times as potential cost waste
    specialist = create_efficiency_specialist()
    metrics = {"City_Center": 2.0}
    task = create_efficiency_review_task(specialist, metrics)
    assert "OVERSERVED (<3m wait): City_Center" in task.description


def test_review_task_ignores_normal_wait_times():
    # Validate that normal wait times do not trigger an overserved warning
    specialist = create_efficiency_specialist()
    metrics = {"Yad_HaTisha": 7.0}
    task = create_efficiency_review_task(specialist, metrics)
    assert "OVERSERVED: Yad_HaTisha" not in task.description


def test_review_task_identifies_dead_zones_for_cuts():
    # Ensure the task logic points out areas with zero passengers as candidates for route reductions
    specialist = create_efficiency_specialist()
    metrics = {"Neve_Amirim": 0.0}
    task = create_efficiency_review_task(specialist, metrics)
    assert "Dead Zones (0 pax): Neve_Amirim" in task.description
