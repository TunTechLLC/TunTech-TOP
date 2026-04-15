# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Technical Debt — Address Before Next Major Feature

### Build Sequence — Verified 2026-04-15

Full code investigation confirmed this order. Work top to bottom within this section.

| # | Item | Sessions |
|---|------|----------|
| 1 | Executive Briefing Sharpness + Execution Path Section | 1 |
| 2 | Narrator Quality Improvements — Session 1 (Improvements 1–6, 12, 13) | 1 |
| 3 | Narrator Quality Improvements — Session 2 (Improvements 7–11, 14) | 1 |
| 4 | Quick Wins Section | 1 |
| 5 | Domain Maturity Scoring | 1 |
| 6 | Visual 3 — Causal Chain | 1 |
| 7 | Three Systemic Drivers Section | 1 |
| 8 | Auto-Suggest Knowledge | 1 |
| 9 | Standardize Economic Output | 1 |
| 10 | Structured File Metadata Capture | 1 |
| 11 | Editable Engagement Info | 1 |
| 12 | PowerPoint Export | 1 |
| — | Checkpoint 5 — Dry Run 5 | milestone |

---

### Domain Maturity Scoring
**Problem:** Section 3 (Operational Maturity Overview) shows signal counts by domain but
no maturity score. Clients respond to scorecards in a way they don't respond to tables.

**Design:**
- Compute a 1–5 maturity score per domain at report generation time from existing data:
  - Pattern count (more patterns = more problems = lower score)
  - Average pattern confidence (High-confidence patterns weight more heavily)
  - Finding severity (High-priority findings pull score down)
- Domains with zero signals AND zero patterns show "No data" — a score of 5 would be
  misleading since it could mean genuinely healthy or simply unexamined
- Show as a scorecard table in Section 3 alongside the existing signal count table
- No new database columns — computed entirely at report time
- Future value: as TOP accumulates data across engagements, scoring becomes benchmarked

**Scoring formula (starting point — refine after first use):**
- Base score: 5
- Subtract 0.5 per accepted High-confidence pattern in the domain
- Subtract 0.25 per accepted Medium-confidence pattern
- Subtract 0.5 per High-priority finding in the domain
- Floor at 1; show "No data" if zero signals and zero patterns

**File:** `api/services/report_generator.py` — add `_compute_domain_scores(engagement_id)`

**Commit message:** Domain maturity scoring — 1–5 score per domain in Section 3

---
### Executive Briefing Sharpness + Execution 
Path Section

**Problem:** Two related issues identified 
from external feedback:

1. The Executive Briefing reads like analysis 
   rather than landing like a punch. Sentences 
   are long and dense. Key insights are buried 
   inside paragraphs rather than standing alone. 
   A CEO reading this page in 5 minutes should 
   feel the weight of the problem immediately.

2. The document has no clear answer to 
   "then what?" — after reading the roadmap, 
   the client does not know how implementation 
   gets done or what role the consultant plays 
   going forward. This is a conversion gap, 
   not just a document gap.

**Fix 1 — Executive Briefing prose style**

Update REPORT_NARRATOR_PROMPT instruction 
for the executive_briefing opening paragraph:

"Write the opening paragraph in short 
declarative sentences. Each sentence is 
one idea. No sentence should exceed 20 words. 
Do not embed the key insight inside a clause — 
pull it out as its own sentence. The reader 
should feel the weight of the problem after 
three sentences, not after three paragraphs.

Wrong style:
'Northstar's margin problem is not a PM 
execution problem — it is a pricing and 
governance problem: gross margin has compressed 
from 40% to 31% over four years because the 
CEO retains unilateral authority over pricing, 
SOW execution, and change order acceptance 
with no governance gates, and that authority 
has been used in ways that lock in losses 
before delivery begins.'

Right style:
'Northstar's margin problem is not a PM 
execution problem. It is a pricing and 
governance problem. Gross margin has fallen 
from 40% to 31% in four years. The cause is 
not delivery failure — it is a decision 
structure that locks in losses before delivery 
begins.'"

This is a REPORT_NARRATOR_PROMPT change only.
No report_generator.py changes needed.

**Fix 2 — How This Gets Implemented section**

Add a new subsection to Section 11 
(What Happens Next) titled 
"How This Gets Implemented."

The Narrator generates this section from 
engagement data. It should produce three 
short paragraphs covering:

Path 1 — Internal Execution
If the firm has sufficient internal capacity 
and leadership bandwidth, the roadmap can 
be executed internally. The Priority Zero 
actions require leadership decisions only. 
The Stabilize phase requires process design 
and governance changes that internal leaders 
can own with clear accountability.

Path 2 — Guided Execution (recommended 
for most firms at this stage)
A structured advisory engagement where the 
consultant provides weekly or biweekly 
leadership alignment, roadmap sequencing, 
and accountability review. The client executes. 
The consultant ensures the work gets done 
correctly and in the right order. This is 
the recommended model for firms without 
a dedicated transformation function.

Path 3 — Partner-Supported Execution
For firms that lack both internal capacity 
and a structured advisory relationship, 
specific initiatives can be staffed through 
fractional resources — fractional PMO, 
contractor PMs, finance operations support. 
The consultant architects the solution and 
directs the resources.

