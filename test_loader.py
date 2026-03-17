from backend.data.vault_loader import load_psu_cmpsc_vault

records = load_psu_cmpsc_vault()

print("Total records:", len(records))
print("\nFirst record:")
print(records[0])