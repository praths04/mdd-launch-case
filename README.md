# MDD Launch Case: US launch strategy for a second-line depression therapy

A mock consulting engagement built entirely on public US healthcare data. A fictional mid-size biotech, with Phase 3 data due in 2027 for a once-daily pill with a novel, non-serotonin mechanism (for adults whose first antidepressant did not work well enough), asks: **should we launch in the US, at what price, and where do we focus first?**

*Status (October 2026): Workstreams 1-2 complete; Workstream 3 in progress.*

## Findings so far
| Question | Answer |
|---|---|
| Is it worth launching? | Yes: a **$4.3-8.3B** US depression drug market (list prices); add-on spend growing ~13% a year; realistic 8-10% share at maturity (~$340-830M a year), benchmarked against a comparable launch (Auvelity) |
| Where is the value? | Branded second-line add-ons: 82% of add-on spend, branded fills growing 18% a year (volume, not price) |
| Who competes? | 7,393 trials narrow to ~12 realistic new US competitors. The client is the only non-antipsychotic add-on at launch, for about a year before osavampator; Caplyta (J&J) is already strong in the launch region |
| Where first? | Six connected states (TN, KY, IN, OH, MI, WI): 9.3M patients, ~16% of the US |
| How to launch? | Be commercially ready before approval; build the prescriber network early; plan for a ~6-month commercial insurance lag; lead with "the add-on benefit without adding an antipsychotic" |

## Workstreams
1. **Market sizing** (`notebooks/02_market_sizing.ipynb`): CDC PLACES, CMS Part D and Medicaid spending, MEPS 2024; triangulation of the national market, depression share of use, growth, launch analogs, state ranking.
2. **Competitive landscape** (`notebooks/03_competitive_landscape.ipynb`): ClinicalTrials.gov API funnel, Phase 3 research, timeline, focus competitors, Caplyta index by state, non-drug alternatives, lessons from recent launches.
3. Pricing and access (next): CMS negotiated prices, Part D formulary coverage, patient cost.
4. Prescriber targeting: CMS Part D prescriber-level data.
5. Go-to-market synthesis.

## Data (all public)
CMS Medicare Part D (by geography, by prescriber, spending by drug), CMS Medicaid spending by drug, MEPS (AHRQ), CDC PLACES, Census population estimates, ClinicalTrials.gov, company disclosures and FDA announcements. Raw files are not committed; `scripts/01_download_data.py` re-downloads them and logs every download.

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
