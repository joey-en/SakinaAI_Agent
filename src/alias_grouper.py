import json
import os
from rapidfuzz import fuzz, process
import re

FUZZY_THRESHOLD = 90  # Good default

def extract_parenthetical_aliases(name: str) -> list:
    """
    Extracts aliases from a diagnosis or alias string with parentheses.
    e.g. "Childhood-onset fluency disorder (Stuttering)" → ["Childhood-onset fluency disorder", "Stuttering"]
    """
    matches = re.match(r"^(.*)\(([^)]+)\)", name)
    if matches:
        outside = matches.group(1).strip()
        inside = matches.group(2).strip()
        return [name.strip(), outside, inside]
    return [name.strip()] if name.strip() else []

def create_name_mapping(input_json_path, output_json_path):
    with open(input_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Load existing alias groups if the file exists
    if os.path.exists(output_json_path):
        with open(output_json_path, "r", encoding="utf-8") as f:
            alias_groups = json.load(f)
    else:
        alias_groups = []

    for entry in records:
        names = set()
        main_name = entry.get("diagnosis", "")
        for n in extract_parenthetical_aliases(main_name):
            names.add(n)

        raw_aliases = entry.get("aliases")
        if isinstance(raw_aliases, list):
            for alias in raw_aliases:
                if isinstance(alias, str):
                    for n in extract_parenthetical_aliases(alias):
                        names.add(n)

        matched = False
        for group in alias_groups:
            for name in names:
                best_match = process.extractOne(
                    name,
                    [group["main"]] + group["aliases"],
                    scorer=fuzz.token_set_ratio
                )
                if best_match and best_match[1] >= FUZZY_THRESHOLD:
                    # Add only new aliases
                    group["aliases"].extend(
                        [n for n in names if n != group["main"] and n not in group["aliases"]]
                    )
                    matched = True
                    break
            if matched:
                break

        if not matched:
            main = main_name
            other_aliases = list(names - {main})
            alias_groups.append({
                "main": main,
                "aliases": other_aliases
            })

    # Deduplicate and sort aliases
    for group in alias_groups:
        group["aliases"] = sorted(set(group["aliases"]))

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(alias_groups, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(alias_groups)} alias groups to {output_json_path}")

def normalize_names_from_mapping(
    input_json_path,
    alias_mapping_path,
    output_json_path,
    threshold=90
):
    # Load input diagnosis JSON
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load alias group mapping (dict-based)
    with open(alias_mapping_path, 'r', encoding='utf-8') as f:
        alias_dicts = json.load(f)

    print(f"✅ Loaded {len(alias_dicts)} alias groups")

    # Build name-to-group map
    name_to_group = {}
    skipped = 0

    for i, group in enumerate(alias_dicts):
        main = group.get("main")
        aliases = group.get("aliases", [])
        if not main or not isinstance(aliases, list):
            print(f"⚠️ Skipping invalid alias group at index {i}: {group}")
            skipped += 1
            continue

        all_names = [main] + aliases
        for alias in all_names:
            if alias and isinstance(alias, str):
                name_to_group[alias.strip()] = {"main": main, "aliases": list(set(all_names) - {main})}

    print(f"🔍 Total mapped names: {len(name_to_group)}")

    # Normalize entries
    normalized = []
    for obj in data:
        name = obj.get("diagnosis", "")
        aliases = obj.get("aliases", []) or []
        all_terms = [name] + aliases

        best_match = None
        best_score = -1

        for term in all_terms:
            if term is None: continue
            for known_name in name_to_group:
                score = fuzz.ratio(term.lower(), known_name.lower())
                if score > best_score and score >= threshold:
                    best_match = known_name
                    best_score = score

        if best_match:
            group = name_to_group[best_match]
            obj["diagnosis"] = group["main"]
            obj["aliases"] = sorted(set(group["aliases"]))
            # print(f"✔ Matched '{name}' → '{group['main']}' (score: {best_score})")
        else:
            print(f"⚠ No match found for: {name}")
            # Keep original

        normalized.append(obj)

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved normalized file to {output_json_path}")



def main():
    create_name_mapping(
        input_json_path="./src/saved_json/DSM_5 Short.json",
        output_json_path="./src/saved_mappings/diagnosis_names.json"
    )
    
    normalize_names_from_mapping(
        input_json_path="./src/saved_json/DSM_5 Short.json",
        alias_mapping_path="./src/saved_mappings/diagnosis_names.json",
        output_json_path="./src/saved_json/DSM_5 Short (cleaned).json"
    )

main()