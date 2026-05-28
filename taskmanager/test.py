import psutil
import tkinter as tk
from tkinter import ttk
import threading
import time
import os

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")

        # ===== CPU Usage Bar =====
        cpu_frame = ttk.Frame(root)
        cpu_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(cpu_frame, text="CPU Usage: ", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)

        self.cpu_var = tk.DoubleVar()
        self.cpu_bar = ttk.Progressbar(cpu_frame, orient="horizontal", length=300, mode="determinate", variable=self.cpu_var, maximum=100)
        self.cpu_bar.pack(side=tk.LEFT, padx=10)

        self.cpu_label = ttk.Label(cpu_frame, text="0%", font=("Segoe UI", 10, "bold"))
        self.cpu_label.pack(side=tk.LEFT)

        # ===== Refresh Button =====
        refresh_button = ttk.Button(cpu_frame, text="🔄 Refresh", command=self.manual_refresh)
        refresh_button.pack(side=tk.RIGHT)

        # ===== Treeview for Processes =====
        columns = ("pid", "name", "cpu", "memory", "publisher")
        self.tree = ttk.Treeview(root, columns=columns, show='headings', height=20)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Create headings
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Process Name")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("publisher", text="Publisher")

        # Set column widths
        self.tree.column("pid", width=80, anchor="center")
        self.tree.column("name", width=200, anchor="w")
        self.tree.column("cpu", width=100, anchor="center")
        self.tree.column("memory", width=120, anchor="center")
        self.tree.column("publisher", width=250, anchor="w")

        # Start background update thread
        threading.Thread(target=self.update_processes, daemon=True).start()

    # -------- Get publisher information -------- #
    def get_publisher(self, exe_path):
        """Try to get publisher info for Windows executables"""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, '\\')

            # Get all language/codepage pairs
            translations = win32api.VerQueryValue(info, '\\VarFileInfo\\Translation')
            for lang, codepage in translations:
                key = f'\\StringFileInfo\\{lang:04x}{codepage:04x}\\CompanyName'
                company = win32api.VerQueryValue(info, key)
                if company:
                    return company.strip()
        except Exception:
            pass
        return "Unknown"

    # -------- Update process list every second -------- #
    def update_processes(self):
        # Initial CPU read to establish baseline
        for p in psutil.process_iter():
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

        while True:
            self.refresh_cpu_bar()
            self.load_process_data()
            time.sleep(3000000)  # Refresh every 5 minutes

    # -------- Manual refresh on button click -------- #
    def manual_refresh(self):
        self.load_process_data()

    # -------- Load processes into Treeview -------- #
    def load_process_data(self):
        # Clear old data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch and insert process data
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                exe_path = proc.info['exe']
                cpu = proc.cpu_percent(interval=None)
                mem = proc.info['memory_info'].rss / (1024 * 1024)  # Convert bytes to MB

                publisher = self.get_publisher(exe_path) if exe_path else "Unknown"

                self.tree.insert("", "end", values=(pid, name, f"{cpu:.1f}", f"{mem:.2f}", publisher))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    # -------- CPU Bar Updater -------- #
    def refresh_cpu_bar(self):
        cpu_usage = psutil.cpu_percent(interval=None)
        self.cpu_var.set(cpu_usage)
        self.cpu_label.config(text=f"{cpu_usage:.1f}%")

# -------- Run the app -------- #
if __name__ == "__main__":
       root = tk.Tk()
       app = TaskManagerApp(root)
       root.mainloop()