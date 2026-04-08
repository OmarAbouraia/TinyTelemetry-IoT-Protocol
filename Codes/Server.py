import socket
import struct
import time
import os
import csv

# -----------------------------
# Configuration
# -----------------------------
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MAX_PACKET_SIZE = 200

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# -----------------------------
# Protocol Maps
# -----------------------------
SENSOR_TYPE_MAP = {0: "Temperature", 1: "Humidity", 2: "Voltage"}
UNIT_TYPE_MAP = {0: "C", 2: "%", 3: "V"}
MSG_TYPE_MAP = {0: "DATA", 1: "HEARTBEAT", 2: "INIT"}

# -----------------------------
# Per-device state
# -----------------------------
last_seq = {}
last_timestamp = {}
last_value = {}
prev_value = {}

recv_count = {}
lost_count = {}
dup_count = {}
reorder_count = {}
reset_count = {}

# -----------------------------
# CSV Logging
# -----------------------------
def log_csv(device, seq, timestamp, arrival, duplicate, gap, cpu_ms, bytes_per_report):
    filename = f"{LOG_DIR}/device_{device}.csv"
    new_file = not os.path.isfile(filename)

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow([
                "device_id", "seq", "timestamp",
                "arrival_time", "duplicate_flag", "gap_flag",
                "cpu_ms_per_report", "bytes_per_report"
            ])
        writer.writerow([
            device, seq, timestamp,
            arrival, duplicate, gap,
            cpu_ms, bytes_per_report
        ])

# -----------------------------
# Parsing helpers
# -----------------------------
def parse_header(data):
    if len(data) < 12:
        return None
    try:
        vt, dev, seq, ts, flags = struct.unpack("!B H I I B", data[:12])
    except struct.error:
        return None

    return {
        "msg_type": vt & 0x0F,
        "device_id": dev,
        "seq": seq,
        "timestamp": ts,
        "flags": flags
    }

def parse_payload(payload):
    if len(payload) < 5:
        return []

    t = payload[0]
    value = struct.unpack("!f", payload[1:5])[0]

    return [{
        "sensor": (t >> 4) & 0x0F,
        "unit": t & 0x0F,
        "value": value
    }]

# -----------------------------
# State helpers
# -----------------------------
def ensure_device(dev):
    if dev not in recv_count:
        recv_count[dev] = 0
        lost_count[dev] = 0
        dup_count[dev] = 0
        reorder_count[dev] = 0
        reset_count[dev] = 0
        last_seq[dev] = None
        last_timestamp[dev] = 0
        last_value[dev] = None
        prev_value[dev] = None

def reset_device(dev):
    reset_count[dev] += 1
    last_seq[dev] = None
    last_timestamp[dev] = 0
    last_value[dev] = None
    prev_value[dev] = None

# -----------------------------
# UDP Server
# -----------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"Server listening on UDP {UDP_IP}:{UDP_PORT}")

try:
    while True:
        packet, addr = sock.recvfrom(1024)
        arrival = time.time()

        if len(packet) > MAX_PACKET_SIZE:
            continue

        header = parse_header(packet)
        if not header:
            continue

        dev = header["device_id"]
        seq = header["seq"]
        ts = header["timestamp"]
        msg = header["msg_type"]

        ensure_device(dev)

        print(f"\n[{MSG_TYPE_MAP.get(msg)}] Device={dev} Seq={seq}")

        # INIT handling
        if msg == 2:
            print("[INIT] Device state reset")
            reset_device(dev)
            continue

        cpu_start = time.process_time()
        duplicate = False
        gap = False
        gap_size = 0
        gap_start_seq = None

        # -----------------------------
        # Sequence handling
        # -----------------------------
        if last_seq[dev] is None:
            last_seq[dev] = seq
            recv_count[dev] += 1
        else:
            expected = last_seq[dev] + 1

            if seq == last_seq[dev]:
                dup_count[dev] += 1
                duplicate = True

            elif seq > expected:
                gap_start_seq = expected
                gap_size = seq - expected
                lost_count[dev] += gap_size
                gap = True
                prev_value[dev] = last_value[dev]

            elif seq < last_seq[dev]:
                reorder_count[dev] += 1

            last_seq[dev] = seq
            recv_count[dev] += 1

        # -----------------------------
        # Payload parsing
        # -----------------------------
        readings = parse_payload(packet[12:])
        print(f"Parsed {len(readings)} readings")

        unit_symbol = ""

        for r in readings:
            sensor = SENSOR_TYPE_MAP.get(r["sensor"], "?")
            unit_symbol = UNIT_TYPE_MAP.get(r["unit"], "")
            value = r["value"]
            print(f"  {sensor}: {value:.2f}{unit_symbol}")
            last_value[dev] = value

        # -----------------------------
        # Linear interpolation for loss
        # -----------------------------
        if gap and prev_value[dev] is not None and last_value[dev] is not None:
            v1 = prev_value[dev]
            v2 = last_value[dev]
            step = (v2 - v1) / (gap_size + 1)

            print(f"[LOSS] Detected {gap_size} missing packet(s)")
            for i in range(1, gap_size + 1):
                lost_seq = gap_start_seq + (i - 1)
                est = v1 + step * i
                print(f"\n[LOSS] Device={dev} Seq={lost_seq} (LOST)")
                print(f"  Estimated → {est:.2f}{unit_symbol}")

        # -----------------------------
        # Metrics + CSV
        # -----------------------------
        cpu_ms = (time.process_time() - cpu_start) * 1000
        bytes_per_report = len(packet) / max(len(readings), 1)

        log_csv(dev, seq, ts, arrival, duplicate, gap, cpu_ms, bytes_per_report)

except KeyboardInterrupt:
    print("\n--- Final Statistics ---")
    for dev in recv_count:
        total = recv_count[dev]
        lost = lost_count[dev]
        loss_pct = (lost / (total + lost)) * 100 if (total + lost) else 0
        print(
            f"Device {dev}: received={total}, "
            f"lost={lost}, loss%={loss_pct:.2f}, "
            f"dups={dup_count[dev]}, reorders={reorder_count[dev]}, resets={reset_count[dev]}"
        )

