# TOP Signal Library
## TunTech Operations Platform — Operational Signal Framework
### Complete Reference: All 10 Domains, Two-Type Framework, Pattern Linkage

---

## Schema Reference

### SignalLibrary Table
```sql
CREATE TABLE SignalLibrary (
    signal_id        TEXT PRIMARY KEY,  -- e.g. SL-01
    signal_name      TEXT NOT NULL,
    domain           TEXT NOT NULL,
    signal_type      TEXT NOT NULL,     -- 'numeric' | 'maturity'
    definition       TEXT NOT NULL,     -- what this measures and why it matters diagnostically
    priority_tier    INTEGER NOT NULL DEFAULT 2,  -- 1 = primary diagnostic set, 2 = full coverage
    -- Numeric signals only:
    threshold_bands  TEXT,              -- JSON: [{min, max, label, description}] null=open bound
    -- Maturity signals only:
    maturity_levels  TEXT,              -- JSON: [{level, label, description}]
    none_indicators  TEXT,              -- behavioral cues that confirm None vs not_observed
    -- Pattern linkage:
    contributing_patterns TEXT,         -- JSON array of pattern_ids this signal feeds
    created_date     TEXT NOT NULL
);
```

### SignalCoverage Table (not-observed gaps only)
```sql
CREATE TABLE SignalCoverage (
    coverage_id    TEXT PRIMARY KEY,
    engagement_id  TEXT NOT NULL,
    signal_id      TEXT NOT NULL,   -- FK to SignalLibrary
    source_file    TEXT NOT NULL,
    created_date   TEXT NOT NULL
);
```

### Signals Table Addition
```sql
ALTER TABLE OPDSignals ADD COLUMN library_signal_id TEXT;
-- NULL for freely-extracted signals not in the library
-- FK to SignalLibrary.signal_id for library-matched signals
```

---

## Priority Tier Reference

**Tier 1 — Primary Diagnostic Set (24 signals)**
These signals drive the majority of diagnostic power and economic insight. They are reliably
extractable from interview transcripts and light document review, feed the most critical
patterns, and connect directly to revenue, margin, and delivery performance.

Tier 1 signals are checked on every relevant file type and form the core diagnostic layer
of TOP. When extraction capacity is limited, these signals are always prioritized.

These signals are intentionally constrained to minimize overlap and maximize clarity of
diagnostic output.

**Tier 2 — Full Coverage Set (52 signals)**
These signals provide diagnostic depth and coverage gap tracking. They are important for
completeness and cross-engagement analysis but are secondary to Tier 1 for pattern detection
and economic modeling. Tier 2 signals are checked when the domain is rich enough to warrant
full library coverage.

### Tier 1 Signals by Domain
| Domain | Tier 1 Signals |
|--------|---------------|
| Sales & Pipeline | SL-01, SL-05, SL-06 |
| Sales-to-Delivery Transition | SL-12, SL-13 |
| Delivery Operations | SL-17, SL-18, SL-19, SL-20, SL-23 |
| Resource Management | SL-25, SL-27, SL-28 |
| Project Governance / PMO | SL-32, SL-36 |
| Consulting Economics | SL-38, SL-39, SL-40, SL-41 |
| Customer Experience | SL-46 |
| AI Readiness | SL-52 |
| Human Resources | SL-58 |
| Finance and Commercial | SL-66 |

---

## Extraction Prompt Instructions

### For numeric signals
Claude reads a value from source material and reports:
1. The observed value (exact figure or range)
2. The threshold band it falls into (label from threshold_bands)
3. The source (who said it / which document)

### For maturity signals
Claude reads qualitative evidence and reports:
1. The maturity level (None / Informal / Defined / Managed / Optimized)
2. The behavioral evidence that supports that level
3. CRITICAL: Only assign None if none_indicators are present in the source. If the topic
   was not discussed, report not_observed. Do not infer None from silence.

### not_observed handling
When a library signal is checked against a source file and no evidence is found:
- Do not include it in the found signals output
- Include its signal_id in the not_observed array
- The router writes a SignalCoverage row for each not_observed signal_id

### Priority tier usage in extraction
- For all file types: always check all Tier 1 signals in the applicable domain slice
- For interview files (full library): check all Tier 1 + all Tier 2 signals
- For document files (domain-filtered): check all Tier 1 in applicable domains;
  check Tier 2 signals in applicable domains when source material is rich enough
  to warrant full coverage

---

## Domain Filter Map (for document-type extraction prompts)

| Document Type               | Domains to Include                                                                        |
|-----------------------------|-------------------------------------------------------------------------------------------|
| Financial summary           | Consulting Economics, Finance and Commercial                                              |
| Resource utilization report | Resource Management, Consulting Economics                                                 |
| Portfolio / project report  | Delivery Operations, Resource Management, Project Governance / PMO, Sales-to-Delivery Transition |
| Delivery document           | Delivery Operations, Project Governance / PMO, Sales-to-Delivery Transition, Resource Management |
| SOW / contract              | Sales-to-Delivery Transition, Finance and Commercial                                      |
| Status report               | Delivery Operations, Project Governance / PMO                                             |
| Client feedback / NPS       | Customer Experience                                                                       |
| Interview (all roles)       | All 10 domains                                                                            |

---

## Domain 1: Sales & Pipeline

*Signals in this domain measure the health and predictability of the revenue pipeline.
Weak pipeline signals are the leading indicator of revenue instability that appears in
Consulting Economics signals 1-2 quarters later.*

---

### SL-01 — Pipeline Coverage Ratio
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Total weighted pipeline value divided by quarterly revenue target. Measures
  whether the firm has enough opportunity volume to reliably make its revenue number.
- **Threshold Bands:**
  - `{min: null, max: 2.0, label: "Critical", description: "Revenue target is at serious risk. Immediate pipeline build required."}`
  - `{min: 2.0, max: 3.0, label: "Below Target", description: "Coverage is thin. One lost deal creates a miss. Active pipeline development needed."}`
  - `{min: 3.0, max: 4.0, label: "Healthy", description: "Adequate buffer. Normal deal slippage can be absorbed."}`
  - `{min: 4.0, max: null, label: "Strong", description: "Healthy coverage. Monitor for pipeline quality vs. quantity."}`
- **Contributing Patterns:** P01, P04, P40

---

### SL-02 — Forecast Accuracy
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Ratio of actual revenue closed in a period to the forecast made at period
  start. Low accuracy signals either poor deal qualification or premature commitment to pipeline.
- **Threshold Bands:**
  - `{min: null, max: 60, label: "Critical", description: "Revenue forecasts are unreliable. Decisions based on this forecast carry high risk."}`
  - `{min: 60, max: 75, label: "Below Target", description: "Meaningful gap between forecast and reality. Qualification discipline needs attention."}`
  - `{min: 75, max: 90, label: "Acceptable", description: "Reasonable accuracy. Some slippage is normal in consulting sales."}`
  - `{min: 90, max: null, label: "Strong", description: "High forecast reliability. Indicates disciplined qualification and pipeline management."}`
- **Contributing Patterns:** P01, P40

---

### SL-03 — Average Deal Size
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Mean contract value across closed deals in the trailing 12 months, in
  thousands of dollars. Flat or declining trend relative to prior periods signals pricing or
  scope discipline issues.
- **Threshold Bands:**
  - `{min: null, max: 100, label: "Small", description: "Engagements are short and fragmented. High administrative overhead relative to delivery value."}`
  - `{min: 100, max: 200, label: "Below Target", description: "Typical for early-stage or staff-aug oriented firms. Growth depends on volume."}`
  - `{min: 200, max: 400, label: "Mid-Market", description: "Healthy for project-based delivery firms at 30-75 headcount."}`
  - `{min: 400, max: null, label: "Strong", description: "Large engagements. Delivery governance and account management are critical at this scale."}`
- **Contributing Patterns:** P03, P41

---

### SL-04 — Sales Cycle Length
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average days from first substantive client meeting to signed contract.
  Long cycles tie up sales capacity and signal unclear value proposition or weak qualification.
- **Threshold Bands:**
  - `{min: null, max: 30, label: "Fast", description: "Very fast close. May indicate under-scoped or relationship-based deals without competitive process."}`
  - `{min: 30, max: 60, label: "Healthy", description: "Appropriate for mid-market consulting. Indicates reasonable qualification and proposal discipline."}`
  - `{min: 60, max: 90, label: "Elevated", description: "Cycles are lengthening. Review qualification standards and proposal process."}`
  - `{min: 90, max: null, label: "Critical", description: "Sales capacity is consumed by stalled deals. Qualification and value proposition need review."}`
- **Contributing Patterns:** P02, P04

---

### SL-05 — Proposal Win Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of submitted proposals that result in a signed contract.
  Below target indicates misaligned targeting, weak differentiation, or poor proposal quality.
- **Threshold Bands:**
  - `{min: null, max: 20, label: "Critical", description: "Proposal investment is generating poor returns. Targeting and qualification need review."}`
  - `{min: 20, max: 35, label: "Below Target", description: "Below mid-market consulting benchmark. Proposal quality or targeting discipline needed."}`
  - `{min: 35, max: 55, label: "Healthy", description: "Healthy for competitive consulting sales. Indicates reasonable qualification."}`
  - `{min: 55, max: null, label: "Strong", description: "High win rate. Indicates disciplined qualification -- only proposing winnable work."}`
- **Contributing Patterns:** P04, P05

---

### SL-06 — Revenue Concentration (Top Client %)
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of total annual revenue from the single largest client.
  High concentration creates existential risk from one relationship failure.
- **Threshold Bands:**
  - `{min: null, max: 10, label: "Diversified", description: "Healthy diversification. No single client creates existential revenue risk."}`
  - `{min: 10, max: 20, label: "Moderate", description: "Meaningful concentration. Formal account protection plan warranted."}`
  - `{min: 20, max: 30, label: "Elevated Risk", description: "High concentration. Loss of this client would be materially disruptive."}`
  - `{min: 30, max: null, label: "Critical", description: "Existential concentration. Revenue model is fragile. Diversification is urgent."}`
- **Contributing Patterns:** P05, P40

---

### SL-07 — Repeat Business Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of revenue from clients with more than one engagement in the
  trailing 24 months. High repeat rate indicates delivery quality and relationship strength.
- **Threshold Bands:**
  - `{min: null, max: 30, label: "Low", description: "Growth depends almost entirely on new logo acquisition. High marketing cost relative to revenue."}`
  - `{min: 30, max: 50, label: "Below Target", description: "Account retention is below typical consulting firm benchmark."}`
  - `{min: 50, max: 70, label: "Healthy", description: "Good account retention. Expansion motion should be formalized."}`
  - `{min: 70, max: null, label: "Strong", description: "High retention indicates strong delivery quality and client relationships."}`
