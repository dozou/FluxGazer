from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


@dataclass(frozen=True)
class Parameters:
    poles: int = 8
    slots: int = 12
    air_gap: float = .05
    yoke_inner: float = .85
    yoke_outer: float = 1.
    tooth_inner: float = .64
    tooth_outer: float = .88
    tooth_half_width: float = .065
    apothem: float = .47
    shaft_radius: float = .15
    magnet_half_width: float = .16
    magnet_height: float = .12
    coil_inner: float = .68
    coil_outer: float = .82
    coil_v_inner: float = .078
    coil_v_outer: float = .12
    iron_mu: float = 800.
    magnet_mu: float = 1.05
    remanence: float = 1.
    current_density: float = 5.  # arbitrary dimensionless J at 1 p.u.
    boundary: float = 3.
    spacing: float = .018

    def __post_init__(self):
        if self.poles not in range(4,25,2):
            raise ValueError('極数は4～24の偶数を指定してください。')
        if self.slots not in range(6,37,3):
            raise ValueError('スロット数は6～36の3の倍数を指定してください。')
        if not np.isfinite(self.air_gap) or not .01 <= self.air_gap <= .20:
            raise ValueError('エアギャップは0.01～0.20（無次元）を指定してください。')

    @property
    def pole_pairs(self):
        return self.poles//2

    @property
    def tooth_pitch(self):
        return 2*np.pi/self.slots

    @property
    def pole_pitch(self):
        return 2*np.pi/self.poles

    @property
    def slot_scale(self):
        return min(1.,12/self.slots)

    @property
    def magnet_scale(self):
        return min(1.,np.tan(np.pi/self.poles)/np.tan(np.pi/8))


def rotate(xy, angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.asarray(xy) @ np.array([[c, s], [-s, c]])


def circle(radius, spacing):
    t = np.linspace(0, 2*np.pi, max(64, int(np.ceil(2*np.pi*radius/spacing))), endpoint=False)
    return Polygon(np.c_[radius*np.cos(t), radius*np.sin(t)])


def rectangle(u0, u1, v0, v1, angle):
    return Polygon(rotate([[u0,v0],[u1,v0],[u1,v1],[u0,v1]], angle))


class Geometry:
    """One polygon representation shared by meshing, region labels and drawing.

    Circles are chord approximations with controlled spacing; no raster labels.
    """
    def __init__(self, p, angle):
        self.p, self.angle = p, angle
        scale = p.slot_scale
        apothem = min(p.apothem,(p.tooth_inner-.025)*np.cos(np.pi/p.poles))
        width = p.magnet_half_width*p.magnet_scale
        height = p.magnet_height*p.magnet_scale
        # Clearance between the swept rotor envelope and the tooth-tip circle.
        envelope = max(apothem/np.cos(np.pi/p.poles),apothem+height,
                       np.hypot(apothem,width))
        rotor_scale = (p.tooth_inner-p.air_gap)/envelope
        apothem, width, height = np.array([apothem,width,height])*rotor_scale
        if apothem <= p.shaft_radius:
            raise ValueError('ロータ鉄心が軸穴より小さくなります。')
        self.teeth = [rectangle(p.tooth_inner,p.tooth_outer,-p.tooth_half_width*scale,
                               p.tooth_half_width*scale,k*p.tooth_pitch) for k in range(p.slots)]
        self.stator = unary_union([circle(p.yoke_outer,p.spacing).difference(
            circle(p.yoke_inner,p.spacing)), *self.teeth])
        # Include PM endpoints as rotor vertices so shared edges are identical.
        half_facet = apothem*np.tan(np.pi/p.poles)
        outline = np.concatenate([rotate([[apothem,-half_facet],
            [apothem,-width],[apothem,width]],
            angle+k*p.pole_pitch) for k in range(p.poles)])
        self.rotor = Polygon(outline).difference(circle(p.shaft_radius,p.spacing))
        h, w = height, width
        radius = (w*w+h*h)/(2*h)
        center = apothem+h-radius
        alpha = np.arcsin(w/radius)
        count = max(25,int(2*alpha*radius/p.spacing)+1)
        count += (count+1)%2  # Include the exact central apex in the polygon.
        a = np.linspace(-alpha,alpha,count)
        cap = np.c_[center+radius*np.cos(a),radius*np.sin(a)]
        cap[0] = [apothem,-w]
        cap[-1] = [apothem,w]
        self.magnets = [Polygon(rotate(cap,angle+k*p.pole_pitch)) for k in range(p.poles)]
        self.coils = []
        for k in range(p.slots):
            for sign in (1,-1):
                bounds = sorted([sign*p.coil_v_inner*scale, sign*p.coil_v_outer*scale])
                self.coils.append((rectangle(p.coil_inner,p.coil_outer,*bounds,k*p.tooth_pitch),k,sign))
        self.domain = Polygon([(-p.boundary,-p.boundary),(p.boundary,-p.boundary),
                               (p.boundary,p.boundary),(-p.boundary,p.boundary)])

    def regions(self):
        return [self.stator,self.rotor,*self.magnets,*[c[0] for c in self.coils]]
