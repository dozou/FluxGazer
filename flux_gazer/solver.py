from dataclasses import dataclass
import numpy as np
import triangle
import shapely
from shapely.ops import unary_union
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from flux_gazer.geometry import Geometry
from flux_gazer.excitation import winding


@dataclass
class Solution:
    geometry: Geometry
    nodes: np.ndarray
    triangles: np.ndarray
    bases: np.ndarray
    gradients: np.ndarray
    residual: float

    def potential(self, currents, source='both'):
        a = np.zeros(len(self.nodes))
        if source != 'current':
            a += self.bases[:,0]
        if source != 'pm':
            a += currents[0]*self.bases[:,1]+currents[1]*self.bases[:,2]
        return a


def mesh(geometry):
    p = geometry.p
    # Noding splits shared PM/rotor edges and tooth/yoke union boundaries.
    lines = unary_union([g.boundary for g in [geometry.domain,*geometry.regions()]])
    vertices, segments, lookup = [], [], {}
    def index(point):
        key = tuple(np.round(point,12))
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(key)
        return lookup[key]
    for line in lines.geoms:
        xy = np.asarray(line.coords)
        for a,b in zip(xy[:-1],xy[1:]):
            # Fine edges near the motor, graded exterior elsewhere.
            length = np.linalg.norm(b-a)
            n = max(1,int(np.ceil(length/(p.spacing if np.linalg.norm((a+b)/2)<1.1*p.yoke_outer else .3*p.yoke_outer))))
            ids = [index(a+(b-a)*t) for t in np.linspace(0,1,n+1)]
            segments.extend(zip(ids[:-1],ids[1:]))
    # Interior seeds keep the air gap resolved irrespective of boundary distance.
    axis = np.arange(-1.06*p.yoke_outer,1.06*p.yoke_outer+p.spacing/2,p.spacing)
    xx, yy = np.meshgrid(axis,axis)
    candidates = np.c_[xx.ravel(),yy.ravel()]
    candidates = candidates[shapely.distance(shapely.points(candidates),lines)>p.spacing*.2]
    for point in candidates:
        index(point)
    # Resolve narrow gaps locally without refining the entire exterior domain.
    gap_step = min(p.spacing,p.air_gap/3)
    for radius in np.arange(p.tooth_inner-p.air_gap+gap_step,p.tooth_inner,gap_step):
        angles = np.linspace(0,2*np.pi,int(np.ceil(2*np.pi*radius/gap_step)),endpoint=False)
        ring = np.c_[radius*np.cos(angles),radius*np.sin(angles)]
        ring = ring[shapely.distance(shapely.points(ring),lines)>gap_step*.15]
        for point in ring:
            index(point)
    for radius in np.arange(1.15*p.yoke_outer,p.boundary,.18*p.yoke_outer):
        t = np.linspace(0,2*np.pi,max(30,int(2*np.pi*radius/(.04*p.yoke_outer+.12*(radius-p.yoke_outer)))),endpoint=False)
        for point in np.c_[radius*np.cos(t),radius*np.sin(t)]:
            index(point)
    # Avoid unlimited quality refinement at the deliberately sharp magnet tips.
    result = triangle.triangulate({'vertices':np.array(vertices),'segments':np.array(segments)},'pq20Q')
    return result['vertices'],result['triangles']


def solve(p, angle):
    phases, winding_signs = winding(p)
    g = Geometry(p,angle)
    nodes, triangles = mesh(g)
    xy = nodes[triangles]
    twice = (xy[:,1,0]-xy[:,0,0])*(xy[:,2,1]-xy[:,0,1])-(xy[:,2,0]-xy[:,0,0])*(xy[:,1,1]-xy[:,0,1])
    area = np.abs(twice)/2
    grad = np.stack([xy[:,[1,2,0],1]-xy[:,[2,0,1],1],
                     xy[:,[2,0,1],0]-xy[:,[1,2,0],0]],axis=2)/twice[:,None,None]
    centroids = xy.mean(axis=1)
    points = shapely.points(centroids)
    mu = np.ones(len(triangles))
    mu[shapely.contains(g.stator,points)|shapely.contains(g.rotor,points)] = p.iron_mu
    br = np.zeros((len(triangles),2))
    j = np.zeros((len(triangles),2))
    for k,magnet in enumerate(g.magnets):
        mask = shapely.contains(magnet,points)
        mu[mask] = p.magnet_mu
        a = angle+k*p.pole_pitch
        br[mask] = p.remanence*(-1)**k*np.array([np.cos(a),np.sin(a)])
    for coil,k,sign in g.coils:
        mask = shapely.contains(coil,points)
        # Positive local-v side +J: FEM verifies outward Br for positive current.
        j[mask] = sign*winding_signs[k]*p.current_density*np.array([[1,0],[0,1],[-1,-1]])[phases[k]]
    local = area[:,None,None]/mu[:,None,None]*np.einsum('tik,tjk->tij',grad,grad)
    rows = np.repeat(triangles,3,axis=1).ravel()
    cols = np.tile(triangles,(1,3)).ravel()
    matrix = coo_matrix((local.ravel(),(rows,cols)),shape=(len(nodes),len(nodes))).tocsc()
    rhs_local = np.zeros((len(triangles),3,3))
    rhs_local[:,:,0] = area[:,None]/mu[:,None]*(br[:,0,None]*grad[:,:,1]-br[:,1,None]*grad[:,:,0])
    rhs_local[:,:,1:] = area[:,None,None]*j[:,None,:]/3
    rhs = np.zeros((len(nodes),3))
    np.add.at(rhs,triangles.ravel(),rhs_local.reshape(-1,3))
    free = np.max(np.abs(nodes),axis=1)<p.boundary-1e-9
    reduced = matrix[free][:,free]
    bases = np.zeros_like(rhs)
    bases[free] = splu(reduced).solve(rhs[free])
    residual = np.linalg.norm(reduced@bases[free]-rhs[free])/max(np.linalg.norm(rhs[free]),1e-30)
    return Solution(g,nodes,triangles,bases,grad,residual)