The Narrator should select which path to 
recommend based on firm size and the 
capacity signals observed in the engagement 
data. Firms under 60 people with no dedicated 
operations function should default to 
recommending Path 2.

**Implementation:**
- New Narrator JSON field: 
  execution_path_recommendation — 
  one of "internal" | "guided" | "partner"
- New REPORT_NARRATOR_PROMPT instruction 
  to generate the execution path narrative
- New subsection in report_generator.py 
  within Section 11, rendered after the 
  existing What Happens Next content

**Trigger for recommendation logic 
in Narrator prompt:**
"Based on the firm's headcount, the 
presence or absence of a dedicated 
operations or transformation function, 
and the leadership bandwidth signals 
observed in this engagement, recommend 
one of three execution paths: internal, 
guided, or partner-supported. Most firms 
under 75 people without a dedicated 
transformation function should be 
recommended the guided execution path."

**Priority:** High — do before first 
paid client engagement. This directly 
addresses the conversion gap identified 
by an experienced IT consulting practitioner. 
The "then what?" question will be asked 
in every client meeting.

**Scope:**
- REPORT_NARRATOR_PROMPT — two changes 
  (executive briefing style, execution 
  path recommendation)
- report_generator.py — one new subsection 
  in Section 11
- No schema changes
- No frontend changes

**Do in a single focused session.**
**Commit message:** "Narrator — sharper 
Executive Briefing prose style + 
How This Gets Implemented section 
in What Happens Next"

---

### DEFAULT_DOMAIN Constant — Centralize Hardcoded Domain Fallback

**Do not build as a standalone session. Split across Signal Library Sessions 1 and 2:**
- **Session 1:** Add `DEFAULT_DOMAIN = 'Delivery Operations'` to `api/utils/domains.py` and
  `src/constants.js`. Replace the 7 hardcoded fallback strings in backend and frontend files.
- **Session 2:** Fix domain list injection in all extraction prompts — the domain lists in all
  6 prompts in `document_processor.py` are hardcoded literal strings, not injected from
  `VALID_DOMAINS`. Signal Library Session 2 rewrites all extraction prompts anyway — fix
  the injection at that point. Touching these prompts twice is wrong.

**Problem:** The string `'Delivery Operations'` is hardcoded as a fallback default in 3 backend
files and 4 frontend components. If the default ever changes it must be updated in 7 places.

**Backend — add to `api/utils/domains.py`:**
```python
DEFAULT_DOMAIN = 'Delivery Operations'
```
Replace hardcoded strings in:
- `api/services/document_processor.py` — invalid domain fallback in `process_file()`
- `api/routers/findings.py` — invalid domain fallback in parse-synthesizer
- `api/routers/roadmap.py` — invalid domain fallback in parse-synthesizer

**Frontend — add to `src/constants.js`:**
```javascript
export const DEFAULT_DOMAIN = 'Delivery Operations'
```
Replace hardcoded strings in:
- `SignalPanel.jsx` — `EMPTY_FORM` default + inline candidate card fallback
- `FindingsPanel.jsx` — `EMPTY_FORM` default + inline candidate card fallback
- `RoadmapPanel.jsx` — `EMPTY_FORM` default + two inline candidate card fallbacks

**Also flag:** Domain lists are hardcoded in all extraction prompts in `document_processor.py`
and `claude.py` instead of being injected from `VALID_DOMAINS`. This is the same violation
at a larger scale — domain added to `domains.py` without updating prompt strings would be
silently ignored by Claude. Consider dynamic prompt injection in the same session.

**Commit message:** Centralize DEFAULT_DOMAIN constant — remove hardcoded domain fallbacks

---

### Visual Generator Layer — Status

| Visual | Description | Status |
|--------|-------------|--------|
| Visual 3 — Causal Chain Diagram | Left-to-right SVG flow showing how upstream failures produce downstream consequences. Nodes are finding titles, arrows show causal relationships from Root Cause Analysis. Embedded in Section 5. | Not built — pending |

**Visual 3 design:**
- New `causal_chain` JSON field in narrator output — finding-to-finding relationships for diagram node construction
- Generated as a temporary SVG, embedded via python-docx add_picture(), then deleted
- If generation fails, report generates without the visual and logs a warning

**Commit message:** Visual 3 — causal chain diagram in Section 5

---

### Quick Wins Section in the Report
**Problem:** The report surfaces all roadmap items in three phase tables but does not
call out which items the client can act on immediately. Executives leave the presentation
wanting something concrete to do next week — the report should give them that explicitly.

**Note:** Section Priority Zero Actions and Section Immediate Next Steps now
address the most urgent items from the Synthesizer output. Quick Wins as defined here —
a filtered table of priority=High AND effort=Low roadmap items — is still distinct and
worth adding, but is lower priority than before given the new sections.

**Design:** Add a "Quick Wins" subsection in Section 8 between the Roadmap Overview (8.2)
and the phase tables (8.3). Filter roadmap items where priority=High AND effort=Low.
Display as a short highlighted table — title, domain, and one-line description. Cap at 5 items.

