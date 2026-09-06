from dataclasses import replace
import numpy as np
import pytest
from motor_sim.geometry import Parameters, Geometry
from motor_sim.excitation import currents, dq
from motor_sim.solver import solve
from motor_sim.postprocess import tooth_br, element_b
from motor_sim.cache import FieldCache


@pytest.fixture(scope='module')
def solution():
    return solve(Parameters(),0.)


def test_geometry():
    for angle in (0,.123,np.pi/4):
        g = Geometry(Parameters(),angle)
        assert len(g.magnets)==8 and len(g.teeth)==12 and len(g.coils)==24
        regions = g.regions()
        for i,a in enumerate(regions):
            assert a.is_valid
            for b in regions[i+1:]:
                assert a.intersection(b).area<1e-11
        assert np.isclose(g.magnets[0].area,g.magnets[7].area)


def test_currents():
    for angle in np.linspace(0,2*np.pi,31):
        for direction in (-1,1):
            for beta in (-np.pi/3,0,np.pi/3):
                for mode in ('sine','six'):
                    i = currents(angle,1.3,beta,direction,mode)
                    assert abs(i.sum())<1e-13
                    if mode=='sine':
                        np.testing.assert_allclose(dq(angle,i),[-1.3*np.sin(beta),direction*1.3*np.cos(beta)],atol=1e-14)
                np.testing.assert_allclose(currents(angle+np.pi/2,1,beta,direction),currents(angle,1,beta,direction),atol=1e-14)


def test_superposition(solution):
    s = solution
    i = currents(.17)
    np.testing.assert_allclose(s.potential(i),s.potential(i,'pm')+s.potential(i,'current'),atol=1e-14)
    np.testing.assert_array_equal(s.potential([0,0,0],'current'),0)
    np.testing.assert_array_equal(s.potential([0,0,0]),s.bases[:,0])
    np.testing.assert_allclose(element_b(s,s.potential(2*i,'current')),2*element_b(s,s.potential(i,'current')))
    assert s.residual<1e-9


def test_computed_field_sign_and_weakening(solution):
    s = solution
    pm = tooth_br(s,s.bases[:,0])
    direct = tooth_br(s,s.potential([1,-.5,-.5],'current'))
    assert pm[0]>0 and direct[0]>0
    assert np.dot(pm,direct)>0
    t = np.arange(12)*np.pi/6
    for direction in (-1,1):
        q = tooth_br(s,s.potential(currents(0,1,0,direction),'current'))
        # Computed four-pole-pair quadrature component follows requested rotation.
        assert direction*np.dot(q,np.sin(4*t))>0
        advanced = tooth_br(s,s.potential(currents(0,1,np.pi/6,direction),'current'))
        assert np.dot(advanced,pm)<np.dot(q,pm)


def test_polarity_and_rotation(solution):
    from matplotlib.tri import LinearTriInterpolator
    from motor_sim.postprocess import triangulation
    # Radial B by tangential Az differences just outside every magnet.
    for angle in (0,.13):
        s = solution if angle==0 else solve(Parameters(),angle)
        f = LinearTriInterpolator(triangulation(s),s.bases[:,0])
        for k in range(8):
            a = angle+k*np.pi/4
            center = .607*np.array([np.cos(a),np.sin(a)])
            tangent = np.array([-np.sin(a),np.cos(a)])
            plus,minus = center+.003*tangent,center-.003*tangent
            br = (float(f(*plus))-float(f(*minus)))/.006
            assert br*(-1)**k>0


def test_cache():
    cache = FieldCache(1)
    p = Parameters(spacing=.04)
    a = cache.get(p,0.)
    assert cache.get(p,0.) is a
    cache.get(p,.1)
    assert len(cache.data)==1
