from backend.data.vault_loader import load_psu_cmpsc_vault
from backend.services.rule_extraction_service import extract_rules_from_records

records = load_psu_cmpsc_vault()
rules = extract_rules_from_records(records)

print("Total rules extracted:", len(rules))
print()

for i, rule in enumerate(rules[:20], start=1):
    print(f"Rule {i}:")
    print(rule)
    print()