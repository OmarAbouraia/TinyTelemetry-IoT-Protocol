import socket
import struct
import time
import random

# -----------------------------
# Configuration
# -----------------------------
SERVER_IP = "172.20.10.4"   # 🔸 Change if server IP differs
SERVER_PORT = 5005

PROTOCOL_VERSION = 1
MSG_DATA = 0
DEVICE_ID = 999

# Sensor definitions
SENSOR_TEMPERATURE = 0
UNIT_CELSIUS = 0

HEADER_SIZE = 12
MAX_PACKET_SIZE = 200


# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def build_header(seq, flags):
    """Return 12-byte protocol header"""
    version_type = (PROTOCOL_VERSION << 4) | MSG_DATA
    timestamp = int(time.time())
    header = struct.pack("!B H I I B",
                         version_type,
                         DEVICE_ID,
                         seq,
                         timestamp,
                         flags)
    return header


def build_single_payload(seq, add_checksum=False):
    """Build a single reading payload"""
    type_unit = (SENSOR_TEMPERATURE << 4) | UNIT_CELSIUS
    value = float(seq)  # use sequence number as test value
    if add_checksum:
        checksum = (sum(struct.pack("!Bf", type_unit, value)) % 256)
        payload = struct.pack("!BfB", type_unit, value, checksum)
        flags = 4  # checksum flag
    else:
        payload = struct.pack("!Bf", type_unit, value)
        flags = 0
    return payload, flags


def build_batch_payload(batch_size, add_checksum=False):
    """Build a batched payload with multiple readings"""
    batch = bytearray()
    batch.append(batch_size)
    type_unit = (SENSOR_TEMPERATURE << 4) | UNIT_CELSIUS
    for i in range(batch_size):
        value = 20.0 + i * 0.1
        if add_checksum:
            checksum = (sum(struct.pack("!Bf", type_unit, value)) % 256)
            batch += struct.pack("!BfB", type_unit, value, checksum)
        else:
            batch += struct.pack("!Bf", type_unit, value)
    flags = 1 | (4 if add_checksum else 0)
    return bytes(batch), flags


# -------------------------------------------------
# Individual test routines
# -------------------------------------------------
def send_loss_test(sock, count, rate):
    """Normal sequential sends (baseline for loss detection)"""
    print("\n=== [1] Packet Loss Test ===")
    delay = 1.0 / rate
    for seq in range(count):
        payload, flags = build_single_payload(seq)
        packet = build_header(seq, flags) + payload
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        time.sleep(delay)
    print("[INFO] Loss test done.")


def send_duplicate_test(sock, count, rate):
    """Inject duplicate packets"""
    print("\n=== [2] Duplicate Packet Test ===")
    delay = 1.0 / rate
    for seq in range(count):
        payload, flags = build_single_payload(seq)
        packet = build_header(seq, flags) + payload
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        if seq % 20 == 0:  # send duplicate every 20 packets
            sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        time.sleep(delay)
    print("[INFO] Duplicate test done.")


def send_reorder_test(sock, count, rate):
    """Send packets in random order"""
    print("\n=== [3] Out-of-Order Packet Test ===")
    delay = 1.0 / rate
    packets = []
    for seq in range(count):
        payload, flags = build_single_payload(seq)
        packets.append(build_header(seq, flags) + payload)

    random.shuffle(packets)
    for p in packets:
        sock.sendto(p, (SERVER_IP, SERVER_PORT))
        time.sleep(delay)
    print("[INFO] Reorder test done.")


def send_checksum_test(sock, count, rate):
    """Send packets with valid checksum field"""
    print("\n=== [4] Checksum Test ===")
    delay = 1.0 / rate
    for seq in range(count):
        payload, flags = build_single_payload(seq, add_checksum=True)
        packet = build_header(seq, flags) + payload
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        time.sleep(delay)
    print("[INFO] Checksum test done.")


def send_batch_test(sock, count, rate):
    """Send packets with multiple readings in one payload"""
    print("\n=== [5] Batch Payload Test ===")
    delay = 1.0 / rate
    for seq in range(count):
        batch_size = random.randint(2, 6)
        payload, flags = build_batch_payload(batch_size)
        packet = build_header(seq, flags) + payload
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        time.sleep(delay)
    print("[INFO] Batch test done.")


# -------------------------------------------------
# Master combined test routine
# -------------------------------------------------
def run_all_tests(sock):
    """Run all test modes sequentially"""
    test_config = [
        ("Loss", send_loss_test, 100, 100),
        ("Duplicate", send_duplicate_test, 100, 100),
        ("Reorder", send_reorder_test, 100, 100),
        ("Checksum", send_checksum_test, 100, 100),
        ("Batch", send_batch_test, 50, 50),
    ]

    print("\n========== UDP Telemetry Protocol Combined Test ==========")
    print(f"Target: {SERVER_IP}:{SERVER_PORT}")
    print(f"Device ID: {DEVICE_ID}")
    print("----------------------------------------------------------")

    for name, func, count, rate in test_config:
        print(f"\n>>> Running {name} Test ({count} packets @ {rate} pkt/s)")
        func(sock, count, rate)
        print(f"--- {name} Test Completed ---\n")
        time.sleep(2)  # short pause between tests

    print("\n✅ All tests finished successfully.")
    print("Check your server console for detailed analysis.")


# -------------------------------------------------
# Entry Point
# -------------------------------------------------
if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    run_all_tests(sock)
