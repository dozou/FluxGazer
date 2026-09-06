import numpy as np
from motor_sim.geometry import Parameters
from motor_sim.solver import solve
from motor_sim.excitation import currents
from motor_sim.torque import maxwell_torque


def test_torque_sign_scaling_and_sampling():
    s=solve(Parameters(),.137)
    forward=s.potential(currents(.137))
    reverse=s.potential(currents(.137,direction=-1))
    t=maxwell_torque(s,forward)
    assert np.all(t.values>0)
    assert np.all(maxwell_torque(s,reverse).values<0)
    np.testing.assert_allclose(maxwell_torque(s,2*forward).values,4*t.values)
    np.testing.assert_array_equal(maxwell_torque(s,np.zeros(len(s.nodes))).values,0)
    finer=maxwell_torque(s,forward,samples=8192)
    assert abs(finer.mean-t.mean)/abs(t.mean)<.01
    p=s.geometry.p
    assert np.all(t.radii>p.tooth_inner-p.air_gap)
    assert np.all(t.radii<p.tooth_inner)


def test_torque_is_not_sum_of_excitation_torques():
    s=solve(Parameters(),0.)
    i=currents(0.)
    combined=maxwell_torque(s,s.potential(i)).mean
    isolated=sum(maxwell_torque(s,s.potential(i,source)).mean for source in ('pm','current'))
    assert abs(combined-isolated)>.03
