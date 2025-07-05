import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import hash_algorithms
import utils
import wdf_parser
import wdf_exporter

class HashToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title('哈希算法推测与样本比对工具')
        self.root.geometry('1400x900')
        self.create_widgets()
        self.wdf_entries = []

    def create_widgets(self):
        # 样本输入区
        frame_input = ttk.LabelFrame(self.root, text='1. 样本输入区')
        frame_input.pack(fill='x', padx=10, pady=5)
        self.text_samples = tk.Text(frame_input, height=6)
        self.text_samples.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        btn_import = ttk.Button(frame_input, text='导入样本', command=self.import_samples)
        btn_import.pack(side='right', padx=5)
        btn_import_wdf = ttk.Button(frame_input, text='导入WDF包', command=self.import_wdf)
        btn_import_wdf.pack(side='right', padx=5)

        # 算法选择区
        frame_algo = ttk.LabelFrame(self.root, text='2. 哈希算法选择区')
        frame_algo.pack(fill='x', padx=10, pady=5)
        ttk.Label(frame_algo, text='算法:').pack(side='left', padx=5)
        self.combo_algo = ttk.Combobox(frame_algo, values=hash_algorithms.get_algorithm_names(), state='readonly')
        self.combo_algo.current(0)
        self.combo_algo.pack(side='left', padx=5)
        self.var_case = tk.BooleanVar(value=False)
        chk_case = ttk.Checkbutton(frame_algo, text='区分大小写', variable=self.var_case)
        chk_case.pack(side='left', padx=5)
        ttk.Label(frame_algo, text='种子:').pack(side='left', padx=5)
        self.entry_seed = ttk.Entry(frame_algo, width=8)
        self.entry_seed.insert(0, '131')
        self.entry_seed.pack(side='left', padx=5)

        # 操作区
        frame_ops = ttk.Frame(self.root)
        frame_ops.pack(fill='x', padx=10, pady=5)
        btn_start = ttk.Button(frame_ops, text='开始比对', command=self.start_compare)
        btn_start.pack(side='left', padx=5)
        btn_clear = ttk.Button(frame_ops, text='清空结果', command=self.clear_results)
        btn_clear.pack(side='left', padx=5)
        btn_export_wdf = ttk.Button(frame_ops, text='导出WDF索引', command=self.export_wdf_index)
        btn_export_wdf.pack(side='left', padx=5)
        btn_export_unmatched = ttk.Button(frame_ops, text='导出未命中样本', command=self.export_unmatched)
        btn_export_unmatched.pack(side='left', padx=5)
        btn_export_matched = ttk.Button(frame_ops, text='导出命中资源', command=self.export_matched_files)
        btn_export_matched.pack(side='left', padx=5)

        # 主体区采用左右布局
        frame_main = ttk.Frame(self.root)
        frame_main.pack(fill='both', expand=True, padx=10, pady=5)
        # 左侧结果展示
        frame_result = ttk.LabelFrame(frame_main, text='4. 结果展示区')
        frame_result.pack(side='left', fill='both', expand=True)

        columns = ('path', 'calc_hash', 'target_hash', 'match', 'wdf_uid', 'wdf_offset', 'wdf_size', 'wdf_space')
        self.tree = ttk.Treeview(frame_result, columns=columns, show='headings', height=18)
        for col, txt in zip(columns, ['路径/文件名', '算法结果', '目标哈希', '匹配', 'WDF_UID', '偏移', '大小', '空间']):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=120 if col!='path' else 180, anchor='center')
        self.tree.pack(fill='both', expand=True)
        self.label_stats = ttk.Label(frame_result, text='命中率统计:')
        self.label_stats.pack(anchor='w', padx=5, pady=2)

        # 右侧日志区
        frame_log = ttk.LabelFrame(frame_main, text='日志窗口')
        frame_log.pack(side='right', fill='y', padx=5)
        self.log_text = tk.Text(frame_log, width=40, height=40, state='disabled')
        self.log_text.pack(fill='both', expand=True)

        # 进度条区
        frame_progress = ttk.Frame(self.root)
        frame_progress.pack(fill='x', padx=10, pady=5)
        self.progress = ttk.Progressbar(frame_progress, orient='horizontal', length=600, mode='determinate')
        self.progress.pack(side='left', padx=5)
        self.label_progress = ttk.Label(frame_progress, text='未开始')
        self.label_progress.pack(side='left', padx=5)

    def import_samples(self):
        filepath = filedialog.askopenfilename(filetypes=[('Text Files', '*.txt;*.csv'), ('All Files', '*.*')])
        if filepath:
            content = utils.read_file(filepath)
            self.text_samples.delete('1.0', tk.END)
            self.text_samples.insert(tk.END, content)
            self.lst_path = filepath
            self.append_log(f"导入列表: {filepath}，共{len(content.splitlines())}行")

    def import_wdf(self):
        filepath = filedialog.askopenfilename(filetypes=[('WDF Files', '*.wdf'), ('All Files', '*.*')])
        if filepath:
            try:
                entries = wdf_parser.parse_wdf_index(filepath)
                self.wdf_entries = entries
                self.wdf_path = filepath
                self.tree.delete(*self.tree.get_children())
                for e in entries:
                    self.tree.insert('', 'end', values=('', '', '', '', f'0x{e['uid']:08X}', e['offset'], e['size'], e['space']))
                self.label_stats.config(text=f'WDF资源数: {len(entries)}')
                self.label_progress.config(text='WDF索引导入完成')
                self.append_log(f"导入WDF包: {filepath}，共{len(entries)}条资源")
            except Exception as ex:
                messagebox.showerror('WDF解析失败', str(ex))
                self.append_log(f"导入WDF包失败: {filepath}，错误: {ex}")

    def export_wdf_index(self):
        if not self.wdf_entries:
            messagebox.showinfo('无WDF索引', '请先导入WDF包')
            return
        filepath = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files', '*.txt')])
        if filepath:
            wdf_parser.export_index_to_txt(self.wdf_entries, filepath)
            messagebox.showinfo('导出成功', f'已导出 {len(self.wdf_entries)} 条WDF索引')

    def start_compare(self):
        samples = utils.parse_samples(self.text_samples.get('1.0', tk.END))
        algo_name = self.combo_algo.get()
        case_sensitive = self.var_case.get()
        try:
            seed = int(self.entry_seed.get())
        except ValueError:
            messagebox.showerror('参数错误', '种子必须为整数')
            return
        self.progress['maximum'] = len(samples)
        self.progress['value'] = 0
        self.label_progress.config(text=f'已处理 0/{len(samples)} 条')
        self.tree.delete(*self.tree.get_children())
        self.append_log(f"开始比对: 样本数={len(samples)}，算法={algo_name}，区分大小写={case_sensitive}，种子={seed}")
        threading.Thread(target=self.compare_thread, args=(samples, algo_name, case_sensitive, seed), daemon=True).start()

    def compare_thread(self, samples, algo_name, case_sensitive, seed):
        matched = 0
        for idx, (path, target_hash) in enumerate(samples):
            # 如果没有目标哈希，自动用算法计算
            if target_hash is None:
                target_hash = hash_algorithms.calc_hash(algo_name, path, case_sensitive, seed)
            calc_hash = hash_algorithms.calc_hash(algo_name, path, case_sensitive, seed)
            is_match = (calc_hash == target_hash)
            # 查找WDF索引中是否有该uid
            wdf_info = next((e for e in self.wdf_entries if e['uid'] == calc_hash), None)
            wdf_uid = f'0x{calc_hash:08X}'
            wdf_offset = wdf_info['offset'] if wdf_info else ''
            wdf_size = wdf_info['size'] if wdf_info else ''
            wdf_space = wdf_info['space'] if wdf_info else ''
            self.tree.insert('', 'end', values=(path, hex(calc_hash), hex(target_hash), '√' if is_match else '×', wdf_uid, wdf_offset, wdf_size, wdf_space))
            if is_match:
                matched += 1
            self.progress['value'] = idx + 1
            self.label_progress.config(text=f'已处理 {idx+1}/{len(samples)} 条')
            self.root.update_idletasks()
        rate = matched / len(samples) * 100 if samples else 0
        self.label_stats.config(text=f'命中率统计: {matched}/{len(samples)} ({rate:.2f}%)')
        self.label_progress.config(text='比对完成')
        self.append_log(f"比对完成: 命中{matched}/{len(samples)} ({rate:.2f}%)")

    def clear_results(self):
        self.tree.delete(*self.tree.get_children())
        self.label_stats.config(text='命中率统计:')
        self.progress['value'] = 0
        self.label_progress.config(text='未开始')
        self.wdf_entries = []

    def export_unmatched(self):
        unmatched = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, 'values')
            if vals[3] == '×':
                unmatched.append(f'{vals[0]},{vals[2]}')
        if unmatched:
            filepath = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files', '*.txt')])
            if filepath:
                utils.write_file(filepath, '\n'.join(unmatched))
                messagebox.showinfo('导出成功', f'已导出 {len(unmatched)} 条未命中样本')
        else:
            messagebox.showinfo('无未命中样本', '所有样本均已命中')

    def export_matched_files(self):
        out_dir = filedialog.askdirectory(title='选择导出目录')
        if not out_dir:
            return
        if not hasattr(self, 'wdf_path') or not self.wdf_path:
            messagebox.showerror('错误', '请先导入WDF包')
            return
        if not hasattr(self, 'lst_path') or not self.lst_path:
            messagebox.showerror('错误', '请先导入lst样本文件')
            return
        algo_name = self.combo_algo.get()
        case_sensitive = self.var_case.get()
        try:
            seed = int(self.entry_seed.get())
        except ValueError:
            messagebox.showerror('参数错误', '种子必须为整数')
            return
        try:
            self.append_log(f"开始导出资源到: {out_dir}")
            wdf_exporter.export_by_lst(self.wdf_path, self.lst_path, out_dir, algo_name, case_sensitive, seed)
            messagebox.showinfo('导出完成', f'资源导出已完成！')
            self.append_log(f"导出完成: 资源已导出到 {out_dir}")
        except Exception as ex:
            messagebox.showerror('导出失败', str(ex))
            self.append_log(f"导出失败: {ex}")

    def append_log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

def main():
    root = tk.Tk()
    app = HashToolApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
