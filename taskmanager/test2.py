import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Task Manager With Memory Forensics")

        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000  # milli seconds
        self.all_processes = []
        self.last_net_io = {}

        # --- Top Frame (Search + Limit + Buttons) ---
        input_frame = tk.Frame(root)
        input_frame.pack(pady=20, fill=tk.X)

        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=10)
        self.search_entry = tk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=10)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=10)
        self.memory_limit_entry = tk.Entry(input_frame, width=20)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="Refresh", command=self.refresh_processes).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=5)

        # --- Treeview (Process Table) ---
        columns = ("pid", "name", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        for col, text, width in [
            ("name", "Name", 180),
            ("pid", "PID", 70),
            ("cpu", "CPU (milliseconds))", 80),
            ("memory", "Memory (MB)", 100),
            ("power", "Power (mW)", 100),
            ("network", "Network (KB/s)", 120),
        ]:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("high_memory", background="#ec8c8c")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Double-click to show process info
        self.tree.bind("<Double-1>", self.show_process_info)

        # --- Graph Frame ---
        graph_frame = tk.LabelFrame(root, text="Live System Usage", padx=5, pady=5)
        graph_frame.pack(fill=tk.BOTH, expand=False, pady=10)

        self.fig = Figure(figsize=(6, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("CPU & Memory Usage Over Time")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel("Time (miliseconds)")
        self.ax.set_ylabel("Usage (%)")

        self.cpu_data, self.mem_data = [], []
        self.line_cpu, = self.ax.plot([], [], label="CPU", lw=2)
        self.line_mem, = self.ax.plot([], [], label="Memory", lw=2)
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Prime CPU for smoother numbers
        self._prime_cpu_percent()
        self.refresh_processes()
        self.update_graph()

    # ---------- Process Handling ----------

    def _prime_cpu_percent(self):
        for proc in psutil.process_iter(['pid']):
            try:
                proc.cpu_percent(interval=None)
            except Exception:
                pass
        psutil.cpu_percent(interval=None)

    def _estimate_power_mw(self, proc_cpu_percent):
        try:
            return f"{(proc_cpu_percent / 100.0) * self.CPU_TDP_WATTS * 1000:.0f}"
        except Exception:
            return "—"

    def _get_network_kbps(self, proc, now_time):
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

    # ---------- UI Actions ----------

    def refresh_processes(self):
        threading.Thread(target=self.update_processes_list, daemon=True).start()
        self.root.after(self.update_interval, self.refresh_processes)

    def update_processes_list(self):
        processes = []
        now = time.time()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                pinfo = proc.info
                pid = pinfo['pid']
                name = pinfo['name'] or "Unknown"
                cpu = proc.cpu_percent(interval=None)
                mem_mb = (pinfo['memory_info'].rss / (1024 * 1024))
                power = self._estimate_power_mw(cpu)
                network = self._get_network_kbps(proc, now)

                processes.append({
                    "pid": pid,
                    "name": name,
                    "cpu": cpu,
                    "memory": mem_mb,
                    "power": power,
                    "network": network
                })
            except Exception:
                continue

        self.all_processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)
        self.root.after(0, lambda: self.display_processes(self.all_processes))

    def display_processes(self, processes):
        self.tree.delete(*self.tree.get_children())
        try:
            memory_limit = float(self.memory_limit_entry.get())
        except ValueError:
            memory_limit = 0

        for p in processes:
            tag = "high_memory" if memory_limit > 0 and p["memory"] > memory_limit else ""
            self.tree.insert("", tk.END,
                             values=(p["pid"], p["name"], f"{p['cpu']:.1f}",
                                     f"{p['memory']:.2f}",
                                     p["power"], p["network"]),
                             tags=(tag,))

    # ---------- Sorting ----------
    def sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            data.sort(reverse=descending, key=lambda t: float(t[0]))
        except ValueError:
            data.sort(reverse=descending)
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(col, command=lambda c=col: self.sort_by(c, not descending))

    # ---------- Search ----------
    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = [p for p in self.all_processes if query in p["name"].lower() or query == str(p["pid"])]
        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        self.display_processes(filtered)

    # ---------- End Task ----------
    def end_selected_task(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to end.")
            return

        pid = int(self.tree.item(selected, "values")[0])
        try:
            p = psutil.Process(pid)
            p.terminate()
            messagebox.showinfo("Process Ended", f"Process {pid} terminated successfully.")
            self.refresh_processes()
        except Exception as e:
            messagebox.showerror("Error", f"Could not terminate process: {e}")

    # ---------- Process Info Popup ----------
    def show_process_info(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        pid = int(self.tree.item(item, "values")[0])
        try:
            p = psutil.Process(pid)
            info = f"""
PID: {pid}
Name: {p.name()}
Status: {p.status()}
Threads: {p.num_threads()}
Memory: {p.memory_info().rss / (1024*1024):.2f} MB
CPU %: {p.cpu_percent(interval=0.1):.1f}
Executable: {p.exe()}
            """.strip()
            messagebox.showinfo("Process Info", info)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to fetch process details: {e}")

    # ---------- Graph Update ----------
    def update_graph(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        self.cpu_data.append(cpu)
        self.mem_data.append(mem)

        if len(self.cpu_data) > 50:
            self.cpu_data.pop(0)
            self.mem_data.pop(0)

        self.line_cpu.set_data(range(len(self.cpu_data)), self.cpu_data)
        self.line_mem.set_data(range(len(self.mem_data)), self.mem_data)
        self.ax.set_xlim(0, len(self.cpu_data))
        self.canvas.draw_idle()

        self.root.after(1000, self.update_graph)


# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.geometry("1100x700")
    root.mainloop()
