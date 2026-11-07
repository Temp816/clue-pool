import requests, io
import openpyxl

B = 'http://localhost:8000/api'
def login(u, p):
    r = requests.post(B + '/login', json={'username': u, 'password': p})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['token']}, r.json()['user']

AH, admin = login('admin', 'admin123')
DH, demo = login('demo', 'demo123')
RH, rev = login('reviewer', 'review123')
print('reviewer:', rev['name'], rev['roles'], 'scope:', rev.get('approve_scope'))

# --- 审批流程 ---
# 找一条结构件线索（审批员范围=结构件）
items = requests.get(B + '/clues', headers=AH).json()['items']
struct = next(c for c in items if c['material'] == '结构件' and c['approval'] == '待审批')
chem = next((c for c in items if c['material'] == '化工料'), None)

# 审批员通过结构件线索
r = requests.post(f"{B}/clues/{struct['id']}/approve", json={'action': 'pass'}, headers=RH)
print('approve struct:', r.status_code, r.json().get('approval'), r.json().get('approved_by'))

# 审批员审批化工料线索（超范围，应拒绝）——注意化工料样例同时含IC，scope=IC也超范围
if chem:
    r = requests.post(f"{B}/clues/{chem['id']}/approve", json={'action': 'pass'}, headers=RH)
    print('approve chem (超范围):', r.status_code, r.json().get('detail'))

# 普通用户审批应拒绝
r = requests.post(f"{B}/clues/{struct['id']}/approve", json={'action': 'reject'}, headers=DH)
print('demo approve (无角色):', r.status_code)

# 管理员驳回 + 撤销
r = requests.post(f"{B}/clues/{struct['id']}/approve", json={'action': 'reject', 'comment': '信息不完整'}, headers=AH)
print('admin reject:', r.json()['approval'], r.json()['approval_comment'])
r = requests.post(f"{B}/clues/{struct['id']}/approve", json={'action': 'reset'}, headers=AH)
print('admin reset:', r.json()['approval'])

# 审批筛选
n1 = requests.get(B + '/clues', params={'approval': '待审批'}, headers=AH).json()['total']
n2 = requests.get(B + '/clues', params={'approval': '已通过'}, headers=AH).json()['total']
print('approval filter: 待审批', n1, '已通过', n2)

# 导出含审批列
r = requests.get(B + '/admin/export', headers=AH)
wb = openpyxl.load_workbook(io.BytesIO(r.content))
ws = wb.active
headers = [c.value for c in ws[1]]
print('export headers contain 审批状态/审批人:', '审批状态' in headers, '审批人' in headers)

# --- 头像 ---
from PIL import Image
img = Image.new('RGB', (64, 64), (43, 108, 255))
buf = io.BytesIO(); img.save(buf, 'PNG'); png = buf.getvalue()
r = requests.post(B + '/me/avatar', files={'file': ('a.png', png, 'image/png')}, headers=DH)
print('avatar upload:', r.status_code, r.json())

# --- 权限回归 ---
nd = requests.get(B + '/clues', headers=DH).json()['total']
na = requests.get(B + '/clues', headers=AH).json()['total']
print(f'权限回归: admin={na}, demo={nd}')
print('ALL V4 TESTS DONE')
