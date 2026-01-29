# AR Chatbot - System Design

## Overview

The AR Chatbot validates LLM responses against AWS Guardrails policies using automated reasoning. It provides an iterative rewriting loop where invalid responses are automatically corrected based on policy feedback, with support for follow-up questions when clarification is needed.

**Tech Stack:** Python/Flask backend, React/TypeScript frontend, AWS Bedrock (LLM), AWS Guardrails (validation)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Config   │  │   Chat   │  │  Debug   │               │
│  │ Panel    │  │  Panel   │  │  Panel   │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       └─────────────┼─────────────┘                     │
│                     │ APIClient                         │
└─────────────────────┼───────────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────┼─────────────────────────────────┐
│              ┌──────▼──────┐                          │
│              │  Flask App  │                          │
│              └──────┬──────┘                          │
│                     │                                 │
│       ┌─────────────┼─────────────┐                   │
│       │             │             │                   │
│  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐                │
│  │ Config  │  │ Thread  │  │ Service │                │
│  │ Manager │  │Processor│  │Container│                │
│  └─────────┘  └─────────┘  └────┬────┘                │
│                                  │                    │
│         Backend Services (10 core services)           │
│    ┌─────────────────────────────┴──────────┐         │
│    │ ThreadManager │ LLMService │ Validation│         │
│    │ PolicyService │ Parser │ TemplateManager│        │
│    │ IterationHandler │ AuditLogger │ Timeout│        │
│    │ TestCaseService                         │        │
│    └─────────────────────────────────────────┘        │
└───────────────────────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
      ┌─────▼─────┐      ┌─────▼─────┐
      │   AWS     │      │    AWS    │
      │  Bedrock  │      │ Guardrails│
      └───────────┘      └───────────┘
```

---

## Backend Architecture

### Service Container (Dependency Injection)

```
ServiceContainer
├── Always Initialized
│   ├── ThreadManager
│   ├── AuditLogger
│   ├── TimeoutHandler
│   └── TestCaseService
│
└── Lazy Initialized (on first access)
    ├── PolicyService (requires policy definition)
    ├── LLMService (requires config + policy context)
    ├── ValidationService (requires guardrail)
    ├── LLMResponseParser
    └── PromptTemplateManager
```

Note: `RetryHandler` is a standalone utility module providing decorators for AWS API retry logic with exponential backoff, not a service in the container.

### Core Services

**ThreadManager** - Thread lifecycle (CRUD, status, locking)  
**ThreadProcessor** - State machine for validation/rewriting loop, handles iterations  
**LLMService** - Bedrock LLM interface, retry logic, prompt generation  
**ValidationService** - Guardrails validation interface  
**PolicyService** - Finding sorting, enrichment, policy context formatting  
**LLMResponseParser** - Parse LLM decisions (REWRITE/ASK_QUESTIONS/IMPOSSIBLE)  
**PromptTemplateManager** - Load/render templates, auto-append policy context  
**AuditLogger** - JSON audit logging  
**TimeoutHandler** - Auto-resume stale threads  
**ConfigManager** - Config management, AWS integration  
**TestCaseService** - Fetch test cases for policies  
**RetryHandler** - Utility module for AWS API retry with exponential backoff

---

## Thread Processing Flow

```
User submits prompt
         │
         ▼
Create thread → Generate initial response
         │
         ▼
Validate with Guardrails
         │
         ▼
Enrich findings with policy rules
         │
         ▼
Store as iteration 0 (AR_FEEDBACK)
         │
         ▼
Check for questions in response
         │
    ┌────┴────┐
    │         │
Questions   No questions
    │         │
    ▼         ▼
 Pause    Handle validation
for user     outcome
 input       │
    │    ┌───┴───┐
    │    │       │
    │  VALID  INVALID
    │    │       │
    │    ▼       ▼
    │  Done   Rewriting
    │          loop
    │           │
    └───────────┘
