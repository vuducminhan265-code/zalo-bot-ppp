# test_formatter.py
import json
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('Function department/rag_engine/consolidated_full_with_highlights.json', encoding='utf-8'))
amends = json.load(open('Function department/rag_engine/amendments_nd377_chapter2.json', encoding='utf-8'))

# Map target articles of NĐ 243 to NĐ 377 amendment article
dieu_to_nd377 = {}
for nd377_num, info in amends.items():
    m = re.search(r'Điều (\d+)', info['header'])
    if m:
        target = int(m.group(1))
        dieu_to_nd377[target] = (nd377_num, info['header'])

def format_article(d_num):
    art = data.get(str(d_num))
    if not art:
        return ''
    out = [art['title'], '']
    curr_khoan = None
    curr_diem_block = []
    
    nd377_info = dieu_to_nd377.get(d_num)
    
    for p in art['paragraphs']:
        t = p['text'].strip()
        hl = p['highlighted']
        
        m_k = re.match(r'^(\d+)\.\s*(.*)', t)
        if m_k:
            curr_khoan = m_k.group(1)
            out.append(t)
            # If the Khoản itself is not followed immediately by points or has points,
            # We check if it is amended
            if hl:
                if nd377_info:
                    citation = f"(Căn cứ: Khoản {curr_khoan} Điều {d_num} Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Điều {nd377_info[0]} Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)"
                else:
                    citation = f"(Căn cứ: Khoản {curr_khoan} Điều {d_num} Nghị định 243/2025/NĐ-CP; được sửa đổi, bổ sung bởi Nghị định 377/2026/NĐ-CP ngày 01/10/2026, có hiệu lực từ ngày 01/10/2026)"
            else:
                citation = f"(Căn cứ: Khoản {curr_khoan} Điều {d_num} Nghị định 243/2025/NĐ-CP)"
            out.append(citation)
            out.append('')
        elif re.match(r'^[a-zđ]\)\s*(.*)', t):
            out.append(t)
        else:
            out.append(t)
            
    return '\n'.join(out).strip()

if __name__ == '__main__':
    print(format_article(72))
