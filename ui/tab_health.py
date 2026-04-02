import customtkinter as ctk
from core.health import get_all_disks, scan_disk_async


class TabHealth(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.disks = []
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.header_label = ctk.CTkLabel(
            self.header_frame, text="Disk Health Check", font=("Segoe UI", 20, "bold")
        )
        self.header_label.pack(side="left")

        self.reset_btn = ctk.CTkButton(
            self.header_frame, text="Reset", fg_color="gray40", hover_color="gray30",
            width=80, height=28, command=self.reset
        )
        self.reset_btn.pack(side="right")
        
        self.select_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.select_frame.pack(fill="x", padx=20, pady=10)
        
        self.disk_label = ctk.CTkLabel(self.select_frame, text="Select Disk:")
        self.disk_label.pack(side="left", padx=(0, 10))
        
        self.disk_combo = ctk.CTkOptionMenu(
            self.select_frame, values=["Scan untuk list disk..."], width=200
        )
        self.disk_combo.pack(side="left", padx=(0, 10))
        
        self.scan_btn = ctk.CTkButton(
            self.select_frame, text="Scan Now", command=self.on_scan_clicked, width=120
        )
        self.scan_btn.pack(side="left")
        
        self.status_label = ctk.CTkLabel(self.select_frame, text="")
        self.status_label.pack(side="left", padx=20)
        
        self.results_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", height=400
        )
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.load_disks()
    
    def load_disks(self):
        self.disks = get_all_disks()
        if self.disks:
            values = [f"{d['drive_letter']} - {d['name'][:30]} ({d['type']})" for d in self.disks]
            self.disk_combo.configure(values=values)
            self.disk_combo.set(values[0])
        else:
            self.disk_combo.configure(values=["Tidak ada disk terdeteksi"])
            self.disk_combo.set("Tidak ada disk terdeteksi")
    
    def on_scan_clicked(self):
        selected = self.disk_combo.get()
        if not self.disks or "Tidak ada" in selected:
            return
        
        idx = self.disk_combo.cget("values").index(selected)
        drive_letter = self.disks[idx]["drive_letter"]
        
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="Scanning disk...")
        self.clear_results()
        
        scan_disk_async(drive_letter, self.on_scan_complete)
    
    def on_scan_complete(self, data):
        self.scan_btn.configure(state="normal", text="Scan Now")
        self.status_label.configure(text="Scan complete")
        self.display_results(data)
    
    def clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
    
    def display_results(self, data):
        self.clear_results()
        
        status = data.get("status", "Unknown")
        color_map = {"Good": "#2ECC71", "Warning": "#F39C12", "Critical": "#E74C3C", "Unknown": "#95A5A6"}
        status_color = color_map.get(status, "#95A5A6")
        
        status_card = ctk.CTkFrame(self.results_frame, corner_radius=15)
        status_card.pack(fill="x", pady=(0, 15))
        
        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            status_inner, text="Health Status", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w")
        
        status_badge = ctk.CTkLabel(
            status_inner, text=status, font=("Segoe UI", 16, "bold"),
            text_color=status_color
        )
        status_badge.grid(row=0, column=1, sticky="e", padx=(20, 0))
        
        ctk.CTkLabel(
            status_inner, text="Health Score", font=("Segoe UI", 14, "bold")
        ).grid(row=1, column=0, sticky="w", pady=(15, 0))
        
        health_percent = data.get("health_percent", 0)
        health_bar = ctk.CTkProgressBar(status_inner, width=200, height=20)
        health_bar.set(health_percent / 100)
        health_bar.grid(row=1, column=1, sticky="e", padx=(20, 0), pady=(15, 0))
        
        ctk.CTkLabel(
            status_inner, text=f"{health_percent}%"
        ).grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(15, 0))
        
        details_card = ctk.CTkFrame(self.results_frame, corner_radius=15)
        details_card.pack(fill="x", pady=(0, 15))
        
        details_inner = ctk.CTkFrame(details_card, fg_color="transparent")
        details_inner.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            details_inner, text="Disk Details", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        details = [
            ("Temperature", f"{data.get('temperature', 'N/A')} °C"),
            ("Bad Sectors", str(data.get('bad_sectors', 'N/A'))),
            ("Reallocated Sectors", str(data.get('reallocated_sectors', 'N/A'))),
            ("Power On Hours", f"{data.get('power_on_hours', 'N/A')} hrs"),
        ]
        
        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(
                details_inner, text=f"{label}:", font=("Segoe UI", 12)
            ).grid(row=i+1, column=0, sticky="w", pady=5)
            ctk.CTkLabel(
                details_inner, text=value, font=("Segoe UI", 12, "bold")
            ).grid(row=i+1, column=1, sticky="e", pady=5)
        
        message = data.get("message")
        if message:
            ctk.CTkLabel(
                details_inner, text=message, font=("Segoe UI", 10),
                text_color="#F39C12"
            ).grid(row=len(details)+1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        source = data.get("source", "")
        if source == "unavailable":
            ctk.CTkLabel(
                details_inner, text="(Run as Administrator for full SMART data)", 
                font=("Segoe UI", 9), text_color="gray"
            ).grid(row=len(details)+2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        usage_card = ctk.CTkFrame(self.results_frame, corner_radius=15)
        usage_card.pack(fill="x")
        
        usage_inner = ctk.CTkFrame(usage_card, fg_color="transparent")
        usage_inner.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            usage_inner, text="Disk Usage", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        usage_total = data.get('total_gb', 0)
        usage_used = data.get('used_gb', 0)
        usage_free = data.get('free_gb', 0)
        usage_percent = data.get('percent', 0)
        
        ctk.CTkLabel(
            usage_inner, text="Used:"
        ).grid(row=1, column=0, sticky="w", pady=3)
        ctk.CTkLabel(
            usage_inner, text=f"{usage_used} GB / {usage_total} GB", font=("Segoe UI", 12, "bold")
        ).grid(row=1, column=1, sticky="e", pady=3)
        
        usage_bar = ctk.CTkProgressBar(usage_inner, width=300, height=15)
        usage_bar.set(usage_percent / 100)
        usage_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 10))
        
        ctk.CTkLabel(
            usage_inner, text="Free:"
        ).grid(row=3, column=0, sticky="w", pady=3)
        ctk.CTkLabel(
            usage_inner, text=f"{usage_free} GB ({100 - usage_percent}%)", font=("Segoe UI", 12, "bold")
        ).grid(row=3, column=1, sticky="e", pady=3)

    def reset(self):
        self.clear_results()
        self.status_label.configure(text="Ready to scan")
        self.scan_btn.configure(state="normal", text="Scan Now")
        self.load_disks()
