import os
import tkinter as tk
from tkinter import filedialog, END, ttk, messagebox
import threading
import struct
import subprocess

class UnpackerUI:
    def __init__(self, root):
        self.root = root
        root.title("WDF批量解包工具")
        root.geometry('600x420')
        root.minsize(520, 350)
        self.setup_ui()
        self._stop = False

    def setup_ui(self):
        # 主体分为左右两栏
        frm_main = tk.Frame(self.root)
        frm_main.pack(fill='both', expand=True, padx=10, pady=10)
        frm_left = tk.Frame(frm_main)
        frm_left.grid(row=0, column=0, sticky='nsew')
        frm_right = tk.Frame(frm_main)
        frm_right.grid(row=0, column=1, sticky='nsew', padx=(10,0))
        frm_main.grid_columnconfigure(0, weight=3)
        frm_main.grid_columnconfigure(1, weight=1)
        frm_main.grid_rowconfigure(0, weight=1)

        # 左侧：文件路径设置分组
        frm_group = tk.LabelFrame(frm_left, text="文件路径设置", padx=12, pady=10, font=("微软雅黑", 10, "bold"))
        frm_group.pack(fill='x', pady=(0, 8))
        for row_idx, (label, varname, choose_func) in enumerate([
            ("WDF文件:", 'wdf_var', self.choose_wdf),
            ("LST列表:", 'lst_var', self.choose_lst),
            ("工具1路径:", 'tool_var', self.choose_tool),
            ("工具2路径:", 'tool2_var', self.choose_tool2)
        ]):
            tk.Label(frm_group, text=label, width=9, anchor='e', font=("微软雅黑", 10)).grid(row=row_idx, column=0, sticky='e', pady=4)
            setattr(self, varname, tk.StringVar())
            tk.Entry(frm_group, textvariable=getattr(self, varname), width=48, font=("Consolas", 10)).grid(row=row_idx, column=1, padx=6, pady=4, sticky='we')
            tk.Button(frm_group, text="选择", command=choose_func, width=7).grid(row=row_idx, column=2, padx=2, pady=4)
        frm_group.grid_columnconfigure(1, weight=1)

        # 左侧：进度条
        frm_progress = tk.Frame(frm_left)
        frm_progress.pack(fill='x', pady=(0, 8))
        self.progress = ttk.Progressbar(frm_progress, orient='horizontal', length=480, mode='determinate')
        self.progress.pack(fill='x', expand=True)

        # 左侧：按钮区
        frm_btn = tk.Frame(frm_left)
        frm_btn.pack(fill='x', pady=(0, 8))
        frm_btn.grid_columnconfigure(0, weight=1)
        frm_btn.grid_columnconfigure(1, weight=1)
        frm_btn.grid_columnconfigure(2, weight=1)
        btn_unpack = tk.Button(frm_btn, text="解包", command=self.unpack_threaded, height=1, width=10, font=("微软雅黑", 10, "bold"))
        btn_tool = tk.Button(frm_btn, text="工具解包", command=self.tool_unpack, height=1, width=10, font=("微软雅黑", 10, "bold"))
        btn_parse = tk.Button(frm_btn, text="解析", command=self.parse_wdf_threaded, height=1, width=10, font=("微软雅黑", 10, "bold"))
        btn_unpack.grid(row=0, column=0, padx=6, pady=2, sticky='e')
        btn_tool.grid(row=0, column=1, padx=6, pady=2)
        btn_parse.grid(row=0, column=2, padx=6, pady=2, sticky='w')

        # 左侧：主日志栏
        frm_log_group = tk.LabelFrame(frm_left, text="工作日志", padx=10, pady=8, font=("微软雅黑", 10, "bold"))
        frm_log_group.pack(fill='both', expand=True)
        self.log_text = tk.Text(frm_log_group, height=10, state='disabled', font=("Consolas", 10))
        self.log_text.pack(fill='both', expand=True)

        # 右侧：WDF内容日志栏
        frm_wdf_log = tk.LabelFrame(frm_right, text="WDF内容(name/uid)", padx=10, pady=8, font=("微软雅黑", 10, "bold"))
        frm_wdf_log.pack(fill='both', expand=True)
        self.wdf_log_text = tk.Text(frm_wdf_log, width=32, height=10, state='disabled', font=("Consolas", 10))
        self.wdf_log_text.pack(fill='both', expand=True)
        # 直接在日志栏下方添加导出LST按钮
        btn_export_lst = tk.Button(frm_right, text="导出LST", command=self.export_lst, height=1, width=10, font=("微软雅黑", 10, "bold"))
        btn_export_lst.pack(pady=(8, 0), anchor='n')
        self.parsed_names = []

    def choose_wdf(self):
        f = filedialog.askopenfilename(title="选择WDF文件", filetypes=[('WDF文件', '*.wdf'), ('所有文件', '*.*')])
        if f:
            self.wdf_var.set(f)

    def choose_lst(self):
        f = filedialog.askopenfilename(title="选择LST列表文件", filetypes=[('LST文件', '*.lst'), ('所有文件', '*.*')])
        if f:
            self.lst_var.set(f)

    def choose_tool(self):
        f = filedialog.askopenfilename(title="选择解包工具", filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')])
        if f:
            self.tool_var.set(f)

    def choose_tool2(self):
        f = filedialog.askopenfilename(title="选择解包工具2", filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')])
        if f:
            self.tool2_var.set(f)

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

    def unpack_threaded(self):
        t = threading.Thread(target=self.unpack)
        t.start()

    def unpack(self):
        wdf = self.wdf_var.get()
        lst = self.lst_var.get()
        if not (os.path.isfile(wdf) and os.path.isfile(lst)):
            self.log("请正确选择WDF和LST路径！")
            return
        self.log(f"开始解包：\nWDF: {wdf}\nLST: {lst}")
        try:
            from core_unipacker import wdf_unpack
            wdf_unpack(wdf, lst, self.log, self.update_progress)
            self.update_progress(100)
            self.log("解包完成！")
        except Exception as e:
            self.log(f"解包失败: {e}")

    def tool_unpack(self):
        import subprocess
        wdf = self.wdf_var.get()
        lst = self.lst_var.get()
        tool1 = self.tool_var.get()
        tool2 = self.tool2_var.get()
        if not (os.path.isfile(wdf) and os.path.isfile(lst) and os.path.isfile(tool1) and os.path.isfile(tool2)):
            self.log("请正确选择WDF、LST和两个工具路径！")
            return
        base = wdf[:-4] if wdf.lower().endswith('.wdf') else wdf
        self.log(f"[工具解包] 1号工具: {tool1} x {base}")
        self.log(f"[工具解包] 2号工具: {tool2} x {base}")
        def run_tool(tool_path, base, lst, progress_start, progress_end):
            try:
                with open(lst, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                import tempfile
                with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.lst') as tf:
                    for l in lines:
                        tf.write(l + '\n')
                    temp_lst = tf.name
                cmd = [tool_path, 'x', base, temp_lst]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
                total_lines = 0
                for line in proc.stdout:
                    self.log(line.rstrip())
                    total_lines += 1
                    # 进度条分段显示
                    progress = progress_start + (progress_end - progress_start) * min(total_lines, 100) // 100
                    self.update_progress(progress)
                proc.wait()
                self.update_progress(progress_end)
                if proc.returncode == 0:
                    self.log(f"[工具解包] 工具 {tool_path} 解包完成！")
                else:
                    self.log(f"[工具解包] 工具 {tool_path} 进程异常退出，返回码: {proc.returncode}")
            except Exception as e:
                self.log(f"[工具解包] 工具 {tool_path} 调用失败: {e}")
        def run_both_tools():
            run_tool(tool1, base, lst, 0, 50)
            run_tool(tool2, base, lst, 50, 100)
            self.update_progress(100)
        threading.Thread(target=run_both_tools).start()

    def parse_wdf_threaded(self):
        t = threading.Thread(target=self.parse_wdf)
        t.start()

    def parse_wdf(self):
        wdf = self.wdf_var.get()
        self.parsed_names = []
        if not os.path.isfile(wdf):
            self.log("请正确选择WDF路径！")
            return
        self.wdf_log_text.config(state='normal')
        self.wdf_log_text.delete(1.0, END)
        try:
            import struct
            with open(wdf, 'rb') as f:
                header = f.read(12)
                # 调试输出header内容
                print("DEBUG header:", header)
                if len(header) < 12 or (header[:4] != b'WDFP' and header[:4] != b'PFDW'):
                    self.wdf_log_text.insert(END, f"不是有效的WDF文件！\n实际头部: {header[:4]}\n")
                    self.wdf_log_text.config(state='disabled')
                    return
                file_count = struct.unpack('<i', header[4:8])[0]
                index_offset = struct.unpack('<I', header[8:12])[0]
                f.seek(index_offset)
                index_data = f.read(file_count * 32)
                for i in range(file_count):
                    entry = index_data[i*32:(i+1)*32]
                    uid = struct.unpack('<I', entry[:4])[0]
                    name = entry[16:32].split(b'\x00')[0].decode('utf-8', errors='ignore')
                    if name:
                        self.parsed_names.append(name)
                        self.wdf_log_text.insert(END, f"{name} | {uid:08X}\n")
        except Exception as e:
            self.wdf_log_text.insert(END, f"解析失败: {e}\n")
        self.wdf_log_text.config(state='disabled')

    def export_lst(self):
        if not self.parsed_names:
            messagebox.showinfo("无数据", "请先解析WDF文件！")
            return
        file_path = filedialog.asksaveasfilename(defaultextension='.lst', filetypes=[('LST文件', '*.lst')])
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for name in self.parsed_names:
                    f.write(name + '\n')
            messagebox.showinfo("导出成功", f"已导出到: {file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

# --- wdfpck原版算法复刻 ---
def string_adjust(s):
    # 全部转小写，'/'转'\\'，去除首尾空白，兼容多种分隔符
    s = s.strip().replace('/', '\\').replace('\\\\', '\\').lower()
    return s

def wdf_string_id(s):
    import struct
    s = string_adjust(s)
    # 拷贝到长度256的int数组，后补两个魔数
    m = [0] * 70
    b = s.encode('utf-8')[:256]
    # 按4字节一组填充m
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

def wdf_unpack_python(wdf_path, lst_lines, log_func, progress_func):
    import os
    wdf_dir = os.path.dirname(os.path.abspath(wdf_path))
    wdf_name = os.path.splitext(os.path.basename(wdf_path))[0]
    base_dir = os.path.join(wdf_dir, wdf_name)
    with open(wdf_path, 'rb') as f:
        header = f.read(12)
        if len(header) < 12 or header[:4] != b'WDFP':
            log_func("不是有效的WDF文件！")
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
            name = entry[16:32].split(b'\x00')[0].decode('utf-8', errors='ignore')
            file_table.append({'uid': uid, 'offset': offset, 'size': size, 'space': space, 'name': name})
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

if __name__ == '__main__':
    root = tk.Tk()
    app = UnpackerUI(root)
    root.mainloop() 