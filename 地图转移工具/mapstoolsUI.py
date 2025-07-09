import tkinter as tk
from tkinter import ttk, filedialog
import os
import zipfile
import shutil
import threading
import subprocess

# 颜色定义
BG_MAIN = "#e6f2ff"    # 淡蓝色
BG_A = "#eaffea"       # 淡绿色
BG_B = "#fffbe6"       # 淡黄色

def choose_old_dir():
    path = filedialog.askdirectory(title="选择旧版文件夹")
    if path:
        old_dir_var.set(path)

def choose_new_dir():
    path = filedialog.askdirectory(title="选择新版文件夹")
    if path:
        new_dir_var.set(path)

def list_cdata_with_7z(cdata_path):
    result = subprocess.run(['7z', 'l', cdata_path], capture_output=True, text=True)
    print("7z raw output:\n", result.stdout)  # 打印原始7z输出
    lines = result.stdout.splitlines()
    files = []
    start = False
    for line in lines:
        if line.strip().startswith('----'):
            if not start:
                start = True
                continue
            else:
                break
        if start and line.strip():
            parts = line.split()
            if len(parts) > 5:
                # 统一分隔符为/
                fname = parts[-1].replace('\\', '/')
                files.append(fname)
    return files

def extract_cdata_file_7z(cdata_path, inner_file):
    # 提取单个文件到内存
    result = subprocess.run(['7z', 'x', f'-so', cdata_path, inner_file], capture_output=True)
    if result.returncode == 0:
        return result.stdout
    return None

def scan_cdata_layers(cdata_path):
    layers = []
    dom_paths = []
    # 优先用zipfile
    if zipfile.is_zipfile(cdata_path):
        try:
            with zipfile.ZipFile(cdata_path, 'r') as z:
                for i in range(1, 11):
                    lname = f"terrain2/layer {i}"
                    if lname in z.namelist():
                        layers.append(lname)
                if "terrain2/dominantTextures" in z.namelist():
                    dom_data = z.read("terrain2/dominantTextures")
                    try:
                        dom_str = dom_data.decode('utf-8', errors='ignore')
                        dom_paths = [line.strip() for line in dom_str.replace('\0', '\n').splitlines() if line.strip()]
                    except Exception:
                        dom_paths = [str(dom_data)]
        except Exception:
            pass
    # fallback to 7z
    if not layers:
        files = list_cdata_with_7z(cdata_path)
        print("7z files:", files)  # 调试输出
        for i in range(1, 11):
            lname = f"terrain2/layer {i}"
            if any(lname == f.strip() for f in files):
                layers.append(lname)
        if any("terrain2/dominantTextures" == f.strip() for f in files):
            dom_data = extract_cdata_file_7z(cdata_path, "terrain2/dominantTextures")
            if dom_data:
                try:
                    dom_str = dom_data.decode('utf-8', errors='ignore')
                    dom_paths = [line.strip() for line in dom_str.replace('\0', '\n').splitlines() if line.strip()]
                except Exception:
                    dom_paths = [str(dom_data)]
    return len(layers), dom_paths

def unpack_cdata_files():
    tree.delete(*tree.get_children())
    old_dir = old_dir_var.get()
    if not old_dir or not os.path.isdir(old_dir):
        log_text.insert("end", "请选择有效的旧版文件夹！\n")
        log_text.see("end")
        return
    files = sorted([f for f in os.listdir(old_dir) if f.endswith('.cdata')])
    log_text.insert("end", f"共发现{len(files)}个cdata文件，开始批量解包...\n")
    log_text.see("end")
    success_count = 0
    for idx, fname in enumerate(files, 1):
        cdata_path = os.path.abspath(os.path.join(old_dir, fname))
        out_dir = os.path.splitext(fname)[0]
        out_dir = os.path.abspath(out_dir)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        # 只用7z命令行解包
        cmd = f'7z x "{cdata_path}" -o"{out_dir}" -y'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            success_count += 1
            log_text.insert("end", f"[{idx}/{len(files)}] {fname} 解包成功 -> {out_dir}\n")
        else:
            log_text.insert("end", f"[{idx}/{len(files)}] {fname} 解包失败: {result.stderr}\n")
        log_text.see("end")
    log_text.insert("end", f"全部解包完成！成功：{success_count}，失败：{len(files)-success_count}。\n")
    if success_count == 0:
        log_text.insert("end", "提示：当前目录下的cdata文件可能不是标准zip格式，建议切换到bs等能被7z解包的目录。\n")
    log_text.see("end")

