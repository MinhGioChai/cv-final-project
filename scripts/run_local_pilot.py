"""Compatibility alias for the current team pilot; --model gemma uses BF16."""
from run_pilot import main

if __name__=='__main__':
    raise SystemExit(main())
