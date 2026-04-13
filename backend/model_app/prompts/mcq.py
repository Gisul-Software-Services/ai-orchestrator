_CODE_TOPIC_KEYWORDS = [
    # ── Slicing / indexing ────────────────────────────────────────────────
    # These unambiguously describe expression-output questions.
    'slicing',
    'slice',
    'list slicing',
    'string slicing',
    'list indexing',
    'string indexing',
    'index notation',
    'negative indexing',

    # ── Explicit output-prediction framing ───────────────────────────────
    # Any topic phrased this way is asking the student to evaluate an expression.
    'output prediction',
    'what is the output',
    'predict the output',
    'code output',
    'python output',
    'print result',
    'print output',

    # ── Comprehension / generator — ONLY with 'output' qualifier ─────────
    # "list comprehension" alone is a concept topic; "list comprehension output"
    # is an execution question. The qualifier ensures correct routing.
    'list comprehension output',
    'generator expression output',

    # ── Lambda / async — ONLY with 'output' qualifier ────────────────────
    'lambda output',
    'async output',

    # ── Generic code-execution phrasings ─────────────────────────────────
    'code execution',
    'expression evaluation',
]


def build_mcq_context_prompt(req: dict) -> str:
    """
    Deterministic-first prompt: LLM generates context ONLY (no correct answer).
    System executes the expression and builds the correct answer itself.
    Used for all Python output-prediction / executable MCQs.
    """
    return f"""
You are generating raw material for a Python output-prediction MCQ.
Topic: {req['topic']}
Difficulty: {req['difficulty']}
Audience: {req['target_audience']}

YOUR ONLY JOB: Generate the code scenario. Do NOT compute or include the correct answer.
The system will execute the code and determine the correct answer automatically.

STRICT RULES:
- setup_code: 1-5 lines of plain Python assignments/definitions. No imports.
  Must be self-contained and executable as-is.
- expression: ONE single Python expression that can be evaluated with eval().
  No print(). No assignment. No semicolons. Just the expression itself.
  Example: "numbers[1::2]"  or  "len(data) * 2"  or  "sorted(d.items())"
- distractors: exactly 3 WRONG answers a student commonly guesses.
  Must be plausible Python literal values — NOT the real output.
  Must differ from each other and from the real answer.
  Use common off-by-one errors, wrong step values, wrong indices.
- explanation_template: explain the concept clearly. Use the exact placeholder
  {{CORRECT_ANSWER}} where the computed result should appear.
- question: full question text including the code and the expression to evaluate.
  Format it as: "Given:\\n\\n<setup_code>\\n\\nWhat is the value of: <expression>"
- Do NOT include the correct answer anywhere in this JSON. Not in distractors,
  not in explanation_template, not in question. The system computes it.
- Return ONLY valid JSON — no markdown, no extra text.

PYTHON RULES (generate correct setup_code and expression):
- List slicing never raises IndexError — out-of-range slices return empty list.
- [::-1] reverses the entire sequence.
- dict.items(), .keys(), .values() return views in Python 3 — wrap in list() if needed.
- Mutable default arguments persist across calls.
- is vs == : is checks identity, == checks equality.
- range() is lazy; list(range(n)) gives a list.

JSON FORMAT (return exactly this structure):
{{
  "question": "Given:\\n\\nnumbers = [10, 20, 30, 40, 50]\\n\\nWhat is the value of: numbers[1::2]",
  "setup_code": "numbers = [10, 20, 30, 40, 50]",
  "expression": "numbers[1::2]",
  "distractors": ["[10, 30, 50]", "[20, 40]", "[10, 20, 30]"],
  "explanation_template": "The slice [1::2] starts at index 1 and steps by 2, picking every second element from index 1 onward. The result is {{CORRECT_ANSWER}}.",
  "difficulty": "{req['difficulty']}",
  "bloomLevel": "Apply"
}}
"""


