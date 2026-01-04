import os
import sys

# Try to import PyYAML
try:
    import yaml
except ImportError:
    print("Error: PyYAML is not installed. Please install it using 'pip install PyYAML'.")
    sys.exit(1)

# Determine the absolute path to the project root
# This assumes src/config.py is one level deep (e.g., project_root/src/config.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")

def load_config():
    """Loads configuration from config.yml."""
    if not os.path.exists(CONFIG_PATH):
        # Fallback to checking if a sample exists, or just error out
        print(f"Error: Configuration file not found at {CONFIG_PATH}")
        print("Please copy config_sample.yml to config.yml and add your secrets.")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        try:
            config_data = yaml.safe_load(f)
            return config_data
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML configuration: {exc}")
            sys.exit(1)

# Load the config
_config = load_config()

# Export secrets
# access safely with .get() or direct access if strict
GEMINI_API_KEY = _config.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in config.yml.")
    sys.exit(1)