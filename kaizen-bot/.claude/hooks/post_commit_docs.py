#!/usr/bin/env python3
"""
Post-commit documentation reminder hook.
Triggers after git commit to remind Claude to update documentation.
"""
import json
import sys
import os

def main():
    try:
        input_data = json.load(sys.stdin)
        tool_input = input_data.get('tool_input', {})
        command = tool_input.get('command', '')

        # Check if this was a git commit command
        if 'git commit' not in command:
            sys.exit(0)

        # Check if commit was successful (tool_result would have commit hash)
        tool_result = input_data.get('tool_result', {})
        stdout = tool_result.get('stdout', '')

        # If commit failed, don't trigger
        if 'nothing to commit' in stdout or 'error' in stdout.lower():
            sys.exit(0)

        # Output feedback for Claude
        feedback = """
DOCUMENTATION UPDATE REQUIRED:

After this commit, please update the project documentation:

1. **CHANGELOG.md** - Add entry for this change:
   - What was changed/added/fixed
   - Why it was done
   - Any breaking changes

2. **CLAUDE.md** - Update if needed:
   - New files/modules added
   - Changed project structure
   - New patterns or conventions
   - New commands or workflows

3. **Code comments** - Ensure complex logic is documented inline

Keep documentation concise but complete for fast context retrieval.
"""
        print(feedback)

    except Exception as e:
        # Don't block on errors, just log
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
