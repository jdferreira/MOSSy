import sys
import inspect

class Tracker:
    
    def __init__(self, indent_size=4, stream=sys.stderr):
        self.indent = 0
        self.stream = stream
        self.indent_str = " " * indent_size
    
    
    def enter(self, fn, *args, **kwargs):
        argspec = inspect.getargspec(fn).args
        ismethod = argspec and argspec[0] == "self"
        
        ft_args = []
        for arg in args:
            ft_args.append("{!r}".format(arg))
        for keyword, value in kwargs.items():
            ft_args.append("{}={!r}".format(keyword, value))
        
        if ismethod:
            ft_args[0] = "self"
        
        self.print("Entering {}({})".format(fn.__name__, ', '.join(ft_args)))
        self.indent += 1
    
    
    def error(self, fn, e):
        self.indent -= 1
    
    
    def exit(self, fn, result):
        self.print("return {!r}".format(result))
        self.indent -= 1
    
    
    def print(self, msg):
        lines = msg.splitlines()
        lines = (self.indent_str * self.indent + line for line in lines)
        print('\n'.join(lines), file=self.stream)
        


def track(fn):
    def wrapper(*args, **kwargs):
        _tracker.enter(fn, *args, **kwargs)
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            _tracker.error(fn, e)
            raise
        else:
            _tracker.exit(fn, result)
            return result
    return wrapper


def track_print(msg):
    _tracker.print(msg)
track.print = track_print


_tracker = Tracker(2)
