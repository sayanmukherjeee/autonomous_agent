"""
A simple calculator module.
BUG: divide() crashes with ZeroDivisionError when b == 0.
Try asking the agent: "Fix the division-by-zero bug in sample_repo/calculator.py"
"""

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    # BUG: no zero check!
    return a / b


if __name__ == "__main__":
    print(add(10, 5))       # 15
    print(subtract(10, 5))  # 5
    print(multiply(10, 5))  # 50
    print(divide(10, 0))    # CRASHES HERE