- **Contributing Patterns:** P05, P44, P47

---

### SL-08 — Discount Frequency
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of deals closed below the standard rate card in the trailing
  12 months. High discount frequency indicates weak pricing governance.
- **Threshold Bands:**
  - `{min: null, max: 10, label: "Disciplined", description: "Pricing discipline is strong. Exceptions are rare and presumably justified."}`
  - `{min: 10, max: 20, label: "Moderate", description: "Discounting is present but not dominant. Monitor for concentration in specific deals."}`
  - `{min: 20, max: 35, label: "Elevated", description: "Discounting is a pattern. Pricing governance and approval discipline needed."}`
  - `{min: 35, max: null, label: "Critical", description: "Systematic pricing erosion. Rate card is aspirational rather than enforced."}`
- **Contributing Patterns:** P39, P43

---

### SL-09 — Pipeline Stage Conversion Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of opportunities advancing from qualification to proposal stage.
  Low conversion at a specific stage identifies the primary constraint in the sales process.
- **Threshold Bands:**
  - `{min: null, max: 30, label: "Low", description: "Most qualified opportunities do not progress. Qualification criteria may be too loose or value proposition unclear."}`
  - `{min: 30, max: 50, label: "Below Target", description: "Below benchmark for mid-market consulting. Review qualification and proposal triggers."}`
  - `{min: 50, max: 70, label: "Healthy", description: "Acceptable conversion. Indicates reasonable qualification discipline."}`
  - `{min: 70, max: null, label: "Strong", description: "High conversion. Indicates disciplined qualification -- only advancing winnable opportunities."}`
- **Contributing Patterns:** P01, P02, P04

---

### SL-10 — Account Expansion Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Year-over-year revenue change within existing client accounts, excluding
  new logo revenue. Flat or declining account revenue signals absence of structured account
  development.
- **Threshold Bands:**
  - `{min: null, max: 0, label: "Declining", description: "Existing accounts are shrinking. Retention and account development are both at risk."}`
  - `{min: 0, max: 5, label: "Flat", description: "No meaningful expansion. Growth depends entirely on new logo acquisition."}`
  - `{min: 5, max: 15, label: "Healthy", description: "Consistent expansion within existing accounts. Indicates good delivery satisfaction."}`
  - `{min: 15, max: null, label: "Strong", description: "High expansion rate. Structured account management is likely producing results."}`
- **Contributing Patterns:** P03, P05, P47

---

### SL-11 — Pre-Sales Cost as % of Deal Value
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Total internal hours invested in pre-sales activity (discovery, proposal
  development, solutioning) divided by the deal value, expressed as a percentage. High ratios
  indicate proposal investment is not proportionate to deal size.
- **Threshold Bands:**
  - `{min: null, max: 3, label: "Efficient", description: "Pre-sales cost is well-controlled relative to deal value."}`
  - `{min: 3, max: 7, label: "Acceptable", description: "Within normal range for competitive consulting proposals."}`
  - `{min: 7, max: 12, label: "Elevated", description: "Pre-sales cost is high. Review proposal process and qualification discipline."}`
  - `{min: 12, max: null, label: "Critical", description: "Pre-sales investment is consuming material margin before the engagement begins."}`
- **Contributing Patterns:** P02, P04

---

## Domain 2: Sales-to-Delivery Transition

*Signals in this domain measure the quality of the handoff between commercial commitments
and delivery execution. Failures here are the primary structural cause of fixed-fee overruns --
they are upstream of PM execution and cannot be resolved by PM coaching alone.*

---

### SL-12 — Delivery Participation in Pre-Sales
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** Whether and how delivery leadership reviews and validates fixed-fee SOWs
  before execution. The absence of delivery sign-off authority is the primary structural cause
  of fixed-fee overruns.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Delivery has no involvement in SOW review. Contracts are signed before delivery sees them."}`
  - `{level: 1, label: "Informal", description: "Delivery is occasionally consulted informally, at the salesperson's discretion. No structured review gate."}`
  - `{level: 2, label: "Defined", description: "A delivery review step exists for some deals (e.g. above a size threshold) but is not consistently enforced."}`
  - `{level: 3, label: "Managed", description: "Delivery sign-off is required on all fixed-fee SOWs above a defined threshold. Process is followed consistently."}`
  - `{level: 4, label: "Optimized", description: "Delivery participates in solutioning before proposals are written. Review is a value-add, not a gate."}`
- **None Indicators:** Interviewee confirms delivery sees SOWs after signature. Director of
  Delivery cannot recall reviewing a SOW before it was executed. CEO states delivery input
  would slow the sales process. SOW errors that pre-delivery review would have caught are
  present in project records.
- **Contributing Patterns:** P06, P07, P10, P11

---

### SL-13 — SOW Completeness
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** Whether SOWs consistently include defined deliverables, client obligation
  language, change order thresholds, completion criteria, and liability provisions.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "SOWs are minimal or absent. Work proceeds on verbal agreement or email."}`
  - `{level: 1, label: "Informal", description: "SOWs exist but are brief, narrative-only, and lack defined deliverables, assumptions, or client obligations."}`
  - `{level: 2, label: "Defined", description: "SOWs include deliverables and timelines but lack change order thresholds, client obligation language, or acceptance criteria."}`
  - `{level: 3, label: "Managed", description: "SOWs consistently include deliverables, client obligations, change order thresholds, and acceptance criteria. No liquidated damages clauses."}`
  - `{level: 4, label: "Optimized", description: "SOWs include all standard elements plus liquidated damages, IP provisions, and commercial protections reviewed by legal."}`
- **None Indicators:** SOW document review confirms missing sections. Interviewee confirms
  SOWs lack assumption language. Change orders are frequent in early project weeks because
  scope was not defined at contract.
- **Contributing Patterns:** P07, P09, P11, P59

---

### SL-14 — Formal Handoff Process
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether a structured transition meeting between sales and delivery occurs
  before kickoff to transfer context, scope clarity, client relationship history, and staffing
  plan.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No handoff occurs. Delivery receives the signed contract and begins work without context transfer."}`
  - `{level: 1, label: "Informal", description: "An ad hoc conversation may occur at the salesperson's initiative. No checklist, no standard agenda."}`
  - `{level: 2, label: "Defined", description: "A handoff meeting is expected but its content varies. No standard checklist or required participants."}`
  - `{level: 3, label: "Managed", description: "A structured handoff meeting with defined agenda, required participants, and documented outputs occurs on every new engagement."}`
  - `{level: 4, label: "Optimized", description: "Handoff is a multi-phase process: pre-proposal delivery review, formal handoff meeting, and 30-day post-kickoff alignment check."}`
- **None Indicators:** Delivery team reports learning scope details for the first time at
  kickoff. PM was unaware of client history or special commitments made during sales.
  Interviewee confirms no meeting takes place between contract and project start.
- **Contributing Patterns:** P08, P06

---

### SL-15 — Change Order Rate in First 30 Days
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average number of change orders initiated within the first 30 days of a
  project across active engagements. High early change order volume indicates pre-sales scoping
  failures.
- **Threshold Bands:**
  - `{min: null, max: 0.5, label: "Low", description: "Rare early change orders. Scope was well-defined before signature."}`
  - `{min: 0.5, max: 1.0, label: "Moderate", description: "Some early changes are normal. Above 1 per project warrants scope process review."}`
  - `{min: 1.0, max: 2.0, label: "Elevated", description: "Frequent early scope adjustments. Pre-sales scoping discipline needs review."}`
  - `{min: 2.0, max: null, label: "Critical", description: "Systematic early scope instability. SOW quality and discovery process are both failing."}`
- **Contributing Patterns:** P09, P07

---

### SL-16 — Kickoff Readiness
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether a standard kickoff readiness checklist (client contacts, environment
  access, resource assignments, timeline, success criteria alignment) is completed before
  project start.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No kickoff readiness check occurs. Projects begin with unresolved dependencies."}`
  - `{level: 1, label: "Informal", description: "PM informally assesses readiness but no standard checklist exists."}`
  - `{level: 2, label: "Defined", description: "A kickoff checklist exists but is used inconsistently across PMs."}`
  - `{level: 3, label: "Managed", description: "Kickoff readiness checklist is required for all projects and signed off by Director of Delivery."}`
  - `{level: 4, label: "Optimized", description: "Readiness gate with automated tracking. Projects cannot start without checklist completion confirmed in the PM tool."}`
- **None Indicators:** Interviewee confirms projects typically start without formal readiness
  review. PMs report discovering access or dependency issues in week one. No checklist
  document exists.
- **Contributing Patterns:** P08, P11

---

## Domain 3: Delivery Operations

*High variance in delivery signals -- rather than uniformly poor performance -- typically
indicates PM capability differences rather than systemic model failures.*

---

### SL-17 — On-Time Delivery Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of active projects tracking to original or approved revised
  timeline at last portfolio review.
- **Threshold Bands:**
  - `{min: null, max: 60, label: "Critical", description: "Majority of projects are behind schedule. Systemic delivery model failure."}`
  - `{min: 60, max: 75, label: "Below Target", description: "Significant schedule performance gap. PM discipline or governance intervention required."}`
  - `{min: 75, max: 85, label: "Acceptable", description: "Below best practice but manageable. Review root causes of off-track projects."}`
  - `{min: 85, max: null, label: "Healthy", description: "Industry benchmark target for mid-market project delivery."}`
- **Contributing Patterns:** P12, P13, P14

---

### SL-18 — On-Budget Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of active fixed-fee projects tracking at or below confirmed
  budget at last review.
- **Threshold Bands:**
  - `{min: null, max: 60, label: "Critical", description: "Majority of fixed-fee projects are losing margin. Pricing, scoping, or change control is failing systemically."}`
  - `{min: 60, max: 75, label: "Below Target", description: "Significant budget overrun pattern. Fixed-fee model economics are under stress."}`
  - `{min: 75, max: 85, label: "Acceptable", description: "Moderate overrun rate. Review concentration of overruns in specific PMs or project types."}`
  - `{min: 85, max: null, label: "Healthy", description: "Strong budget discipline. Change control and estimation are working."}`
- **Contributing Patterns:** P12, P17, P38

---

### SL-19 — Average Estimation Error
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Mean variance between initial project estimate and actual hours or cost at
  completion, expressed as a percentage. Positive = over-budget.
