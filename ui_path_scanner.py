import os
import re
import tkinter as tk
from tkinter import filedialog, END, ttk, messagebox
import threading
import csv
import time
import concurrent.futures

# 常用后缀名
COMMON_EXTS = (
    '.dds', '.model', '.bmp', '.xml', '.wav', '.tga', '.texanim', '.visual',
    '.primitives', '.mfm', '.py', '.fxo', '.gui', '.json', '.html', '.cab',
    '.asp', '.ppchain', '.mp3', '.animation', '.png', '.chunk', '.fx'
)

# 路径前缀
PREFIXES = [
    "char/", "flora/", "effect/", "env/", "item/", "light/", "music/", "particle/", "shaders/", "sound/", "system/", "tex/", "gui/",
    "smap/", "entities/", "com/", "player/", "ani/", "jm/", "bj/", "bs/", "cy/", "dk/", "gl/", "gm/", "hq/", "jl/", "jn/", "kl/", "ls/",
    "xy/", "yc/", "zb/", "zy/", "zz/", "test/", "test3/", "zb/", "yl/", "jl/", "jn/", "hq/", "bs/", "jwh/", "zy/", "zz/", "jm/", "jm_bx/",
    "jm_hh/", "jm_jndk/", "jm_ly/", "jm_tj/", "jm_tx/", "jm_wl/", "jm_yq/", "jm_yj/", "jm_yl/", "jm_zydk/", "zjm/", "tl/", "gm01/", "gm02/"
]

def extract_paths(line, exts=COMMON_EXTS, prefixes=PREFIXES):
    results = []
    lower_line = line.lower()
    search_start = 0
    while True:
        # 找到最靠前的前缀
        prefix_pos = -1
        prefix_val = ""
        for prefix in prefixes:
            pos = lower_line.find(prefix, search_start)
            if pos != -1 and (prefix_pos == -1 or pos < prefix_pos):
                prefix_pos = pos
                prefix_val = prefix
        if prefix_pos == -1:
            break
        # 找到后缀
        ext_pos = -1
        ext_val = ""
        for ext in exts:
            pos = lower_line.find(ext, prefix_pos)
            if pos != -1 and (ext_pos == -1 or pos < ext_pos):
                ext_pos = pos
                ext_val = ext
        if ext_pos == -1:
            break
        end = ext_pos + len(ext_val)
        path = line[prefix_pos:end]
        # 截断遇到<或>
        for ch in ['<', '>']:
            cut = path.find(ch)
            if cut != -1:
                path = path[:cut]
        path = path.strip()
        if path:
            results.append(path)
        search_start = end
    return results

