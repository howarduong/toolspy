def wdfpck_hash(string, seed=None, case_sensitive=False):
    # string_adjust: 全部转小写，/转为\
    s = string.lower().replace('/', '\\')
    # 拷贝到 70 个 unsigned int 的数组（最多 256 字节）
    m = [0] * 70
    b = s.encode('utf-8')[:256]
    for i in range(0, len(b), 4):
        m[i // 4] = int.from_bytes(b[i:i+4].ljust(4, b'\0'), 'little')
    i = 0
    while i < 256 // 4 and m[i]:
        i += 1
    m[i] = 0x9BE74448
    m[i+1] = 0x66F42C48
    v = 0xF4FA8928
    x = 0x37A8470E
    y = 0x7758B42B
    idx = 0
    while idx < i+2:
        w = 0x267B0B11
        v = ((v << 1) | (v >> 31)) & 0xFFFFFFFF  # rol v,1
        ebx = w ^ v
        eax = m[idx]
        x ^= eax
        y ^= eax
        edx = ebx + y
        edx = (edx | 0x2040801) & 0xBFEF7FDF
        # eax = x * edx + edx
        eax1 = (x * edx + edx) & 0xFFFFFFFF
        edx2 = ebx + x
        edx2 = (edx2 | 0x804021) & 0x7DFEFBFF
        # esi = eax1
        # edi = y
        # eax = edi * edx2
        eax2 = (y * edx2) & 0xFFFFFFFF
        edx3 = (edx2 * 2) & 0xFFFFFFFF
        eax2 = (eax2 + edx3) & 0xFFFFFFFF
        if eax2 < edx3:
            eax2 = (eax2 + 2) & 0xFFFFFFFF
        y = eax2
        idx += 1
    v = x ^ y
    return v & 0xFFFFFFFF

def BKDRHash(string, seed=131, case_sensitive=False):
    if not case_sensitive:
        string = string.lower()
    hash_val = 0
    for ch in string:
        hash_val = hash_val * seed + ord(ch)
    return hash_val & 0x7FFFFFFF

def CRC32Hash(string, seed=0, case_sensitive=False):
    import zlib
    if not case_sensitive:
        string = string.lower()
    return zlib.crc32(string.encode('utf-8')) & 0xFFFFFFFF

def DJBHash(string, seed=5381, case_sensitive=False):
    if not case_sensitive:
        string = string.lower()
    hash_val = seed
    for ch in string:
        hash_val = ((hash_val << 5) + hash_val) + ord(ch)
    return hash_val & 0xFFFFFFFF

def get_algorithm_names():
    return ['wdfpck_hash', 'BKDRHash', 'CRC32Hash', 'DJBHash']

def calc_hash(algo_name, string, case_sensitive, seed):
    if algo_name == 'wdfpck_hash':
        return wdfpck_hash(string, None, case_sensitive)
    elif algo_name == 'BKDRHash':
        return BKDRHash(string, seed, case_sensitive)
    elif algo_name == 'CRC32Hash':
        return CRC32Hash(string, seed, case_sensitive)
    elif algo_name == 'DJBHash':
        return DJBHash(string, seed, case_sensitive)
    else:
        raise ValueError(f'未知算法: {algo_name}')
