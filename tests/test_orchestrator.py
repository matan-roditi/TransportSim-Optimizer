import pytest
from datetime import time
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

def test_run_tick_advances_exactly_one_minute():
    # Verify that the simulation clock moves by exactly 1 minute per tick
    orchestrator = SimulationOrchestrator()
    orchestrator.run_tick()
    # If it starts at 06:00, it must be 06:01
    assert orchestrator.clock.current_time == time(6, 1)

def test_bus_dispatched_during_peak_hour():
    # At 08:00 (Peak), a new bus should be added to the active list
    orchestrator = SimulationOrchestrator()
    # We force the clock to a known dispatch time
    orchestrator.clock.current_time = time(8, 0)
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 1

def test_no_bus_dispatched_on_off_interval():
    # At 08:05 (Peak, but not a 15-min mark), no bus should be created
    orchestrator = SimulationOrchestrator()
    orchestrator.clock.current_time = time(8, 5)
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 0

def test_passenger_generation_increases_active_count():
    # Verify that passengers are added to the system during a tick
    orchestrator = SimulationOrchestrator()
    # We'll assume the generator is called every tick or based on a probability
    orchestrator.run_tick()
    assert len(orchestrator.active_passengers) > 0

def test_frequency_transition_at_ten_am():
    # At 10:15, a bus should NOT be dispatched (off-peak is every 30m)
    orchestrator = SimulationOrchestrator()
    orchestrator.clock.current_time = time(10, 15)
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 0

def test_simulation_ends_at_twenty_two():
    # Verify the orchestrator stops or reflects 'finished' status after 22:00
    orchestrator = SimulationOrchestrator()
    orchestrator.clock.current_time = time(22, 0)
    # This test depends on how you implement is_running
    assert orchestrator.is_running() is False