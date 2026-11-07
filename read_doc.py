from docx import Document
doc = Document(r'D:\KimiData\kimi\Workspaces\竞赛软件开发\AI竞赛第一期—11.07(1).docx')
for p in doc.paragraphs:
    if p.text.strip():
        print(p.text)
for i, t in enumerate(doc.tables):
    print(f'--- TABLE {i} ---')
    for row in t.rows:
        print(' | '.join(c.text.strip() for c in row.cells))
