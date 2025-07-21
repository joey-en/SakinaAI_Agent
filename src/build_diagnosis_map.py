import json
from fuzzywuzzy import fuzz, process

def build_diagnosis_alias_map(diagnoses, threshold=90):
    alias_map = {}
    for d in diagnoses:
        best_match, score = process.extractOne(d, diagnoses, scorer=fuzz.token_sort_ratio)
        if score >= threshold and best_match != d:
            alias_map[d.lower()] = best_match
        else:
            alias_map[d.lower()] = d  # Use self as canonical
    return alias_map

# ill tell you what wrong with this aproach
# *  this assumes different are different like this "child neglect": "Child Neglect", "delusional disorder": "Delusional Disorder", those dont need to be in the alias map cuz theyre the same right
# *  i dont think this 

def save_diagnosis_map(alias_map, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(alias_map, f, indent=2, ensure_ascii=False)

def load_diagnosis_map(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
