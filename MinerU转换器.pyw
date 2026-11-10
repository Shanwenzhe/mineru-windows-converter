"""MinerU 转换器：扫描版 PDF → Markdown / PDF（可多选文件，可选页码与输出格式）"""
import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
PDF2MD = os.path.join(HERE, "pdf2md.ps1")
MD2PDF = os.path.join(HERE, "md2pdf.ps1")
NOWIN = 0x08000000  # CREATE_NO_WINDOW


def ps(script, *args):
    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, *args]


class App:
    def __init__(self, root):
        self.root = root
        root.title("MinerU 转换器")
        root.geometry("720x520")
        try:
            root.iconbitmap(os.path.join(HERE, "mineru.ico"))
        except Exception:
            pass
        self.q = queue.Queue()
        self.running = False

        f = ttk.Frame(root, padding=12)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="① 选择 PDF（可多选）").grid(row=0, column=0, sticky="w")
        self.files = tk.Listbox(f, height=5)
        self.files.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=4)
        bf = ttk.Frame(f)
        bf.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Button(bf, text="添加文件…", command=self.add).pack(side="left")
        ttk.Button(bf, text="清空", command=lambda: self.files.delete(0, "end")).pack(side="left", padx=6)

        ttk.Label(f, text="② 页码（留空 = 全书；例：20-35 或 1-5,8）").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.pages = ttk.Entry(f, width=30)
        self.pages.grid(row=4, column=0, sticky="w")

        ttk.Label(f, text="③ 输出格式").grid(row=5, column=0, sticky="w", pady=(10, 0))
        of = ttk.Frame(f)
        of.grid(row=6, column=0, sticky="w")
        self.want_pdf = tk.BooleanVar(value=True)
        self.want_md = tk.BooleanVar(value=False)
        ttk.Checkbutton(of, text="PDF（排版好的公式，适合阅读）", variable=self.want_pdf).pack(side="left")
        ttk.Checkbutton(of, text="Markdown（.md，可编辑）", variable=self.want_md).pack(side="left", padx=12)

        self.btn = ttk.Button(f, text="开始转换", command=self.start)
        self.btn.grid(row=7, column=0, sticky="w", pady=10)
        self.bar = ttk.Progressbar(f, mode="indeterminate", length=300)
        self.bar.grid(row=7, column=1, sticky="w")

        self.log = tk.Text(f, height=12, state="disabled", font=("Microsoft YaHei", 9))
        self.log.grid(row=8, column=0, columnspan=3, sticky="nsew")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(8, weight=1)
        self.say("提示：首次转换可能下载并加载模型，耗时取决于硬件和页数。结果放在原 PDF 旁的独立 _mineru 文件夹，不覆盖原件。")
        root.after(200, self.pump)

    def add(self):
        for p in filedialog.askopenfilenames(title="选择 PDF", filetypes=[("PDF", "*.pdf")]):
            self.files.insert("end", os.path.normpath(p))

    def say(self, s):
        self.log.configure(state="normal")
        self.log.insert("end", s.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def pump(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item is None:
                    self.running = False
                    self.btn.configure(state="normal")
                    self.bar.stop()
                else:
                    self.say(item)
        except queue.Empty:
            pass
        self.root.after(200, self.pump)

    def start(self):
        files = list(self.files.get(0, "end"))
        if not files:
            return messagebox.showwarning("提示", "请先添加 PDF 文件")
        if not (self.want_pdf.get() or self.want_md.get()):
            return messagebox.showwarning("提示", "至少选一种输出格式")
        pages = self.pages.get().strip().replace("，", ",").replace(" ", "") or "all"
        self.running = True
        self.btn.configure(state="disabled")
        self.bar.start(12)
        threading.Thread(target=self.work, args=(files, pages, self.want_pdf.get(), self.want_md.get()),
                         daemon=True).start()

    def run(self, cmd):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              creationflags=NOWIN, encoding="utf-8", errors="replace", env=env) as p:
            for line in p.stdout:
                if line.strip():
                    self.q.put("   " + line.rstrip())
            return p.wait()

    def work(self, files, pages, want_pdf, want_md):
        succeeded = 0
        try:
            for i, pdf in enumerate(files, 1):
                try:
                    stem = os.path.splitext(os.path.basename(pdf))[0]
                    suffix = "" if pages == "all" else f"_p{pages}"
                    folder = os.path.join(os.path.dirname(pdf), stem + "_mineru" + suffix)
                    md = os.path.join(folder, stem + ".md")
                    out_pdf = os.path.join(folder, stem + ".pdf")
                    self.q.put(f"[{i}/{len(files)}] {os.path.basename(pdf)}  页码：{pages}")
                    if os.path.exists(folder):
                        self.q.put("   ✗ 输出目录已存在，请先重命名或移走它：" + folder)
                        continue
                    if self.run(ps(PDF2MD, pdf, pages)) != 0 or not os.path.isfile(md) or os.path.getsize(md) == 0:
                        self.q.put("   ✗ 识别失败，请查看上方日志。")
                        continue
                    if want_pdf:
                        self.q.put("   使用 Typst 生成 PDF …")
                        result = self.run(ps(MD2PDF, md))
                        if result != 0 or not os.path.isfile(out_pdf) or os.path.getsize(out_pdf) == 0:
                            self.q.put("   ✗ PDF 生成失败，保留 Markdown：" + md)
                            continue
                        self.q.put("   ✓ " + out_pdf)
                    if want_md:
                        self.q.put("   ✓ " + md)
                    elif want_pdf:
                        os.remove(md)  # 仅清理本次成功转换创建的中间文件
                    succeeded += 1
                except Exception as exc:
                    self.q.put("   ✗ 转换出错：" + str(exc))
            self.q.put(f"处理结束：成功 {succeeded}，失败 {len(files) - succeeded}。")
        finally:
            self.q.put(None)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
