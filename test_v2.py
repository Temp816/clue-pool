import requests

B = 'http://localhost:8000/api'
tok = requests.post(B + '/login', json={'username': 'admin', 'password': 'admin123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}
demo = requests.post(B + '/login', json={'username': 'demo', 'password': 'demo123'}).json()['token']
DH = {'Authorization': f'Bearer {demo}'}

# meta：新分类体系
m = requests.get(B + '/meta', headers=H).json()
print('taxonomy depts:', m['taxonomy']['depts'], '| ai_enabled:', m['ai_enabled'], '| ai_suggest:', m['ai_suggest'])

# 本地智能推荐
r = requests.post(B + '/ai/suggest', json={'title': '供应商B结构件模具交期延长', 'content': '注塑产能不足，交期延长两周'}, headers=H).json()
print('local suggest:', r)

# 完整提交（新字段）
r = requests.post(B + '/clues', json={
    'title': 'IC课题：某厂商发布新一代电源管理芯片', 'content': '网络调研发现，该芯片性能提升30%',
    'source': '厂商官网新闻', 'scene': '网络调研', 'acquired_at': '2026-11-07 09:00',
    'depts': ['IC', '原价'], 'material': '电子料', 'category': '技术趋势', 'channel': '网络调研',
    'keywords': ['电源芯片', '新品'], 'credibility': '高',
}, headers=H)
cid = r.json()['id']
print('create:', r.json()['depts'], r.json()['material'], r.json()['category'], r.json()['channel'])

# 多维筛选
for p in [{'dept': '原价'}, {'material': '电子料'}, {'channel': '网络调研'}, {'category': '技术趋势'}, {'dept': 'IC', 'material': '电子料'}]:
    n = requests.get(B + '/clues', params=p, headers=H).json()['total']
    print('filter', p, '->', n)

# 看板
s = requests.get(B + '/admin/stats', headers=H).json()
print('stats:', {k: s[k] for k in ('total', 'users', 'today', 'week')})
print('by_dept:', s['by_dept'])

# 标签体系管理
tax = requests.get(B + '/admin/taxonomy', headers=H).json()
tax['topics']['原价'].append('测试主题')
print('put taxonomy:', requests.put(B + '/admin/taxonomy', json=tax, headers=H).json())
tax2 = requests.get(B + '/admin/taxonomy', headers=H).json()
print('taxonomy updated:', '测试主题' in tax2['topics']['原价'])
tax2['topics']['原价'].remove('测试主题')
requests.put(B + '/admin/taxonomy', json=tax2, headers=H)

# AI 开关（默认关）
st = requests.get(B + '/admin/settings', headers=H).json()
print('settings:', st)
print('AI默认本地引擎验证:', requests.post(B + '/ai/suggest', json={'title': 'AI视觉检测新技术'}, headers=H).json()['engine'])

# 导出含新字段
r = requests.get(B + '/admin/export', headers=H)
print('export bytes:', len(r.content))
print('ALL V2 TESTS DONE')
