# TimberLine Issue 70 — Payment and Feasibility Validation

## Decisão

**TECHNICALLY_AND_ECONOMICALLY_ELIGIBLE**

## Issue

- Repository: $Repo
- Issue: #70
- Title: Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture
- State: $(@{assignees=System.Object[]; author=; body=## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout; closedAt=; comments=System.Object[]; createdAt=2026-07-16T17:42:58Z; labels=System.Object[]; milestone=; number=70; state=OPEN; stateReason=; title=Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture; updatedAt=2026-07-16T18:19:02Z; url=https://github.com/johncollinsgit/TimberLine/issues/70}.state)
- State reason: $(@{assignees=System.Object[]; author=; body=## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout; closedAt=; comments=System.Object[]; createdAt=2026-07-16T17:42:58Z; labels=System.Object[]; milestone=; number=70; state=OPEN; stateReason=; title=Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture; updatedAt=2026-07-16T18:19:02Z; url=https://github.com/johncollinsgit/TimberLine/issues/70}.stateReason)
- URL: https://github.com/johncollinsgit/TimberLine/issues/70
- Author: $(@{assignees=System.Object[]; author=; body=## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout; closedAt=; comments=System.Object[]; createdAt=2026-07-16T17:42:58Z; labels=System.Object[]; milestone=; number=70; state=OPEN; stateReason=; title=Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture; updatedAt=2026-07-16T18:19:02Z; url=https://github.com/johncollinsgit/TimberLine/issues/70}.author.login)
- Assignees: Nenhum
- Labels: Nenhum
- Created: $(@{assignees=System.Object[]; author=; body=## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout; closedAt=; comments=System.Object[]; createdAt=2026-07-16T17:42:58Z; labels=System.Object[]; milestone=; number=70; state=OPEN; stateReason=; title=Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture; updatedAt=2026-07-16T18:19:02Z; url=https://github.com/johncollinsgit/TimberLine/issues/70}.createdAt)
- Updated: $(@{assignees=System.Object[]; author=; body=## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout; closedAt=; comments=System.Object[]; createdAt=2026-07-16T17:42:58Z; labels=System.Object[]; milestone=; number=70; state=OPEN; stateReason=; title=Front Yard Foods launch partner: proposal, agreements, recurring billing, and Shopify/Square architecture; updatedAt=2026-07-16T18:19:02Z; url=https://github.com/johncollinsgit/TimberLine/issues/70}.updatedAt)
- Comments: $( .Count)

## Reward evidence

USD/Token value detected: 299
USD/Token value detected: 149
USD/Token value detected: 90
USD/Token value detected: 59
USD/Token value detected: 50
USD/Token value detected: 39
USD/Token value detected: 29

Detected payment terms: $PaymentTermText

## Competition

- Attempt/claim comments: $(.Count)
- Explicit claim/PR comments: $(.Count)
- Related pull requests found: $(.Count)

### Attempts

Nenhum comentário de tentativa ou reivindicação detectado.

### Related pull requests

Nenhum PR relacionado encontrado pela busca.

## Repository

- Description: Production Management System
- Archived: $(@{createdAt=2026-01-31T19:07:01Z; defaultBranchRef=; description=Production Management System; isArchived=False; isFork=False; issues=; licenseInfo=; nameWithOwner=johncollinsgit/TimberLine; primaryLanguage=; pullRequests=; updatedAt=2026-07-18T21:16:25Z; url=https://github.com/johncollinsgit/TimberLine}.isArchived)
- Fork: $(@{createdAt=2026-01-31T19:07:01Z; defaultBranchRef=; description=Production Management System; isArchived=False; isFork=False; issues=; licenseInfo=; nameWithOwner=johncollinsgit/TimberLine; primaryLanguage=; pullRequests=; updatedAt=2026-07-18T21:16:25Z; url=https://github.com/johncollinsgit/TimberLine}.isFork)
- Primary language: $(@{createdAt=2026-01-31T19:07:01Z; defaultBranchRef=; description=Production Management System; isArchived=False; isFork=False; issues=; licenseInfo=; nameWithOwner=johncollinsgit/TimberLine; primaryLanguage=; pullRequests=; updatedAt=2026-07-18T21:16:25Z; url=https://github.com/johncollinsgit/TimberLine}.primaryLanguage.name)
- Updated: $(@{createdAt=2026-01-31T19:07:01Z; defaultBranchRef=; description=Production Management System; isArchived=False; isFork=False; issues=; licenseInfo=; nameWithOwner=johncollinsgit/TimberLine; primaryLanguage=; pullRequests=; updatedAt=2026-07-18T21:16:25Z; url=https://github.com/johncollinsgit/TimberLine}.updatedAt)
- Default branch: $(@{createdAt=2026-01-31T19:07:01Z; defaultBranchRef=; description=Production Management System; isArchived=False; isFork=False; issues=; licenseInfo=; nameWithOwner=johncollinsgit/TimberLine; primaryLanguage=; pullRequests=; updatedAt=2026-07-18T21:16:25Z; url=https://github.com/johncollinsgit/TimberLine}.defaultBranchRef.name)
- Local branch: $GitBranch
- Local commit: $GitCommit
- Origin: $GitRemote

## Relevant project files

- $(@{Path=AGENTS.md; Length=2581}.Path) — 2581 bytes
- $(@{Path=README.md; Length=141936}.Path) — 141936 bytes
- $(@{Path=package.json; Length=1731}.Path) — 1731 bytes

## Positive evidence

- A issue está aberta.
- O repositório não está arquivado.
- Há valor monetário explícito no conteúdo da issue ou comentários.
- Há sinal explícito de plataforma ou pagamento.
- Nenhum PR concorrente foi encontrado.
- A concorrência observável não ultrapassa três tentativas.

## Blocking evidence

- Nenhum bloqueio identificado.

## Complete issue body

## Goal
Create the commercial, agreement, billing-readiness, and implementation foundation needed to move Front Yard Foods LLC from Squarespace to Shopify as an Everbranch Launch Partner.

This must extend the existing `front-yard-foods` tenant and reusable Front Yard Foods scheduling work. Do not create a parallel tenant-specific application or duplicate class/customer/job systems.

## Core architecture decision

### Shopify owns the public commerce layer
Shopify should be the source of truth for:
- Product catalog and variants
- Sellable inventory quantities
- Retail and wholesale checkout/order entry
- Porch pickup
- Local delivery and delivery fees
- Future-market pickup selection
- Plant and plug preorders
- Paid class registration
- Paid garden consultation checkout
- Public customer accounts
- Front Yard Academy purchase/access entry point

### Everbranch owns the operating layer
Everbranch should be the operational workspace and unified internal view for:
- Canonical customer identity across Shopify and Square
- Normalized Shopify and Square order history
- Inventory cost and purchased-resale plant lot tracking
- Inventory holds/reservations such as holding strawberries for a customer
- Available-to-promise quantity
- Wholesale workflow and follow-up
- Class scheduling, enrollments, reminders, and capacity
- Garden consultations and associated jobs/tasks/files
- Grant application tracking
- Reporting and operator alerts
- Agreement, scope, pricing, signature, subscription, and termination records

### Square integration rule
- Shopify is the canonical catalog and inventory system.
- Publish/map products from Shopify to Square.
- Square inventory/sale changes must decrement Shopify inventory through an idempotent Everbranch integration.
- Do not copy Square orders into Shopify.
- Everbranch may ingest and normalize Square orders/customers for the unified internal customer and order view.
- Prevent sync loops and duplicate inventory adjustments with provider event IDs, mapping records, cursors, and reconciliation jobs.

## Workstream 1: Proposal and user agreements
Build a reusable commercial proposal/agreement system.

### Public proposal surface
- Host-lock a password-protected proposal route to the Evergrove website domain.
- Example route: `/proposals/{public_token}`.
- Use a cryptographically random public token and a separately hashed password.
- Add throttling, expiry support, viewed timestamps, and audit events.
- Proposal must have a simple client-facing matrix:
  - Thing you want done
  - Software/surface that will do it
  - Included scope
  - Price/fee owner
  - Notes/limitations

### Landlord surfaces
- Tenant agreement list under `/landlord/tenants/{tenant}/agreements`.
- Agreement detail, version history, status, scope, pricing, acceptance evidence, termination status, exports, and internal notes.
- Add a landlord-wide agreement queue/filter page.

### Tenant/user surfaces
- Add a User Agreements section where authorized tenant users can see accepted agreements and current terms.
- Accepted agreements must be read-only and downloadable.

### Suggested data model
Use naming consistent with current commercial conventions, but support at least:
- agreements/proposals
- immutable agreement versions
- scope line items
- pricing line items
- acceptance/signature evidence
- agreement events/audit trail
- termination records

Store:
- tenant_id
- agreement type
- status: draft, sent, viewed, accepted, declined, expired, active, termination_pending, terminated
- public token
- password hash
- version number and content hash
- scope JSON or normalized line items
- pricing JSON or normalized line items
- effective date
- subscription terms
- termination terms
- accepted name, email, title, timestamp, IP, user agent, and authenticated user when available
- immutable rendered snapshot/PDF path after acceptance

### Signature behavior
- Typed legal name
- Title/role
- Email
- Required agreement checkbox
- Explicit acknowledgement that the signer is authorized to bind Front Yard Foods LLC
- Timestamp and evidence log
- No editing after acceptance; amendments require a new version or addendum

## Workstream 2: Recurring subscriptions
Treat recurring subscriptions as two separate domains.

### Everbranch SaaS subscription
Front Yard Foods is expected to be a Shopify-connected/App Store merchant. Use the Shopify-provided app pricing/billing lane, not Stripe direct billing.

Launch Partner commercial terms:
- $299 onboarding
- $59/month for the first 6 billing cycles
- $149/month after the promotional period

Investigate and document the safest Shopify App Pricing implementation. Preferred model to validate:
- Standard $149 recurring plan
- Merchant-specific/private Launch Partner access or a $90 discount for six billing cycles
- Shopify remains the billing source of truth
- Everbranch stores a read-only normalized subscription mirror and commercial audit history

Do not activate legacy/manual billing paths just to make the promotion work. Use the current Shopify Partner API subscription state and billing event model. Keep Stripe direct billing separate and disabled unless a future approved lane-specific PR activates it.

Create or extend a provider-neutral subscription record that can represent:
- shopify_app_pricing
- stripe_direct
- manual_invoice
- comped/internal

Track:
- provider subscription ID/plan handle
- billing status
- billing period
- promotional cycles remaining/end date
- cancellation scheduled/effective date
- last reconciled timestamp
- source event IDs
- agreement version that authorized billing

Billing activation must require:
1. Accepted agreement
2. Approved billing lane
3. Verified provider subscription state
4. Audited entitlement fulfillment

## Workstream 3: Website versus Everbranch placement
Add an architecture decision document and store the surface decision on proposal scope line items.

Use these defaults:
- Public pages, products, checkout, pickup, delivery, and public account: Shopify
- Internal workflow, unified customer/order context, costs, reservations, tasks, reporting, and agreements: Everbranch
- Paid class/consultation checkout: Shopify
- Class schedule/capacity/enrollment operations: Everbranch
- Academy storefront/access purchase: Shopify/course app initially
- Academy entitlement mirror and customer context: Everbranch
- Newsletter publishing: Substack initially
- Newsletter consent/source/customer context: Everbranch

Do not build a full LMS, general-purpose booking platform, or public checkout inside Everbranch when Shopify or an established Shopify app already handles the public transaction safely.

## Workstream 4: Inventory, wholesale, preorders, and reservations
Audit existing Shopify/Square/inventory tables and services before adding new ones.

Required capabilities:
- Shopify variant to Square catalog variation mapping
- Shopify-to-Square catalog publish/update queue
- Square inventory webhook ingestion
- Idempotent Shopify inventory adjustment
- Reconciliation command and landlord diagnostics
- No order replication from Square into Shopify
- Normalized Square order/customer mirror in Everbranch
- Purchased plant lots with vendor, quantity, total cost, unit cost, received date, and notes
- Weighted-average and/or lot-aware cost reporting
- Inventory reservations/holds with customer, variant, quantity, reason, expiry, status, and source
- Available-to-promise calculation
- Preorder windows, caps, expected availability, and fulfillment dates
- Wholesale allocation/reservation behavior
- Audit trail for every inventory adjustment and hold release

Strawberry use case:
- Staff can hold a quantity for a customer.
- Hold immediately lowers available-to-promise.
- Hold has an expiry or explicit no-expiry override.
- Release or conversion to paid order is audited.
- System must prevent negative available-to-promise unless an intentional preorder rule permits it.

## Workstream 5: Classes, consultations, academy, newsletter, and app
Reuse the existing Front Yard Foods class scheduling, public signup, consultation/job, messaging, reminder, and mobile work.

### Paid classes
- Shopify product/booking checkout handles payment.
- Shopify paid-order webhook creates or confirms the Everbranch enrollment idempotently.
- Free classes may continue using the existing public signup flow.
- Capacity must still be enforced server-side.

### Garden consultations
- Public booking/checkout lives in Shopify with a booking/calendar integration.
- Support in-person and Zoom/Google Meet style appointments.
- Calendar availability and blocked times must be respected.
- Everbranch receives the booking and creates/updates the customer, consultation, job/task, notes, and follow-up state.

### Front Yard Academy
Start with Shopify customer accounts plus a Shopify course/membership app unless discovery proves that Everbranch-specific academy functionality is required.
- Mirror purchase/access status into Everbranch.
- Do not build an LMS in Everbranch in this PR.

### Newsletter: Rooting In with Laura
- Use Substack as the initial publishing/newsletter surface.
- Add the newsletter link/signup presentation to Shopify.
- Store consent/source/customer relationship metadata in Everbranch where legally and technically appropriate.
- Do not duplicate the writing/publishing editor inside Everbranch.

### Mobile app/App Store
Decide and document whether this is:
1. The shared Everbranch app with tenant-specific access, or
2. A separate Front Yard Foods white-label app listing.

Preferred default: shared Everbranch app, unless the client agreement explicitly purchases a separate white-label listing.

Termination behavior differs:
- Shared app: disable Front Yard Foods workspace access and tenant-specific features; do not remove the global Everbranch app from the App Store.
- Separate white-label app: delist the Front Yard Foods app and disable its APIs/features according to the agreement.

## Workstream 6: Termination lifecycle
Agreement must clearly separate client-owned assets from licensed Everbranch functionality.

On termination:
- Shopify store, domain, client content, and client-owned product data remain with the client.
- Everbranch access, custom modules, integrations, sync jobs, APIs, and tenant-specific mobile functionality are disabled on the effective termination date.
- Square/Shopify inventory synchronization stops.
- Shared Everbranch mobile app access is revoked for the tenant.
- A separate white-label Front Yard Foods app may be delisted.
- Provide a defined data export window, recommended 30 days.
- Third-party subscriptions remain the client's responsibility unless the agreement explicitly says Evergrove manages cancellation.
- Preserve required billing, acceptance, audit, and legal records after operational data deletion.

Add termination states, effective dates, export tracking, deactivation jobs, operator checklist, and tests. Do not automatically delete tenant data immediately on cancellation.

## Proposal pricing rules
The proposal must distinguish:
1. Everbranch Launch Partner subscription fees
2. One-time Shopify migration/implementation fees
3. Optional custom integration/app work
4. Third-party vendor fees paid directly by the client

Do not imply that the $299 onboarding fee automatically includes an unlimited Squarespace-to-Shopify migration, full catalog entry, custom Square inventory integration, course setup, booking setup, and mobile app publication. These must be explicit scope line items with agreed prices, even if discounted or waived for the pilot.

## Required tests
- Landlord-only agreement administration
- Public token/password access and throttling
- Cross-tenant denial
- Immutable accepted version
- Signature evidence capture
- Agreement-required billing activation guard
- Provider subscription reconciliation idempotency
- Shopify lane cannot call Stripe checkout
- Square webhook replay/idempotency
- Inventory sync loop prevention
- Reservation capacity and negative-availability prevention
- Paid class webhook enrollment idempotency
- Termination deactivates tenant capabilities without deleting client-owned Shopify data
- Shared-app versus white-label app termination behavior

## Documentation updates
Update:
- `SYSTEM_SNAPSHOT.md`
- `README_FOR_AGENTS.md`
- relevant readiness/billing/commercial docs
- Front Yard Foods runbook
- route/page ownership inventory
- UI changelog for every UI-affecting change

## Delivery approach
Implement in small PRs rather than one large PR:
1. Architecture decision + proposal/agreement data model and landlord/public surfaces
2. Signature/versioning/export/termination lifecycle
3. Subscription provider mirror and Shopify App Pricing readiness
4. Inventory mapping, webhook ingestion, and reconciliation
5. Reservations/cost lots/preorders/wholesale allocation
6. Shopify paid class and consultation handoffs
7. Academy/newsletter/mobile surface decisions and final tenant rollout
