"""
Drug classification for the depression market.
Single source of truth for which drugs are in scope; every notebook imports this file.

Buckets
- core      : antidepressants whose main use is depression (counted in the market size)
- adjunct   : antipsychotics with an FDA add-on depression approval or common add-on use
              (counted separately, scaled by their depression share from MEPS; also the pricing benchmarks)
- other_use : contain a depression-drug ingredient but are mostly used for something else (sensitivity only)
"""
import re

CORE = [
    "sertraline", "escitalopram", "citalopram", "fluoxetine", "paroxetine", "fluvoxamine",   # SSRIs
    "venlafaxine", "desvenlafaxine", "duloxetine", "levomilnacipran",                         # SNRIs
    "bupropion", "mirtazapine", "vortioxetine", "vilazodone", "nefazodone",                   # other antidepressants
    "dextromethorphan hbr/bupropion", "gepirone", "zuranolone", "esketamine",                               # newer brands (Auvelity, Exxua, Zurzuvae, Spravato)
    "imipramine", "desipramine", "protriptyline", "clomipramine",                             # tricyclics (mostly depression)
    "phenelzine", "tranylcypromine", "isocarboxazid",                                         # MAOIs
]
ADJUNCT = ["aripiprazole", "brexpiprazole", "cariprazine", "quetiapine"]
OTHER_USE = {   # ingredient -> main other use (why it is excluded from the core market)
    "trazodone": "mostly insomnia",
    "amitriptyline": "mostly pain / migraine",
    "nortriptyline": "mostly pain",
    "doxepin": "low dose mostly insomnia",
    "olanzapine": "mostly schizophrenia / bipolar",
    "lumateperone": "schizophrenia / bipolar depression",
    "selegiline": "oral form mostly Parkinson's (patch is depression)",
}
# Not depression drugs at all, even though an ingredient matches (e.g. Contrave = naltrexone/bupropion for obesity,
# Nuedexta = dextromethorphan/quinidine for pseudobulbar affect)
NOT_DEPRESSION_PATTERNS = ["naltrexone", "quinidine"]
# Antipsychotic forms used for schizophrenia only (long-acting injectables, schizophrenia combos) -> other_use
OTHER_USE_PATTERNS = ["lauroxil", "samidorphan"]
OTHER_USE_BRANDS = ["maintena", "asimtufii", "aristada", "abilify main", "abilify asim"]  # MEPS truncates names to 12 characters
# Symbyax (olanzapine/fluoxetine) is FDA-approved for treatment-resistant depression -> adjunct
ADJUNCT_PATTERNS = ["olanzapine/fluoxetine"]

def classify(generic_name: str, brand_name: str = "") -> str:
    """Return core / adjunct / other_use / not_depression for a drug (generic name, optional brand name)."""
    g = str(generic_name).lower(); b = str(brand_name).lower()
    if any(p in g for p in NOT_DEPRESSION_PATTERNS):
        return "not_depression"
    has = lambda keys: any(re.search(rf"\b{k}", g) for k in keys)
    if "emsam" in b:                                   # selegiline patch is approved for depression
        return "core"
    if any(p in g for p in ADJUNCT_PATTERNS):          # Symbyax
        return "adjunct"
    if has(ADJUNCT):
        base = "adjunct"
    elif has(CORE):
        base = "core"
    elif has(OTHER_USE):
        return "other_use"
    else:
        return "not_depression"
    # depression ingredient, but a schizophrenia-only formulation (long-acting injectables etc.)
    if any(p in g for p in OTHER_USE_PATTERNS) or any(p in b for p in OTHER_USE_BRANDS):
        return "other_use"
    return base

def is_brand(brand_name: str, generic_name: str) -> bool:
    """CMS lists generics with brand name == generic name. Different names = a branded product."""
    first_ingredient = re.split(r"[^a-z]+", str(generic_name).lower().strip())[0]
    return first_ingredient not in str(brand_name).lower()   # e.g. "Bupropion XL" = generic, "Wellbutrin XL" = brand


def brand_names_from_cms(cms_df) -> set:
    """Brand names (lower case) from a CMS file, used to recognise brands in MEPS, whose pharmacy names are
    abbreviated (e.g. 'BUPROPN HCL' is a generic, 'LEXAPRO' is a brand)."""
    return {str(b).lower() for b, g in zip(cms_df.Brnd_Name, cms_df.Gnrc_Name) if is_brand(b, g)}

def meps_is_brand(rxname: str, cms_brands: set) -> bool:
    """True if a MEPS pharmacy drug name starts with the first word of a known CMS brand name."""
    first = re.split(r"[^a-z]+", str(rxname).lower().strip())[0]
    return len(first) >= 4 and any(b.split()[0] == first for b in cms_brands)
