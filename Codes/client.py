import socket
import struct
import time
import argparse
import random

class TinyTelemetryClient:
    # Protocol constants
    PROTOCOL_VERSION = 1
    MSG_DATA = 0
    MSG_HEARTBEAT = 1
    MSG_INIT = 2

    # Sensor types
    SENSOR_TEMPERATURE = 0
    SENSOR_HUMIDITY = 1
    SENSOR_VOLTAGE = 2

    # Unit mapping
    UNIT_CELSIUS = 0
    UNIT_PERCENT = 2
    UNIT_VOLTS = 3

    HEADER_SIZE = 12
    MAX_PACKET_SIZE = 200

    # ----------------------------------------------------------------------
    def __init__(self, server_ip="192.168.100.37", server_port=5005,
                 device_id=1, interval=1.0, batch=False, checksum=False):
        self.server_ip = server_ip
        self.server_port = server_port
        self.device_id = device_id
        self.interval = interval          # reporting interval (Phase 2 requirement)
        self.batch_mode = batch
        self.checksum_mode = checksum
        self.sock = None
        self.sequence_num = 0
        self.connected = False

    # ----------------------------------------------------------------------
    def connect(self):
        """UDP connect (no handshake, just sets destination)."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.connect((self.server_ip, self.server_port))
            self.connected = True
            print(f"[INFO] UDP client ready -> {self.server_ip}:{self.server_port}")
        except Exception as e:
            print(f"[ERROR] Could not create UDP socket: {e}")
            self.connected = False

    # ----------------------------------------------------------------------
    def disconnect(self):
        if self.sock:
            self.sock.close()
        self.connected = False
        print("[INFO] UDP client closed.")

    # ----------------------------------------------------------------------
    def build_header(self, msg_type, flags):
        """Build 12-byte header."""
        vertype = (self.PROTOCOL_VERSION << 4) | (msg_type & 0x0F)
        timestamp = int(time.time())
        return struct.pack("!B H I I B",
                           vertype,
                           self.device_id,
                           self.sequence_num,
                           timestamp,
                           flags)

    # ----------------------------------------------------------------------
    def get_unit(self, sensor_type):
        return {
            self.SENSOR_TEMPERATURE: self.UNIT_CELSIUS,
            self.SENSOR_HUMIDITY: self.UNIT_PERCENT,
            self.SENSOR_VOLTAGE: self.UNIT_VOLTS
        }.get(sensor_type, 0)

    # ----------------------------------------------------------------------
    def calc_checksum(self, type_unit, value):
        return (sum(struct.pack("!Bf", type_unit, float(value))) % 256)

    # ----------------------------------------------------------------------
    def build_single_payload(self, sensor_type, value):
        """Build 5-byte or 6-byte single payload."""
        type_unit = (sensor_type << 4) | self.get_unit(sensor_type)

        if self.checksum_mode:
            chk = self.calc_checksum(type_unit, value)
            payload = struct.pack("!BfB", type_unit, float(value), chk)
            flags = 4       # checksum flag
        else:
            payload = struct.pack("!Bf", type_unit, float(value))
            flags = 0

        return payload, flags

    # ----------------------------------------------------------------------
    def build_batch_payload(self, sensor_type, values):
        """Build batched payload."""
        flags = 1                  # batch flag
        if self.checksum_mode:
            flags |= 4             # checksum flag

        type_unit = (sensor_type << 4) | self.get_unit(sensor_type)
        payload = bytearray([len(values)])

        for v in values:
            if self.checksum_mode:
                chk = self.calc_checksum(type_unit, v)
                payload += struct.pack("!BfB", type_unit, float(v), chk)
            else:
                payload += struct.pack("!Bf", type_unit, float(v))

        return bytes(payload), flags

    # ----------------------------------------------------------------------
    def send_packet(self, msg_type, payload=b"", flags=0):
        """Send packet with header + payload."""
        if not self.connected:
            print("[ERROR] Cannot send: client not connected.")
            return

        header = self.build_header(msg_type, flags)
        packet = header + payload

        if len(packet) > self.MAX_PACKET_SIZE:
            print(f"[ERROR] Packet too large ({len(packet)} bytes). Skipped.")
            return

        try:
            self.sock.send(packet)
            print(f"[SEND] {['DATA','HEARTBEAT','INIT'][msg_type]} seq={self.sequence_num}, size={len(packet)}")
        except Exception as e:
            print(f"[ERROR] send() failed: {e}")
            self.disconnect()
            return

        self.sequence_num += 1

    # ----------------------------------------------------------------------
    def send_init(self):
        """Send INIT (always seq=0)."""
        self.sequence_num = 0
        self.send_packet(self.MSG_INIT)

    # ----------------------------------------------------------------------
    def send_sensor_data(self, sensor_type, readings):
        """Send DATA packet (single or batch)."""
        if not self.batch_mode or len(readings) == 1:
            payload, flags = self.build_single_payload(sensor_type, readings[0])
        else:
            payload, flags = self.build_batch_payload(sensor_type, readings)

        self.send_packet(self.MSG_DATA, payload, flags)

    # ----------------------------------------------------------------------
    def send_heartbeat(self):
        self.send_packet(self.MSG_HEARTBEAT)

    # ----------------------------------------------------------------------
    # 🔥 PHASE-2 FEATURE: Continuous periodic reporting loop
    # ----------------------------------------------------------------------
    def generate_sensor_values(self, sensor_type):
        if sensor_type == self.SENSOR_TEMPERATURE:
            base = random.uniform(-1.0, 48.0)
            return base + random.gauss(0, 0.3)

        if sensor_type == self.SENSOR_HUMIDITY:
            base = random.uniform(20.0, 70.0)
            return max(30.0, min(90.0, base + random.gauss(0, 2)))

        if sensor_type == self.SENSOR_VOLTAGE:
            return 3.3 + random.gauss(0, 0.02)

    def start_reporting(self, sensor_type=SENSOR_TEMPERATURE):
        print(f"[INFO] Starting telemetry reporting every {self.interval} sec")
        print(f"[INFO] Mode: {'BATCH' if self.batch_mode else 'SINGLE'} | Checksum: {self.checksum_mode}")

        try:
            self.send_init()
            time.sleep(0.5)

            while True:
                if self.batch_mode:
                    batch_size = random.randint(3, 8)
                    readings = [self.generate_sensor_values(sensor_type) for _ in range(batch_size)]
                else:
                    readings = [self.generate_sensor_values(sensor_type)]

                self.send_sensor_data(sensor_type, readings)

                # send heartbeat every 10 packets
                if self.sequence_num % 10 == 0:
                    self.send_heartbeat()

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n[INFO] Stopping client...")
            self.disconnect()


# ----------------------------------------------------------------------
# Example usage for Phase 2
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--device", type=int, default=99)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--checksum", action="store_true")

    args = parser.parse_args()

    client = TinyTelemetryClient(
        server_ip=args.ip,
        server_port=args.port,
        device_id=args.device,
        interval=args.interval,
        batch=args.batch,
        checksum=args.checksum
    )

    client.connect()
    client.start_reporting(sensor_type=TinyTelemetryClient.SENSOR_TEMPERATURE)

