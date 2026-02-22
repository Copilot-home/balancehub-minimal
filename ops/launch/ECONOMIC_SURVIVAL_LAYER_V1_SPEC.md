# Economic Survival Layer v1 (Canonical Spec)

Status: `DRAFT-READY-TO-IMPLEMENT`
Owner: `BalanceHub Runtime`
Version: `v1`

## 1. Scope
This spec defines the production contract for:
- `GET /system/economics`
- `GET /system/sustainability`

Constraints:
- Keep Free core untouched
- No new connector/axis behavior
- Economic layer is additive only

## 2. Canonical Formulas
All monetary values are monthly USD unless explicitly stated.

- `C_base = SUM(node monthly_cost)`
- `C_shared = SUM(shared monthly_cost)`
- `C_infra = C_base + C_shared`
- `Revenue_actual = SUM(revenue monthly_amount)`
- `CoverageRatio = Revenue_actual / C_infra` when `C_infra > 0`, else `0`
- `BreakEvenGap = max(0, C_infra - Revenue_actual)`
- `BurnRate = max(0, C_infra - Revenue_actual)`
- `RunwayMonths = INF if BurnRate == 0 else CashReserve / BurnRate`
- `SustainabilityIndex = min(1, max(0, CoverageRatio))`

Rounding policy:
- Money fields: 2 decimals
- Ratios/index: 4 decimals
- Runway: 2 decimals

## 3. Data Schema
## 3.1 Required table: `economic_costs`
Use this table as the single source for node costs, shared costs, and revenue entries.

```sql
CREATE TABLE IF NOT EXISTS economic_costs (
  id UUID PRIMARY KEY,
  entry_type VARCHAR(16) NOT NULL,
  -- enum-like constraint in app layer: NODE_COST | SHARED_COST | REVENUE
  name VARCHAR(128) NOT NULL,
  node_name VARCHAR(128) NULL,
  monthly_amount NUMERIC(12,2) NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'USD',
  effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  effective_to TIMESTAMPTZ NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_economic_costs_type_active
  ON economic_costs(entry_type, is_active);

CREATE INDEX IF NOT EXISTS idx_economic_costs_node_name
  ON economic_costs(node_name);
```

Validation rules:
- `monthly_amount >= 0`
- `currency` must be `USD` for v1
- For `NODE_COST`, `node_name` is required
- For `SHARED_COST` and `REVENUE`, `node_name` is null
- Inactive or expired rows (`effective_to < now`) are excluded from computation

## 3.2 Runtime config input
- `CASH_RESERVE_USD` (required for runway endpoint, default `0`)
- Optional fallback values are allowed when DB has no rows (for bootstrap only)

## 4. API Contracts
## 4.1 `GET /system/economics`
Response:

```json
{
  "C_base": 200.0,
  "C_shared": 75.0,
  "C_infra": 275.0,
  "Revenue_actual": 80.0,
  "CoverageRatio": 0.2909,
  "BreakEvenGap": 195.0,
  "currency": "USD",
  "generated_at": "2026-02-22T09:00:00Z",
  "components": {
    "node_costs": [{"name":"Stripe","monthly_cost":15.0}],
    "shared_costs": [{"name":"Domain","monthly_cost":20.0}],
    "revenue_streams": [{"name":"Sponsors","monthly_amount":50.0}]
  }
}
```

## 4.2 `GET /system/sustainability`
Response:

```json
{
  "runway_months": 3.08,
  "sustainability_index": 0.2909,
  "status": "AT_RISK",
  "coverage_ratio": 0.2909,
  "burn_rate": 195.0,
  "kill_switch_recommendation": "REDUCE_NODE_FOOTPRINT",
  "policy_flags": {
    "freeze_growth_marketing": true,
    "disable_experimental_nodes": true,
    "downgrade_compute_tier": true
  },
  "generated_at": "2026-02-22T09:00:00Z"
}
```

## 5. Rule Engine (v1)
Status mapping from `CoverageRatio`:
- `>= 1.0`: `SUSTAINABLE`
- `>= 0.6 and < 1.0`: `STABLE_BUT_SUBSIDIZED`
- `>= 0.3 and < 0.6`: `AT_RISK`
- `< 0.3`: `CRITICAL`

