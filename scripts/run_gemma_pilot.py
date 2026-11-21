"""Compatibility alias for the current NF4/BF16 team pilot."""
from run_pilot import main

if __name__=='__main__':
    raise SystemExit(main(default_model='gemma'))