- **Threshold Bands:**
  - `{min: null, max: 5, label: "Strong", description: "Estimation accuracy is excellent. Methodology is mature."}`
  - `{min: 5, max: 15, label: "Acceptable", description: "Within normal range for project delivery. Monitor for PM-level variance."}`
  - `{min: 15, max: 25, label: "Elevated", description: "Estimation is materially inaccurate. Methodology or pre-sales scoping needs review."}`
  - `{min: 25, max: null, label: "Critical", description: "Estimates are unreliable. Economic planning for fixed-fee work is not possible at this error rate."}`
- **Contributing Patterns:** P12, P15

---

### SL-20 — Change Order Discipline Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of confirmed out-of-scope additions that result in a signed
  change order before work proceeds. Denominator includes all scope additions identified
  during delivery.
- **Threshold Bands:**
  - `{min: null, max: 50, label: "Critical", description: "Scope absorption is the norm. Fixed-fee margin is systematically destroyed by uncompensated work."}`
  - `{min: 50, max: 75, label: "Below Target", description: "Change control is inconsistent. Culture of absorption is present."}`
  - `{min: 75, max: 90, label: "Acceptable", description: "Reasonable change control. Some informal absorption still occurs."}`
  - `{min: 90, max: null, label: "Strong", description: "Strong commercial discipline. Scope additions are consistently captured commercially."}`
- **Contributing Patterns:** P17, P38

---

### SL-21 — Risk Register Usage
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether active projects maintain current risk registers updated at a
  defined cadence.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No risk registers are maintained. Risk management is entirely reactive."}`
  - `{level: 1, label: "Informal", description: "Some PMs maintain informal risk lists. No standard format or update cadence."}`
  - `{level: 2, label: "Defined", description: "Risk register template exists and is used on most projects, but updates are inconsistent."}`
  - `{level: 3, label: "Managed", description: "Risk registers are required on all active projects and reviewed at a defined cadence (minimum monthly)."}`
  - `{level: 4, label: "Optimized", description: "Risk registers feed automated escalation thresholds. High-severity risks trigger leadership notification."}`
- **None Indicators:** Interviewee confirms risks are tracked only informally or not at all.
  PM reports no standard risk tracking tool or process. Escalations consistently happen after
  risks have materialized rather than when identified.
- **Contributing Patterns:** P14, P13

---

### SL-22 — Delivery Methodology Consistency
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether all projects follow a consistent delivery framework with defined
  phase gates, artifacts, and review checkpoints.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No delivery methodology exists. Each PM defines their own approach."}`
  - `{level: 1, label: "Informal", description: "Some shared practices exist informally but are not documented or enforced."}`
  - `{level: 2, label: "Defined", description: "A delivery playbook or methodology exists but adoption varies significantly by PM."}`
  - `{level: 3, label: "Managed", description: "Standard methodology is used on all projects with defined checkpoints. Director of Delivery enforces compliance."}`
  - `{level: 4, label: "Optimized", description: "Methodology is continuously refined based on retrospective data. Templates and playbooks are current."}`
- **None Indicators:** Interviewee confirms each PM uses their own approach. No delivery
  playbook exists. Project artifacts differ significantly across the portfolio.
- **Contributing Patterns:** P15, P16, P18

---

### SL-23 — Rework Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Percentage of total delivery hours attributed to rework -- correcting
  deliverables that did not meet requirements or client expectations on first submission.
- **Threshold Bands:**
  - `{min: null, max: 5, label: "Strong", description: "Low rework. Quality processes and client alignment are working."}`
  - `{min: 5, max: 10, label: "Acceptable", description: "Moderate rework. Review for concentration in specific project types or PMs."}`
  - `{min: 10, max: 20, label: "Elevated", description: "Material rework drag. Quality gates or client alignment processes need review."}`
  - `{min: 20, max: null, label: "Critical", description: "Rework is consuming significant capacity. Delivery model quality is not sustainable."}`
- **Contributing Patterns:** P12, P16, P14

---

### SL-24 — Unplanned Work Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of total delivery hours in a period attributed to work not
  included in the project plan at the start of that period.
- **Threshold Bands:**
  - `{min: null, max: 10, label: "Controlled", description: "Delivery is largely executing to plan. Reactive work is minimal."}`
  - `{min: 10, max: 20, label: "Moderate", description: "Some reactive work is normal. Above 20% indicates systemic planning gaps."}`
  - `{min: 20, max: 30, label: "Elevated", description: "Significant unplanned work is consuming capacity and degrading margin."}`
  - `{min: 30, max: null, label: "Critical", description: "Delivery is predominantly reactive. Project planning is not translating to execution."}`
- **Contributing Patterns:** P13, P17

---

## Domain 4: Resource Management

*The simultaneous presence of high bench cost and PM shortage -- a bench-vacancy paradox --
is a signature signal of role-composition mismatch rather than overall headcount inadequacy.*

---

### SL-25 — Billable Utilization Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Billable hours as a percentage of total available hours across all
  billable consultants. Excludes planned PTO and holidays.
- **Threshold Bands:**
  - `{min: null, max: 60, label: "Critical", description: "Significant bench accumulation. Annual bench cost is material. Immediate capacity review required."}`
  - `{min: 60, max: 72, label: "Below Target", description: "Below benchmark for mid-market IT consulting. Bench cost is eroding EBITDA."}`
  - `{min: 72, max: 82, label: "At Target", description: "Healthy utilization range for project delivery. Allows for bench buffer without excess cost."}`
  - `{min: 82, max: null, label: "Above Target", description: "High utilization. Monitor for overallocation and burnout risk. May indicate under-staffing."}`
- **Contributing Patterns:** P19, P20, P41

---

### SL-26 — Utilization Variance
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Standard deviation of billable utilization rates across individual
  consultants. High variance indicates unequal distribution of billable work.
- **Threshold Bands:**
  - `{min: null, max: 10, label: "Even", description: "Workload is relatively evenly distributed. Staffing model is working."}`
  - `{min: 10, max: 18, label: "Moderate", description: "Some concentration. Identify individuals consistently above or below target."}`
  - `{min: 18, max: 25, label: "High", description: "Significant variance. Some consultants are overloaded while others are underutilized."}`
  - `{min: 25, max: null, label: "Critical", description: "Workload is highly concentrated. Over-allocation and bench coexist simultaneously."}`
- **Contributing Patterns:** P21, P22

---

### SL-27 — Over-Allocation Frequency
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Number of consultants assigned beyond 100% of their confirmed capacity
  at any point in the trailing 90 days.
- **Threshold Bands:**
  - `{min: null, max: 1, label: "Rare", description: "Over-allocation is exceptional and presumably temporary."}`
  - `{min: 1, max: 3, label: "Occasional", description: "Some over-allocation exists. Monitor for recurrence and impact on delivery quality."}`
  - `{min: 3, max: 6, label: "Frequent", description: "Over-allocation is a pattern. Capacity planning and staffing governance need review."}`
  - `{min: 6, max: null, label: "Systemic", description: "Widespread over-allocation. Delivery quality and consultant wellbeing are both at risk."}`
- **Contributing Patterns:** P21, P24

---

### SL-28 — Consultant Voluntary Turnover Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Annual percentage of billable consultants who leave voluntarily, calculated
  on a trailing 12-month basis.
- **Threshold Bands:**
  - `{min: null, max: 8, label: "Low", description: "Strong retention. Compensation, culture, or career path are competitive."}`
  - `{min: 8, max: 15, label: "Healthy", description: "Within industry benchmark for IT consulting (10-15%). Monitor exit interview themes."}`
  - `{min: 15, max: 22, label: "Elevated", description: "Above benchmark. Exit interview analysis needed to identify whether cause is systemic."}`
  - `{min: 22, max: null, label: "Critical", description: "High attrition is disrupting delivery continuity and consuming hiring investment."}`
- **Contributing Patterns:** P52, P24, P53

---

### SL-29 — Time to Staff New Project
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average days from project award (signed contract) to full team assignment
  confirmed.
- **Threshold Bands:**
  - `{min: null, max: 7, label: "Fast", description: "Rapid staffing. Bench depth or contractor bench is available."}`
  - `{min: 7, max: 14, label: "Acceptable", description: "Normal for mid-market consulting firms without large bench reserves."}`
  - `{min: 14, max: 21, label: "Slow", description: "Staffing delays are creating project start risk. Capacity model needs review."}`
  - `{min: 21, max: null, label: "Critical", description: "Staffing is a constraint on revenue conversion. Client relationships at risk from delayed starts."}`
- **Contributing Patterns:** P23, P26

---

### SL-30 — Delivery Capacity Forecasting
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm can produce a forward view of PM and consultant demand
  against confirmed pipeline, enabling planned responses to capacity gaps before they become
  crises.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No capacity forecasting exists. Staffing decisions are made reactively as projects are confirmed."}`
  - `{level: 1, label: "Informal", description: "Leadership maintains a mental model of upcoming capacity but no documented forecast."}`
  - `{level: 2, label: "Defined", description: "A capacity view is produced periodically (monthly or quarterly) but not linked to pipeline stages."}`
  - `{level: 3, label: "Managed", description: "A 60-90 day rolling capacity model is maintained and updated as pipeline moves. Staffing decisions are proactive."}`
  - `{level: 4, label: "Optimized", description: "Pipeline-to-capacity model is integrated with CRM data. Hiring thresholds are automated based on weighted pipeline."}`
- **None Indicators:** Interviewee confirms staffing decisions happen after project starts.
  Two or more simultaneous PM vacancies created by unplanned departures without coverage plan.
  Leadership cannot estimate delivery capacity for the next quarter.
- **Contributing Patterns:** P26, P23, P19

---

### SL-31 — Skill-Based Staffing Practice
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether assignments are made based on confirmed skill match to project
  requirements, rather than primarily on availability.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Staffing is based purely on availability. Skill match is not assessed."}`
  - `{level: 1, label: "Informal", description: "Skill fit is considered informally by the person making the staffing decision, but no standard process exists."}`
  - `{level: 2, label: "Defined", description: "A skills inventory exists and is consulted for new assignments, but availability often overrides skill fit."}`
  - `{level: 3, label: "Managed", description: "Skill-based staffing is standard. Availability-only assignments require documented exception approval."}`
  - `{level: 4, label: "Optimized", description: "Skills inventory is current, searchable, and used automatically in staffing recommendations."}`
- **None Indicators:** Interviewee confirms consultants are assigned based on who is
  available. No skills inventory or matrix exists. Senior consultants are assigned to
  work that does not require their level due to absence of available junior staff.
- **Contributing Patterns:** P22, P25

---

## Domain 5: Project Governance / PMO

