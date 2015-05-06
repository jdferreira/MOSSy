import time
import sys


class ETA:
    
    def __init__(self, total, stream=sys.stderr):
        self.total = total
        self.stream = stream
    
    
    def start(self):
        self.count = 0
        self.start_time = time.time()
        self.last_estimate = None
    
    
    def increment(self, amount=1):
        self.count += amount
    
    
    def estimate(self):
        now = time.time()
        
        # Do a maximum of one estimation per second
        if self.last_estimate is not None and now - self.last_estimate < 1:
            return
        self.last_estimate = now
        
        todo = self.total - self.count
        elapsed = now - self.start_time
        
        eta = todo * elapsed / self.count
        percentage = int(100 * self.count / self.total)
        
        if eta < 60:
            msg = "{:02}s".format(int(eta))
        elif eta < 3600:
            m, s = divmod(eta, 60)
            msg = "{:02}m {:02}s".format(int(m), int(s))
        else:
            eta = time.strftime("%Y-%b-%d %H:%M:%S",
                                time.localtime(now + eta))
            msg = "ETA: {}".format(eta)
        
        # Format a line to print the ETA, ensuring that the previous line
        # gets erased
        print("\r\033[K[{:3}%] {}".format(percentage, msg),
              file=self.stream, end="")
        self.stream.flush()
    
    
    def finish(self):
        percentage = int(100 * self.count / self.total)
        
        elapsed = time.time() - self.start_time
        hours, rest = divmod(elapsed, 3600)
        minutes, seconds = divmod(rest, 60)
        
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        
        if hours:
            elapsed = "{:02}h {:02}m {:02}s".format(hours, minutes, seconds)
        elif minutes:
            elapsed = "{:02}m {:02}s".format(minutes, seconds)
        else:
            elapsed = "{:02}s".format(seconds)
        
        print("\r\033[K[{:3}%] Elapsed: {}".format(percentage, elapsed),
              file=self.stream)
        self.stream.flush()
