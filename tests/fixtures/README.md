# synthetic_test_only

All images and manifest rows used by the offline test suite are generated in
pytest temporary directories. They are synthetic fixtures, not RePOPE samples
and not model predictions. No fixture output is written into `results/`.
