# SKILL.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.


## 5. CRYPTOSAFE Project Rules

These rules apply specifically to the CRYPTOSAFE application.

### Project Documentation

- Read relevant documentation in the `docs/` directory before implementing features.
- Follow `PLAN.md` and `IMPLEMENTATION_GUIDE.md`.
- Follow the security requirements in `SECURITY.md`.
- Follow the database design in `DATABASE.md`.
- Do not silently change established project requirements.

### Development Workflow

- Follow milestones sequentially.
- Complete and verify the current milestone before moving to the next.
- Inspect existing code before creating or modifying files.
- Preserve working features and existing project architecture.
- Ask for approval before major architectural changes.

### Security Requirements

- Use established cryptographic libraries.
- Never implement production cryptographic primitives manually.
- Never store plaintext passwords.
- Never hardcode encryption keys or credentials.
- Use authenticated encryption where appropriate.
- Use unique nonces according to the selected cryptographic algorithm.
- Protect sensitive user and biometric information.
- Do not claim a security feature is implemented unless it has been verified.

### Testing and Reporting

- Test every implemented feature.
- Report the files modified.
- Report commands executed and their results.
- Identify known limitations and unresolved security risks.
- Never claim tests passed without actually running them.


## 6. Token and Context Efficiency

Optimize context usage and avoid unnecessary work.

### Documentation Reading
- Do not reread all documentation for every task.
- Read only documents relevant to the current task.
- Use existing project documentation as the source of truth.
- Avoid repeating information already established in the conversation.
- Do not summarize entire documents unless requested.

### Code Inspection
- Inspect only relevant files and their direct dependencies.
- Do not repeatedly inspect unchanged files.
- Avoid unnecessary directory listings and duplicate commands.
- Reuse existing test results when the code has not changed.

### Implementation
- Work on one milestone or clearly defined task at a time.
- Prefer the smallest implementation that satisfies the requirements.
- Do not implement future milestones prematurely.
- Avoid unnecessary dependencies, abstractions, and generated files.

### Testing
- Run focused tests first.
- Run broader regression tests when changes may affect other components.
- Do not repeat successful tests without a reason.
- Never skip essential security tests to save tokens.

### Communication
- Keep progress updates concise.
- Use short implementation plans.
- Report only:
  1. What changed.
  2. Files modified.
  3. Tests executed and results.
  4. Remaining issues.
- Explain complex decisions only when necessary.
- Ask only essential clarification questions.

### Tool Usage
- Avoid unnecessary tool calls.
- Combine independent read-only inspection commands when practical.
- Do not perform repeated searches for information already available.
- Never claim an action succeeded without verifying its result.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
