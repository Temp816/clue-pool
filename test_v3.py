import requests, io
import openpyxl

B = 'http://localhost:8000/api'
admin = requests.post(B + '/login', json={'username': 'admin', 'password': 'admin123'}).json()['token']
AH = {'Authorization': f'Bearer {admin}'}
demo = requests.post(B + '/login', json={'username': 'demo', 'password': 'demo123'}).json()
DH = {'Authorization': f'Bearer {demo["token"]}'}
print('demo perms:', demo['user'].get('perms'))

# 权限测试：admin 全量 vs demo（无化工料权限）
na = requests.get(B + '/clues', headers=AH).json()['total']
nd = requests.get(B + '/clues', headers=DH).json()['total']
print(f'admin sees {na} clues, demo sees {nd} clues (化工料线索应被隐藏)')

# demo 直接访问化工料线索详情应被拒
chem = [c for c in requests.get(B + '/clues', headers=AH).json()['items'] if c['material'] == '化工料']
if chem:
    r = requests.get(f"{B}/clues/{chem[0]['id']}", headers=DH)
    print('demo access chem clue ->', r.status_code, r.json().get('detail', ''))
# demo 自己的线索仍可见
mine = requests.get(B + '/clues', params={'mine': 1}, headers=DH).json()['total']
print('demo own clues visible:', mine)

# 标签组合预设
r = requests.post(B + '/presets', json={'name': '供应商出差-结构件', 'depts': ['原价'], 'material': '结构件', 'category': '供应商信息', 'channel': '供应商出差'}, headers=DH)
print('preset create:', r.json())
ps = requests.get(B + '/presets', headers=DH).json()
print('presets:', [(p['name'], p['depts'], p['material'], p['category'], p['channel']) for p in ps])
print('preset delete:', requests.delete(f"{B}/presets/{ps[0]['id']}", headers=DH).json())

# 批量导入：构造表格
wb = openpyxl.Workbook(); ws = wb.active
ws.append(['用户名', '姓名', '密码', '角色', '查看权限'])
ws.append(['wangwu', '王五', '123456', '提交人,查看人', '结构件,电子料'])
ws.append(['zhaoliu', '赵六', '123456', '查看人', '全部'])
ws.append(['wangwu', '重复', '123456', '查看人', 'CI'])
buf = io.BytesIO(); wb.save(buf); buf.seek(0)
r = requests.post(B + '/admin/users/import', files={'file': ('import.xlsx', buf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}, headers=AH)
print('import:', r.json())

# 模板下载
r = requests.get(B + '/admin/users/template', headers=AH)
print('template bytes:', len(r.content))

# 新用户登录 + 权限生效
tok5 = requests.post(B + '/login', json={'username': 'wangwu', 'password': '123456'}).json()
n5 = requests.get(B + '/clues', headers={'Authorization': f"Bearer {tok5['token']}"}).json()['total']
print(f"wangwu (结构件,电子料) sees {n5} clues")

users = requests.get(B + '/admin/users', headers=AH).json()
print('users:', [(u['username'], u['perm_list']) for u in users])
print('ALL V3 TESTS DONE')