If no items meet the criteria, omit the section entirely — do not show an empty table.

**Implementation:** Pure report generation logic in `api/services/report_generator.py`.
No schema changes. No frontend changes. No new endpoints.

**Commit message:** Quick wins section in report — high priority, low effort roadmap items

---

### Editable Engagement Info
Need to be able to edit engagement information after initial entry — should not require
DB Browser to update firm name, stated problem, hypothesis, etc. Items such as stated problem,
hypothesis, etc. should show on the screen after the initial save. It can be in
a collapsed section like settings is so it doesn't take up a lot of the screen.

**Priority: High — needed before first paid client engagement.** Engagement data will need correction mid-engagement (revised hypothesis, corrected firm name, etc.) and DB Browser is not a viable workaround in a live setting.

---

### Auto-Suggest Knowledge Promotions
**Problem:** Knowledge promotions are the only panel that remains fully manual.
Every other panel (Signals, Patterns, Findings, Roadmap) follows the detect-review-load
pattern. Knowledge should too. Also, existing knowledge promotions have no Edit or Delete.

**Design — Suggest flow (mirrors Findings parse pattern):**
- "Suggest Knowledge" button in KnowledgePanel — show after Synthesizer is accepted
- Calls Claude with KNOWLEDGE_EXTRACTION_PROMPT
- Claude receives: full Synthesizer output + all accepted findings + engagement context
- Returns 3–5 reusable insights as reviewable cards — observations useful across future
  engagements, not specific to this one
- Each card is editable before saving (inline text edit on the card)
- Accept / Reject per card
- "Load Approved" saves accepted items via existing knowledge create endpoint
- On success: clear candidates, refresh knowledge list

**Design — Edit/Delete on existing promotions:**
- Edit button per row — inline edit form (same fields as the Add form)
- Delete button with confirmation prompt
- New endpoint needed: `DELETE /{engagement_id}/knowledge/{knowledge_id}`
- Check whether `PATCH /{engagement_id}/knowledge/{knowledge_id}` exists — add if not

**New prompt:** `KNOWLEDGE_EXTRACTION_PROMPT` in `api/services/claude.py`
**New endpoints:**
- `POST /{engagement_id}/knowledge/suggest`
- `DELETE /{engagement_id}/knowledge/{knowledge_id}`
- `PATCH /{engagement_id}/knowledge/{knowledge_id}` (if not already present)

**Commit message:** Knowledge panel — suggest-review-load + edit/delete on existing promotions

---
### Narrator and Agent Quality Improvements
— Sequencing, Prioritization, and 
Economic Integrity

**Priority: High — affects output quality 
across all future engagements**

**Scope:** Prompt changes only — 
REPORT_NARRATOR_PROMPT, SKEPTIC_PROMPT, 
SYNTHESIZER_PROMPT in claude.py. 
No schema changes. No report_generator 
changes. No frontend changes.

**Do in a single focused session.**

**Commit message:** "Narrator and agent 
prompt improvements — sequencing rules, 
prioritization logic, economic overlap 
handling, risk mitigation triggers, 
leading indicators in success metrics"

---

#### Improvement 1 — Revenue concentration 
risk belongs in Stabilize not Scale

When a finding identifies a single client 
representing more than 15% of revenue 
with any of the following signals present 
— declining NPS, active escalation, 
relationship deterioration, no account 
plan — the account stabilization action 
must be placed in Stabilize, not Scale.

Revenue concentration with deteriorating 
relationship signals is a risk containment 
action, not a growth initiative. Placing 
it in Scale treats a Stabilize problem 
as an optimization opportunity and 
leaves the firm's largest revenue 
exposure unmanaged for 6-9 months.

Add to REPORT_NARRATOR_PROMPT:
"When the Revenue Concentration Risk 
pattern has fired AND relationship 
deterioration signals are present for 
the concentrated client (declining NPS, 
active escalation, no account plan, 
or client communication gaps), the 
account stabilization initiative must 
be placed in Stabilize. Only account 
expansion initiatives belong in Scale. 
Stabilization and expansion are 
different actions with different urgency."

---

#### Improvement 2 — Active rate loss 
requires Stabilize policy, not just 
Optimize reporting

When rate card non-enforcement is 
identified as an ongoing active loss 
(the gap between realized rate and 
target rate is confirmed and persisting), 
the rate floor policy and approval 
workflow must be drafted in Stabilize 
and ratified in early Optimize. 
The reporting infrastructure that 
enforces the policy belongs in Optimize, 
but the policy itself does not require 
the reporting to exist before it can 
be written.

Waiting for Optimize to begin rate 
governance means every new deal signed 
during Stabilize continues at the 
below-target rate, compounding the 
confirmed annual loss for 3+ months.

Add to REPORT_NARRATOR_PROMPT:
"When billable rate realization is 
below target and rate card non-enforcement 
is identified as an active ongoing loss, 
the roadmap must include a rate floor 
policy and approval workflow draft in 
Stabilize (not Optimize). Deal-level 
rate reporting infrastructure belongs 
in Optimize. The policy does not require 
the reporting infrastructure to exist 
before it can be drafted and communicated."

---

