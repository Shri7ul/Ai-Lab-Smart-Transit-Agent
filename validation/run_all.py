import sys
import subprocess
from pathlib import Path

# Fix sys.path for absolute project-root imports if needed
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# List of deterministic offline validations in order
VALIDATION_SCRIPTS = [
    "validate_phase1.py",
    "validate_phase2.py",
    "validate_phase3.py",
    "validate_phase4.py",
    "validate_phase5_offline.py",
    "validate_phase6_offline.py",
    "validate_phase7_offline.py",
    "validate_phase8_offline.py",
    "validate_phase9_offline.py",
    "validate_phase10_offline.py",
    "validate_phase11_offline.py",
    "validate_phase12_offline.py",
    "validate_phase13_auth_offline.py",
    "validate_phase13_step1.py",
    "validate_phase13_step2.py",
    "validate_phase13_frontend.py",
    "validate_phase13_time_controls.py",
    "validate_phase13_filters.py",
    "validate_phase14_map.py",
    "validate_phase15_nlp_ranking.py"
]

def run_all():
    validation_dir = Path(__file__).parent
    
    for script_name in VALIDATION_SCRIPTS:
        script_path = validation_dir / script_name
        
        if not script_path.exists():
            print(f"==================================================")
            print(f"Error: Could not find {script_name}")
            print(f"==================================================")
            sys.exit(1)
            
        print(f"==================================================")
        print(f"Running {script_name}")
        print(f"==================================================")
        
        result = subprocess.call([sys.executable, str(script_path)])
        
        if result != 0:
            print(f"\n[FAIL] {script_name} failed with exit code {result}.")
            sys.exit(result)
            
        print("\nPASS\n")
        
    print("==================================================")
    print("ALL DETERMINISTIC VALIDATIONS PASSED")
    print("==================================================")

if __name__ == "__main__":
    run_all()
