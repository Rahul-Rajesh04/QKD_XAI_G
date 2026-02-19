import numpy as np
import core_real as phys

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
        
        # Attack State Config
        self.attack_mode = "none" # options: "none", "timeshift"

    def set_attack_mode(self, mode):
        """Allows simulation of attacks that affect detector physics (like Time Shift)"""
        self.attack_mode = mode

    def detect(self, q_state, incident_flux, basis):
        """
        Simulates APD response based on Flux and Attack Mode.
        """
        # --- 1. CHECK FOR BLINDING (High Flux) ---
        if incident_flux > self.saturation_limit:
            # Linear Mode (Blinding)
            self.current_voltage = np.random.normal(9.0, 0.05) 
            self.current_jitter = np.random.normal(0.1, 0.01) # Zero jitter
            return q_state.measure(basis) 

        # --- 2. CHECK FOR TIME SHIFT (Timing Manipulation) ---
        elif self.attack_mode == "timeshift":
            # Eve shifts the window:
            # - Voltage is Normal (Geiger mode works)
            # - Jitter is suspicious (Too perfect, ~0.2ns)
            # - Counts drop (Efficiency drops from 25% to 15% due to window mismatch)
            
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(0.2, 0.05) # ARTIFICIAL PRECISION
            
            # Reduced efficiency (0.15 effective rate)
            if np.random.random() > 0.15: 
                self.current_voltage = 0.0
                return None
            
            return q_state.measure(basis)

        # --- 3. NORMAL OPERATION ---
        else:
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(1.2, 0.2) # THERMAL NOISE
            
            # Standard Efficiency (0.25)
            if np.random.random() > self.base_efficiency:
                self.current_voltage = 0.0
                return None 
            
            return q_state.measure(basis)

if __name__ == "__main__":
    print("--- HARDWARE COMPONENT TEST ---")
    bob = APD_Detector()
    print("Detector Ready.")