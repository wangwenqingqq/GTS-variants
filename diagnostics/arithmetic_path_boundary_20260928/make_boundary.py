#!/usr/bin/env python3
"""Six deterministic 4096-point finite-value L2 boundary fixtures."""
from array import array
from pathlib import Path
import argparse
import struct


def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    values = (0.0, 1.0, -1.0, 2.0 ** -149, 2.0 ** -126,
              2.0 ** 100, -(2.0 ** 100), 0.125, -0.125)
    for d in (2, 31, 32, 33, 96, 960):
        path = a.output / str(d)
        path.mkdir(parents=True)
        rows = array("f")
        for i in range(4096):
            for j in range(d):
                if i in (0, 1):
                    v = 0.0  # Two IDs, one vector.
                elif i == 2:
                    v = 1.0 if j == 0 else 0.0
                elif i == 3:
                    v = -1.0 if j == 0 else 0.0
                elif i == 4:
                    v = 2.0 ** -149 if j == 0 else 0.0
                elif i == 5:
                    v = 2.0 ** 100 if j == 0 else 0.0
                elif i % 31 == 0:
                    v = values[(i * 17 + j * 13) % len(values)]
                else:
                    v = ((i * 167 + j * 271) % 2001 - 1000) / 1000.0
                rows.append(v)
        with (path / "data.f32bin").open("wb") as f:
            f.write(struct.pack("<iii", d, 4096, 2))
            rows.tofile(f)
        (path / "queries.qid").write_text("4\n0\n2\n4\n5\n")


if __name__ == "__main__":
    main()
