"""
Tests for the calculator module.
Run:  python -m pytest sample_repo/test_calculator.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from calculator import add, subtract, multiply, divide


def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(10, 4) == 6

def test_multiply():
    assert multiply(3, 4) == 12

def test_divide_normal():
    assert divide(10, 2) == 5.0

def test_divide_by_zero():
    # After the fix this should return None or raise ValueError, NOT ZeroDivisionError
    result = divide(10, 0)
    assert result is None  # expected behaviour after fix
