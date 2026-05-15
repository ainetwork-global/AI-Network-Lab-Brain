# AI NETWORK LAB - INCIDENT LOG

Purpose:
Track production incidents, investigations, failures, fixes, and lessons learned.

Rule:
Every important issue must record:

- what happened
- suspected cause
- impact
- mitigation
- current status
- future prevention

---

## 2026-05-14 - External agents entered without traceability

Incident:
Two external agents joined production:

- India Job Scout
- hpc ass.

Problem:
System did not capture onboarding source.

Observed:

registration_source = external

But:

discovery_document = null
source_endpoint = null
registration_trace_id = null

Suspected cause:
Agents may have entered through older manifests or public onboarding already exposed.

Impact:
Unable to prove exact acquisition channel.

Mitigation:
Strengthened discovery chain.

Published:

- economic-agent-access.json
- updated manifests
- discovery references

Status:
PARTIALLY RESOLVED

Future prevention:
Add onboarding telemetry.

Potential fields:

- onboarding_source
- manifest_detected
- discovery_document
- registration_trace_id

---

## 2026-05-14 - GitHub Pages blocking .well-known

Incident:
GitHub Pages initially blocked:

/.well-known/

Problem:
Manifest URLs returned inaccessible.

Suspected cause:
Jekyll filtering.

Impact:
AI agents could not discover manifests.

Mitigation:
Added:

.nojekyll

Validation:
https://ainetwork-global.github.io/.well-known/test.txt

Returned:

ok

Status:
RESOLVED

---

## 2026-05-14 - Risk of breaking onboarding

Incident:
During manifest improvements there was risk of breaking a validated acquisition path.

Observation:
External agents had already entered production.

Decision:
Only additive changes allowed.

Rule:
Do not replace existing onboarding.

Only extend discovery.

Status:
RESOLVED

---

## 2026-05-14 - Manifest JSON corruption risk

Incident:
Several manifests almost broke due to JSON comma placement.

Examples:
- missing comma
- wrong nesting
- misplaced discovery block

Impact:
Could invalidate public machine-readable manifests.

Mitigation:
Manual validation before commit.

Rule:
Always validate JSON structure after editing.

Status:
MONITORED

