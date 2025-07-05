import os
import struct

def string_adjust(s):
    s = s.strip().replace('/', '\\').replace('\\\\', '\\').lower()
    return s

def wdf_string_id(s):
    s = string_adjust(s)
    m = [0] * 70
    b = s.encode('utf-8')[:256]
    for i in range(0, len(b), 4):
        chunk = b[i:i+4]
        val = int.from_bytes(chunk.ljust(4, b'\0'), 'little')
        m[i//4] = val
    i = (len(b) + 3) // 4
    m[i] = 0x9BE74448
    m[i+1] = 0x66F42C48
    v = 0xF4FA8928
    x0 = 0x37A8470E
    y0 = 0x7758B42B
    a = 0x2040801
    b_ = 0x804021
    c = 0xBFEF7FDF
    d = 0x7DFEFBFF
    esi = x0
    edi = y0
    for ecx in range(i+2):
        w = 0x267B0B11
        v = ((v << 1) | (v >> 31)) & 0xFFFFFFFF
        ebx = w ^ v
        eax = m[ecx]
        edx = ebx
        esi ^= eax
        edi ^= eax
        edx = (edx + edi) & 0xFFFFFFFF
        edx = (edx | a) & c
        eax = esi
        eax = (eax * edx) & 0xFFFFFFFF
        eax = (eax + edx) & 0xFFFFFFFF
        edx = ebx
        eax = (eax + 0) & 0xFFFFFFFF
        edx = (edx + esi) & 0xFFFFFFFF
        edx = (edx | b_) & d
        esi = eax
        eax = edi
        eax = (eax * edx) & 0xFFFFFFFF
        eax = (eax + edx) & 0xFFFFFFFF
        if ((eax + edx) & 0xFFFFFFFF) < eax:
            eax = (eax + 2) & 0xFFFFFFFF
        edi = eax
    v = esi ^ edi
    return v & 0xFFFFFFFF

def wdf_unpack(wdf_path, lst_path, log_func, progress_func):
    wdf_dir = os.path.dirname(os.path.abspath(wdf_path))
    wdf_name = os.path.splitext(os.path.basename(wdf_path))[0]
    base_dir = os.path.join(wdf_dir, wdf_name)
    with open(lst_path, 'r', encoding='utf-8') as f:
        lst_lines = [line.strip() for line in f if line.strip()]
    with open(wdf_path, 'rb') as f:
        header = f.read(12)
        valid_magic = [b'WDFP', b'PFDW', b'WDFA', b'AFDW']
        if len(header) < 12 or header[:4] not in valid_magic:
            log_func(f"不是有效的WDF文件！实际头部: {header[:4]}")
            return
        file_count = struct.unpack('<i', header[4:8])[0]
        index_offset = struct.unpack('<I', header[8:12])[0]
        f.seek(index_offset)
        index_data = f.read(file_count * 32)
        file_table = []
        for i in range(file_count):
            entry = index_data[i*32:(i+1)*32]
            uid = struct.unpack('<I', entry[:4])[0]
            offset = struct.unpack('<I', entry[4:8])[0]
            size = struct.unpack('<I', entry[8:12])[0]
            space = struct.unpack('<I', entry[12:16])[0]
            file_table.append({'uid': uid, 'offset': offset, 'size': size, 'space': space})
        uid_map = {e['uid']: e for e in file_table}
        for idx, path in enumerate(lst_lines, 1):
            uid = wdf_string_id(path)
            entry = uid_map.get(uid)
            if entry:
                try:
                    f.seek(entry['offset'])
                    data = f.read(entry['size'])
                    out_path = os.path.join(base_dir, path.replace('/', os.sep))
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, 'wb') as fout:
                        fout.write(data)
                    log_func(f"解包: {path} -> {out_path}")
                except Exception as e:
                    log_func(f"解包失败: {path}，错误: {e}")
            else:
                log_func(f"未找到: {path}")
            progress_func(idx * 100 // len(lst_lines)) 