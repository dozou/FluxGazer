import numpy as np
from matplotlib.tri import Triangulation, LinearTriInterpolator
from flux_gazer.geometry import rotate


def triangulation(solution):
    return Triangulation(*solution.nodes.T,solution.triangles)


def tooth_br(solution, potential):
    interpolator = LinearTriInterpolator(triangulation(solution),potential)
    result = []
    p = solution.geometry.p
    half_width = p.tooth_half_width*(.05/.065)*p.slot_scale
    sections = p.tooth_inner+(p.yoke_inner-p.tooth_inner)*np.array([.03,.05,.07])/.21
    for k in range(p.slots):
        points = rotate([[u,v] for u in sections for v in (-half_width,half_width)],k*p.tooth_pitch)
        values = interpolator(*points.T).reshape(3,2)
        result.append(np.mean((values[:,1]-values[:,0])/(2*half_width)))
    return np.array(result)


def element_b(solution, potential):
    derivative = np.einsum('ti,tij->tj',potential[solution.triangles],solution.gradients)
    return np.c_[derivative[:,1],-derivative[:,0]]
