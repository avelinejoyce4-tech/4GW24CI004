"""
Combined Task Manager:
- Groups .exe processes by filename (aggregates CPU, memory, power, network)
- Expandable parent rows show per-PID children
- Desktop toast notifications (win10toast_click) when a group's memory sum exceeds configured limit
- Clicking a toast brings the Tk window forward and selects the offending group
- End Task terminates all PIDs in a group
- STOP button suspends all PIDs in a group for:
        - 2 Hours
        - 7 Days
        - 1 Month
        - 1 Year
        - Custom (minutes)
- Automatic resume of all processes after the duration
- Suspended state persists to disk so the app can resume on restart
"""

import json
import os
import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from win10toast_click import ToastNotifier

SUSPEND_STATE_FILE = "suspended_state.json"
class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Task Manager")

        # --- State / constants ---
        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 30000  # ms
        self.refreshing = False
        self.all_processes = []  # aggregated list
        self.last_net_io = {}  # pid -> (bytes, timestamp)
        self.notifier = ToastNotifier()
        self.alerted_names = set()
        self.notification_lock = threading.Lock()

        # Keep track of active suspended sessions in memory
        # (also persisted to file)
        self.active_suspended = None  # dict: {"pids": [...], "resume_time": epoch}

        # ---------------- UI ----------------
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

        # STOP button + duration combobox + custom minutes
        tk.Label(input_frame, text="Stop Duration:").pack(side=tk.LEFT, padx=6)

        self.stop_duration = ttk.Combobox(
            input_frame,
            values=["2 Hours", "7 Days", "1 Month", "1 Year", "Custom (Minutes)"],
            width=18,
            state="readonly"
        )
        self.stop_duration.current(0)
        self.stop_duration.pack(side=tk.LEFT, padx=4)

        self.custom_minutes = tk.Entry(input_frame, width=6)
        self.custom_minutes.insert(0, "0")
        self.custom_minutes.pack(side=tk.LEFT, padx=4)

        tk.Button(input_frame, text="Stop", command=self.stop_selected_task).pack(side=tk.LEFT, padx=4)

        # Treeview (use tree column #0 for name so arrow appears)
        columns = ("pids", "cpu", "memory", "power", "network")
        self.tree = ttk.Treeview(root, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("pids", text="PIDs")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("power", text="Power (mW)")
        self.tree.heading("network", text="Network (KB/s)")

        self.tree.column("#0", width=320, anchor="w")
        self.tree.column("pids", width=120, anchor="center")
        self.tree.column("cpu", width=100, anchor="center")
        self.tree.column("memory", width=120, anchor="center")
        self.tree.column("power", width=120, anchor="center")
        self.tree.column("network", width=120, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree.tag_configure("high_memory", background="#f8d7da")

        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Live graph
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

        # Prime and start
        self._prime_cpu_percent()
        self.manual_refresh()
        self.update_graph()

        # After UI is initialized, check for suspended state file (persisted)
        # schedule small delay so window shows first
        self.root.after(500, self.check_persisted_suspend_state)

    # ---------------- Persistence helpers ----------------
    def save_suspend_state(self, pid_list, resume_time):
        """Save suspended session to disk so it persists across app restarts."""
        try:
            data = {
                "pids": [int(x) for x in pid_list],
                "resume_time": float(resume_time),
                "saved_at": time.time()
            }
            with open(SUSPEND_STATE_FILE, "w") as f:
                json.dump(data, f)
            # keep in-memory copy too
            self.active_suspended = data
        except Exception:
            pass

    def load_suspend_state(self):
        """Load suspended session from disk (if present). Returns dict or None."""
        try:
            if not os.path.exists(SUSPEND_STATE_FILE):
                return None
            with open(SUSPEND_STATE_FILE, "r") as f:
                data = json.load(f)
            # Basic validation
            if not isinstance(data.get("pids"), list) or "resume_time" not in data:
                return None
            return data
        except Exception:
            return None

    def clear_suspend_state(self):
        """Remove persisted suspended session."""
        try:
            if os.path.exists(SUSPEND_STATE_FILE):
                os.remove(SUSPEND_STATE_FILE)
        except Exception:
            pass
        self.active_suspended = None

    # ---------------- Suspend / Resume ----------------
    def stop_selected_task(self):
        """Called when STOP button is pressed. Suspend selected group's PIDs for chosen duration."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process/group to stop.")
            return

        # If child selected, get parent; else use selected
        parent = selected if not self.tree.parent(selected) else self.tree.parent(selected)

        # Collect PIDs from child rows
        pid_list = []
        for child in self.tree.get_children(parent):
            pid_val = str(self.tree.set(child, "pids") or "")
            if pid_val.isdigit():
                pid_list.append(int(pid_val))
            else:
                text = str(self.tree.item(child, "text") or "")
                if text.lower().startswith("pid"):
                    try:
                        pid_list.append(int(text.split()[1]))
                    except Exception:
                        pass

        if not pid_list:
            messagebox.showwarning("Warning", "Could not determine PIDs to stop.")
            return

        choice = self.stop_duration.get()
        if choice == "2 Hours":
            seconds = 2 * 3600
        elif choice == "7 Days":
            seconds = 7 * 24 * 3600
        elif choice == "1 Month":
            seconds = 30 * 24 * 3600
        elif choice == "1 Year":
            seconds = 365 * 24 * 3600
        elif choice == "Custom (Minutes)":
            try:
                seconds = float(self.custom_minutes.get()) * 60
            except Exception:
                messagebox.showerror("Error", "Invalid custom minutes.")
                return
        else:
            seconds = 3600

        if not messagebox.askyesno("Confirm", f"Suspend {len(pid_list)} processes for {seconds/60:.1f} minutes?"):
            return

        # Start background thread that suspends, persists state, waits, and resumes.
        threading.Thread(target=self._suspend_resume_processes, args=(pid_list, seconds), daemon=True).start()

    def _suspend_resume_processes(self, pid_list, seconds):
        # compute resume epoch
        resume_time = time.time() + float(seconds)
        # persist state before suspending so we can resume on restart
        try:
            self.save_suspend_state(pid_list, resume_time)
        except Exception:
            pass

        suspended_pids = []
        for pid in pid_list:
            try:
                p = psutil.Process(pid)
                p.suspend()
                suspended_pids.append(pid)
            except Exception:
                # ignore errors (permission, process gone)
                pass

        # show initial stopped info on main thread
        self.root.after(0, lambda: messagebox.showinfo(
            "Stopped",
            f"{len(suspended_pids)} process(es) suspended.\nThey will resume automatically after the selected duration, or when you choose to resume on app restart."
        ))

        # Sleep (non-blocking UI because this is a background thread)
        # If app closes while sleeping, resume won't occur here--it will be handled on startup via persisted file.
        time_left = resume_time - time.time()
        if time_left > 0:
            time.sleep(time_left)

        # Attempt to resume (if app still running)
        resumed = 0
        for pid in suspended_pids:
            try:
                psutil.Process(pid).resume()
                resumed += 1
            except Exception:
                pass

        # clear persisted state and show resumed message
        try:
            self.clear_suspend_state()
        except Exception:
            pass

        if resumed > 0:
            self.root.after(0, lambda: messagebox.showinfo("Resumed", f"{resumed} process(es) resumed automatically."))

    def resume_pids(self, pid_list):
        """Resume a list of PIDs (best-effort)."""
        resumed = 0
        for pid in pid_list:
            try:
                psutil.Process(int(pid)).resume()
                resumed += 1
            except Exception:
                pass
        return resumed

    # ---------------- CPU / network helpers ----------------
    def _prime_cpu_percent(self):
        for p in psutil.process_iter(['pid']):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def _estimate_power_mw(self, cpu_pct):
        try:
            return (cpu_pct / 100.0) * self.CPU_TDP_WATTS * 1000.0
        except Exception:
            return 0.0

    def _get_network_kbps_for_pid(self, pid, proc, now):
        try:
            io = proc.io_counters()
            total_bytes = (getattr(io, "read_bytes", 0) or 0) + (getattr(io, "write_bytes", 0) or 0)
            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta = total_bytes - last_bytes
                dt = max(now - last_time, 0.001)
                kbps = (delta / dt) / 1024.0
            else:
                kbps = 0.0
            self.last_net_io[pid] = (total_bytes, now)
            return max(kbps, 0.0)
        except Exception:
            return 0.0

    # ---------------- Refresh / grouping ----------------
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
                pid = info.get('pid')
                raw_name = (info.get('name') or "unknown").strip()
                name_lower = raw_name.lower()

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

                net_kbps = self._get_network_kbps_for_pid(pid, proc, now)
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
                agg["network"] += float(net_kbps or 0.0)
                agg["per_pid"][pid] = {
                    "cpu": float(cpu or 0.0),
                    "memory": float(mem_mb or 0.0),
                    "power": float(power_mw or 0.0),
                    "network": float(net_kbps or 0.0)
                }

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        aggregated_list = list(processes.values())
        aggregated_list.sort(key=lambda x: x["cpu"], reverse=True)
        self.all_processes = aggregated_list

        # update UI
        self.root.after(0, lambda: self.display_processes(self.all_processes))
        # schedule next auto refresh
        self.root.after(self.update_interval, self.manual_refresh)
        self.refreshing = False

    # ---------------- Display & Notifications ----------------
    def display_processes(self, processes):
        self.tree.delete(*self.tree.get_children())

        try:
            memory_limit = float(self.memory_limit_entry.get())
            if memory_limit < 0:
                memory_limit = 0.0
        except Exception:
            memory_limit = 0.0

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

                with self.notification_lock:
                    if name not in self.alerted_names:
                        self.alerted_names.add(name)
                        try:
                            self.notifier.show_toast(
                                "High Memory Usage",
                                f"{name} is using {mem_sum:.2f} MB (limit {memory_limit:.0f} MB). Click to focus.",
                                icon_path=None,
                                duration=8,
                                threaded=True,
                                callback_on_click=lambda n=name: self.on_notification_click(n)
                            )
                        except Exception:
                            # fallback: non-clickable toast
                            try:
                                self.notifier.show_toast(
                                    "High Memory Usage",
                                    f"{name} is using {mem_sum:.2f} MB (limit {memory_limit:.0f} MB).",
                                    duration=8,
                                    threaded=True
                                )
                            except Exception:
                                pass

            parent = self.tree.insert(
                "", tk.END,
                text=name,
                values=(pid_display, f"{cpu_sum:.1f}", f"{mem_sum:.2f}", f"{power_sum:.0f}", f"{net_sum:.1f}"),
                tags=(tag,),
                open=False
            )

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

        # cleanup alerted names no longer high
        with self.notification_lock:
            to_remove = [n for n in self.alerted_names if n not in current_high_names]
            for n in to_remove:
                try:
                    self.alerted_names.remove(n)
                except Exception:
                    pass

    def on_notification_click(self, process_name):
        """Called when user clicks the toast: focus window and select parent row."""
        def _focus_and_select():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                for child in self.tree.get_children():
                    if str(self.tree.item(child, "text")).lower() == str(process_name).lower():
                        self.tree.selection_set(child)
                        self.tree.focus(child)
                        self.tree.see(child)
                        # also expand to show PIDs
                        self.tree.item(child, open=True)
                        break
            except Exception:
                pass

        try:
            self.root.after(0, _focus_and_select)
        except Exception:
            pass

    # ---------------- Search / End task ----------------
    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = []
        for p in self.all_processes:
            name = p["display_name"]
            if query in name.lower():
                filtered.append(p)
                continue
            if any(query in str(pid) for pid in p["pids"]):
                filtered.append(p)

        if not filtered:
            messagebox.showinfo("Not Found", f"No match for: {query}")
        else:
            self.display_processes(filtered)

    def end_selected_task(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process/group to end.")
            return

        parent = selected if not self.tree.parent(selected) else self.tree.parent(selected)

        pid_list = []
        for child in self.tree.get_children(parent):
            pid_val = str(self.tree.set(child, "pids") or "")
            if pid_val.isdigit():
                pid_list.append(int(pid_val))
            else:
                text = str(self.tree.item(child, "text") or "")
                if text.lower().startswith("pid"):
                    try:
                        pid_list.append(int(text.split()[1]))
                    except Exception:
                        pass

        if not pid_list:
            messagebox.showwarning("Warning", "Could not determine PIDs to terminate.")
            return

        if not messagebox.askyesno("Confirm Terminate", f"Terminate {len(pid_list)} processes?"):
            return

        killed = 0
        for pid in pid_list:
            try:
                psutil.Process(pid).terminate()
                killed += 1
            except Exception:
                try:
                    psutil.Process(pid).kill()
                    killed += 1
                except Exception:
                    pass

        messagebox.showinfo("Result", f"Attempted to terminate {killed} process(es).")
        self.manual_refresh()

    # ---------------- Double-click Info ----------------
    def on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return

        text = self.tree.item(row, "text")
        vals = self.tree.item(row, "values")
        if not self.tree.parent(row):
            # parent aggregate info
            info_lines = [
                f"Name: {text}",
                f"PIDs: {vals[0] if vals else ''}",
                f"CPU (sum %): {vals[1] if len(vals) > 1 else ''}",
                f"Memory (sum MB): {vals[2] if len(vals) > 2 else ''}",
                f"Power (approx mW): {vals[3] if len(vals) > 3 else ''}",
                f"Network (KB/s sum): {vals[4] if len(vals) > 4 else ''}",
            ]
            for child in self.tree.get_children(row):
                ctext = self.tree.item(child, "text")
                cvals = self.tree.item(child, "values")
                info_lines.append(f"\n{ctext}: {cvals}")
            messagebox.showinfo("Process Group Info", "\n".join(info_lines))
        else:
            # child row: show PID details and attempt psutil details
            pid_text = text  # "PID {pid}"
            info_lines = [f"{pid_text}", f"Values: {vals}"]
            try:
                pid_num = int(pid_text.split()[1])
                try:
                    p = psutil.Process(pid_num)
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

                    info_lines.append(f"exe={exe}, status={status}, threads={threads}, cpu={cpu_pct}, mem={mem_mb}")
                except psutil.NoSuchProcess:
                    info_lines.append("(process no longer exists)")
            except Exception:
                pass

            messagebox.showinfo("PID Info", "\n".join(info_lines))

    # ---------------- Graph updates ----------------
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

    # ---------------- Persisted-suspension handling on startup ----------------
    def check_persisted_suspend_state(self):
        """If a persisted suspended session exists, ask user whether to resume now.
        If user declines, schedule automatic resume when the resume_time arrives."""
        state = self.load_suspend_state()
        if not state:
            return

        pids = state.get("pids", [])
        resume_time = float(state.get("resume_time", 0))
        now = time.time()
        remaining = int(resume_time - now)

        if remaining <= 0:
            # resume immediately (best-effort) and clear state
            resumed = self.resume_pids(pids)
            self.clear_suspend_state()
            if resumed > 0:
                # show info on main thread
                self.root.after(0, lambda: messagebox.showinfo("Resumed", f"{resumed} processes resumed (time elapsed)."))
            return

        # Ask the user if they want to resume immediately
        def ask_and_take_action():
            try:
                ans = messagebox.askyesno(
                    "Resume Suspended Processes",
                    f"A previous stop session was detected with {len(pids)} suspended process(es).\n\n"
                    f"Resume now?"
                )
                if ans:
                    resumed = self.resume_pids(pids)
                    self.clear_suspend_state()
                    if resumed > 0:
                        messagebox.showinfo("Resumed", f"{resumed} process(es) resumed.")
                else:
                    # schedule a background thread to auto-resume when time arrives
                    threading.Thread(target=self._delayed_resume_from_persisted, args=(pids, resume_time), daemon=True).start()
            except Exception:
                # if messagebox fails, still schedule auto-resume
                threading.Thread(target=self._delayed_resume_from_persisted, args=(pids, resume_time), daemon=True).start()

        # show popup on main thread
        self.root.after(0, ask_and_take_action)

    def _delayed_resume_from_persisted(self, pids, resume_time):
        """Background thread: wait until resume_time then resume persisted pids and clear file."""
        now = time.time()
        wait = resume_time - now
        if wait > 0:
            time.sleep(wait)
        resumed = 0
        for pid in pids:
            try:
                psutil.Process(int(pid)).resume()
                resumed += 1
            except Exception:
                pass
        try:
            self.clear_suspend_state()
        except Exception:
            pass
        if resumed > 0:
            self.root.after(0, lambda: messagebox.showinfo("Resumed", f"{resumed} process(es) resumed (persisted session)."))

# ---------------- Run ----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1300x750")
    app = TaskManagerApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass