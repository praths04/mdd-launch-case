#!/usr/bin/env python3
"""
MDD Launch Case - data acquisition (standard library only, no installs needed).

Run from the project folder on your Mac:
    python3 scripts/01_download_data.py monday     # small files for market sizing (~2-5 min)
    python3 scripts/01_download_data.py big        # Medicare Part D prescriber file, filtered to depression drugs while streaming (30-90 min)
    python3 scripts/01_download_data.py all
    python3 scripts/01_download_data.py trials     # Workstream 2: ClinicalTrials.gov depression trials (~1-2 min)
    python3 scripts/01_download_data.py pricing    # Workstream 3: Medicare negotiated prices + Part D formulary file (large, 5-20 min)

Every file lands in data/raw/ and a line is appended to data/raw/_download_log.csv
(source, URL, timestamp, rows) so the pipeline is documented and re-runnable.
"""
import csv, io, json, os, sys, time, urllib.parse, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "mdd-launch-case/1.0 (portfolio project)"}
csv.field_size_limit(10**9)

# Depression-relevant generics (CMS Gnrc_Name matched case-insensitively, substring).
# Some are multi-use (e.g. trazodone for sleep, amitriptyline for pain, antipsychotics for schizophrenia);
# they are kept and flagged in the cleaning step, not dropped here.
DEPRESSION_GENERICS = [
    "sertraline", "escitalopram", "citalopram", "fluoxetine", "paroxetine", "fluvoxamine",
    "venlafaxine", "desvenlafaxine", "duloxetine", "levomilnacipran",
    "bupropion", "mirtazapine", "trazodone", "nefazodone", "vortioxetine", "vilazodone",
    "gepirone", "zuranolone", "esketamine",
    "nortriptyline", "amitriptyline", "imipramine", "desipramine", "doxepin", "protriptyline", "clomipramine",
    "phenelzine", "tranylcypromine", "isocarboxazid", "selegiline",
    "aripiprazole", "brexpiprazole", "cariprazine", "quetiapine", "olanzapine", "lumateperone",
]

def log(source, url, path, rows):
    p = os.path.join(RAW, "_download_log.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["source", "url", "file", "rows", "downloaded_at"])
        w.writerow([source, url, os.path.basename(path), rows, datetime.datetime.now().isoformat(timespec="seconds")])

def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout)

def save(url, fname, source):
    path = os.path.join(RAW, fname)
    print(f"-> {source}\n   {url}")
    with get(url, timeout=300) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk)
    rows = -1 if path.endswith(".zip") else sum(1 for _ in open(path, encoding="utf-8", errors="ignore")) - 1
    print(f"   saved {fname}" + ("" if rows < 0 else f" ({rows:,} rows)"))
    log(source, url, path, rows)
    return path

# ---------- CMS catalog lookup (finds the newest CSV so links never go stale) ----------
_catalog = None
def cms_latest_csv(title):
    global _catalog
    if _catalog is None:
        print("-> Reading data.cms.gov catalog")
        with get("https://data.cms.gov/data.json", timeout=300) as r:
            _catalog = json.load(r)["dataset"]
    ds = [d for d in _catalog if d.get("title", "").strip().lower() == title.lower()]
    if not ds:  # fall back to a contains-match (titles sometimes carry extra words)
        ds = [d for d in _catalog if title.lower() in d.get("title", "").lower()]
        if ds: print(f"   using catalog title: {ds[0]['title']}")
    if not ds:
        near = [d.get("title") for d in _catalog if all(w in d.get("title", "").lower() for w in title.lower().split()[:2])][:8]
        print(f"   closest catalog titles: {near}")
        raise RuntimeError(f"CMS dataset not found: {title}")
    dists = [x for x in ds[0].get("distribution", [])
             if x.get("downloadURL", "").lower().endswith(".csv") or x.get("mediaType") == "text/csv"]
    dists.sort(key=lambda x: (x.get("temporal", ""), x.get("modified", "")), reverse=True)
    if not dists:
        api = [x for x in ds[0].get("distribution", []) if "data-api" in (x.get("accessURL", "") + x.get("downloadURL", ""))]
        api.sort(key=lambda x: (x.get("temporal", ""), x.get("modified", "")), reverse=True)
        if api:
            return "API::" + (api[0].get("accessURL") or api[0].get("downloadURL")), api[0].get("temporal", "")
        raise RuntimeError(f"No CSV or API distribution for: {title}")
    return dists[0]["downloadURL"], dists[0].get("temporal", "")

