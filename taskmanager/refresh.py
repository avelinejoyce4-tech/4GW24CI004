
import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TaskManagerApp:
    def _init_(self, root):
        self.root = root
        self.root.title("Simple Task Manager With Memory Forensics")

        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000  # milliseconds for automatic refresh (30s)
        self.all_processes = []
        self.last_net_io = {}
        self.updating = False  # flag to prevent concurrent updates
        self.update_lock = threading.Lock()

        # --- Top Frame (Search + Limit + Buttons) ---
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10, fill=tk.X)

        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=8)
        self.search_entry = tk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=8)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=8)
        self.memory_limit_entry = tk.Entry(input_frame, width=20)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=5)

        # --- Treeview (Process Table) ---
        # Ensure columns order matches inserted values
        columns = ("pid", "name", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        for col, text, width in [
            ("pid", "PID", 70),
            ("name", "Name", 220),
            ("cpu", "CPU (%)", 80),
            ("memory", "Memory (MB)", 120),
            ("power", "Power (mW)", 100),
            ("network", "Network (KB/s)", 120),
        ]:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("high_memory", background="#ec8c8c")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Double-click to show process info
        self.tree.bind("<Double-1>", self.show_process_info)

        # --- Graph Frame ---
        graph_frame = tk.LabelFrame(root, text="Live System Usage", padx=5, pady=5)
        graph_frame.pack(fill=tk.BOTH, expand=False, pady=8, padx=8)

        self.fig = Figure(figsize=(6, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("CPU & Memory Usage Over Time")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel("Time (seconds)")
        self.ax.set_ylabel("Usage (%)")

        self.cpu_data, self.mem_data = [], []
        self.line_cpu, = self.ax.plot([], [], label="CPU", lw=2)
        self.line_mem, = self.ax.plot([], [], label="Memory", lw=2)
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Prime CPU percentages for smoother initial readings
        self._prime_cpu_percent()

        # Start by doing one refresh (in background)
        self.manual_refresh(start_periodic=True)

        # Start graph updates
        self.update_graph()

    # ---------- Helpers ----------
    def _prime_cpu_percent(self):
        # Call cpu_percent once for each process to initialize internal counters
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

    def _get_network_kbps(self, pid, proc, now_time):
        try:
            io = proc.io_counters()
            total_bytes = (io.read_bytes or 0) + (io.write_bytes or 0)
            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta_bytes = total_bytes - last_bytes
                delta_time = max(now_time - last_time, 0.001)
                rate_kbps = (delta_bytes / delta_time) / 1024.0
            else:
                rate_kbps = 0.0
            self.last_net_io[pid] = (total_bytes, now_time)
            return f"{rate_kbps:.1f}"
        except Exception:
            return "—"

    # ---------- Refresh / Update (thread-safe) ----------
    def manual_refresh(self, start_periodic=False):
        """
        Called by the Refresh button. Starts a background update if one isn't already running.
        If start_periodic=True, also starts the periodic scheduling.
        """
        # Provide immediate UI feedback and start background update
        if not self.updating:
            self.root.config(cursor="watch")
            threading.Thread(target=self._safe_update_processes, daemon=True).start()
        else:
            # If an update is already running, give quick feedback
            messagebox.showinfo("Updating", "An update is already in progress, please wait.")

        if start_periodic:
            # schedule the next automatic run after update_interval
            self.root.after(self.update_interval, self._periodic_refresh)

    def _periodic_refresh(self):
        # Called by after() — try to start an update if none is running
        if not self.updating:
            self.root.config(cursor="watch")
            threading.Thread(target=self._safe_update_processes, daemon=True).start()
        # Always schedule the next periodic attempt
        self.root.after(self.update_interval, self._periodic_refresh)

    def _safe_update_processes(self):
        """
        Runs update_processes_list while ensuring only one instance runs at a time.
        """
        with self.update_lock:
            if self.updating:
                return
            self.updating = True
            try:
                self.update_processes_list()
            finally:
                # Reset UI state on main thread
                self.root.after(0, lambda: self.root.config(cursor=""))
                self.updating = False

    def update_processes_list(self):
        """
        Collects process metrics in background thread and schedules display on the main thread.
        """
        processes = []
        now = time.time()

        # Use process_iter with limited attrs for speed
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pinfo = proc.info
                pid = pinfo.get('pid')
                name = (pinfo.get('name') or "Unknown")
                # cpu_percent with interval=None is non-blocking and returns the last computed
                cpu = proc.cpu_percent(interval=None)
                mem_info = pinfo.get('memory_info')
                mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                power = self._estimate_power_mw(cpu)
                network = self._get_network_kbps(pid, proc, now)

                processes.append({
                    "pid": pid,
                    "name": name,
                    "cpu": cpu,
                    "memory": mem_mb,
                    "power": power,
                    "network": network
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                # protect against unexpected errors per-process
                continue

        # Sort by CPU usage (descending) for display
        self.all_processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)
        # Schedule UI update on main thread
        self.root.after(0, lambda: self.display_processes(self.all_processes))

    def display_processes(self, processes):
        # Remove old items
        self.tree.delete(*self.tree.get_children())
        try:
            memory_limit = float(self.memory_limit_entry.get())
        except Exception:
            memory_limit = 0.0

        for p in processes:
            tag = "high_memory" if (memory_limit > 0 and p["memory"] > memory_limit) else ""
            # Insert values in same column order as tree definition
            self.tree.insert("", tk.END,
                             values=(p["pid"], p["name"], f"{p['cpu']:.1f}",
                                     f"{p['memory']:.2f}",
                                     p["power"], p["network"]),
                             tags=(tag,))

    # ---------- Sorting ----------
    def sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            # try numeric sort
            data.sort(reverse=descending, key=lambda t: float(t[0]))
        except Exception:
            data.sort(reverse=descending, key=lambda t: t[0].lower())
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(col, command=lambda c=col: self.sort_by(c, not descending))

    # ---------- Search ----------
    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = [p for p in self.all_processes if (query in (p["name"] or "").lower()) or query == str(p["pid"])]
        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        self.display_processes(filtered)

    # ---------- End Task ----------
    def end_selected_task(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to end.")
            return

        try:
            pid = int(self.tree.item(selected, "values")[0])
        except Exception:
            messagebox.showerror("Error", "Invalid selection.")
            return

        try:
            p = psutil.Process(pid)
            p.terminate()
            gone, alive = psutil.wait_procs([p], timeout=3)
            if alive:
                # try kill if terminate didn't work
                for proc in alive:
                    proc.kill()
            messagebox.showinfo("Process Ended", f"Process {pid} terminated.")
            # trigger a refresh now (background)
            self.manual_refresh()
        except psutil.NoSuchProcess:
            messagebox.showinfo("Process Ended", f"Process {pid} is no longer running.")
            self.manual_refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Could not terminate process: {e}")

    # ---------- Process Info Popup ----------
    def show_process_info(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        try:
            pid = int(self.tree.item(item, "values")[0])
            p = psutil.Process(pid)
            info = f"""
PID: {pid}
Name: {p.name()}
Status: {p.status()}
Threads: {p.num_threads()}
Memory: {p.memory_info().rss / (1024*1024):.2f} MB
CPU %: {p.cpu_percent(interval=0.1):.1f}
Executable: {p.exe() if p.exe() else 'N/A'}
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
        self.ax.set_xlim(0, max(50, len(self.cpu_data)))
        self.canvas.draw_idle()

        # update every second
        self.root.after(1000, self.update_graph)


# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.geometry("1100x700")
    root.mainloop()

