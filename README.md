# Project README

## Git Hooks

This project uses a Git hook to push the main branch automatically after each commit.

### Setup

1. Create a file called `.git/hooks/post-commit` in the repository.
2. Add the following content:

```sh
#!/bin/sh
echo "Post-commit hook: Pushing main branch automatically..."
git push origin main
```

3. Make the hook executable:

```bash
chmod +x .git/hooks/post-commit
```

Note: This hook pushes the `main` branch regardless of the active branch. Adjust the script if your workflow requires different behavior.

## Firmware Node Details

The firmware is built from tracks/firmware/main.cpp, and the main entry point for running on the device is tracks/tracks/__main__.py.

The following table summarizes the pin configuration used in the firmware:

| Motor  | VCC Pin | PWM Pin | DIR Pin |
| ------ | ------- | ------- | ------- |
| Right  |    2    |    3    |    4    |
| Left   |    6    |    7    |    8    |

## Tracks Node Details

The Tracks node is responsible for interfacing with the firmware and processing serial logs and events.
It is executed from tracks/tracks/__main__.py and utilizes additional logic from tracks/tracks/main.py.
