import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import re
import os
import sv_ttk  # Sun Valley temasını uygulamak için
import datetime
import threading
import time

# Makro kaydı için global liste
macro_recording = False
macro_actions = []

class EditorTab:
    def __init__(self, master, notebook, file_path=None):
        self.master = master
        self.file_path = file_path
        self.frame = ttk.Frame(notebook)
        self.text = tk.Text(self.frame, wrap="none", undo=True)
        self.text.pack(side="right", fill="both", expand=True)
        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<Key>", self.record_macro)
        self.text.bind("<Button-1>", self.hide_context_menu)
        # Scrollbarlar
        self.v_scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.text.yview)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll = ttk.Scrollbar(self.frame, orient="horizontal", command=self.text.xview)
        self.h_scroll.pack(side="bottom", fill="x")
        self.text.config(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # Satır numarası alanı
        self.linenumbers = tk.Canvas(self.frame, width=40, background="#2b2b2b")
        self.linenumbers.pack(side="left", fill="y")
        self.text.bind("<KeyRelease>", self.update_linenumbers)
        self.text.bind("<MouseWheel>", self.update_linenumbers)
        self.text.bind("<ButtonRelease-1>", self.update_linenumbers)
        self.text.bind("<Configure>", self.update_linenumbers)

        # İlk satır numarası güncellemesi
        self.update_linenumbers()

        # Otomatik sözdizimi renklendirme (örnek: Python)
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.setup_tags()

        # Değişiklik kontrolü
        self._modified = False

    def setup_tags(self):
        # Basit Python sözdizimi renklendirme için etiketler
        self.text.tag_configure("keyword", foreground="#cc7832")
        self.text.tag_configure("string", foreground="#6a8759")
        self.text.tag_configure("comment", foreground="#808080")
        self.text.tag_configure("number", foreground="#6897bb")
        self.text.tag_configure("class", foreground="#66d9ef")
        self.text.tag_configure("function", foreground="#a6e22e")

    def on_key_release(self, event=None):
        self.highlight_syntax()

    def highlight_syntax(self):
        # Örnek Python sözdizimi renklendirmesi (tam kapsamlı değildir)
        content = self.text.get("1.0", tk.END)
        self.text.tag_remove("keyword", "1.0", tk.END)
        self.text.tag_remove("string", "1.0", tk.END)
        self.text.tag_remove("comment", "1.0", tk.END)
        self.text.tag_remove("number", "1.0", tk.END)
        self.text.tag_remove("class", "1.0", tk.END)
        self.text.tag_remove("function", "1.0", tk.END)
        # Anahtar kelimeler
        keywords = r"\b(?:def|class|if|else|elif|while|for|in|import|from|as|return|try|except|finally|with|pass|break|continue|lambda|global|nonlocal|assert|yield)\b"
        for match in re.finditer(keywords, content):
            start = "1.0+{}c".format(match.start())
            end = "1.0+{}c".format(match.end())
            if match.group() == "class":
                self.text.tag_add("class", start, end)
            elif match.group() == "def":
                self.text.tag_add("function", start, end)
            else:
                self.text.tag_add("keyword", start, end)
        # Stringler (tek veya çift tırnak)
        for match in re.finditer(r"(['\"])(?:(?=(\\?))\2.)*?\1", content):
            start = "1.0+{}c".format(match.start())
            end = "1.0+{}c".format(match.end())
            self.text.tag_add("string", start, end)
        # Yorumlar (# ile başlayanlar)
        for match in re.finditer(r"#.*", content):
            start = "1.0+{}c".format(match.start())
            end = "1.0+{}c".format(match.end())
            self.text.tag_add("comment", start, end)
        # Numaralar
        for match in re.finditer(r"\b\d+(\.\d+)?\b", content):
            start = "1.0+{}c".format(match.start())
            end = "1.0+{}c".format(match.end())
            self.text.tag_add("number", start, end)

    def update_linenumbers(self, event=None):
        self.linenumbers.delete("all")
        i = self.text.index("@0,0")
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.linenumbers.create_text(2, y, anchor="nw", text=linenum, fill="white", font=("Consolas", 10))
            i = self.text.index(f"{i}+1line")

    def on_modified(self, event=None):
        # Dosyada değişiklik olduğunda notebook sekme başlığını güncellemek için kullanılabilir.
        self._modified = self.text.edit_modified()
        self.text.edit_modified(False)
        self.update_linenumbers()

    def record_macro(self, event=None):
        global macro_recording, macro_actions
        if macro_recording:
            # Burada, örnek olarak basitçe event.char ve event.keysym kaydediliyor.
            macro_actions.append((event.type, event.keysym, event.char))

    def hide_context_menu(self, event=None):
        # (İsteğe bağlı) sağ tık menüsü gizlenebilir.
        pass


class FindReplaceDialog(tk.Toplevel):
    def __init__(self, master, editor, mode="find"):
        super().__init__(master)
        self.editor = editor
        self.mode = mode
        self.title("Bul" if mode == "find" else "Değiştir")
        self.geometry("450x150")
        self.transient(master)
        self.resizable(False, False)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Bul:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.find_entry = ttk.Entry(self, width=30)
        self.find_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.find_entry.focus_set()

        if self.mode == "replace":
            ttk.Label(self, text="Değiştir:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
            self.replace_entry = ttk.Entry(self, width=30)
            self.replace_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(self, text="Regex", variable=self.regex_var).grid(row=2, column=1, sticky="w", padx=5)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Bul", command=self.find).pack(side="left", padx=5)
        if self.mode == "replace":
            ttk.Button(btn_frame, text="Değiştir", command=self.replace).pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Tümünü Değiştir", command=self.replace_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Kapat", command=self.destroy).pack(side="left", padx=5)

    def find(self):
        self.editor.text.tag_remove("match", "1.0", tk.END)
        pattern = self.find_entry.get()
        if not pattern:
            return
        flags = 0
        if not self.regex_var.get():
            pattern = re.escape(pattern)
        content = self.editor.text.get("1.0", tk.END)
        for match in re.finditer(pattern, content, flags):
            start = "1.0+{}c".format(match.start())
            end = "1.0+{}c".format(match.end())
            self.editor.text.tag_add("match", start, end)
        self.editor.text.tag_config("match", foreground="white", background="blue")

    def replace(self):
        pattern = self.find_entry.get()
        replace_with = self.replace_entry.get()
        if not pattern:
            return
        content = self.editor.text.get("1.0", tk.END)
        if self.regex_var.get():
            new_content, count = re.subn(pattern, replace_with, content)
        else:
            new_content = content.replace(pattern, replace_with, 1)
        self.editor.text.delete("1.0", tk.END)
        self.editor.text.insert("1.0", new_content)
        self.find()

    def replace_all(self):
        pattern = self.find_entry.get()
        replace_with = self.replace_entry.get() if self.mode == "replace" else ""
        if not pattern:
            return
        content = self.editor.text.get("1.0", tk.END)
        if self.regex_var.get():
            new_content, count = re.subn(pattern, replace_with, content)
        else:
            new_content = content.replace(pattern, replace_with)
        self.editor.text.delete("1.0", tk.END)
        self.editor.text.insert("1.0", new_content)
        self.editor.text.tag_remove("match", "1.0", tk.END)


class NotepadPlusPlusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyNotepad++")
        self.root.geometry("1000x700")
        sv_ttk.set_theme("dark")  # Uygulama genelinde tema

        # Menü ve araç çubuğu oluşturuluyor
        self.create_menu()

        # Sekmeli editör (Notebook) oluşturuluyor
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=1, fill="both")

        # Durum çubuğu
        self.status_var = tk.StringVar(value="Hazır")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

        # İlk sekmeyi aç
        self.new_file()

        # Makro kaydı değişkenleri
        self.macro_recording = False
        self.macro_actions = []

        # Otomatik kaydetme ayarları
        self.auto_save = tk.BooleanVar(value=False)
        self.auto_save_interval = tk.IntVar(value=60)  # Dakika cinsinden

        # Otomatik kaydetme işlemini başlat
        self.start_auto_save()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Dosya Menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Yeni", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Aç...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Kaydet", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Farklı Kaydet...", command=self.save_as)
        file_menu.add_command(label="Sekmeyi Kapat", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", accelerator="Alt+F4", command=self.exit_app)

        # Düzen Menüsü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Düzen", menu=edit_menu)
        edit_menu.add_command(label="Geri Al", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Yinele", accelerator="Ctrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Kes", accelerator="Ctrl+X", command=self.cut)
        edit_menu.add_command(label="Kopyala", accelerator="Ctrl+C", command=self.copy)
        edit_menu.add_command(label="Yapıştır", accelerator="Ctrl+V", command=self.paste)
        edit_menu.add_command(label="Sil", accelerator="Del", command=self.delete)
        edit_menu.add_separator()
        edit_menu.add_command(label="Tümünü Seç", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_command(label="Go To Line...", accelerator="Ctrl+G", command=self.go_to_line)

        # Arama Menüsü
        search_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arama", menu=search_menu)
        search_menu.add_command(label="Bul...", accelerator="Ctrl+F", command=self.find)
        search_menu.add_command(label="Değiştir...", accelerator="Ctrl+H", command=self.replace)

        # Görünüm Menüsü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Görünüm", menu=view_menu)
        self.word_wrap = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Kelime Sarma", variable=self.word_wrap, command=self.toggle_word_wrap)
        view_menu.add_command(label="Tema Değiştir", command=sv_ttk.toggle_theme)
        view_menu.add_checkbutton(label="Otomatik Kaydet", variable=self.auto_save, command=self.toggle_auto_save)

        # Makro Menüsü
        macro_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Makro", menu=macro_menu)
        macro_menu.add_command(label="Makro Kaydını Başlat", command=self.start_macro_recording)
        macro_menu.add_command(label="Makro Kaydını Durdur", command=self.stop_macro_recording)
        macro_menu.add_command(label="Makroyu Çalıştır", command=self.run_macro)

        # Yardım Menüsü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        help_menu.add_command(label="Hakkında", command=self.show_about)

    def get_current_editor(self):
        current_tab = self.notebook.select()
        if current_tab:
            return self.notebook.nametowidget(current_tab).editor
        return None

    def new_file(self, file_path=None):
        # Yeni bir sekme oluştur
        tab_frame = ttk.Frame(self.notebook)
        editor = EditorTab(self.root, self.notebook, file_path)
        # Editor nesnesini frame içine saklayalım
        tab_frame.editor = editor
        editor.frame.pack(expand=1, fill="both")
        self.notebook.add(editor.frame, text="Yeni Dosya")
        self.notebook.select(editor.frame)
        self.status_var.set("Yeni dosya oluşturuldu")

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Tüm Dosyalar", "*.*"), ("Metin Dosyaları", "*.txt"), ("Python Dosyaları", "*.py")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tab_frame = ttk.Frame(self.notebook)
                editor = EditorTab(self.root, self.notebook, file_path)
                editor.text.delete("1.0", tk.END)
                editor.text.insert(tk.END, content)
                editor.highlight_syntax()
                tab_frame.editor = editor
                editor.frame.pack(expand=1, fill="both")
                self.notebook.add(editor.frame, text=os.path.basename(file_path))
                self.notebook.select(editor.frame)
                self.status_var.set(f"{os.path.basename(file_path)} dosyası açıldı")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı:\n{e}")

    def save_file(self):
        editor = self.get_current_editor()
        if editor:
            if editor.file_path:
                try:
                    content = editor.text.get("1.0", tk.END)
                    with open(editor.file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.status_var.set(f"{os.path.basename(editor.file_path)} kaydedildi")
                except Exception as e:
                    messagebox.showerror("Hata", f"Kaydedilemedi:\n{e}")
            else:
                self.save_as()

    def save_as(self):
        editor = self.get_current_editor()
        if editor:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Tüm Dosyalar", "*.*"), ("Metin Dosyaları", "*.txt")])
            if file_path:
                try:
                    content = editor.text.get("1.0", tk.END)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    editor.file_path = file_path
                    self.notebook.tab("current", text=os.path.basename(file_path))
                    self.status_var.set(f"{os.path.basename(file_path)} kaydedildi")
                except Exception as e:
                    messagebox.showerror("Hata", f"Kaydedilemedi:\n{e}")

    def close_current_tab(self):
        current_tab = self.notebook.select()
        if current_tab:
            # Değişiklik var mı diye kontrol edilebilir...
            self.notebook.forget(current_tab)
            self.status_var.set("Sekme kapatıldı")

        def exit_app(self):
        if messagebox.askyesno("Çıkış", "Çıkmak istediğinize emin misiniz?"):
            self.root.quit()

    # Düzen İşlemleri
    def undo(self):
        editor = self.get_current_editor()
        if editor:
            try:
                editor.text.edit_undo()
            except tk.TclError:
                pass

    def redo(self):
        editor = self.get_current_editor()
        if editor:
            try:
                editor.text.edit_redo()
            except tk.TclError:
                pass

    def cut(self):
        editor = self.get_current_editor()
        if editor:
            editor.text.event_generate("<<Cut>>")

    def copy(self):
        editor = self.get_current_editor()
        if editor:
            editor.text.event_generate("<<Copy>>")

    def paste(self):
        editor = self.get_current_editor()
        if editor:
            editor.text.event_generate("<<Paste>>")

    def delete(self):
        editor = self.get_current_editor()
        if editor:
            try:
                sel = editor.text.get(tk.SEL_FIRST, tk.SEL_LAST)
                editor.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass

    def select_all(self):
        editor = self.get_current_editor()
        if editor:
            editor.text.tag_add("sel", "1.0", tk.END)

    def go_to_line(self):
        editor = self.get_current_editor()
        if editor:
            line = simpledialog.askinteger("Go To Line", "Satır numarası:")
            if line is not None:
                editor.text.mark_set("insert", f"{line}.0")
                editor.text.see(f"{line}.0")

    # Arama İşlemleri
    def find(self):
        editor = self.get_current_editor()
        if editor:
            FindReplaceDialog(self.root, editor, mode="find")

    def replace(self):
        editor = self.get_current_editor()
        if editor:
            FindReplaceDialog(self.root, editor, mode="replace")

    # Görünüm İşlemleri
    def toggle_word_wrap(self):
        editor = self.get_current_editor()
        if editor:
            if self.word_wrap.get():
                editor.text.config(wrap="word")
            else:
                editor.text.config(wrap="none")

    def toggle_auto_save(self):
        if self.auto_save.get():
            self.status_var.set("Otomatik kaydetme açık")
        else:
            self.status_var.set("Otomatik kaydetme kapalı")

    # Makro İşlemleri
    def start_macro_recording(self):
        self.macro_recording = True
        self.macro_actions = []
        self.status_var.set("Makro kaydı başladı")

    def stop_macro_recording(self):
        self.macro_recording = False
        self.status_var.set(f"Makro kaydı durduruldu. {len(self.macro_actions)} işlem kaydedildi.")

    def run_macro(self):
        editor = self.get_current_editor()
        if editor:
            for action in self.macro_actions:
                # Basit örnek: yalnızca klavye tuşları (keysym) giriliyor
                event_type, keysym, char = action
                # Örneğin, 'BackSpace' gibi klavye tuşlarına bağlı işlemler uygulanabilir
                # Bu kısım genişletilerek daha detaylı yapılabilir.
                if keysym == "BackSpace":
                    editor.text.delete("insert-1c")
                else:
                    editor.text.insert("insert", char)
            self.status_var.set("Makro çalıştırıldı")

    def show_about(self):
        messagebox.showinfo("Hakkında", f"PyNotepad++\n\nGeliştirilme Tarihi: {datetime.date.today()}\nNotepad++ benzeri özellikler Tkinter ile uygulanmıştır.")

    def start_auto_save(self):
        if self.auto_save.get():
            self.auto_save_thread = threading.Thread(target=self.auto_save_loop)
            self.auto_save_thread.daemon = True  # Uygulama kapanınca thread de kapanır
            self.auto_save_thread.start()

    def auto_save_loop(self):
        while True:
            time.sleep(self.auto_save_interval.get() * 60)  # Dakika cinsinden
            editor = self.get_current_editor()
            if editor and editor.file_path:
                try:
                    content = editor.text.get("1.0", tk.END)
                    with open(editor.file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.status_var.set(f"{os.path.basename(editor.file_path)} otomatik olarak kaydedildi")
                except Exception as e:
                    messagebox.showerror("Hata", f"Otomatik kaydetme sırasında hata oluştu:\n{e}")


def bind_global_shortcuts(app):
    # Genel kısayollar
    app.root.bind("<Control-n>", lambda e: app.new_file())
    app.root.bind("<Control-o>", lambda e: app.open_file())
    app.root.bind("<Control-s>", lambda e: app.save_file())
    app.root.bind("<Control-w>", lambda e: app.close_current_tab())
    app.root.bind("<Control-f>", lambda e: app.find())
    app.root.bind("<Control-h>", lambda e: app.replace())
    app.root.bind("<Control-g>", lambda e: app.go_to_line())
    app.root.bind("<Control-a>", lambda e: app.select_all())
    app.root.bind("<Control-z>", lambda e: app.undo())
    app.root.bind("<Control-y>", lambda e: app.redo())


if __name__ == "__main__":
    root = tk.Tk()
    app = NotepadPlusPlusApp(root)
    bind_global_shortcuts(app)
    root.mainloop()
