AWS Architecture Analysis & Migration Advisor

An AI-assisted tool that verifies a codebase's actual architecture against what a developer says it is, then produces a grounded, data-backed recommendation for a specific AWS migration scenario — starting with Lambda ↔ EC2.

The core principle: the analysis engine is deterministic and verifiable. The LLM only explains results after they've already been computed — it never invents numbers or makes the recommendation itself.

What It Does
Reads a codebase (a specific repo the user points it at).
Takes the user's stated architecture (e.g., "this is a monolith on EC2" or "these are Lambda functions handling X").
Cross-references the claim against the real code to verify it's accurate — flags mismatches.
Takes a migration scenario the user is considering (e.g., Lambda → EC2).
Outputs a structured report: pros/cons, real cost comparison, and a recommendation. The final decision stays with the user.
Why This Scope

The original idea was broader — "any architecture, any cloud, generate full migration reports with team size/timeline estimates." That version was cut because:

Team size / timeline estimates from a codebase read alone are essentially fabricated numbers with false precision.
A broad, open-ended "consulting report" generator reads as a thin LLM wrapper

Narrowed scope: AWS-only, one migration scenario done deeply (Lambda ↔ EC2), verification + real cost comparison instead of open-ended output.

Principle: depth over breadth. One migration scenario done rigorously beats five done shallowly.

MVP Service Scope

To keep Stage 1 (claim extraction) and Stage 3 (verification) matched — since Stage 4's comparison logic depends on both sides speaking the same fixed vocabulary — the MVP recognizes only the following AWS services. This list is intentionally narrow, matching the Lambda ↔ EC2 v1 target below; expanding it is deferred until that core loop is proven.

Field	Allowed values
compute_model	EC2, LAMBDA, UNSPECIFIED
trigger	API_GATEWAY, EVENTBRIDGE, SQS, S3, UNSPECIFIED
monitoring	CLOUDWATCH, UNSPECIFIED
dependencies	SQS, SNS, S3, UNSPECIFIED
database	DYNAMODB, RDS, UNSPECIFIED

Any AWS service mentioned by the user that falls outside this list is not yet recognized and will be extracted as UNSPECIFIED for its category. Containers (ECS/EKS) are explicitly out of scope for MVP.

