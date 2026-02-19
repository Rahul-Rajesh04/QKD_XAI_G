import numpy as np
import core_real as phys

# --- REAL-WORLD PHYSICS CONSTANTS ---
# Based on ID Quantique / Toshiba specifications for InGaAs APDs
CONSTANTS = {
    'dark_count_prob': 1e-5,    # Thermal noise probability per gate
    'dead_time': 10e-6,         # 10 microseconds (CORRECTED: Was 0.01)
    'jitter_normal_ns': 0.200,  # 200ps FWHM (Standard Jitter)
    'jitter_attack_ns': 0.050,  # 50ps (Eve's Artificial Precision)
}

class LaserSource:
    def __init__(self, wavelength=1550):
        self.wavelength = wavelength

    def emit(self, label, intensity_mode='single_photon'):
        """
        Emits a photon state.
        intensity_mode: 
          - 'single_photon': Standard quantum transmission.
          - 'blinding': High power attack (Bright light).
        """
        q_state = phys.QState.from_label(label)
        
        if intensity_mode == 'single_photon':
            photon_flux = 0.1
        elif intensity_mode == 'blinding':
            photon_flux = 1e9 # Massive blast of light
        else:
            photon_flux = 0.1
            
        return q_state, photon_flux

class APD_Detector:
    def __init__(self, efficiency=0.25):
        self.base_efficiency = efficiency
        self.saturation_limit = 1e7 
        self.attack_mode = "none" 
        
        # Dead Time Tracker (Stores the timestamp of the last click)
        self.last_click_time = -1.0
        
        # Current Vitals (For AI Monitoring)
        self.current_voltage = 0.0
        self.current_jitter = 0.0

    def set_attack_mode(self, mode):
        self.attack_mode = mode

    def detect(self, q_state, incident_flux, basis, current_time=0.0):
        """
        Simulates APD response with Dead Time, Dark Counts, and Attack Physics.
        Args:
            q_state: The incoming photon state.
            incident_flux: Intensity of light.
            basis: Measurement basis.
            current_time: The simulation time of the current pulse (in seconds).
        """
        
        # --- 1. CHECK DEAD TIME (The Fix) ---
        # If the detector clicked less than 10us ago, it is "blind" while recharging.
        if current_time - self.last_click_time < CONSTANTS['dead_time']:
            return None # Photon lost due to dead time

        # --- 2. CHECK DARK COUNTS (Thermal Noise) ---
        # Even if no photon arrives, heat can trigger a false click.
        if np.random.random() < CONSTANTS['dark_count_prob']:
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(1.2, 0.5) # Dark counts have erratic jitter
            self.last_click_time = current_time
            return np.random.choice([0, 1]) # Random error bit

        # --- 3. QUANTUM MEASUREMENT (The Actual Physics) ---
        measurement = q_state.measure(basis)
        
        # Intrinsic Error (0.5% base error rate due to imperfections)
        if np.random.random() < 0.005: 
            measurement = 1 - measurement

        # --- 4. HARDWARE RESPONSE LOGIC ---
        
        # CASE A: BLINDING ATTACK (High Flux)
        if incident_flux > self.saturation_limit:
            # Linear Mode: High Voltage, Zero Jitter
            self.current_voltage = np.random.normal(9.0, 0.05) 
            self.current_jitter = np.random.normal(0.1, 0.01)
            self.last_click_time = current_time
            return measurement 

        # CASE B: TIME-SHIFT ATTACK
        elif self.attack_mode == "timeshift":
            # Eve shifts pulse: Voltage Normal, Jitter suspiciously low
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(CONSTANTS['jitter_attack_ns'], 0.01)
            
            # Efficiency Drop: Eve misses the gate center often
            # Only 15% chance of detection
            if np.random.random() < 0.15: 
                 self.last_click_time = current_time
                 return measurement
            
            return None # Missed the gate

        # CASE C: NORMAL OPERATION
        else:
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(1.2, 0.2) # Normal Thermal Jitter
            
            # Standard Efficiency (25%)
            if np.random.random() < self.base_efficiency:
                self.last_click_time = current_time
                return measurement 
            
            return None # Photon lost due to inefficiency

if __name__ == "__main__":
    print("--- HARDWARE COMPONENT TEST ---")
    bob = APD_Detector()
    print(f"Detector Ready. Dead Time set to {CONSTANTS['dead_time']} seconds.")