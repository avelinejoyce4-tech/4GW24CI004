import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading

class TaskManagerApp:
    def _init_(self, root):
        self.root = root
        self.root.title("Simple Task Manager")

        # Frame for search and input fields
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10, fill=tk.X)

        # Search label and entry
        tk.Label(input_frame, text="Search (PID or Name):").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(input_frame, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        # Memory threshold input
        tk.Label(input_frame, text="Average Memory Limit (MB):").pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry = tk.Entry(input_frame, width=10)
        self.memory_limit_entry.pack(side=tk.LEFT, padx=5)
        self.memory_limit_entry.insert(0, "200")  # Default threshold

        # Search button
        search_button = tk.Button(input_frame, text="Search", command=self.search_process)
        search_button.pack(side=tk.LEFT, padx=5)

        # Refresh button
        refresh_button = tk.Button(input_frame, text="Refresh", command=self.refresh_processes)
        refresh_button.pack(side=tk.LEFT, padx=5)

        # Set up the Treeview
        columns = ("pid", "name", "cpu", "memory", "publisher")
        self.tree = ttk.Treeview(root, columns=columns, show='headings')
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Name")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("memory", text="Memory (MB)")
        self.tree.heading("publisher", text="Publisher")

        self.tree.column("pid", width=80)
        self.tree.column("name", width=200)
        self.tree.column("cpu", width=80)
        self.tree.column("memory", width=100)
        self.tree.column("publisher", width=200)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Treeview tag styling for highlighting
        self.tree.tag_configure("high_memory", background="#ffcccc")  # light red

        # Auto-update every 5 minutes (300000 ms)
        self.update_interval = 300000
        self.refresh_processes()

    def refresh_processes(self):
        """Refresh the process list in a background thread."""
        threading.Thread(target=self.update_processes_list, daemon=True).start()
        # Schedule next refresh
        self.root.after(self.update_interval, self.refresh_processes)

    def get_publisher(self, exe_path):
        """Try to get publisher info for Windows executables."""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, '\\')
            str_info = win32api.VerQueryValue(info, '\\StringFileInfo\\040904B0\\CompanyName')
            return str_info.strip() if str_info else "Unknown"
        except Exception:
            return "Unknown"

    def update_processes_list(self):
        """Collect and display process info."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe']):
            try:
                pinfo = proc.info
                exe_path = pinfo.get('exe') or ""
                publisher = self.get_publisher(exe_path)
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_usage': pinfo['memory_info'].rss / (1024 * 1024),  # MB
                    'publisher': publisher
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort by CPU usage
        processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)

        # Save the list for searching
        self.all_processes = processes

        self.display_processes(processes)

    def display_processes(self, processes):
        """Display process list in the table and highlight high memory usage."""
        self.tree.delete(*self.tree.get_children())

        # Get user-defined average memory limit
        try:
            memory_limit = float(self.memory_limit_entry.get())
        except ValueError:
            memory_limit = 0

        for proc in processes:
            tag = ""
            if proc['memory_usage'] > memory_limit and memory_limit > 0:
                tag = "high_memory"
            self.tree.insert(
                "",
                tk.END,
                values=(proc['pid'], proc['name'], f"{proc['cpu_percent']:.1f}",
                        f"{proc['memory_usage']:.2f}", proc['publisher']),
                tags=(tag,)
            )

    def search_process(self):
        """Filter and display processes based on user input."""
        query = self.search_entry.get().strip().lower()
        if not hasattr(self, "all_processes") or not self.all_processes:
            messagebox.showinfo("Info", "Process list is empty. Please refresh first.")
            return

        if not query:
            self.display_processes(self.all_processes)
            return

        # Try to match by PID or name
        filtered = []
        for proc in self.all_processes:
            if query.isdigit() and int(query) == proc['pid']:
                filtered.append(proc)
            elif query in proc['name'].lower():
                filtered.append(proc)

        if not filtered:
            messagebox.showinfo("Not Found", f"No process found for '{query}'.")
        self.display_processes(filtered)


# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()