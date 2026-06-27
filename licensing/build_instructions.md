# Deployment: Obfuscation (PyArmor) & Compilation (Nuitka)

To deploy your application securely without distributing raw Python source files, follow these instructions to obfuscate and compile your PySide6 desktop application.

---

## 1. Prerequisites
Ensure you have the build tools installed on your Windows machine:
- **C++ Compiler**: A compiler like Visual Studio (Community Edition with C++ Desktop Development tools) or MinGW64 is required by Nuitka. We recommend VS 2022.
- **Python Packages**:
  ```bash
  pip install pyarmor nuitka
  ```

---

## 2. Option A: Native Compilation with Nuitka (Recommended)
Nuitka compiles Python source code directly into C++ and links it into native machine code (binary `.exe`). This provides excellent performance and is extremely secure, as it does not distribute Python bytecode or scripts.

### Build Command:
Run the following command from the root of your project:
```bash
nuitka --standalone --onefile --enable-plugin=pyside6 --windows-console-mode=disable --include-data-dir=licensing=licensing main.py
```

### Options Explained:
- `--standalone`: Bundles all necessary dynamic-link libraries (`.dll` files) and the Python runtime into a distribution folder.
- `--onefile`: Compresses everything into a single, clean `.exe` executable file.
- `--enable-plugin=pyside6`: Informs Nuitka to resolve PySide6 metadata, style files, icons, and Qt dependencies.
- `--windows-console-mode=disable`: Runs the app as a pure GUI application without showing a black command console in the background.
- `--include-data-dir=licensing=licensing`: Bundles any support files inside the licensing package if needed.

The output will be created inside the `main.dist/` (or as `main.exe` directly if `--onefile` is used).

---

## 3. Option B: Obfuscation with PyArmor
If you want to obfuscate the Python scripts before compiling (or if you want to ship obfuscated `.pyc`/`.py` files), use PyArmor.

### Obfuscate Command (PyArmor 8+):
Run the following command from your project root:
```bash
pyarmor gen -O dist/obfuscated -r main.py
```

### Options Explained:
- `gen`: Generate obfuscated scripts.
- `-O dist/obfuscated`: Output the obfuscated scripts and runtime packages into `dist/obfuscated/`.
- `-r`: Recursively scan and obfuscate all imported local modules (e.g., `licensing`, `ui`, `utils`).
- `main.py`: Entry point.

To run the obfuscated application directly (as Python scripts):
```bash
cd dist/obfuscated
python main.py
```
You will notice the files inside `dist/obfuscated` look like this:
```python
# Cryptographically obfuscated header by PyArmor
from pyarmor_runtime import __pyarmor__
__pyarmor__(__name__, __file__, b'\x40\x43\x4f\x44...')
```

---

## 4. Option C: Double Protection (PyArmor + Nuitka)
If you want maximum security, you can compile the PyArmor-obfuscated python files with Nuitka into a single binary.

1. **Obfuscate the project** into `dist/obfuscated`:
   ```bash
   pyarmor gen -O dist/obfuscated -r main.py
   ```
2. **Compile the obfuscated output** using Nuitka:
   ```bash
   nuitka --standalone --onefile --enable-plugin=pyside6 --windows-console-mode=disable dist/obfuscated/main.py
   ```
This translates the PyArmor runtime wrapper scripts into C++ and compiles them into a single binary file. The resulting application runs native machine code that decrypts and runs obfuscated Python bytecode in memory.

---

## 5. Summary of Built Executable Distribution
When distributing your app to clients, you only need to send:
1. `main.exe` (a single standalone executable from Nuitka).
2. Any external SQLite database files if they are not dynamically generated on start (e.g. `inventory.db` will be initialized on first run anyway, so it doesn't need to be distributed).
3. The database backup utility will work out of the box.
No `.py` files are distributed, and all local license validation, hardware checking, and crypto keys are fully baked into the binary.