#### Improvement 3 — Change order 
discipline must be portfolio-wide 
from Month 1

When the Weak Change Control pattern 
has fired, change order governance 
initiatives must apply to the entire 
active portfolio from Month 1. Scoping 
a change order freeze to specific 
at-risk projects leaves the remaining 
portfolio ungoverned and creates 
inconsistent enforcement that project 
managers will exploit.

Add to REPORT_NARRATOR_PROMPT:
"When change order discipline is 
identified as a finding, the change 
order governance initiative must be 
portfolio-wide from Month 1 of Stabilize. 
Do not scope it to specific at-risk 
projects — this creates two tiers of 
enforcement and the ungoverned projects 
will absorb scope without commercial 
capture. Portfolio-wide enforcement 
is the only effective implementation."

---

#### Improvement 4 — Confirmed 
contractual AI liability is a 
Stabilize concern regardless of 
finding confidence level

When a finding documents confirmed 
contractual exposure from ungoverned 
AI tool use on active client engagements 
(no AI usage policy, no SOW AI clause, 
confirmed tool use on client work), 
the AI governance initiative must be 
prioritized as High and placed in 
Stabilize regardless of the finding's 
overall confidence level.

Contractual liability exists today on 
active engagements. It is not a future 
risk — it is a current condition. 
Medium confidence on the finding's 
broader AI readiness picture does not 
reduce the urgency of closing confirmed 
contractual gaps.

Add to REPORT_NARRATOR_PROMPT:
"When the AI Governance Absence pattern 
has fired AND confirmed AI tool use on 
client engagements is present without 
an AI usage policy or SOW AI clause, 
the AI governance policy initiative 
must be placed in Stabilize at High 
priority. The absence of a policy on 
active client engagements is a confirmed 
contractual liability today, not a 
future risk. AI service offering 
development belongs in Scale."

---

#### Improvement 5 — Dual PM departures 
or PM over-allocation require structural 
capacity model, not just hiring 
recommendation

When two or more simultaneous PM 
departures are identified, or when 
PM over-allocation is confirmed across 
three or more active projects, the 
roadmap must include a PM capacity 
model initiative in Stabilize or early 
Optimize. A hiring recommendation 
alone is insufficient — the structural 
condition that made the firm unable 
to absorb the departures must be 
addressed or the next departure 
produces the same crisis.

Add to REPORT_NARRATOR_PROMPT:
"When PM attrition events or chronic 
PM over-allocation are identified, 
the roadmap must include a structural 
PM capacity model initiative — a 
pipeline-to-PM-demand forecasting 
model with a defined bench reserve 
target — in addition to any hiring 
recommendation. A hiring recommendation 
without a capacity model solves the 
immediate gap but does not prevent 
recurrence. The capacity model belongs 
in Stabilize or early Optimize depending 
on the severity of the current gap."

---

#### Improvement 6 — CEO as bottleneck 
with multiple P0 ownership requires 
structural delegation mechanism in 
risk register

When the Leadership Bottleneck pattern 
has fired AND the CEO is assigned 
ownership of more than two P0 or 
Stabilize initiatives, the risk register 
must include a structural delegation 
mechanism as a required mitigation 
option — not just a tracking log or 
review cadence.

A tracking log fires after the failure. 
A structural delegation mechanism 
(written decision rights matrix, 
defined escalation thresholds below 
CEO, or external operating resource) 
changes the path of least resistance 
before the failure occurs.

Add to REPORT_NARRATOR_PROMPT:
"When the Leadership Bottleneck or 
Scaling Breakdown pattern has fired 
AND the CEO is identified as the owner 
of more than two Stabilize initiatives, 
the risk register entry for CEO 
reversion must include at least one 
structural delegation mechanism as 
a mitigation — a written decision 
rights matrix with defined thresholds, 
a fractional operating resource, or 
an explicit opt-out delegation model. 
A tracking log or review cadence alone 
is not a mitigation for a bottleneck 
risk rated High likelihood."

---

#### Improvement 7 — Scale-phase targets 
must name the mechanism or flag it 
as undefined

When a Scale-phase initiative projects 
a performance improvement of more than 
20% over current confirmed baseline 
(e.g. deal size, revenue per consultant, 
gross margin), the roadmap must either 
name the specific mechanism that drives 
the improvement or explicitly state 
that the mechanism requires definition 
during the Optimize phase.

A target without a mechanism is 
aspirational, not defensible. A CFO 
or board reviewer will immediately 
challenge an 18-month target that 
has no bridge math.

Add to REPORT_NARRATOR_PROMPT:
"When a Scale-phase initiative projects 
a target that represents more than 20% 
improvement over the current confirmed 
baseline for that metric, the initiative 
description must name the specific 
mechanism driving the improvement 
(new segment, new sales motion, pricing 
change, etc.) or explicitly state: 
'Mechanism to be defined during Optimize 
phase based on [specific prerequisite].' 
Do not generate improvement targets 
without either a named mechanism or 
an explicit acknowledgment that the 
mechanism is undefined."

---

#### Improvement 8 — Utilization recovery 
requires demand conversion plan 
acknowledgment

