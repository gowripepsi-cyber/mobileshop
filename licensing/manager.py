import os
import sys
import json
import hashlib
import winreg
import subprocess
from datetime import datetime, date

from licensing import crypto_utils

def _run_cmd(cmd: str) -> str:
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
        lines = [line.strip() for line in out.decode('utf-8', errors='ignore').split('\n') if line.strip()]
        if len(lines) > 1:
            return lines[1]
        return ""
    except Exception:
        return ""

def get_machine_components() -> tuple[str, str, str]:
    """Retrieves hardware components for Machine ID generation."""
    mobo = _run_cmd("wmic baseboard get serialnumber").strip()
    cpu = _run_cmd("wmic cpu get processorid").strip()
    disk = _run_cmd("wmic diskdrive get serialnumber").strip()
    
    # Filter out generic placeholder values
    generic_placeholders = {"to be filled by o.e.m.", "none", "serial", "serialnumber", "unknown", ""}
    if mobo.lower() in generic_placeholders:
        mobo = ""
    if cpu.lower() in generic_placeholders:
        cpu = ""
    if disk.lower() in generic_placeholders:
        disk = ""
        
    return mobo, cpu, disk

def get_registry_machine_guid() -> str:
    """Retrieves Windows Cryptography MachineGuid as a fallback/additional check."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(val).strip()
    except Exception:
        return ""

def generate_machine_id() -> str:
    """Generates a stable, unique 16-character Machine ID from hardware IDs."""
    mobo, cpu, disk = get_machine_components()
    reg_guid = get_registry_machine_guid()
    
    combined = f"MOBO:{mobo}|CPU:{cpu}|DISK:{disk}|GUID:{reg_guid}"
    
    # Absolute fallback if all queries returned empty
    if not mobo and not cpu and not disk and not reg_guid:
        comp_name = os.environ.get("COMPUTERNAME", "UNKNOWN_PC")
        user_name = os.environ.get("USERNAME", "UNKNOWN_USER")
        combined = f"FALLBACK:{comp_name}:{user_name}"
        
    h = hashlib.sha256(combined.encode('utf-8')).hexdigest().upper()
    # Format as XXXX-XXXX-XXXX-XXXX
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

def get_storage_dir() -> str:
    """Returns the platform-specific directory where license data is stored."""
    appdata = os.environ.get("LOCALAPPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    path = os.path.join(appdata, "MobileShop", "license")
    os.makedirs(path, exist_ok=True)
    return path

def get_trial_file_path() -> str:
    return os.path.join(get_storage_dir(), "trial.dat")

def get_license_file_path() -> str:
    return os.path.join(get_storage_dir(), "license.lic")

def save_trial_data(machine_id: str, start_date: date, last_run_date: date, tampered: bool):
    """Encrypts and saves the trial data to disk."""
    data = {
        "start_date": start_date.isoformat(),
        "last_run_date": last_run_date.isoformat(),
        "tampered": tampered
    }
    plaintext = json.dumps(data).encode('utf-8')
    ciphertext = crypto_utils.encrypt_data(machine_id, plaintext)
    
    with open(get_trial_file_path(), "wb") as f:
        f.write(ciphertext)

def load_trial_data(machine_id: str) -> dict | None:
    """Loads and decrypts trial data. Returns None if file is missing or corrupted."""
    path = get_trial_file_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            ciphertext = f.read()
        plaintext = crypto_utils.decrypt_data(machine_id, ciphertext)
        data = json.loads(plaintext.decode('utf-8'))
        return {
            "start_date": date.fromisoformat(data["start_date"]),
            "last_run_date": date.fromisoformat(data["last_run_date"]),
            "tampered": bool(data.get("tampered", False))
        }
    except Exception:
        # If decryption fails, it indicates tampering or copying to a different PC.
        return {"tampered": True}

def save_license(machine_id: str, activation_key: str):
    """Saves the activation key to the license file."""
    data = {
        "machine_id": machine_id,
        "activation_key": activation_key
    }
    plaintext = json.dumps(data).encode('utf-8')
    ciphertext = crypto_utils.encrypt_data(machine_id, plaintext)
    
    with open(get_license_file_path(), "wb") as f:
        f.write(ciphertext)

def load_license(machine_id: str) -> dict | None:
    """Loads and decrypts license file. Returns None if file is missing or tampered."""
    path = get_license_file_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            ciphertext = f.read()
        plaintext = crypto_utils.decrypt_data(machine_id, ciphertext)
        return json.loads(plaintext.decode('utf-8'))
    except Exception:
        return None

def verify_license_key(machine_id: str, activation_key: str) -> bool:
    """Verifies that the activation key matches the machine ID using the public key."""
    return crypto_utils.verify_signature(
        crypto_utils.DEFAULT_PUBLIC_KEY,
        machine_id.encode('utf-8'),
        activation_key
    )

def check_license_status() -> dict:
    """Checks the status of the license/trial and returns status info."""
    machine_id = generate_machine_id()
    today = date.today()
    
    # 1. Check License File first
    license_data = load_license(machine_id)
    if license_data:
        # Check if the license is bound to this machine ID and signature is valid
        lic_machine_id = license_data.get("machine_id")
        activation_key = license_data.get("activation_key")
        if lic_machine_id == machine_id and verify_license_key(machine_id, activation_key):
            return {
                "status": "active",
                "days_remaining": 99999,
                "machine_id": machine_id,
                "message": "Software is permanently activated."
            }
    
    # 2. Check Trial File
    trial = load_trial_data(machine_id)
    
    if trial is None:
        # First launch - initialize trial
        save_trial_data(machine_id, today, today, False)
        return {
            "status": "trial",
            "days_remaining": 30,
            "machine_id": machine_id,
            "message": "Trial initialized. 30 days remaining."
        }
        
    if trial.get("tampered"):
        return {
            "status": "tampered",
            "days_remaining": 0,
            "machine_id": machine_id,
            "message": "Licensing integrity violation detected. System blocked."
        }
        
    start_date = trial["start_date"]
    last_run_date = trial["last_run_date"]
    
    # Detect System Clock Rollback
    if today < last_run_date:
        # User turned back their clock
        save_trial_data(machine_id, start_date, last_run_date, True)
        return {
            "status": "tampered",
            "days_remaining": 0,
            "machine_id": machine_id,
            "message": "System clock manipulation detected. Trial is suspended."
        }
        
    # Valid execution day - update last run date
    save_trial_data(machine_id, start_date, today, False)
    
    days_used = (today - start_date).days
    days_remaining = max(0, 30 - days_used)
    
    if days_remaining <= 0:
        return {
            "status": "expired",
            "days_remaining": 0,
            "machine_id": machine_id,
            "message": "Your 30-day free trial has expired. Activation required."
        }
        
    return {
        "status": "trial",
        "days_remaining": days_remaining,
        "machine_id": machine_id,
        "message": f"Trial active. {days_remaining} days remaining."
    }

def activate_software(activation_key: str) -> bool:
    """Attempts to activate the software using the provided key."""
    machine_id = generate_machine_id()
    if verify_license_key(machine_id, activation_key):
        save_license(machine_id, activation_key)
        return True
    return False

def deactivate_software() -> bool:
    """Deactivates the software by removing the local license file."""
    path = get_license_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception:
            return False
    return False

def reset_trial() -> bool:
    """Resets the trial data by deleting the trial file."""
    path = get_trial_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception:
            return False
    return True

