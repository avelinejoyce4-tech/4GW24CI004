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
        self.root.title("Advanced Task Manager")
        self.root.geometry("1100x720")

        self.CPU_TDP_WATTS = 15.0
        self.update_interval = 5000
        self.all_processes = []
        self.last_net_io = {}

        # ===========================
        # TOP MENU BUTTON BLOCKS
        # ===========================
        top_block = tk.Frame(root)
        top_block.pack(fill=tk.X, pady=10)

        # BLOCK 1 – Processes
        btn_proc = tk.Button(
            top_block,
            text="PROCESS LIST (DEFAULT)",
            width=25,
            height=2,
            command=self.show_process_block,
            bg="#cfe2ff"
        )
        btn_proc.grid(row=0, column=0, padx=10)

        # BLOCK 2 – Graph Window
        btn_graph = tk.Button(
            top_block,
            text="LIVE GRAPH WINDOW",
            width=25,
            height=2,
            command=self.open_graph_window,
            bg="#d1e7dd"
        )
        btn_graph.grid(row=0, column=1, padx=10)

        # BLOCK 3 – About
        btn_about = tk.Button(
            top_block,
            text="ABOUT THIS PROJECT",
            width=25,
            height=2,
            command=self.open_about_window,
            bg="#fce4ec"
        )
        btn_about.grid(row=0, column=2, padx=10)

        # ===========================
        # PROCESS BLOCK (SEARCH+TABLE)
        # ===========================
        self.process_frame = tk.Frame(root)
        self.process_frame.pack(fill=tk.BOTH, expand=True)

        self.build_process_ui()

        # Bootstrap CPU for accuracy
        self._prime_cpu_percent()
        self.refresh_processes()
        self.update_graph_background()

    # -------------------------------------------------------------

    def build_process_ui(self):
        input_frame = tk.Frame(self.process_frame)
        input_frame.pack(pady=10, fill=tk.X)

        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(input_frame, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(input_frame, text="Memory Limit (MB):").pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry = tk.Entry(input_frame, width=10)
        self.memory_limit_entry.insert(0, "200")
        self.memory_limit_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(input_frame, text="Search", command=self.search_process).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="Refresh", command=self.refresh_processes).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="End Task", command=self.end_selected_task).pack(side=tk.LEFT, padx=5)

        columns = ("pid", "name", "cpu", "memory", "publisher", "power", "network")
        self.tree = ttk.Treeview(self.process_frame, columns=columns, show='headings')

        for col, text, width in [
            ("pid", "PID", 70),
            ("name", "Name", 180),
            ("cpu", "CPU (%)", 80),
            ("memory", "Memory (MB)", 100),
            ("publisher", "Publisher", 160),
            ("power", "Power (mW)", 100),
            ("network", "Network (KB/s)", 120),
        ]:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("high_memory", background="#ffcccc")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self.show_process_info)

    # ================= PROCESS HANDLING ======================

    def _prime_cpu_percent(self):
        for proc in psutil.process_iter(['pid']):
            try:
                proc.cpu_percent(interval=None)
            except:
                pass
        psutil.cpu_percent(interval=None)

    def refresh_processes(self):
        threading.Thread(target=self.update_processes_list, daemon=True).start()
        self.root.after(self.update_interval, self.refresh_processes)

    def update_processes_list(self):
        processes = []
        now = time.time()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                cpu = proc.cpu_percent(interval=None)
                mem_mb = proc.memory_info().rss / 1024 / 1024
                publisher = self.get_publisher(proc.info.get('exe') or "")
                power = self._estimate_power_mw(cpu)
                network = self._get_network_kbps(proc, now)

                processes.append({
                    "pid": proc.pid,
                    "name": proc.info['name'],
                    "cpu": cpu,
                    "memory": mem_mb,
                    "publisher": publisher,
                    "power": power,
                    "network": network
                })
            except:
                continue

        self.all_processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)
        self.root.after(0, lambda: self.display_processes(self.all_processes))

    def display_processes(self, processes):
        self.tree.delete(*self.tree.get_children())

        try:
            memory_limit = float(self.memory_limit_entry.get())
        except:
            memory_limit = 0

        for p in processes:
            tag = "high_memory" if (memory_limit > 0 and p["memory"] > memory_limit) else ""
            self.tree.insert("", tk.END,
                             values=(p["pid"], p["name"], f"{p['cpu']:.1f}",
                                     f"{p['memory']:.2f}", p["publisher"],
                                     p["power"], p["network"]),
                             tags=(tag,))

    # =================== SORTING =======================

    def sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]

        try:
            data.sort(reverse=descending, key=lambda t: float(t[0]))
        except:
            data.sort(reverse=descending)

        for idx, (_, child) in enumerate(data):
            self.tree.move(child, "", idx)

        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    # =================== SEARCH =======================

    def search_process(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.display_processes(self.all_processes)
            return

        filtered = [
            p for p in self.all_processes
            if query in p["name"].lower() or query == str(p["pid"])
        ]

        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")

        self.display_processes(filtered)

    # ================= END TASK ========================

    def end_selected_task(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Select a process.")
            return

        pid = int(self.tree.item(selected, "values")[0])
        try:
            psutil.Process(pid).terminate()
            messagebox.showinfo("Process Ended", f"Process {pid} terminated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= PROCESS DETAILS =================

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
Memory: {p.memory_info().rss/1024/1024:.2f} MB
CPU %: {p.cpu_percent(interval=0.1):.1f}
Executable: {p.exe()}
            """
            messagebox.showinfo("Process Info", info)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= GRAPH WINDOW ====================

    def open_graph_window(self):
        win = tk.Toplevel(self.root)
        win.title("CPU & Memory Live Graph")
        win.geometry("700x400")

        fig = Figure(figsize=(7, 3), dpi=100)
        ax = fig.add_subplot(111)

        ax.set_title("Live CPU & Memory Usage")
        ax.set_ylim(0, 100)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Usage (%)")

        self.cpu_data, self.mem_data = [], []
        self.line_cpu, = ax.plot([], [], label="CPU", lw=2)
        self.line_mem, = ax.plot([], [], label="Memory", lw=2)
        ax.legend()

        canvas = FigureCanvasTkAgg(fig, win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.graph_canvas = canvas
        self.graph_ax = ax

        self.update_graph_window()

    def update_graph_window(self):
        if not hasattr(self, "graph_ax"):
            return

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        self.cpu_data.append(cpu)
        self.mem_data.append(mem)

        if len(self.cpu_data) > 50:
            self.cpu_data.pop(0)
            self.mem_data.pop(0)

        self.line_cpu.set_data(range(len(self.cpu_data)), self.cpu_data)
        self.line_mem.set_data(range(len(self.mem_data)), self.mem_data)

        self.graph_ax.set_xlim(0, len(self.cpu_data))

        self.graph_canvas.draw_idle()
        self.root.after(1000, self.update_graph_window)

    # Invisible background graph update (for future extensions)
    def update_graph_background(self):
        self.root.after(1000, self.update_graph_background)

    # ================= ABOUT WINDOW ==================

    def open_about_window(self):
        win = tk.Toplevel(self.root)
        win.title("About this Project")
        win.geometry("500x350")

        text = """
📌 **Advanced Task Manager Project**

This project is developed using:
✔ Python  
✔ Tkinter  
✔ psutil  
✔ Matplotlib

Features:
- View running processes
- CPU, RAM, network usage
- End tasks
- Publisher information
- Live performance graph
- Search & filter
- Memory highlighting

This mini-project is suitable for:
B.Tech | Diploma | Python learners.
"""

        tk.Label(win, text=text, justify="left", font=("Arial", 12)).pack(padx=10, pady=10)

    # ================= HELPERS ==================

    def _estimate_power_mw(self, cpu_percent):
        return f"{(cpu_percent/100)*self.CPU_TDP_WATTS*1000:.0f}"

    def _get_network_kbps(self, proc, now):
        try:
            io = proc.io_counters()
            total = io.read_bytes + io.write_bytes
            pid = proc.pid

            if pid in self.last_net_io:
                last_bytes, last_time = self.last_net_io[pid]
                delta_b = total - last_bytes
                delta_t = max(now - last_time, 0.001)
                rate = (delta_b / delta_t) / 1024
            else:
                rate = 0.0

            self.last_net_io[pid] = (total, now)
            return f"{rate:.1f}"
        except:
            return "—"
    def get_publisher(self, exe):
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe, '\\')
            return win32api.VerQueryValue(info, '\\StringFileInfo\\040904B0\\CompanyName') or "Unknown"
        except:
            return "Unknown"


# Run App
if __name__ == "__main__":
    root = tk.Tk()
    TaskManagerApp(root)
    root.mainloop()