def build_mcq_prompt(req: dict) -> str:
    topic_lower = req['topic'].lower()

    # -------------------------------------------------------------------------
    # ROUTING: deterministic pipeline vs conceptual pipeline
    #
    # Check whether any execution-specific keyword is present in the topic.
    # _CODE_TOPIC_KEYWORDS contains ONLY slicing/indexing/output-prediction
    # signals — NOT broad language names or concept-level topics.
    #
    # Examples that DO route here (deterministic):
    #   "Python list slicing"             → 'list slicing' matches
    #   "String slicing with step"        → 'slicing' matches
    #   "Output prediction: list indexing"→ 'output prediction' matches
    #   "What is the output of slicing"   → 'what is the output' matches
    #
    # Examples that do NOT route here (conceptual):
    #   "Python decorators"               → no execution keyword present
    #   "Python closures"                 → no execution keyword present
    #   "Python OOP"                      → no execution keyword present
    #   "Asyncio fundamentals"            → no execution keyword present
    #   "List comprehension basics"       → bare 'list comprehension' not in list
    #   "Lambda functions"                → bare 'lambda' not in list
    # -------------------------------------------------------------------------
    if any(k in topic_lower for k in _CODE_TOPIC_KEYWORDS):
        return build_mcq_context_prompt(req)

    # Detect domain for domain-specific guidance injection
    domain_hint = ""

    if any(k in topic_lower for k in ['python', 'slicing', 'list comprehension', 'generator', 'decorator', 'gil', 'asyncio']):
        domain_hint = """
PYTHON-SPECIFIC RULES:
- List slicing never raises IndexError — out-of-range slices return empty list.
- [::-1] reverses the entire sequence.
- range() is lazy; list(range()) is a list.
- dict.items(), .keys(), .values() return views, not lists, in Python 3.
- Mutable default arguments (e.g. def f(x=[])) persist across calls — classic bug.
- Global variables require the `global` keyword to be reassigned inside functions.
- is vs == : 'is' checks identity, '==' checks equality.
- For output prediction questions: include FULL executable code inline (no fences).
- Options MUST be pure Python literal values (e.g. [1,2,3], True, 'hello').
"""
    elif any(k in topic_lower for k in ['javascript', 'node', 'nodejs', 'es6', 'promise', 'async/await', 'closure', 'hoisting', 'event loop']):
        domain_hint = """
JAVASCRIPT/NODE-SPECIFIC RULES:
- var is function-scoped and hoisted; let/const are block-scoped.
- typeof null === 'object' is a known quirk.
- == does type coercion; === does strict comparison.
- Promises: .then() runs asynchronously even when already resolved.
- async functions always return a Promise.
- Arrow functions do NOT have their own `this`.
- NaN !== NaN; use Number.isNaN() to check.
- Node.js require() is synchronous; import is static and hoisted.
- Event loop: microtasks (Promise callbacks) run before macrotasks (setTimeout).
"""
    elif any(k in topic_lower for k in ['react', 'hooks', 'usestate', 'useeffect', 'jsx', 'component', 'props', 'virtual dom']):
        domain_hint = """
REACT-SPECIFIC RULES:
- useState setter is asynchronous — state does NOT update in the same render cycle.
- useEffect with [] runs only on mount, NOT on every render.
- useEffect with no dependency array runs after EVERY render.
- Keys in lists must be unique and stable — never use array index as key when items can reorder.
- props are READ-ONLY — components must not mutate their props.
- Conditional rendering with && short-circuit: {0 && <Comp/>} renders 0, not nothing.
- React batches state updates in event handlers (React 18+).
- useRef does not trigger re-renders when ref.current changes.
"""
    elif any(k in topic_lower for k in ['next.js', 'nextjs', 'next js', 'app router', 'pages router', 'getserversideprops', 'getstaticprops', 'ssr', 'ssg', 'isr']):
        domain_hint = """
NEXT.JS-SPECIFIC RULES:

ROUTER CONSISTENCY (CRITICAL - READ FIRST):
- Next.js has TWO routers: Pages Router (pages/ dir) and App Router (app/ dir).
- You MUST pick exactly ONE router for the entire question. NEVER mix them.
- If your question shows an app/ directory structure: ALL options MUST use App Router patterns only.
- If your question shows a pages/ directory structure: ALL options MUST use Pages Router patterns only.
- FORBIDDEN: Showing app/blog/[id]/page.tsx in question but using getServerSideProps in options.
- FORBIDDEN: Showing pages/blog/[id].js in question but using useParams() from next/navigation.
- If unsure which router to use: default to Pages Router for getServerSideProps/getStaticProps questions,
  and App Router for useParams/Server Component questions.

PAGES ROUTER (pages/ directory):
- pages/about.js maps to route /about (NEVER /pages/about).
- pages/api/users.js maps to /api/users (NEVER /pages/api/users).
- Dynamic: pages/blog/[id].js maps to /blog/:id. Access via useRouter().query.id or context.params.id.
- SSR (every request): export async function getServerSideProps(context)
- SSG (build time): export async function getStaticProps(context)
- Dynamic SSG also needs: export async function getStaticPaths()
- ISR: getStaticProps with return value containing revalidate: N
- Client-side fetch: useRouter() for params, then useEffect + fetch or SWR/React Query.

APP ROUTER (app/ directory - Next.js 13+):
- app/about/page.tsx maps to route /about.
- app/blog/[id]/page.tsx maps to route /blog/:id.
- Server Components (default): async component, fetch data directly with await fetch(). NO getServerSideProps.
- Client Components: add 'use client' directive at top of file.
- Get dynamic params in Client Component: useParams() from 'next/navigation'.
- Get dynamic params in Server Component: props.params.id directly.
- Client-side fetch: 'use client' + useParams() + useEffect + fetch, or SWR/React Query.
- getServerSideProps, getStaticProps, getStaticPaths do NOT exist in App Router.

DATA FETCHING (which function goes where):
- SSR every-request (Pages Router only) = getServerSideProps
- SSG at build time (Pages Router only) = getStaticProps
- Server Component data (App Router only) = async component + fetch() with cache settings
- Client-side fetch (both routers) = useEffect + fetch, SWR, or React Query
- getServerSideProps and getStaticProps are NEVER used in App Router. NEVER.
"""
    elif any(k in topic_lower for k in ['sql', 'database', 'query', 'join', 'group by', 'having', 'index', 'normalization', 'transaction']):
        domain_hint = """
SQL-SPECIFIC RULES:
- JOIN without ON is a CROSS JOIN (cartesian product), NOT an INNER JOIN.
- WHERE filters rows BEFORE grouping; HAVING filters AFTER grouping.
- GROUP BY must include all non-aggregated SELECT columns.
- NULL comparisons MUST use IS NULL / IS NOT NULL, never = NULL.
- COUNT(*) counts all rows; COUNT(col) skips NULLs.
- DISTINCT removes duplicate rows; UNIQUE is a constraint.
- Subquery in WHERE with IN: NULLs in the subquery result cause unexpected no-matches.
- PRIMARY KEY implies UNIQUE + NOT NULL.
- TRUNCATE vs DELETE: TRUNCATE is DDL and cannot be rolled back in most RDBMS.
- CHAR is fixed-length; VARCHAR is variable-length.
"""
    elif any(k in topic_lower for k in ['typescript', 'ts', 'interface', 'type alias', 'generic', 'enum', 'union', 'intersection']):
        domain_hint = """
TYPESCRIPT-SPECIFIC RULES:
- interface and type alias are mostly interchangeable but interface supports declaration merging.
- any disables type checking; unknown forces type checking before use — prefer unknown.
- Type assertions (as) do not perform runtime checks.
- Enums compile to objects at runtime; const enum inlines values and produces no runtime object.
- Optional chaining (?.) returns undefined, not null, if the chain is broken.
- Nullish coalescing (??) triggers only on null/undefined, not on 0 or ''.
- Generics are erased at runtime — no runtime type information from generics.
- never is the return type of functions that never return (throw or infinite loop).
"""
    elif any(k in topic_lower for k in ['java', 'jvm', 'spring', 'oop', 'inheritance', 'polymorphism', 'interface', 'abstract', 'garbage collection']):
        domain_hint = """
JAVA/OOP-SPECIFIC RULES:
- Java passes object references by value — the reference is copied, not the object.
- == compares references for objects; .equals() compares content.
- String pool: string literals are interned; new String("x") creates a new object.
- abstract class can have implementation; interface (pre-Java 8) cannot.
- Java 8+: interfaces can have default and static methods.
- final class cannot be extended; final method cannot be overridden; final variable cannot be reassigned.
- Autoboxing: int ↔ Integer. Integer cache applies only for values -128 to 127.
- Checked exceptions must be declared or caught; unchecked (RuntimeException) need not be.
- super() must be the FIRST statement in a constructor if used.
- Garbage collection: objects are eligible when no live references remain.
"""
    elif any(k in topic_lower for k in ['git', 'version control', 'merge', 'rebase', 'branch', 'commit', 'cherry-pick', 'stash']):
        domain_hint = """
GIT-SPECIFIC RULES:
- git merge creates a merge commit preserving full history.
- git rebase rewrites commit history — do NOT rebase shared/public branches.
- git reset --hard destroys uncommitted changes permanently.
- git revert creates a NEW commit that undoes a previous commit (safe for shared branches).
- git stash saves dirty working directory temporarily; git stash pop restores it.
- git cherry-pick applies a specific commit from another branch.
- Detached HEAD: HEAD points to a commit, not a branch — commits can be lost.
- git pull = git fetch + git merge (or rebase with --rebase flag).
- origin/main is a remote-tracking branch, not the remote itself.
"""
    elif any(k in topic_lower for k in ['docker', 'container', 'kubernetes', 'k8s', 'image', 'dockerfile', 'volume', 'network', 'pod']):
        domain_hint = """
DOCKER/KUBERNETES-SPECIFIC RULES:
- Docker images are immutable layers; containers are running instances of images.
- COPY vs ADD: COPY is preferred; ADD can auto-extract tarballs (use only when needed).
- CMD sets default command; ENTRYPOINT sets fixed command. CMD args override; ENTRYPOINT args append.
- ENV sets environment variables at build AND runtime; ARG only at build time.
- Volumes persist data beyond container lifecycle; bind mounts link to host filesystem.
- Docker networking: bridge (default), host (no isolation), none.
- Kubernetes Pod = smallest deployable unit; can contain multiple containers.
- kubectl apply is declarative; kubectl create is imperative.
- ConfigMap stores non-sensitive config; Secret stores sensitive config (base64 encoded, NOT encrypted by default).
- Liveness probe: restarts container if it fails; Readiness probe: removes from service if it fails.
"""
    elif any(k in topic_lower for k in ['rest', 'api', 'http', 'status code', 'authentication', 'jwt', 'oauth', 'graphql', 'websocket']):
        domain_hint = """
REST/API-SPECIFIC RULES:
- GET is idempotent and safe (no side effects); POST is neither.
- PUT replaces the entire resource; PATCH applies partial updates.
- DELETE is idempotent (deleting already-deleted resource returns 404 or 204, same result).
- 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden,
  404 Not Found, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error.
- JWT: header.payload.signature — payload is base64 encoded, NOT encrypted.
- OAuth2: Authorization Code flow for web apps; Client Credentials for machine-to-machine.
- CORS: preflight OPTIONS request is sent before cross-origin requests with custom headers.
- REST is stateless — server stores no session state between requests.
- GraphQL: single endpoint, client specifies exact fields needed (no over/under-fetching).
"""
    elif any(k in topic_lower for k in ['algorithm', 'data structure', 'big o', 'complexity', 'sorting', 'graph', 'tree', 'binary search', 'hash', 'linked list', 'stack', 'queue', 'heap', 'dp', 'dynamic programming']):
        domain_hint = """
ALGORITHMS/DATA STRUCTURES-SPECIFIC RULES:
- Big O measures asymptotic worst-case growth, not exact runtime.
- O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2^n) < O(n!)
- Binary search requires a SORTED array; O(log n).
- Hash table average O(1) lookup; worst case O(n) due to collisions.
- BFS uses a queue; DFS uses a stack (or recursion).
- BFS finds shortest path in unweighted graphs; Dijkstra for weighted graphs.
- In-order traversal of BST gives sorted output.
- Heap: parent is always larger (max-heap) or smaller (min-heap) than children.
- Dynamic programming requires overlapping subproblems and optimal substructure.
- Quicksort average O(n log n), worst O(n²); Mergesort always O(n log n) but needs O(n) space.
- Linked list: O(n) access, O(1) insert/delete at head.
"""
    elif any(k in topic_lower for k in ['aws', 'cloud', 'azure', 's3', 'ec2', 'lambda', 'gcp', 'serverless', 'vpc', 'iam']):
        domain_hint = """
CLOUD/AWS-SPECIFIC RULES:
- S3 is object storage (not a file system); keys are flat, folders are prefixes.
- EC2 is IaaS; Lambda is FaaS (serverless, stateless, ephemeral).
- IAM: Users have credentials; Roles are assumed by services/instances.
- IAM policies: explicit Deny overrides any Allow.
- VPC: private network inside AWS; subnets can be public (internet gateway) or private.
- Security Groups are stateful (return traffic auto-allowed); NACLs are stateless.
- RDS: managed relational DB; DynamoDB: managed NoSQL key-value/document store.
- CloudFront: CDN (edge caching); Route 53: DNS service.
- Lambda cold start: first invocation has latency; provisioned concurrency eliminates it.
- SQS: message queue (pull); SNS: pub/sub notifications (push).
"""
    elif any(k in topic_lower for k in ['system design', 'scalability', 'load balancer', 'caching', 'microservices', 'message queue', 'cdn', 'sharding', 'cap theorem', 'consistency']):
        domain_hint = """
SYSTEM DESIGN-SPECIFIC RULES:
- CAP theorem: Consistency, Availability, Partition Tolerance — can only guarantee 2 of 3.
- CP systems (Zookeeper, HBase): consistent but may be unavailable during partition.
- AP systems (Cassandra, DynamoDB): available but may return stale data during partition.
- Horizontal scaling: add more machines. Vertical scaling: add more resources to one machine.
- Load balancer distributes traffic; does NOT cache responses (that's a CDN/reverse proxy).
- Write-through cache: write to cache AND DB simultaneously.
- Write-back cache: write to cache first, DB later (faster but risk of data loss).
- Read-through cache: application reads from cache; cache fetches from DB on miss.
- Message queues decouple producers and consumers; enable async processing.
- Sharding (horizontal partitioning) splits data across multiple DB instances.
- Consistent hashing minimizes reshuffling when nodes are added/removed.
"""
    else:
        domain_hint = """
GENERAL TECHNICAL RULES:
- Answer must be unambiguous — only ONE option is defensibly correct.
- Avoid trick questions based on obscure edge cases.
- Prefer standard, widely-accepted behavior over implementation-specific quirks.
- Do not mix concepts from different language versions unless explicitly stated.
"""

    return f"""
You are a senior technical examiner creating professional assessment questions.

Create ONE {req['difficulty']} multiple-choice question about: {req['topic']}
Target audience: {req['target_audience']}

{domain_hint}

UNIVERSAL STRICT RULES:
- Write a COMPLETE, REAL question — NO placeholders like "...", "example", or "TBD".
- EXACTLY ONE option must be correct. All other three must be clearly incorrect.
- Explanation MUST match the correct option and explain WHY others are wrong.
- For output prediction questions: include FULL executable code inline as plain text lines.
- Do NOT use triple backticks, code fences, or language labels before code.
- Do NOT write "python" or "javascript" as a standalone word before code.
- Write code directly as plain indented lines.
- For code questions: options MUST be pure literal values (e.g. [1,2,3], True, 'hello', 42).
- Do NOT include explanation text inside options.
- Return ONLY valid JSON — no markdown, no extra text outside the JSON.

ANTI-AMBIGUITY RULES (CRITICAL):
- Do NOT use vague phrases: "best practice", "recommended approach", "modern way",
  "latest method", "preferred way", "most efficient", "correct way" — unless the question
  is locked to a specific version or documented constraint.
- If framework version matters: state it explicitly.
  GOOD: "In Next.js App Router (Next.js 13+), which hook gets dynamic route params in a Client Component?"
  BAD:  "What is the best way to get route params in Next.js?"
- Rewrite opinion-based questions as factual, constraint-based questions so only ONE answer
  is correct from official documentation.
  GOOD: "Which Next.js Pages Router function fetches data on every server request?"
  BAD:  "What is the recommended data fetching method in Next.js?"
- Never mark an officially documented API as wrong unless the question explicitly
  excludes it (e.g. "without using getServerSideProps").
- ALL code snippets inside options must be syntactically valid. An option with
  undefined variables, missing imports, or syntax errors is INVALID and must not be used.

OPTION QUALITY RULES:
- All 4 options must be plausible — avoid obviously absurd distractors.
- Distractors should represent common mistakes or misconceptions.
- Options should be similar in length and format.
- For conceptual questions: options should cover the most commonly confused alternatives.

JSON FORMAT (strict):
{{
  "question": "Complete question text with all code/context included",
  "options": [
    {{"label": "A", "text": "...", "isCorrect": false}},
    {{"label": "B", "text": "...", "isCorrect": true}},
    {{"label": "C", "text": "...", "isCorrect": false}},
    {{"label": "D", "text": "...", "isCorrect": false}}
  ],
  "explanation": "Detailed explanation of WHY option B is correct and why A, C, D are wrong.",
  "difficulty": "{req['difficulty']}",
  "bloomLevel": "Apply"
}}
"""


