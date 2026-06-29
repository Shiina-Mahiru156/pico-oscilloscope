#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import struct
import threading
import sys
import time

SYNC_BYTES = bytes([0xAA, 0x55])
DEFAULT_RATE_PACK = 100
DEFAULT_NUM_CH = 3
COLORS = ["#00ff88", "#00ccff", "#ffaa00"]
BG_COLOR = "#0d0d0d"
GRID_COLOR = "#333333"
LINE_WIDTH = 1.5

class OscilloscopeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pico Simple Oscilloscope")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("900x600")

        self.ser = None
        self.running = False
        self.buffer = bytearray()
        self.data = [[0]*DEFAULT_RATE_PACK for _ in range(DEFAULT_NUM_CH)]
        self.paused = False
        self.frame_count = 0
        self.last_fps_time = 0
        self.fps = 0

        self._build_ui()
        self._find_ports()

    def _build_ui(self):
        ctrl = tk.Frame(self.root, bg=BG_COLOR)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(ctrl, text="Port:", bg=BG_COLOR, fg="white", font=("Consolas", 10)).pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(ctrl, textvariable=self.port_var, width=15, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(ctrl, text="Refresh", command=self._find_ports, bg="#333", fg="white", 
                  font=("Consolas", 10), relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

        self.btn_connect = tk.Button(ctrl, text="Connect", command=self._toggle_connect, 
                                      bg="#00aa44", fg="white", font=("Consolas", 10, "bold"), 
                                      width=10, relief=tk.FLAT)
        self.btn_connect.pack(side=tk.LEFT, padx=10)

        self.lbl_status = tk.Label(ctrl, text="Disconnected", bg=BG_COLOR, fg="#ff6666", 
                                   font=("Consolas", 10))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        self.lbl_fps = tk.Label(ctrl, text="FPS: 0", bg=BG_COLOR, fg="#888888", 
                                font=("Consolas", 10))
        self.lbl_fps.pack(side=tk.RIGHT, padx=10)

        self.canvas = tk.Canvas(self.root, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        info = tk.Frame(self.root, bg=BG_COLOR)
        info.pack(fill=tk.X, padx=10, pady=5)

        self.ch_labels = []
        for i in range(DEFAULT_NUM_CH):
            lbl = tk.Label(info, text=f"CH{i+1}: ----", bg=BG_COLOR, fg=COLORS[i], 
                           font=("Consolas", 11, "bold"))
            lbl.pack(side=tk.LEFT, padx=20)
            self.ch_labels.append(lbl)

        self.root.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._toggle_pause)

        self.root.after(16, self._update_loop)

    def _find_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _on_resize(self, event=None):
        self.width = self.canvas.winfo_width()
        self.height = self.canvas.winfo_height()
        self._draw_grid()

    def _draw_grid(self):
        self.canvas.delete("grid")
        if self.width < 50 or self.height < 50:
            return
        for i in range(1, 10):
            y = self.height * i // 10
            self.canvas.create_line(0, y, self.width, y, fill=GRID_COLOR, tags="grid")
        for i in range(1, 10):
            x = self.width * i // 10
            self.canvas.create_line(x, 0, x, self.height, fill=GRID_COLOR, tags="grid")

    def _toggle_pause(self, event=None):
        self.paused = not self.paused

    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            self.lbl_status.config(text="Select a port", fg="#ff6666")
            return
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.05, write_timeout=1)
            self.ser.reset_input_buffer()
            self.ser.write(b"INFO\n")
            time.sleep(0.1)
            info = self.ser.read(256).decode("utf-8", errors="ignore").strip()
            print("[INFO]", info)
            self.ser.write(b"START\n")
            self.running = True
            self.thread = threading.Thread(target=self._read_thread, daemon=True)
            self.thread.start()
            self.btn_connect.config(text="Disconnect", bg="#aa2222")
            self.lbl_status.config(text=f"Connected {port}", fg="#00ff88")
        except Exception as e:
            self.lbl_status.config(text=f"Connect failed: {e}", fg="#ff6666")

    def _disconnect(self):
        self.running = False
        if self.ser:
            try:
                self.ser.write(b"STOP\n")
                self.ser.close()
            except:
                pass
            self.ser = None
        self.btn_connect.config(text="Connect", bg="#00aa44")
        self.lbl_status.config(text="Disconnected", fg="#ff6666")

    def _read_thread(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting:
                    chunk = self.ser.read(self.ser.in_waiting)
                    self.buffer.extend(chunk)
                self._parse_buffer()
            except Exception as e:
                print("[ERROR]", e)
                break

    def _parse_buffer(self):
        while True:
            idx = self.buffer.find(SYNC_BYTES)
            if idx == -1:
                if self.buffer and self.buffer[-1] == 0xAA:
                    self.buffer = bytearray([0xAA])
                else:
                    self.buffer = bytearray()
                return

            if len(self.buffer) < idx + 5:
                self.buffer = self.buffer[idx:]
                return

            num_ch = self.buffer[idx + 2]
            rate_pack = struct.unpack_from("<H", self.buffer, idx + 3)[0]
            data_len = num_ch * rate_pack * 2
            total_len = 5 + data_len

            if len(self.buffer) < idx + total_len:
                self.buffer = self.buffer[idx:]
                return

            payload = bytes(self.buffer[idx + 5 : idx + 5 + data_len])
            try:
                fmt = f"<{num_ch * rate_pack}H"
                flat = struct.unpack(fmt, payload)
                for ch in range(min(num_ch, DEFAULT_NUM_CH)):
                    for p in range(min(rate_pack, DEFAULT_RATE_PACK)):
                        self.data[ch][p] = flat[p * num_ch + ch]
            except Exception as e:
                print("[PARSE ERR]", e)

            self.buffer = self.buffer[idx + total_len:]

    def _update_loop(self):
        if not self.paused:
            self._draw_waveform()
            self.frame_count += 1

        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = now
            self.lbl_fps.config(text=f"FPS: {self.fps}")

        self.root.after(16, self._update_loop)

    def _draw_waveform(self):
        self.canvas.delete("wave")
        w, h = self.width, self.height
        if w < 50 or h < 50:
            return

        ch_h = h // DEFAULT_NUM_CH
        points = DEFAULT_RATE_PACK

        for ch in range(DEFAULT_NUM_CH):
            y_base = ch * ch_h + ch_h // 2
            scale = (ch_h // 2 - 10) / 4095

            coords = []
            for i in range(points):
                x = i * w // points
                y = y_base - int(self.data[ch][i] * scale)
                coords.extend([x, y])

            if len(coords) >= 4:
                self.canvas.create_line(coords, fill=COLORS[ch], width=LINE_WIDTH, tags="wave", smooth=True)

            last_val = self.data[ch][-1]
            self.ch_labels[ch].config(text=f"CH{ch+1}: {last_val:4d}")

    def on_close(self):
        self._disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = OscilloscopeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
