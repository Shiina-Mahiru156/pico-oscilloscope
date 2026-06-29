from machine import Pin, ADC
import time
import struct
import sys

try:
    import select
except ImportError:
    import uselect as select

Channels = [
    {"name": "ch1", "pin": 26, "enabled": True},
    {"name": "ch2", "pin": 27, "enabled": True},
    {"name": "ch3", "pin": 28, "enabled": True},
]

Rate = 20000
Rate_pack = 100

adcs = []
for ch in Channels:
    if ch["enabled"]:
        adc = ADC(Pin(ch["pin"]))
        adcs.append({"name": ch["name"], "adc": adc})
        print(f"[INIT] {ch['name']} -> GP{ch['pin']}")

NUM_CH = len(adcs)
BUF_SIZE = NUM_CH * Rate_pack * 2
data_buf = bytearray(BUF_SIZE)

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

def send_packet():
    header = struct.pack('<BBBH', 0xAA, 0x55, NUM_CH, Rate_pack)
    sys.stdout.buffer.write(header + data_buf)

print("=" * 40)
print("Pico Simple Oscilloscope Ready")
print(f"Channels : {NUM_CH}")
print(f"Target   : {Rate} Hz")
print(f"PackSize : {Rate_pack} points")
print("Commands : START | STOP | INFO | REBOOT")
print("=" * 40)

running = False

while True:
    try:
        events = poll.poll(0)
        if events:
            line = sys.stdin.readline()
            if line:
                cmd = line.strip()
                if cmd == "START":
                    running = True
                    print("[OK] Sampling started")
                elif cmd == "STOP":
                    running = False
                    print("[OK] Sampling stopped")
                elif cmd == "INFO":
                    print(f"[INFO] ch:{NUM_CH} rate:{Rate} pack:{Rate_pack}")
                elif cmd == "REBOOT":
                    print("[OK] Rebooting...")
                    time.sleep(0.1)
                    sys.exit()
               
        if running:
            idx = 0
            for _ in range(Rate_pack):
                for ch in adcs:
                    raw = ch["adc"].read_u16()
                    value = raw >> 4
                    data_buf[idx]     = (value >> 8) & 0xFF
                    data_buf[idx + 1] = value & 0xFF
                    idx += 2
            send_packet()
           
    except Exception as e:
        print(f"[ERROR] {e}")
        running = False
        time.sleep(1)
