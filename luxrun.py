import os
import time

seed = 471756362
seed2 =  297064116
i = 0
os.system(f'lux-ai-2021 --rankSystem="trueskill" --tournament --maxConcurrentMatches=2 --storeReplay=false --storeLogs=false "simple.tar\main.py" "bot v0.3\main.py" "bot v0.7\main.py" "submission bots\\bot v0.6\main.py" "attempt 3\main.py" ') 
