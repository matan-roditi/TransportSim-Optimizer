import pytest
from datetime import time
from simulation.clock import SimulationClock

def test_clock_initialization():
    # Verify the clock starts at exactly 06:00 as required for Herzliya
    clock = SimulationClock(start_time="06:00", end_time="22:00")
    assert clock.current_time == time(6, 0)

def test_clock_advancement():
    # Ensure one tick represents exactly one minute of simulation time
    clock = SimulationClock(start_time="06:00", end_time="22:00")
    clock.tick()
    assert clock.current_time == time(6, 1)

def test_clock_not_finished_before_end():
    # Check that the clock is not finished before reaching the end time
    clock = SimulationClock(start_time="21:59", end_time="22:00")
    assert not clock.is_finished()  # Should not be finished before ticking

def test_simulation_end_boundary():
    # Verify the simulation's 'is_finished' flag works when reaching the end time
    clock = SimulationClock(start_time="21:59", end_time="22:00")
    clock.tick()
    assert clock.is_finished()

def test_simulation_ends_exactly_at_2200():
    # Explicitly check that the final logged time is exactly 22:00
    clock = SimulationClock(start_time="21:59", end_time="22:00")
    clock.tick()
    assert clock.current_time == time(22, 0)