class PathScannerUI:
    def __init__(self, root):
        self.root = root
        self.status_var = tk.StringVar()
        self.status_var.set("速度/用时：-")
        self.setup_ui()
        self.matches = []  # [(rel_path, match_path)]
        self.total_files = 0
        self.scanned_files = 0
        self._stop = False

    def setup_ui(self):
        frm_top = tk.Frame(self.root)
        frm_top.pack(fill='x', padx=5, pady=5)
        tk.Label(frm_top, text="检索目录:").pack(side='left')
        self.dir_var = tk.StringVar()
        tk.Entry(frm_top, textvariable=self.dir_var, width=60).pack(side='left', padx=5)
        tk.Button(frm_top, text="选择", command=self.choose_dir).pack(side='left')
        tk.Button(frm_top, text="检索", command=self.scan_threaded).pack(side='left', padx=10)
        tk.Button(frm_top, text="复检", command=self.recheck_threaded).pack(side='left', padx=5)
        tk.Button(frm_top, text="模型补全", command=self.model_complete_threaded).pack(side='left', padx=5)
        tk.Button(frm_top, text="导出CSV", command=self.export_csv).pack(side='left', padx=5)
        self.progress = ttk.Progressbar(self.root, orient='horizontal', length=400, mode='determinate')
        self.progress.pack(fill='x', padx=5, pady=2)
        frm_log = tk.Frame(self.root)
        frm_log.pack(fill='both', expand=False, padx=5, pady=2)
        tk.Label(frm_log, text="日志输出").pack(anchor='w')
        self.log_text = tk.Text(frm_log, height=8, state='disabled')
        self.log_text.pack(fill='both', expand=True)
        frm_result = tk.Frame(self.root)
        frm_result.pack(fill='both', expand=True, padx=5, pady=2)
        tk.Label(frm_result, text="检索到的路径/地址（列表）").pack(anchor='w')
        columns = ("序号", "相对路径", "检索路径")
        self.tree = ttk.Treeview(frm_result, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=300 if col != "序号" else 60, anchor='w')
        self.tree.column("序号", width=60, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frm_result, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tk.Label(frm_top, textvariable=self.status_var, width=30).pack(side='left', padx=5)

    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.dir_var.set(d)

    def log(self, msg):
        def _log():
            self.log_text.config(state='normal')
            self.log_text.insert(END, msg + '\n')
            self.log_text.see(END)
            self.log_text.config(state='disabled')
        self.root.after(0, _log)

    def update_progress(self, value):
        def _update():
            self.progress['value'] = value
        self.root.after(0, _update)

    def clear_tree(self):
        def _clear():
            for i in self.tree.get_children():
                self.tree.delete(i)
        self.root.after(0, _clear)

    def insert_tree_row(self, idx, rel_path, match_path):
        def _insert():
            self.tree.insert('', 'end', values=(idx, rel_path, match_path))
        self.root.after(0, _insert)

    def scan_threaded(self):
        self._stop = False
        t = threading.Thread(target=self.scan)
        t.start()

    def scan(self):
        self.matches.clear()
        self.clear_tree()
        scan_dir = self.dir_var.get()
        if not scan_dir or not os.path.isdir(scan_dir):
            self.log("请先选择有效的检索目录！")
            return
        self.log(f"开始递归检索: {scan_dir}")
        workspace_root = os.path.abspath(os.getcwd())
        self.total_files = sum(len(files) for _, _, files in os.walk(scan_dir))
        self.scanned_files = 0
        self.update_progress(0)
        prefix_bytes = [p.encode('utf-8') for p in PREFIXES]
        self.start_time = time.time()
        file_list = []
        for dirpath, _, filenames in os.walk(scan_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                rel_file_path = os.path.relpath(fpath, workspace_root)
                file_list.append((fpath, rel_file_path))
        lock = threading.Lock()
        unique_set = set()
        self.matches = []
        def process_file(fpath, rel_file_path):
            try:
                with open(fpath, 'rb') as f:
                    content = f.read()
                for prefix in prefix_bytes:
                    start = 0
                    while True:
                        start = content.find(prefix, start)
                        if start == -1:
                            break
                        end = start
                        while end < len(content) and content[end] not in b'\x00 \r\n;,\"\')':
                            end += 1
                        match = content[start:end].decode('utf-8', errors='ignore')
                        if match:
                            rel_path = rel_file_path
                            match_path = match
                            with lock:
                                if (rel_path, match_path) not in unique_set:
                                    unique_set.add((rel_path, match_path))
                                    self.matches.append((rel_path, match_path))
                        start = end
            except Exception as e:
                self.log(f"读取文件失败: {fpath} {e}")
            with lock:
                self.scanned_files += 1
                elapsed = time.time() - self.start_time
                speed = self.scanned_files / elapsed if elapsed > 0 else 0
                self.status_var.set(f"速度: {speed:.1f} 文件/秒  用时: {elapsed:.1f} 秒")
                self.update_progress(self.scanned_files * 100 // self.total_files)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_file, fpath, rel_file_path) for fpath, rel_file_path in file_list]
            concurrent.futures.wait(futures)
        self.update_progress(100)
        elapsed = time.time() - self.start_time
        speed = self.scanned_files / elapsed if elapsed > 0 else 0
        self.status_var.set(f"速度: {speed:.1f} 文件/秒  用时: {elapsed:.1f} 秒")
        self.log(f"检索完成，共发现 {len(self.matches)} 个路径/地址。")

        self.clear_tree()
        for idx, (rel_path, match_path) in enumerate(self.matches, 1):
            self.insert_tree_row(idx, rel_path, match_path)

    def recheck_threaded(self):
        t = threading.Thread(target=self._recheck_impl)
        t.start()

    def _recheck_impl(self):
        total = len(self.matches)
        changed = 0
        added = 0
        new_matches = []
        self.update_progress(0)
        for idx, (rel_path, match_path) in enumerate(self.matches):
            paths = extract_paths(match_path)
            if paths:
                if paths[0] != match_path:
                    changed += 1
                new_matches.append((rel_path, paths[0]))
                for extra_path in paths[1:]:
                    new_matches.append((rel_path, extra_path))
                    added += 1
            else:
                new_matches.append((rel_path, match_path))
            if total > 0 and idx % 10 == 0:
                self.update_progress(idx * 100 // total)
        self.matches = new_matches
        self.update_progress(100)
        self.clear_tree()
        for idx, (rel_path, match_path) in enumerate(self.matches, 1):
            self.insert_tree_row(idx, rel_path, match_path)
        self.log(f"复检完成，共处理 {total} 条，修改 {changed} 条，新增 {added} 条。")

    def model_complete_threaded(self):
        t = threading.Thread(target=self._model_complete_impl)
        t.start()

    def _model_complete_impl(self):
        # 规则：遇到 .dds/.primitives/.visual/.model 补全其余三种后缀
        SUFFIXES = ['.dds', '.primitives', '.visual', '.model']
        total = len(self.matches)
        added = 0
        new_matches = list(self.matches)
        exist_set = set((rel_path, match_path.lower()) for rel_path, match_path in self.matches)
        self.update_progress(0)
        for idx, (rel_path, match_path) in enumerate(self.matches):
            lower = match_path.lower()
            for suf in SUFFIXES:
                if lower.endswith(suf):
                    base = match_path[:-len(suf)]
                    for other in SUFFIXES:
                        if other != suf:
                            new_path = base + other
                            # 避免重复
                            if (rel_path, new_path.lower()) not in exist_set:
                                new_matches.append((rel_path, new_path))
                                exist_set.add((rel_path, new_path.lower()))
                                added += 1
                    break  # 只补全一次
            if total > 0 and idx % 10 == 0:
                self.update_progress(idx * 100 // total)
        self.matches = new_matches
        self.update_progress(100)
        self.clear_tree()
        for idx, (rel_path, match_path) in enumerate(self.matches, 1):
            self.insert_tree_row(idx, rel_path, match_path)
        self.log(f"模型补全完成，共处理 {total} 条，新增 {added} 条。")

    def export_csv(self):
        if not self.matches:
            messagebox.showinfo("无数据", "没有可导出的数据！")
            return
        file_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV文件', '*.csv')])
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["序号", "相对路径", "检索路径"])
                for idx, (rel_path, match_path) in enumerate(self.matches, 1):
                    writer.writerow([idx, rel_path, match_path])
            messagebox.showinfo("导出成功", f"已导出到: {file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

if __name__ == '__main__':
    root = tk.Tk()
    app = PathScannerUI(root)
    root.mainloop() 