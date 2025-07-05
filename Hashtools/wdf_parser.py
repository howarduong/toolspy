import struct

def parse_wdf_index(filepath):
    """
    解析.wdf文件，返回资源索引信息列表：
    [{uid, offset, size, space} ...]
    """
    entries = []
    with open(filepath, 'rb') as f:
        # 读取文件头
        header = f.read(12)
        if len(header) < 12:
            raise ValueError('文件头长度不足')
        id_bytes, number, index_offset = struct.unpack('<4sII', header)
        print(f"[调试] 文件头原始内容: {id_bytes}")
        # 宽松判断：只要包含WDF即可
        if not (b'WDF' in id_bytes or b'WDF' in id_bytes[::-1]):
            raise ValueError(f'不是有效的WDF文件，文件头为: {id_bytes}')
        # 跳转到索引区
        f.seek(index_offset)
        for _ in range(number):
            entry = f.read(16)
            if len(entry) < 16:
                break
            uid, offset, size, space = struct.unpack('<IIII', entry)
            entries.append({'uid': uid, 'offset': offset, 'size': size, 'space': space})
    return entries

def export_index_to_txt(entries, out_path):
    """
    将索引信息导出为文本（uid, offset, size, space）
    """
    with open(out_path, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(f"0x{e['uid']:08X},{e['offset']},{e['size']},{e['space']}\n")

