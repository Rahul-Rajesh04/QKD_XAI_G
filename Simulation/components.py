__author__ = "Rahul Rajesh 2360445"

import numpy as np
import core_real as phys

CONSTANTS = {
    'dark_count_prob': 1e-5,    
    'dead_time': 10e-6,         
    'jitter_normal_ns': 0.200,  
    'jitter_attack_ns': 0.050,  
}

class LaserSource:
    def __init__(self, wavelength=1550):
        self.wavelength = wavelength

    def emit(self, label, intensity_mode='single_photon'):
        q_state = phys.QState.from_label(label)
        
        if intensity_mode == 'single_photon':
            photon_flux = 0.1
        elif intensity_mode == 'blinding':
            photon_flux = 1e9 
        else:
            photon_flux = 0.1
            
        return q_state, photon_flux

class APD_Detector:
    def __init__(self, efficiency=0.25):
        self.base_efficiency = efficiency
        self.saturation_limit = 1e7 
        self.attack_mode = "none" 
        
        self.last_click_time = -1.0
        
        self.current_voltage = 0.0
        self.current_jitter = 0.0

    def set_attack_mode(self, mode):
        self.attack_mode = mode

    def detect(self, q_state, incident_flux, basis, current_time=0.0):
        if current_time - self.last_click_time < CONSTANTS['dead_time']:
            return None 

        if np.random.random() < CONSTANTS['dark_count_prob']:
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(1.2, 0.5) 
            self.last_click_time = current_time
            return np.random.choice([0, 1]) 

        measurement = q_state.measure(basis)
        
        if np.random.random() < 0.005: 
            measurement = 1 - measurement

        if incident_flux > self.saturation_limit:
            self.current_voltage = np.random.normal(9.0, 0.05) 
            self.current_jitter = np.random.normal(0.1, 0.01)
            self.last_click_time = current_time
            return measurement 

        elif self.attack_mode == "timeshift":
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(CONSTANTS['jitter_attack_ns'], 0.01)
            
            if np.random.random() < 0.15: 
                 self.last_click_time = current_time
                 return measurement
            
            return None 

        else:
            self.current_voltage = np.random.normal(3.3, 0.2)
            self.current_jitter = np.random.normal(1.2, 0.2) 
            
            if np.random.random() < self.base_efficiency:
                self.last_click_time = current_time
                return measurement 
            
            return None 

if __name__ == "__main__":
    print("--- HARDWARE COMPONENT TEST ---")
    bob = APD_Detector()
    print(f"Detector Ready. Dead Time set to {CONSTANTS['dead_time']} seconds.")