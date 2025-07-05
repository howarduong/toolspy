import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, scrolledtext
import os
import threading
import queue
import packedxml_codec
import binascii
import packedxml_reader
import xml.dom.minidom
import time
import concurrent.futures

class XMLDecoderApp:
    SUPPORTED_EXTS = ['.xml', '.def', '.visual', '.chunk', '.settings', '.primitives', '.model', '.animation', '.anca']

    def __init__(self, root):
        self.root = root
        self.root.title("XML解码工具（纯内置库）")
        self.root.geometry("1024x766")
        self.root.minsize(900, 600)
        self.files_to_decode = []
        self.decode_queue = queue.Queue()
        self.decode_results = {}  # 新增：用于批量解码结果缓存
        self.current_file = None  # 当前显示的文件

        # ======= 顶部输入区 =======
        tip_label = tk.Label(root, text="支持所有PackedXml格式的二进制文件，不限于.xml扩展名。", fg="#0077aa", font=("微软雅黑", 10, "bold"))
        tip_label.pack(fill='x', padx=12, pady=2)

        top_frame = tk.LabelFrame(root, text="文件与目录选择", font=("微软雅黑", 11, "bold"), padx=10, pady=8)
        top_frame.pack(fill='x', padx=12, pady=8)

        # 单文件
        self.single_file_var = tk.StringVar()
        tk.Label(top_frame, text="单文件:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky='e', padx=2, pady=2)
        tk.Entry(top_frame, textvariable=self.single_file_var, width=38, font=("微软雅黑", 10)).grid(row=0, column=1, padx=2, pady=2)
        tk.Button(top_frame, text="选择", command=self.select_single_file, font=("微软雅黑", 10)).grid(row=0, column=2, padx=4, pady=2)

        # 批量文件
        self.multi_file_var = tk.StringVar()
        tk.Label(top_frame, text="批量文件:", font=("微软雅黑", 10)).grid(row=0, column=3, sticky='e', padx=2, pady=2)
        tk.Entry(top_frame, textvariable=self.multi_file_var, width=38, font=("微软雅黑", 10)).grid(row=0, column=4, padx=2, pady=2)
        tk.Button(top_frame, text="选择", command=self.select_multi_files, font=("微软雅黑", 10)).grid(row=0, column=5, padx=4, pady=2)

        # 目录
        self.dir_var = tk.StringVar()
        tk.Label(top_frame, text="目录:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky='e', padx=2, pady=2)
        tk.Entry(top_frame, textvariable=self.dir_var, width=38, font=("微软雅黑", 10)).grid(row=1, column=1, padx=2, pady=2)
        tk.Button(top_frame, text="选择", command=self.select_dir, font=("微软雅黑", 10)).grid(row=1, column=2, padx=4, pady=2)

        # 检索目录按钮
        tk.Button(top_frame, text="检索目录", command=self.scan_files, font=("微软雅黑", 10, "bold"), bg="#e6f7ff").grid(row=1, column=3, columnspan=3, sticky='we', padx=8, pady=2)

        # ======= 进度条 =======
        progress_frame = tk.Frame(root)
        progress_frame.pack(fill='x', padx=12, pady=4)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=800)
        self.progress.pack(fill='x', padx=8, pady=2)
        self.progress_label = tk.Label(progress_frame, text="进度：0%", font=("微软雅黑", 10))
        self.progress_label.pack(anchor='e', padx=8)

        # ======= 操作按钮 =======
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill='x', padx=12, pady=4)
        self.btn_decode = tk.Button(btn_frame, text="文件解码", command=self.decode_files, font=("微软雅黑", 11, "bold"), bg="#d9f7be", width=16, height=1)
        self.btn_decode.pack(side='left', padx=8)
        self.btn_save = tk.Button(btn_frame, text="保存", command=self.save_current_result, font=("微软雅黑", 10), bg="#e6f7ff", width=10)
        self.btn_save.pack(side='left', padx=8)
        self.btn_batch_save = tk.Button(btn_frame, text="批量解码保存", command=self.batch_decode_and_save, font=("微软雅黑", 10), bg="#ffd591", width=14)
        self.btn_batch_save.pack(side='left', padx=8)
        tk.Label(btn_frame, text="（请先选择文件或目录）", font=("微软雅黑", 10), fg="#888").pack(side='left', padx=8)

        # ======= 文本显示区 =======
        text_frame = tk.Frame(root)
        text_frame.pack(fill='both', expand=True, padx=12, pady=6)
        left_frame = tk.LabelFrame(text_frame, text="解码前内容", font=("微软雅黑", 10, "bold"), padx=6, pady=4)
        left_frame.pack(side='left', fill='both', expand=True, padx=4)
        right_frame = tk.LabelFrame(text_frame, text="解码后内容", font=("微软雅黑", 10, "bold"), padx=6, pady=4)
        right_frame.pack(side='left', fill='both', expand=True, padx=4)
        self.text_before = scrolledtext.ScrolledText(left_frame, width=50, height=18, font=("Consolas", 10), bg="#f6ffed")
        self.text_before.pack(fill='both', expand=True)
        self.text_after = scrolledtext.ScrolledText(right_frame, width=50, height=18, font=("Consolas", 10), bg="#fffbe6")
        self.text_after.pack(fill='both', expand=True)

        # ======= 日志区 =======
        log_frame = tk.LabelFrame(root, text="工作日志", font=("微软雅黑", 10, "bold"), padx=8, pady=4)
        log_frame.pack(fill='both', expand=False, padx=12, pady=6)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=7, font=("微软雅黑", 9), bg="#f0f5ff")
        self.log_text.pack(fill='both', expand=True)

    def select_single_file(self):
        file = filedialog.askopenfilename(filetypes=[("所有文件", "*.*")])
        if file:
            self.single_file_var.set(file)
            self.files_to_decode = [file]
            self.log(f"已选择单文件：{file}")

    def select_multi_files(self):
        files = filedialog.askopenfilenames(filetypes=[("所有文件", "*.*")])
        if files:
            self.multi_file_var.set(";".join(files))
            self.files_to_decode = list(files)
            self.log(f"已选择{len(files)}个文件。")
            # 新增：批量文件时，自动切换到第一个文件显示
            if files:
                self.current_file = files[0]

    def select_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.dir_var.set(dir_path)
            self.files_to_decode = self.get_all_xml_files(dir_path)
            self.log(f"已选择目录：{dir_path}")

    def scan_files(self):
        dir_path = self.dir_var.get()
        if dir_path and os.path.isdir(dir_path):
            self.files_to_decode = self.get_all_xml_files(dir_path)
            self.log(f"已检索到{len(self.files_to_decode)}个XML文件")
        else:
            self.log("目录无效，请重新选择")

    def decode_files(self):
        if not self.files_to_decode:
            self.log("没有可解码的文件")
            return
        self.decode_results = {}  # 清空批量解码缓存
        self.progress_var.set(0)
        self.progress_label.config(text="进度：0%")
        self.text_before.delete('1.0', 'end')
        self.text_after.delete('1.0', 'end')
        threading.Thread(target=self.decode_worker, daemon=True).start()
        self.root.after(100, self.check_decode_queue)

    def remove_xml_declaration(self, xml_str):
        lines = xml_str.splitlines()
        if lines and lines[0].strip().startswith('<?xml'):
            return '\n'.join(lines[1:]).lstrip()
        return xml_str

    def decode_worker(self):
        total = len(self.files_to_decode)
        for i, file in enumerate(self.files_to_decode):
            try:
                ext = os.path.splitext(file)[1].lower()
                with open(file, 'rb') as f:
                    raw = f.read()
                before = raw[:64].hex()
                # 检查文件头
                if len(raw) >= 4:
                    head = int.from_bytes(raw[:4], byteorder='little')
                    if head == 0x62A14E45:
                        self.decode_queue.put(('log', f"文件头检测通过（PackedXml格式）: {file}"))
                    else:
                        self.decode_queue.put(('log', f"文件头检测失败（非PackedXml格式）: {file}"))
                else:
                    self.decode_queue.put(('log', f"文件过短，无法检测文件头: {file}"))
                # 优先用严格对标C#源码的PackedXml解码
                try:
                    xml_str = packedxml_reader.decode_packedxml_strict(raw, root_name='resources')
                    # 格式化美化输出
                    try:
                        pretty_xml = xml.dom.minidom.parseString(xml_str).toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
                        pretty_xml = self.remove_xml_declaration(pretty_xml)
                        self.decode_results[file] = (before, pretty_xml)  # 缓存结果
                        if i == 0:
                            self.decode_queue.put(('result', before, pretty_xml))
                        self.decode_queue.put(('log', f"PackedXml严格解码并格式化成功: {file}"))
                    except Exception as fmt_e:
                        self.decode_results[file] = (before, xml_str)
                        if i == 0:
                            self.decode_queue.put(('result', before, xml_str))
                        self.decode_queue.put(('log', f"PackedXml解码成功，但格式化失败: {file}，错误: {fmt_e}"))
                except Exception as e:
                    # 如果不是PackedXml或解码失败，尝试文本解码
                    try:
                        content, used_encoding = self.try_decode(raw)
                        if content is not None:
                            decoded = content.replace('<', '[').replace('>', ']')
                            self.decode_results[file] = (before, decoded)
                            if i == 0:
                                self.decode_queue.put(('result', before, decoded))
                            self.decode_queue.put(('log', f"文本解码成功: {file}，编码方式: {used_encoding}"))
                        else:
                            after = '无法解码为文本（常见编码均失败）'
                            self.decode_results[file] = (before, after)
                            if i == 0:
                                self.decode_queue.put(('result', before, after))
                            self.decode_queue.put(('log', f"解码失败: {file}，未知编码"))
                    except Exception as e2:
                        after = f'无法解码为文本，错误: {e2}'
                        self.decode_results[file] = (before, after)
                        if i == 0:
                            self.decode_queue.put(('result', before, after))
                        self.decode_queue.put(('log', f"解码失败: {file}，错误: {e2}"))
                # 修复：单文件解码时也设置current_file，保证保存按钮可用
                if total == 1:
                    self.current_file = file
            except Exception as e:
                self.decode_queue.put(('log', f"解码失败: {file}，错误: {e}"))
            self.decode_queue.put(('progress', int((i + 1) / total * 100)))

    def try_decode(self, raw, encodings=('utf-8', 'gbk', 'gb2312', 'big5')):
        for enc in encodings:
            try:
                return raw.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return None, None

    def check_decode_queue(self):
        updated_progress = False
        try:
            while True:
                item = self.decode_queue.get_nowait()
                if item[0] == 'result':
                    before, after = item[1], item[2]
                    self.text_before.delete('1.0', 'end')
                    self.text_before.insert('end', before)
                    self.text_after.delete('1.0', 'end')
                    self.text_after.insert('end', after)
                elif item[0] == 'log':
                    self.log(item[1])
                elif item[0] == 'progress':
                    self.progress_var.set(item[1])
                    self.progress_label.config(text=f"进度：{item[1]}%")
                    updated_progress = True
        except queue.Empty:
            pass
        if self.progress_var.get() < 100 or not updated_progress:
            self.root.after(100, self.check_decode_queue)

    def get_all_xml_files(self, dir_path):
        exts = self.SUPPORTED_EXTS
        xml_files = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in exts):
                    xml_files.append(os.path.join(root, file))
        return xml_files

    def log(self, msg):
        self.log_text.insert('end', msg + '\n')
        self.log_text.see('end')

    def save_current_result(self):
        if not self.current_file or self.current_file not in self.decode_results:
            self.log("没有可保存的解码结果")
            return
        before, after = self.decode_results[self.current_file]
        # 直接覆盖原文件
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(after)
            self.log(f"已覆盖原文件: {self.current_file}")
        except Exception as e:
            self.log(f"保存失败: {self.current_file}，错误: {e}")

    def batch_decode_and_save(self):
        if not self.files_to_decode:
            self.log("没有可批量解码的文件，请先批量选择或检索目录")
            return
        total = len(self.files_to_decode)
        self.log(f"开始批量解码和覆盖保存，共{total}个文件...")
        start_time = time.time()
        self.batch_queue = queue.Queue()
        self.batch_completed = 0
        self.batch_total = total
        self.batch_start_time = start_time
        def worker(files):
            for file in files:
                try:
                    with open(file, 'rb') as f:
                        raw = f.read()
                    # 恢复为：只有文件头为PackedXml才尝试解码
                    if len(raw) >= 4 and int.from_bytes(raw[:4], byteorder='little') == 0x62A14E45:
                        try:
                            xml_str = packedxml_reader.decode_packedxml_strict(raw, root_name='resources')
                            pretty_xml = xml.dom.minidom.parseString(xml_str).toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
                            pretty_xml = self.remove_xml_declaration(pretty_xml)
                            with open(file, 'w', encoding='utf-8') as fw:
                                fw.write(pretty_xml)
                            self.batch_queue.put((file, True, None))
                        except Exception as e:
                            self.batch_queue.put((file, False, f"解码失败: {e}"))
                    else:
                        self.batch_queue.put((file, False, "文件头检测失败（非PackedXml格式）"))
                except Exception as e:
                    self.batch_queue.put((file, False, f"IO错误: {e}"))
        threading.Thread(target=worker, args=(self.files_to_decode,), daemon=True).start()
        self.root.after(100, self.batch_update_ui)

    def batch_update_ui(self):
        updated = False
        while not getattr(self, 'batch_queue', None) or not self.batch_queue.empty():
            try:
                file, ok, msg = self.batch_queue.get_nowait()
                self.batch_completed += 1
                percent = int(self.batch_completed / self.batch_total * 100)
                self.progress_var.set(percent)
                self.progress_label.config(text=f"进度：{percent}%")
                if ok:
                    self.log(f"批量解码并覆盖保存成功: {file}")
                else:
                    self.log(f"批量解码失败: {file}，原因: {msg}")
                updated = True
            except queue.Empty:
                break
        if self.batch_completed < self.batch_total:
            self.root.after(100, self.batch_update_ui)
        else:
            elapsed = time.time() - self.batch_start_time
            self.log(f"批量解码保存完成，总耗时: {elapsed:.2f}秒，平均每个文件: {elapsed/self.batch_total:.2f}秒")

if __name__ == "__main__":
    root = tk.Tk()
    app = XMLDecoderApp(root)
    root.mainloop()