import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from main import SCENARIOS
from service_desk.data import L2_ENGINEERS, build_bank_service_desk
from service_desk.models import PRIORITIES
from service_desk.simulation import Scenario, simulate_improvement
from service_desk.sla import (CRITICAL_VIOLATION_THRESHOLD, apply_money_transfer_policy,
                              build_sla_report, critical_warning)
from service_desk.statistics import generate_incident_statistics

RED = "#fde2e1"
GREEN = "#e3f5e1"
BAR_OK = "#3c9d5d"
BAR_WARN = "#e0a030"
BAR_BAD = "#d9534f"
SCALE = 1.0


def px(value):
    return int(value * SCALE)


def make_tree(parent, columns, widths, height=8):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=px(width), anchor="w")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, tree


def fill(tree, rows, tags=None):
    tree.delete(*tree.get_children())
    for n, row in enumerate(rows):
        tree.insert("", "end", values=row, tags=(tags[n],) if tags else ())


class ServiceDeskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        global SCALE
        SCALE = self.winfo_fpixels("1i") / 96
        self.title("Bank Service Desk - SLA monitoring")
        width = min(px(1180), self.winfo_screenwidth() - 40)
        height = min(px(720), self.winfo_screenheight() - px(90))
        self.geometry(f"{width}x{height}+10+10")
        self.minsize(min(px(900), width), min(px(560), height))

        self.desk = build_bank_service_desk(operators=2)
        self.policy_changes = apply_money_transfer_policy(self.desk)

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=px(24))
        style.configure("Big.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Head.TLabel", font=("Segoe UI", 11, "bold"))

        self.banner = tk.Label(self, font=("Segoe UI", 11, "bold"), anchor="w", padx=12, pady=6)
        self.banner.pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_services = ttk.Frame(notebook, padding=10)
        self.tab_incidents = ttk.Frame(notebook, padding=10)
        self.tab_sla = ttk.Frame(notebook, padding=10)
        self.tab_stats = ttk.Frame(notebook, padding=10)
        self.tab_sim = ttk.Frame(notebook, padding=10)
        notebook.add(self.tab_services, text="  Services  ")
        notebook.add(self.tab_incidents, text="  Incidents  ")
        notebook.add(self.tab_sla, text="  SLA report  ")
        notebook.add(self.tab_stats, text="  Statistics  ")
        notebook.add(self.tab_sim, text="  Improvements  ")

        self.build_services_tab()
        self.build_incidents_tab()
        self.build_sla_tab()
        self.build_stats_tab()
        self.build_sim_tab()
        self.refresh()

    def build_services_tab(self):
        tab = self.tab_services
        cols = ("ID", "Service", "Category", "Response, min", "Resolution, min", "Owner", "Status", "Transfer")
        frame, self.services_tree = make_tree(tab, cols, (70, 220, 160, 100, 110, 200, 80, 70), height=6)
        frame.pack(fill="both", expand=True)
        self.services_tree.bind("<<TreeviewSelect>>", self.on_service_select)

        if self.policy_changes:
            ttk.Label(tab, text="Option 5 policy applied: " + "; ".join(self.policy_changes),
                      foreground="#555").pack(side="bottom", anchor="w", pady=(6, 0), before=frame)

        form = ttk.LabelFrame(tab, text="Change SLA targets of the selected service", padding=10)
        form.pack(side="bottom", fill="x", pady=(10, 0), before=frame)
        self.edit_service_label = ttk.Label(form, text="Select a service in the table")
        self.edit_service_label.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))
        ttk.Label(form, text="Response, min").grid(row=1, column=0, sticky="w")
        self.edit_response = ttk.Spinbox(form, from_=1, to=1440, width=8)
        self.edit_response.grid(row=1, column=1, padx=(4, 16))
        ttk.Label(form, text="Resolution, min").grid(row=1, column=2, sticky="w")
        self.edit_resolution = ttk.Spinbox(form, from_=1, to=2880, width=8)
        self.edit_resolution.grid(row=1, column=3, padx=(4, 16))
        ttk.Button(form, text="Save targets", command=self.save_targets).grid(row=1, column=4)

    def on_service_select(self, _event=None):
        selected = self.services_tree.selection()
        if not selected:
            return
        sid = self.services_tree.item(selected[0], "values")[0]
        service = self.desk.get_service(sid)
        self.edit_service_label.config(text=f"{service.service_id} - {service.service_name}")
        self.edit_response.set(round(service.sla_response_time_hours * 60))
        self.edit_resolution.set(round(service.sla_resolution_time_hours * 60))

    def save_targets(self):
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showinfo("SLA targets", "Select a service first.")
            return
        try:
            response = float(self.edit_response.get())
            resolution = float(self.edit_resolution.get())
            if response <= 0 or resolution <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("SLA targets", "Targets must be positive numbers of minutes.")
            return
        service = self.desk.get_service(self.services_tree.item(selected[0], "values")[0])
        service.sla_response_time_hours = response / 60
        service.sla_resolution_time_hours = resolution / 60
        self.refresh()

    def build_incidents_tab(self):
        tab = self.tab_incidents
        cols = ("ID", "Service", "Priority", "Created", "Assigned to", "Response", "Resolution",
                "Status", "FCR", "SLA", "Description")
        frame, self.incidents_tree = make_tree(
            tab, cols, (70, 70, 70, 100, 150, 70, 80, 60, 40, 80, 300), height=8)
        frame.pack(fill="both", expand=True)
        self.incidents_tree.tag_configure("bad", background=RED)
        self.incidents_tree.tag_configure("ok", background=GREEN)

        form = ttk.LabelFrame(tab, text="Register a new incident", padding=10)
        form.pack(side="bottom", fill="x", pady=(10, 0), before=frame)
        names = [f"{s.service_id} - {s.service_name}" for s in self.desk.services.values()]
        self.new_service = ttk.Combobox(form, values=names, state="readonly", width=34)
        self.new_service.current(0)
        self.new_service.bind("<<ComboboxSelected>>", self.on_new_service)
        self.new_priority = ttk.Combobox(form, values=PRIORITIES, state="readonly", width=10)
        self.new_priority.set("High")
        self.new_description = ttk.Entry(form, width=48)
        self.new_created = ttk.Entry(form, width=17)
        self.new_created.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.new_engineer = ttk.Entry(form, width=22)
        self.new_response = ttk.Spinbox(form, from_=0, to=1440, width=7)
        self.new_response.set(5)
        self.new_resolution = ttk.Spinbox(form, from_=1, to=2880, width=7)
        self.new_resolution.set(30)
        self.new_fcr = tk.BooleanVar()

        widgets = [
            ("Service", self.new_service), ("Priority", self.new_priority),
            ("Created (YYYY-MM-DD HH:MM)", self.new_created), ("Description", self.new_description),
            ("Assigned to", self.new_engineer), ("Response, min", self.new_response),
            ("Resolution, min", self.new_resolution),
        ]
        for n, (label, widget) in enumerate(widgets):
            row, col = divmod(n, 4)
            ttk.Label(form, text=label).grid(row=row * 2, column=col, sticky="w", padx=4)
            widget.grid(row=row * 2 + 1, column=col, sticky="w", padx=4, pady=(0, 6))
        ttk.Checkbutton(form, text="Resolved at first contact", variable=self.new_fcr).grid(
            row=3, column=3, sticky="w", padx=4)
        ttk.Button(form, text="Add incident", command=self.add_incident).grid(
            row=3, column=4, sticky="e", padx=4)
        self.on_new_service()

    def on_new_service(self, _event=None):
        sid = self.new_service.get().split(" - ")[0]
        self.new_engineer.delete(0, "end")
        self.new_engineer.insert(0, L2_ENGINEERS.get(sid, ""))

    def add_incident(self):
        try:
            sid = self.new_service.get().split(" - ")[0]
            description = self.new_description.get().strip()
            if not description:
                raise ValueError("Enter a description.")
            created = datetime.strptime(self.new_created.get().strip(), "%Y-%m-%d %H:%M")
            response = float(self.new_response.get())
            resolution = float(self.new_resolution.get())
            if resolution < response:
                raise ValueError("Resolution time cannot be shorter than response time.")
            engineer = self.new_engineer.get().strip() or "Service Desk"
        except ValueError as err:
            messagebox.showerror("New incident", str(err) if str(err) else "Check the entered values.")
            return
        incident = self.desk.open_incident(sid, description, self.new_priority.get(), created)
        incident.assign(engineer, created + timedelta(minutes=response))
        incident.resolve(created + timedelta(minutes=resolution), first_contact=self.new_fcr.get())
        incident.close(incident.resolved_time + timedelta(minutes=30))
        self.new_description.delete(0, "end")
        self.refresh()
        check = build_sla_report(self.desk).checks[-1]
        messagebox.showinfo("New incident", f"{incident.incident_id} registered.\nSLA: "
                            + ("met" if check.met else "VIOLATED - " + check.reason()))

    def build_sla_tab(self):
        tab = self.tab_sla
        top = ttk.Frame(tab)
        top.pack(fill="x")
        self.sla_total = ttk.Label(top, style="Big.TLabel")
        self.sla_total.pack(side="left")
        self.sla_transfer = ttk.Label(top, style="Head.TLabel")
        self.sla_transfer.pack(side="left", padx=30)

        middle = ttk.Frame(tab)
        middle.pack(fill="both", expand=True, pady=10)
        cols = ("ID", "Service", "Incidents", "SLA met", "Violated", "Compliance")
        frame, self.sla_tree = make_tree(middle, cols, (70, 220, 80, 70, 70, 90), height=8)
        frame.pack(side="left", fill="both", expand=True)
        self.sla_chart = tk.Canvas(middle, width=px(440), height=px(270), bg="white", highlightthickness=1,
                                   highlightbackground="#ccc")
        self.sla_chart.pack(side="left", padx=(10, 0))

        frame, self.violations_tree = make_tree(
            tab, ("Incident", "Priority", "Service", "Reason"), (80, 80, 240, 420), height=5)
        frame.pack(side="bottom", fill="x", before=middle)
        ttk.Label(tab, text="Incidents that violated the SLA", style="Head.TLabel").pack(
            side="bottom", anchor="w", before=frame)

    def draw_chart(self, report):
        c = self.sla_chart
        c.delete("all")
        w, h = int(c["width"]), int(c["height"])
        left, bottom, top = px(40), h - px(30), px(48)
        c.create_text(w / 2, px(14), text="SLA compliance by service, %", font=("Segoe UI", 9, "bold"))
        for pct in (0, 50, 100):
            y = bottom - (bottom - top) * pct / 100
            c.create_line(left, y, w - px(10), y, fill="#eee")
            c.create_text(left - px(6), y, text=str(pct), anchor="e", font=("Segoe UI", 8))
        target_y = bottom - (bottom - top) * (100 - CRITICAL_VIOLATION_THRESHOLD) / 100
        c.create_line(left, target_y, w - px(10), target_y, fill=BAR_BAD, dash=(4, 2))
        c.create_text(w - px(12), px(30), text="- - 90% target", anchor="e", fill=BAR_BAD, font=("Segoe UI", 8))
        sids = list(self.desk.services)
        slot = (w - left - px(10)) / len(sids)
        for n, sid in enumerate(sids):
            pct = report.service_percent(sid)
            x0 = left + n * slot + slot * 0.2
            x1 = left + (n + 1) * slot - slot * 0.2
            y = bottom - (bottom - top) * pct / 100
            color = BAR_OK if pct >= 90 else BAR_WARN if pct >= 60 else BAR_BAD
            c.create_rectangle(x0, y, x1, bottom, fill=color, outline="")
            c.create_text((x0 + x1) / 2, y - px(8), text=f"{pct:.0f}", font=("Segoe UI", 8))
            c.create_text((x0 + x1) / 2, bottom + px(14), text=sid, font=("Segoe UI", 8))

    def build_stats_tab(self):
        tab = self.tab_stats
        left = ttk.Frame(tab)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))

        ttk.Label(left, text="Incidents and average resolution time by service",
                  style="Head.TLabel").pack(anchor="w")
        service_frame, self.stats_service_tree = make_tree(
            left, ("ID", "Service", "Incidents", "Avg resolution, h"), (70, 220, 80, 120), height=6)
        service_frame.pack(fill="both", expand=True, pady=(4, 12))
        frame, self.stats_priority_tree = make_tree(
            left, ("Priority", "Avg resolution, h"), (120, 140), height=4)
        frame.pack(side="bottom", fill="x", pady=4, before=service_frame)
        ttk.Label(left, text="Average resolution time by priority", style="Head.TLabel").pack(
            side="bottom", anchor="w", before=frame)

        ttk.Label(right, text="Top 3 most problematic services", style="Head.TLabel").pack(anchor="w")
        self.top3_label = ttk.Label(right, justify="left", font=("Segoe UI", 10))
        self.top3_label.pack(anchor="w", pady=(4, 16))
        ttk.Label(right, text="First contact resolution (FCR)", style="Head.TLabel").pack(anchor="w")
        self.fcr_label = ttk.Label(right, style="Big.TLabel")
        self.fcr_label.pack(anchor="w", pady=4)

    def build_sim_tab(self):
        tab = self.tab_sim
        form = ttk.LabelFrame(tab, text="Scenario parameters", padding=10)
        form.pack(fill="x")
        ttk.Label(form, text=f"Service Desk operators (now {self.desk.operators})").grid(row=0, column=0, sticky="w")
        self.sim_operators = ttk.Spinbox(form, from_=1, to=10, width=6)
        self.sim_operators.set(self.desk.operators)
        self.sim_operators.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(form, text="Work time reduction (knowledge base, runbooks, automation)").grid(
            row=1, column=0, sticky="w", pady=6)
        self.sim_reduction = tk.IntVar(value=0)
        self.sim_reduction_label = ttk.Label(form, text="0 %", width=6)
        ttk.Scale(form, from_=0, to=90, variable=self.sim_reduction, length=px(240),
                  command=lambda v: self.sim_reduction_label.config(text=f"{float(v):.0f} %")).grid(
            row=1, column=1, sticky="w", padx=6)
        self.sim_reduction_label.grid(row=1, column=2, sticky="w")

        ttk.Label(form, text="Apply reduction to").grid(row=2, column=0, sticky="nw")
        boxes = ttk.Frame(form)
        boxes.grid(row=2, column=1, columnspan=3, sticky="w", padx=6)
        self.sim_services = {}
        for n, (sid, service) in enumerate(self.desk.services.items()):
            var = tk.BooleanVar(value=service.money_transfer)
            ttk.Checkbutton(boxes, text=service.service_name, variable=var).grid(
                row=n // 3, column=n % 3, sticky="w", padx=(0, 16))
            self.sim_services[sid] = var

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Run scenario", command=self.run_custom_scenario).pack(side="left")
        ttk.Label(buttons, text="   Presets:").pack(side="left")
        for scenario in SCENARIOS:
            ttk.Button(buttons, text=scenario.name.split(".")[0],
                       command=lambda s=scenario: self.show_scenario(s)).pack(side="left", padx=3)

        self.sim_title = ttk.Label(tab, style="Head.TLabel")
        self.sim_title.pack(anchor="w", pady=(14, 4))
        self.sim_result = tk.Label(tab, font=("Segoe UI", 14, "bold"), anchor="w", padx=10, pady=8)
        self.sim_result.pack(fill="x")
        ttk.Label(tab, text="Remaining SLA violations after the change", style="Head.TLabel").pack(
            anchor="w", pady=(12, 4))
        frame, self.sim_tree = make_tree(tab, ("Incident", "Service", "Reason"), (80, 240, 480), height=7)
        frame.pack(fill="both", expand=True)

    def run_custom_scenario(self):
        try:
            operators = int(self.sim_operators.get())
            if operators < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Scenario", "Operators must be a whole number >= 1.")
            return
        services = [sid for sid, var in self.sim_services.items() if var.get()]
        scenario = Scenario(f"{operators} operators, work time -{self.sim_reduction.get()} % "
                            f"for {len(services)} service(s)",
                            operators=operators, resolution_reduction=self.sim_reduction.get() / 100,
                            reduction_services=services)
        self.show_scenario(scenario)

    def show_scenario(self, scenario):
        result = simulate_improvement(self.desk, scenario)
        warning = critical_warning(result.after)
        self.sim_title.config(text=f"Scenario: {scenario.name}")
        self.sim_result.config(
            text=f"SLA {result.before.compliance_percent:.1f}%  ->  {result.after.compliance_percent:.1f}%"
                 f"   ({result.change_points:+.1f} points)   "
                 + ("critical warning remains" if warning else "no critical warning"),
            bg=RED if warning else GREEN)
        fill(self.sim_tree, [[c.incident_id, result.desk_after.get_service(c.service_id).service_name, c.reason()]
                             for c in result.after.violations])

    def refresh(self):
        report = build_sla_report(self.desk)
        stats = generate_incident_statistics(self.desk)
        warning = critical_warning(report)

        self.banner.config(
            text=(f"CRITICAL WARNING: {report.violation_percent:.1f}% of incidents violated the SLA "
                  f"(allowed {CRITICAL_VIOLATION_THRESHOLD:.0f}%)") if warning else
                 f"SLA violations {report.violation_percent:.1f}% - within the allowed limit",
            bg=BAR_BAD if warning else BAR_OK, fg="white")

        fill(self.services_tree, [[s.service_id, s.service_name, s.service_category,
                                   round(s.sla_response_time_hours * 60), round(s.sla_resolution_time_hours * 60),
                                   s.owner, s.status, "yes" if s.money_transfer else "no"]
                                  for s in self.desk.services.values()])

        rows, tags = [], []
        for inc, check in zip(self.desk.incidents, report.checks):
            rows.append([inc.incident_id, inc.service_id, inc.priority, f"{inc.created_time:%d.%m %H:%M}",
                         inc.assigned_to, f"{check.response_hours * 60:.0f} min",
                         f"{check.resolution_hours * 60:.0f} min", inc.status,
                         "yes" if inc.was_resolved_at_first_contact else "no",
                         "OK" if check.met else "VIOLATED", inc.description])
            tags.append("ok" if check.met else "bad")
        fill(self.incidents_tree, rows, tags)

        transfer = [c for c in report.checks if self.desk.get_service(c.service_id).money_transfer]
        t_met = sum(c.met for c in transfer)
        self.sla_total.config(text=f"SLA compliance: {report.met}/{report.total} = {report.compliance_percent:.1f}%")
        self.sla_transfer.config(text=f"Money transfer services (15 min): {t_met}/{len(transfer)} "
                                      f"= {100 * t_met / len(transfer) if transfer else 100:.1f}%")
        sla_rows = []
        for sid, service in self.desk.services.items():
            met, total = report.by_service[sid]
            sla_rows.append([sid, service.service_name, total, met, total - met, f"{report.service_percent(sid):.1f}%"])
        fill(self.sla_tree, sla_rows)
        fill(self.violations_tree, [[c.incident_id, self.desk.get_incident(c.incident_id).priority,
                                     self.desk.get_service(c.service_id).service_name, c.reason()]
                                    for c in report.violations])
        self.draw_chart(report)

        fill(self.stats_service_tree, [[sid, self.desk.services[sid].service_name, n,
                                        f"{stats.avg_resolution_by_service.get(sid, 0):.2f}"]
                                       for sid, n in stats.count_by_service.items()])
        fill(self.stats_priority_tree, [[p, f"{v:.2f}"] for p, v in stats.avg_resolution_by_priority.items()])
        self.top3_label.config(text="\n".join(
            f"{n}. {self.desk.services[sid].service_name} - {count} incidents, {viol} SLA violation(s)"
            for n, (sid, count, viol) in enumerate(stats.top_problem_services, 1)))
        self.fcr_label.config(text=f"{stats.first_contact_resolution_percent:.1f}%")


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass
    ServiceDeskApp().mainloop()
