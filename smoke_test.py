import requests, json

B = 'http://localhost:8000/api'
tok = requests.post(B + '/login', json={'username': 'admin', 'password': 'admin123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}
demo = requests.post(B + '/login', json={'username': 'demo', 'password': 'demo123'}).json()['token']
DH = {'Authorization': f'Bearer {demo}'}

# 建线索（完整）
r = requests.post(B + '/clues', json={
    'title': '竞品A计划下季度降价15%', 'content': '在行业交流会上从客户处获悉，竞品A正在制定Q1降价方案',
    'source': '某客户采购经理', 'scene': '行业交流会', 'acquired_at': '2026-11-06',
    'category': '竞争对手', 'keywords': ['竞品A', '降价'], 'credibility': '中',
}, headers=H)
print('create:', r.status_code, r.json()['title'])
cid = r.json()['id']

# 快速录入
r2 = requests.post(B + '/clues', json={'title': '听说隔壁部门在调研新政策', 'status': '待补充'}, headers=DH)
print('quick:', r2.status_code, r2.json()['status'])
cid2 = r2.json()['id']

# 列表/搜索/筛选/排序
for params in [{}, {'sort': 'hot'}, {'keyword': '降价'}, {'category': '竞争对手'}, {'mine': 1}]:
    r = requests.get(B + '/clues', params=params, headers=H).json()
    print('list', params, '->', r['total'])

# 详情(浏览+1) 点赞 收藏
d = requests.get(f'{B}/clues/{cid}', headers=DH).json()
print('detail views:', d['views'])
print('like:', requests.post(f'{B}/clues/{cid}/like', headers=DH).json())
print('fav:', requests.post(f'{B}/clues/{cid}/favorite', headers=DH).json())

# 关注（公开+隐藏）
print('follow-cat:', requests.post(B + '/follows', json={'target_type': 'category', 'target_value': '竞争对手', 'is_public': True}, headers=DH).status_code)
print('follow-sub:', requests.post(B + '/follows', json={'target_type': 'submitter', 'target_value': 1, 'is_public': False}, headers=DH).status_code)
r = requests.get(B + '/clues', params={'following': 1}, headers=DH).json()
print('following list ->', r['total'])

# 个人标签
print('mytag:', requests.post(f'{B}/clues/{cid}/my-tags', json={'tag': '重点跟进'}, headers=DH).json())
r = requests.get(B + '/clues', params={'my_tags': '重点跟进'}, headers=DH).json()
print('my_tags filter ->', r['total'])

# 补充待补充线索
r = requests.patch(f'{B}/clues/{cid2}', json={'content': '补充后的完整内容', 'source': '内部交流', 'scene': '茶水间', 'acquired_at': '2026-11-07', 'category': '政策法规'}, headers=DH)
print('patch status ->', r.json()['status'])

# 管理端
print('users:', len(requests.get(B + '/admin/users', headers=H).json()))
print('create user:', requests.post(B + '/admin/users', json={'username': 'zhangsan', 'name': '张三', 'password': '123456', 'roles': ['submitter', 'viewer']}, headers=H).json())
r = requests.get(B + '/admin/export', headers=H)
print('export:', r.status_code, len(r.content), 'bytes')
print('AI suggest (fallback):', requests.post(B + '/ai/suggest', json={'title': '竞品B发布新技术', 'content': '涉及AI算法研发'}, headers=H).json())
print('ALL SMOKE TESTS DONE')
