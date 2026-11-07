import requests
B = 'http://localhost:8000/api'
tok = requests.post(B + '/login', json={'username': 'admin', 'password': 'admin123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}
r = requests.post(B + '/ai/suggest', json={
    'title': '某省拟出台数据安全管理办法',
    'content': '监管部门起草新规，涉及数据采集存储合规要求，预计下月发布'
}, headers=H, timeout=60)
print('suggest:', r.json())
print('meta ai_enabled:', requests.get(B + '/meta', headers=H).json()['ai_enabled'])
