import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import csv
import os
from collections import Counter

A4_WIDTH = 1122  # A4横向像素（约96dpi）
A4_HEIGHT = 794
FONT_FAMILY = "微软雅黑"
FONT_SIZE = 11

class FilterOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("筛选整理器 Filter Organizer")
        self.root.geometry(f"{A4_WIDTH}x{A4_HEIGHT}")
        self.csv_path = tk.StringVar()
        self.suffixes = set()
        self.data = []
        self.headers = []
        self.stop_refresh = False

        # 字体
        self.default_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.title_font = font.Font(family=FONT_FAMILY, size=14, weight="bold")

        # 主框架（横向2/3+1/3分割）
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=2)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # 左侧2/3区域（输入、按钮、表格）
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # 输入区（居中）
        self.input_frame = tk.Frame(self.left_frame)
        self.input_frame.grid(row=0, column=0, pady=(20, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(1, weight=0)
        self.path_entry = tk.Entry(self.input_frame, textvariable=self.csv_path, width=60, font=self.default_font, justify="center")
        self.path_entry.grid(row=0, column=0, padx=5, sticky="ew")
        self.browse_btn = tk.Button(self.input_frame, text="浏览", command=self.browse_file, font=self.default_font)
        self.browse_btn.grid(row=0, column=1, padx=5)

        # 按钮区（居中）
        self.btn_frame = tk.Frame(self.left_frame)
        self.btn_frame.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        self.btn_frame.grid_columnconfigure(0, weight=1)
        self.btn_frame.grid_columnconfigure(1, weight=0)
        self.btn_frame.grid_columnconfigure(2, weight=0)
        self.btn_frame.grid_columnconfigure(3, weight=0)
        self.btn_frame.grid_columnconfigure(4, weight=1)
        self.search_btn = tk.Button(self.btn_frame, text="检索", command=self.load_csv, font=self.default_font, width=10)
        self.search_btn.grid(row=0, column=1, padx=10)
        self.suffix_btn = tk.Button(self.btn_frame, text="后缀", command=self.show_suffixes, font=self.default_font, width=10)
        self.suffix_btn.grid(row=0, column=2, padx=10)
        self.garbled_btn = tk.Button(self.btn_frame, text="处理乱码", command=self.handle_garbled, font=self.default_font, width=10)
        self.garbled_btn.grid(row=0, column=3, padx=10)
        self.filter_btn = tk.Button(self.btn_frame, text="筛选", command=self.filter_by_suffix, font=self.default_font, width=10)
        self.filter_btn.grid(row=0, column=4, padx=10)
        self.export_btn = tk.Button(self.btn_frame, text="导出表格", command=self.export_csv, font=self.default_font, width=10)
        self.export_btn.grid(row=0, column=5, padx=10)

        # 表格区
        self.table_frame = tk.Frame(self.left_frame)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=(20, 5), pady=(0, 20))
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table = ttk.Treeview(self.table_frame, show="headings")
        self.table.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscroll=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        style = ttk.Style()
        style.configure("Treeview", font=(FONT_FAMILY, FONT_SIZE))
        style.configure("Treeview.Heading", font=(FONT_FAMILY, FONT_SIZE, "bold"))

        # 右侧1/3区域（后缀区）
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.grid(row=0, column=1, rowspan=3, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        # 后缀名显示区：上对齐输入区，下对齐表格区
        self.suffix_label = tk.Label(self.right_frame, text="后缀名显示区", font=self.title_font)
        self.suffix_label.grid(row=0, column=0, pady=(20, 10), sticky="n")
        suffix_text_frame = tk.Frame(self.right_frame)
        suffix_text_frame.grid(row=1, column=0, sticky="nsew", padx=(5, 20), pady=(0, 20))
        suffix_text_frame.grid_rowconfigure(0, weight=1)
        suffix_text_frame.grid_columnconfigure(0, weight=1)
        self.suffix_text = tk.Text(suffix_text_frame, width=18, font=self.default_font, height=30)
        self.suffix_text.grid(row=0, column=0, sticky="nsew")
        self.suffix_scrollbar = tk.Scrollbar(suffix_text_frame, orient="vertical", command=self.suffix_text.yview)
        self.suffix_text.configure(yscrollcommand=self.suffix_scrollbar.set)
        self.suffix_scrollbar.grid(row=0, column=1, sticky="ns")

        # 启动定时刷新
        self.refresh_table()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.csv_path.set(file_path)

    def load_csv(self):
        path = self.csv_path.get()
        self.data = []
        self.headers = []
        if not os.path.isfile(path):
            messagebox.showerror("错误", "文件不存在")
            return
        try:
            with open(path, encoding="utf-8") as f:
                reader = csv.reader(f)
                self.headers = next(reader, [])
                self.data = [row for row in reader]
        except Exception:
            try:
                with open(path, encoding="gbk") as f:
                    reader = csv.reader(f)
                    self.headers = next(reader, [])
                    self.data = [row for row in reader]
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
                self.data = []
                self.headers = []
        self.collect_suffixes()

    def refresh_table(self):
        # 清空表格
        for col in self.table["columns"]:
            self.table.heading(col, text="")
        self.table.delete(*self.table.get_children())
        # 设置表头
        if self.headers:
            self.table["columns"] = self.headers
            for col in self.headers:
                self.table.heading(col, text=col)
            # 填充数据（只显示前50行）
            for row in self.data[:50]:
                self.table.insert("", "end", values=row)
        # 1秒后再次刷新
        if not self.stop_refresh:
            self.root.after(1000, self.refresh_table)

    def collect_suffixes(self):
        self.suffixes.clear()
        for row in self.data:
            for cell in row:
                if "." in cell:
                    self.suffixes.add(cell.split(".")[-1])

    def show_suffixes(self):
        # 只检索第三列，提取路径后缀，统计出现次数，显示最多的后缀
        suffix_counter = Counter()
        for row in self.data:
            if len(row) > 2:
                value = row[2]
                if isinstance(value, str) and "." in value:
                    ext = os.path.splitext(value)[1]
                    if ext:  # 只要以点开头，长度不限
                        suffix_counter[ext] += 1
        # 取出现次数最多的后缀，全部列出（按出现次数排序）
        self.suffixes = [item[0] for item in suffix_counter.most_common()]
        self.update_suffix_text()

    def add_suffix(self):
        # 弹窗输入新后缀
        new_suffix = tk.simpledialog.askstring("增加后缀", "请输入新后缀（如 .png）：")
        if new_suffix:
            new_suffix = new_suffix.strip()
            if not new_suffix.startswith('.'):
                new_suffix = '.' + new_suffix
            if new_suffix not in self.suffixes:
                self.suffixes.append(new_suffix)
                self.update_suffix_text()

    def handle_garbled(self):
        # 获取当前后缀名列表（每行一个，去除空行和空格）
        suffix_lines = self.suffix_text.get(1.0, "end").splitlines()
        suffixes = [s.strip() for s in suffix_lines if s.strip()]
        if not suffixes:
            messagebox.showwarning("警告", "后缀名列表为空！")
            return
        changed = False
        for i, row in enumerate(self.data):
            if len(row) > 2:
                path = row[2]
                for suf in suffixes:
                    idx = path.lower().find(suf.lower())
                    if idx != -1:
                        # 保留到后缀名结尾
                        row[2] = path[:idx+len(suf)]
                        changed = True
                        break
        if changed:
            self.refresh_table()
            messagebox.showinfo("完成", "已按后缀名清理乱码内容！")
        else:
            messagebox.showinfo("提示", "未发现可清理的内容。")

    def filter_by_suffix(self):
        # 获取当前后缀名列表（每行一个，去除空行和空格）
        suffix_lines = self.suffix_text.get(1.0, "end").splitlines()
        suffixes = [s.strip().lower() for s in suffix_lines if s.strip()]
        if not suffixes:
            messagebox.showwarning("警告", "后缀名列表为空！")
            return
        filtered_data = []
        for row in self.data:
            if len(row) > 2:
                value = row[2].lower()
                for suf in suffixes:
                    if value.endswith(suf):
                        filtered_data.append(row)
                        break
        removed = len(self.data) - len(filtered_data)
        self.data = filtered_data
        self.refresh_table()
        messagebox.showinfo("筛选完成", f"已筛选，移除 {removed} 行。")

    def export_csv(self):
        if not self.data or not self.headers:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="导出CSV文件")
        if save_path:
            try:
                with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.headers)
                    writer.writerows(self.data)
                messagebox.showinfo("成功", f"导出成功：{save_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def on_close(self):
        self.stop_refresh = True
        self.root.destroy()

    def update_suffix_text(self):
        self.suffix_text.delete(1.0, "end")
        for suf in self.suffixes:
            if suf:
                self.suffix_text.insert("end", f"{suf}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = FilterOrganizerApp(root)
    root.mainloop() 