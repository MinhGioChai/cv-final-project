"""Team pilot: Qwen NF4/FP16 or Gemma NF4/BF16; default 2 rows and new outputs."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vlmbench.pilot_launcher import main

if __name__=='__main__':
    raise SystemExit(main())