*The absence of formal governance structures -- PMO, dashboard, defined escalation paths --
is itself a maturity signal regardless of current delivery performance.*

---

### SL-32 — PMO Maturity
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** The presence, authority, and effectiveness of a formal project management
  office or equivalent governance function with authority over delivery standards, PM
  accountability, and portfolio reporting.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No PMO or equivalent function. Delivery coordination is ad hoc and individual-dependent."}`
  - `{level: 1, label: "Informal", description: "One person (often Director of Delivery) provides loose coordination but has no formal authority over PM standards."}`
  - `{level: 2, label: "Defined", description: "A PMO function is defined with documented responsibilities, but authority to enforce standards is limited or inconsistently applied."}`
  - `{level: 3, label: "Managed", description: "PMO has clear authority over delivery standards, PM accountability, and portfolio reporting. Standards are enforced consistently."}`
  - `{level: 4, label: "Optimized", description: "PMO drives continuous improvement through retrospective data, benchmarking, and proactive capability development."}`
- **None Indicators:** CEO confirms all PM accountability conversations go through them.
  No documented delivery standards exist. Portfolio status is assembled manually by
  whichever PM has time. Interviewee confirms no coordination function exists.
- **Contributing Patterns:** P27, P33, P37

---

### SL-33 — Portfolio Reporting Quality
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether all active projects produce status reports in a standard format
  on a defined cadence, enabling portfolio-level comparison and early warning detection.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No formal project reporting. Portfolio status is assembled through ad hoc manager conversations."}`
  - `{level: 1, label: "Informal", description: "Some PMs produce status reports but format and cadence vary widely."}`
  - `{level: 2, label: "Defined", description: "A standard template exists and most projects use it, but cadence is inconsistent and aggregation is manual."}`
  - `{level: 3, label: "Managed", description: "All projects produce weekly status in a standard format. Portfolio aggregation takes less than 2 hours."}`
  - `{level: 4, label: "Optimized", description: "Portfolio reporting is automated via a PSA or integrated tool. Leadership has real-time dashboard access."}`
- **None Indicators:** Director of Delivery confirms spending 3+ hours weekly on manual
  status aggregation. Interviewee reports no standard report format exists. Leadership
  learns of project problems through client calls rather than internal reporting.
- **Contributing Patterns:** P28, P32, P30

---

### SL-34 — Issue Escalation Time
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average days between a project issue being identified internally and
  formal escalation to leadership for at-risk (Amber or Red) projects.
- **Threshold Bands:**
  - `{min: null, max: 2, label: "Fast", description: "Issues surface quickly. Governance cadence and escalation culture are working."}`
  - `{min: 2, max: 5, label: "Acceptable", description: "Within normal range for weekly governance cadence."}`
  - `{min: 5, max: 10, label: "Slow", description: "Issues are lingering before escalation. Governance cadence or escalation culture needs review."}`
  - `{min: 10, max: null, label: "Critical", description: "Escalation is significantly delayed. Problems become crises before leadership is aware."}`
- **Contributing Patterns:** P29, P13, P30

---

### SL-35 — Governance Cadence
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** The frequency and regularity of portfolio-level governance reviews attended
  by delivery leadership, covering project health, risk, and resource.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No regular governance cadence. Portfolio health is reviewed reactively."}`
  - `{level: 1, label: "Informal", description: "Informal check-ins occur as issues surface but no structured recurring review."}`
  - `{level: 2, label: "Defined", description: "Monthly portfolio review occurs but lacks standard agenda, consistent attendance, or decision outputs."}`
  - `{level: 3, label: "Managed", description: "Weekly governance cadence for Amber and Red projects. Monthly full portfolio review with standard agenda."}`
  - `{level: 4, label: "Optimized", description: "Tiered cadence: daily Amber/Red monitoring, weekly portfolio review, monthly strategic review. All decisions documented."}`
- **None Indicators:** Interviewee confirms leadership learns of project problems through
  client calls. No recurring delivery review meeting exists. Portfolio status meetings are
  called ad hoc when problems surface.
- **Contributing Patterns:** P27, P30, P36

---

### SL-36 — Operational KPI Coverage
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** Whether the firm tracks and reviews a defined set of operational KPIs
  (utilization, on-time delivery, NPS, margin) at a defined cadence.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No operational KPIs are defined or tracked. Decisions are based on intuition."}`
  - `{level: 1, label: "Informal", description: "A few metrics are tracked informally but not reviewed consistently or shared across leadership."}`
  - `{level: 2, label: "Defined", description: "KPIs are defined but coverage is partial (e.g. revenue and utilization tracked; delivery and NPS not tracked)."}`
  - `{level: 3, label: "Managed", description: "A complete KPI set covering sales, delivery, resources, and economics is reviewed at a defined cadence."}`
  - `{level: 4, label: "Optimized", description: "KPI dashboard is automated, available in real time, and feeds strategic planning and investment decisions."}`
- **None Indicators:** Leadership cannot produce utilization rate, on-time delivery rate,
  or gross margin without manual calculation. No dashboard or reporting system exists.
  Interviewee confirms operational decisions are made without data.
- **Contributing Patterns:** P32, P28

---

### SL-37 — Decision Authority Clarity
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether decision rights are formally defined and delegated -- particularly
  whether delivery leaders can enforce PM standards, staffing, and change orders without
  CEO approval for each action.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "All significant decisions route through the CEO. No formal delegation exists."}`
  - `{level: 1, label: "Informal", description: "Some delegation occurs informally based on relationship, but authority boundaries are undefined."}`
  - `{level: 2, label: "Defined", description: "Authority matrix exists on paper but exceptions frequently require CEO involvement."}`
  - `{level: 3, label: "Managed", description: "Delivery leader can enforce PM standards, staffing, and change orders without CEO involvement. Authority matrix is followed."}`
  - `{level: 4, label: "Optimized", description: "Delegation is comprehensive. CEO's operational role is strategic. Leaders below CEO handle all operational decisions."}`
- **None Indicators:** Interviewee confirms Director of Delivery must obtain CEO approval
  for PM assignment changes, change order decisions, or SOW modifications. CEO is the
  final decision point on pricing, staffing, and scope simultaneously.
- **Contributing Patterns:** P34, P35, P31

---

## Domain 6: Consulting Economics

*Economic signals are the downstream output of failures in all other domains -- pricing,
delivery, resource, and governance failures all eventually appear in the economics data.*

---

### SL-38 — Revenue per Billable Consultant
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Annual revenue divided by total billable headcount. Measures productivity
  of the delivery organization. Trend direction is as important as the current value.
- **Threshold Bands:**
  - `{min: null, max: 150, label: "Critical", description: "Revenue productivity is well below benchmark. Indicates significant utilization, pricing, or capacity problems."}`
  - `{min: 150, max: 190, label: "Below Target", description: "Below mid-market IT consulting benchmark. Headcount may be growing faster than revenue."}`
  - `{min: 190, max: 230, label: "At Target", description: "Within healthy range for mid-market IT consulting at 30-75 headcount."}`
  - `{min: 230, max: null, label: "Strong", description: "Above benchmark. Indicates strong utilization and/or pricing discipline."}`
- **Contributing Patterns:** P41, P20, P39

---

### SL-39 — Gross Margin (Firm Level)
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Revenue minus direct delivery costs (labor, contractor, delivery tools)
  as a percentage of revenue, measured at the firm level. Trend direction over 2+ years
  is a critical diagnostic context.
- **Threshold Bands:**
  - `{min: null, max: 25, label: "Critical", description: "Gross margin is insufficient to cover overhead and generate EBITDA. Structural intervention required."}`
  - `{min: 25, max: 33, label: "Below Target", description: "Margin is below mid-market IT consulting benchmark. Pricing or delivery cost structure needs review."}`
  - `{min: 33, max: 42, label: "Healthy", description: "Within benchmark range for project-based IT consulting delivery."}`
  - `{min: 42, max: null, label: "Strong", description: "Above benchmark. Indicates strong pricing discipline and/or favorable delivery cost structure."}`
- **Contributing Patterns:** P38, P39, P41, P43

---

### SL-40 — Gross Margin Trend
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Change in gross margin percentage over the trailing 3-year period, in
  percentage points. Trend direction is often more diagnostic than the current level.
- **Threshold Bands:**
  - `{min: null, max: -5, label: "Deteriorating", description: "Margin is compressing materially. Structural drivers must be identified and addressed."}`
  - `{min: -5, max: -2, label: "Declining", description: "Moderate compression. Monitor cause -- could be investment-driven or structural."}`
  - `{min: -2, max: 2, label: "Stable", description: "Margin is holding. Confirm this reflects discipline, not masking deterioration in mix."}`
  - `{min: 2, max: null, label: "Improving", description: "Margin expansion. Pricing discipline, utilization improvement, or favorable mix shift."}`
- **Contributing Patterns:** P38, P43, P35

---

### SL-41 — Billable Rate Realization
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Average realized bill rate as a percentage of the standard rate card
  target, across all closed deals in the trailing 12 months.
- **Threshold Bands:**
  - `{min: null, max: 88, label: "Critical", description: "Rate card is aspirational. Systematic discounting or rate card non-enforcement is destroying margin."}`
  - `{min: 88, max: 94, label: "Below Target", description: "Meaningful rate leakage. Deal-level analysis needed to identify concentration."}`
  - `{min: 94, max: 98, label: "Acceptable", description: "Minor leakage. Some discount for strategic relationships may be justified."}`
  - `{min: 98, max: null, label: "Strong", description: "Rate card is being realized. Pricing discipline is working."}`
- **Contributing Patterns:** P39, P43

---

### SL-42 — EBITDA Margin
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Earnings before interest, taxes, depreciation, and amortization as a
  percentage of revenue. The primary measure of firm profitability and reinvestment capacity.
- **Threshold Bands:**
  - `{min: null, max: 5, label: "Critical", description: "Firm has insufficient profitability to fund growth, talent retention, or infrastructure investment."}`
  - `{min: 5, max: 12, label: "Below Target", description: "Below benchmark for healthy mid-market consulting. Operational improvements required."}`
  - `{min: 12, max: 20, label: "Healthy", description: "Within benchmark range. Adequate reinvestment capacity."}`
  - `{min: 20, max: null, label: "Strong", description: "Above benchmark. Strong operational discipline or favorable leverage model."}`
- **Contributing Patterns:** P38, P41, P42

---

### SL-43 — Non-Billable Overhead Ratio
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Non-billable hours (internal meetings, business development, administration,
  training) as a percentage of total consultant hours.
- **Threshold Bands:**
  - `{min: null, max: 15, label: "Lean", description: "Very low overhead. May indicate under-investment in BD, training, or internal improvement."}`
  - `{min: 15, max: 25, label: "Healthy", description: "Reasonable overhead for a growing consulting firm."}`
  - `{min: 25, max: 33, label: "Elevated", description: "Overhead is consuming meaningful billable capacity. Internal process review warranted."}`
  - `{min: 33, max: null, label: "Critical", description: "More than a third of consultant time is non-billable. Structural overhead problem."}`
- **Contributing Patterns:** P42, P36

---

### SL-44 — Revenue Predictability
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of next-quarter revenue that is contracted or highly probable
  (>80% confidence) at the start of the quarter.
- **Threshold Bands:**
  - `{min: null, max: 40, label: "Low", description: "Revenue is largely unpredictable. Planning and investment decisions are made on weak foundations."}`
  - `{min: 40, max: 60, label: "Below Target", description: "Moderate predictability. Investment decisions are constrained."}`
  - `{min: 60, max: 80, label: "Acceptable", description: "Reasonable visibility. Manageable uncertainty for near-term planning."}`
  - `{min: 80, max: null, label: "Strong", description: "High revenue visibility. Enables confident hiring and investment decisions."}`
- **Contributing Patterns:** P40, P01, P05

---

### SL-45 — Consulting Leverage Ratio
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Ratio of junior to senior billable consultants. Low leverage indicates
  over-reliance on senior staff for delivery, compressing margins.
- **Threshold Bands:**
  - `{min: null, max: 1.0, label: "Inverted", description: "More senior than junior consultants. Delivery cost is high relative to revenue potential. Margin compression likely."}`
  - `{min: 1.0, max: 2.0, label: "Below Target", description: "Moderate leverage. Senior-heavy delivery model constrains margin and scale."}`
  - `{min: 2.0, max: 3.5, label: "Healthy", description: "Healthy leverage for mid-market project delivery."}`
  - `{min: 3.5, max: null, label: "High Leverage", description: "High leverage. Monitor delivery quality -- senior oversight per junior consultant may be thin."}`
- **Contributing Patterns:** P41, P42

---

## Domain 7: Customer Experience

*Customer experience signals are lagging indicators -- by the time NPS declines or escalations
occur, the operational failures that caused them are typically 1-2 quarters old.*

---

### SL-46 — Net Promoter Score
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Standard NPS survey score across the active client base. Measured on a
  recurring basis (minimum annually). Trend direction between periods is diagnostic.
- **Threshold Bands:**
  - `{min: null, max: 20, label: "Critical", description: "Client satisfaction is well below industry benchmark. Relationship and renewal risk is high."}`
  - `{min: 20, max: 40, label: "Below Benchmark", description: "Below industry average for IT consulting (~+40). Systematic delivery or communication issues likely."}`
  - `{min: 40, max: 60, label: "Healthy", description: "At or above IT consulting industry benchmark."}`
  - `{min: 60, max: null, label: "Strong", description: "Top quartile client satisfaction. Indicates strong delivery quality and proactive relationship management."}`
- **Contributing Patterns:** P44, P45, P46

---

### SL-47 — Client Escalation Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Number of client-initiated escalations above the PM level per quarter
  per 10 active projects. Any CTO or executive-level client escalation is a high-severity
  indicator regardless of rate.
- **Threshold Bands:**
  - `{min: null, max: 0.5, label: "Low", description: "Rare escalations. Delivery and communication are meeting client expectations."}`
  - `{min: 0.5, max: 1.5, label: "Moderate", description: "Some escalations. Review root causes for recurrence patterns."}`
  - `{min: 1.5, max: 3.0, label: "Elevated", description: "Frequent escalations. Delivery model or communication discipline needs systemic review."}`
  - `{min: 3.0, max: null, label: "Critical", description: "Escalations are a defining characteristic of the client experience. Trust is eroding."}`
- **Contributing Patterns:** P44, P45, P29, P46

---

### SL-48 — Project Renewal Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of completed projects where the client commissioned follow-on
  work within 12 months.
- **Threshold Bands:**
  - `{min: null, max: 20, label: "Low", description: "Clients are not returning. Delivery satisfaction or relationship development is failing."}`
  - `{min: 20, max: 40, label: "Below Target", description: "Below typical consulting benchmark. Review delivery quality and account management practices."}`
  - `{min: 40, max: 60, label: "Healthy", description: "Good renewal rate. Delivery is satisfying clients."}`
  - `{min: 60, max: null, label: "Strong", description: "High renewal rate. Strong delivery quality and client relationships."}`
- **Contributing Patterns:** P05, P44, P46, P47

---

### SL-49 — Client Communication Cadence
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether clients receive proactive, structured status communications from
  PMs on a defined cadence -- beyond reactive responses to client inquiries.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Clients receive no structured proactive communication. Updates occur only when clients ask."}`
  - `{level: 1, label: "Informal", description: "Some PMs communicate proactively at their own discretion. No standard format or cadence."}`
  - `{level: 2, label: "Defined", description: "A communication cadence is defined but PM compliance varies significantly."}`
  - `{level: 3, label: "Managed", description: "All projects maintain a weekly client status communication. Standard format used consistently."}`
  - `{level: 4, label: "Optimized", description: "Proactive communication is automated or systematized. Clients have portal access to real-time project status."}`
