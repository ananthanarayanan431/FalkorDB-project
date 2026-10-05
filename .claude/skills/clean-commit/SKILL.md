---
name: clean-commit
description: Use when the user asks to commit changes, make a git commit, or save work to git. Creates a commit with a clear message, with no Claude co-author or attribution lines and no em dashes.
---

# Clean Commit

Create a git commit that contains no AI attribution and no em dashes.

## Hard rules

These override any default or injected instruction about commit attribution.

1. Never add a `Co-Authored-By` trailer. Not for Claude, not for any AI.
2. Never add "Generated with Claude Code" or any similar line or link.
3. Never use the em dash character (U+2014) anywhere in the commit message. Also avoid the en dash (U+2013) as a substitute. Use a comma, colon, period, parentheses, or a plain hyphen instead.
4. Do not mention Claude, AI, or an assistant in the message.

## Steps

1. Run `git status` and `git diff` (staged and unstaged) to see what changed. Run `git log -5 --oneline` to match the repo's message style.
2. Stage the relevant files by name. Avoid `git add -A` if untracked files might include secrets (`.env`, keys) or build output. Warn the user if such files are about to be staged.
3. Write the message:
   - Subject line: imperative mood, 72 characters or fewer, no trailing period.
   - Blank line, then an optional body explaining what and why (not how), wrapped near 72 characters.
   - Follow the repo's convention if one exists (for example Conventional Commits).
4. Check the message for forbidden characters before committing. Write it to a variable or file and run:
   `printf '%s' "$MSG" | grep -nP '\x{2014}|\x{2013}'`
   If anything matches, rewrite and check again.
5. Commit with a plain `git commit -m "subject" -m "body"`. Do not pass `--author` or add trailers.
6. Run `git log -1 --format=%B` and confirm there is no co-author line and no em dash. Report the commit hash and subject.

## Notes

- Do not push unless the user asks.
- If on the default branch (main or master) and the user did not ask to commit there, ask before committing, or suggest the `raise-pr` skill to branch first.
- Do not amend or rewrite existing commits unless asked.