Tech Stack
Backend / orchestration: Python
Code parsing: tree-sitter (via py-tree-sitter) — chosen over language-specific parsers (Python's ast, @babel/parser) for its unified, multi-language query API and its robustness against partial/messy real-world code.
Cost data: AWS Pricing API — real dollar figures, not LLM-estimated numbers.
LLM layer: used only as a final explanation/summarization step on top of already-computed, verified output.
Target codebases for v1: Node.js/TypeScript AWS CDK codebases (matches my own hands-on experience with both from co-op and prior Terraform projects, so I can speak credibly to what "correct" analysis looks like).
Build Order
1. AST / call-graph parser (the core hard problem — lead with this in the demo)

MVP source of truth: CDK infra-as-code only, not runtime handler tracing.

A CDK app declares its architecture in bin/ (a thin entrypoint that instantiates the App/Stacks — usually boilerplate, low signal) and lib/ (the actual Stack/Construct definitions — Lambdas, API Gateway, tables, permissions — this is where the real signal is). For MVP, Stage 1 parses only this declarative layer, not the runtime body of Lambda handler functions (e.g. actual SDK calls like dynamoClient.send(...) inside the handler).

This is a deliberate scope cut, not an oversight:

Every field in the MVP schema above (compute_model, trigger, monitoring, dependencies, database) is something CDK constructs declare directly — a Lambda is instantiated, wired to API Gateway via LambdaRestApi/.addEventSource, granted access to a table via .grantReadWriteData(). None of these require tracing into what the handler's code actually executes at runtime.
Runtime handler tracing (following imports, aliased SDK clients, indirection through helper functions) is a much harder, more open-ended AST problem — the same kind of scope creep the "Why This Scope" section above already cut once. It's deferred to a future increment.
It resolves the Lambda/EC2 asymmetry: EC2 codebases don't have a handler to trace in the first place. Scoping to declarative infra means both sides of the comparison are verified the same way — by what's declared in lib/, not by what's executed at runtime.

What infra.ts / lib/ can and can't tell you: construct instantiations often carry real config as literal arguments (e.g. memorySize, timeout, instanceType), so this isn't just "existence" data — but it only reflects what's declared, not runtime behavior that isn't visible in the construct definition itself.

Pipeline:

File discovery — walk the target repo, collect .ts files under bin/ and lib/ (skip node_modules, tests, .d.ts).
Parse pass — parse each file with tree-sitter's TypeScript grammar (tree-sitter-typescript) into a Concrete Syntax Tree (CST) per file. (Tree-sitter's headline feature is fast incremental re-parsing on edits, which isn't directly relevant here since files are parsed once; what matters for this project is the structured, queryable tree it produces.)
Construct-extraction query — a tree-sitter query matching new_expression nodes whose callee path matches a known CDK construct list (lambda.Function, apigateway.RestApi / LambdaRestApi, dynamodb.Table, ec2.Instance, rds.DatabaseInstance, sns.Topic, sqs.Queue, s3.Bucket, events.Rule). Capture, per match: construct type, the variable it's bound to, and its config object literal.
Relationship/wiring query — a second query for method calls that connect two constructs into an edge: .addEventSource(...), .grantInvoke(...), .grantReadWriteData(...), .addTarget(...), or a Lambda variable passed as a handler: prop into an API construct.
Internal graph model — nodes (typed constructs + captured config) and edges (relationships from step 4), built purely from steps 3–4, no LLM involved.
Map to schema — translate the graph into the same field/value vocabulary as the Stage 1 LLM claim-extraction output, so Stage 4's comparison logic is a plain diff between "what the user claimed" and "what the code declares," with no special-casing.

Config/resource definition files (e.g. swagger, JSON/YAML resource configs): parsed via json.load / yaml.safe_load, not tree-sitter — these are data files, not code with logic/branches, so a full grammar-based parse isn't needed.

Open design questions flagged for MVP (decide before/while implementing, not after):

Existence vs. identity. Is MVP "a Lambda exists with an API Gateway trigger somewhere in the stack" (existence-only — simpler), or "this specific Lambda has this specific trigger" (identity-tracked — matches a real call-graph, more work, needed if a stack has multiple Lambdas/tables)? This decision shapes the internal data model and should be made explicitly rather than defaulting silently.
Indirection. Constructs instantiated through a team's own wrapper/factory function (e.g. createStandardLambda(this, 'x', {...}) internally calling new lambda.Function(...)) won't be caught by a direct new_expression match. Not required for MVP, but the decision to explicitly scope this out (and document it) should be intentional, not a silent miss.
Multiple environments. MVP parses a single environment/config (e.g. one dev config); consolidating across environments (dev/staging/prod) is deferred to a future increment.

Output: a dependency/call graph — grounded in CDK infra-as-code, not runtime tracing — used for the verification step against the user's stated architecture.

2. Lambda ↔ EC2 comparison logic + real cost data
Pull real pricing from the AWS Pricing API.
Inputs: invocation count/frequency, memory/duration (Lambda) vs. instance type/uptime (EC2).
Output: cost comparison and the "crossover point" — e.g., "above ~X requests/month, EC2 becomes cheaper."
Encode qualitative tradeoffs (cold starts, operational overhead, scaling behavior, vendor lock-in) as structured rules, not LLM-generated text — more credible and consistent.
3. LLM layer (added last)
Takes the already-computed, verified output (graph + cost numbers + rule-based tradeoffs) and explains it in plain English.
Does not perform the analysis or generate the numbers itself.
Answers the "how do you know the AI isn't just making things up" question directly: the underlying logic works correctly even with the LLM layer removed entirely.
Key Principles
Every claim the tool makes should be explainable and correct, not just plausible-sounding.
Any number presented as fact must be grounded in real data (AWS Pricing API), never guessed.
The LLM's job is explanation, not decision-making.
Scope stays narrow and rigorous rather than broad and shallow.
Possible Future Expansion

(only after Lambda ↔ EC2 is solid and proven)

Runtime handler tracing (following actual SDK calls inside Lambda function bodies, not just declarative infra) — would tighten verification beyond "declared" to "declared and actually used."
Indirection/factory-function detection for CDK constructs.
Multi-environment consolidation (dev/staging/prod).
RDS ↔ DynamoDB comparison
Monolith → microservices on ECS
Broader "modernization suggestions" — once the core verification + cost engine is proven reliable
Status

🚧 In active development. Stage 1 (LLM claim extraction) is functional and manually tested. Currently scoping and building Stage 2: tree-sitter-based CDK infra-as-code parsing (bin/, lib/) into a dependency/call graph.
