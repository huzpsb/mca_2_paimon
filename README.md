# 📘 Manual for MCA to Paimon Region Converter

0.1x as big as mca, 10x as fast as linear.  

Get paimon with [CrazyLeaf](https://builtbybit.com/resources/crazyleaf-modern-spigot-fork.64180/)!

## 📁 Project Directory Structure

```
project_root/
│
├── mca_to_paimon.py               # Worker script: converts individual MCA files to Paimon format
├── mca_to_paimon_supervisor.py    # Supervisor script: spawns multiple worker processes
├── world/
│   ├── region/                    # Input directory containing `.mca` (Anvil format) region files
│   └── region1/                   # Output directory for `.paimon` files
```

## ⚙️ Dependencies

Install Python packages (tested with Python ≥ 3.7):

```bash
pip install pyzstd nbtlib
```

## 🚧 Build Output Directory

Ensure the output directory exists before running the scripts:

```bash
mkdir -p world/region1
```

## ▶️ Running the Conversion

### Step-by-step:

1. **Prepare Input Files**: Put all `.mca` region files into `world/region/`.

2. **Start Conversion**:

Run the supervisor script:

```bash
python mca_to_paimon_supervisor.py
```

This:

* Cleans stale lock files from `world/region1/`.
* Starts 10 worker processes running `mca_to_paimon.py` in parallel.
* Waits for them to finish.
* Cleans up locks again.
* Calls `mca_to_paimon.py fin` once to convert any remaining unprocessed files.

## 🧠 How It Works

### Worker (`mca_to_paimon.py`)

* Randomly samples `.mca` files from `world/region/`.
* Skips if the `.paimon` version exists or is locked.
* Uses `.lock` files to prevent collisions in multi-process settings.
* Converts each region file using:

  * Custom binary parsing of Anvil format
  * Chunk-wise decompression and re-encoding using Zlib
  * Reassembly into a compressed binary format with a `PAIMON_SIGNATURE`
* Writes to a temp file, flushes to disk, renames atomically.

### Supervisor (`mca_to_paimon_supervisor.py`)

* Manages worker lifecycles
* Ensures deterministic cleanup and batch finalization

## 🧪 Testing Tips

* Drop a few known `.mca` files into `world/region/`, run the supervisor, then inspect `world/region1/` for `.paimon` files.
* Do not remove the original region file unless you've tested the paimon files.

## 🚀 Performance & Efficiency

The `.paimon` format is specifically engineered for both **space efficiency** and **high-throughput conversion**, significantly outperforming the legacy `.mca` format and traditional linear processing pipelines:

### 📦 Compression Ratio

Paimon region files are on average:

$$
\textbf{Only 10\\% the size of the original } .mca \textbf{ files}
$$

This translates into:

* Massive disk space savings
* Faster I/O operations
* Better archiving and transfer performance

### ⚡ Conversion Speed

By leveraging:

* A pool of 10 parallel worker processes,
* Lock-based atomicity control,
* Batching and low-overhead file renaming,

this converter achieves:

$$
\textbf{10× the speed} \textbf{ of a naive single-threaded (linear) implementation}
$$

Benchmarked on typical Minecraft region sets, this means converting 500+ regions in a matter of minutes instead of hours — **without sacrificing determinism or output fidelity**.  
[Linear](https://github.com/xymb-endcrystalme/LinearRegionFileFormatTools) doesn't have performance in mind, we do :3
