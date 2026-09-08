"""
Rank utilities for military and civilian rank sorting precedence.
Standard Military Order (Senior to Junior):
Commissioned Officers (GEN down to 2LT) -> Warrant Officers (CW5 down to WO1) -> Enlisted (SMA down to PV1) -> Civilians -> Unassigned
"""
import re

RANK_WEIGHTS = {
    # Commissioned Officers (O-10 down to O-1)
    "GEN": 1, "O10": 1,
    "LTG": 2, "O9": 2,
    "MG": 3, "O8": 3,
    "BG": 4, "O7": 4,
    "COL": 5, "O6": 5,
    "LTC": 6, "O5": 6,
    "MAJ": 7, "O4": 7,
    "CPT": 8, "CAPT": 8, "O3": 8,
    "1LT": 9, "1STLT": 9, "O2": 9,
    "2LT": 10, "2DLT": 10, "2NDLT": 10, "O1": 10,

    # Warrant Officers (W-5 down to W-1)
    "CW5": 11, "CWO5": 11, "W5": 11,
    "CW4": 12, "CWO4": 12, "W4": 12,
    "CW3": 13, "CWO3": 13, "W3": 13,
    "CW2": 14, "CWO2": 14, "W2": 14,
    "WO1": 15, "W01": 15, "W1": 15, "WO": 15,

    # Enlisted (E-9 down to E-1)
    "SMA": 16,
    "CSM": 17, "SGTMAJ": 17,
    "SGM": 18, "MGYSGT": 18, "E9": 18,
    "1SG": 19, "1STSGT": 19,
    "MSG": 20, "MSGT": 20, "E8": 20,
    "SFC": 21, "GYSGT": 21, "E7": 21,
    "SSG": 22, "SSGT": 22, "E6": 22,
    "SGT": 23, "E5": 23,
    "CPL": 24,
    "SPC": 25, "SP4": 25, "E4": 25,
    "PFC": 26, "LCPL": 26, "E3": 26,
    "PV2": 27, "E2": 27,
    "PV1": 28, "PVT": 28, "E1": 28,

    # Civilians / Contractors
    "CIV": 90, "CTR": 90, "MR": 90, "MS": 90, "MRS": 90, "DR": 90
}

def clean_rank_string(rank: str) -> str:
    if not rank:
        return ""
    # Strip dots, spaces, dashes
    cleaned = re.sub(r'[\s.\-_/]', '', rank).upper()
    return cleaned

def get_sort_weight(rank: str) -> int:
    if not rank:
        return 99
    r = clean_rank_string(rank)
    if not r:
        return 99
    
    # Direct match
    if r in RANK_WEIGHTS:
        return RANK_WEIGHTS[r]
    
    # Check if starts with a known rank prefix (e.g. "SSG " or "SSGDIXON")
    for k in sorted(RANK_WEIGHTS.keys(), key=len, reverse=True):
        if r.startswith(k):
            return RANK_WEIGHTS[k]
            
    return 80  # Default unknown rank string
