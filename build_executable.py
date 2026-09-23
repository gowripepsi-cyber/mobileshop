import subprocess
import sys
import os

def build():
    print("=" * 60)
    print("Building Mobile Shop Management System Executable (.exe)")
    print("=" * 60)

    spec_file = "Mobile_Shop_Management_System.spec"
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found!")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "-y",
        spec_file
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd)

    if res.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "Mobile Shop Management System.exe"))
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print(f"Executable output: {exe_path}")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"File Size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\nBUILD FAILED with exit code:", res.returncode)
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()
