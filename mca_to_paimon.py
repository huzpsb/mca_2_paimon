import os
import struct
import sys
from time import sleep

import pyzstd
import nbtlib
import io
import zlib
import random


class Chunk:
    def __init__(self, raw_chunk, x, z):
        self.raw_chunk = raw_chunk
        self.x, self.z = x, z

    def as_nbtlib(self):
        fileobj = io.BytesIO(self.raw_chunk)
        file = nbtlib.File.parse(fileobj)
        return file

    def from_nbtlib(self, nbtlib_obj):
        fileobj = io.BytesIO()
        nbtlib_obj.write(fileobj)
        self.raw_chunk = fileobj.getvalue()

    def __str__(self):
        return "Chunk %d %d - %d bytes" % (self.x, self.z, len(self.raw_chunk))


class Region:
    def __init__(self, chunks, region_x, region_z, mtime, timestamps):
        self.chunks = chunks
        self.region_x, self.region_z = region_x, region_z
        self.mtime = mtime
        self.timestamps = timestamps

    def chunk_count(self):
        return sum(1 for c in self.chunks if c is not None)


REGION_DIMENSION = 32
PAIMON_SIGNATURE = 1145141919811
COMPRESSION_TYPE_ZLIB = 2
EXTERNAL_FILE_COMPRESSION_TYPE = 128 + 2


def write_region_paimon(destination_filename, region: Region):
    buffer_uncompressed_size = [0] * (32 ** 2)
    compressed_chunks = []

    for i in range(32 ** 2):
        chunk = region.chunks[i]
        if chunk is not None:
            raw_data = chunk.raw_chunk
            compressed_chunks.append(raw_data)
            buffer_uncompressed_size[i] = len(raw_data)
        else:
            compressed_chunks.append(b"")
            buffer_uncompressed_size[i] = 0

    header_data = struct.pack(">" + "I" * 1024, *buffer_uncompressed_size)
    chunks_data = b"".join(compressed_chunks)
    complete_region = header_data + chunks_data
    compressed_data = pyzstd.compress(complete_region, level_or_option=21)
    preheader = struct.pack(">QI", PAIMON_SIGNATURE, len(compressed_data))
    footer = struct.pack(">Q", PAIMON_SIGNATURE)
    final_region_file = preheader + compressed_data + footer
    tmp_path = destination_filename + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(final_region_file)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp_path, destination_filename)
    os.utime(destination_filename, (region.mtime, region.mtime))


def open_region_anvil(file_path):
    SECTOR = 4096
    chunk_starts = []
    chunk_sizes = []
    timestamps = []
    chunks = []
    file_coords = file_path.split('/')[-1].split('.')[1:3]
    region_x, region_z = int(file_coords[0]), int(file_coords[1])

    mtime = os.path.getmtime(file_path)
    anvil_file = open(file_path, 'rb').read()

    source_folder = file_path.rpartition("/")[0]

    for i in range(REGION_DIMENSION * REGION_DIMENSION):
        a, b, c, sector_count = struct.unpack_from(">BBBB", anvil_file, i * 4)
        chunk_starts.append(c + b * 256 + a * 256 * 256)
        chunk_sizes.append(sector_count)

    for i in range(REGION_DIMENSION * REGION_DIMENSION):
        timestamps.append(struct.unpack_from(">I", anvil_file, SECTOR + i * 4)[0])

    for i in range(REGION_DIMENSION * REGION_DIMENSION):
        if chunk_starts[i] > 0 and chunk_sizes[i] > 0:
            whole_raw_chunk = anvil_file[SECTOR * chunk_starts[i]:SECTOR * (chunk_starts[i] + chunk_sizes[i])]
            chunk_size, compression_type = struct.unpack_from(">IB", whole_raw_chunk, 0)
            if compression_type == COMPRESSION_TYPE_ZLIB:
                chunks.append(
                    Chunk(zlib.decompress(whole_raw_chunk[5:5 + chunk_size]), REGION_DIMENSION * region_x + i % 32,
                          REGION_DIMENSION * region_z + i // 32))
            elif compression_type == EXTERNAL_FILE_COMPRESSION_TYPE:
                external_file = open(source_folder + "/c.%d.%d.mcc" % (
                    REGION_DIMENSION * region_x + i % 32, REGION_DIMENSION * region_z + i // 32), "rb").read()
                chunks.append(Chunk(zlib.decompress(external_file), REGION_DIMENSION * region_x + i % 32,
                                    REGION_DIMENSION * region_z + i // 32))
            else:
                raise Exception("Compression type %d unimplemented!" % compression_type)
        else:
            chunks.append(None)

    return Region(chunks, region_x, region_z, mtime, timestamps)


def create_file_cas(file_path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(file_path, flags)
        with os.fdopen(fd, 'w') as f:
            f.write('locked')
        return True
    except FileExistsError:
        return False


failed_attempts = 0

mca_files = os.listdir("world/region")

argv = sys.argv
if len(argv) > 1:
    if (argv[1] == "fin"):
        for mca_file in mca_files:
            if mca_file.endswith(".mca"):
                p_dest = "world/region1/" + mca_file.replace(".mca", ".paimon")
                if not os.path.exists(p_dest):
                    p_src = "world/region/" + mca_file
                    p_dest = "world/region1/" + mca_file.replace(".mca", ".paimon")

                    region = open_region_anvil(p_src)
                    write_region_paimon(p_dest, region)
        sys.exit(0)

while True:
    rdm_file = mca_files[random.randint(0, len(mca_files) - 1)]
    if not rdm_file.endswith(".mca"):
        continue

    p_src = "world/region/" + rdm_file
    p_dest = "world/region1/" + rdm_file.replace(".mca", ".paimon")
    p_lock = p_dest + ".lock"

    if os.path.exists(p_dest):
        print("Skipping %s, already exists." % p_dest)
        failed_attempts += 1
        if failed_attempts > 10:
            print("Too many failed attempts, exiting.")
            break

        continue

    if not create_file_cas(p_lock):
        print("Skipping %s, already locked." % p_dest)
        sleep(0.001 * random.randint(1, 2000))
        continue

    print("Converting %s to paimon format..." % rdm_file)

    region = open_region_anvil(p_src)
    write_region_paimon(p_dest, region)
    os.remove(p_lock)

    print("Converted %s to paimon format." % rdm_file)
