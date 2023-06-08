def angle_add(a: float, b: float) -> float:
    assert a >= 0 and a < 360
    assert b >= 0 and b < 360
    return (a + b) % 360

def angle_subtract(a: float, b: float) -> float:
    assert a >= 0 and a < 360
    assert b >= 0 and b < 360
    if a < b:
        return (360 - (b - a)) % 360
    else:
        return a - b
