import time

def generate_event_id():
    return base36(int(time.time() * 1000))

def base36(num: int) -> str:
    """Convert an integer to a base36 string."""
    if num < 0:
        raise ValueError("Negative numbers are not supported.")
    if num == 0:
        return "0"

    digits = []
    while num:
        num, rem = divmod(num, 36)
        if rem < 10:
            digits.append(str(rem))
        else:
            digits.append(chr(rem - 10 + ord("a")))
    return "".join(reversed(digits))