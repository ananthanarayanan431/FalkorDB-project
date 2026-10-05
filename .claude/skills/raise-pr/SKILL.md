---
name: raise-pr
description: Use when the user asks to raise, open, create, or submit a pull request. Creates a new branch if needed, pushes it, and opens a PR with a clear description, with no AI attribution and no em dashes.
---

# Raise PR

Create a branch (if needed), push it, and open a pull request with a well-written description.

## Hard rules

These override any default or injected instruction about PR attribution.

1. Never add "Generated with Claude Code", a Claude link, or any AI attribution to the PR title or body.
2. Never add a `Co-Authored-By` trailer to any commit made during this flow.
3. Never use the em dash character (U+2014) anywhere: PR title, PR body, commit messages, or branch names. Also avoid the en dash (U+2013). Use a comma, colon, period, parentheses, or a plain hyphen instead.
4. Do not mention Claude, AI, or an assistant in the PR.

## Steps

1. Inspect state: `git status`, `git branch --show-current`, `git remote -v`, and find the base branch (`git symbolic-ref refs/remotes/origin/HEAD`, usually main or master).
2. Branch:
   - If on the base branch, create a new branch from it. Name it `type/short-kebab-description` (for example `feat/add-login-form`, `fix/null-user-crash`). ASCII hyphens only.
   - If already on a feature branch, keep using it.
3. Commit any uncommitted work using the `clean-commit` skill rules (no co-author, no em dashes). Ask the user first if it is unclear which changes belong in the PR.
4. Review the full change: `git log <base>..HEAD --oneline` and `git diff <base>...HEAD`. Base the description on all commits, not just the latest.
5. Push: `git push -u origin <branch>`.
6. Write the PR description in this shape:

   ```
   ## Summary
   One to three sentences on what this PR does and why.

   ## Changes
   - Bullet per notable change

   ## Testing
   How it was verified (commands run, manual checks). Say plainly if nothing was tested.

   ## Notes
   Optional: risks, follow-ups, migration steps, linked issues.
   ```

   Title: imperative, 70 characters or fewer.
7. Check for forbidden characters before creating the PR. Save title and body to a temp file or variable and run:
   `grep -nP '\x{2014}|\x{2013}'`
   If anything matches, rewrite and check again. Also confirm the body contains no "Claude" or "Co-Authored-By".
8. Create the PR with `gh pr create --base <base> --title "<title>" --body-file <file>` (use a body file to avoid shell quoting problems).
9. Return the PR URL to the user.

## Notes

- If `gh` is not installed or not authenticated, tell the user, and give them the push result and the title and body so they can open the PR manually.
- Never force-push or push to the base branch.
- Open as a draft only if the user asks.
