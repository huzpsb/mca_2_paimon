import os
import subprocess


def cleanup_lock_files():
    outputs = os.listdir("world/region1")
    for output in outputs:
        if not output.endswith(".paimon"):
            os.remove(os.path.join("world/region1", output))


cleanup_lock_files()

workers = []

for i in range(10):
    worker = subprocess.Popen(
        ["python", "mca_to_paimon.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    workers.append(worker)

# Wait for all workers to finish
for worker in workers:
    worker.wait()

# Clean up any remaining lock files
cleanup_lock_files()

worker = subprocess.Popen(
    ["python", "mca_to_paimon.py", "fin"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
worker.wait()

print("All MCA files have been processed and converted to Paimon format.")
