# Proposed Manual QA Test Plan — Sana.run Trading Terminal

**Candidate:** Gilson Begatti  
**Purpose:** Application work sample  
**Status:** Proposed plan — testing has not started  
**Constraint:** Execution begins only after selection by the sponsor.

## 1. Objective

Evaluate the Sana.run web experience systematically, with emphasis on spot trading, perpetual futures, wallet/onboarding flows, Visa card features, error handling, usability, and clear defect reporting.

## 2. Test approach

- Exploratory testing supported by structured checklists.
- Positive, negative, boundary, interruption, and recovery scenarios.
- Cross-browser and responsive-layout checks where applicable.
- No real-money transaction, deposit, leverage exposure, or irreversible action without explicit sponsor authorization and an approved safe test environment.
- Evidence captured with timestamps, environment details, screenshots or recordings, and reproducible steps.

## 3. Coverage

### Account, wallet, and onboarding
- Registration, login, logout, session expiration, and recovery.
- Wallet connection and disconnection.
- Network mismatch, rejected signature, delayed response, and insufficient balance.
- Clarity of confirmations, warnings, and error messages.

### Spot trading
- Market and limit order interfaces.
- Asset pair selection and price/amount input validation.
- Minimum, maximum, decimal precision, and insufficient-balance boundaries.
- Order confirmation, cancellation, history, and status consistency.
- Prevention of duplicate actions during slow network responses.

### Perpetual futures
- Long/short order flows and leverage controls.
- Margin mode, estimated liquidation price, fees, and risk warnings.
- Reduce-only, stop-loss, take-profit, closing, and cancellation flows.
- Validation of unavailable markets, invalid size, and insufficient collateral.
- Consistency between positions, balances, PnL, and activity history.

### Visa card experience
- Card availability and eligibility messaging.
- Activation, freeze/unfreeze, limits, transaction history, and declined-payment states.
- Privacy masking for card and personal information.
- Clear separation between pending, completed, reversed, and failed transactions.

### UX, accessibility, and resilience
- Mobile and desktop layouts.
- Keyboard navigation, focus visibility, labels, contrast, and actionable errors.
- Loading, empty, offline, timeout, and retry states.
- Refresh, back-navigation, duplicate click, and interrupted-session behavior.

## 4. Sample defect format

**ID:** SANA-QA-001  
**Title:** Concise description of the observed problem  
**Environment:** Browser, version, operating system, viewport, wallet/network  
**Preconditions:** Required account and system state  
**Steps to reproduce:** Numbered, minimal, repeatable steps  
**Expected result:** Correct behavior  
**Actual result:** Observed behavior  
**Frequency:** Always / intermittent, with repetition count  
**Severity:** Critical / high / medium / low  
**Evidence:** Screenshot, recording, console or transaction reference when safe  
**Notes:** User impact, workaround, and related scenarios

## 5. Deliverables

- Prioritized defect log with reproduction steps and evidence.
- Executed test checklist and environment matrix.
- UX observations separated from functional defects.
- End-of-cycle summary covering risks, blockers, and retest status.
- One retest pass for resolved items within the agreed project window.

## 6. Reporting principles

Reports will distinguish verified defects from observations and questions. No vulnerability will be publicly disclosed, and no production-impacting, high-traffic, destructive, or real-funds test will be performed without explicit authorization.