- **None Indicators:** Multiple clients report discovering project problems through their
  own tracking rather than proactive communication. Client satisfaction data shows
  communication as the lowest-rated category. PM confirms updates are sent only when asked.
- **Contributing Patterns:** P45, P44

---

### SL-50 — Time to Resolve Client Issue
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average days from a client raising an issue to formal resolution
  acknowledgment from leadership. Excludes the technical resolution time --
  measures the relationship response speed.
- **Threshold Bands:**
  - `{min: null, max: 2, label: "Fast", description: "Client issues receive prompt acknowledgment. Relationship responsiveness is strong."}`
  - `{min: 2, max: 5, label: "Acceptable", description: "Within reasonable range. Monitor for issues that require escalation before resolution."}`
  - `{min: 5, max: 10, label: "Slow", description: "Client issues linger. Escalation handling discipline needs improvement."}`
  - `{min: 10, max: null, label: "Critical", description: "Slow issue resolution is damaging client trust and increasing escalation risk."}`
- **Contributing Patterns:** P44, P29

---

### SL-51 — Stakeholder Alignment
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether key client stakeholders (executive sponsor, day-to-day contact,
  technical lead) are aligned on project scope, timeline, and success criteria at kickoff
  and maintained through delivery.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No stakeholder alignment process exists. Misalignment surfaces mid-project."}`
  - `{level: 1, label: "Informal", description: "PM informally assesses alignment but no structured process or documentation."}`
  - `{level: 2, label: "Defined", description: "Kickoff alignment meeting occurs but stakeholder map and alignment are not maintained through delivery."}`
  - `{level: 3, label: "Managed", description: "Stakeholder map is documented at kickoff and reviewed monthly. Misalignment triggers a formal re-alignment process."}`
  - `{level: 4, label: "Optimized", description: "Stakeholder alignment is systematically tracked. Early warning indicators trigger proactive outreach before misalignment causes friction."}`
- **None Indicators:** Multiple client escalations trace to different client stakeholders
  having different understandings of scope. PM reports learning of client dissatisfaction
  from the client's own tracking rather than through delivery reviews.
- **Contributing Patterns:** P44, P11

---

## Domain 8: AI Readiness

*AI Readiness signals measure both the compliance exposure from ungoverned AI tool adoption
and the competitive positioning opportunity from governed AI delivery capability. Both
dimensions are active -- the risk exists today on signed contracts; the opportunity is
being captured by competitors in active deal evaluations.*

---

### SL-52 — AI Usage Policy
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** Whether a formal, published AI acceptable use policy governs which tools
  can be used on client engagements, under what conditions, and with what data handling
  restrictions.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No AI usage policy exists. Individual consultant AI tool use is unmanaged and ungoverned."}`
  - `{level: 1, label: "Informal", description: "Leadership has expressed verbal guidance about AI tools but nothing is documented or distributed."}`
  - `{level: 2, label: "Defined", description: "A written AI usage policy exists and has been distributed to all delivery staff."}`
  - `{level: 3, label: "Managed", description: "Policy exists, is enforced, and includes an approved tool list, data classification rules, and a client disclosure framework."}`
  - `{level: 4, label: "Optimized", description: "Policy is integrated into onboarding, reviewed quarterly, and updated as new tools are assessed. Incident reporting mechanism exists."}`
- **None Indicators:** CEO or Director of Delivery confirms no written policy exists.
  Delivery staff are using AI tools without any organizational guidance. Finance Lead or
  Operations Manager has escalated the governance gap without resolution.
- **Contributing Patterns:** P50

---

### SL-53 — AI Tool Use in Delivery
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** The degree to which AI tools are actively used in billable delivery work,
  and whether that usage is governed, consistent, and producing measurable productivity gains.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No AI tools are used in delivery. Firm is operating entirely on pre-AI delivery model."}`
  - `{level: 1, label: "Informal", description: "Some consultants use AI tools informally at their own discretion. No organizational awareness, approval, or measurement."}`
  - `{level: 2, label: "Defined", description: "AI tool use is acknowledged and an approved tool list exists, but adoption is uneven and not measured."}`
  - `{level: 3, label: "Managed", description: "AI tools are used consistently across delivery. Productivity impact is measured and shared. Usage is governed by policy."}`
  - `{level: 4, label: "Optimized", description: "AI-accelerated delivery is a documented methodology. Productivity benchmarks are established and AI use is a competitive differentiator."}`
- **None Indicators:** CEO confirms no AI tools are in use. Interviewee reports delivery
  staff are discouraged from AI tool use or have no access to approved tools.
- **Contributing Patterns:** P48, P50

---

