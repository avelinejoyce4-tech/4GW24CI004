"""
Combined Task Manager:
- Groups .exe processes by filename (aggregates CPU, memory, power, network)
- Expandable parent rows show per-PID children
- Desktop toast notifications (win10toast_click) when a group's memory sum exceeds configured limit
- Clicking a toast brings the Tk window forward and selects the offending group
- End Task terminates all PIDs in a group
"""

import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Make sure you installed: pip install win10toast-click
from win10toast_click import ToastNotifier


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager — Grouped EXE + Notifications")

        # --- State / constants ---
        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000  # ms between automatic refreshes
        self.refreshing = False
        self.all_processes = []  # aggregated list
        self.last_net_io = {}  # pid -> (bytes, timestamp)
        self.notifier = ToastNotifier()
        self.alerted_names = set()  # names that have already had an active alert
        self.notification_lock = threading.Lock()

        # --- Top input frame ---
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10, fill=tk.X)

        tk.Label(input_frame, text="Search:").pack(side=tk.LEFT, padx=6)
        self.search_entry = tk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=6)
        self.memory_limit_entry = tk.Entry(input_frame, width=10)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=4)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=4)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=4)

        # --- Treeview ---
        # Use the tree column (#0) for the name so Treeview shows native expand/collapse arrows.
        columns = ("pids", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show="tree headings")
        # heading for tree (name) appears via column #0 (text)
        self.tree.heading("#0", text="Name")
        self.tree.heading("pids", text="PIDs")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("power", text="Power (mW)")
        self.tree.heading("network", text="Network (KB/s)")

        # column sizes
        self.tree.column("#0", width=300, anchor="w")
        self.tree.column("pids", width=120, anchor="center")
        self.tree.column("cpu", width=100, anchor="center")
        self.tree.column("memory", width=120, anchor="center")
        self.tree.column("power", width=120, anchor="center")
        self.tree.column("network", width=120, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree.tag_configure("high_memory", background="#f8d7da")

        # bind double-click for info
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # --- Graph Frame ---
        graph_frame = tk.LabelFrame(root, text="Live System Usage", padx=5, pady=5)
        graph_frame.pack(fill=tk.BOTH, expand=False, padx=8, pady=8)

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

        # prime CPU percentages
        self._prime_cpu_percent()

        # initial load
        self.manual_refresh()
        self.update_graph()

    # ---------------- helpers ----------------
    def _prime_cpu_percent(self):
        # call cpu_percent once for each process so subsequent calls are meaningful
        for p in psutil.process_iter(['pid']):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass
        psutil.cpu_percent(interval=None)

    def _estimate_power_mw(self, proc_cpu_percent):
        try:
            return (proc_cpu_percent / 100.0) * self.CPU_TDP_WATTS * 1000.0
        except Exception:
            return 0.0

    def _get_network_kbps_for_pid(self, pid, proc, now_time):
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
            return 0.0

    # ---------------- process gathering & grouping ----------------
    def manual_refresh(self):
        """Trigger an immediate update (in background)"""
        if not self.refreshing:
            threading.Thread(target=self.update_processes_list, daemon=True).start()

    def update_processes_list(self):
        self.refreshing = True
        processes = {}  # key -> aggregated dict
        now = time.time()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                info = proc.info
                pid = info.get('pid')
                raw_name = (info.get('name') or "unknown").strip()
                name_lower = raw_name.lower()

                # Group ".exe" by filename; non-exe keep per-pid
                if name_lower.endswith(".exe"):
                    key = name_lower
                    display_name = raw_name
                else:
                    key = f"{name_lower}_{pid}"
                    display_name = raw_name

                cpu = proc.cpu_percent(interval=None)
                mem_mb = 0.0
                meminfo = info.get('memory_info')
                if meminfo:
                    mem_mb = (meminfo.rss or 0) / (1024.0 * 1024.0)

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
                        "network": 0.0,
                        "per_pid": {}
                    }

                agg = processes[key]
                agg["pids"].append(pid)
                agg["cpu"] += float(cpu or 0.0)
                agg["memory"] += float(mem_mb or 0.0)
                agg["power"] += float(power_mw or 0.0)
                agg["network"] += float(network_kbps or 0.0)
                agg["per_pid"][pid] = {
                    "cpu": float(cpu or 0.0),
                    "memory": float(mem_mb or 0.0),
                    "power": float(power_mw or 0.0),
                    "network": float(network_kbps or 0.0)
                }

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        aggregated_list = list(processes.values())
        aggregated_list.sort(key=lambda x: x["cpu"], reverse=True)
        self.all_processes = aggregated_list

        # Update UI on main thread
        self.root.after(0, lambda: self.display_processes(self.all_processes))
        # schedule next automatic refresh
        self.root.after(self.update_interval, self.manual_refresh)
        self.refreshing = False

    # ---------------- display & notifications ----------------
    def display_processes(self, processes):
        self.tree.delete(*self.tree.get_children())

        # memory threshold from UI
        try:
            memory_limit = float(self.memory_limit_entry.get())
            if memory_limit < 0:
                memory_limit = 0.0
        except Exception:
            memory_limit = 0.0

        # record current high-memory names to clear alerts that are no longer high
        current_high_names = set()

        for p in processes:
            name = p["display_name"]
            pid_list = p["pids"]
            pid_display = f"{len(pid_list)} PIDs"
            cpu_sum = p["cpu"]
            mem_sum = p["memory"]
            power_sum = p["power"]
            net_sum = p["network"]

            tag = ""
            if memory_limit > 0 and mem_sum > memory_limit:
                tag = "high_memory"
                current_high_names.add(name)

                # send notification once per name until it goes below limit
                with self.notification_lock:
                    if name not in self.alerted_names:
                        self.alerted_names.add(name)
                        # show toast in background; provide callback_on_click to select & focus
                        try:
                            # Note: callback_on_click receives no args; use lambda to capture name
                            self.notifier.show_toast(
                                "High Memory Usage",
                                f"{name} is using {mem_sum:.2f} MB (limit {memory_limit:.0f} MB). Click to focus.",
                                icon_path=None,
                                duration=8,
                                threaded=True,
                                callback_on_click=lambda n=name: self.on_notification_click(n)
                            )
                        except Exception:
                            # fallback: try plain toast without click
                            try:
                                self.notifier.show_toast(
                                    "High Memory Usage",
                                    f"{name} is using {mem_sum:.2f} MB (limit {memory_limit:.0f} MB).",
                                    duration=8,
                                    threaded=True
                                )
                            except Exception:
                                pass

            # Insert parent row using the tree column (#0) as the "Name" so expand arrow appears.
            parent = self.tree.insert(
                "", tk.END,
                text=name,  # displayed in the tree column; this ensures native expand/collapse arrow
                values=(pid_display, f"{cpu_sum:.1f}", f"{mem_sum:.2f}", f"{power_sum:.0f}", f"{net_sum:.1f}"),
                tags=(tag,),
                open=False
            )

            # Insert child rows for each PID (hidden until parent expanded)
            for pid in pid_list:
                d = p["per_pid"].get(pid, {})
                cpu_p = d.get("cpu", 0.0)
                mem_p = d.get("memory", 0.0)
                power_p = d.get("power", 0.0)
                net_p = d.get("network", 0.0)

                self.tree.insert(
                    parent, tk.END,
                    text=f"PID {pid}",
                    values=(str(pid), f"{cpu_p:.1f}", f"{mem_p:.2f}", f"{power_p:.0f}", f"{net_p:.1f}")
                )

        # Remove names from alerted_names that are no longer above the limit
        with self.notification_lock:
            to_remove = [n for n in self.alerted_names if n not in current_high_names]
            for n in to_remove:
                self.alerted_names.remove(n)

    def on_notification_click(self, process_name):
        """
        Called when a notification is clicked. Focus app window and select the first parent
        row whose text (name) matches process_name. This is scheduled on the GUI thread.
        """
        def _focus_and_select():
            try:
                # bring window to front and focus
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()

                # find first top-level item where text == process_name (case-insensitive)
                for child in self.tree.get_children():
                    # text (displayed in #0) is retrieved by item()['text']
                    if str(self.tree.item(child, "text")).lower() == str(process_name).lower():
                        self.tree.selection_set(child)
                        self.tree.focus(child)
                        self.tree.see(child)
                        # ensure it's expanded so the user sees PIDs
                        self.tree.item(child, open=True)
                        break
            except Exception:
                pass

        try:
            self.root.after(0, _focus_and_select)
        except Exception:
            pass

    # ---------------- sorting & search ----------------
    def sort_by(self, col, descending):
        """Sort tree contents by column (numeric if possible)."""
        data = []
        for child in self.tree.get_children(''):
            val = self.tree.set(child, col)
            data.append((val, child))
        try:
            data.sort(key=lambda t: float(t[0]), reverse=descending)
        except Exception:
            data.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0], reverse=descending)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

        # toggle for next click
        # Map headings back to a new command
        self.tree.heading(col, command=lambda c=col: self.sort_by(c, not descending))

    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = []
        for p in self.all_processes:
            name = p["display_name"]
            pids = p["pids"]
            if query in name.lower() or any(query in str(x) for x in pids):
                filtered.append(p)

        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        else:
            self.display_processes(filtered)

    # ---------------- end task ----------------
    def end_selected_task(self):
        """Terminate all PIDs associated with the selected row (parent or child)."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process/group to end.")
            return

        # If the focused item is a parent, its children contain PIDs.
        # If it's a child, get its parent.
        parent = selected
        if self.tree.parent(selected):  # has a parent -> it's a child row
            parent = self.tree.parent(selected)

        # Gather PIDs from child rows (children are per-PID rows)
        pid_list = []
        for child in self.tree.get_children(parent):
            val_pid = self.tree.set(child, "pids")  # first column in values is pids
            # some child rows set PID as the first value in values
            if not val_pid:
                # fallback to text like "PID 1234"
                text = self.tree.item(child, "text")
                if isinstance(text, str) and text.lower().startswith("pid"):
                    try:
                        pid_num = int(text.split()[1])
                        pid_list.append(pid_num)
                    except Exception:
                        pass
            else:
                # try parse pid from the "pids" cell
                try:
                    # parent may show "N PIDs", children may show "1234"
                    if "," in val_pid:
                        # support comma list
                        for part in val_pid.split(","):
                            part = part.strip()
                            if part.isdigit():
                                pid_list.append(int(part))
                    elif val_pid.isdigit():
                        pid_list.append(int(val_pid))
                except Exception:
                    pass

        # fallback: if pid_list empty, try parse parent pids cell (format "N PIDs" or comma-list)
        if not pid_list:
            parent_vals = self.tree.item(parent, "values")
            if parent_vals:
                # parent_vals[0] may be like "3 PIDs" — not helpful for actual PID numbers,
                # so we only try if a comma-separated list exists there.
                maybe = parent_vals[0]
                if isinstance(maybe, str) and "," in maybe:
                    for part in maybe.split(","):
                        try:
                            pid_list.append(int(part.strip()))
                        except Exception:
                            pass

        if not pid_list:
            messagebox.showwarning("Warning", "Could not determine PIDs to terminate.")
            return

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
                    psutil.Process(pid).kill()
                    killed += 1
                except Exception:
                    pass

        messagebox.showinfo("Result", f"Attempted to terminate {killed} process(es).")
        # Refresh list after termination
        self.manual_refresh()

    # ---------------- tree double-click (info) ----------------
    def on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return

        vals = self.tree.item(row, "values")
        text = self.tree.item(row, "text")
        # If row is a parent, show aggregated info + list of PID details
        if not self.tree.parent(row):
            # parent
            name = text
            pid_cell = vals[0] if vals and len(vals) > 0 else ""
            cpu = vals[1] if len(vals) > 1 else ""
            mem = vals[2] if len(vals) > 2 else ""
            power = vals[3] if len(vals) > 3 else ""
            net = vals[4] if len(vals) > 4 else ""

            info_lines = [
                f"Name: {name}",
                f"PIDs: {pid_cell}",
                f"CPU (sum %): {cpu}",
                f"Memory (sum MB): {mem}",
                f"Power (approx mW): {power}",
                f"Network (KB/s sum): {net}",
            ]

            # list details about each child PID row
            for child in self.tree.get_children(row):
                cvals = self.tree.item(child, "values")
                ctext = self.tree.item(child, "text")
                info_lines.append(f"\n{ctext}: {cvals}")

            messagebox.showinfo("Process Group Info", "\n".join(info_lines))
        else:
            # child row: show pid details
            pid_text = text  # "PID 1234"
            info_lines = [f"{pid_text}"]
            info_lines.append(f"Values: {vals}")
            # attempt to fetch live details from psutil
            try:
                pid_num = int(pid_text.split()[1])
                try:
                    p = psutil.Process(pid_num)
                    exe = "N/A"
                    status = "N/A"
                    threads = "N/A"
                    cpu_pct = "N/A"
                    mem_mb = "N/A"
                    try:
                        exe = p.exe()
                    except Exception:
                        pass
                    try:
                        status = p.status()
                    except Exception:
                        pass
                    try:
                        threads = p.num_threads()
                    except Exception:
                        pass
                    try:
                        cpu_pct = p.cpu_percent(interval=0.1)
                    except Exception:
                        pass
                    try:
                        mem_mb = p.memory_info().rss / (1024 * 1024)
                    except Exception:
                        pass

                    info_lines.append(f"exe={exe}, status={status}, threads={threads}, cpu={cpu_pct}, mem={mem_mb}")
                except psutil.NoSuchProcess:
                    info_lines.append("(process no longer exists)")
            except Exception:
                pass

            messagebox.showinfo("PID Info", "\n".join(info_lines))

    # ---------------- live graph ----------------
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
            self.root.after(1000, self.update_graph)


# ---------------- run ----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x720")
    app = TaskManagerApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
