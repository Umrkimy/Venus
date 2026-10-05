import os

# numpy's maths library reserves memory for every CPU thread (~350 MB on 12 threads)
# at import. Venus only does small sums, so one thread is plenty.
# Must run before anything imports numpy; this package loads first.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
