# MDD Launch Case: US launch strategy for a second-line depression therapy

A mock consulting engagement built entirely on public US healthcare data. A fictional mid-size biotech, with Phase 3 data due in 2027 for a once-daily pill with a novel, non-serotonin mechanism (for adults whose first antidepressant did not work well enough), asks: **should we launch in the US, at what price, and where do we focus first?**

*Status (October 2026): Workstreams 1-4 complete; Workstream 5 (launch plan and synthesis) next.*

## Findings so far
| Question | Answer |
|---|---|
| Is it worth launching? | Yes: a **$4.3-8.3B** US depression drug market (list prices); add-on spend growing about 13% a year; realistic 8-10% share at maturity (about $340-830M a year), benchmarked against a comparable launch (Auvelity) |
| Where is the value? | Branded second-line add-ons: 82% of add-on spend, branded fills growing 18% a year (volume, not price) |
| Who competes? | 7,393 trials narrow to about 12 realistic new US competitors. The client is the only non-antipsychotic add-on at launch, for about a year before osavampator; Caplyta (J&J) is already strong in the launch region |
| Where first? | Six connected states (TN, KY, IN, OH, MI, WI): 9.3M patients, about 16% of the US |
| At what price? | About $940 a month by default, just below Medicare's about $950 specialty-tier line (about $299M year-2 net revenue on a national basis); move to $1,350 (about $416M nationally) only if Phase 3 proves better tolerability. The client keeps about 57% of list price after rebates and discounts. The premium only loses if insurer pushback costs it 28%+ of patients, the one assumption that can flip the decision |
| How do patients get access? | Every Medicare plan covers the competitor brands (protected class), but hurdles follow price and role, and Michigan and Kentucky insurers add the most. Win on pre-approval support (hub + field reimbursement managers), not copay: competitors match on $0-10 cards but leave pre-approval to the doctor |
| Which prescribers? | 7,347 prescribers (14% of 53,642 in the six states) write 98% of competitor-brand fills, mostly nurse practitioners and psychiatrists; 1,147 (about 2%) write half. About 59 reps (about $12M a year) cover them; the six-state launch earns about $68-86M in year 2, with a checkpoint at 6-9 months |
| How to launch? | Be commercially ready before approval; build the prescriber network early; plan for a commercial insurance lag of about 6 months; lead with "the add-on benefit without adding an antipsychotic" |

## Workstreams
1. **Market sizing** (`notebooks/02_market_sizing.ipynb`): CDC PLACES, CMS Part D and Medicaid spending, MEPS 2024; triangulation of the national market, depression share of use, growth, launch analogs, state ranking.
2. **Competitive landscape** (`notebooks/03_competitive_landscape.ipynb`): ClinicalTrials.gov API funnel, Phase 3 research, timeline, focus competitors, Caplyta index by state, non-drug alternatives, lessons from recent launches.
3. **Pricing and access** (`notebooks/04_pricing_access.ipynb`): competitor price per month, Medicare negotiated prices, coverage and hurdles across 804 Medicare plans in the launch states, gross-to-net assumptions, net revenue by price scenario with break-even and sensitivity analysis, patient support package.
4. **Prescriber targeting** (`notebooks/05_prescriber_targeting.ipynb`): CMS Part D prescriber x drug data for the six states; who writes competitor brands by specialty, four target groups, A/B/C tiers with a concentration curve (H4), an adoption check on the newest brand, targets by state, sales-force size and cost, and six-state revenue.
5. Launch plan and synthesis (next).

## Data (all public)
CMS Medicare Part D (by geography, by prescriber, spending by drug), CMS Medicare negotiated prices, CMS Part D formulary file, CMS Medicaid spending by drug, MEPS (AHRQ), CDC PLACES, Census population estimates, ClinicalTrials.gov, company disclosures, FDA announcements and published research (MedPAC, MACPAC, IQVIA, Drug Channels). Raw files are not committed; `scripts/01_download_data.py` re-downloads them and logs every download.

## Run
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/01_download_data.py monday   # market-sizing inputs
python3 scripts/01_download_data.py big      # Part D prescriber x drug (large)
python3 scripts/01_download_data.py payers   # Medicaid and MEPS
python3 scripts/01_download_data.py meps2024
python3 scripts/01_download_data.py places2024
python3 scripts/01_download_data.py trials   # ClinicalTrials.gov
python3 scripts/01_download_data.py pricing  # Workstream 3 inputs
```
Then run the notebooks in `notebooks/` from top to bottom.

## Structure
- `scripts/` acquisition (`01_download_data.py`) and drug classification (`drug_classes.py`)
- `notebooks/` analysis by workstream
- `data/processed/` small derived tables
- `outputs/` charts (matplotlib)

*The client is fictional. Figures are list prices before rebates and rely on public, largely Medicare data; see each notebook for methods and limitations.*
