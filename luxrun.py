import os
import time

seed = 471756362
seed2 =  297064116
i = 0
while i < 20:
    os.system(f'lux-ai-2021 "submission bots\\bot v0.6\main.py" "attempt 3\main.py" --out=file.json{i}') 
    print(f"Finsished game {i}")
    i+=1
    break


#os.startfile("attempt 2/basicLog.log")