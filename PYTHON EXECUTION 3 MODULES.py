# main.py
"""
Merged Instruction Simulator Project
Tabs:
 - Instruction Cycle Explorer
 - Bus Structure Simulator & Memory Transfer Lab
 - Architecture Profiler & Benchmark
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from functools import partial
import threading
import time
import math

# Matplotlib: Module1 expects it; Module3 handles optional matplotlib
try:
    import matplotlib
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False

# -----------------------------------------------------------
# Module 1 content (Instruction Cycle Explorer) converted to Frame
# -----------------------------------------------------------

# Instruction DB (same as provided)
INSTRUCTION_DB = {
    "8085": {
        "ADD": ("ADD", "REGISTER-REG", ["Fetch Opcode", "Read Regs", "ALU Add", "Set Flags", "Write Result"], 4, ["Z","S","CY","P"]),
        "SUB": ("SUB", "REGISTER-REG", ["Fetch Opcode", "Read Regs", "ALU Sub", "Set Flags", "Write Result"], 4, ["Z","S","CY","P"]),
        "CMP": ("CMP", "REGISTER-REG", ["Fetch Opcode", "Read Regs", "ALU Compare", "Set Flags"], 3, ["Z","S","CY"]),
        "MOV": ("MOV", "REGISTER-REG", ["Fetch Opcode", "Read Source", "Write Destination"], 2, []),
        "LDA": ("LDA", "DIRECT", ["Fetch Opcode", "Read Address", "Memory Read", "Write A"], 3, []),
        "STA": ("STA", "DIRECT", ["Fetch Opcode", "Read Address", "Memory Write"], 3, [])
    },
    "8086": {
        "ADD": ("ADD", "REGISTER-REG", ["Fetch Instr", "Decode", "Read Regs", "ALU Add", "Write Result", "Set Flags"], 4, ["Z","S","OF","CF"]),
        "SUB": ("SUB", "REGISTER-REG", ["Fetch Instr", "Decode", "Read Regs", "ALU Sub", "Write Result", "Set Flags"], 4, ["Z","S","OF","CF"]),
        "MOV": ("MOV", "REGISTER-REG", ["Fetch Instr", "Decode", "Read Source", "Write Dest"], 2, []),
        "MUL": ("MUL", "REGISTER-REG", ["Fetch Instr", "Decode", "Read Regs", "ALU Mul", "Adjust Hi/Lo", "Write Result"], 5, ["CF","OF"]),
        "CMP": ("CMP", "REGISTER-REG", ["Fetch Instr", "Decode", "Read Regs", "ALU Compare", "Set Flags"], 3, ["Z","S","OF","CF"])
    },
    "ARM": {
        "ADD": ("ADD", "REGISTER-REG", ["Fetch", "Decode", "Read Regs", "ALU Add", "Write Result", "Update Flags?"], 4, ["Z","N","C","V"]),
        "SUB": ("SUB", "REGISTER-REG", ["Fetch", "Decode", "Read Regs", "ALU Sub", "Write Result", "Update Flags?"], 4, ["Z","N","C","V"]),
        "MOV": ("MOV", "REGISTER-REG", ["Fetch", "Decode", "Read Source", "Write Dest"], 2, []),
        "LDR": ("LDR", "LOAD", ["Fetch", "Decode", "Calculate Addr", "Memory Read", "Write Reg"], 4, []),
        "STR": ("STR", "STORE", ["Fetch", "Decode", "Calculate Addr", "Memory Write"], 3, [])
    }
}

def make_registers_for(cpu):
    if cpu == "8085":
        return {"A":0, "B":0, "C":0, "D":0, "E":0, "H":0, "L":0, "PC":0, "SP":0, "FLAGS":{"Z":0,"S":0,"P":0,"CY":0,"AC":0}}
    if cpu == "8086":
        return {"AX":0, "BX":0, "CX":0, "DX":0, "SI":0, "DI":0, "BP":0, "SP":0, "IP":0, "FLAGS":{"Z":0,"S":0,"OF":0,"CF":0}}
    if cpu == "ARM":
        regs = {f"R{i}":0 for i in range(8)}
        regs.update({"PC":0, "SP":0, "FLAGS":{"N":0,"Z":0,"C":0,"V":0}})
        return regs
    return {}

def make_memory(size=256):
    return [0]*size

def decode_instruction_instance(cpu, instr_text):
    raw = instr_text.strip()
    if not raw:
        return None
    parts = raw.replace(",", " ").split()
    mnemonic = parts[0].upper()
    operands = parts[1:] if len(parts) > 1 else []
    db = INSTRUCTION_DB.get(cpu, {})
    match = None
    for key, val in db.items():
        if val[0] == mnemonic:
            match = (key, val)
            break
    if not match:
        return None
    opcode_key, info = match
    mnemonic, addr_mode, micro_ops, cycles, flags = info[0], info[1], info[2], info[3], info[4]
    return {"mnemonic":mnemonic, "opcode":opcode_key, "addressing":addr_mode, "micro_ops":micro_ops, "cycles":cycles, "flags":flags, "operands":operands}

def fsm_execute_instruction(state, instr_instance):
    cpu = state["cpu"]
    regs = state["registers"]
    mem = state["memory"]
    op = instr_instance
    ops = op["operands"]
    micro_ops = op["micro_ops"]

    for step in micro_ops:
        if "Fetch" in step:
            if cpu == "8085":
                regs["PC"] = (regs.get("PC",0) + 1) & 0xFFFF
            elif cpu == "8086":
                regs["IP"] = (regs.get("IP",0) + 1) & 0xFFFF
            elif cpu == "ARM":
                regs["PC"] = (regs.get("PC",0) + 4) & 0xFFFFFFFF
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Read Reg" in step or "Read Regs" in step:
            state["temp"] = []
            for operand in ops:
                opn = operand.upper()
                val = regs.get(opn, None)
                if val is None:
                    try:
                        val = int(opn.strip("[]"),0)
                    except:
                        val = 0
                state["temp"].append(val)
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Read Source" in step or "Read A" in step:
            src = ops[0] if ops else None
            value = regs.get(src, 0) if src in regs else 0
            state["temp"] = [value]
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Write Result" in step or "Write A" in step or "Write Reg" in step:
            dest = None
            if len(ops) >= 2:
                dest = ops[0] if op["addressing"].endswith("REG") else ops[0]
            elif len(ops) == 1:
                dest = ops[0]
            if dest is None:
                if cpu == "8085":
                    dest = "A"
                elif cpu == "ARM":
                    dest = "R0"
                else:
                    dest = list(regs.keys())[0]
            try:
                regs[dest] = state.get("alu_result", state["temp"][0] if state.get("temp") else 0)
            except Exception:
                pass
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif any(x in step for x in ("ALU Add","Add","ALU Sub","Sub","Mul","Multiply","Compare","AND","ALU Mul","ALU Sub","ALU Compare")):
            a = state.get("temp", [0,0])[0] if state.get("temp") else 0
            b = state.get("temp", [0,0])[1] if len(state.get("temp",[]))>1 else 0
            res = 0
            if "Add" in step or "ALU Add" in step:
                if len(ops)>=2:
                    ra = ops[0].upper(); rb = ops[1].upper()
                    va = regs.get(ra,0); vb = regs.get(rb,0)
                else:
                    va = state.get("temp",[0])[0]; vb = 0
                res = (va + vb) & 0xFFFFFFFF
            elif "Sub" in step or "ALU Sub" in step or "ALU Subtract" in step:
                if len(ops)>=2:
                    ra = ops[0].upper(); rb = ops[1].upper()
                    res = (regs.get(ra,0) - regs.get(rb,0)) & 0xFFFFFFFF
                else:
                    res = 0
            elif "Mul" in step or "Multiply" in step:
                if len(ops)>=2:
                    ra = ops[0].upper(); rb = ops[1].upper()
                    res = (regs.get(ra,0) * regs.get(rb,0)) & 0xFFFFFFFF
                else:
                    res = 0
            elif "Compare" in step or "ALU Compare" in step:
                if len(ops)>=2:
                    ra = ops[0].upper(); rb = ops[1].upper()
                    v = regs.get(ra,0) - regs.get(rb,0)
                    set_flag(regs, "Z", 1 if v==0 else 0)
                    set_flag(regs, "S", 1 if v<0 else 0)
                res = None
            elif "AND" in step:
                if len(ops)>=2:
                    ra = ops[0].upper(); rb = ops[1].upper()
                    res = regs.get(ra,0) & regs.get(rb,0)
            state["alu_result"] = res
            if isinstance(res,int):
                set_flag(regs, "Z", 1 if res==0 else 0)
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Memory Read" in step:
            addr = None
            if ops:
                a = ops[-1]
                if a.startswith("[") and a.endswith("]"):
                    try:
                        addr = int(a.strip("[]"),0)
                    except:
                        addr = 0
            if addr is None:
                addr = 0
            readv = mem[addr] if 0 <= addr < len(mem) else 0
            state["temp"] = [readv]
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Memory Write" in step:
            addr = 0
            if ops:
                a = ops[-1]
                if a.startswith("[") and a.endswith("]"):
                    try:
                        addr = int(a.strip("[]"),0)
                    except:
                        addr = 0
            val = state.get("alu_result", state.get("temp",[0])[0] if state.get("temp") else 0)
            if 0 <= addr < len(mem):
                mem[addr] = val & 0xFF
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Set Flags" in step or "Update Flags" in step:
            res = state.get("alu_result", None)
            if res is not None:
                set_flag(regs, "Z", 1 if res==0 else 0)
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Normalize" in step or "Adjust" in step:
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        elif "Calculate Addr" in step:
            addr = 0
            if ops:
                a = ops[-1]
                if a.startswith("[") and a.endswith("]"):
                    try:
                        addr = int(a.strip("[]"),0)
                    except:
                        addr = 0
            state["temp"] = [addr]
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
        else:
            state["cycle_count"] += 1
            yield (step, snapshot_state(state))
    return

def set_flag(regs, flag, value):
    if "FLAGS" in regs and flag in regs["FLAGS"]:
        regs["FLAGS"][flag] = 1 if value else 0

def snapshot_state(state):
    regs = state["registers"]
    mem_preview = state["memory"][:16]
    # shallow copy
    regs_copy = regs.copy() if isinstance(regs, dict) else dict(regs)
    flags_copy = regs.get("FLAGS", {}).copy() if isinstance(regs, dict) and "FLAGS" in regs else {}
    return {"registers": regs_copy, "flags": flags_copy, "PC": regs.get("PC", regs.get("IP", regs.get("PC",0))),
            "cycle_count": state.get("cycle_count",0), "mem_preview": mem_preview, "alu_result": state.get("alu_result", None)}

class InstructionSimulatorFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # states
        self.left_state = None
        self.right_state = None
        self.running_thread = None
        self.run_flag = False

        # layout
        self._build_top_controls()
        self._build_center_visuals()
        self._build_right_state_panels()
        self._reset_states()

    def _reset_states(self):
        self.left_state = {"cpu":"8085", "registers": make_registers_for("8085"), "memory": make_memory(256), "cycle_count":0, "temp":[], "alu_result":None}
        self.right_state = {"cpu":"ARM", "registers": make_registers_for("ARM"), "memory": make_memory(256), "cycle_count":0, "temp":[], "alu_result":None}
        self.update_state_panels()
        self.log_clear()

    def _build_top_controls(self):
        frm = tk.Frame(self)
        frm.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        tk.Label(frm, text="Primary CPU:").grid(row=0, column=0, padx=4)
        self.cpu_var = tk.StringVar(value="8085")
        self.cpu_choice = ttk.Combobox(frm, textvariable=self.cpu_var, values=list(INSTRUCTION_DB.keys()), width=8)
        self.cpu_choice.grid(row=0, column=1)
        self.cpu_choice.bind("<<ComboboxSelected>>", self._on_cpu_change)

        tk.Label(frm, text="Instruction:").grid(row=0, column=2, padx=4)
        self.instr_var = tk.StringVar()
        self.instr_choice = ttk.Combobox(frm, textvariable=self.instr_var, width=20)
        self.instr_choice.grid(row=0, column=3, padx=4)

        tk.Label(frm, text="Operands (comma separated):").grid(row=0, column=4, padx=4)
        self.oper_entry = tk.Entry(frm, width=18)
        self.oper_entry.grid(row=0, column=5, padx=4)

        tk.Button(frm, text="Decode", command=self.decode_primary).grid(row=0, column=6, padx=4)
        tk.Button(frm, text="Step", command=self.step_primary).grid(row=0, column=7, padx=4)
        tk.Button(frm, text="Run", command=self.run_primary).grid(row=0, column=8, padx=4)
        tk.Button(frm, text="Reset", command=self.reset_all).grid(row=0, column=9, padx=4)

        tk.Label(frm, text="Breakpoint PC:").grid(row=1, column=0, padx=4, pady=6)
        self.bp_entry = tk.Entry(frm, width=8)
        self.bp_entry.grid(row=1, column=1, padx=4)
        tk.Button(frm, text="Set BP", command=self.set_breakpoint).grid(row=1, column=2, padx=4)

        self.compare_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="Comparison Mode (Left:Primary, Right:Compare)", variable=self.compare_var, command=self._on_compare_toggle).grid(row=1, column=3, columnspan=4, sticky="w")

        self._populate_instr_list()

    def _on_compare_toggle(self):
        if self.compare_var.get():
            self.right_state = {"cpu":"ARM", "registers": make_registers_for("ARM"), "memory": make_memory(256), "cycle_count":0, "temp":[], "alu_result":None}
        else:
            self.right_state = None
        self.update_state_panels()
        self.log_clear()

    def _on_cpu_change(self, event=None):
        self._populate_instr_list()

    def _populate_instr_list(self):
        cpu = self.cpu_var.get()
        db = INSTRUCTION_DB.get(cpu, {})
        values = [info[0] for key, info in db.items()]
        self.instr_choice["values"] = values
        if values:
            self.instr_choice.current(0)

    def _build_center_visuals(self):
        center = tk.Frame(self)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        log_frame = tk.LabelFrame(center, text="Micro-op Log / Timeline")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.log_text = tk.Text(log_frame, height=12, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Matplotlib timeline (if matplotlib available use it, else still create fig object)
        if HAS_MATPLOTLIB:
            self.fig, self.ax = plt.subplots(figsize=(6,2))
            self.canvas = FigureCanvasTkAgg(self.fig, master=center)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=False, padx=4, pady=4)
        else:
            self.fig, self.ax, self.canvas = None, None, None
            lbl = tk.Label(center, text="matplotlib not available: timeline disabled")
            lbl.pack(pady=8)

        perf_frame = tk.Frame(center)
        perf_frame.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(perf_frame, text="Cycles:").grid(row=0,column=0,sticky="w")
        self.cycles_var = tk.StringVar(value="0")
        tk.Label(perf_frame, textvariable=self.cycles_var).grid(row=0,column=1,sticky="w", padx=4)
        tk.Label(perf_frame, text="Instruction Latency (cycles):").grid(row=0,column=2,sticky="w")
        self.latency_var = tk.StringVar(value="-")
        tk.Label(perf_frame, textvariable=self.latency_var).grid(row=0,column=3,sticky="w", padx=4)

    def _build_right_state_panels(self):
        right = tk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=6, pady=6)

        self.left_panel = tk.LabelFrame(right, text="Primary State (Left)")
        self.left_panel.pack(fill=tk.X, padx=4, pady=4)
        self.left_regs_text = tk.Text(self.left_panel, height=10, width=40, state="disabled")
        self.left_regs_text.pack(padx=4, pady=4)

        self.right_panel = tk.LabelFrame(right, text="Compare State (Right)")
        self.right_panel.pack(fill=tk.X, padx=4, pady=4)
        self.right_regs_text = tk.Text(self.right_panel, height=10, width=40, state="disabled")
        self.right_regs_text.pack(padx=4, pady=4)

    def decode_primary(self):
        mnemonic = self.instr_var.get().strip()
        operands = self.oper_entry.get().strip()
        instr_text = mnemonic + (" " + operands if operands else "")
        decoded = decode_instruction_instance(self.cpu_var.get(), instr_text)
        if not decoded:
            messagebox.showerror("Decode Error", f"Cannot decode instruction: {instr_text}")
            return
        self.left_state["cpu"] = self.cpu_var.get()
        self.left_state["instr_instance"] = decoded
        self.left_state["generator"] = fsm_execute_instruction(self.left_state, decoded)
        self.left_state["start_cycle"] = self.left_state.get("cycle_count",0)
        if self.compare_var.get():
            right_cpu = self.right_state["cpu"] if self.right_state else "ARM"
            decoded_r = decode_instruction_instance(right_cpu, instr_text)
            if decoded_r:
                self.right_state["instr_instance"] = decoded_r
                self.right_state["generator"] = fsm_execute_instruction(self.right_state, decoded_r)
                self.right_state["start_cycle"] = self.right_state.get("cycle_count",0)
        self.log(f"Decoded: {instr_text}")
        self.update_state_panels()
        self.draw_timeline_empty()

    def step_primary(self):
        if not self.left_state.get("generator"):
            messagebox.showinfo("Info", "Decode an instruction first")
            return
        try:
            m, snap = next(self.left_state["generator"])
            self.log(f"[Left] {m}  (Cycle {snap['cycle_count']})")
            self.update_state_panels()
            self.cycles_var.set(str(self.left_state.get("cycle_count",0)))
            self.draw_timeline_from_state(self.left_state)
        except StopIteration:
            self.log("[Left] Instruction completed")
            latency = self.left_state.get("cycle_count",0) - self.left_state.get("start_cycle",0)
            self.latency_var.set(str(latency))
        if self.compare_var.get() and self.right_state and self.right_state.get("generator"):
            try:
                m2, snap2 = next(self.right_state["generator"])
                self.log(f"[Right] {m2}  (Cycle {snap2['cycle_count']})")
                self.update_state_panels()
                self.draw_timeline_from_state(self.right_state, right_side=True)
            except StopIteration:
                self.log("[Right] Instruction completed")

    def run_primary(self):
        if not self.left_state.get("generator"):
            messagebox.showinfo("Info", "Decode an instruction first")
            return
        self.run_flag = True
        def run_loop():
            while self.run_flag:
                bp = self.get_breakpoint()
                pc = self.left_state["registers"].get("PC", self.left_state["registers"].get("IP",0))
                if bp is not None and pc == bp:
                    self.log(f"[Left] Breakpoint hit at PC={bp}")
                    break
                try:
                    m, snap = next(self.left_state["generator"])
                    self.log(f"[Left] {m}  (Cycle {snap['cycle_count']})")
                    self.update_state_panels()
                    self.cycles_var.set(str(self.left_state.get("cycle_count",0)))
                    self.draw_timeline_from_state(self.left_state)
                except StopIteration:
                    self.log("[Left] Instruction completed")
                    latency = self.left_state.get("cycle_count",0) - self.left_state.get("start_cycle",0)
                    self.latency_var.set(str(latency))
                    break
                if self.compare_var.get() and self.right_state and self.right_state.get("generator"):
                    try:
                        m2, snap2 = next(self.right_state["generator"])
                        self.log(f"[Right] {m2}  (Cycle {snap2['cycle_count']})")
                        self.draw_timeline_from_state(self.right_state, right_side=True)
                    except StopIteration:
                        self.log("[Right] Instruction completed")
                time.sleep(0.4)
        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

    def reset_all(self):
        self._reset_states()
        self.draw_timeline_empty()
        self.cycles_var.set("0")
        self.latency_var.set("-")
        self.run_flag = False

    def set_breakpoint(self):
        val = self.bp_entry.get().strip()
        try:
            bp = int(val,0)
            self.left_state["breakpoint"] = bp
            self.log(f"Breakpoint set at {bp}")
        except:
            messagebox.showerror("Error", "Invalid breakpoint value")

    def get_breakpoint(self):
        try:
            return self.left_state.get("breakpoint", None)
        except:
            return None

    def log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def log_clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")

    def update_state_panels(self):
        self.left_regs_text.configure(state="normal")
        self.left_regs_text.delete("1.0","end")
        self.left_regs_text.insert("end", self._format_state_text(self.left_state))
        self.left_regs_text.configure(state="disabled")
        if self.compare_var.get() and self.right_state:
            self.right_regs_text.configure(state="normal")
            self.right_regs_text.delete("1.0","end")
            self.right_regs_text.insert("end", self._format_state_text(self.right_state))
            self.right_regs_text.configure(state="disabled")
        else:
            self.right_regs_text.configure(state="normal")
            self.right_regs_text.delete("1.0","end")
            self.right_regs_text.insert("end", "(Comparison disabled)")
            self.right_regs_text.configure(state="disabled")

    def _format_state_text(self, st):
        regs = st["registers"]
        s = f"CPU: {st.get('cpu')}\nCycles: {st.get('cycle_count',0)}\n"
        if "PC" in regs:
            s += f"PC: {regs.get('PC')}\n"
        if "IP" in regs:
            s += f"IP: {regs.get('IP')}\n"
        s += "Registers:\n"
        for k,v in regs.items():
            if k=="FLAGS": continue
            s += f"  {k}: {v}\n"
        s += "FLAGS:\n"
        flags = regs.get("FLAGS",{})
        for fk,fv in flags.items():
            s += f"  {fk}: {fv}  "
        s += "\nMemory (first 16 addresses):\n"
        mem = st["memory"][:16]
        s += " ".join([f"{x:02X}" for x in mem])
        return s

    def draw_timeline_empty(self):
        if HAS_MATPLOTLIB and self.ax:
            self.ax.clear()
            self.ax.set_title("Timeline (no instruction)")
            self.ax.set_yticks([])
            self.canvas.draw()

    def draw_timeline_from_state(self, st, right_side=False):
        if not (HAS_MATPLOTLIB and self.ax):
            return
        start = st.get("start_cycle",0)
        count = st.get("cycle_count",0) - start
        self.ax.clear()
        self.ax.set_xlim(0, max(6,count+2))
        self.ax.set_ylim(-1,2)
        self.ax.set_yticks([])
        for i in range(count):
            # don't set specific colors/styles beyond defaults
            self.ax.barh(0, 1, left=i, height=0.5, edgecolor='black')
            try:
                lines = self.log_text.get("1.0","end").strip().splitlines()
                labels = [ln for ln in lines if ("[Left]" in ln and not right_side) or ("[Right]" in ln and right_side)]
                lbl = labels[i] if i < len(labels) else ""
                self.ax.text(i+0.5, 0, lbl.split("]",1)[-1][:18].strip(), ha='center', va='center', fontsize=8, rotation=0)
            except:
                pass
        self.ax.set_xlabel("Clock Cycles")
        self.canvas.draw()

# -----------------------------------------------------------
# Module 2 content (BusSim) converted to Frame
# -----------------------------------------------------------

HEX16 = lambda v: f"0x{v & 0xFFFF:04X}"
HEX8 = lambda v: f"0x{v & 0xFF:02X}"

class MemoryModel:
    def __init__(self, size=65536):
        self.size = size
        self.store = {}

    def read(self, addr):
        addr &= 0xFFFF
        return self.store.get(addr, 0)

    def write(self, addr, data):
        addr &= 0xFFFF
        self.store[addr] = data & 0xFF

    def dump_range(self, start, count=16):
        out = []
        for i in range(count):
            a = (start + i) & 0xFFFF
            out.append((a, self.store.get(a, 0)))
        return out

class BusModel:
    def __init__(self):
        self.address = 0
        self.data = None
        self.ctrl = {"RD": 0, "WR": 0, "MEM": 0, "IO": 0}
        self.driver = None

    def reset(self):
        self.address = 0
        self.data = None
        self.ctrl = {"RD": 0, "WR": 0, "MEM": 0, "IO": 0}
        self.driver = None

class BusSimFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.mem = MemoryModel()
        self.bus = BusModel()
        self.start_time = time.time()
        self._build_ui()
        self._refresh_canvas()

    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        ctrl_frame = ttk.Frame(paned, padding=10)
        paned.add(ctrl_frame, weight=1)

        ttk.Label(ctrl_frame, text="Address (hex):").pack(anchor="w")
        self.addr_entry = ttk.Entry(ctrl_frame)
        self.addr_entry.pack(fill="x")

        ttk.Label(ctrl_frame, text="Data (hex):").pack(anchor="w")
        self.data_entry = ttk.Entry(ctrl_frame)
        self.data_entry.pack(fill="x")

        ttk.Label(ctrl_frame, text="Operation:").pack(anchor="w", pady=(10,0))
        self.op = tk.StringVar(value="READ")
        ttk.Radiobutton(ctrl_frame, text="READ", variable=self.op, value="READ").pack(anchor="w")
        ttk.Radiobutton(ctrl_frame, text="WRITE", variable=self.op, value="WRITE").pack(anchor="w")

        ttk.Button(ctrl_frame, text="Step Transfer", command=self.step_transfer).pack(pady=10, fill="x")

        ttk.Separator(ctrl_frame).pack(fill="x", pady=8)

        ttk.Label(ctrl_frame, text="Memory Inspector").pack(anchor="w")
        self.inspect_entry = ttk.Entry(ctrl_frame)
        self.inspect_entry.insert(0, "0x0000")
        self.inspect_entry.pack(fill="x")
        ttk.Button(ctrl_frame, text="Dump 16 bytes", command=self.dump_memory).pack(pady=4, fill="x")

        self.mem_text = tk.Text(ctrl_frame, height=10, width=30)
        self.mem_text.pack(fill="both", expand=True, pady=(5,0))

        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        self.canvas = tk.Canvas(right, height=300, bg="#0B1220")
        self.canvas.pack(fill="x", padx=5, pady=5)

        ttk.Label(right, text="Transfer Log").pack(anchor="w")
        cols = ("Time", "Addr", "Data", "Op", "Driver")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, addr, data, op, who):
        t = f"{time.time()-self.start_time:6.3f}"
        self.tree.insert("", "end",
                         values=(t, HEX16(addr), "-" if data is None else HEX8(data), op, who))
        self.tree.see(self.tree.get_children()[-1])

    def _refresh_canvas(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 300
        h = c.winfo_height() or 120
        margin = 20
        mid = h // 2

        c.create_line(margin, mid-40, w-margin, mid-40, width=4, fill="#7F9CB0")
        c.create_text(margin+5, mid-55, anchor="nw", fill="white",
                      text=f"ADDR={HEX16(self.bus.address)}")

        col = "#7F9CB0" if self.bus.data is None else "#22C55E"
        c.create_line(margin, mid, w-margin, mid, width=6, fill=col)
        dtxt = "(Z)" if self.bus.data is None else HEX8(self.bus.data)
        c.create_text(margin+5, mid+5, anchor="nw", fill="white",
                      text=f"DATA={dtxt}")

        ctrl_text = " ".join([f"{k}={v}" for k,v in self.bus.ctrl.items()])
        c.create_text(margin+5, mid+35, anchor="nw", fill="yellow",
                      text=f"CTRL: {ctrl_text}")

        self.after(500, self._refresh_canvas)

    def step_transfer(self):
        try:
            addr = int(self.addr_entry.get(), 16)
        except:
            messagebox.showerror("Error", "Invalid address")
            return

        if self.op.get() == "WRITE":
            try:
                data = int(self.data_entry.get(), 16)
            except:
                messagebox.showerror("Error", "Invalid data")
                return
            self.bus.address = addr
            self.bus.data = data
            self.bus.ctrl = {"RD": 0, "WR": 1, "MEM": 1, "IO": 0}
            self.bus.driver = "CPU"
            self.mem.write(addr, data)
            self.log(addr, data, "WRITE", "CPU")
        else:
            self.bus.address = addr
            data = self.mem.read(addr)
            self.bus.data = data
            self.bus.ctrl = {"RD": 1, "WR": 0, "MEM": 1, "IO": 0}
            self.bus.driver = "MEM"
            self.log(addr, data, "READ", "MEM")

    def dump_memory(self):
        try:
            start = int(self.inspect_entry.get(), 16)
        except:
            messagebox.showerror("Error", "Invalid address")
            return
        rows = self.mem.dump_range(start, 16)
        self.mem_text.delete("1.0", "end")
        for a, d in rows:
            self.mem_text.insert("end", f"{HEX16(a)} : {HEX8(d)}\n")

# -----------------------------------------------------------
# Module 3 content (Profiler) converted to Frame
# -----------------------------------------------------------

# Minimal ISA (same as provided)
class SimpleISA:
    def __init__(self):
        self.registers = {"A": 0, "B": 0}
        self.memory = [0] * 256
        self.pc = 0
        self.program = []

    def load_program(self, prog):
        self.program = [p.strip() for p in prog]
        self.pc = 0
        self.registers = {"A": 0, "B": 0}

    def step(self):
        if self.pc >= len(self.program):
            return "HALT"
        instr = self.program[self.pc]
        self.pc += 1
        t = instr.upper()
        if t.startswith("LDA"):
            parts = instr.split()
            if len(parts) >= 2:
                try:
                    self.registers["A"] = int(parts[1])
                except:
                    pass
            return f"A={self.registers['A']} B={self.registers['B']}"
        if t.startswith("LDB"):
            parts = instr.split()
            if len(parts) >= 2:
                try:
                    self.registers["B"] = int(parts[1])
                except:
                    pass
            return f"A={self.registers['A']} B={self.registers['B']}"
        if t == "ADD":
            self.registers["A"] = self.registers["A"] + self.registers["B"]
            return f"A={self.registers['A']} B={self.registers['B']}"
        if t == "SUB":
            self.registers["A"] = self.registers["A"] - self.registers["B"]
            return f"A={self.registers['A']} B={self.registers['B']}"
        if t == "OUT":
            return f"OUTPUT: {self.registers['A']}"
        return f"UNKNOWN: {instr}"

class ProfilerBus:
    def __init__(self, width=8, latency=1):
        self.width = max(8, int(width))
        self.latency = max(0, int(latency))

    def transfer_cycles(self, size_bytes):
        bytes_per_transfer = max(1, self.width // 8)
        chunks = math.ceil(size_bytes / bytes_per_transfer)
        return chunks * self.latency

def run_profiler(bus):
    return {
        "Simple loop": 100,
        "Memory bound": 100 + bus.transfer_cycles(64),
        "Compute bound": 200,
    }

class ProfilerFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.isa = SimpleISA()
        self.bus = ProfilerBus()
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        top = ttk.Frame(container)
        top.pack(fill="x")
        ttk.Label(top, text="Mode:").pack(side="left")
        self.mode_var = tk.StringVar(value="Instruction Execution")
        self.mode_menu = ttk.Combobox(
            top,
            textvariable=self.mode_var,
            values=["Instruction Execution", "Bus Designer", "Architecture Profiler"],
            state="readonly",
        )
        self.mode_menu.pack(side="left", fill="x", expand=True, padx=6)
        self.mode_menu.bind("<<ComboboxSelected>>", self.update_inputs)

        self.input_frame = ttk.Frame(container)
        self.input_frame.pack(fill="x", pady=6)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x")
        self.run_btn = ttk.Button(btn_frame, text="Run", command=self.run)
        self.run_btn.pack(side="left")
        ttk.Button(btn_frame, text="Clear Output", command=self.clear_output).pack(side="left", padx=6)

        self.output = scrolledtext.ScrolledText(container, height=15)
        self.output.pack(fill="both", expand=True, pady=6)

        self.plot_frame = ttk.Frame(container)
        self.plot_frame.pack(fill="both", expand=False)
        self.canvas_widget = None

        self.update_inputs()

    def update_inputs(self, event=None):
        for w in self.input_frame.winfo_children():
            w.destroy()
        mode = self.mode_var.get()
        if mode == "Instruction Execution":
            ttk.Label(self.input_frame, text="Program (comma-separated, e.g. LDA 5,LDB 3,ADD,OUT):").pack(anchor="w")
            self.prog_entry = ttk.Entry(self.input_frame)
            self.prog_entry.insert(0, "LDA 5,LDB 3,ADD,OUT")
            self.prog_entry.pack(fill="x")
        elif mode == "Bus Designer":
            ttk.Label(self.input_frame, text="Bus width (bits):").pack(anchor="w")
            self.bus_width = ttk.Entry(self.input_frame)
            self.bus_width.insert(0, "8")
            self.bus_width.pack(fill="x")
            ttk.Label(self.input_frame, text="Latency (cycles per transfer):").pack(anchor="w")
            self.bus_latency = ttk.Entry(self.input_frame)
            self.bus_latency.insert(0, "1")
            self.bus_latency.pack(fill="x")
            ttk.Label(self.input_frame, text="Transfer size (bytes):").pack(anchor="w")
            self.transfer_size = ttk.Entry(self.input_frame)
            self.transfer_size.insert(0, "16")
            self.transfer_size.pack(fill="x")
        else:
            ttk.Label(self.input_frame, text="Profiler bus width (bits):").pack(anchor="w")
            self.prof_width = ttk.Entry(self.input_frame)
            self.prof_width.insert(0, "8")
            self.prof_width.pack(fill="x")
            ttk.Label(self.input_frame, text="Profiler latency (cycles per transfer):").pack(anchor="w")
            self.prof_latency = ttk.Entry(self.input_frame)
            self.prof_latency.insert(0, "1")
            self.prof_latency.pack(fill="x")

    def clear_output(self):
        self.output.delete("1.0", "end")
        if self.canvas_widget:
            try:
                self.canvas_widget.get_tk_widget().destroy()
            except Exception:
                pass
            self.canvas_widget = None

    def run(self):
        self.clear_output()
        mode = self.mode_var.get()
        if mode == "Instruction Execution":
            prog_text = self.prog_entry.get()
            prog = [p.strip() for p in prog_text.split(",") if p.strip()]
            self.isa.load_program(prog)
            steps = 0
            while True:
                res = self.isa.step()
                if res == "HALT":
                    self.output.insert("end", "HALT\n")
                    break
                self.output.insert("end", res + "\n")
                steps += 1
                if steps > 500:
                    self.output.insert("end", "-- stopped (max steps)\n")
                    break
        elif mode == "Bus Designer":
            try:
                width = int(self.bus_width.get())
                lat = int(self.bus_latency.get())
                size = int(self.transfer_size.get())
            except Exception:
                self.output.insert("end", "Invalid bus parameters\n")
                return
            bus = ProfilerBus(width, lat)
            cycles = bus.transfer_cycles(size)
            self.output.insert("end", f"Transfer {size} bytes -> {cycles} cycles (width={width} bits, latency={lat})\n")
        else:
            try:
                width = int(self.prof_width.get())
                lat = int(self.prof_latency.get())
            except Exception:
                self.output.insert("end", "Invalid profiler bus parameters\n")
                return
            bus = ProfilerBus(width, lat)
            results = run_profiler(bus)
            for k, v in results.items():
                self.output.insert("end", f"{k}: {v} cycles\n")

            if HAS_MATPLOTLIB:
                keys = list(results.keys())
                vals = list(results.values())
                fig = plt.Figure(figsize=(5, 2.5))
                ax = fig.add_subplot(111)
                ax.bar(keys, vals)
                ax.set_ylabel("Cycles")
                ax.set_title("Profiler")
                if self.canvas_widget:
                    try:
                        self.canvas_widget.get_tk_widget().destroy()
                    except Exception:
                        pass
                self.canvas_widget = FigureCanvasTkAgg(fig, master=self.plot_frame)
                self.canvas_widget.draw()
                self.canvas_widget.get_tk_widget().pack(fill="both", expand=True)
            else:
                self.output.insert("end", "\nmatplotlib is not installed — install it to see embedded plots:\n    pip install matplotlib\n")

# -----------------------------------------------------------
# Main application with Notebook
# -----------------------------------------------------------

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Architecture Simulation Suite")
        self.geometry("1200x800")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        instr_tab = InstructionSimulatorFrame(notebook)
        notebook.add(instr_tab, text="Instruction Cycle Explorer")

        bus_tab = BusSimFrame(notebook)
        notebook.add(bus_tab, text="Bus & Memory Transfer Lab")

        prof_tab = ProfilerFrame(notebook)
        notebook.add(prof_tab, text="Architecture Profiler & Benchmark")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
