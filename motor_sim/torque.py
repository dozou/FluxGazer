"""Air-gap Maxwell stress, dimensionless torque per reference axial length.

T* = integral r*² Br* Btheta* dtheta; T_SI = B0² L0² l / mu0 * T*.
The spread between evaluation circles is a sensitivity indicator, not an error bar.
"""
from dataclasses import dataclass
import numpy as np
from motor_sim.postprocess import triangulation, element_b


@dataclass(frozen=True)
class TorqueResult:
    radii: np.ndarray
    values: np.ndarray

    @property
    def mean(self):
        return float(np.mean(self.values))

    @property
    def spread(self):
        return float(np.ptp(self.values))


def maxwell_torque(solution,potential,samples=4096):
    """Integrate element B on three circles fully inside the common air gap.

    Positive means counterclockwise torque on the enclosed rotor. No display
    normalization, smoothing, or cancellation of PM-only numerical torque.
    """
    if samples<32:
        raise ValueError('Torque integration requires at least 32 samples.')
    p=solution.geometry.p
    radii=p.tooth_inner-p.air_gap+np.array([.3,.5,.7])*p.air_gap
    theta=(np.arange(samples)+.5)*2*np.pi/samples
    cosine,sine=np.cos(theta),np.sin(theta)
    # The geometry and sample-to-element map are reusable for changed currents.
    cache=getattr(solution,'_torque_samples',None)
    if cache is None or cache[0]!=samples:
        finder=triangulation(solution).get_trifinder()
        ids=np.asarray(finder(radii[:,None]*cosine,radii[:,None]*sine))
        if np.any(ids<0):
            raise ValueError('トルク評価円がメッシュ領域外です。')
        solution._torque_samples=(samples,ids)
    else:
        ids=cache[1]
    b=element_b(solution,potential)[ids]
    radial=b[:,:,0]*cosine+b[:,:,1]*sine
    tangent=-b[:,:,0]*sine+b[:,:,1]*cosine
    values=radii**2*np.sum(radial*tangent,axis=1)*(2*np.pi/samples)
    return TorqueResult(radii,values)