def build_mcq_verifier_prompt(mcq: dict) -> str:
    return f"""
You are a STRICT exam quality validator and senior multi-domain technical specialist.

GOAL:
Ensure this MCQ is technically accurate, unambiguous, and suitable for a real
professional or university technical assessment.

VALIDATION RULES (MANDATORY):
1. There MUST be EXACTLY ONE correct option.
2. If more than one option is logically correct, modify so ONLY ONE remains correct.
3. Prefer the MOST DIRECT, UNAMBIGUOUS, and STANDARD solution.
4. All other options MUST be clearly incorrect.
5. The explanation MUST justify the correct option AND briefly note why others are wrong.
6. If code is present: verify the output step-by-step. Do NOT guess.
7. Remove ambiguity, edge cases, or trick interpretations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN-SPECIFIC VALIDATION RULES (ALL MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PYTHON:
- List slicing NEVER raises IndexError.
- [::-1] reverses entire sequence.
- is vs ==: is checks object identity, == checks value equality.
- Mutable default args persist across function calls.
- dict views (.items/.keys/.values) are NOT lists in Python 3.
- Chained comparisons like 1 < x < 10 are valid Python.

JAVASCRIPT / NODE.JS:
- var is function-scoped and hoisted (initialized as undefined).
- let/const are block-scoped; accessing before declaration → ReferenceError.
- typeof null === 'object' (historical quirk).
- == does type coercion; === does not.
- Arrow functions have no own `this` binding.
- Promises: microtasks run BEFORE macrotasks (setTimeout).
- async functions ALWAYS return a Promise.
- NaN !== NaN; use Number.isNaN() or Object.is(x, NaN).

REACT:
- useState setter is ASYNCHRONOUS within the same render.
- useEffect([]) fires on mount ONLY.
- useEffect() with no deps fires after EVERY render.
- Keys must be stable — avoid array index when list can reorder/delete.
- props are read-only; never mutate props directly.
- {{0 && <Comp/>}} renders 0 (falsy number), not nothing.
- useSWR/useQuery require the dynamic parameter (e.g. id) to be obtained FIRST via useRouter() or useParams() before constructing the URL. A snippet that uses id in useSWR without defining id first is BROKEN code and MUST be marked wrong.

NEXT.JS:
- /pages/ is a filesystem convention, NEVER part of a URL.
- pages/about.js → route /about (NOT /pages/about).
- pages/api/users.js → /api/users (NOT /pages/api/users).
- SSR (every request) = getServerSideProps ONLY (Pages Router only).
- SSG (build time) = getStaticProps ONLY (Pages Router only).
- ISR = getStaticProps + {{ revalidate: N }} (Pages Router only).
- getServerSideProps and getStaticProps are NEVER interchangeable.
- App Router: app/about/page.tsx → /about.
- App Router Client Component: requires 'use client' + useParams() from 'next/navigation'.
- App Router Server Component: async component, fetch directly with await, NO getServerSideProps.
- getServerSideProps / getStaticProps / getStaticPaths do NOT exist in App Router. EVER.

NEXT.JS ROUTER MIXING CHECK (MANDATORY — check BEFORE validating options):
- Read the directory structure shown in the question.
- If it shows app/ directory: ALL options must use App Router patterns only.
  - INVALID in App Router options: getServerSideProps, getStaticProps, getStaticPaths.
  - VALID in App Router options: 'use client', useParams(), async Server Component, fetch().
- If it shows pages/ directory: ALL options must use Pages Router patterns only.
  - INVALID in Pages Router options: useParams() from 'next/navigation', Server Components.
  - VALID in Pages Router options: getServerSideProps, getStaticProps, useRouter().query.
- If ANY option mixes routers (e.g. app/ structure + getServerSideProps): mark that option WRONG.
- If ALL options mix routers (no option is correct for the shown directory): return rejected JSON.
- If the question itself mixes routers (app/ structure + getServerSideProps in the question text):
  fix the question to use a consistent router before validating options.

SQL:
- JOIN without ON = CROSS JOIN (cartesian product).
- WHERE filters BEFORE GROUP BY; HAVING filters AFTER.
- GROUP BY must include all non-aggregated SELECT columns.
- NULL: use IS NULL / IS NOT NULL, never = NULL.
- COUNT(*) includes NULLs; COUNT(col) excludes NULLs.
- TRUNCATE is DDL (cannot be rolled back in most RDBMS); DELETE is DML.

TYPESCRIPT:
- any disables type checking; unknown forces checking before use.
- const enum values are inlined; regular enum creates a runtime object.
- Type assertions (as) perform NO runtime checks.
- never is return type of functions that never return.
- Nullish coalescing (??) triggers only on null/undefined, NOT on 0 or ''.

JAVA / OOP:
- Java passes object references by value.
- == compares references; .equals() compares content for objects.
- String literals are interned; new String("x") creates a new heap object.
- Integer cache only applies for values -128 to 127 (autoboxing).
- abstract class can have implementation; interface (pre-Java 8) cannot.
- super() must be FIRST statement in a constructor.

GIT:
- git rebase rewrites history; never rebase shared/public branches.
- git revert is safe for shared branches (creates new undo commit).
- git reset --hard is DESTRUCTIVE — cannot be undone for uncommitted changes.
- Detached HEAD: commits can be lost if you switch branches without saving.
- git pull = fetch + merge (or rebase with --rebase).

DOCKER / KUBERNETES:
- CMD sets default; ENTRYPOINT sets fixed executable.
- ARG is build-time only; ENV persists to runtime.
- ConfigMap = non-sensitive config; Secret = sensitive (base64, NOT encrypted).
- Liveness probe restart container; Readiness probe removes from service endpoint.
- Docker images are immutable; containers are running instances.

REST / HTTP:
- GET is idempotent and safe; POST is neither.
- PUT replaces entire resource; PATCH applies partial update.
- 401 Unauthorized = not authenticated; 403 Forbidden = authenticated but no permission.
- JWT payload is base64 encoded, NOT encrypted — do NOT store secrets in payload.
- CORS preflight OPTIONS request is sent automatically by browser.

ALGORITHMS / DATA STRUCTURES:
- Binary search requires SORTED input.
- BFS uses queue (shortest path unweighted); DFS uses stack/recursion.
- Hash table: O(1) average, O(n) worst case lookup.
- Heap property: parent > children (max-heap) or parent < children (min-heap).
- Quicksort worst case O(n²); Mergesort always O(n log n) but O(n) space.
- In-order BST traversal gives sorted output.

CLOUD / AWS:
- IAM explicit Deny ALWAYS overrides Allow.
- Security Groups are stateful; NACLs are stateless.
- Lambda is stateless and ephemeral — no persistent local storage.
- S3 is object storage (not a filesystem); no true directories.
- EC2 = IaaS; Lambda = FaaS; ECS/EKS = CaaS.

SYSTEM DESIGN:
- CAP theorem: Consistency + Availability + Partition Tolerance — pick 2.
- Write-through: write to cache AND DB simultaneously.
- Write-back: write to cache first, DB lazily (risk of data loss).
- Load balancer distributes traffic; does NOT cache (CDN caches).
- Consistent hashing minimizes reshuffling when cluster nodes change.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPT COMPLETENESS CHECK (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before validating, ask: "Does any option contain the TRUE correct concept?"

- If YES → proceed with normal validation.
- If NO → do NOT attempt to fix. Return EXACTLY this JSON:
  {{
    "rejected": true,
    "rejection_reason": "missing_correct_concept",
    "question": "<original question>",
    "options": <original options>,
    "explanation": "The correct concept is absent from all options. MCQ must be regenerated.",
    "difficulty": "<original difficulty>",
    "bloomLevel": "<original bloomLevel>"
  }}

Examples requiring rejection:
- SSR question but getServerSideProps absent → reject.
- React side-effects question but useEffect absent → reject.
- SQL aggregation but GROUP BY absent → reject.
- JWT question but base64/signature absent → reject.
- Next.js routing but [param] dynamic syntax absent → reject.
- Git undo question but git revert absent → reject.
- Next.js App Router question (app/ directory shown) but ALL options use getServerSideProps/getStaticProps → reject (wrong router in all options).
- Next.js client-side fetch in App Router but no option uses useParams() + useEffect/'use client' → reject.

DO NOT try to patch an MCQ when the correct concept is entirely missing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IF ISSUES EXIST (correct concept IS present):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Fix the question, options, and explanation.
- Preserve difficulty level.
- Return ONLY valid JSON — no markdown, no extra text.

MCQ TO VALIDATE:
{json.dumps(mcq, indent=2)}
"""


# ============================================================================
# verify_mcq_with_llm
# FIX 1: Now checks for {"rejected": true} returned by verifier when correct
#         concept is missing. Previously this was silently ignored, causing
#         deterministic validation to receive a rejected MCQ dict without
#         ever triggering a proper retry.
# ============================================================================