When a utilization improvement target 
is included in the roadmap, the 
initiative description must acknowledge 
that utilization recovery creates 
new billable capacity that requires 
a demand conversion plan. Capacity 
without demand produces bench cost, 
not revenue.

Add to REPORT_NARRATOR_PROMPT:
"When a utilization improvement 
initiative is included in the roadmap, 
the initiative description must include 
a note that utilization recovery creates 
additional billable capacity that requires 
a corresponding demand conversion plan. 
Reference the pipeline and account 
management initiatives as the demand 
side of the utilization recovery. 
Do not present utilization improvement 
as a standalone margin lever without 
acknowledging the demand requirement."

---

#### Improvement 9 — Success metrics 
include leading indicators

Each roadmap initiative success metric 
must include a leading indicator 
alongside the binary completion 
criterion. A binary completion criterion 
alone gives no signal of whether an 
initiative is on track before it is 
done.

Add to REPORT_NARRATOR_PROMPT:
"Each initiative success_metric must 
include two components:
1. A leading indicator — an observable 
   measurable signal that the initiative 
   is progressing correctly before 
   completion
2. A completion criterion — the binary 
   condition that defines done

Format: '[Leading indicator] → 
[Completion criterion]'

Example wrong: 'System lockout for 
weekly time entry is active'

Example right: 'Time entry compliance 
rate above 90% in week one → System 
lockout active and all billable 
consultants submitting weekly for 
two consecutive weeks'"

---

#### Improvement 10 — Risk mitigations 
include trigger conditions

Each risk register mitigation must 
specify the observable trigger condition 
that activates it. A mitigation without 
a trigger is advice, not an operational 
plan. It fires reactively at best and 
is ignored at worst.

Add to REPORT_NARRATOR_PROMPT:
"Each risk mitigation must follow this 
format: 'If [specific observable trigger 
condition or threshold], then [mitigation 
action].'

The trigger must be specific and 
observable — not 'if the risk occurs' 
but 'if [measurable threshold or 
observable event].'

Example wrong: 'Complete legal MSA 
review before the client call'

Example right: 'If MSA review surfaces 
financial remedy obligations or liability 
clauses that exceed confirmed project 
losses, engage outside counsel before 
the client call and prepare a written 
position on maximum exposure before 
any financial remedy discussion occurs.'"

---

#### Improvement 11 — Skeptic flags 
economic overlap, Synthesizer uses 
adjusted figures

When the Skeptic identifies overlapping 
economic inputs across findings (the 
same underlying figure contributing 
to two separate finding exposures), 
the Synthesizer must use the adjusted 
combined exposure in executive summary 
prose and economic narrative — not the 
unadjusted sum of individual findings.

The overlap note in the economic table 
footnote is correct and should be 
preserved. The headline figures in the 
executive summary and economic narrative 
must reflect the adjusted figure.

Add to SKEPTIC_PROMPT:
"When you identify that two or more 
findings share an underlying economic 
input (the same project loss, the same 
revenue figure, or the same cost 
contributing to multiple finding 
exposures), output an explicit overlap 
flag in this format:

OVERLAP: [Finding A title] and 
[Finding B title] share [description 
of shared input]. Do not sum these 
independently. Adjusted combined 
exposure: [figure].

This flag must appear in your output 
whenever overlapping inputs exist, 
regardless of whether the findings 
are in the same domain."

Add to SYNTHESIZER_PROMPT:
"When the Skeptic output contains an 
OVERLAP flag, the executive summary 
economic narrative and all headline 
economic figures must use the adjusted 
combined exposure from the overlap 
flag, not the sum of the individual 
finding figures.

Acknowledge the overlap explicitly 
in the economic narrative prose:
'[Finding A] and [Finding B] share 
underlying exposure — the combined 
confirmed figure is [adjusted amount], 
not the sum of the individual findings.'

The economic table footnote behavior 
is unchanged — the overlap note there 
is correct and should be preserved."

### Improvement 12 — Active client 
escalation with financial exposure 
requires contingency planning, not 
just a single recommended action

**Problem:** When an active client 
escalation is present with confirmed 
financial exposure and no contractual 
protection (absent liquidated damages 
clause, incomplete SOW), the roadmap 
currently generates a single recommended 
action. A single-path plan for a live 
dispute with indeterminate legal and 
financial exposure is not operationally 
sound — if the recommended action fails 
or the client escalates further, the 
firm has no defined fallback.

This is a general rule that applies to 
any engagement with an active client 
crisis, not a Northstar-specific fix.

**Add to REPORT_NARRATOR_PROMPT:**
"When the Client Escalations pattern 
has fired AND confirmed financial 
exposure exists on the escalated 
engagement AND the SOW lacks contractual 
protection (no liquidated damages clause, 
missing client obligation enforcement 
language, or below-rate pricing with 
no floor), the roadmap Priority Zero 
action for that escalation must include 
three components:

1. Primary path — the recommended 
   immediate action (e.g. legal MSA 
   review, revised project plan delivery, 
   CEO-CTO call)

2. Contingency path — what to do if 
   the primary path fails or the client 
   escalates further (e.g. settlement 
   floor, reserve recognition threshold, 
   legal escalation criteria)

