# Independent main-kernel diagnostics

One first-measured-query NCU capture/mode; no sampling CI. Decimal total DRAM GB/s uses the same capture duration and real bytes. Occupancy is NCU active-warps percentage. READ_ONLY arithmetic is a checksum, not search work; inflation is N/A. Profiler duration is not Host ACK.

| Mode | Kernel ms | DRAM GB/s | DRAM read / write GB | SM % | Active-warps % | Registers | Work inflation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Native | 3.324128 | 1160.115 | 3.840073 / 0.016297 | 76.47 | 28.86 | 126 | 64.022230× |
| Non-padded | 2.517536 | 1530.511 | 3.840146 / 0.012971 | 11.97 | 85.35 | 37 | 1.045155× |
| Read-only | 2.509504 | 1532.455 | 3.840063 / 0.005638 | 1.69 | 87.99 | 18 | N/A |
