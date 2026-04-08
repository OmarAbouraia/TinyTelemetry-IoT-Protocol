# 🛰️ TinyTelemetry: Efficient IoT Protocol over UDP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![University: Ain Shams](https://img.shields.io/badge/ASU-Faculty%20of%20Engineering-red)](https://eng.asu.edu.eg/)

[cite_start]**TinyTelemetry** is a custom application-layer protocol designed for resource-constrained IoT devices[cite: 19, 268]. [cite_start]Developed over **UDP**, it prioritizes minimal overhead, deterministic timing, and robustness in lossy network environments[cite: 20, 444, 664].

---

## 📖 Table of Contents
* [Overview](#overview)
* [Protocol Architecture](#protocol-architecture)
* [Key Features](#key-features)
* [Experimental Results](#experimental-results)
* [Getting Started](#getting-started)
* [Reproducing Analysis](#reproducing-analysis)
* [Project Contributors](#project-contributors)

---

## 🔍 Overview
[cite_start]Traditional telemetry (TCP-based) introduces connection delays and retransmission jitter[cite: 446, 671]. [cite_start]**TinyTelemetry** trades strict reliability for simplicity and efficiency using a fixed 12-byte header and optional batching[cite: 447, 675].

### Target Use Case
* [cite_start]**Environment**: Periodic reporting of sensor readings (Temp, Humidity, Voltage)[cite: 19, 303].
* [cite_start]**Constraints**: 5-15% network loss, 200-byte max packet size[cite: 450, 451].

---

## 🏗️ Protocol Architecture
[cite_start]The protocol follows a **Stateless Unidirectional Client-Server Model**[cite: 277, 467, 674].

### Finite State Machine (FSM)
[cite_start]The client transitions through the following states[cite: 469, 779]:
`START` ➡️ `INIT` (Seq 0) ➡️ `REPORTING` (DATA/HB) ➡️ `END`

<p align="center">
  <img src="Assets/Protocol Flowchart.png" alt="Protocol Flowchart" width="600">
  <img src="Assets/Architecture_FSM.png" alt="Client FSM" width="600">
</p>

### Message Structure (12-Byte Header)
| Field | Size | Description |
| :--- | :--- | :--- |
| **Ver/MsgType** | 1 Byte | Upper 4 bits: Version; [cite_start]Lower 4 bits: Type (INIT/DATA/HB)[cite: 287, 471]. |
| **DeviceID** | 2 Bytes | [cite_start]Unique sensor identifier[cite: 288, 474]. |
| **SeqNum** | 4 Bytes | [cite_start]Incremented per packet for gap/duplicate detection[cite: 288, 475, 676]. |
| **Timestamp** | 4 Bytes | [cite_start]UNIX epoch for synchronization and reordering[cite: 288, 476, 589]. |
| **Flags** | 1 Byte | [cite_start]Bitwise flags: Batching (Bit 0), Checksum (Bit 2)[cite: 287, 477]. |

---

## ✨ Key Features
* [cite_start]**Optional Batching**: Group up to 31 readings into one packet to amortize header overhead[cite: 273, 499, 677].
* [cite_start]**Loss Estimation**: Server-side **Linear Interpolation** to approximate missing data without retransmission[cite: 502, 643].
* [cite_start]**Anomaly Detection**: Real-time detection of duplicates, sequence gaps, and reordered packets[cite: 43, 321, 681].
* [cite_start]**Integrity**: Optional 1-byte modulo checksum for per-reading validation[cite: 290, 366, 498].

---

## 📊 Experimental Results
[cite_start]Evaluated using Linux `netem` to simulate real-world impairments[cite: 50, 149, 685].

### 1. Header Amortization (Batching)
[cite_start]As the reporting interval increases, more readings are batched, significantly reducing the **average bytes per report**[cite: 539, 541, 689].

<p align="center">
  <img src="Experiments/plots/bytes_per_report_vs_reporting_interval.png" alt="Batching Efficiency" width="500">
</p>

### 2. Network Resilience
[cite_start]Testing with **5% Packet Loss** and **100ms Jitter**[cite: 53, 627, 628]:
* [cite_start]**Baseline (0% Loss)**: High reliability with sequence tracking[cite: 53, 552].
* [cite_start]**Impaired**: Server successfully detects gaps and applies interpolation[cite: 53, 365, 681].

<p align="center">
  <img src="Assets/loss5_server_output.png" alt="5 Percent Loss Output" width="450">
  <img src="Assets/delay_jitter_server_output.png" alt="Jitter Output" width="450">
</p>

---

## 🚀 Getting Started

### Prerequisites
* [cite_start]Python 3.8+ [cite: 383, 625]
* [cite_start]Linux (for `netem` testing) [cite: 147, 625]

### Usage
1. **Start Server**:
   ```bash
   python src/server.py