Escalation rules:
- If `CoverageRatio < 0.3`:
  - `freeze_growth_marketing = true`
  - `reduce_infra_immediately = true`
- If `CoverageRatio < 0.6` for `8 consecutive weeks`:
  - `downgrade_compute_tier = true`
  - `disable_experimental_nodes = true`
- If `CoverageRatio >= 1.0`:
  - `reinvest_for_expansion = true`

Note for v1 implementation:
- `8 consecutive weeks` requires weekly snapshots.
- If history is unavailable, return recommendation based on current ratio and set `history_confidence = "LOW"`.

## 6. Pseudo-code (Production-oriented)
```python
# app/services/economics_service.py

def list_active_entries(db, now_utc):
    rows = query economic_costs where is_active=true
      and effective_from <= now_utc
      and (effective_to is null or effective_to >= now_utc)
    return rows


def aggregate_monthly(rows):
    node_costs = [r for r in rows if r.entry_type == "NODE_COST"]
    shared_costs = [r for r in rows if r.entry_type == "SHARED_COST"]
    revenues = [r for r in rows if r.entry_type == "REVENUE"]

    C_base = sum(r.monthly_amount for r in node_costs)
    C_shared = sum(r.monthly_amount for r in shared_costs)
    C_infra = C_base + C_shared
    Revenue_actual = sum(r.monthly_amount for r in revenues)

    coverage = (Revenue_actual / C_infra) if C_infra > 0 else 0
    gap = max(0, C_infra - Revenue_actual)

    return {
      "C_base": round(C_base, 2),
      "C_shared": round(C_shared, 2),
      "C_infra": round(C_infra, 2),
      "Revenue_actual": round(Revenue_actual, 2),
      "CoverageRatio": round(coverage, 4),
      "BreakEvenGap": round(gap, 2),
      "node_costs": node_costs,
      "shared_costs": shared_costs,
      "revenues": revenues,
    }


def sustainability_from_economics(economics, cash_reserve_usd, weekly_coverage_history):
    coverage = economics["CoverageRatio"]
    burn_rate = max(0, economics["C_infra"] - economics["Revenue_actual"])

    if burn_rate == 0:
        runway = float("inf")
    else:
        runway = cash_reserve_usd / burn_rate

    if coverage >= 1.0:
        status = "SUSTAINABLE"
    elif coverage >= 0.6:
        status = "STABLE_BUT_SUBSIDIZED"
    elif coverage >= 0.3:
        status = "AT_RISK"
    else:
        status = "CRITICAL"

    flags = {
      "freeze_growth_marketing": coverage < 0.3,
      "disable_experimental_nodes": False,
      "downgrade_compute_tier": False,
      "reinvest_for_expansion": coverage >= 1.0,
    }

    if has_8_consecutive_weeks_below(weekly_coverage_history, 0.6):
        flags["disable_experimental_nodes"] = True
        flags["downgrade_compute_tier"] = True

    recommendation = derive_recommendation(flags)

    return {
      "runway_months": round(runway, 2) if runway != float("inf") else "INF",
      "sustainability_index": round(min(1, max(0, coverage)), 4),
      "status": status,
      "coverage_ratio": round(coverage, 4),
      "burn_rate": round(burn_rate, 2),
      "kill_switch_recommendation": recommendation,
      "policy_flags": flags,
    }
```

## 7. Implementation Mapping (No Drift)
- Model file: `app/core/models.py` (`EconomicCost`)
- Service file: `app/services/economics_service.py`
- Endpoints: `app/main.py`
  - `GET /system/economics`
  - `GET /system/sustainability`
- Metrics extension (optional v1.1):
  - `balancehub_coverage_ratio`
  - `balancehub_burn_rate_usd`
  - `balancehub_runway_months`

## 8. Acceptance Criteria
- API contracts match this spec exactly (field names + rounding)
- Empty DB returns valid zeros, never 500
- Negative amounts are rejected at write-time
- Currency mismatch is rejected for v1
- Runway returns `INF` when burn rate is zero