```

### Rewriting Loop

```
Select highest priority finding
         │
         ▼
Generate rewriting prompt
         │
         ▼
LLM generates response
         │
         ▼
Parse LLM decision
         │
    ┌────┴────┐
    │         │
 REWRITE  ASK_QUESTIONS
    │         │
    ▼         ▼
Validate  Pause for
response  user input
    │         │
    ▼         ▼
Store as  Store as
AR_FEEDBACK  USER_CLARIFICATION
iteration    iteration
    │         │
    │         ▼
    │    Wait for answers
    │         │
    │         ▼
    │    Generate new response
    │         │
    │         ▼
    │    Validate response
    │         │
    └─────────┴─────────┐
                        │
                        ▼
              Check if VALID or
              max iterations reached
                        │
                   ┌────┴────┐
                   │         │
                 VALID   Continue
                   │      loop
                   ▼
                 Done
```

---

## Policy Context Flow

Policy rules and variables are injected into prompts via two mechanisms:

```
PolicyService.format_policy_context()
    (Formats rules + variables as markdown)
         │
         ├─────────────────────────────┐
         │                             │
         ▼                             ▼
   LLMService                  TemplateManager
   (stores context)            (receives context)
         │                             │
         ▼                             ▼
   Prepends to ALL            Renders template
   prompts sent to                    │
   Bedrock                    ┌───────┴───────┐
         │                    │               │
         │              Has {{policy_    No placeholder
         │              context}}?            │
         │                    │               │
         │                    ▼               ▼
         │              Replace         Auto-append
         │              inline          at end
         │                    │               │
         │                    └───────┬───────┘
         │                            │
         └────────────────────────────┘
                                      │
                                      ▼
                          Final prompt to Bedrock
                     (Policy context may appear twice)
```

**Why twice?** Ensures LLM always has policy access even if template author forgets to include `{{policy_context}}` placeholder.

---

## Data Models

### Thread

```
Thread
├── thread_id: str (UUID)
├── user_prompt: str
├── model_id: str
├── status: ThreadStatus (PROCESSING/AWAITING_USER_INPUT/COMPLETED/ERROR)
├── final_response: str | None
├── warning_message: str | None
├── iterations: List[TypedIteration]
├── iteration_counter: int
├── max_iterations: int (from config)
├── processed_finding_indices: Set[int]
├── current_findings: List[Finding]
├── all_clarifications: List[QuestionAnswerExchange]
├── schema_version: str
├── awaiting_input_since: datetime | None
├── created_at: datetime
└── completed_at: datetime | None
```

### TypedIteration

```
TypedIteration
├── iteration_number: int
├── iteration_type: IterationType (AR_FEEDBACK | USER_CLARIFICATION)
├── original_answer: str
├── rewritten_answer: str
├── rewriting_prompt: str
└── type_specific_data: ARIterationData | ClarificationIterationData
```

**ARIterationData:**
- findings: List[Finding]
- validation_output: str
- processed_finding_index: int | None
- llm_decision: str (REWRITE/ASK_QUESTIONS/IMPOSSIBLE)
- iteration_type: str (initial/rewriting/final)

**ClarificationIterationData:**
- qa_exchange: QuestionAnswerExchange
- context_augmentation: str | None
- processed_finding_index: int | None
- llm_decision: str
- validation_output: str | None (post-clarification)
- validation_findings: List[Finding] (post-clarification)

---

## Frontend Architecture

```
App (global state + polling)
├── ConfigPanel
│   └── Model/policy selection, max iterations
├── ChatPanel
│   ├── Thread list
│   └── ThreadMessage
│       ├── InitialAnswerView (iteration 0)
│       │   ├── ValidationBadge
│       │   └── FindingsList
│       ├── IterationView (iterations 1+)
│       │   ├── OriginalAnswerSection
│       │   └── ValidationResult
│       └── Q&A UI (when AWAITING_USER_INPUT)
├── DebugPanel (sliding panel)
│   └── Full thread inspection
├── TestPromptBrowser (sliding panel)
│   └── Browse and select test prompts for policy
├── ConfirmationDialog
│   └── Confirm actions (e.g., replace unsent text)
└── RuleEvaluationModal
    └── Display rule evaluation details
