import time

def readableSeconds(sec):
    """
    Produces a string with readable units of time
    """
    units = [
        #Singular unit, plural unit, amount until next unit
        ('sec', 'secs', 60),
        ('min', 'mins', 60),
        ('hr', 'hrs', 24),
        ('day', 'days', 7),
        ('week', 'weeks', 52),
        ('year', 'years', 10)
    ]
    send = ""
    index = 0
    while sec > 0:
        remainder = int(sec % units[index][2])
        sec = sec // units[index][2]
        send = str(remainder) + " " + (units[index][0] if remainder == 1 else units[index][1]) + (", " if index != 0 else "") + send
        index += 1
    return send

def printBar(iteration, total, barLength=40, timeSinceStart = -1, timeNow = 0):
    full = '█' * int(barLength * iteration / total)
    empty = '░' * int(barLength-len(full))
    print(f'\rProgress: [{full}{empty}] - {iteration}/{total}', end='')
    if timeSinceStart != -1:
        printTime = 'N/A'
        elapsed = timeNow - timeSinceStart
        if iteration != 0:
            perUnit = elapsed / iteration
            totalTime = perUnit * total
            #"Total Estimated Time: " + readableSeconds(round(totalTime, 2)) + ", ETA: "
            printTime = "ETA: " + readableSeconds(round(totalTime - elapsed, 2)) + ", Time of completion: " + time.asctime(time.localtime(timeNow + totalTime-elapsed))
        #Time Elapsed: {readableSeconds(elapsed)}
        print(f'{printTime}\033[K', end='')
    print(end='', flush=True)

if __name__ == "__main__":
    import time
    total_steps = 100
    start = time.time()
    for i in range(total_steps + 1):
        printBar(i, total_steps, timeSinceStart = start, timeNow = time.time())
        time.sleep(0.5)
    print() # New line on completion
