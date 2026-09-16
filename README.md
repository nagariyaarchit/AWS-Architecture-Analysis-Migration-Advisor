# AWS Architecture Analysis & Migration Advisor

An AI-assisted tool that verifies a codebase's actual architecture against what a developer says it is, then produces a grounded, data-backed recommendation for a specific AWS migration scenario — starting with Lambda ↔ EC2.

The core principle: the analysis engine is deterministic and verifiable. The LLM only explains results after they've already been computed — it never invents numbers or makes the recommendation itself.

## What It Does
- Reads a codebase (a specific repo the user points it at).
- Takes the user's stated architecture (e.g., "this is a monolith on EC2" or "these are Lambda functions handling X").
- Cross-references the claim against the real code to verify it's accurate — flags mismatches.
- Takes a migration scenario the user is considering (e.g., Lambda → EC2).
- Outputs a structured report: pros/cons, real cost comparison, and a recommendation. The final decision stays with the user.

## Why This Scope

The original idea was broader — "any architecture, any cloud, generate full migration reports with team size/timeline estimates." That version was cut because:

- Team size / timeline estimates from a codebase read alone are essentially fabricated numbers with false precision.
- A broad, open-ended "consulting report" generator reads as a thin LLM wrapper — not defensible in a technical interview.

Narrowed scope: AWS-only, one migration scenario done deeply (Lambda ↔ EC2), verification + real cost comparison instead of open-ended output.

**Principle: depth over breadth.** One migration scenario done rigorously beats five done shallowly.

## MVP Service Scope

To keep Stage 1 (claim extraction) and Stage 3 (verification) matched — since Stage 4's comparison logic depends on both sides speaking the same fixed vocabulary — the MVP recognizes only the following AWS services. This list is intentionally narrow, matching the Lambda ↔ EC2 v1 target below; expanding it is deferred until that core loop is proven.

| Field | Allowed values |
|---|---|
| `compute_model` | `EC2`, `LAMBDA`, `UNSPECIFIED` |
| `trigger` | `API_GATEWAY`, `EVENTBRIDGE`, `SQS`, `S3`, `UNSPECIFIED` |
| `monitoring` | `CLOUDWATCH`, `UNSPECIFIED` |
| `dependencies` | `SQS`, `SNS`, `S3`, `UNSPECIFIED` |
| `database` | `DYNAMODB`, `RDS`, `UNSPECIFIED` |

Any AWS service mentioned by the user that falls outside this list is not yet recognized and will be extracted as `UNSPECIFIED` for its category. Containers (ECS/EKS) are explicitly out of scope for MVP.

## Tech Stack
- **Backend / orchestration:** Python
- **Code parsing:** tree-sitter (via py-tree-sitter) — chosen over language-specific parsers (Python's `ast`, `@babel/parser`) for its unified, multi-language query API and its robustness against partial/messy real-world code.
- **Cost data:** AWS Pricing API — real dollar figures, not LLM-estimated numbers.
- **LLM layer:** used only as a final explanation/summarization step on top of already-computed, verified output.
- **Target codebases for v1:** Node.js/JavaScript Lambda + EC2 setups (matches my own hands-on experience with both from co-op and prior Terraform projects, so I can speak credibly to what "correct" analysis looks like).

## Build Order

### 1. AST / call-graph parser (the core hard problem — lead with this in the demo)
- Use tree-sitter to parse the target codebase into a syntax tree.
- Write queries to extract meaningful patterns: which functions call which AWS services (e.g., DynamoDB, S3), which modules hold no external state, which services communicate over HTTP.
- Output: a dependency/call graph used for the verification step against the user's stated architecture.

### 2. Lambda ↔ EC2 comparison logic + real cost data
- Pull real pricing from the AWS Pricing API.
- Inputs: invocation count/frequency, memory/duration (Lambda) vs. instance type/uptime (EC2).
- Output: cost comparison and the "crossover point" — e.g., "above ~X requests/month, EC2 becomes cheaper."
- Encode qualitative tradeoffs (cold starts, operational overhead, scaling behavior, vendor lock-in) as structured rules, not LLM-generated text — more credible and consistent.

### 3. LLM layer (added last)
- Takes the already-computed, verified output (graph + cost numbers + rule-based tradeoffs) and explains it in plain English.
- Does not perform the analysis or generate the numbers itself.
- Answers the "how do you know the AI isn't just making things up" question directly: the underlying logic works correctly even with the LLM layer removed entirely.

## Key Principles
- Every claim the tool makes should be explainable and correct, not just plausible-sounding.
- Any number presented as fact must be grounded in real data (AWS Pricing API), never guessed.
- The LLM's job is explanation, not decision-making.
- Scope stays narrow and rigorous rather than broad and shallow.

## Possible Future Expansion

*(only after Lambda ↔ EC2 is solid and proven)*

- RDS ↔ DynamoDB comparison
- Monolith → microservices on ECS
- Broader "modernization suggestions" — once the core verification + cost engine is proven reliable

## Status

🚧 In active development. Currently building the tree-sitter-based call-graph extraction (Phase 1).
