import os
import sys
import ctypes
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from ui.tab_health import TabHealth
from ui.tab_recovery import TabRecovery

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
ICON_PNG_PATH = os.path.join(BASE_DIR, "icon.png")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)
    
    def show(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(
            self.tooltip, text=self.text, justify="left",
            fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=5,
            padx=8, pady=4, font=("Segoe UI", 10)
        )
        label.pack()
    
    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class LoadingSpinner(ctk.CTkFrame):
    def __init__(self, master, text="Loading..."):
        super().__init__(master, fg_color=("gray90", "gray20"), corner_radius=10)
        
        self.spinner_label = ctk.CTkLabel(
            self, text="⏳", font=("Segoe UI", 24)
        )
        self.spinner_label.pack(pady=(15, 5))
        
        self.text_label = ctk.CTkLabel(
            self, text=text, font=("Segoe UI", 12)
        )
        self.text_label.pack(pady=(0, 15))
        
        self.after(100, self._animate)
    
    def _animate(self):
        symbols = ["⏳", "⏰", "⏳", "⏱️"]
        current = self.text_label.cget("text")
        idx = symbols.index(current) + 1 if current in symbols else 0
        self.spinner_label.configure(text=symbols[idx % len(symbols)])
        self.after(200, self._animate)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DiskGuard v1.0.0")
        self.geometry("1000x700")
        
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass
                
            try:
                from PIL import ImageTk
                img = Image.open(ICON_PNG_PATH if os.path.exists(ICON_PNG_PATH) else ICON_PATH)
                photo = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, photo)
            except Exception:
                pass
        
        from config import config
        saved_theme = config.get('theme', 'dark') or 'dark'
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("blue")
        self.current_theme = saved_theme
        
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)
        
        header_icon_path = ICON_PNG_PATH if os.path.exists(ICON_PNG_PATH) else ICON_PATH
        if os.path.exists(header_icon_path):
            icon_img = CTkImage(Image.open(header_icon_path), size=(32, 32))
            self.header_icon = ctk.CTkLabel(
                self.header_frame, image=icon_img, text=""
            )
            self.header_icon.pack(side="left", padx=(10, 5))
        
        self.logo_label = ctk.CTkLabel(
            self.header_frame, text="DiskGuard", 
            font=("Segoe UI", 20, "bold")
        )
        self.logo_label.pack(side="left", padx=(5, 20))
        
        self.version_label = ctk.CTkLabel(
            self.header_frame, text="v1.0.0", 
            font=("Segoe UI", 12), text_color="gray"
        )
        self.version_label.pack(side="left", padx=(5, 0))
        
        self.settings_btn = ctk.CTkButton(
            self.header_frame, text="⚙️", width=40, height=30,
            command=self.open_settings
        )
        self.settings_btn.pack(side="right", padx=5)
        ToolTip(self.settings_btn, "Settings")
        
        self.theme_btn = ctk.CTkButton(
            self.header_frame, text="🌙" if saved_theme == "light" else "☀️", width=40, height=30,
            command=self.toggle_theme
        )
        self.theme_btn.pack(side="right", padx=(0, 10))
        ToolTip(self.theme_btn, "Toggle Theme")
        
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_view.add("Recovery")
        self.tab_view.add("Health Check")
        self.tab_view.set("Recovery")

        self.recovery_tab = TabRecovery(self.tab_view.tab("Recovery"))
        self.recovery_tab.pack(fill="both", expand=True)
        
        self.health_tab = TabHealth(self.tab_view.tab("Health Check"))
        self.health_tab.pack(fill="both", expand=True)
        
        self.status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, text="Ready", anchor="w",
            font=("Segoe UI", 10), text_color="gray"
        )
        self.status_label.pack(side="left", padx=15)
        
        self.status_indicator = ctk.CTkLabel(
            self.status_frame, text="●", text_color="#2ECC71",
            font=("Segoe UI", 10)
        )
        self.status_indicator.pack(side="right", padx=15)
        
        self.loading_overlay = None
    
    def set_status(self, text, color="#95A5A6"):
        self.status_label.configure(text=text)
        self.status_indicator.configure(text_color=color)
        self.update_idletasks()
    
    def show_loading(self, text="Loading..."):
        if not self.loading_overlay:
            self.loading_overlay = ctk.CTkFrame(self, fg_color=("white", "#1a1a1a"), corner_radius=0)
            self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.loading_overlay.lift()
            
            self.spinner = LoadingSpinner(self.loading_overlay, text=text)
            self.spinner.place(relx=0.5, rely=0.5, anchor="center")
    
    def hide_loading(self):
        if self.loading_overlay:
            self.loading_overlay.destroy()
            self.loading_overlay = None
    
    def open_settings(self):
        from config import config
        from tkinter import messagebox
        
        settings_text = f"""Settings Configuration:

Default Output Folder: {config.get('default_output_folder', 'Not set')}
Chunk Size: {config.get('chunk_size_mb', 4)} MB
Auto-Retry Count: {config.get('auto_retry_count', 5)}
Theme: {config.get('theme', 'dark')}
Color Accent: {config.get('color_accent', 'blue')}

Settings are stored in:
{config.config_file}

Note: Full settings UI coming soon!"""
        
        messagebox.showinfo("DiskGuard Settings", settings_text)
    
    def toggle_theme(self):
        from config import config
        
        if self.current_theme == "dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="🌙")
            self.current_theme = "light"
            config.set('theme', 'light')
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="☀️")
            self.current_theme = "dark"
            config.set('theme', 'dark')


def run():
    # Tell Windows to use a specific app ID for taskbar icon grouping
    myappid = 'diskguard.app.v1'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
        
    app = App()
    app.mainloop()
