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
