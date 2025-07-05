import os
import shutil
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, END, MULTIPLE

# 支持的明文格式
TEXT_EXTS = {'.xml', '.txt', '.json', '.model', '.visual', '.fx', '.mfm', '.gui'}

def is_text_file(filename):
    return os.path.splitext(filename)[1].lower() in TEXT_EXTS

def extract_paths_from_text(content):
    # 支持 ./、../、空格、引号包裹
    pattern = r'["\']?([\.]{0,2}[a-zA-Z0-9_\-/\\\.]+?\.[a-zA-Z0-9]+)["\']?'
    matches = re.findall(pattern, content)
    filtered = []
    valid_exts = {'.visual', '.model', '.fx', '.png', '.jpg', '.dds', '.tga', '.bmp', '.mfm', '.xml', '.gui'}
    for m in matches:
        m = m.strip().lstrip('./\\')  # 去除前导 ./、\\、空格
        try:
            float(m)
            continue
        except ValueError:
            pass
        if '/' not in m and '\\' not in m:
            continue
        ext = os.path.splitext(m)[1].lower()
        if ext not in valid_exts:
            continue
        filtered.append(os.path.normpath(m))
    return filtered

class ResourceFixerUI:
    def __init__(self, root):
        self.root = root
        root.title("BigWorld资源修复工具")
        self.setup_ui()
        self.missing_list = []
        self.found_list = []

    def setup_ui(self):
        # 目录选择
        frm_dirs = tk.Frame(self.root)
        frm_dirs.pack(fill='x')
        self.dir_vars = [tk.StringVar() for _ in range(4)]
        dir_labels = ["修复目录", "参考目录1", "参考目录2", "参考目录3"]
        for i in range(4):
            tk.Label(frm_dirs, text=dir_labels[i]).grid(row=i, column=0, sticky='e')
            tk.Entry(frm_dirs, textvariable=self.dir_vars[i], width=60).grid(row=i, column=1)
            tk.Button(frm_dirs, text="选择", command=lambda idx=i: self.choose_dir(idx)).grid(row=i, column=2)

        # 列表区
        frm_lists = tk.Frame(self.root)
        frm_lists.pack(fill='both', expand=True)
        tk.Label(frm_lists, text="缺失资源路径").grid(row=0, column=0)
        tk.Label(frm_lists, text="参考目录找到的文件").grid(row=0, column=1)
        self.listbox1 = tk.Listbox(frm_lists, width=60, height=20, selectmode=MULTIPLE)
        self.listbox2 = tk.Listbox(frm_lists, width=60, height=20, selectmode=MULTIPLE)
        self.listbox1.grid(row=1, column=0, padx=5, pady=5)
        self.listbox2.grid(row=1, column=1, padx=5, pady=5)

        # 按钮区
        frm_btns = tk.Frame(self.root)
        frm_btns.pack(fill='x')
        tk.Button(frm_btns, text="检索", command=self.threaded(self.scan_missing)).pack(side='left', padx=10, pady=5)
        tk.Button(frm_btns, text="查找", command=self.threaded(self.search_found)).pack(side='left', padx=10, pady=5)
        tk.Button(frm_btns, text="修复", command=self.threaded(self.do_fix)).pack(side='left', padx=10, pady=5)

        # 日志区
        tk.Label(self.root, text="日志输出").pack()
        self.log_text = tk.Text(self.root, height=10, state='disabled')
        self.log_text.pack(fill='both', expand=True)

    def choose_dir(self, idx):
        d = filedialog.askdirectory()
        if d:
            self.dir_vars[idx].set(d)

    def log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(END, msg + '\n')
        self.log_text.see(END)
        self.log_text.config(state='disabled')
        self.root.update()

    def threaded(self, func):
        def wrapper():
            t = threading.Thread(target=func)
            t.start()
        return wrapper

    def scan_missing(self):
        self.listbox1.delete(0, END)
        self.missing_list.clear()
        fix_dir = self.dir_vars[0].get()
        if not fix_dir or not os.path.isdir(fix_dir):
            self.log("请先选择有效的修复目录！")
            return
        self.log("开始检索缺失资源...")
        all_refs = set()
        for dirpath, _, filenames in os.walk(fix_dir):
            for fname in filenames:
                if is_text_file(fname):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        refs = extract_paths_from_text(content)
                        for ref in refs:
                            ref = os.path.normpath(ref.strip().lstrip('/\\'))  # 标准化
                            if len(ref) < 5 or ref.count('.') == 0:
                                continue
                            abs_ref = os.path.normpath(os.path.join(fix_dir, ref))
                            if not os.path.exists(abs_ref):
                                all_refs.add(ref)
                    except Exception as e:
                        self.log(f"读取文件失败: {fpath} {e}")
        self.missing_list = sorted(all_refs)
        for ref in self.missing_list:
            self.listbox1.insert(END, ref)
        self.log(f"检索完成，共发现缺失资源 {len(self.missing_list)} 个。")

    def search_found(self):
        self.listbox2.delete(0, END)
        self.found_list.clear()
        ref_dirs = [self.dir_vars[i].get() for i in range(1, 4) if self.dir_vars[i].get()]
        if not ref_dirs:
            self.log("请至少选择一个参考目录！")
            return
        self.log("开始查找参考目录中的资源...")
        for ref in self.missing_list:
            fname = os.path.basename(ref)
            fext = os.path.splitext(ref)[1].lower()
            found = False
            for ref_dir in ref_dirs:
                for dirpath, _, filenames in os.walk(ref_dir):
                    for f in filenames:
                        if f.lower() == fname.lower() and os.path.splitext(f)[1].lower() == fext:
                            found_path = os.path.join(dirpath, f)
                            self.found_list.append((ref, found_path))
                            self.listbox2.insert(END, f"{ref}  <--  {found_path}")
                            found = True
                            break
                    if found:
                        break
                if found:
                    break
            if not found:
                self.listbox2.insert(END, f"{ref}  <--  未找到")
        self.log(f"查找完成，找到 {len(self.found_list)} 个可修复资源。")

    def do_fix(self):
        fix_dir = self.dir_vars[0].get()
        if not fix_dir or not os.path.isdir(fix_dir):
            self.log("请先选择有效的修复目录！")
            return
        self.log("开始修复缺失资源...")
        count = 0
        for ref, src_path in self.found_list:
            if not os.path.exists(src_path):
                self.log(f"源文件不存在: {src_path}")
                continue
            dst_path = os.path.normpath(os.path.join(fix_dir, ref))
            dst_dir = os.path.dirname(dst_path)
            try:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                self.log(f"已修复: {ref}  <--  {src_path}")
                count += 1
            except Exception as e:
                self.log(f"修复失败: {ref}  <--  {src_path}  错误: {e}")
        self.log(f"修复完成，共修复 {count} 个资源。")

if __name__ == '__main__':
    root = tk.Tk()
    app = ResourceFixerUI(root)
    root.mainloop()