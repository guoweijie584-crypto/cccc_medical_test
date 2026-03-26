import json

with open('data/patient_structured/patient_structured_50_desensitize.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

p = data[0]
print("Patient keys:", list(p.keys()))
print()
print("Patient ID:", p.get('patient_id', 'NOT FOUND'))
print("Name:", p.get('name', 'NOT FOUND'))
print("Age:", p.get('age', 'NOT FOUND'))
print("Gender:", p.get('gender', 'NOT FOUND'))
print("Condition:", p.get('condition', 'NOT FOUND'))
print("Blood glucose records count:", len(p.get('blood_glucose_records', [])))
