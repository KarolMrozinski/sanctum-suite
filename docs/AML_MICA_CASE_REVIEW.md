# EU CASP AML / MiCA case review

The authenticated Workbench and API provide a case-scoped starter checklist for
the user-selected profile: a CASP operating in the EU, with references to:

- MiCA, Regulation (EU) 2023/1114:
  <https://eur-lex.europa.eu/eli/reg/2023/1114/oj>
- Transfer of Funds Regulation, Regulation (EU) 2023/1113:
  <https://eur-lex.europa.eu/eli/reg/2023/1113/oj>
- EU AMLR, Regulation (EU) 2024/1624:
  <https://eur-lex.europa.eu/eli/reg/2024/1624/oj>
- Polish Act of 1 March 2018 on counteracting money laundering and terrorist
  financing, as amended:
  <https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20180000723>

## API

- `GET /api/v1/cases/{case_id}/aml-mica-checklist`
- `PATCH /api/v1/cases/{case_id}/aml-mica-checklist/{control_id}`
- `POST /api/v1/cases/{case_id}/aml-mica-checklist/{control_id}/evidence`

All records are stored in the same tenant-scoped SQLite database as the case.
The fixed starter controls cover CASP perimeter, service-specific review,
transfer information handling, AMLR applicability/transition planning, Polish
AML scope, and human transaction-monitoring case review. The prompts are
review questions, not a transcription or exhaustive interpretation of the
legislation. Verify each source publication, amendments, commencement,
transitional provisions, national law, and applicability with qualified
counsel and the relevant competent authority.

Each control has an applicability value (`not_assessed`, `in_scope`,
`out_of_scope`, or `needs_legal_review`) and a tracking state (`not_assessed`,
`evidence_recorded`, or `needs_review`). An out-of-scope decision requires a
recorded rationale. `evidence_recorded` requires at least one reference. There
is deliberately no `compliant`, `verified`, or `passed` state. The overall
status always remains `NOT_ASSESSED`; an operator-entered applicability or
evidence reference is not a compliance decision.

Evidence entries store only a source label, reference, caller-supplied
lowercase SHA-256 digest, analyst label (taken from the OIDC identity when
available, otherwise supplied by the caller), and timestamp. Files and
evidence contents are not uploaded. The digest can identify bytes only if
independently recomputed; it does not prove authenticity, sufficiency, legal
relevance, or control effectiveness. Evidence references are append-only and
cascade-delete with their case. A maximum of 100 references is accepted per
control.

This is not legal advice, a complete AML program, a customer due-diligence or
sanctions-screening implementation, a Travel Rule transport, an STR/SAR
decision, or a CASP authorization assessment. On-chain provider data and
Crypto OSINT matches are unverified investigative inputs and do not
automatically populate or satisfy checklist controls. The experimental ZK
policy proof is not bound to this checklist or its evidence.
