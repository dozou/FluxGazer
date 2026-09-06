from collections import OrderedDict
from motor_sim.solver import solve


class FieldCache:
    """Bounded LRU; worker-owned, exact requested geometry, no angle interpolation."""
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, parameters, angle):
        key = (parameters,float(angle))
        if key not in self.data:
            self.data[key] = solve(parameters,angle)
            if len(self.data)>self.capacity:
                self.data.popitem(last=False)
        self.data.move_to_end(key)
        return self.data[key]