def save_api(api_url, fname, source, page=5000):
    # Page through a data.cms.gov data-api endpoint (JSON) and write a CSV.
    path = os.path.join(RAW, fname); print(f"-> {source} (via API)\n   {api_url}")
    rows, offset, header = 0, 0, None
    with open(path, "w", newline="") as f:
        w = None
        while True:
            sep = "&" if "?" in api_url else "?"
            with get(f"{api_url}{sep}size={page}&offset={offset}", timeout=300) as r:
                batch = json.load(r)
            if not batch: break
            if header is None:
                header = list(batch[0].keys()); w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore"); w.writeheader()
            w.writerows(batch); rows += len(batch); offset += page
            if len(batch) < page: break
    print(f"   saved {fname} ({rows:,} rows)"); log(source, api_url, path, rows); return path

# ---------- Monday: market sizing ----------
def places():
    # CDC PLACES county estimates, 2025 release. DEPRESSION = adults ever told they have depression.
    # Extra measures for the "expected treatment" regression: frequent mental distress, no insurance, routine checkup.
    where = "measureid in('DEPRESSION','MHLTH','ACCESS2','CHECKUP')"
    url = "https://data.cdc.gov/resource/swc5-untb.csv?" + urllib.parse.urlencode({"$where": where, "$limit": 50000})
    save(url, "cdc_places_county_2025.csv", "CDC PLACES county 2025 release")

def places_2024():
    # Previous PLACES release (2022 survey). Used to fill Kentucky and Pennsylvania, which have no county
    # estimates in the 2025 release, and to check how stable county rates are from one release to the next.
    url = "https://data.cdc.gov/resource/fu4u-a9bh.csv?" + urllib.parse.urlencode({"$where": "measureid='DEPRESSION'", "$limit": 50000})
    save(url, "cdc_places_county_2024.csv", "CDC PLACES county 2024 release (DEPRESSION)")

