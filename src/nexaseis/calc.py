import numpy as np


def process_packets(
    packet: dict, 
    time_array: list[float], 
    sensitivity: float,
    response: str = "m/s",
) -> dict:
    
    counts = np.asarray(packet["waveform"], dtype=float)
    time = np.asarray(time_array, dtype=float)

    demeaned_counts = counts - np.mean(counts)
    
    calibrated = demeaned_counts if not sensitivity else demeaned_counts / sensitivity

    def differentiate(values: np.ndarray) -> np.ndarray:
        if len(values) < 2:
            return np.zeros_like(values)
        return np.gradient(values, time)

    def integrate(values: np.ndarray) -> np.ndarray:
        integrated = np.zeros_like(values)
        if len(values) > 1:
            intervals = np.diff(time)
            areas = 0.5 * (values[1:] + values[:-1]) * intervals
            integrated[1:] = np.cumsum(areas)
        return integrated

    if response == "m":
        displacement = calibrated
        velocity = differentiate(displacement)
        acceleration = differentiate(velocity)
    elif response == "m/s":
        velocity = calibrated
        acceleration = differentiate(velocity)
        displacement = integrate(velocity)
    elif response == "m/s**2":
        acceleration = calibrated
        velocity = integrate(acceleration)
        displacement = integrate(velocity)
    else:
        raise ValueError(f"Unsupported response unit: {response!r}")

    pgv = float(np.max(np.abs(velocity)))
    pga = float(np.max(np.abs(acceleration)))
    pgd = float(np.max(np.abs(displacement)))

    return {
        **packet,
        "pgv": pgv,
        "pga": pga,
        "pgd": pgd,
        "velocity": velocity.tolist(),
        "acceleration": acceleration.tolist(),
        "displacement": displacement.tolist()
    }