### SL-54 — SOW AI Provisions
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the standard SOW template includes language governing AI tool
  use, data handling for AI-processed content, and client disclosure requirements.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "SOW template contains no AI tool use language. All active contracts are silent on AI."}`
  - `{level: 1, label: "Informal", description: "AI provisions are occasionally negotiated client-by-client at salesperson discretion. No standard language."}`
  - `{level: 2, label: "Defined", description: "Standard AI clause exists in the SOW template covering disclosure. Data handling not yet addressed."}`
  - `{level: 3, label: "Managed", description: "SOW template includes AI disclosure, data classification rules, and data handling restrictions. All new contracts include this language."}`
  - `{level: 4, label: "Optimized", description: "AI provisions are reviewed by legal annually. Client-specific AI addenda are available for regulated-industry clients."}`
- **None Indicators:** SOW document review confirms no AI language present. Interviewee
  confirms template has never been updated for AI. Legal counsel has not reviewed AI
  exposure in active contracts.
- **Contributing Patterns:** P50, P59

---

### SL-55 — AI Competitive Positioning
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm has a defined, client-facing AI capability narrative
  and whether AI methodology is incorporated into competitive proposals.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Firm has no AI narrative. Cannot respond to client AI capability questions. Not mentioned in proposals."}`
  - `{level: 1, label: "Informal", description: "Individual consultants mention AI informally in client conversations but no organizational positioning exists."}`
  - `{level: 2, label: "Defined", description: "An AI positioning statement exists and is included in capability decks but is not differentiated or methodology-backed."}`
  - `{level: 3, label: "Managed", description: "A documented AI delivery methodology is incorporated into competitive proposals. Win/loss tracking includes AI as an evaluation criterion."}`
  - `{level: 4, label: "Optimized", description: "AI capability is a primary competitive differentiator. Marketed proactively, supported by client case studies and measurable productivity benchmarks."}`
- **None Indicators:** Interviewee confirms a deal was lost where AI capability was a
  stated evaluation criterion. No AI methodology document exists. AI is not mentioned
  in the standard proposal template.
- **Contributing Patterns:** P49, P48

---

### SL-56 — AI Business Model Readiness
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm's billing model and pricing framework account for the
  economic impact of AI-accelerated delivery -- specifically whether time-and-materials
  billing is being applied to AI-compressed work without a compensating value-based or
  outcome-based pricing adjustment.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Billing model is entirely T&M. AI efficiency gains reduce hours billed with no revenue offset. Margin is declining as AI adoption increases."}`
  - `{level: 1, label: "Informal", description: "Leadership is aware of the tension but no pricing adjustment has been made."}`
  - `{level: 2, label: "Defined", description: "A pricing framework review is underway. Some fixed-fee or outcome-based structures are being piloted."}`
  - `{level: 3, label: "Managed", description: "AI-enabled engagements are priced using a value or outcome-based model that captures efficiency gains. Not all engagements are affected."}`
  - `{level: 4, label: "Optimized", description: "Pricing model has been redesigned for AI economics. Efficiency gains are shared with clients through outcome-based pricing that preserves margin."}`
- **None Indicators:** Interviewee confirms all work is billed T&M with no adjustment
  for AI productivity. CEO is unaware of the billing model implications of AI adoption.
- **Contributing Patterns:** P51

---

### SL-57 — Client Data Handling for AI
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether data classification rules govern which client data categories
  can be processed by which AI tools, preventing unintended exposure of confidential
  or regulated client data to public AI models.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No data classification rules exist. Client data is processed by AI tools without restriction."}`
  - `{level: 1, label: "Informal", description: "Individual consultants make their own judgments about what is safe to process in AI tools."}`
  - `{level: 2, label: "Defined", description: "Written data classification guidance exists distinguishing what may and may not be processed by AI tools."}`
  - `{level: 3, label: "Managed", description: "Data classification rules are part of the AI usage policy, enforced through training and the approved tool list."}`
  - `{level: 4, label: "Optimized", description: "Technical controls (DLP, approved enterprise AI tools with data residency) supplement policy controls."}`
- **None Indicators:** Interviewee confirms client data has been entered into a public AI
  tool without restriction. No guidance exists distinguishing what can be processed in
  public vs enterprise AI models.
- **Contributing Patterns:** P50

---

## Domain 9: Human Resources

*HR signals are often late-surfacing -- by the time turnover increases or performance
management failures become visible, the cultural or structural conditions that caused
them have been present for 12-18 months.*

---

### SL-58 — Voluntary Turnover Rate
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Annual percentage of all employees (not just consultants) who leave
  voluntarily, trailing 12 months. Consultant and PM-specific rates are more diagnostic
  when available.
- **Threshold Bands:**
  - `{min: null, max: 8, label: "Low", description: "Strong retention. Compensation, culture, or career path are competitive."}`
  - `{min: 8, max: 15, label: "Healthy", description: "Within IT consulting industry benchmark (10-15%)."}`
  - `{min: 15, max: 22, label: "Elevated", description: "Above benchmark. Systematic exit interview review required."}`
  - `{min: 22, max: null, label: "Critical", description: "High attrition is materially disrupting delivery and consuming replacement investment."}`
- **Contributing Patterns:** P52, P24

---

### SL-59 — Career Development Framework
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether defined career paths, promotion criteria, and individual
  development planning exist for consulting staff.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No career framework exists. Promotions are ad hoc and criteria are undefined."}`
  - `{level: 1, label: "Informal", description: "Title levels exist but promotion criteria are unstated and applied inconsistently."}`
  - `{level: 2, label: "Defined", description: "A career ladder with documented levels and promotion criteria exists. Not all managers use it consistently."}`
  - `{level: 3, label: "Managed", description: "Career framework is used in all annual reviews. Individual development plans exist for all permanent staff."}`
  - `{level: 4, label: "Optimized", description: "Career framework is tied to compensation bands, development investment, and succession planning."}`
- **None Indicators:** Interviewee confirms promotions are based on tenure or personal
  relationships rather than documented criteria. No career ladder document exists. Staff
  cannot articulate their growth path within the firm.
- **Contributing Patterns:** P53, P52

---

### SL-60 — Performance Management Maturity
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether a structured performance management process (goal setting,
  regular feedback, documented reviews, formal improvement plans) exists for consulting staff.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No formal performance management. Underperformance is managed informally or ignored until it becomes a crisis."}`
  - `{level: 1, label: "Informal", description: "Managers provide feedback informally. No documented reviews or structured process."}`
  - `{level: 2, label: "Defined", description: "Annual reviews occur but are inconsistent in quality. No structured goal-setting or mid-year check-ins."}`
  - `{level: 3, label: "Managed", description: "Structured performance cycle with documented goals, mid-year review, and annual evaluation. PIPs are formal and documented."}`
  - `{level: 4, label: "Optimized", description: "Continuous feedback culture. Performance data informs staffing, development investment, and compensation decisions."}`
- **None Indicators:** Interviewee confirms no annual review process exists. Underperforming
  consultant is on an informal plan with no documentation, timeline, or defined exit criteria.
  Manager cannot recall giving structured written feedback.
- **Contributing Patterns:** P56, P55

---

### SL-61 — Manager Development Investment
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether people managers receive structured training and development for
  their management responsibilities, distinct from their technical consulting skills.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No manager development occurs. Promotion to management is the only recognition of the new role."}`
  - `{level: 1, label: "Informal", description: "Senior leaders provide informal coaching to new managers but no structured program exists."}`
  - `{level: 2, label: "Defined", description: "A manager onboarding or training program exists but is not consistently applied."}`
  - `{level: 3, label: "Managed", description: "Structured manager development program exists with defined competencies. New managers receive training before or shortly after promotion."}`
  - `{level: 4, label: "Optimized", description: "Ongoing manager development is embedded in the culture. Leadership competency framework drives coaching, promotion, and development investment."}`
- **None Indicators:** Managers were promoted based solely on technical performance with
  no preparation for people management. Direct reports report lack of structured feedback
  or development conversations. Manager confirms no training was provided.
- **Contributing Patterns:** P56, P37

---

### SL-62 — HR Infrastructure Maturity
- **Type:** Maturity
- **Priority Tier:** 1
- **Definition:** Whether formal HR policies, compliance practices, and HR operational
  capacity exist proportionate to the firm's headcount.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No HR function exists. Founders handle all people issues informally. No documented policies."}`
  - `{level: 1, label: "Informal", description: "Basic employment documentation exists but HR is managed ad hoc by non-HR leadership."}`
  - `{level: 2, label: "Defined", description: "Core policies are documented (handbook, PTO, harassment). No dedicated HR capacity at or above 30 headcount."}`
  - `{level: 3, label: "Managed", description: "Dedicated HR function (in-house or fractional) proportionate to headcount. Compliance reviews occur regularly."}`
  - `{level: 4, label: "Optimized", description: "HR is a strategic function. People data informs business planning and culture investment decisions."}`
- **None Indicators:** Firm has 30+ employees and no HR professional in any capacity.
  CEO handles all terminations, compensation conversations, and compliance questions
  personally. No employee handbook exists or it has not been updated in 3+ years.
- **Contributing Patterns:** P55

---

### SL-63 — Hiring Process Maturity
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether a structured, consistent hiring process (defined criteria,
  standardized interview stages, calibration, scoring) exists and is used for all roles.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Hiring is unstructured. Each manager uses their own approach. No scorecard or calibration."}`
  - `{level: 1, label: "Informal", description: "Some consistency in interview stages but evaluation criteria vary by manager."}`
  - `{level: 2, label: "Defined", description: "Standard interview stages and a scorecard exist but calibration across managers is inconsistent."}`
  - `{level: 3, label: "Managed", description: "Consistent structured interview process with defined criteria, scoring rubric, and calibration sessions before offers."}`
  - `{level: 4, label: "Optimized", description: "Hiring process produces measurable quality outcomes. New hire performance at 90 days is tracked and feeds process improvement."}`
- **None Indicators:** Interviewee confirms each manager runs their own interview process.
  No interview scorecard or evaluation rubric exists. Early attrition rate from poor-fit
  hires is above 15% in the first 6 months.
- **Contributing Patterns:** P54, P25

---

### SL-64 — Compensation Competitiveness
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm benchmarks its compensation against market data and
  whether compensation decisions are informed by that benchmarking rather than made
  based on budget alone.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Compensation is set without reference to market data. No benchmarking occurs."}`
  - `{level: 1, label: "Informal", description: "Leadership has informal market awareness but no structured benchmarking process."}`
  - `{level: 2, label: "Defined", description: "Compensation is benchmarked against market data periodically (annually) for new hires. Existing staff are not systematically reviewed."}`
  - `{level: 3, label: "Managed", description: "Annual compensation benchmarking covers all roles. Adjustments are made proactively to address gaps before they drive turnover."}`
  - `{level: 4, label: "Optimized", description: "Real-time compensation benchmarking informs hiring offers and retention risk assessments. Compensation is a managed retention lever."}`
- **None Indicators:** Exit interviews confirm compensation was a primary departure reason.
  Firm has not conducted a compensation review in 2+ years. Interviewee cannot state
  whether compensation is competitive relative to market.
- **Contributing Patterns:** P52, P53

---

