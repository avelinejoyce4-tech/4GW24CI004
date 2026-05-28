# 🔥 UPDATED VERSION WITH PID DROPDOWN (EXPANDABLE TREE ROWS)

import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from win10toast_click import ToastNotifier


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")

        # Constants
        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000
        self.refreshing = False
        self.all_processes = []
        self.last_net_io = {}
        self.notifier = ToastNotifier()
        self.alerted_names = set()
        self.notification_lock = threading.Lock()

        # --- UI ---
        input_frame = tk.Frame(root)
        input_frame.pack(pady=12, fill=tk.X)

        tk.Label(input_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry = tk.Entry(input_frame, width=10)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=4)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=4)

        # TreeView with dropdown support
        columns = ("pid", "name", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show="tree headings")

        self.tree.heading("pid", text="PIDs")
        self.tree.heading("name", text="Name")
        self.tree.heading("cpu", text="CPU (milliseconds)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("power", text="Power (mW)")
        self.tree.heading("network", text="Network (KB/s)")

        for col in columns:
            self.tree.column(col, width=150, anchor="center")
        self.tree.column("name", width=250)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree.tag_configure("high_memory", background="#f8d7da")

        self.tree.bind("<<TreeviewOpen>>", self.on_expand_pid)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Graph Section
        graph_frame = tk.LabelFrame(root, text="Live Usage Graph")
        graph_frame.pack(fill=tk.X, padx=10, pady=10)

        self.fig = Figure(figsize=(7, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("CPU & Memory Usage (%)")

        self.cpu_data, self.mem_data = [], []
        self.line_cpu, = self.ax.plot([], [], label="CPU")
        self.line_mem, = self.ax.plot([], [], label="MEM")
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, graph_frame)
        self.canvas.get_tk_widget().pack()

        # Initialize
        self._prime_cpu_percent()
        self.manual_refresh()
        self.update_graph()

    # ---------- Small Helpers ----------
    def _prime_cpu_percent(self):
        for p in psutil.process_iter():
            try: p.cpu_percent()
            except: pass
        psutil.cpu_percent()

    def _estimate_power(self, cpu):
        return (cpu / 100) * self.CPU_TDP_WATTS * 1000

    def _get_network(self, pid, proc, now):
        try:
            io = proc.io_counters()
            total = io.read_bytes + io.write_bytes
            if pid in self.last_net_io:
                last_total, last_t = self.last_net_io[pid]
                dt = now - last_t if now > last_t else 0.1
                kbps = (total - last_total) / dt / 1024
            else:
                kbps = 0.0
            self.last_net_io[pid] = (total, now)
            return max(kbps, 0)
        except:
            return 0

    # ---------- Update Processes ----------
    def manual_refresh(self):
        if not self.refreshing:
            threading.Thread(target=self.update_processes_list, daemon=True).start()

    def update_processes_list(self):
        self.refreshing = True
        processes = {}
        now = time.time()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                info = proc.info
                pid = info["pid"]
                name = info.get("name", "unknown").strip()
                keyname = name.lower()

                if keyname.endswith(".exe"):
                    key = keyname
                else:
                    key = f"{keyname}_{pid}"

                cpu = proc.cpu_percent()
                mem = info["memory_info"].rss / (1024 * 1024)
                net = self._get_network(pid, proc, now)
                power = self._estimate_power(cpu)

                if key not in processes:
                    processes[key] = {
                        "name": name,
                        "pids": [],
                        "cpu": 0, "memory": 0, "power": 0, "network": 0,
                        "per_pid": {}
                    }

                processes[key]["pids"].append(pid)
                processes[key]["cpu"] += cpu
                processes[key]["memory"] += mem
                processes[key]["power"] += power
                processes[key]["network"] += net
                processes[key]["per_pid"][pid] = {
                    "cpu": cpu,
                    "memory": mem,
                    "power": power,
                    "network": net
                }

            except:
                continue

        self.all_processes = list(processes.values())
        self.root.after(0, lambda: self.display_processes(self.all_processes))
        self.root.after(self.update_interval, self.manual_refresh)
        self.refreshing = False

    # ---------- Display Processes in Tree ----------
    def display_processes(self, processes):
        self.tree.delete(*self.tree.get_children())

        try:
            limit = float(self.memory_limit_entry.get())
        except:
            limit = 0

        for p in processes:
            name = p["name"]
            pids = p["pids"]

            pid_display = f"{len(pids)} PIDs"
            tag = "high_memory" if p["memory"] > limit > 0 else ""

            parent = self.tree.insert(
                "", tk.END,
                text="",  # required for tree mode
                values=(pid_display, name, f"{p['cpu']:.1f}", f"{p['memory']:.1f}",
                        f"{p['power']:.0f}", f"{p['network']:.1f}"),
                tags=(tag,),
                open=False
            )

            # Hidden children (shown when expanded)
            for pid in pids:
                d = p["per_pid"][pid]
                self.tree.insert(
                    parent, tk.END,
                    text=f"PID {pid}",
                    values=(
                        pid, f"{name} (PID)", f"{d['cpu']:.1f}",
                        f"{d['memory']:.1f}", f"{d['power']:.0f}", f"{d['network']:.1f}"
                    )
                )

    # ---------- Expand / Collapse ----------
    def on_expand_pid(self, event):
        """Triggered on expanding rows (no code needed here now)."""
        pass

    # ---------- Search ----------
    def search_process(self):
        query = self.search_entry.get().lower().strip()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = []
        for p in self.all_processes:
            if query in p["name"].lower():
                filtered.append(p)
                continue
            if any(query in str(pid) for pid in p["pids"]):
                filtered.append(p)

        if filtered:
            self.display_processes(filtered)
        else:
            messagebox.showinfo("Not Found", f"No match for: {query}")

    # ---------- End Task ----------
    def end_selected_task(self):
        item = self.tree.focus()
        if not item:
            messagebox.showwarning("Select Process", "Please select a process")
            return

        values = self.tree.item(item, "values")
        if "PIDs" in values[0]:
            # Parent row
            parent = item
        else:
            # Child row
            parent = self.tree.parent(item)

        pids = []
        for child in self.tree.get_children(parent):
            pid = self.tree.item(child, "values")[0]
            if str(pid).isdigit():
                pids.append(int(pid))

        if messagebox.askyesno("Confirm", f"Terminate {len(pids)} processes?"):
            for pid in pids:
                try:
                    psutil.Process(pid).terminate()
                except:
                    pass

            messagebox.showinfo("Done", "Processes terminated.")
            self.manual_refresh()

    # ---------- Double-click Info ----------
    def on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        vals = self.tree.item(item, "values")
        messagebox.showinfo("Info", str(vals))

    # ---------- Live Graph ----------
    def update_graph(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        self.cpu_data.append(cpu)
        self.mem_data.append(mem)
        if len(self.cpu_data) > 60:
            self.cpu_data.pop(0)
            self.mem_data.pop(0)

        self.line_cpu.set_data(range(len(self.cpu_data)), self.cpu_data)
        self.line_mem.set_data(range(len(self.mem_data)), self.mem_data)
        self.ax.set_xlim(0, len(self.cpu_data))
        self.canvas.draw()
        self.root.after(1000, self.update_graph)


# ---------- Run App ----------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1300x750")
    TaskManagerApp(root)
    root.mainloop()
