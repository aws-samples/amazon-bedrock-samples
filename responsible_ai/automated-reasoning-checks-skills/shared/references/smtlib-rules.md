# Writing AR Rules (SMT-LIB subset) & Modeling Patterns

Rules are formal-logic expressions in a **subset of SMT-LIB**. Most rules should be **if-then
(implicative)**: a condition (`if`) and a conclusion (`then`) joined by `=>`.

## Operators
| Operator | Meaning | Example |
|---|---|---|
| `=>` | implication (if-then) | `(=> isFullTime eligibleForBenefits)` |
| `and` | logical AND | `(and isFullTime (> tenureMonths 12))` |
| `or` | logical OR | `(or isVeteran isTeacher)` |
| `not` | logical NOT | `(not isTerminated)` |
| `=` | equality | `(= employmentType FULL_TIME)` |
| `>` `<` `>=` `<=` | comparison | `(>= creditScore 700)` |

Well-formed:
```
;; If full-time AND tenure > 12 months, then eligible for parental leave.
(=> (and isFullTime (> tenureMonths 12)) eligibleForParentalLeave)
;; If loan > 500,000, then a co-signer is required.
(=> (> loanAmount 500000) requiresCosigner)
```

## ⚠️ Bare assertions = the #1 trap
A rule with no if-then (e.g. `eligibleForParentalLeave` or `(= eligibleForParentalLeave true)`)
becomes an **axiom** — always true — so any input claiming the opposite returns `IMPOSSIBLE`.
Only use bare assertions for genuine **boundary conditions**:
```
;; GOOD: account balance can't be negative
(>= accountBalance 0)
;; BAD: asserts eligibility unconditionally
eligibleForParentalLeave
```

## Variable types
`BOOL` · `INT` (whole number) · `NUMBER` (decimal) · **custom enum** (one of a fixed value set).

### Variable descriptions are the #1 accuracy lever
A good description states: what the variable means · the **unit/format** · **synonyms & alt-phrasings**
users use · **boundary conditions**. Example:
> `tenureMonths`: "The number of complete months the employee has been continuously employed. When
> users mention years of service, convert to months (2 years = 24 months). Set to 0 for new hires."

## Modeling patterns (best practices)
- **Implications over assertions** — structure rules as `(=> condition conclusion)`.
- **Enums for mutually-exclusive states; booleans for co-existing states.** A person can be veteran
  AND teacher → two booleans, not an enum (an enum would force a false choice → contradictions).
  Add an `OTHER`/`NONE` enum value when input might not match any value.
- **Validate numeric ranges** with boundary rules (`(>= age 0)`, `(<= age 150)`).
- **Intermediate variables** for abstraction — name a derived concept once, reference it in many rules.
- **Describe what is true, not how to compute it.** AR models facts, not algorithms. Avoid rules that
  require the translation step to calculate values.
- **Avoid:** contradictory rules, unused variables, duplicate/near-duplicate variables
  (`tenureMonths` vs `monthsOfService`), circular dependencies, nonlinear arithmetic (→ `TOO_COMPLEX`).
- **Namespace:** variable names, type names, and enum values share **one namespace** — all unique.
  Prefix collisions: `LeaveType_OTHER`, `Severity_OTHER`.

## Not a fit for AR
Char-by-char / string-format validation (e.g. password rules) — use deterministic code instead.
AR reasons over natural-language concepts mapped to typed variables, not raw text.
