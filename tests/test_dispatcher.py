import pytest
from datetime import time
from simulation.dispatcher import Dispatcher

def test_peak_exact_start_6_00():
    # Ensure the very first dispatch of the day at 06:00 works
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(6, 0)) is True
    
def test_peak_hour_6_15():
    # Peak: 06:00-10:00. Should dispatch every 15 minutes.
    dispatcher = Dispatcher()
    # should dispatch at 6:00, 6:15, 6:30, 6:45, etc.
    assert dispatcher.should_dispatch(time(6, 15)) is True

def test_peak_hour_6_40():
    # Peak: 06:00-10:00. Should dispatch every 15 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(6, 40)) is False  # Not on the 15-minute mark

def test_peak_hour_9_45():
    # Peak: 06:00-10:00. Should dispatch every 15 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(9, 45)) is True

def test_off_peak_hour_10_15():
    # Off-peak: 10:00-16:00. Should dispatch every 30 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(10, 15)) is False  # 10:00 is the cutoff for peak

def test_off_peak_hour_intervals():
    # Off-peak: 10:00-16:00. Should dispatch every 30 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(12, 15)) is False

def test_peak_hour_16_45():
    # Peak: 16:00-20:00. Should dispatch every 15 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(16, 45)) is True

def test_peak_hour_19_20():
    # Peak: 16:00-20:00. Should dispatch every 15 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(19, 20)) is False  # Not on the 15-minute mark

def test_night_hour_21_00():
    # Night: 20:00-22:00. Should dispatch every 30 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(21, 0)) is True

def test_night_hour_21_15():
    # Night: 20:00-22:00. Should dispatch every 30 minutes.
    dispatcher = Dispatcher()
    assert dispatcher.should_dispatch(time(21, 15)) is False  # Not on the 30-minute mark