3. Exposure boundary — the maximum 
   confirmed financial exposure the 
   firm faces and the contractual basis 
   for that boundary (or explicit 
   acknowledgment that the boundary is 
   indeterminate without legal review)

Do not generate a single-bullet P0 
action for an active escalation with 
financial exposure. A live dispute 
requires a primary path, a fallback, 
and a known exposure boundary."

**Scope:** REPORT_NARRATOR_PROMPT only.
No schema changes. No report_generator 
changes.

**Priority:** High — a single-path 
plan for an active client crisis is 
a material gap in any engagement where 
this condition exists.

---

### Improvement 13 — Sequential 
initiative dependencies must be 
explicitly sequenced, not shown 
as concurrent

**Problem:** When two initiatives in 
the same phase have a sequential data 
dependency — Initiative B requires 
clean output from Initiative A before 
it can execute — the Narrator currently 
places them in the same phase with 
overlapping timelines. This produces 
logically impossible roadmaps where 
a process improvement initiative is 
deployed before the data infrastructure 
it depends on exists.

This is an architectural rule that 
applies to any engagement where 
reporting infrastructure and process 
improvement initiatives coexist in 
the same phase.

**Common patterns where this fires:**
- Estimation model deployment depends 
  on PSA or project tracking data 
  being clean and consistent
- Pricing governance enforcement 
  depends on deal-level rate reporting 
  existing
- PM performance management depends 
  on project-level margin visibility 
  existing
- Capacity forecasting depends on 
  utilization tracking being reliable

**Add to REPORT_NARRATOR_PROMPT:**
"Before finalizing initiative timelines 
within each phase, check for sequential 
data dependencies: does any initiative 
require clean, reliable data that 
another initiative in the same phase 
is responsible for producing?

If yes, the dependent initiative must 
be placed later in the phase timeline 
or moved to the next phase. Show the 
dependency explicitly in the initiative 
description:

'Prerequisite: [Initiative A] must 
be producing reliable [data type] 
before this initiative can execute. 
Realistic start: [month].'

Specific rule: any initiative that 
deploys a model, framework, or process 
that calibrates against historical 
actuals requires that the actuals 
dataset exists in usable form today 
or that the infrastructure producing 
it is fully operational before the 
model deployment begins. Do not show 
these as concurrent."

**Scope:** REPORT_NARRATOR_PROMPT only.
No schema changes. No report_generator 
changes.

**Priority:** High — logically impossible 
concurrent timelines undermine the 
roadmap's credibility with any 
operationally experienced reviewer 
and will surface in the first progress 
review when the dependent initiative 
cannot start.

---

### Improvement 14 — Utilization 
recovery with concurrent hiring or 
capacity initiatives requires a 
scenario note defining decision 
criteria for new capacity

**Problem:** When utilization improvement 
and capacity-related initiatives 
(hiring plan, PM bench reserve, 
contractor bench) coexist in the 
roadmap, the document currently treats 
them as independent levers. They are 
not — utilization recovery creates 
new billable capacity that must either 
be converted to revenue or actively 
managed as bench. If pipeline does not 
convert at the rate assumed, the firm 
accumulates bench cost while also 
spending on hiring.

Improvement 8 already requires 
acknowledging the demand conversion 
requirement. This improvement adds 
the scenario planning layer: what 
are the decision criteria that 
determine whether the new capacity 
is held as bench, converted to revenue, 
or triggers a hiring plan adjustment?

**Add to REPORT_NARRATOR_PROMPT:**
"When the roadmap contains both a 
utilization improvement initiative 
AND a hiring or PM capacity initiative 
in overlapping phases, include a 
scenario note in the roadmap overview 
section addressing the capacity 
decision tree:

'Utilization recovery and hiring 
investment are concurrent in this 
roadmap. The following criteria 
determine how new billable capacity 
is managed:

- If pipeline conversion produces 
  demand within [timeframe]: deploy 
  new capacity to revenue-generating 
  work and proceed with hiring plan

- If pipeline conversion does not 
  materialize within [timeframe]: 
  pause hiring plan and hold 
  utilization recovery gains as 
  bench buffer pending demand 
  confirmation

- Decision owner: [CEO / Director 
  of Delivery] reviews at [cadence]'

Use confirmed pipeline coverage ratio 
and revenue predictability signals 
from the engagement to set realistic 
timeframes. Do not leave utilization 
recovery and hiring as independent 
levers with no defined interaction 
logic."

**Scope:** REPORT_NARRATOR_PROMPT only.
No schema changes. No report_generator 
changes.

**Priority:** Medium — most firms at 
this scale are managing both capacity 
and demand simultaneously. Without 
a decision tree, the roadmap implicitly 
assumes both succeed, which is 
optimistic and will be challenged 
by any financially sophisticated 
reviewer.

---

### Implementation note for all 
14 Narrator improvements

When Claude Code implements these 
14 prompt additions, organize them 
in REPORT_NARRATOR_PROMPT as a 
named section:

"## Roadmap Quality Rules

The following rules must be applied 
when generating roadmap content. 
Check each rule against the engagement 
data before finalizing roadmap output."