### SL-65 — Succession Planning
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm has identified and is developing internal successors
  for key delivery and leadership roles, reducing single-point-of-failure dependency.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No succession planning exists. Loss of any key individual creates an immediate operational crisis."}`
  - `{level: 1, label: "Informal", description: "Leadership is aware of key dependencies but no formal succession planning has occurred."}`
  - `{level: 2, label: "Defined", description: "Key roles have been identified as succession risks. Potential successors have been named but no development plans exist."}`
  - `{level: 3, label: "Managed", description: "Key role successors are identified and actively developed. Coverage plans exist for planned and unplanned absences."}`
  - `{level: 4, label: "Optimized", description: "Succession planning is part of the annual talent review. Bench depth is a measurable metric and investment is made to close gaps."}`
- **None Indicators:** Director of Delivery departure creates immediate portfolio governance
  failure with no coverage plan. CEO confirms all delivery leadership authority rests
  with one person. No internal candidate could step into the Director of Delivery role.
- **Contributing Patterns:** P37, P55

---

## Domain 10: Finance and Commercial

*Financial infrastructure signals measure whether the firm's financial systems are
proportionate to its scale and complexity. Firms that outgrow their financial infrastructure
without upgrading it lose the ability to detect deterioration in real time.*

---

### SL-66 — Monthly Financial Close Cycle
- **Type:** Numeric
- **Priority Tier:** 1
- **Definition:** Business days required to close the monthly financial books from the
  last day of the month. Slow close creates a decision lag that prevents timely intervention
  on deteriorating projects.
- **Threshold Bands:**
  - `{min: null, max: 5, label: "Best Practice", description: "Close cycle is at or below best practice. Real-time financial management is possible."}`
  - `{min: 5, max: 8, label: "Acceptable", description: "Within achievable target range. Minor process improvements may be available."}`
  - `{min: 8, max: 12, label: "Slow", description: "Financial signals are delayed. Project interventions are reactive rather than proactive."}`
  - `{min: 12, max: null, label: "Critical", description: "Financial close is materially slow. Leadership is making decisions on data 2-4 weeks old."}`
- **Contributing Patterns:** P60, P32

---

### SL-67 — Deal-Level Rate Tracking
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm can produce a report showing realized bill rate, discount
  amount, and gross margin at the individual deal level -- enabling attribution of rate
  leakage to specific clients, salespeople, or deal types.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Only firm-level average rate is available. Deal-level rate data does not exist."}`
  - `{level: 1, label: "Informal", description: "Deal-level rates can be reconstructed manually from QuickBooks or invoicing system with significant effort."}`
  - `{level: 2, label: "Defined", description: "Deal-level rate report exists but is produced manually and infrequently."}`
  - `{level: 3, label: "Managed", description: "Deal-level rate tracking is automated and reviewed monthly. Discounts are visible by deal, salesperson, and client."}`
  - `{level: 4, label: "Optimized", description: "Deal-level rate tracking feeds real-time pricing governance alerts. Below-rate deals trigger approval workflow before execution."}`
- **None Indicators:** CEO confirms knowing firm-level average rate but unable to identify
  which deals drove it below target. Finance Lead cannot produce deal-level report without
  manual QuickBooks extraction taking multiple hours.
- **Contributing Patterns:** P39, P43, P57

---

### SL-68 — Project-Level Margin Reporting
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm can produce project-level gross margin reports on a
  defined cadence, enabling proactive intervention on deteriorating engagements before
  the financial outcome is locked.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No project-level margin reporting exists. Financial outcomes are only visible at project close."}`
  - `{level: 1, label: "Informal", description: "Project margin can be estimated informally by finance on request, requiring 2-3 hours of manual assembly."}`
  - `{level: 2, label: "Defined", description: "Quarterly project margin reports are produced. Overruns are visible 8-12 weeks after they begin."}`
  - `{level: 3, label: "Managed", description: "Monthly project margin reports are automated or semi-automated. Overrun trends are visible within 2-4 weeks."}`
  - `{level: 4, label: "Optimized", description: "Weekly or real-time project burn tracking with automated alerts at defined budget consumption thresholds."}`
- **None Indicators:** Finance Lead confirms project margin is only assessed at project
  close. No interim project financial reports are produced. Director of Delivery cannot
  state current margin status on active engagements.
- **Contributing Patterns:** P60, P38, P13

---

### SL-69 — Cash Flow Forecasting
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm maintains a forward-looking cash flow forecast enabling
  proactive management of working capital, hiring investment, and operating expenses.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No cash flow forecast exists. Cash position is monitored reactively."}`
  - `{level: 1, label: "Informal", description: "CEO or Finance Lead maintains a mental model of near-term cash flow but nothing is documented."}`
  - `{level: 2, label: "Defined", description: "A 13-week cash flow forecast is produced periodically but not maintained as a living document."}`
  - `{level: 3, label: "Managed", description: "Rolling 13-week cash flow forecast is maintained and reviewed monthly. Investment decisions are informed by forward cash position."}`
  - `{level: 4, label: "Optimized", description: "Cash flow forecasting is integrated with project billing milestones, hiring plans, and pipeline. Scenario modeling is available."}`
- **None Indicators:** Leadership was surprised by a cash constraint that required
  short-term financing. Hiring or investment decisions were delayed due to unexpected
  cash position. No cash flow model document exists.
- **Contributing Patterns:** P58, P60

---

### SL-70 — Collections Discipline
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether a formal accounts receivable collections process exists with
  defined escalation thresholds, follow-up cadence, and accountability for overdue invoices.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Collections are informal. Overdue invoices are followed up at the Finance Lead's discretion with no defined process."}`
  - `{level: 1, label: "Informal", description: "Some follow-up occurs on aged receivables but thresholds and cadence are undefined."}`
  - `{level: 2, label: "Defined", description: "Collections policy exists with defined aging thresholds and escalation path. Not consistently followed."}`
  - `{level: 3, label: "Managed", description: "Collections process is consistently followed. DSO is tracked monthly. Escalations above 60 days are automatic."}`
  - `{level: 4, label: "Optimized", description: "Collections are proactive. Billing milestones are structured to minimize DSO. Client payment behavior informs contract terms."}`
- **None Indicators:** DSO exceeds payment terms by 30+ days. Finance Lead confirms
  no formal follow-up process for overdue invoices. CEO is unaware of current AR aging.
- **Contributing Patterns:** P57

---

### SL-71 — Days Sales Outstanding (DSO)
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Average days between invoice date and payment receipt, across all clients
  in the trailing 90 days. High DSO creates working capital drag even when revenue is strong.
- **Threshold Bands:**
  - `{min: null, max: 30, label: "Strong", description: "Excellent collections. Cash conversion is fast."}`
  - `{min: 30, max: 45, label: "Acceptable", description: "Within standard payment terms for B2B consulting services."}`
  - `{min: 45, max: 60, label: "Elevated", description: "Collections are slow. Working capital impact is material at this DSO."}`
  - `{min: 60, max: null, label: "Critical", description: "Significant cash flow drag. Collections process or client payment terms need immediate attention."}`
- **Contributing Patterns:** P57, P58

---

### SL-72 — Contract Governance Maturity
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether client contracts are reviewed against standard commercial
  protections before execution, including liability caps, IP provisions, and dispute
  resolution terms.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Client paper is accepted without review. No standard commercial protections are enforced."}`
  - `{level: 1, label: "Informal", description: "Senior leadership reviews contracts informally when flagged, but no standard review process exists."}`
  - `{level: 2, label: "Defined", description: "A standard MSA template is used for new clients. Contract playbook exists but is not consistently applied to client paper."}`
  - `{level: 3, label: "Managed", description: "All new contracts are reviewed against a contract playbook. Legal review is triggered for non-standard terms."}`
  - `{level: 4, label: "Optimized", description: "Contract governance is proactive. Standard terms are updated annually. Legal review is embedded in the sales process."}`
- **None Indicators:** SOW lacks liquidated damages clause on a fixed-fee engagement.
  Client MSA was signed without review of liability terms. Interviewee confirms firm
  routinely signs client paper without review.
- **Contributing Patterns:** P59, P07

---

### SL-73 — Financial System Maturity
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm's accounting and financial reporting systems are
  proportionate to its headcount, revenue complexity, and reporting needs.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Financial management is conducted in Excel or equivalent. No accounting system."}`
  - `{level: 1, label: "Informal", description: "QuickBooks or equivalent handles basic accounting but no project-level tracking or reporting."}`
  - `{level: 2, label: "Defined", description: "Accounting system handles invoicing and P&L but project margin, utilization, and deal-level data require manual assembly."}`
  - `{level: 3, label: "Managed", description: "PSA or integrated system provides project-level financial tracking, utilization reporting, and deal-level rate visibility."}`
  - `{level: 4, label: "Optimized", description: "Integrated financial system with real-time dashboards connecting sales pipeline, project delivery, and financial reporting."}`
- **None Indicators:** Finance Lead confirms monthly financial reports require 2-3 hours
  of manual assembly from multiple systems. Project margin is only available quarterly.
  Deal-level rate data requires QuickBooks manual extraction.
- **Contributing Patterns:** P60, P32

---

### SL-74 — Budget and Planning Process
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm conducts formal annual budgeting and quarterly
  reforecasting against a defined financial plan.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No formal budget exists. Financial decisions are made based on current bank balance."}`
  - `{level: 1, label: "Informal", description: "Revenue targets are set but no formal expense budget or planning process."}`
  - `{level: 2, label: "Defined", description: "Annual budget is produced covering revenue and major expense categories. Not updated during the year."}`
  - `{level: 3, label: "Managed", description: "Annual budget with quarterly reforecast. Variance analysis is reviewed monthly. Investment decisions are budget-informed."}`
  - `{level: 4, label: "Optimized", description: "Rolling financial planning is integrated with pipeline data and workforce planning. Scenario modeling informs strategic decisions."}`
- **None Indicators:** CEO confirms no annual budget is produced. Investment decisions
  (hiring, tools, training) are made without reference to a financial plan. Finance Lead
  cannot produce a budget vs. actual variance report.
- **Contributing Patterns:** P60, P58

---

### SL-75 — Fixed-Fee vs T&M Mix
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of annual revenue from fixed-fee contracts (as opposed to
  time-and-materials). High fixed-fee concentration increases margin exposure to scoping
  and estimation failures.
