import cli2
import math


# Deepest function that may raise an exception
def function_g(z):
    prelim = z + 3.5
    factor = math.sqrt(abs(prelim))
    threshold = 10
    if not isinstance(z, int):
        raise TypeError("Input must be an integer for function_g")
    elif z == 0:
        result = 100 / z  # Triggers ZeroDivisionError
    elif z > threshold:
        dummy_list = [1, 2]
        # Triggers IndexError if z >= 2 (and z > threshold)
        result = dummy_list[z]
    else:
        result = factor * z
    return result


# Function with extensive calculations and a loop
def function_f(w):
    base = w - 2
    accumulator = 0
    temp_list = []
    for i in range(5):
        temp = base + i * 0.5
        temp_list.append(temp)
        accumulator += temp ** 2
    mean = accumulator / len(temp_list)
    variance = sum((x - mean) ** 2 for x in temp_list) / len(temp_list)
    std_dev = math.sqrt(variance)
    adjusted = mean + std_dev
    processed = adjusted / 3
    intermediate = processed - 1.5
    next_val = intermediate * 2
    # Line 36: Call may raise due to float input to function_g
    outcome = function_g(next_val)
    final = outcome + accumulator
    return final


# Function with dictionary operations and conditionals
def function_e(v):
    config = {"low": 1, "mid": 5, "high": 10}
    category = "low"
    if v > 7:
        category = "high"
    elif v > 3:
        category = "mid"
    base_value = config[category]
    scaled = base_value * v
    offset = scaled - 2.5
    multiplier = offset / 1.5
    result = multiplier + 3
    # Line 54: Call function_f
    next_result = function_f(result)
    return next_result


# Function with list comprehension and filtering
def function_d(lst):
    squares = [x * x for x in lst]
    positives = [x for x in squares if x > 0]
    negatives = [x for x in squares if x <= 0]
    total_pos = sum(positives)
    total_neg = sum(negatives)
    ratio = total_pos / (total_neg or 1)  # Avoid division by zero
    adjusted_ratio = ratio * 2
    scaled = adjusted_ratio - 1
    processed = scaled + len(lst)
    intermediate = processed / 2
    # Line 71: Call function_e
    next_call = function_e(intermediate)
    final_value = next_call + total_pos
    return final_value


# Function with nested loops and aggregation
def function_c(n):
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            value = (i + 1) * (j + 1)
            row.append(value)
        matrix.append(row)
    flat_list = [item for sublist in matrix for item in sublist]
    sum_total = sum(flat_list)
    avg = sum_total / len(flat_list)
    max_val = max(flat_list)
    min_val = min(flat_list)
    range_val = max_val - min_val
    normalized = (avg - min_val) / range_val if range_val else avg
    processed = normalized * 10
    # Line 92: Call function_d
    result = function_d(flat_list)
    return result + processed


# Function with string manipulation and list processing
def function_b(prefix, count):
    labels = [f"{prefix}_{i}" for i in range(count)]
    lengths = [len(label) for label in labels]
    total_length = sum(lengths)
    avg_length = total_length / len(lengths)
    chars = []
    for label in labels:
        for char in label:
            if char.isdigit():
                chars.append(int(char))
    digit_sum = sum(chars)
    combined = total_length + digit_sum
    scaled = combined / 2.5
    next_value = scaled + avg_length
    # Ensure next_value is integer for function_c if needed, example uses int()
    # Line 111: Call function_c
    result = function_c(int(next_value))
    final = result - digit_sum
    return final


# Top-level function with complex initialization
def function_a(base_num):
    initial_list = [base_num + i for i in range(-3, 4)]
    evens = [x for x in initial_list if x % 2 == 0]
    odds = [x for x in initial_list if x % 2 != 0]
    product_evens = 1
    for num in evens:
        product_evens *= num if num != 0 else 1
    sum_odds = sum(odds)
    combined = product_evens + sum_odds
    prefix_str = "test"
    count_val = len(initial_list)
    accumulator = 0
    for i in range(5):
        temp = combined + i * 1.5
        accumulator += temp
    avg_accum = accumulator / 5
    # Line 134: Call function_b
    next_result = function_b(prefix_str, count_val)
    final_result = next_result + avg_accum
    return final_result


# Simple function for testing error on first line
def error_on_first_line(arg):
    # Line 141
    result = 1 / arg  # Error if arg is 0, on the first executable line
    return result


# Main entry point
def main():
    print(
        "--- Running function_a(5)",
        "--- (Expected: TypeError in function_g line 9)",
    )
    try:
        function_a(5)  # This likely causes TypeError in function_g line 9
    except Exception:
        cli2.log.exception()

    print(
        "--- Running function_g(0)",
        "--- (Expected: ZeroDivisionError in function_g line 12)",
    )
    try:
        function_g(0)  # Trigger ZeroDivisionError line 12
    except Exception:
        cli2.log.exception()

    print(
        "--- Running function_g(15)",
        "--- (Expected: IndexError in function_g line 15)")
    try:
        # Note: Needs z > threshold (10) and z >= 2. So 15 works.
        function_g(15)  # Trigger IndexError line 15
    except Exception:
        cli2.log.exception()

    print(
        "--- Running error_on_first_line(0)",
        "--- (Expected: ZeroDivisionError in error_on_first_line line 141)",
    )
    try:
        error_on_first_line(0)  # Trigger ZeroDivisionError on line 141
    except Exception:
        cli2.log.exception()

    print("--- Triggering SyntaxError ---")
    try:
        # Using exec() to dynamically trigger a SyntaxError
        # This ensures the error happens after the hook is enabled.
        # Note: The filename in the traceback might be '<string>'
        syntax_error_code = "invalid syntax here = 1"
        exec(syntax_error_code)
    except Exception:
        cli2.log.exception()


if __name__ == "__main__":
    main()
