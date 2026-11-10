# AutoScout Mobile validation report

Validation performed for this package:

- Python syntax compilation: `main.py` and `autoscout_core.py` pass `py_compile`.
- Core smoke test: constructed a synthetic four-team/two-match session and verified team stats, predictions, standings fields, win-probability complement, and session save/reopen.
- Export smoke test: CSV and HTML report generation both completed and produced non-empty files. The HTML report's embedded logo was restored from the bundled asset.
- Kivy UI runtime test: not run in this build environment because Kivy is not installed and package installation/network access was unavailable. Run the Windows preview on the target PC to validate rendering and interactions.
- Live FTCScout event loading: not tested because it requires network access and a valid event code.
- iOS packaging/signing: not tested. The GitHub Actions workflow builds an Xcode project; Apple signing credentials are still needed for an installable signed iPhone build.

A successful syntax or core smoke test does not guarantee all GUI screens or live API requests work on every machine.
