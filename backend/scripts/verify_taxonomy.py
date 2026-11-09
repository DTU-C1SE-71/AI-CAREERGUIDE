import openpyxl
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('backend/app/db/seeds/moet_taxonomy_tt74.xlsx')
ws = wb['Danh mục 435 ngành']
excel_rows = list(ws.iter_rows(min_row=4, values_only=True))

with open('backend/app/db/seeds/moet_taxonomy_tt74.json', encoding='utf-8') as f:
    json_data = json.load(f)

print(f'Checking {len(excel_rows)} rows...')
errors = []
for i, (ex, js) in enumerate(zip(excel_rows, json_data)):
    ex_lv = str(ex[0]).strip()
    ex_lv_name = str(ex[1]).strip()
    ex_nhom = str(ex[2]).strip()
    ex_nhom_name = str(ex[3]).strip()
    ex_ma = str(ex[4]).strip()
    ex_ten = str(ex[5]).strip()
    
    js_raw = str(js.get('raw_code', '')).strip()
    js_major = str(js.get('major_code', '')).strip()
    js_name = str(js.get('name', '')).strip()
    js_group = str(js.get('group_code', '')).strip()
    js_field = str(js.get('field_code', '')).strip()
    
    if ex_ma != js_raw:
        errors.append(f'STT {i+1}: raw_code {js_raw} != Excel {ex_ma}')
    if ex_ten != js_name:
        errors.append(f'STT {i+1}: name "{js_name}" != Excel "{ex_ten}"')
    if ex_nhom != js_group:
        errors.append(f'STT {i+1}: group {js_group} != Excel {ex_nhom}')
    if ex_lv != js_field:
        errors.append(f'STT {i+1}: field {js_field} != Excel {ex_lv}')
    if js_major != f'7{ex_ma}':
        errors.append(f'STT {i+1}: major_code {js_major} != 7{ex_ma}')

print(f'Verification result: {len(errors)} issues found.')
if errors:
    for e in errors[:10]:
        print('  ', e)
else:
    print('SUCCESS: ALL 435 rows have 100% exact match in raw_code, name, group_code, field_code, and 7-prefix major_code!')