def acs():
    # Census ACS 5-year county profile: total population, 65+, median household income.
    for year in (2024, 2023):
        base = f"https://api.census.gov/data/{year}/acs/acs5/profile"
        try:
            with get(base + "/variables.json") as r:
                vars_ = json.load(r)["variables"]
        except Exception as e:
            print(f"   ACS {year} variables not available ({type(e).__name__}: {e}); trying earlier year"); continue
        want = {
            "total_pop": lambda l: l == "Estimate!!SEX AND AGE!!Total population",
            "pop_65plus": lambda l: l == "Estimate!!SEX AND AGE!!Total population!!65 years and over",
            "median_hh_income": lambda l: l.startswith("Estimate!!INCOME AND BENEFITS") and l.endswith("Total households!!Median household income (dollars)"),
        }
        picked = {}
        for k, fn in want.items():
            hits = [v for v, meta in vars_.items() if fn(meta.get("label", ""))]
            if hits: picked[k] = sorted(hits)[0]
        print(f"   ACS {year} variables: {picked}")
        if len(picked) < 3:
            print(f"   ACS {year}: could not resolve all variables {picked}; trying earlier year"); continue
        params = {"get": "NAME," + ",".join(picked.values()), "for": "county:*"}
        if os.environ.get("CENSUS_API_KEY"):
            params["key"] = os.environ["CENSUS_API_KEY"]  # free key: https://api.census.gov/data/key_signup.html
        url = base + "?" + urllib.parse.urlencode(params)
        print(f"-> Census ACS {year} 5-year profile\n   {url}")
        try:
            with get(url, timeout=300) as r:
                body = r.read().decode("utf-8", errors="replace")
            data = json.loads(body)
        except json.JSONDecodeError:
            print(f"   ACS {year}: Census returned a non-data page (usually means an API key is needed). First 200 chars:\n   {body[:200]!r}")
            print("   Tip: get a free key at https://api.census.gov/data/key_signup.html, then run:\n   CENSUS_API_KEY=yourkey python3 scripts/01_download_data.py census")
            return
        except Exception as e:
            print(f"   ACS {year} query failed ({type(e).__name__}: {e}); trying earlier year"); continue
        header = ["county_name"] + list(picked.keys()) + ["state_fips", "county_fips"]
        path = os.path.join(RAW, f"census_acs5_{year}_county.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(header + ["fips"])
            for row in data[1:]:
                w.writerow(row + [row[-2] + row[-1]])
        print(f"   saved {os.path.basename(path)} ({len(data)-1:,} counties)")
        log(f"Census ACS {year} 5-yr profile", url, path, len(data) - 1)
        return
    print("   !! ACS download failed for all years")

def popest_age():
    # Fallback / complement to ACS: Census county population estimates by age (Vintage 2024), from www2.census.gov.
    save("https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/cc-est2024-agesex-all.csv",
         "census_popest_2024_county_agesex.csv", "Census county population estimates by age, Vintage 2024")

def zcta_county():
    # Census ZIP (ZCTA) to county relationship file, used to place prescribers in counties.
    save("https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt",
         "census_zcta_county_2020.txt", "Census ZCTA-county relationship 2020")

def partd_geo():
    url, t = cms_latest_csv("Medicare Part D Prescribers - by Geography and Drug")
    save(url, "cms_partd_geo_drug.csv", f"CMS Part D by Geography and Drug {t}")

def partd_spending():
    url, t = cms_latest_csv("Medicare Part D Spending by Drug")
    save(url, "cms_partd_spending_by_drug.csv", f"CMS Part D Spending by Drug {t}")

def partd_provider():
    url, t = cms_latest_csv("Medicare Part D Prescribers - by Provider")
    save(url, "cms_partd_by_provider.csv", f"CMS Part D Prescribers by Provider {t}")

def hrsa_mh_hpsa():
    save("https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_MH.csv",
         "hrsa_hpsa_mental_health.csv", "HRSA Mental Health HPSAs")

# ---------- Big: prescriber x drug, filtered while streaming ----------
def partd_provider_drug():
    try:
        url, t = cms_latest_csv("Medicare Part D Prescribers - by Provider and Drug")
    except Exception as e:
        print(f"   catalog lookup failed ({e}); using known 2024 file")
        url, t = ("https://data.cms.gov/sites/default/files/2026-05/0ae165f4-eb44-495d-8cac-67f4571b6b83/"
                  "MUP_DPR_RY26_P04_V10_DY24_NPIBN.csv"), "2024"
    out = os.path.join(RAW, "cms_partd_provider_drug_DEPRESSION.csv")
    print(f"-> CMS Part D Prescribers by Provider and Drug {t} (streaming ~25M rows; keeping depression drugs only)\n   {url}")
    keys = [g.lower() for g in DEPRESSION_GENERICS]
    kept = seen = 0; t0 = time.time()
    with get(url, timeout=600) as r, open(out, "w", newline="") as f:
        reader = csv.reader(io.TextIOWrapper(r, encoding="utf-8", errors="replace", newline=""))
        header = next(reader); w = csv.writer(f); w.writerow(header)
        gi = header.index("Gnrc_Name")
        for row in reader:
            seen += 1
            g = row[gi].lower() if len(row) > gi else ""
            if any(k in g for k in keys):
                w.writerow(row); kept += 1
            if seen % 1_000_000 == 0:
                print(f"   {seen/1e6:.0f}M rows scanned, {kept:,} kept, {time.time()-t0:,.0f}s")
    print(f"   done: {seen:,} scanned, {kept:,} depression-drug rows kept -> {os.path.basename(out)}")
    log(f"CMS Part D Provider x Drug {t} (filtered)", url, out, kept)


# ---------- All-payer triangulation ----------
def medicaid_spending():
    # Medicaid drug spending by drug (national), same format family as Medicare Part D Spending by Drug.
    url, t = cms_latest_csv("Medicaid Spending by Drug")
    if url.startswith("API::"):
        save_api(url[5:], "cms_medicaid_spending_by_drug.csv", f"CMS Medicaid Spending by Drug {t}")
    else:
        save(url, "cms_medicaid_spending_by_drug.csv", f"CMS Medicaid Spending by Drug {t}")

def _save_first(candidates, fname, source):
    last = None
    for url in candidates:
        try:
            return save(url, fname, source)
        except Exception as e:
            last = e; print(f"   not at {url} ({e}); trying next")
    raise RuntimeError(f"{source}: no candidate URL worked ({last})")

def meps():
    # MEPS 2023 (AHRQ): every prescription fill with who paid (Medicare/Medicaid/private/self) + link to the condition it treated.
    #   HC-248A prescribed medicines, HC-249 medical conditions, HC-248I appendix (CLNK condition-event link).
    # Stata format (.dta inside a zip) - pandas can read it directly.
    base = "https://meps.ahrq.gov/data_files/pufs/"
    for code, fname, label in [("h248a", "meps_2023_prescribed_medicines_dta.zip", "MEPS 2023 Prescribed Medicines (HC-248A)"),
                               ("h249",  "meps_2023_conditions_dta.zip",          "MEPS 2023 Medical Conditions (HC-249)"),
                               ("h248i", "meps_2023_clnk_dta.zip",                "MEPS 2023 Condition-Event Link (HC-248I)")]:
        names = [f"{code}dta.zip", f"{code}f1dta.zip"] if code == "h248i" else [f"{code}dta.zip"]
        cands = [f"{base}{code}/{n}" for n in names] + [f"https://meps.ahrq.gov/mepsweb/data_files/pufs/{code}/{n}" for n in names]
        _save_first(cands, fname, label)

def meps_2024():
    # MEPS 2024 (released July-August 2026): same three files as 2023, new file numbers.
    base = "https://meps.ahrq.gov/data_files/pufs/"
    for code, fname, label in [("h254a", "meps_2024_prescribed_medicines_dta.zip", "MEPS 2024 Prescribed Medicines (HC-254A)"),
                               ("h255",  "meps_2024_conditions_dta.zip",          "MEPS 2024 Medical Conditions (HC-255)"),
                               ("h254i", "meps_2024_clnk_dta.zip",                "MEPS 2024 Condition-Event Link (HC-254I)")]:
        names = [f"{code}dta.zip", f"{code}f1dta.zip"] if code == "h254i" else [f"{code}dta.zip"]
        cands = [f"{base}{code}/{n}" for n in names] + [f"https://meps.ahrq.gov/mepsweb/data_files/pufs/{code}/{n}" for n in names]
        _save_first(cands, fname, label)

# ---------- Workstream 2: ClinicalTrials.gov (API v2) ----------
CT_API = "https://clinicaltrials.gov/api/v2/studies"
CT_CONDITION = "major depressive disorder OR treatment-resistant depression OR depressive disorder"
CT_TERM = "AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2015-01-01,MAX]"
CT_FIELDS = "IdentificationModule,StatusModule,SponsorCollaboratorsModule,ConditionsModule,DesignModule,ArmsInterventionsModule,ContactsLocationsModule"

def _ct_pages(params):
    """Yield every study for the query, following nextPageToken (1,000 studies per page)."""
    token = None
    while True:
        p = dict(params, pageSize=1000, format="json")
        if token: p["pageToken"] = token
        url = CT_API + "?" + urllib.parse.urlencode(p)
        with get(url, timeout=180) as r:
            data = json.load(r)
        yield from data.get("studies", [])
        token = data.get("nextPageToken")
        if not token: break
        time.sleep(0.5)            # be polite to the API

def trials():
    """Interventional depression trials starting 2015 or later: drugs, devices, digital, psychotherapy, all phases."""
    base = {"query.cond": CT_CONDITION}
    attempts = [dict(base, **{"query.term": CT_TERM, "fields": CT_FIELDS}),   # preferred: filtered on the server, slim fields
                dict(base, **{"query.term": CT_TERM}),                        # fallback: full records
                dict(base)]                                                   # last resort: filter locally below
    studies = None
    for params in attempts:
        try:
            print(f"-> ClinicalTrials.gov: {params}")
            studies = list(_ct_pages(params))
            if studies and "designModule" in studies[0].get("protocolSection", {}):
                break
            print("   query returned no usable records; trying a simpler query"); studies = None
        except Exception as e:
            print(f"   query failed ({e}); trying a simpler query")
    if studies is None:
        raise RuntimeError("all ClinicalTrials.gov queries failed")

    raw_path = os.path.join(RAW, "ctgov_depression_studies.json")
    with open(raw_path, "w") as f: json.dump(studies, f)

    def d(s, *keys, default=""):
        for k in keys:
            s = s.get(k, {}) if isinstance(s, dict) else {}
        return s if s not in ({}, None) else default

    rows = []
    for st in studies:
        ps = st.get("protocolSection", {})
        if d(ps, "designModule", "studyType") != "INTERVENTIONAL": continue
        start = d(ps, "statusModule", "startDateStruct", "date")
        if start and start[:4] < "2015": continue
        ivs = d(ps, "armsInterventionsModule", "interventions", default=[])
        locs = d(ps, "contactsLocationsModule", "locations", default=[])
        rows.append({
            "nct_id": d(ps, "identificationModule", "nctId"),
            "title": d(ps, "identificationModule", "briefTitle"),
            "status": d(ps, "statusModule", "overallStatus"),
            "start_date": start,
            "primary_completion_date": d(ps, "statusModule", "primaryCompletionDateStruct", "date"),
            "last_update": d(ps, "statusModule", "lastUpdatePostDateStruct", "date"),
            "phases": "|".join(d(ps, "designModule", "phases", default=[])),
            "allocation": d(ps, "designModule", "designInfo", "allocation"),
            "primary_purpose": d(ps, "designModule", "designInfo", "primaryPurpose"),
            "enrollment": d(ps, "designModule", "enrollmentInfo", "count"),
            "sponsor": d(ps, "sponsorCollaboratorsModule", "leadSponsor", "name"),
            "sponsor_class": d(ps, "sponsorCollaboratorsModule", "leadSponsor", "class"),
            "collaborators": "; ".join(c.get("name", "") for c in d(ps, "sponsorCollaboratorsModule", "collaborators", default=[])),
            "conditions": "; ".join(d(ps, "conditionsModule", "conditions", default=[])),
            "intervention_types": "|".join(sorted({i.get("type", "") for i in ivs})),
            "interventions": "; ".join(i.get("name", "") for i in ivs),
            "intervention_other_names": "; ".join(n for i in ivs for n in i.get("otherNames", [])),
            "countries": "|".join(sorted({l.get("country", "") for l in locs if l.get("country")})),   # where the trial is run
            "us_sites": sum(1 for l in locs if l.get("country") == "United States"),
        })
    path = os.path.join(RAW, "ctgov_depression_trials.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"   saved ctgov_depression_trials.csv ({len(rows):,} interventional trials, 2015+) and the raw JSON ({len(studies):,} records)")
    log("ClinicalTrials.gov API v2 (depression, interventional, 2015+)", CT_API, path, len(rows))

# ---------- Workstream 3: pricing and access ----------
NEGOTIATED_PRICES_URL = "https://www.cms.gov/files/zip/selected-drug-list-negotiated-prices-also-known-maximum-fair-prices-statutezip.zip"

def negotiated_prices():
    """Medicare negotiated ('maximum fair') prices for selected drugs, incl. Vraylar (2027). Small ZIP with .xlsx/.csv."""
    save(NEGOTIATED_PRICES_URL, "cms_negotiated_prices.zip", "CMS Medicare Drug Price Negotiation: selected drugs and negotiated prices")

def partd_formulary():
    """Quarterly Part D formulary public use file: tier, prior authorization, step therapy for every plan and drug (large ZIP, ~1-3 GB)."""
    global _catalog
    if _catalog is None:
        print("-> Reading data.cms.gov catalog")
        with get("https://data.cms.gov/data.json", timeout=300) as r:
            _catalog = json.load(r)["dataset"]
    ds = [d for d in _catalog if "formulary" in d.get("title", "").lower() and "pharmacy network" in d.get("title", "").lower()]
    if not ds:
        print("   closest titles:", [d["title"] for d in _catalog if "formulary" in d.get("title", "").lower()][:8])
        raise RuntimeError("Formulary dataset not found in the data.cms.gov catalog; download manually from "
                           "https://data.cms.gov (search 'Prescription Drug Plan Formulary') into data/raw/")
    print(f"   catalog title: {ds[0]['title']}")
    zips = [x for x in ds[0].get("distribution", []) if x.get("downloadURL", "").lower().endswith(".zip")]
    zips.sort(key=lambda x: (x.get("temporal", ""), x.get("modified", ""), x.get("downloadURL", "")), reverse=True)
    if not zips:
        raise RuntimeError("No ZIP distribution found for the formulary dataset; download manually (see above)")
    print("   this is a large file (1-3 GB): expect 5-20 minutes")
    path = save(zips[0]["downloadURL"], "cms_partd_formulary_latest.zip", f"CMS Part D formulary PUF ({zips[0].get('temporal', 'latest')})")
    import zipfile
    print("   files inside:", zipfile.ZipFile(path).namelist()[:12])

MONDAY = [places, acs, popest_age, zcta_county, partd_geo, partd_spending, hrsa_mh_hpsa]
BIG = [partd_provider, partd_provider_drug]

if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "monday").lower()
    jobs = {"monday": MONDAY, "big": BIG, "all": MONDAY + BIG, "census": [acs, popest_age],
            "payers": [medicaid_spending, meps], "medicaid": [medicaid_spending], "places2024": [places_2024], "meps2024": [meps_2024], "trials": [trials], "pricing": [negotiated_prices, partd_formulary], "negotiated": [negotiated_prices], "formulary": [partd_formulary]}.get(mode)
    if jobs is None:
        sys.exit("usage: python3 scripts/01_download_data.py [monday|big|all|census|payers|medicaid|places2024|meps2024|trials|pricing|negotiated|formulary]")
    failed = []
    for job in jobs:
        try: job()
        except Exception as e:
            print(f"   !! {job.__name__} failed: {e}"); failed.append(job.__name__)
    print("\nFinished." + (f" Failed: {', '.join(failed)} (re-run later; everything else is saved)" if failed else " All downloads succeeded."))
