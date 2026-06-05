# Windows Installer Instructions

## Build EXE

```powershell
python -m PyInstaller packaging\AdvancedVideoQAPro.spec --noconfirm --clean
```

Expected output:

```text
dist\AdvancedVideoQAPro\AdvancedVideoQAPro.exe
```

## Build Installer

Install Inno Setup 6, then run:

```powershell
iscc packaging\AdvancedVideoQAPro.iss
```

Expected output:

```text
dist\installer\AdvancedVideoQAProSetup-1.0.0.exe
```

## Installer Behavior

- Installs to `%ProgramFiles%\Advanced Video QA Pro` unless the user chooses another folder.
- Creates Start Menu entry.
- Optionally creates Desktop shortcut.
- Registers uninstaller.
- Registers `.avqapro` file association.
- Uses `desktop_app\resources\icons\app.ico` for installer and executable branding.

## Clean Machine Validation

Validate on a fresh Windows VM:

1. No Python installed.
2. No existing `%LOCALAPPDATA%\AdvancedVideoQA` folder.
3. Install `AdvancedVideoQAProSetup-1.0.0.exe`.
4. Launch from Start Menu.
5. Complete first-run wizard.
6. Import a sample video.
7. Run provider health check.
8. Confirm app exits and relaunches without errors.