def read_paths():
    sel = tree.selection()
    if not sel:
        log_text.insert("end", "请先在表格中选择一个cdata文件！\n")
        log_text.see("end")
        return
    item = tree.item(sel[0])
    fname = item['values'][1]
    old_dir = old_dir_var.get()
    cdata_path = os.path.join(old_dir, fname)
    cdata_path = os.path.abspath(cdata_path)
    cmd = f'7z l "{cdata_path}"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    log_text.insert("end", f"{fname} 7z l 输出：\n{result.stdout}\n")
    log_text.see("end")

def write_template():
    sel = tree.selection()
    if not sel:
        log_text.insert("end", "请先在表格中选择一个cdata文件！\n")
        log_text.see("end")
        return
    item = tree.item(sel[0])
    fname = item['values'][1]
    old_dir = old_dir_var.get()
    new_dir = new_dir_var.get()
    old_path = os.path.join(old_dir, fname)
    new_path = os.path.join(new_dir, fname)
    if not os.path.exists(new_path):
        log_text.insert("end", f"新版cdata文件不存在: {fname}\n")
        log_text.see("end")
        return
    # 读取旧版layer和dominantTextures
    layers = {}
    dom_data = None
    if zipfile.is_zipfile(old_path):
        try:
            with zipfile.ZipFile(old_path, 'r') as z_old:
                for i in range(1, 11):
                    lname = f"terrain2/layer {i}"
                    if lname in z_old.namelist():
                        layers[lname] = z_old.read(lname)
                if "terrain2/dominantTextures" in z_old.namelist():
                    dom_data = z_old.read("terrain2/dominantTextures")
        except Exception:
            pass
    if not layers:
        files = list_cdata_with_7z(old_path)
        for i in range(1, 11):
            lname = f"terrain2/layer {i}"
            if lname in files:
                layers[lname] = extract_cdata_file_7z(old_path, lname)
        if "terrain2/dominantTextures" in files:
            dom_data = extract_cdata_file_7z(old_path, "terrain2/dominantTextures")
    try:
        shutil.copy2(new_path, new_path + ".bak")
        with zipfile.ZipFile(new_path, 'a') as z_new:
            for lname, ldata in layers.items():
                z_new.writestr(lname, ldata)
            if dom_data:
                z_new.writestr("terrain2/dominantTextures", dom_data)
        log_text.insert("end", f"{fname} 写入模板成功！\n")
    except Exception as e:
        log_text.insert("end", f"{fname} 写入模板失败: {e}\n")
    log_text.see("end")

def batch_migrate_thread():
    old_dir = old_dir_var.get()
    new_dir = new_dir_var.get()
    if not old_dir or not os.path.isdir(old_dir):
        log_text.insert("end", "请选择有效的旧版文件夹！\n")
        log_text.see("end")
        return
    if not new_dir or not os.path.isdir(new_dir):
        log_text.insert("end", "请选择有效的新版文件夹！\n")
        log_text.see("end")
        return
    old_files = sorted([f for f in os.listdir(old_dir) if f.endswith('.cdata')])
    new_files = sorted([f for f in os.listdir(new_dir) if f.endswith('.cdata')])
    mapping = {f: f for f in old_files if f in new_files}
    total = len(mapping)
    progress["maximum"] = total
    log_text.insert("end", f"开始批量迁移，共{total}个cdata文件...\n")
    log_text.see("end")
    for idx, fname in enumerate(mapping, 1):
        old_path = os.path.join(old_dir, fname)
        new_path = os.path.join(new_dir, fname)
        # 读取旧版layer和dominantTextures
        layers = {}
        dom_data = None
        if zipfile.is_zipfile(old_path):
            try:
                with zipfile.ZipFile(old_path, 'r') as z_old:
                    for i in range(1, 11):
                        lname = f"terrain2/layer {i}"
                        if lname in z_old.namelist():
                            layers[lname] = z_old.read(lname)
                    if "terrain2/dominantTextures" in z_old.namelist():
                        dom_data = z_old.read("terrain2/dominantTextures")
            except Exception:
                pass
        if not layers:
            files = list_cdata_with_7z(old_path)
            for i in range(1, 11):
                lname = f"terrain2/layer {i}"
                if lname in files:
                    layers[lname] = extract_cdata_file_7z(old_path, lname)
            if "terrain2/dominantTextures" in files:
                dom_data = extract_cdata_file_7z(old_path, "terrain2/dominantTextures")
        try:
            shutil.copy2(new_path, new_path + ".bak")
            with zipfile.ZipFile(new_path, 'a') as z_new:
                for lname, ldata in layers.items():
                    z_new.writestr(lname, ldata)
                if dom_data:
                    z_new.writestr("terrain2/dominantTextures", dom_data)
            log_text.insert("end", f"[{idx}/{total}] {fname} 迁移成功\n")
        except Exception as e:
            log_text.insert("end", f"[{idx}/{total}] {fname} 迁移失败: {e}\n")
        progress["value"] = idx
        root.update_idletasks()
    log_text.insert("end", "批量迁移完成！\n")
    log_text.see("end")