Then list the rules in logical groups:
- Sequencing rules (1, 2, 3, 4, 5, 
  6, 12)
- Dependency and timing rules (13)
- Target and mechanism rules (7, 8, 
  14)
- Output structure rules (9, 10)
- Economic integrity rules (11)

This prevents the prompt from becoming 
an undifferentiated wall of instructions 
that Claude cannot reliably reason over. 
Named sections with logical grouping 
improve prompt reliability significantly 
at this instruction count.

Do not implement all 14 in one session. 
Split into two sessions:

Session 1 — Sequencing and dependency 
rules (Improvements 1-6, 12, 13): 
these are the highest priority and 
most structurally important

Session 2 — Target, output structure, 
and economic integrity rules 
(Improvements 7-11, 14): these 
improve quality but are less likely 
to produce logically incorrect roadmaps

---

### PowerPoint Export
**Problem:** Every engagement requires a PowerPoint presentation to the client. Victor
currently builds this manually from the Word document — typically after the roadmap is
finalized and before the client meeting. This is significant manual work per engagement
and creates a risk that the deck and the Word doc drift apart if the roadmap is updated
after the presentation.

**Design:** Generate a starting-point PPTX from the same data that drives the Word report.
Use a PowerPoint template named presentation_template.pptx that resides in the assets folder,
which is the same folder where the Word template resides.
Victor tweaks it to presentation quality before the client meeting — same expectation as
the Word document. The goal is to eliminate the blank-slide starting point, not the
consultant's judgment.

**Suggested slide structure:**
1. Title slide
2. Agenda
3. Transformation Process Review
4. Situation and client hypothesis vs. diagnostic reality
5. Domain maturity scorecard
6. Key findings by domain (one slide per domain)
7. Economic stakes summary
8. Transformation roadmap — Stabilize phase
9. Transformation roadmap — Optimize phase
10. Transformation roadmap — Scale phase
11. Quick wins — immediate actions

**Implementation:**
- New function `generate_pptx(engagement_id)` in `api/services/report_generator.py`
- Uses python-pptx library — check if already in requirements.txt, add if not
- New endpoint `POST /{engagement_id}/report/generate-pptx` — saves file alongside the
  Word doc in reports_folder, returns `{"saved_to": "C:\\...\\OPD_Roadmap_E004.pptx"}`
- New button in ReportPanel.jsx — "Generate Presentation" alongside Generate Report
- Content pulled from same data as Word report — no new data sources needed

**Build after:** Domain Maturity Scoring — the scorecard slide requires maturity scores
to be computed. Build maturity scoring first, then PowerPoint.

**Commit message:** PowerPoint export — generate starting-point presentation from roadmap data

---

### Standardize Economic Output Generation
For each economic formula type in the pattern library, define inputs, assumptions,
default values, acceptable ranges, and range logic (point estimate vs range).

**Example — Delivery Overrun Loss:**
```
Inputs: Overrun Hours (estimated or confirmed), Cost Rate (confirmed or estimated)
Assumptions: Overrun % range 10%–25% if not explicitly measured
Range Logic: Low = 10% scenario, High = 25% scenario
```

**Build after:** Economic Breakdown Chart structured fields work (Sessions A–C) — finding economic data must be clean and in structured fields before standardizing the formulas that produce it.

---

### Structured File Metadata Capture at Processing Time

**Problem:** The Engagement Overview section of the OPD report derives interview roles and
document types by parsing filenames using a naming convention. This is fragile — it depends
on the consultant following the convention precisely, fails silently when files are named
differently, and produces generic fallback labels when parsing fails. The short-term
workaround is a documented filename convention (see CLAUDE.md). The correct solution is
capturing role and document subtype as structured fields at the moment a file is processed.

**Design:**
When a consultant processes a file in the Signal Panel, add two optional fields to the
processing UI:

For interview files:
- "Interviewee Role" — free text or dropdown
  Examples: CEO, Director of Delivery, VP Sales, Finance Lead, Senior Consultant,
  Operations Lead
  Stored as: `interview_role TEXT` in ProcessedFiles

For document files:
- "Document Type" — dropdown
  Options: Financial Summary, Portfolio Report, SOW, Project Status Report,
  Client Feedback, Other (free text)
  Stored as: `document_subtype TEXT` in ProcessedFiles

**Database change:**
```sql
ALTER TABLE ProcessedFiles ADD COLUMN interview_role TEXT;
ALTER TABLE ProcessedFiles ADD COLUMN document_subtype TEXT;
```
Both columns are nullable — existing records are unaffected. The filename convention
parsing remains as a fallback when these fields are null.

**Frontend change:**
In `SignalPanel.jsx`, add the appropriate field to the file processing form based on
the selected `file_type`:
- If `file_type` is `"interview"`: show "Interviewee Role" text input (optional,
  placeholder: e.g. "CEO")
- If `file_type` is one of `financial`/`sow`/`status`/`document`: show "Document Type"
  dropdown (optional)

**Backend change:**
In `signals.py` router, accept `interview_role` and `document_subtype` as optional fields
in the process-files request and store them in ProcessedFiles.