```

**Shared Components:** CollapsibleSection, ValidationBadge, FindingsList, FindingDetails, FormInput, StatusIndicator, StateDisplay (EmptyState, LoadingState, ErrorState), Message, SidePanel, WarningMessage, FlowNote, SectionHeader

**State Management:** React hooks, polling every 1s for active threads

**API Client:** Axios-based centralized HTTP client

---

## Key Workflows

### Configuration Update

```
User selects model + policy
  → POST /api/config
  → ConfigManager updates config
  → ConfigManager ensures Guardrail exists
  → ServiceContainer resets services
  → New services initialized with new config
```

### Follow-Up Questions

```
LLM response contains QUESTION: markers
  → Parser detects questions
  → Create USER_CLARIFICATION iteration
  → Set status to AWAITING_USER_INPUT
  → Frontend displays Q&A UI
  → User provides answers (or skips)
  → POST /api/thread/{id}/answer
  → Create context augmentation from Q&A
  → Generate new response with augmented context
  → Validate new response
  → Continue rewriting loop if not VALID
```

### Timeout Handling

```
TimeoutHandler runs every 30s
  → Check threads in AWAITING_USER_INPUT
  → Filter threads older than 5 min
  → For each stale thread:
      → Call resume callback with skipped=True
      → Generate response without user answers
      → Continue validation workflow
```

---

## Testing Strategy

**Unit Tests** - Individual service methods, mocked dependencies  
**Integration Tests** - End-to-end workflows with mocked AWS  
**Property-Based Tests** - Hypothesis for random input validation

```bash
# Backend
cd backend && python -m pytest -v

# Frontend
cd frontend && npm test
```

---

## Development

### Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Run

```bash
# Development (2 terminals)
cd backend && python flask_app.py
cd frontend && npm start

# Production
cd frontend && npm run build
cd backend && python flask_app.py
```

---

## Architecture Decisions

**ServiceContainer** - Centralized dependency management, lazy initialization, easy testing  
**ThreadProcessor State Machine** - Clear state-based control flow for validation/rewriting loop  
**TypedIteration** - Clear AR vs user clarification distinction, type-safe data  
**PolicyService** - Consolidated finding operations (sorting, enrichment, formatting)  
**RetryHandler** - Decorator-based retry logic with exponential backoff for AWS API resilience  
**Polling vs WebSockets** - Simpler implementation, adequate for use case  
**Dual Policy Injection** - Ensures LLM always has policy context (prepend + template)

---

## API Endpoints

**Configuration**
- `GET /api/config/models` - List available models
- `GET /api/config/policies` - List available policies
- `GET /api/config` - Get current config
- `POST /api/config` - Update config

**Chat**
- `POST /api/chat` - Submit prompt, create thread
- `GET /api/thread/{id}` - Get thread status
- `GET /api/threads` - List all threads
- `POST /api/thread/{id}/answer` - Submit answers to questions

**Test Cases**
- `GET /api/policy/{arn}/test-cases` - Get test cases for policy

---

## Validation Outcomes

**VALID** - Response is correct, log to audit, return to user  
**INVALID** - Response contradicts rules, enter rewriting loop  
**IMPOSSIBLE** - Contradictory premises, LLM explains why  
**SATISFIABLE** - Could be true or false, enter rewriting loop  
**TRANSLATION_AMBIGUOUS** - Ambiguous input, enter rewriting loop  
**TOO_COMPLEX** - Cannot validate, return error  
**NO_TRANSLATIONS** - No logical content, return with/without warning

---

For detailed implementation, see code comments and `.kiro/specs/` for feature specifications.
