# Regulatory posture — EU MDR + AI Act

> **What this file is.** A concrete next-step checklist for the project's
> regulatory exposure under EU law. It is **not** legal advice. The actual
> classification decisions, technical-file authoring, and any contact with
> Notified Bodies require a qualified regulatory consultant.

## Why this matters here

Med Assist is a Romanian-language software service that:

1. Takes user-described symptoms as input,
2. Retrieves matching OTC medicines from the official ANMDM nomenclator,
3. Generates a recommendation or routes to 112 via deterministic red-flag rules.

That fact pattern lands the project in **two overlapping regulatory regimes**
in the EU:

- **MDR (Regulation 2017/745)** — applies if the software has a "medical
  purpose" per Article 2(1). Symptom triage that recommends OTC drugs is the
  canonical borderline case Notified Bodies inspect. A disclaimer ("educational
  project") is *not* a defence — function over labelling.
- **EU AI Act (Regulation 2024/1689)** — automatically classifies any AI system
  that is a Medical Device under MDR as **high-risk** under Annex III. Full
  high-risk obligations apply from **2 August 2027**; the prohibited-practices
  ban is already in force (2 February 2025).

## Decision tree — is this a Medical Device?

```
                       Does the software have a stated medical purpose
                       (diagnosis, prevention, monitoring, prediction,
                       prognosis, treatment, alleviation of disease)?
                                       │
                  ┌────────────────────┴────────────────────┐
                  │ YES                                      │ NO
                  ▼                                          ▼
        Likely IN scope of MDR                     Likely OUT of scope.
        → MDD Annex VIII rules                     But: confirm in writing
          determine risk class                     with a regulatory consultant
                                                   before publishing
                                                   non-educational copy.
```

The current README opens with *"Romanian pharmacy-triage chatbot"* and the eval
calls out *"93.9% triage accuracy"*. Both phrases are pulled toward "medical
purpose." The disclaimer at the bottom does not neutralize this for a Notified
Body — they look at function, not footer text.

**Concrete first action:** write a one-page Intended Purpose Statement using
MDCG 2019-11 (the EU guidance on qualification & classification of software as
a medical device) and ask a regulatory consultant for a written **non-MD
opinion** or an **MD classification proposal**. Budget €1500–€4000 for this
opinion in 2026.

## If MDR-classified

Likely **Class IIa** for symptom triage that recommends therapy (Rule 11 of
MDR Annex VIII). Possibly Class I if the function is narrowed to "information
retrieval, no therapy recommendation."

Class IIa requires:

- [ ] Notified Body involvement (Class I does not)
- [ ] ISO 13485 quality management system
- [ ] ISO 14971 risk management file
- [ ] IEC 62304 software lifecycle (most of what this repo already does
      — version control, tests, CI — satisfies the spirit, not the letter)
- [ ] IEC 82304-1 health software product safety
- [ ] CE marking
- [ ] EUDAMED registration
- [ ] Post-market surveillance plan

Realistic timeline: **9–18 months** with a consultant. Realistic cost:
**€20k–€80k** for the first product through Class IIa. Class I is
~€5k–€15k. Numbers vary wildly by consultant and Notified Body backlog.

## If AI-Act high-risk (which MDR-classified implies)

Article 9-15 obligations land regardless of MD class, full force from
**August 2027**:

| Obligation | What it means here | Status today |
|---|---|---|
| Risk management system | ISO 31000-style ongoing process | ❌ not started |
| Data governance | Train/eval data quality + bias docs | ⚠️  ANMDM source documented; bias analysis missing |
| Technical documentation | Annex IV file (architecture, eval, deploy) | ⚠️  README covers half; needs formal Annex IV mapping |
| Record-keeping (audit logs) | Per-decision input + retrieval + output | ✅ implemented in this PR (triage_audit_log) |
| Transparency to users | Clear "this is AI, not a doctor" | ✅ disclaimer present |
| Human oversight | Override mechanism + clinician escalation | ⚠️  emergency redirect counts; clinician-in-loop missing |
| Accuracy / robustness / cybersec | Documented thresholds + adversarial tests | ⚠️  golden-set + CodeQL exist; threshold sign-off doc missing |
| Post-market monitoring | Drift detection + incident reporting | ❌ not started |

The audit-log piece (item #4 in the audit) is now technically in place. The
*remaining* items above are mostly **paperwork** that needs to exist before the
2027 deadline. None of them are coding tasks.

## What to do — the next 3 things

In this order, low-effort first:

### 1. Get a written regulatory opinion (1–2 weeks, €1500–€4000)

Concrete prompt to send a consultant:

> "We have built a Romanian-language software service that takes user-described
> symptoms, runs a deterministic red-flag rule layer, performs hybrid retrieval
> over the ANMDM nomenclator, and either routes the user to 112 or recommends
> an OTC medicine via an LLM grounded on the retrieved evidence. Source code at
> [URL]. README has the architecture and eval methodology. We need:
>
> (a) an Intended Purpose Statement aligned with MDCG 2019-11,
> (b) a written opinion on whether the software qualifies as a Medical Device
>     under MDR 2017/745 Article 2(1), and if so, the proposed risk class,
> (c) an indication of EU AI Act Annex III applicability."

Romanian regulatory consultants: ANMDM-affiliated firms,
INSPECTORATUL DE STAT PENTRU CONTROLUL PRODUSELOR MEDICALE, or
international firms (TÜV SÜD, BSI, DNV) all do this.

### 2. Tighten the README and UI copy (a day)

Until the opinion is in, **deliberately narrow the framing**:

- README headline: "Educational reference implementation of a Romanian
  RAG triage chatbot — not for clinical use."
- Remove "93.9% triage accuracy" from the landing position; keep it in the
  Eval section so the engineering metric is still there but doesn't read as
  a claim of clinical utility.
- Add an in-app modal on first launch: "Acesta este un proiect educațional,
  nu un instrument medical." Persisted dismissal is fine.

This reduces the chance a Notified Body or regulator reads the project as
*marketed* as a medical device, which is what triggers most enforcement.

### 3. Operationalize the audit log (already half done)

This PR added the `triage_audit_log` table and writer. The remaining work is:

- [ ] A small admin UI or `psql` runbook to query by `request_id` for a
      forensic question ("what did the model retrieve for request X?").
      Take the [docs/SETUP-NEON-POSTGRES.md](SETUP-NEON-POSTGRES.md) approach
      and document the canonical query.
- [ ] A retention policy — AI Act Article 12 expects logs kept for the
      lifetime of the system or as required by EU/national law. Default
      to "keep indefinitely" until the consultant gives a number; the
      table is append-only.
- [ ] A backup of `triage_audit_log` rolled into your Postgres backup
      strategy (Neon does daily snapshots on the free tier; pin a
      retention week explicitly).

## What NOT to do

- **Don't** ship a different language version (English, French) without the
  opinion. Each market multiplies the regulatory surface.
- **Don't** add a feature that names a specific dose ("take 500 mg paracetamol
  every 6 hours"). The current `recommend.ro.j2` template avoids this; keep
  it that way until the regulatory posture is settled.
- **Don't** integrate with electronic health records or pharmacy POS systems
  without explicit MDR coverage. That makes the question impossible to avoid.
- **Don't** rely on the educational disclaimer to neutralize MDR scope. It
  helps but it is not load-bearing.

## Sources

- [MDR 2017/745 — full text (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2017/745/oj)
- [EU AI Act 2024/1689 — full text (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [MDCG 2019-11 — software qualification & classification](https://health.ec.europa.eu/system/files/2020-09/md_mdcg_2019_11_guidance_qualification_classification_software_en_0.pdf)
- [MDR Rule 11 explainer (Notified Body BSI)](https://www.bsigroup.com/en-GB/medical-devices/our-services/Software-as-a-Medical-Device-SaMD/)
- [EU AI Act high-risk timelines (European Parliament)](https://www.europarl.europa.eu/topics/en/article/20230601STO93804/eu-ai-act-first-regulation-on-artificial-intelligence)

## TL;DR for the project owner

The headline numbers in your README are good engineering. They are also
*exactly* what a regulator would point at as evidence of a medical claim.

Action this week: ship the README copy change (item 2). Schedule a paid
30-minute call with a regulatory consultant. Everything else can wait until
they tell you whether you have a Class I, Class IIa, or non-MD situation.
