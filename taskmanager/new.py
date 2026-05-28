import psutil
import tkinter as tk
from tkinter import ttk
import threading
import time
import os

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Task Manager")

        # Set up the Treeview (table)
        columns = ("pid", "name", "cpu", "memory", "publisher")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Name")
        self.tree.heading("cpu", text="CPU (milliseconds)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("publisher", text="Publisher")

        self.tree.column("pid", width=80)
        self.tree.column("name", width=200)
        self.tree.column("cpu", width=80)
        self.tree.column("memory", width=100)
        self.tree.column("publisher", width=200)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Add a refresh button
        refresh_button = tk.Button(root, text="Refresh", command=self.refresh_processes)
        refresh_button.pack(pady=5)

        # Update every 5 minutes (300000 ms)
        self.update_interval = 300000
        self.refresh_processes()

    def refresh_processes(self):
        """Refresh the process list in a background thread."""
        threading.Thread(target=self.update_processes_list, daemon=True).start()
        # Schedule next refresh
        self.root.after(self.update_interval, self.refresh_processes)

    def get_publisher(self, exe_path):
        """Try to get publisher info for Windows executables"""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, '\\')
            str_info = win32api.VerQueryValue(info, '\\StringFileInfo\\040904B0\\CompanyName')
            return str_info.strip() if str_info else "Unknown"
        except Exception:
            return "Unknown"

    def update_processes_list(self):
        """Collect and display process info."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe']):
            try:
                pinfo = proc.info
                exe_path = pinfo.get('exe') or ""
                publisher = self.get_publisher(exe_path)
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_usage': pinfo['memory_info'].rss / (1024 * 1024),  # MB
                    'publisher': publisher
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Clear existing entries
        self.tree.delete(*self.tree.get_children())

        # Sort processes by CPU usage
        processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)

        # Insert new data
        for proc in processes:
            self.tree.insert("", tk.END, values=(
                proc['pid'],
                proc['name'],
                f"{proc['cpu_percent']:.1f}",
                f"{proc['memory_usage']:.2f}",
                proc['publisher']
            ))

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