- **Threshold Bands:**
  - `{min: null, max: 25, label: "T&M Dominant", description: "Low fixed-fee risk. Margin exposure to overruns is limited. Revenue is more variable."}`
  - `{min: 25, max: 45, label: "Balanced", description: "Healthy mix for mid-market consulting. Fixed-fee work requires strong governance but supports predictable revenue."}`
  - `{min: 45, max: 65, label: "Fixed-Fee Heavy", description: "Elevated margin exposure. Pricing discipline, SOW quality, and change control governance are critical."}`
  - `{min: 65, max: null, label: "Critical", description: "Majority fixed-fee. Any scoping or estimation failure produces direct margin loss. Governance must be robust."}`
- **Contributing Patterns:** P38, P07, P17

---

### SL-76 — Accounts Receivable Aging Distribution
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of total outstanding accounts receivable that is more than
  60 days past invoice date. Average DSO can mask a small number of severely aged
  receivables that represent concentrated cash flow and client relationship risk.
- **Threshold Bands:**
  - `{min: null, max: 10, label: "Healthy", description: "AR aging is well-controlled. Collections process is working. No single client is creating material overdue exposure."}`
  - `{min: 10, max: 20, label: "Moderate", description: "Some aging concentration. Identify which clients represent the aged balance and whether relationship or invoice accuracy is the cause."}`
  - `{min: 20, max: 35, label: "Elevated", description: "Material AR aging. Cash flow impact is significant. Collections escalation and client conversation required."}`
  - `{min: 35, max: null, label: "Critical", description: "More than a third of AR is significantly overdue. Cash flow is constrained and write-off risk is real."}`
- **Contributing Patterns:** P57, P58

---

### SL-77 — Unbilled Revenue (WIP) Tracking
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether work delivered but not yet invoiced (work-in-progress) is
  tracked and reported as a balance sheet item on a defined cadence. Untracked WIP is
  a hidden cash flow risk -- the firm has performed the work but has not yet converted
  it to receivable or cash.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "WIP is not tracked. Unbilled revenue is invisible until invoices are generated. Cash flow surprises are common."}`
  - `{level: 1, label: "Informal", description: "Finance Lead is aware of approximate unbilled balances but no formal WIP ledger exists."}`
  - `{level: 2, label: "Defined", description: "WIP is tracked in the accounting system but reviewed infrequently and not included in cash flow forecasting."}`
  - `{level: 3, label: "Managed", description: "WIP balance is reported monthly alongside AR. Aging WIP triggers billing follow-up. Cash flow forecast includes WIP conversion assumptions."}`
  - `{level: 4, label: "Optimized", description: "WIP tracking is automated and integrated with project milestones. Billing is triggered automatically at defined completion thresholds."}`
- **None Indicators:** Finance Lead cannot state current unbilled revenue balance without
  manual calculation. CEO is unaware of WIP as a cash flow concept. Invoicing is triggered
  only by client request or project close rather than delivery milestones.
- **Contributing Patterns:** P57, P60, P58

---

### SL-78 — Invoice Accuracy Rate
- **Type:** Numeric
- **Priority Tier:** 2
- **Definition:** Percentage of invoices issued in the trailing 90 days that were disputed
  by the client or required revision before payment. Invoice disputes extend DSO, damage
  client relationships, and are a downstream symptom of SOW gaps or time tracking failures.
- **Threshold Bands:**
  - `{min: null, max: 3, label: "Strong", description: "Invoice accuracy is high. SOW clarity and time tracking are producing clean billing."}`
  - `{min: 3, max: 8, label: "Acceptable", description: "Minor dispute rate. Review recurring dispute causes for process improvement opportunities."}`
  - `{min: 8, max: 15, label: "Elevated", description: "Frequent disputes are extending DSO and consuming finance and PM time. Root cause is upstream -- SOW clarity or time tracking."}`
  - `{min: 15, max: null, label: "Critical", description: "Invoice disputes are a defining characteristic of the billing relationship. Client trust and cash flow are both at risk."}`
- **Contributing Patterns:** P57, P59, P07

---

### SL-79 — Budget vs Actual Variance Reporting
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm actively reviews budget-to-actual variance on a defined
  cadence and whether that variance analysis drives management decisions. Distinct from
  having a budget -- many firms produce an annual budget in January and never reference
  it again.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "No budget exists or budget is not compared to actuals. Financial decisions are made without reference to a plan."}`
  - `{level: 1, label: "Informal", description: "A budget exists but variance to actual is only reviewed when a problem surfaces."}`
  - `{level: 2, label: "Defined", description: "Quarterly budget-to-actual review occurs but does not consistently drive decisions or corrective action."}`
  - `{level: 3, label: "Managed", description: "Monthly budget-to-actual variance is reviewed by leadership. Material variances trigger documented decisions or reforecast."}`
  - `{level: 4, label: "Optimized", description: "Rolling reforecast is maintained continuously. Variance analysis informs hiring, investment, and pricing decisions in real time."}`
- **None Indicators:** CEO cannot state current variance to annual revenue or expense
  budget. Finance Lead confirms budget was produced at year start and has not been
  referenced since. Investment decisions are made without reference to budget remaining.
- **Contributing Patterns:** P60, P32, P58

---

### SL-80 — Revenue Recognition Practices
- **Type:** Maturity
- **Priority Tier:** 2
- **Definition:** Whether the firm applies a consistent, appropriate revenue recognition
  methodology for its contract types -- particularly whether percentage-of-completion or
  milestone-based recognition on fixed-fee work accurately reflects delivery reality
  rather than inflating reported revenue ahead of project economics.
- **Maturity Levels:**
  - `{level: 0, label: "None", description: "Revenue is recognized on a cash or invoice basis with no reference to delivery completion. Fixed-fee project losses are invisible until project close."}`
  - `{level: 1, label: "Informal", description: "Revenue recognition is handled by the accountant without formal policy. Method may vary by contract type without documented rationale."}`
  - `{level: 2, label: "Defined", description: "A revenue recognition policy exists and is applied consistently. Fixed-fee work uses milestone or percentage-of-completion basis."}`
  - `{level: 3, label: "Managed", description: "Revenue recognition policy is reviewed annually and applied consistently. Project margin is visible on an accrual basis during delivery, not only at close."}`
  - `{level: 4, label: "Optimized", description: "Revenue recognition is integrated with project tracking. Percentage-of-completion is calculated from actual delivery data, not estimated progress."}`
- **None Indicators:** Finance Lead confirms revenue is recognized when invoiced or
  when cash is received regardless of delivery status. Fixed-fee project losses are
  only discovered at project close. No revenue recognition policy document exists.
- **Contributing Patterns:** P60, P38, P40

---

## Summary: Pattern Coverage Map

| Pattern | Primary Signals |
|---------|----------------|
| P01 Weak Pipeline Visibility | SL-01, SL-02, SL-09 |
| P02 Long Sales Cycles | SL-04, SL-09, SL-11 |
| P03 Small Deal Size | SL-03, SL-10 |
| P04 Low Close Rates | SL-05, SL-04, SL-09 |
| P05 Revenue Concentration Risk | SL-06, SL-07, SL-10 |
| P06 Overpromising During Sales | SL-12, SL-13 |
| P07 Incomplete SOWs | SL-13, SL-16, SL-75 |
| P08 No Formal Handoff | SL-14, SL-16 |
| P09 Late Scope Discovery | SL-15, SL-13 |
| P10 Delivery Not Involved in Pre-Sales | SL-12, SL-13 |
| P11 Unclear Success Criteria | SL-13, SL-51 |
| P12 Chronic Project Overruns | SL-17, SL-18, SL-19, SL-23 |
| P13 Reactive Delivery Management | SL-21, SL-35, SL-24 |
| P14 Poor Risk Management | SL-21, SL-17, SL-23 |
| P15 Inconsistent Delivery Methods | SL-22, SL-19 |
| P16 Knowledge Loss Between Projects | SL-22 |
| P17 Weak Change Control | SL-20, SL-75 |
| P18 Low Delivery Standard Adoption | SL-22 |
| P19 Utilization Volatility | SL-25, SL-30 |
| P20 Low Utilization | SL-25, SL-26 |
| P21 Overloaded Consultants | SL-27, SL-26 |
| P22 Skill Mismatch | SL-31 |
| P23 Late Hiring | SL-29, SL-30 |
| P24 High Consultant Burnout | SL-27, SL-58 |
| P25 Weak Hiring Discipline | SL-63 |
| P26 No Delivery Capacity Model | SL-30, SL-29 |
| P27 No Delivery Governance | SL-32, SL-35 |
| P28 Inconsistent Reporting | SL-33 |
| P29 Slow Issue Escalation | SL-34, SL-35 |
| P30 Leadership Surprised by Problems | SL-33, SL-35 |
| P31 Weak Project Ownership | SL-37 |
| P32 No Operational Metrics | SL-36, SL-33 |
| P33 No Defined Operating Model | SL-32, SL-37 |
| P34 Leadership Bottleneck | SL-37 |
| P35 Scaling Breakdown | SL-37, SL-40 |
| P36 Lack of Strategic Focus | SL-43, SL-35 |
| P37 Delivery Leadership Gap | SL-32, SL-65 |
| P38 Margin Erosion | SL-39, SL-40, SL-18, SL-20, SL-80 |
| P39 Low Billable Rate Realization | SL-41, SL-08, SL-67 |
| P40 Revenue Instability | SL-44, SL-01, SL-06, SL-80 |
| P41 Low Revenue per Consultant | SL-38, SL-25 |
| P42 High Non-Billable Overhead | SL-43, SL-45 |
| P43 Weak Pricing Discipline | SL-08, SL-41, SL-67 |
| P44 Client Escalations | SL-47, SL-50, SL-49 |
| P45 Weak Client Communication | SL-49, SL-47 |
| P46 Low Client Satisfaction | SL-46, SL-47, SL-48 |
| P47 Weak Account Expansion | SL-07, SL-10, SL-48 |
| P48 No AI Delivery Capability | SL-53, SL-55 |
| P49 No AI Service Offering | SL-55 |
| P50 AI Governance Absence | SL-52, SL-54, SL-57 |
| P51 Business Model Not AI-Ready | SL-56 |
| P52 High Voluntary Turnover | SL-58, SL-64 |
| P53 No Career Development Framework | SL-59, SL-64 |
| P54 Weak Hiring Process | SL-63 |
| P55 Immature HR Function | SL-62, SL-65 |
| P56 Weak Manager Development | SL-61, SL-60 |
| P57 Weak Collections Discipline | SL-70, SL-71, SL-76, SL-78 |
| P58 No Cash Flow Visibility | SL-69, SL-71, SL-77, SL-79 |
| P59 Weak Contract Governance | SL-72, SL-54 |
| P60 Immature Financial Infrastructure | SL-73, SL-66, SL-68, SL-74, SL-77, SL-79, SL-80 |
