"""
Task Manager with:
- Grouping of .exe processes by filename (sums CPU, memory, power, network)
- Desktop notifications when memory usage of a grouped entry exceeds configured limit
- Clicking the notification focuses the Tk window and selects the offending row
- End Task terminates all PIDs in a grouped entry
"""

import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Notification library that supports click callbacks on Windows
from win10toast_click import ToastNotifier


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager — Grouped EXE + Notifications")

        # Constants / State
        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000  # milliseconds for full refresh
        self.refreshing = False
        self.all_processes = []  # list of grouped processes
        self.last_net_io = {}  # per-pid last io counters (bytes, timestamp)
        self.notifier = ToastNotifier()
        self.alerted_names = set()  # to avoid repeating notifications
        self.notification_lock = threading.Lock()

        # --- Top Frame (Search + Limit + Buttons) ---
        input_frame = tk.Frame(root)
        input_frame.pack(pady=12, fill=tk.X)

        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=8)
        self.search_entry = tk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=6)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=8)
        self.memory_limit_entry = tk.Entry(input_frame, width=12)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=6)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=4)

        # --- Treeview (Group display) ---
        columns = ("pid", "name", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        headings = [
            ("pid", "PIDs"),
            ("name", "Name"),
            ("cpu", "CPU (%)"),
            ("memory", "Memory (MB)"),
            ("power", "Power (mW)"),
            ("network", "Network (KB/s)"),
        ]
        for col, text in headings:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=120, anchor="center")

        # make Name column wider
        self.tree.column("name", width=240)

        self.tree.tag_configure("high_memory", background="#f8d7da")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Double-click to show process info (aggregated)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # --- Graph Frame ---
        graph_frame = tk.LabelFrame(root, text="Live System Usage", padx=5, pady=5)
        graph_frame.pack(fill=tk.BOTH, expand=False, pady=10, padx=8)

        self.fig = Figure(figsize=(8, 2.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("CPU & Memory Usage Over Time")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("Usage (%)")

        self.cpu_data, self.mem_data = [], []
        self.line_cpu, = self.ax.plot([], [], label="CPU", lw=2)
        self.line_mem, = self.ax.plot([], [], label="Memory", lw=2)
        self.ax.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # initialize CPU percent priming
        self._prime_cpu_percent()

        # Kick off periodic work
        self.manual_refresh()  # load once immediately
        self.update_graph()

    # ------------------- Helpers -------------------

    def _prime_cpu_percent(self):
        # call cpu_percent once for each process so subsequent calls are meaningful
        for p in psutil.process_iter(['pid']):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass
        psutil.cpu_percent(interval=None)

    def _estimate_power_mw(self, proc_cpu_percent):
        """Rough CPU-based power estimate in mW using CPU_TDP_WATTS."""
        try:
            return (proc_cpu_percent / 100.0) * self.CPU_TDP_WATTS * 1000.0
        except Exception:
            return 0.0

    def _get_network_kbps_for_pid(self, pid, proc, now_time):
        """Return KB/s for this pid by comparing io counters to last saved value."""
        try:
            io = proc.io_counters()
            total_bytes = (getattr(io, "read_bytes", 0) or 0) + (getattr(io, "write_bytes", 0) or 0)
            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta = total_bytes - last_bytes
                dt = max(now_time - last_time, 0.001)
                kbps = (delta / dt) / 1024.0
            else:
                kbps = 0.0
            self.last_net_io[pid] = (total_bytes, now_time)
            return max(kbps, 0.0)
        except Exception:
            # if any error (access denied), just return 0.0
            return 0.0

    # ------------------- Process Gathering & Grouping -------------------

    def manual_refresh(self):
        """Trigger an immediate update (in background)"""
        if not self.refreshing:
            threading.Thread(target=self.update_processes_list, daemon=True).start()

    def update_processes_list(self):
        """Collect processes, group .exe by filename, sum CPU/memory/power/network."""
        self.refreshing = True
        processes = {}  # key -> aggregated dict
        now = time.time()

        # iterate processes and aggregate
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                info = proc.info
                pid = info.get('pid')
                raw_name = (info.get('name') or "unknown").strip()
                name_lower = raw_name.lower()

                # Grouping rule: if endswith .exe -> group by name_lower,
                # otherwise treat each PID separately to avoid accidental grouping
                if name_lower.endswith(".exe"):
                    key = name_lower  # group by exe filename
                    display_name = raw_name  # preserve original case for display when possible
                else:
                    # Non-exe: keep unique by pid so they show separately
                    key = f"{name_lower}_{pid}"
                    display_name = raw_name

                # CPU percent (non-blocking because we've primed)
                cpu = proc.cpu_percent(interval=None)
                memory_mb = 0.0
                meminfo = info.get('memory_info')
                if meminfo:
                    memory_mb = (meminfo.rss or 0) / (1024.0 * 1024.0)

                network_kbps = self._get_network_kbps_for_pid(pid, proc, now)
                power_mw = self._estimate_power_mw(cpu)

                if key not in processes:
                    processes[key] = {
                        "key": key,
                        "display_name": display_name,
                        "pids": [],
                        "cpu": 0.0,
                        "memory": 0.0,
                        "power": 0.0,
                        "network": 0.0
                    }

                # aggregate
                agg = processes[key]
                agg["pids"].append(pid)
                agg["cpu"] += float(cpu or 0.0)
                agg["memory"] += float(memory_mb or 0.0)
                agg["power"] += float(power_mw or 0.0)
                agg["network"] += float(network_kbps or 0.0)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        # Convert to list sorted by CPU descending
        aggregated_list = list(processes.values())
        aggregated_list.sort(key=lambda x: x["cpu"], reverse=True)
        self.all_processes = aggregated_list

        # Update UI on main thread
        self.root.after(0, lambda: self.display_processes(self.all_processes))
        # schedule next automatic refresh
        self.root.after(self.update_interval, self.manual_refresh)
        self.refreshing = False

    # ------------------- Display & Notifications -------------------

    def display_processes(self, processes):
        """Populate the treeview with aggregated process rows and send notifications if needed."""
        self.tree.delete(*self.tree.get_children())

        # memory threshold from UI
        try:
            memory_limit = float(self.memory_limit_entry.get())
            if memory_limit < 0:
                memory_limit = 0.0
        except Exception:
            memory_limit = 0.0

        # We will clear alerted_names entries that no longer exceed threshold,
        # so that new alerts may re-trigger later.
        current_high_names = set()

        for p in processes:
            name = p["display_name"]
            pid_list = p["pids"]
            pid_str = ",".join(str(x) for x in pid_list)
            cpu = p["cpu"]
            mem = p["memory"]
            power = p["power"]
            net = p["network"]

            tag = ""
            if memory_limit > 0 and mem > memory_limit:
                tag = "high_memory"
                current_high_names.add(name)

                # send notification once per name until it goes below limit
                with self.notification_lock:
                    if name not in self.alerted_names:
                        self.alerted_names.add(name)
                        # show toast in background; callback invoked on click
                        try:
                            # callback function will receive no args; wrap with lambda to use name
                            self.notifier.show_toast(
                                "High Memory Usage",
                                f"{name} is using {mem:.2f} MB (limit {memory_limit:.0f} MB). Click to focus.",
                                icon_path=None,
                                duration=8,
                                threaded=True,
                                callback_on_click=lambda n=name: self.on_notification_click(n)
                            )
                        except Exception:
                            # fall back to non-clickable toast if library fails
                            try:
                                self.notifier.show_toast(
                                    "High Memory Usage",
                                    f"{name} is using {mem:.2f} MB (limit {memory_limit:.0f} MB).",
                                    duration=8,
                                    threaded=True
                                )
                            except Exception:
                                pass

            # Insert into tree (match columns: pid,name,cpu,memory,power,network)
            self.tree.insert("", tk.END,
                             values=(pid_str, name, f"{cpu:.1f}", f"{mem:.2f}", f"{power:.0f}", f"{net:.1f}"),
                             tags=(tag,))

        # Clean alerts for those that are no longer high
        with self.notification_lock:
            to_remove = [n for n in self.alerted_names if n not in current_high_names]
            for n in to_remove:
                self.alerted_names.remove(n)

    def on_notification_click(self, process_name):
        """
        Called when notification is clicked. Focus app window and select the first row
        that matches the process_name (display_name).
        This callback can be called from a separate thread by win10toast-click, so
        use root.after to schedule GUI operations on the main thread.
        """
        def _focus_and_select():
            try:
                # bring window to front and focus
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()

                # find first tree item with name equal to process_name
                for child in self.tree.get_children():
                    vals = self.tree.item(child, "values")
                    # columns: pid, name, cpu, memory, power, network
                    if len(vals) >= 2 and str(vals[1]) == process_name:
                        # select & focus this item and ensure it's visible
                        self.tree.selection_set(child)
                        self.tree.focus(child)
                        self.tree.see(child)
                        break
            except Exception:
                pass

        # schedule on main thread
        try:
            self.root.after(0, _focus_and_select)
        except Exception:
            # if scheduling fails, try simple focus
            pass

    # ------------------- Sorting & Search -------------------

    def sort_by(self, col, descending):
        """Sort tree contents by column (numeric if possible)."""
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            data.sort(key=lambda t: float(t[0]), reverse=descending)
        except Exception:
            data.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0], reverse=descending)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

        # toggle for next click
        self.tree.heading(col, command=lambda c=col: self.sort_by(c, not descending))

    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            # show all
            self.display_processes(self.all_processes)
            return

        filtered = []
        for p in self.all_processes:
            name = p["display_name"]
            pids = p["pids"]
            if query in name.lower() or query in ",".join(str(x) for x in pids):
                filtered.append(p)

        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        else:
            self.display_processes(filtered)

    # ------------------- End Task -------------------

    def end_selected_task(self):
        """Terminate all PIDs associated with the selected row."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process/group to end.")
            return

        pid_cell = self.tree.item(selected, "values")[0]
        if not pid_cell:
            messagebox.showwarning("Warning", "No PIDs available for the selected row.")
            return

        try:
            pid_list = [int(x.strip()) for x in str(pid_cell).split(",") if x.strip().isdigit()]
        except Exception:
            pid_list = []

        if not pid_list:
            messagebox.showwarning("Warning", "Could not parse PIDs for the selected row.")
            return

        # confirm
        if not messagebox.askyesno("Confirm Terminate", f"Terminate {len(pid_list)} process(es)?"):
            return

        killed = 0
        for pid in pid_list:
            try:
                p = psutil.Process(pid)
                p.terminate()
                killed += 1
            except Exception:
                try:
                    # try kill if terminate fails
                    psutil.Process(pid).kill()
                    killed += 1
                except Exception:
                    pass

        messagebox.showinfo("Result", f"Attempted to terminate {killed} process(es).")
        # Refresh after termination
        self.manual_refresh()

    # ------------------- Tree double-click (show aggregated info) -------------------

    def on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return

        vals = self.tree.item(row, "values")
        if not vals or len(vals) < 6:
            return

        pid_cell, name, cpu, mem, power, net = vals
        # Build info text
        info_lines = [
            f"Name: {name}",
            f"PIDs: {pid_cell}",
            f"CPU (sum %): {cpu}",
            f"Memory (sum MB): {mem}",
            f"Power (approx mW): {power}",
            f"Network (KB/s sum): {net}",
        ]
        # Additionally, list details about each PID if available
        pid_list = []
        try:
            pid_list = [int(x.strip()) for x in str(pid_cell).split(",") if x.strip().isdigit()]
        except Exception:
            pid_list = []

        for pid in pid_list:
            try:
                p = psutil.Process(pid)
                try:
                    exe = p.exe()
                except Exception:
                    exe = "N/A"
                try:
                    status = p.status()
                except Exception:
                    status = "N/A"
                try:
                    threads = p.num_threads()
                except Exception:
                    threads = "N/A"
                try:
                    cpu_pct = p.cpu_percent(interval=0.1)
                except Exception:
                    cpu_pct = "N/A"
                try:
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                except Exception:
                    mem_mb = "N/A"

                info_lines.append(
                    f"\nPID {pid}: exe={exe}, status={status}, threads={threads}, cpu={cpu_pct}, mem={mem_mb}"
                )
            except psutil.NoSuchProcess:
                info_lines.append(f"\nPID {pid}: (no longer exists)")
            except Exception:
                info_lines.append(f"\nPID {pid}: (details unavailable)")

        messagebox.showinfo("Process Group Info", "\n".join(info_lines))

    # ------------------- Live Graph -------------------

    def update_graph(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent

            self.cpu_data.append(cpu)
            self.mem_data.append(mem)

            if len(self.cpu_data) > 60:
                self.cpu_data.pop(0)
                self.mem_data.pop(0)

            self.line_cpu.set_data(range(len(self.cpu_data)), self.cpu_data)
            self.line_mem.set_data(range(len(self.mem_data)), self.mem_data)
            self.ax.set_xlim(0, max(10, len(self.cpu_data)))
            self.canvas.draw_idle()
        except Exception:
            pass
        finally:
            # call again after 1 second
            self.root.after(1000, self.update_graph)


# ------------------- Run Application -------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.geometry("1200x720")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
