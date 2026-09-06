import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path


def draw_polygon(ax,polygon,color):
    vertices,codes=[],[]
    for ring in [polygon.exterior,*polygon.interiors]:
        points=np.asarray(ring.coords)
        vertices.extend(points)
        codes.extend([Path.MOVETO]+[Path.LINETO]*(len(points)-2)+[Path.CLOSEPOLY])
    ax.add_patch(PathPatch(Path(vertices,codes),facecolor=color,edgecolor='#555555',lw=.65))
