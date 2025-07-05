import os
import struct
from hash_algorithms import calc_hash
from wdf_parser import parse_wdf_index

# 定义BMP/TGA头部结构体
BMP_FILE_HEADER_FMT = '<HIHHI'  # 14字节
BMP_INFO_HEADER_FMT = '<IIIHHIIIIII'  # 40字节
TGA_HEADER_FMT = '<BBBHHBHHHHBB'  # 18字节
BUFFER_SIZE = 1024

def export_matched_files(wdf_path, matched_items, out_dir):
    """
    wdf_path: WDF包路径
    matched_items: [(path, uid, offset, size)]
    out_dir: 导出根目录
    """
    with open(wdf_path, 'rb') as f:
        for path, uid, offset, size in matched_items:
            if not path or offset is None or size is None or size <= 0:
                continue
            save_path = os.path.join(out_dir, path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            f.seek(offset)
            ext = os.path.splitext(path)[1].lower()
            with open(save_path, 'wb') as out_f:
                remain = size
                # BMP特殊处理
                if ext == '.bmp' and remain >= 54:
                    bmp_file_header = f.read(14)
                    bmp_info_header = f.read(40)
                    out_f.write(bmp_file_header)
                    out_f.write(bmp_info_header)
                    remain -= 54
                # TGA特殊处理
                elif ext == '.tga' and remain >= 18:
                    tga_header = f.read(18)
                    out_f.write(tga_header)
                    remain -= 18
                # 其他文件无头部特殊处理
                while remain > 0:
                    chunk = f.read(min(BUFFER_SIZE, remain))
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remain -= len(chunk)

def export_by_samples(
    wdf_path, sample_paths, out_dir,
    algo_name, case_sensitive=False, seed=None
):
    """
    根据样本路径列表，重新计算哈希并比对WDF索引，导出命中资源。
    wdf_path: WDF包路径
    sample_paths: [str]，样本路径列表
    out_dir: 导出目录
    algo_name: 哈希算法名
    case_sensitive: 是否区分大小写
    seed: 哈希算法种子
    """
    # 解析索引
    index_entries = parse_wdf_index(wdf_path)
    uid_map = {e['uid']: e for e in index_entries}
    matched_items = []
    for path in sample_paths:
        hash_val = calc_hash(algo_name, path, case_sensitive, seed)
        entry = uid_map.get(hash_val)
        if entry:
            matched_items.append(
                (path, hash_val, entry['offset'], entry['size'])
            )
    # 调用原有导出
    export_matched_files(wdf_path, matched_items, out_dir)

def export_by_lst(
    wdf_path, lst_path, out_dir,
    algo_name, case_sensitive=False, seed=None
):
    """
    直接读取lst文件，自动比对并导出命中资源。
    wdf_path: WDF包路径
    lst_path: lst文件路径
    out_dir: 导出目录
    algo_name: 哈希算法名
    case_sensitive: 是否区分大小写
    seed: 哈希算法种子
    """
    # 解析WDF索引
    index_entries = parse_wdf_index(wdf_path)
    uid_map = {e['uid']: e for e in index_entries}
    # 读取lst文件
    with open(lst_path, 'r', encoding='utf-8') as f:
        sample_paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    # 命中比对并导出
    matched_items = []
    for path in sample_paths:
        hash_val = calc_hash(algo_name, path, case_sensitive, seed)
        entry = uid_map.get(hash_val)
        if entry:
            matched_items.append((path, hash_val, entry['offset'], entry['size']))
    export_matched_files(wdf_path, matched_items, out_dir) 