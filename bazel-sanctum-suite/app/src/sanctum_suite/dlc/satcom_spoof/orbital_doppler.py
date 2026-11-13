import math
from typing import Dict, Any


class OrbitalDopplerSimulationEngine:
    """Symulacja dynamiki orbity LEO/MEO, przesunięcia częstotliwości Dopplera oraz degradacji SNR."""

    def calculate_link_degradation(self, altitude_km: float, frequency_ghz: float) -> Dict[str, Any]:
        wavelength_m = 0.3 / frequency_ghz
        max_doppler_shift_hz = (7.8 * 1000 * frequency_ghz * 1e9) / 3e8 # Szacunkowa prędkość orbitalna LEO ~7.8 km/s
        free_space_loss_db = 20 * math.log10(altitude_km) + 20 * math.log10(frequency_ghz) + 92.45

        return {
            "orbit_altitude_km": altitude_km,
            "carrier_frequency_ghz": frequency_ghz,
            "max_doppler_shift_hz": round(max_doppler_shift_hz, 2),
            "free_space_path_loss_db": round(free_space_loss_db, 2),
            "signal_stability": "FLUCTUATING_LEO_PASS"
        }