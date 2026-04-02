import os
import time
import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import psutil
from core.recovery import DataRecovery
from utils.helpers import format_size, get_common_extensions

class TabRecovery(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.recovery = None
        self.all_files = []
        self.filtered_files = []
        self.selected_files = []
        self.selected_paths = set()
        self.category_vars = {}
        self.file_checkboxes = {}
        self.rendered_count = 0
        self.batch_size = 50
        self.is_rendering = False
        self.load_more_btn = None
        self.current_folder = ""
        
        self.folder_map = {}
        self.all_dirs = set()
        self.tree_nodes = {}
        self.folder_check_state = {}
        
        self.main_scroll = ctk.CTkScrollableFrame(self)
        self.main_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        self.header_label = ctk.CTkLabel(
            self.header_frame, text="Data Recovery", font=("Segoe UI", 20, "bold")
        )
        self.header_label.pack(side="left")

        self.reset_btn = ctk.CTkButton(
            self.header_frame, text="Reset", fg_color="gray40", hover_color="gray30",
            width=80, height=28, command=self.reset
        )
        self.reset_btn.pack(side="right")
        
        self.source_frame = ctk.CTkFrame(self.main_scroll)
        self.source_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            self.source_frame, text="Source Drive:", font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(15, 10), pady=12)
        
        self.drive_var = ctk.StringVar()
        self.drive_combo = ctk.CTkOptionMenu(
            self.source_frame, variable=self.drive_var, values=self.get_drives(), width=100
        )
        self.drive_combo.pack(side="left", padx=(0, 15), pady=12)
        
        self.scan_btn = ctk.CTkButton(
            self.source_frame, text="Scan Files", command=self.start_scan, width=120
        )
        self.scan_btn.pack(side="left", padx=(0, 15), pady=12)
        
        self.status_label = ctk.CTkLabel(
            self.source_frame, text="", text_color="gray"
        )
        self.status_label.pack(side="left", pady=12)
        
        self.log_frame = ctk.CTkFrame(self.main_scroll, fg_color=("gray90", "gray20"))
        self.log_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.log_header = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.log_header.pack(fill="x", padx=10, pady=(5, 0))
        
        ctk.CTkLabel(
            self.log_header, text="Live Log", font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        
        self.clear_log_btn = ctk.CTkButton(
            self.log_header, text="Clear", command=self.clear_log,
            width=60, height=22, fg_color="gray40", hover_color="gray30"
        )
        self.clear_log_btn.pack(side="right")
        
        self.log_text = tk.Text(
            self.log_frame, wrap="word", font=("Consolas", 9), height=4,
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
            relief="flat", borderwidth=0, padx=10, pady=5
        )
        self.log_text.pack(fill="x", padx=5, pady=(0, 5))
        
        self.log_text.tag_config("ok", foreground="#2ECC71")
        self.log_text.tag_config("partial", foreground="#F39C12")
        self.log_text.tag_config("failed", foreground="#E74C3C")
        self.log_text.tag_config("info", foreground="#3498DB")
        self.log_text.tag_config("skip", foreground="#95A5A6")
        self.log_text.tag_config("header", foreground="#ECF0F1", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("summary", foreground="#9B59B6", font=("Consolas", 9, "bold"))
        
        self.add_log("[INFO] DiskGuard Recovery Log ready.", "info")
        
        self.control_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.start_btn = ctk.CTkButton(
            self.control_frame, text="Start Rescue", command=self.start_rescue,
            fg_color="#27AE60", hover_color="#1E8449", width=140, state="disabled"
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        
        self.cancel_btn = ctk.CTkButton(
            self.control_frame, text="Cancel", command=self.cancel_rescue,
            fg_color="#E74C3C", hover_color="#C0392B", width=100, state="disabled"
        )
        self.cancel_btn.pack(side="left")
        
        self.selected_label = ctk.CTkLabel(
            self.control_frame, text="", text_color="gray"
        )
        self.selected_label.pack(side="left", padx=20)
        
        self.filter_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.filter_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            self.filter_frame, text="Filter by Category:", font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(5, 10))
        
        self.extensions_dict = get_common_extensions()
        self.category_frames = {}
        
        for category in ["Documents", "Images", "Videos", "Audio", "Archives", "All"]:
            var = ctk.BooleanVar(value=(category == "All"))
            self.category_vars[category] = var
            
            cb = ctk.CTkCheckBox(
                self.filter_frame, text=category, variable=var,
                command=lambda c=category: self.on_category_changed(c)
            )
            cb.pack(side="left", padx=5)
            self.category_frames[category] = cb
        
        self.paned_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.paned_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.paned_frame.pack_forget()
        
        self.tree_frame = ctk.CTkFrame(self.paned_frame, width=250, height=250)
        self.tree_frame.pack(side="left", fill="y", padx=(0, 10))
        self.tree_frame.pack_propagate(False)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e",
                        borderwidth=0, font=("Segoe UI", 10))
        style.map('Treeview', background=[('selected', '#1d4ed8')])
        
        self.tree = ttk.Treeview(self.tree_frame, show="tree", height=12)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-1>", self.on_tree_click)
        
        self.list_frame = ctk.CTkFrame(self.paned_frame, height=250)
        self.list_frame.pack(side="left", fill="both", expand=True)
        self.list_frame.pack_propagate(False)
        
        self.search_frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=5, pady=(5, 5))
        
        self.search_entry = ctk.CTkEntry(
            self.search_frame, placeholder_text="Search filename...", width=300
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self.on_search_changed)
        
        self.clear_search_btn = ctk.CTkButton(
            self.search_frame, text="Clear", command=self.clear_search, width=60, height=28
        )
        self.clear_search_btn.pack(side="left", padx=(0, 10))

        self.filter_count_label = ctk.CTkLabel(
            self.search_frame, text="", text_color="gray"
        )
        self.filter_count_label.pack(side="left", padx=5)
        
        self.list_header = ctk.CTkFrame(self.list_frame, fg_color=("gray80", "gray30"))
        self.list_header.pack(fill="x", padx=5, pady=(5, 0))
        
        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_cb = ctk.CTkCheckBox(
            self.list_header, text="", variable=self.select_all_var,
            command=self.toggle_select_all, width=40
        )
        self.select_all_cb.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            self.list_header, text="File Name", font=("Segoe UI", 11, "bold"), width=300
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(
            self.list_header, text="Size", font=("Segoe UI", 11, "bold"), width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(
            self.list_header, text="Status", font=("Segoe UI", 11, "bold"), width=90
        ).pack(side="left", padx=5)
        
        self.file_listbox = ctk.CTkScrollableFrame(
            self.list_frame, fg_color="transparent", height=180
        )
        self.file_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.output_frame = ctk.CTkFrame(self.main_scroll)
        self.output_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.output_frame.pack_forget()
        
        ctk.CTkLabel(
            self.output_frame, text="Output Folder:", font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(15, 10), pady=12)
        
        self.output_entry = ctk.CTkEntry(
            self.output_frame, placeholder_text="Select output folder...", width=400
        )
        self.output_entry.pack(side="left", padx=(0, 10), pady=12, fill="x", expand=True)
        
        self.output_btn = ctk.CTkButton(
            self.output_frame, text="Browse", command=self.browse_output, width=100
        )
        self.output_btn.pack(side="left", padx=(0, 15), pady=12)
        
        self.progress_frame = ctk.CTkFrame(self.main_scroll)
        self.progress_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.progress_frame.pack_forget()
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="Progress: 0%", font=("Segoe UI", 12, "bold")
        )
        self.progress_label.pack(anchor="w", padx=15, pady=(12, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=20)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 8))
        self.progress_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(
            self.progress_frame, text="Rescuing 0 / 0 files", font=("Segoe UI", 10)
        )
        self.stats_label.pack(anchor="w", padx=15, pady=(0, 12))
        
        self.rescue_start_time = None
        self._processed_count = 0
    
    def reset(self):
        self.tree.delete(*self.tree.get_children())
        for widget in self.file_listbox.winfo_children():
            widget.destroy()
        
        self.search_entry.delete(0, "end")
        
        for cat in self.category_vars:
            self.category_vars[cat].set(True if cat == "All" else False)
            
        self.paned_frame.pack_forget()
        self.output_frame.pack_forget()
        self.progress_frame.pack_forget()
        
        self.all_files = []
        self.filtered_files = []
        self.selected_files = []
        self.selected_paths = set()
        
        self.status_label.configure(text="No drive selected")
        self.scan_btn.configure(state="normal", text="Scan Files")
        self.start_btn.configure(state="disabled")
        
        self.progress_bar.set(0)
        
        if hasattr(self, 'log_text'):
            self.log_text.delete("1.0", "end")
            self.add_log("[INFO] DiskGuard Recovery Log ready.", "info")
    
    def clear_log(self):
        self.log_text.delete("1.0", "end")
    
    def add_log(self, message, tag="info"):
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")
    
    def _format_duration(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    
    def get_drives(self):
        drives = []
        for part in psutil.disk_partitions():
            if part.device:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    drive_name = part.device
                    if part.mountpoint:
                        drive_name += f" ({part.mountpoint})"
                    drives.append(drive_name)
                except:
                    drives.append(part.device)
        return drives if drives else ["No drives found"]
    
    def start_scan(self):
        selected_drive = self.drive_var.get()
        if not selected_drive or "No drives" in selected_drive:
            messagebox.showwarning("Warning", "Please select a valid drive.")
            return
        
        drive_letter = selected_drive.split(" ")[0].rstrip("\\").rstrip("/") + "\\"
        
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="Scanning drive...")
        
        self.all_files = []
        self.filtered_files = []
        self.selected_files = []
        self.selected_paths = set()
        self.rendered_count = 0
        
        self.recovery = DataRecovery(drive_letter, "", callback=self.on_scan_progress)
        self.recovery.scan_files()
        
        self.check_scan_complete()
    
    def check_scan_complete(self):
        if self.recovery is None:
            return
        
        if self.recovery._status == "scan_complete" or self.recovery._status == "error":
            self.all_files = self.recovery.scanned_files
            
            self.scan_btn.configure(state="normal", text="Scan Files")
            self.status_label.configure(text=f"Scan complete: {len(self.all_files)} files")
            
            self.paned_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            self.output_frame.pack(fill="x", padx=20, pady=(0, 10))
            
            self.build_tree()
            self.current_folder = ""
            self.apply_filters()
        else:
            if self.recovery.scanned_files:
                self.status_label.configure(
                    text=f"Scanning... {len(self.recovery.scanned_files)} files found"
                )
            self.after(500, self.check_scan_complete)
    
    def on_scan_progress(self, percent, filename, message, status):
        pass

    def build_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.folder_map = {}
        parents = set()
        for f in self.all_files:
            d = os.path.dirname(f["path"])
            if d not in self.folder_map:
                self.folder_map[d] = []
            self.folder_map[d].append(f)
            p = d
            while True:
                parents.add(p)
                new_p = os.path.dirname(p)
                if new_p == p: break
                p = new_p
                
        self.all_dirs = parents
        if not parents: return
        sorted_dirs = sorted(list(parents), key=lambda x: len(x))
        root_dir = sorted_dirs[0]
        
        self.tree_nodes = {}
        self.folder_check_state = {}
        
        root_id = self.tree.insert("", "end", text=f"[ ] 📁 {root_dir}", values=(root_dir,))
        self.tree_nodes[root_dir] = root_id
        self.folder_check_state[root_id] = False
        
        if self._get_child_dirs(root_dir):
            self.tree.insert(root_id, "end", text="dummy")

    def _get_child_dirs(self, parent_dir):
        children = []
        for d in self.all_dirs:
            if d != parent_dir and os.path.dirname(d) == parent_dir:
                children.append(d)
        return children

    def on_tree_open(self, event):
        item = self.tree.focus()
        if not item: return
        
        text = self.tree.item(item, "text")
        if text.startswith("[ ] 📁"):
            self.tree.item(item, text=text.replace("📁", "📂"))
        elif text.startswith("[x] 📁"):
            self.tree.item(item, text=text.replace("📁", "📂"))
            
        children = self.tree.get_children(item)
        if len(children) == 1 and self.tree.item(children[0], "text") == "dummy":
            self.tree.delete(children[0])
            d = self.tree.item(item, "values")[0]
            child_dirs = self._get_child_dirs(d)
            parent_checked = self.folder_check_state.get(item, False)
            prefix = "[x]" if parent_checked else "[ ]"
            
            for child in sorted(child_dirs):
                node_name = os.path.basename(child)
                child_id = self.tree.insert(item, "end", text=f"{prefix} 📁 {node_name}", values=(child,))
                self.tree_nodes[child] = child_id
                self.folder_check_state[child_id] = parent_checked
                
                if self._get_child_dirs(child):
                    self.tree.insert(child_id, "end", text="dummy")

    def on_tree_select(self, event):
        item = self.tree.focus()
        if not item: return
        val = self.tree.item(item, "values")
        if val:
            self.current_folder = val[0]
            folder_path = val[0]
            self.selected_paths = {f["path"] for f in self.all_files if f["path"].startswith(folder_path)}
            self.apply_filters()
            
    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        item = self.tree.identify("item", event.x, event.y)
        if region == "tree" and item:
            x, y, w, h = self.tree.bbox(item)
            if event.x < x + 25: # Click on checkbox approx
                self.toggle_tree_item(item)
                return "break"
                
    def toggle_tree_item(self, item, check=None):
        current = self.folder_check_state.get(item, False)
        new_state = check if check is not None else not current
        self.folder_check_state[item] = new_state
        
        text = self.tree.item(item, "text")
        if new_state:
            self.tree.item(item, text=text.replace("[ ]", "[x]"))
        else:
            self.tree.item(item, text=text.replace("[x]", "[ ]"))
            
        for child in self.tree.get_children(item):
            if self.tree.item(child, "text") != "dummy":
                self.toggle_tree_item(child, new_state)
                
        folder_path = self.tree.item(item, "values")[0]
        for f in self.all_files:
            if f["path"].startswith(folder_path):
                if new_state:
                    self.selected_paths.add(f["path"])
                else:
                    self.selected_paths.discard(f["path"])
                    
        self.apply_filters()

    def on_category_changed(self, changed_category=None):
        selected_categories = []
        for cat, var in self.category_vars.items():
            if var.get():
                selected_categories.append(cat)
        
        if changed_category == "All":
            if "All" in selected_categories:
                for cat in self.category_vars:
                    if cat != "All":
                        self.category_vars[cat].set(False)
                selected_categories = ["All"]
        elif "All" in selected_categories and changed_category and changed_category != "All":
            self.category_vars["All"].set(False)
            selected_categories.remove("All")
        
        self.apply_filters()
    
    def on_search_changed(self, event=None):
        self.apply_filters()
    
    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.apply_filters()
    
    def apply_filters(self):
        search_text = self.search_entry.get().strip().lower()
        selected_categories = []
        for cat, var in self.category_vars.items():
            if var.get():
                selected_categories.append(cat)
                
        base_files = self.folder_map.get(self.current_folder, []) if self.current_folder else self.all_files
        
        if "All" in selected_categories:
            filtered = list(base_files)
        elif selected_categories:
            extensions = []
            for cat in selected_categories:
                if cat in self.extensions_dict:
                    extensions.extend(self.extensions_dict[cat])
            
            filtered = [
                f for f in base_files 
                if any(f["name"].lower().endswith(ext) for ext in extensions)
            ]
        else:
            filtered = []
        
        if search_text:
            filtered = [
                f for f in filtered 
                if search_text in f["name"].lower()
            ]
        
        self.filtered_files = filtered
        self.update_filter_count()
        self.init_file_list(self.filtered_files)
        self.calc_global_selection()
    
    def update_filter_count(self):
        total_size = sum(f["size"] for f in self.filtered_files)
        if self.rendered_count < len(self.filtered_files):
            self.filter_count_label.configure(
                text=f"Showing {self.rendered_count} of {len(self.filtered_files)} files ({format_size(total_size)})"
            )
        else:
            self.filter_count_label.configure(
                text=f"{len(self.filtered_files)} files ({format_size(total_size)})"
            )
    
    def init_file_list(self, files):
        for widget in self.file_listbox.winfo_children():
            widget.destroy()
        
        self.file_checkboxes = {}
        self.rendered_count = 0
        self.is_rendering = False
        
        if files:
            sorted_files = sorted(files, key=lambda f: (
                0 if (f.get('readable') == False or f.get('size') == 0) else 1,
                f['name'].lower()
            ))
            self.filtered_files = sorted_files
            
            for f in self.filtered_files:
                is_error = (f.get('readable') == False or f.get('size') == 0)
                if is_error:
                    self.selected_paths.discard(f['path'])
                else:
                    self.selected_paths.add(f['path'])
            
            all_selected = all((f["path"] in self.selected_paths) for f in files)
            self.select_all_var.set(all_selected)
            self.calc_global_selection()
        else:
            self.select_all_var.set(False)
            
        self.render_batch(0, min(self.batch_size, len(self.filtered_files)))
    
    def render_batch(self, start, end):
        if self.is_rendering:
            return
        
        self.is_rendering = True
        files = self.filtered_files
        end = min(end, len(files))
        
        for i in range(start, end):
            file_info = files[i]
            
            row_frame = ctk.CTkFrame(self.file_listbox, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)
            
            if i % 2 == 0:
                row_frame.configure(fg_color=("gray90", "gray25"))
            
            var = ctk.BooleanVar(value=(file_info["path"] in self.selected_paths))
            self.file_checkboxes[i] = (var, file_info)
            
            cb = ctk.CTkCheckBox(
                row_frame, text="", variable=var,
                command=self.update_selection_from_ui, width=40
            )
            cb.pack(side="left", padx=5)
            
            name_label = ctk.CTkLabel(
                row_frame, text=file_info["name"][:45], anchor="w", width=300
            )
            name_label.pack(side="left", padx=5)
            
            size_label = ctk.CTkLabel(
                row_frame, text=format_size(file_info["size"]), width=100
            )
            size_label.pack(side="left", padx=5)
            
            status_text = "Readable" if file_info["readable"] else "Error"
            status_color = "#2ECC71" if file_info["readable"] else "#E74C3C"
            status_label = ctk.CTkLabel(
                row_frame, text=status_text, text_color=status_color, width=90
            )
            status_label.pack(side="left", padx=5)
        
        self.rendered_count = end
        self.is_rendering = False
        
        self.update_filter_count()
        
        if self.rendered_count < len(files):
            if self.load_more_btn:
                self.load_more_btn.destroy()
            
            self.load_more_btn = ctk.CTkButton(
                self.file_listbox,
                text=f"Load More ({len(files) - self.rendered_count} remaining)",
                command=self.load_more,
                height=35
            )
            self.load_more_btn.pack(pady=10, fill="x", padx=10)
        elif self.load_more_btn:
            self.load_more_btn.destroy()
            self.load_more_btn = None
    
    def load_more(self):
        files = self.filtered_files
        start = self.rendered_count
        end = min(start + self.batch_size, len(files))
        
        self.render_batch(start, end)
        
    def toggle_select_all(self):
        select_all = self.select_all_var.get()
        for idx, (var, file_info) in self.file_checkboxes.items():
            var.set(select_all)
            if select_all:
                self.selected_paths.add(file_info["path"])
            else:
                self.selected_paths.discard(file_info["path"])
                
        # Also apply to off-screen filtered files!
        for f in self.filtered_files:
            if select_all:
                self.selected_paths.add(f["path"])
            else:
                self.selected_paths.discard(f["path"])
                
        self.calc_global_selection()
    
    def update_selection_from_ui(self):
        for idx, (var, file_info) in self.file_checkboxes.items():
            if var.get():
                self.selected_paths.add(file_info["path"])
            else:
                self.selected_paths.discard(file_info["path"])
        
        # Determine Select All state for current folder dynamically
        all_selected = all((f["path"] in self.selected_paths) for f in self.filtered_files) if self.filtered_files else False
        self.select_all_var.set(all_selected)
        
        self.calc_global_selection()
        
    def calc_global_selection(self):
        self.selected_files = [f for f in self.filtered_files if f["path"] in self.selected_paths]
        total_selected = len(self.selected_files)
        total_size = sum(f["size"] for f in self.selected_files)
        
        self.selected_label.configure(
            text=f"{total_selected} files selected ({format_size(total_size)})"
        )
        
        has_output = bool(self.output_entry.get())
        self.start_btn.configure(
            state="normal" if (total_selected > 0 and has_output) else "disabled"
        )
    
    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)
            self.calc_global_selection()
    
    def start_rescue(self):
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select files to rescue.")
            return
        
        output_folder = self.output_entry.get()
        if not output_folder:
            messagebox.showwarning("Warning", "Please select output folder.")
            return
        
        drive_letter = self.drive_var.get().split(" ")[0].rstrip(":") + ":"
        
        self.recovery = DataRecovery(drive_letter, output_folder, callback=self.on_rescue_progress)
        
        self._processed_count = 0
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.log_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.clear_log()
        
        self.rescue_start_time = time.time()
        self.add_log("=" * 60, "header")
        self.add_log(f"[INFO] Starting rescue: {len(self.selected_files)} files", "info")
        self.add_log(f"[INFO] Output: {output_folder}", "info")
        self.add_log(f"[INFO] Source: {drive_letter}", "info")
        self.add_log("=" * 60, "header")
        
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        
        self.recovery.rescue_files(self.selected_files, skip_errors=True)
        
        self.check_rescue_complete()
    
    def check_rescue_complete(self):
        if self.recovery and self.recovery._status == "rescue_complete":
            self.on_rescue_complete()
        elif self.recovery and self.recovery._status == "cancelled":
            self.cancel_btn.configure(state="disabled")
        else:
            self.after(100, self.check_rescue_complete)
    
    def on_rescue_progress(self, percent, filename, message, status):
        self.after(0, lambda: self.update_rescue_progress(percent, filename, message, status))
    
    def update_rescue_progress(self, percent, filename, message, status):
        if status == "complete":
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="Progress: 100%")
            self.stats_label.configure(text="Complete")
            self.add_log(message, "summary")
        elif status == "rescuing":
            self.progress_bar.set(percent / 100)
            self.progress_label.configure(text=f"Progress: {percent:.1f}%")
            self.stats_label.configure(text=f"Processing: {filename[:30]}...")
        elif status == "file_ok":
            self._processed_count += 1
            self.add_log(message, "ok")
            self.stats_label.configure(text=f"Rescued {self._processed_count} / {len(self.selected_files)} files")
            self.progress_bar.set(self._processed_count / len(self.selected_files))
            self.progress_label.configure(text=f"Progress: {self._processed_count * 100 / len(self.selected_files):.1f}%")
        elif status == "file_partial":
            self._processed_count += 1
            self.add_log(message, "partial")
            self.stats_label.configure(text=f"Rescued {self._processed_count} / {len(self.selected_files)} files")
            self.progress_bar.set(self._processed_count / len(self.selected_files))
            self.progress_label.configure(text=f"Progress: {self._processed_count * 100 / len(self.selected_files):.1f}%")
        elif status == "file_failed":
            self._processed_count += 1
            self.add_log(message, "failed")
            self.stats_label.configure(text=f"Rescued {self._processed_count} / {len(self.selected_files)} files")
            self.progress_bar.set(self._processed_count / len(self.selected_files))
            self.progress_label.configure(text=f"Progress: {self._processed_count * 100 / len(self.selected_files):.1f}%")
        elif status == "file_skip":
            self._processed_count += 1
            self.add_log(message, "skip")
            self.stats_label.configure(text=f"Rescued {self._processed_count} / {len(self.selected_files)} files")
            self.progress_bar.set(self._processed_count / len(self.selected_files))
            self.progress_label.configure(text=f"Progress: {self._processed_count * 100 / len(self.selected_files):.1f}%")
        else:
            self.progress_bar.set(percent / 100)
            self.progress_label.configure(text=f"Progress: {percent:.1f}%")
            self.stats_label.configure(text=f"Processing: {message}")
    
    def on_rescue_complete(self):
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="Progress: 100%")
        self.stats_label.configure(text=f"Complete: {len(self.selected_files)} / {len(self.selected_files)} files")
        
        report = self.recovery.get_rescue_report() if self.recovery else {"rescued_ok": 0, "rescued_partial": 0, "failed": 0, "failed_list": [], "total_found": 0, "output_folder": ""}
        
        if self.rescue_start_time:
            duration = time.time() - self.rescue_start_time
            self.add_log("=" * 60, "header")
            self.add_log(
                f"[SUMMARY] Rescue complete: {report['rescued_ok']} OK, {report['rescued_partial']} partial, {report['failed']} failed",
                "summary"
            )
            self.add_log(f"[SUMMARY] Duration: {self._format_duration(duration)}", "summary")
            self.add_log("=" * 60, "header")
        
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        
        self.show_report_popup(report)
    
    def show_report_popup(self, report):
        popup = ctk.CTkToplevel(self)
        popup.title("Rescue Report")
        popup.geometry("450x400")
        popup.transient(self)
        popup.grab_set()
        
        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            frame, text="Rescue Report", font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 20))
        
        summary_items = [
            ("Total Files Found", str(report['total_found'])),
            ("Rescued Successfully", f"{report['rescued_ok']} files"),
            ("Partial Rescue (bad sectors)", f"{report['rescued_partial']} files"),
            ("Failed Total", f"{report['failed']} files"),
            ("Output Folder", report['output_folder']),
        ]
        
        for label, value in summary_items:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=f"{label}:", width=160, anchor="w").pack(side="left")
            color = "#2ECC71" if "Successfully" in label else ("#F39C12" if "Partial" in label else ("#E74C3C" if "Failed" in label else "gray"))
            ctk.CTkLabel(row, text=value, font=("Segoe UI", 11, "bold"), text_color=color, anchor="e").pack(side="right")
        
        if report['failed_list']:
            ctk.CTkLabel(
                frame, text="Failed Files:", font=("Segoe UI", 11, "bold"), anchor="w"
            ).pack(pady=(15, 5))
            
            scroll_frame = ctk.CTkScrollableFrame(frame, height=120)
            scroll_frame.pack(fill="x", pady=(0, 10))
            
            for fail in report['failed_list'][:20]:
                ctk.CTkLabel(
                    scroll_frame, text=f"• {fail['file'][:40]}", text_color="#E74C3C", anchor="w"
                ).pack(fill="x")
            
            if len(report['failed_list']) > 20:
                ctk.CTkLabel(
                    scroll_frame, text=f"... and {len(report['failed_list']) - 20} more", text_color="gray"
                ).pack()
        
        ctk.CTkButton(
            popup, text="Close", command=popup.destroy, width=100
        ).pack(pady=(20, 0))
    
    def cancel_rescue(self):
        if self.recovery:
            self.recovery.cancel()
            self.add_log("[INFO] Rescue cancelled by user", "skip")
            self.status_label.configure(text="Cancelled")
