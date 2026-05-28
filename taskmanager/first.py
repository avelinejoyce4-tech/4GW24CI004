import psutil
import tkinter as tk
from tkinter import ttk
import threading
import time

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Task Manager")

        # Set up the Treeview (table)
        columns = ("pid", "name", "cpu", "memory")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Name")
        self.tree.heading("cpu", text="CPU milliseconds")
        self.tree.heading("memory", text="Memory (MB)")
        
        self.tree.column("pid", width=80)
        self.tree.column("name", width=200)
        self.tree.column("cpu", width=80)
        self.tree.column("memory", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Add a refresh button
        refresh_button = tk.Button(root, text="Refresh", command=self.refresh_processes)
        refresh_button.pack(pady=5)

        # Start periodic update
        self.update_interval = 300000  # milliseconds
        self.refresh_processes()

    def refresh_processes(self):
        # Run the process fetching in a separate thread to avoid UI freeze
        threading.Thread(target=self.update_process_list, daemon=True).start()
        # Schedule next update
        self.root.after(self.update_interval, self.refresh_processes)

    def update_process_list(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_usage': pinfo['memory_info'].rss / (1024 * 1024)  # MB
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
                f"{proc['memory_usage']:.2f}"
            ))

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()