def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='gbk') as f:
            return f.read()

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_samples(text):
    samples = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.replace('\t', ',').replace(';', ',').split(',')
        if len(parts) >= 2:
            path = parts[0].strip()
            hash_str = parts[1].strip()
            try:
                if hash_str.lower().startswith('0x'):
                    hash_val = int(hash_str, 16)
                else:
                    hash_val = int(hash_str)
                samples.append((path, hash_val))
            except Exception:
                continue
        elif len(parts) == 1:
            path = parts[0].strip()
            if path:
                samples.append((path, None))
    return samples
