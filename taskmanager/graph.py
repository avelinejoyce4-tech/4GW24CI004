import psutil
import tkinter as tk
from tkinter import ttk
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager with Power, Network & Live Graph")

        self.CPU_TDP_WATTS = 15.0

        # Main layout frames
        top_frame = tk.Frame(root)
        top_frame.pack(fill=tk.BOTH, expand=True)

        graph_frame = tk.Frame(root, height=200)
        graph_frame.pack(fill=tk.BOTH, expand=False, pady=10)

        # TreeView Table
        columns = ("pid", "name", "cpu", "memory", "publisher", "power_mw", "network")
        self.tree = ttk.Treeview(top_frame, columns=columns, show='headings', height=15)

        for col, text in zip(columns, ["PID", "Name", "CPU (millisecond)", "Memory %", "Publisher", "Power (mW)", "Network (KB/s)"]):
            self.tree.heading(col, text=text)

        for col, w in zip(columns, [60, 200, 70, 90, 150, 90, 100]):
            self.tree.column(col, width=w, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Graph Setup
        self.cpu_data = []
        self.mem_data = []
        self.time_data = []

        self.fig = Figure(figsize=(6, 2.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Live CPU and Memory Usage")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Usage (%)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Track data
        self.last_net_io = {}
        self.last_time = time.time()

        self._prime_cpu_percent()

        # Thread for process update
        self._stop_event = threading.Event()
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

        # Thread for graph update
        self.graph_thread = threading.Thread(target=self._update_graph, daemon=True)
        self.graph_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _prime_cpu_percent(self):
        for proc in psutil.process_iter(['pid']):
            try:
                proc.cpu_percent(interval=None)
            except Exception:
                pass
        psutil.cpu_percent(interval=None)

    def _estimate_power_mw(self, proc_cpu_percent):
        try:
            estimated_watts = (proc_cpu_percent / 100.0) * self.CPU_TDP_WATTS
            estimated_mw = estimated_watts * 1000.0
            return f"{estimated_mw:.0f}"
        except Exception:
            return "—"

    def _get_publisher(self, proc):
        try:
            exe = proc.exe()
            return exe.split('\\')[-1].split('/')[-1]
        except Exception:
            return "Unknown"

    def _get_network_kbps(self, proc, now_time):
        try:
            io_counters = proc.io_counters()
            total_bytes = io_counters.read_bytes + io_counters.write_bytes
            pid = proc.pid
            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta_bytes = total_bytes - last_bytes
                delta_time = now_time - last_time if now_time > last_time else 1
                rate_kbps = (delta_bytes / delta_time) / 1024
            else:
                rate_kbps = 0.0

            self.last_net_io[pid] = (total_bytes, now_time)
            return f"{rate_kbps:.1f}"
        except Exception:
            return "—"

    def _update_loop(self):
        refresh_interval = 1.0
        while not self._stop_event.is_set():
            now = time.time()
            all_procs = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name'] or ""
                    cpu = proc.cpu_percent(interval=None)
                    mem = proc.memory_percent()
                    publisher = self._get_publisher(proc)
                    power_mw = self._estimate_power_mw(cpu)
                    network_kbps = self._get_network_kbps(proc, now)
                    all_procs.append((pid, name, cpu, mem, publisher, power_mw, network_kbps))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception:
                    continue

            self.root.after(0, self._refresh_tree, all_procs)
            time.sleep(refresh_interval)

    def _refresh_tree(self, proc_list):
        existing = {int(self.tree.set(child, "pid")): child
                    for child in self.tree.get_children() if self.tree.set(child, "pid")}
        seen_pids = set()

        for pid, name, cpu, mem, publisher, power_mw, network_kbps in proc_list:
            seen_pids.add(pid)
            values = (pid, name, f"{cpu:.1f}", f"{mem:.1f}", publisher, power_mw, network_kbps)
            if pid in existing:
                self.tree.item(existing[pid], values=values)
            else:
                self.tree.insert('', 'end', values=values)

        for pid, item in existing.items():
            if pid not in seen_pids:
                self.tree.delete(item)

    def _update_graph(self):
        while not self._stop_event.is_set():
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            self.cpu_data.append(cpu)
            self.mem_data.append(mem)
            self.time_data.append(len(self.time_data))

            if len(self.cpu_data) > 30:
                self.cpu_data.pop(0)
                self.mem_data.pop(0)
                self.time_data.pop(0)

            self.ax.clear()
            self.ax.plot(self.time_data, self.cpu_data, label="CPU %", color="blue")
            self.ax.plot(self.time_data, self.mem_data, label="Memory %", color="green")
            self.ax.legend(loc="upper right")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Usage (%)")
            self.ax.set_title("Live CPU and Memory Usage")
            self.canvas.draw()
            time.sleep(1)

    def _on_close(self):
        self._stop_event.set()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.geometry("1020x720")
    root.mainloop()