def batch_migrate():
    threading.Thread(target=batch_migrate_thread).start()

root = tk.Tk()
root.geometry("800x600")
root.title("BigWorld cdata自动迁移工具")
root.configure(bg=BG_MAIN)

# 左侧A组
frame_a = tk.Frame(root, width=400, height=600, bg=BG_A, bd=2, relief="groove")
frame_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

# 右侧B组
frame_b = tk.Frame(root, width=400, height=600, bg=BG_B, bd=2, relief="groove")
frame_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# 1. 旧版文件夹输入
old_dir_var = tk.StringVar()
tk.Label(frame_a, text="旧版文件夹:", bg=BG_A, font=("微软雅黑", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=8)
tk.Entry(frame_a, textvariable=old_dir_var, width=24, font=("微软雅黑", 10)).grid(row=0, column=1, padx=2)
tk.Button(frame_a, text="选择", command=choose_old_dir, width=7).grid(row=0, column=2, padx=5)

# 2. 新版文件夹输入
new_dir_var = tk.StringVar()
tk.Label(frame_a, text="新版文件夹:", bg=BG_A, font=("微软雅黑", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=8)
tk.Entry(frame_a, textvariable=new_dir_var, width=24, font=("微软雅黑", 10)).grid(row=1, column=1, padx=2)
tk.Button(frame_a, text="选择", command=choose_new_dir, width=7).grid(row=1, column=2, padx=5)

# 3. 功能按钮区（单独一行，居中）
btn_frame = tk.Frame(frame_a, bg=BG_A)
btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
btns = [
    ("解包", unpack_cdata_files),
    ("读取路径", read_paths),
    ("写入模板", write_template),
    ("替换/覆盖文件", batch_migrate)
]
for i, (text, cmd) in enumerate(btns):
    ttk.Button(btn_frame, text=text, command=cmd, width=12).grid(row=0, column=i, padx=5)

# 4. 进度条
progress = ttk.Progressbar(frame_a, length=370, mode='determinate')
progress.grid(row=3, column=0, columnspan=3, pady=8, padx=10)

# 5. 信息列表
columns = ("序号", "cdata名称", "层信息", "路径信息")
tree = ttk.Treeview(frame_a, columns=columns, show="headings", height=16)
for i, col in enumerate(columns):
    width = [30, 90, 120, 140][i]
    tree.heading(col, text=col)
    tree.column(col, width=width, anchor="w")
tree.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
scrollbar = tk.Scrollbar(frame_a, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.grid(row=4, column=3, sticky="ns")

# 右侧日志区
log_label = tk.Label(frame_b, text="日志信息", bg=BG_B, font=("微软雅黑", 10, "bold"))
log_label.pack(anchor="nw", padx=8, pady=5)
log_text = tk.Text(frame_b, wrap="word", font=("微软雅黑", 10), bg="#fffff0", relief="sunken", bd=2)
log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
log_scroll = tk.Scrollbar(log_text, command=log_text.yview)
log_text.configure(yscrollcommand=log_scroll.set)
log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

root.mainloop()