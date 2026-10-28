# Pool Geek Marketing Department

This repo holds the role definitions and operating model for a marketing department staffed by
AI agents. It is also where those agents are managed so they keep moving in the right direction.

## Goal

Success is measured in **gross profit growth in 2027**:

- **E-commerce: +$1,000,000 GP**
- **Service: +$300,000 GP**

Targets, the starting split by role, and the counting rules are in
[`goals/2027-gross-profit-targets.md`](goals/2027-gross-profit-targets.md).

## Org chart

```
                         Human owner
                              │
                     Marketing Director (orchestrator)
                              │
     ┌────────────────────────┼─────────────────────────────┐
  Marketing Analytics      E-commerce                      Service
  (scorekeeper; reports    │                               │
   to Director, serves     ├─ Product Development (live)   └─ Local Service Growth
   every agent)            ├─ Pricing
                           ├─ PPC (paid search & shopping)    Shared by both lines:
                           ├─ Amazon Marketplace              └─ Email & Lifecycle
                           ├─ SEO & Content
                           └─ CRO & Merchandising
```

## Roles

| # | Role | Line | Main gross profit lever | Phase |
|---|---|---|---|---|
| 00 | [Marketing Director](roles/00-marketing-director.md) | Both | Priorities, budget, conflict resolution | 1 |
| 01 | [Product Development Specialist](roles/01-product-development-specialist.md) | E-com | New manufacturer catalogs live and selling | **Live** |
| 02 | [Pricing Specialist](roles/02-pricing-specialist.md) | E-com | Margin rate, MAP compliance, vendor rebates and co-op funds | 1 |
| 03 | [PPC Specialist](roles/03-ppc-specialist.md) | E-com | Paid search and shopping, bid toward profit | 1 |
| 04 | [Amazon Marketplace Specialist](roles/04-amazon-marketplace-specialist.md) | E-com | Marketplace GP after fees | 2 |
| 05 | [Local Service Growth Specialist](roles/05-local-service-growth-specialist.md) | Service | Booked jobs from local search, Local Services Ads, reviews | 1 |
| 06 | [Email & Lifecycle Specialist](roles/06-email-lifecycle-specialist.md) | Both | Repeat orders, replenishment, cross-selling between the two lines | 2 |
| 07 | [SEO & Content Specialist](roles/07-seo-content-specialist.md) | E-com | Organic traffic (pays off mostly in 2028) | 2 |
| 08 | [CRO & Merchandising Specialist](roles/08-cro-merchandising-specialist.md) | E-com | Conversion rate, order size, margin mix | 3 |
| 09 | [Marketing Analytics Specialist](roles/09-marketing-analytics-specialist.md) | Both | GP measurement and the weekly scorecard | 1 |

New roles start from [`roles/_TEMPLATE.md`](roles/_TEMPLATE.md).

## Design principles

1. **Every role owns a gross profit number, or measures one.** Agents are steered on GP, never on
   revenue, clicks or ROAS alone. Paid channels report GP *after* ad spend.
2. **One owner per lever.** Each role page has an "Owns" and a "Does not own" section. If two
   pages claim the same thing, that's a bug to fix here.
3. **The scorekeeper is separate from the players.** Analytics produces every number. No agent
   reports its own results to the Director.
4. **Service and e-commerce budgets are kept apart.** Service gets its own growth role and ad
   budget so the $300K service goal isn't crowded out by e-commerce spend.
5. **Guardrails before autonomy.** Every role lists what it can do alone, what needs Director
   approval, and what needs a human. Spend caps, price floors and MAP rules are enforced, not
   suggested.

## Rollout order

Pool season peaks in spring and summer, so the order is set by what has to be working before
**March 2027**:

- **Phase 1 (now through January 2027):** Analytics, Director, Pricing, PPC, Local Service Growth.
  These are measurement, control, and the two biggest paid levers.
- **Phase 2 (Q1 2027):** Amazon, Email & Lifecycle, SEO & Content.
- **Phase 3 (Q2 2027):** CRO & Merchandising, once traffic and tracking support real tests.

## Operating rhythm

| When | What | Owner |
|---|---|---|
| Daily | Spend pacing, MAP and price scan, tracking and lead alerts | Each specialist, Analytics |
| Weekly | Scorecard: GP vs. paced target by line and role | Analytics |
| Weekly | Priorities, budget moves, brief to the human owner | Director |
| Monthly | Business review, recalibrating targets per role | Director + human owner |
| Quarterly | Plan reset, add or retire roles | Human owner |

## Open questions for the human owner

1. What is the 2026 GP baseline for each line, and where does COGS data live?
2. What is the total 2027 marketing budget, and how should it start out split between e-commerce
   and service?
3. Which platforms are in use (ecommerce platform, email/SMS, field service and CRM)?
4. Is Pool Geek already selling on Amazon? Are there manufacturer restrictions on marketplaces?
5. Should Pricing also own service pricing, or does that stay with service operations?
6. What is the service area, and how many jobs can the service team take on at peak?
