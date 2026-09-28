# Tloc million-point paired screen

Frozen before timing. Same compiled E/P/R/Q executable, same Tloc N=1,000,000
fixture and normal radius 3.089289426803589, batch one, original layout,
result fusion and CUDA Graph common to all arms. Full R/Q output passed CPU
oracle/native ordered-hash checks. R/Q memcheck and synccheck passed. Run four
independent processes per arm on one idle physical GPU, orders EPRQ, QRPE,
PREQ, QERP, each with eight warmups and eight measured queries. Report the
median of process mean host-ready query times and same-round E/R, P/Q, E/P,
R/Q and E/Q ratios; keep all rounds including unfavorable ones. No cross-GPU
or previous-campaign denominator. Stop on any foreign activity, retain partial
attempts, and rerun the entire timing stage in a fresh directory if incomplete.
