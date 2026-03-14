import pytest
from simulation.orchestrator import SimulationOrchestrator

def test_orchestrator_starts_with_empty_buses():
    # Verify the simulation begins with no active buses on the road
    orchestrator = SimulationOrchestrator()
    assert orchestrator.active_buses == []

def test_orchestrator_starts_with_empty_passengers():
    # Verify the simulation begins with no passengers in the system
    orchestrator = SimulationOrchestrator()
    assert orchestrator.active_passengers == []

def test_orchestrator_clock_initialization():
    # Verify the orchestrator has a clock instance ready to go
    orchestrator = SimulationOrchestrator()
    assert orchestrator.clock is not None

def test_run_tick_advances_clock_time():
    # Verify that calling run_tick actually moves the simulation time forward
    orchestrator = SimulationOrchestrator()
    initial_time = orchestrator.clock.current_time
    orchestrator.run_tick()
    assert orchestrator.clock.current_time != initial_time