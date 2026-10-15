# Aivara Performance & Scale Guide

This document details the performance benchmarks, resource utilization, sizing limits, concurrency characteristics, and recommended deployment hardware for **Aivara**.

---

## 1. Executive Summary & SLAs

Aivara is engineered for responsive, in-memory tabular analytics without requiring external database dependencies. Analytical pipelines are stateless, thread-safe, and optimized for sub-second to low-second turnaround.

### Key Service Level Agreements (SLAs)

| Scale | Target Processing Latency | Peak Memory Consumption |
| :--- | :--- | :--- |
| **1,000 rows** | < 1.0 second | < 2 MB |
| **10,000 rows** | < 10.0 seconds | < 10 MB |
| **50,000 rows** | < 30.0 seconds | < 25 MB |
| **500,000 rows** | Automatic stratified sampling | Safe bounded execution |

---

## 2. Benchmark Results

Benchmarks were gathered using the reproducible test harness `scripts/bench.py` on an Intel/AMD x86_64 CPU running Python 3.12:

```bash
python scripts/bench.py
```

### End-to-End Pipeline Latency Breakdown

| Rows | Clean | Classify | Profile | Pipeline | Export Assembly | Total Latency | Peak RAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1,000** | 280.5 ms | 178.2 ms | 5.5 ms | 165.7 ms | 1.1 ms | **630.1 ms** | **0.52 MB** |
| **10,000** | 2,720.7 ms | 1,685.0 ms | 3.4 ms | 528.9 ms | 1.2 ms | **4,938.3 ms** | **2.73 MB** |
| **50,000** | 13,496.6 ms | 9,042.5 ms | 11.7 ms | 583.6 ms | 1.3 ms | **23,134.5 ms** | **9.41 MB** |

### Observations:
- **Pipeline Execution:** Once data is typed and cleaned, the core analytical engine (`execute_pipeline`) computes all KPIs, drivers, trends, and risk signals in **under 600 ms** even at 50,000 rows.
- **Memory Footprint:** Peak RAM footprint remains **under 10 MB** across 50,000 rows due to vectorization and avoidance of dataframe copies.
- **Export Assembly:** PPTX slide input assembly is pure Python and completes in **~1 ms**.

---

## 3. Concurrency & Throughput

Aivara's analytical pipelines are pure functions without global state or mutable shared variables. Multiple users can upload and analyze datasets simultaneously without lock contention.

### Concurrency Benchmark (5 Concurrent Sessions)

Simulating 5 concurrent analytical sessions (each processing 10,000 rows):
- **Sessions:** 5 parallel threads
- **Total Rows Processed:** 50,000 rows
- **Wall Time:** 10.85 seconds
- **Throughput:** ~4,609 rows/second
- **Data Integrity:** 0 race conditions, 0 state leakage across sessions.

---

## 4. Ingress Guards & Sizing Limits

To protect against memory exhaustion (OOM), Denial of Service (DoS), or UI unresponsiveness, Aivara enforces three defensive boundaries:

1. **`MAX_UPLOAD_MB = 100`**:
   - Files exceeding 100 MB are rejected immediately before reading into memory.
2. **`MAX_COLUMNS = 500`**:
   - Datasets exceeding 500 columns are rejected to prevent excessive combinatorial complexity.
3. **`MAX_ROWS_FULL_PROCESSING = 500,000`**:
   - When a dataset exceeds 500,000 rows, Aivara executes a deterministic stratified sample down to 500,000 rows (`random_state=42`), appends an informative notification to the load notes (`"Dataset exceeds 500,000 rows; sampled down for responsiveness."`), and processes the sample safely without crashing.

---

## 5. Recommended Hardware Profiles

### Deployment Tiers

| Profile | CPU / vCPU | Memory (RAM) | Recommended Use Case |
| :--- | :--- | :--- | :--- |
| **Minimum / Edge** | 1 vCPU | 1 GB | Single-user local desktop, files < 50k rows. |
| **Standard Production** | 2 vCPUs | 2 GB | Container deployment (`docker-compose.yml`), 1-5 concurrent users, files up to 500k rows. |
| **High Concurrency** | 4+ vCPUs | 4+ GB | Enterprise deployment, 10+ concurrent analysts. |

### Docker Resource Allocation
In production containers (`docker-compose.yml`), the following resource limits are recommended:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2048M
    reservations:
      cpus: '0.5'
      memory: 512M
```
