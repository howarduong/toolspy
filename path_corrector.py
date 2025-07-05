import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk
import csv
import os

FONT_FAMILY = "微软雅黑"
FONT_SIZE = 11

class PathCorrectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("路径修正工具 Path Corrector")
        self.root.geometry("1000x700")
        self.lst_path = tk.StringVar()
        self.original_lines = []
        self.fixed_lines = []

        self.default_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.title_font = font.Font(family=FONT_FAMILY, size=14, weight="bold")

        # 第一行：输入区
        input_frame = tk.Frame(root)
        input_frame.pack(fill="x", pady=(20, 10))
        tk.Entry(input_frame, textvariable=self.lst_path, width=60, font=self.default_font).pack(side="left", padx=5, expand=True, fill="x")
        tk.Button(input_frame, text="浏览", command=self.browse_lst, font=self.default_font).pack(side="left", padx=5)

        # 第二行：按钮区
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", pady=(0, 10))
        tk.Button(btn_frame, text="路径修正", command=self.fix_paths, font=self.default_font, width=12).pack(side="left", padx=10)
        tk.Button(btn_frame, text="导出csv", command=self.export_csv, font=self.default_font, width=12).pack(side="left", padx=10)

        # 进度条
        self.progress = ttk.Progressbar(root, orient='horizontal', length=400, mode='determinate')
        self.progress.pack(fill="x", padx=20, pady=(0, 10))

        # 第三行：显示区
        display_frame = tk.Frame(root)
        display_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # 左右两栏分别显示原路径和修正后路径
        left_label = tk.Label(display_frame, text="原始路径", font=self.title_font)
        left_label.pack(side="left", anchor="n", padx=(0, 5))
        right_label = tk.Label(display_frame, text="修正后路径", font=self.title_font)
        right_label.pack(side="left", anchor="n", padx=(20, 0))
        self.text_orig = tk.Text(display_frame, font=(FONT_FAMILY, FONT_SIZE), wrap="none", width=50)
        self.text_orig.pack(side="left", fill="both", expand=True)
        self.text_fixed = tk.Text(display_frame, font=(FONT_FAMILY, FONT_SIZE), wrap="none", width=50)
        self.text_fixed.pack(side="left", fill="both", expand=True)
        orig_scrollbar = tk.Scrollbar(display_frame, command=self.text_orig.yview)
        orig_scrollbar.pack(side="left", fill="y")
        self.text_orig.config(yscrollcommand=orig_scrollbar.set)
        fixed_scrollbar = tk.Scrollbar(display_frame, command=self.text_fixed.yview)
        fixed_scrollbar.pack(side="left", fill="y")
        self.text_fixed.config(yscrollcommand=fixed_scrollbar.set)

        # 日志窗口
        log_frame = tk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        tk.Label(log_frame, text="修正日志", font=self.title_font).pack(anchor="w")
        self.log_text = tk.Text(log_frame, font=(FONT_FAMILY, FONT_SIZE), wrap="none", height=12, bg="#f5f5f5")
        self.log_text.pack(fill="both", expand=True)
        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scrollbar.set)

    def browse_lst(self):
        file_path = filedialog.askopenfilename(title="选择LST文件", filetypes=[('LST文件', '*.lst'), ('所有文件', '*.*')])
        if file_path:
            self.lst_path.set(file_path)
            self.load_lst(file_path)

    def load_lst(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.original_lines = [line.rstrip() for line in f if line.strip()]
        except Exception:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    self.original_lines = [line.rstrip() for line in f if line.strip()]
            except Exception as e:
                messagebox.showerror("错误", f"读取LST文件失败: {e}")
                self.original_lines = []
        self.fixed_lines = []
        self.show_content()
        self.log_text.delete(1.0, "end")
        self.progress['value'] = 0

    def fix_paths(self):
        self.fixed_lines = []
        self.log_text.delete(1.0, "end")
        total = len(self.original_lines)
        for idx, line in enumerate(self.original_lines, 1):
            fixed = line.split('/', 1)[1] if '/' in line else line
            self.fixed_lines.append(fixed)
            self.progress['value'] = idx * 100 // total if total else 0
            self.root.update_idletasks()
            self.log_text.insert("end", f"原文: {line}\n修正: {fixed}\n\n")
        self.progress['value'] = 100 if total else 0
        self.show_content()

    def export_csv(self):
        if not self.fixed_lines:
            messagebox.showwarning("警告", "没有可导出的内容，请先进行路径修正！")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="导出CSV文件")
        if save_path:
            try:
                with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    for line in self.fixed_lines:
                        writer.writerow([line])
                messagebox.showinfo("成功", f"导出成功：{save_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def show_content(self):
        self.text_orig.delete(1.0, "end")
        self.text_fixed.delete(1.0, "end")
        for orig, fixed in zip(self.original_lines, self.fixed_lines):
            self.text_orig.insert("end", orig + "\n")
            self.text_fixed.insert("end", fixed + "\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = PathCorrectorApp(root)
    root.mainloop() 