**Narrator input change:**
In `generate_report_narrative()`, prefer the structured `interview_role` and
`document_subtype` fields from ProcessedFiles over the filename convention parsing
when they are populated. Fall back to filename parsing when they are null.

**Priority:** Medium — the filename convention is a working workaround. Build this after
the Report Narrator is fully validated and before the first paid client engagement.

**Commit scope:**
ProcessedFiles migration, `signals.py` router update, `SignalPanel.jsx` form addition,
`generate_report_narrative()` input assembly update

---
### Three Systemic Drivers Section

**Problem:** The document presents findings across 
9 domains and 16 roadmap items but never explicitly 
names the 2-3 upstream structural conditions that 
most findings trace back to. A CEO reading the 
document absorbs detail but may not walk away with 
a crisp mental model of what is actually wrong at 
the structural level.

**Design:** A new section between Executive Summary 
and How to Read This Document. Half a page maximum. 
Each driver gets a bold 3-5 word name and one 
sentence explanation. No finding cross-references 
in this section — the domain analysis carries that 
detail.

**Implementation:**
- New Narrator JSON field: systemic_drivers array 
  with driver_name (3-5 words) and 
  driver_explanation (one sentence) per driver
- New REPORT_NARRATOR_PROMPT instruction: 
  "Identify 2-3 systemic drivers — the upstream 
  structural conditions that are the root cause 
  of the majority of findings. A driver is not 
  a finding; it is the condition that produces 
  multiple findings. Every accepted finding should 
  be traceable to at least one driver."
- New section in report_generator.py between 
  Executive Summary and How to Read This Document
- Section map already dynamic — section numbers 
  update automatically

**Priority:** Low — build after causal chain 
diagram. May be redundant once the causal chain 
diagram visually shows the same relationships.

**Build after:** Causal chain diagram is complete.
---

## Checkpoint 5 — Dry Run 5 (Full Feature Validation)

**Goal:** End-to-end run with a new fictional client validating all post-Checkpoint 4
features: key quotes, roadmap capabilities, economic linkage, dependency mapping, and
domain maturity scoring.

**Pre-run setup:**
- New fictional client with 3–4 interview transcripts and 1–2 supporting documents
- Transcripts should use named fictional roles (CEO, Director of Delivery, etc.) so
  key quotes are attributable in the report

**Pass criteria:**
- Every finding has a plain English evidence summary (no P-codes) and 2–3 key quotes in the report
- Every roadmap item has a capability statement in the report
- Economic impact context appears under roadmap items and as a phase-level narrative
- At least one roadmap item has dependencies set — prerequisites appear in report
- Quick wins section appears in Section 8 (if qualifying items exist)
- Domain maturity scorecard appears in Section 3 — "No data" shown for unexamined domains
- PowerPoint generated without errors — opens correctly with all slides populated
- All Checkpoint 4 pass criteria still met

---

## Phase 3 Items

### Background Task Processing for Document Files
Current `process-files` endpoint runs synchronously — for long transcripts or many files
this could approach timeout limits. For Phase 2 dry runs, synchronous is acceptable.
**Phase 3 design:** Background task with job table, polling endpoint, and status tracking.
Workaround: split large transcripts into two files.

### PostgreSQL Migration
Only two changes needed when the time comes:
1. `BaseRepository._get_connection()` — swap `sqlite3` for `psycopg2`, update connection string
2. Parameter placeholders — `?` becomes `%s` throughout all SQL constants

Everything else — repositories, routers, services — is database-agnostic and unchanged.

### Agent Registry URL Cleanup
`GET /api/engagements/agents/registry` is registered under the engagements prefix but is
not engagement-specific. Cosmetic issue only.
**Phase 3 fix:** Move to `/api/agents/registry`. Update `api.js` and `AgentPanel.jsx`.

### Multi-user remote version
Multi-user remote version requires: 
auth/session management, engagement-level access controls, structured interview intake 
for non-consultant interviewers, finding source attribution for remote reviewers, 
PostgreSQL migration, hosted infrastructure. Prerequisite: solo version validated across 
minimum 3 engagements.

### AWS Hosting
- `_get_connection()` uses RDS connection string via `TOP_DB_PATH` env var
- File processing reads from S3 — `document_processor.py` gets S3 client
- `main.py` CORS origins updated to production domain
- Frontend built with `VITE_API_URL=https://top.tuntechllc.com/api`
No architectural changes required.

### Multi-User Auth
1. Add `users` table
2. Add `user_id` column to `Engagements` table
3. Add `WHERE user_id = ?` filter to all engagement queries
4. Add auth middleware (FastAPI + JWT or session)

### Custom Domain
`top.tuntechllc.com` — DNS record pointing to AWS load balancer.
No code changes — driven by `VITE_API_URL` build env var.

---

## Architectural Notes for Future Reference

- **Do not add SQLAlchemy** — clean SQL in repositories is the right pattern for this project.
  PostgreSQL migration only requires changing `_get_connection()` and `?` to `%s`.
- **Do not add global state** — all data must be scoped to `engagement_id`.
  Cross-engagement reporting queries across all engagements by design — that is intentional.
  Any new feature should be scoped to an engagement, not global.
