import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Task Manager (CPU, Power, Network, Search)")

        # Approximate CPU TDP (for power estimation)
        self.CPU_TDP_WATTS = 15.0

        # Frame for search and memory limit
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10, fill=tk.X)

        # Search label and entry
        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(input_frame, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        # Memory limit input
        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry = tk.Entry(input_frame, width=10)
        self.memory_limit_entry.pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry.insert(0, "200")

        # Buttons
        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="Refresh", command=self.refresh_processes).pack(side=tk.LEFT, padx=5)

        # Treeview setup with Power & Network columns
        columns = ("pid", "name", "cpu", "memory", "publisher", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        for col, text, width in [
            ("pid", "PID", 70),
            ("name", "Name", 180),
            ("cpu", "CPU (%)", 80),
            ("memory", "Memory (MB)", 100),
            ("publisher", "Publisher", 160),
            ("power", "Power (mW)", 100),
            ("network", "Network (KB/s)", 120),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("high_memory", background="#ffcccc")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Initialize data holders
        self.all_processes = []
        self.last_net_io = {}
        self.update_interval = 300000  # 5 minutes

        # Prime CPU readings for smoother numbers
        self._prime_cpu_percent()

        # Start the first update
        self.refresh_processes()

    # ---------- Helper methods ----------

    def _prime_cpu_percent(self):
        """Initialize CPU percent values."""
        for proc in psutil.process_iter(['pid']):
            try:
                proc.cpu_percent(interval=None)
            except Exception:
                pass
        psutil.cpu_percent(interval=None)

    def _estimate_power_mw(self, proc_cpu_percent):
        """Estimate power based on CPU usage and CPU TDP."""
        try:
            return f"{(proc_cpu_percent / 100.0) * self.CPU_TDP_WATTS * 1000:.0f}"
        except Exception:
            return "—"

    def _get_network_kbps(self, proc, now_time):
        """Estimate per-process I/O rate in KB/s."""
        try:
            io = proc.io_counters()
            total_bytes = io.read_bytes + io.write_bytes
            pid = proc.pid
            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta_bytes = total_bytes - last_bytes
                delta_time = max(now_time - last_time, 0.001)
                rate_kbps = (delta_bytes / delta_time) / 1024
            else:
                rate_kbps = 0.0
            self.last_net_io[pid] = (total_bytes, now_time)
            return f"{rate_kbps:.1f}"
        except Exception:
            return "—"

    def get_publisher(self, exe_path):
        """Try to get publisher info for Windows executables."""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, '\\')
            str_info = win32api.VerQueryValue(info, '\\StringFileInfo\\040904B0\\CompanyName')
            return str_info.strip() if str_info else "Unknown"
        except Exception:
            return "Unknown"

    # ---------- Update & Display ----------

    def refresh_processes(self):
        """Start a background update."""
        threading.Thread(target=self.update_processes_list, daemon=True).start()
        self.root.after(self.update_interval, self.refresh_processes)

    def update_processes_list(self):
        """Fetch process data (background thread)."""
        processes = []
        now = time.time()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                pinfo = proc.info
                pid = pinfo['pid']
                name = pinfo['name'] or "Unknown"
                cpu = proc.cpu_percent(interval=None)
                mem_mb = (pinfo['memory_info'].rss / (1024 * 1024))
                publisher = self.get_publisher(pinfo.get('exe') or "")
                power = self._estimate_power_mw(cpu)
                network = self._get_network_kbps(proc, now)

                processes.append({
                    "pid": pid,
                    "name": name,
                    "cpu": cpu,
                    "memory": mem_mb,
                    "publisher": publisher,
                    "power": power,
                    "network": network
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        self.all_processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)
        self.root.after(0, lambda: self.display_processes(self.all_processes))

    def display_processes(self, processes):
        """Update the TreeView with the current process list."""
        self.tree.delete(*self.tree.get_children())

        try:
            memory_limit = float(self.memory_limit_entry.get())
        except ValueError:
            memory_limit = 0

        for p in processes:
            tag = "high_memory" if memory_limit > 0 and p["memory"] > memory_limit else ""
            self.tree.insert("", tk.END,
                             values=(p["pid"], p["name"], f"{p['cpu']:.1f}",
                                     f"{p['memory']:.2f}", p["publisher"],
                                     p["power"], p["network"]),
                             tags=(tag,))

    # ---------- Search Feature ----------

    def search_process(self):
        """Filter process list by PID or name."""
        query = self.search_entry.get().strip().lower()
        if not self.all_processes:
            messagebox.showinfo("Info", "Process list is empty. Please refresh first.")
            return

        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = []
        for p in self.all_processes:
            if query.isdigit() and int(query) == p["pid"]:
                filtered.append(p)
            elif query in p["name"].lower():
                filtered.append(p)

        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        self.display_processes(filtered)


# ---------- Run the app ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.geometry("1050x600")
    root.mainloop()
