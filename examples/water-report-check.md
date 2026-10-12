# Source check of water-report-answer.md

This is what the skill returned for the planted summary in
`water-report-answer.md`, checked against `water-report.pdf`. Both files are
fictional and made for trying the skill.

**Source check: 11 claims. 6 supported, 3 contradicted, 2 not in source.**
Source: water-report.pdf (3 pages). Answer: water-report-answer.md.

| # | Claim | Verdict | Page | Evidence (quoted from the source) | Note |
|---|---|---|---|---|---|
| 1 | "demand reached 42.9 million gallons in September, seasonally adjusted" | ❌ Contradicted | 2 | "Before seasonal adjustment, September demand was 42.9 million gallons" | 42.9 is the unadjusted figure. Seasonally adjusted: 41.2. |
| 2 | "up 3.5% from August" | ✅ Supported | 2 | "41.2 million gallons in September 2026, seasonally adjusted, up from 39.8 million gallons in August" | 41.2 / 39.8 = +3.5%. True for the adjusted figures, not for 42.9 (+7.8%). |
| 3 | "Residential customers used 22.9 million gallons a day" | ✅ Supported | 3 | "Residential ... 22.4 22.9" (Table 2) | Seasonally adjusted, September |
| 4 | "the largest share of the total" | ✅ Supported | 3 | "Residential 22.4 22.9 ... Commercial 11.0 11.3 ... Industrial 6.4 7.0" (Table 2) | 22.9 of 41.2, against 11.3 and 7.0 |
| 5 | "Industrial use rose to 7.0 million gallons a day" | ✅ Supported | 3 | "Industrial 6.4 7.0" (Table 2) | Seasonally adjusted, September |
| 6 | "from 6.4 million in August" | ✅ Supported | 3 | "Aug. 2026 Sept. 2026 ... Industrial 6.4" (Table 2) | |
| 7 | "The Board raised the base rate to $4.25 per 1,000 gallons" | ❌ Contradicted | 2 | "The Board left the base rate at $4.15 per 1,000 gallons." | Not raised, and $4.15, not $4.25 |
| 8 | "Director Ana Ruiz said no rate change is expected before the spring review" | ✅ Supported | 2 | "“We expect no rate change before the spring review,” said Director Ana Ruiz." | |
| 9 | "The Authority expects demand to ease in October" | ⚠️ Not in source | 2 | "The Authority does not publish demand forecasts in this report." | Searched: forecast, expect, October |
| 10 | "as temperatures fall" | ⚠️ Not in source | none | none | Searched: temperature, weather, heat |
| 11 | "September figures are final" | ❌ Contradicted | 3 | "Figures for September are preliminary." | |

`check_quotes.py`: 11 claims, 10 PASS, 1 OK.

**What to fix**
- #1: "41.2 million gallons a day, seasonally adjusted" (p. 2), or keep 42.9 and say "before seasonal adjustment".
- #7: the Board left the base rate at $4.15 per 1,000 gallons (p. 2).
- #9 and #10: remove; the report has no demand forecast (p. 2).
- #11: September figures are preliminary (p. 3).
