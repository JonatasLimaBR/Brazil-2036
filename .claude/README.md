# Claude Code Harness

The repository is designed for specification-driven agentic development.

## Rituals
1. `/understand-spec`
2. `/implement-spec`
3. `/verify-spec`
4. `/security-check`
5. `/agent-eval`
6. `/review-pr`

## Author / Reviewer separation
The implementation session is the author.
A fresh reviewer session verifies the SPEC and must be read-only.
A reviewer that fixes the code becomes an author and cannot issue the independent verdict.

## Skills
Skills are vendored under `.claude/skills/` and pinned through `skills.lock`.
Do not auto-upgrade skills during a feature implementation.
