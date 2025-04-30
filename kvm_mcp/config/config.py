import os
import json
import logging

logger = logging.getLogger('kvm_mcp')

def _apply_env_overrides(config: dict, prefix: str = "") -> dict:
    """Apply environment variable overrides to configuration"""
    for key, value in config.items():
        env_key = f"{prefix}{key}".upper()
        if isinstance(value, dict):
            config[key] = _apply_env_overrides(value, f"{env_key}_")
        else:
            if env_key in os.environ:
                env_value = os.environ[env_key]
                if env_value == "":  # Handle empty strings
                    if isinstance(value, str):
                        config[key] = ""
                    continue
                try:
                    if isinstance(value, bool):
                        # For bool values, only accept specific true/false values
                        if env_value.lower() in ("true", "1", "yes", "on"):
                            config[key] = True
                        elif env_value.lower() in ("false", "0", "no", "off"):
                            config[key] = False
                        else:
                            continue  # Keep original value for invalid bool
                    elif isinstance(value, int):
                        config[key] = int(env_value)
                    elif isinstance(value, float):
                        config[key] = float(env_value)
                    else:
                        config[key] = env_value
                except (ValueError, TypeError):
                    # Keep original value if conversion fails
                    continue
    return config

def load_config():
    """Load configuration from config.json and apply environment variable overrides"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in configuration file: {str(e)}", e.doc, e.pos)
    
    # Apply environment variable overrides
    _apply_env_overrides(config, prefix="")
    return config

# Load and store the configuration
config = load_config() 