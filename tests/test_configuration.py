import numpy as np
import pytest
from flux_gazer.geometry import Parameters, Geometry
from flux_gazer.excitation import winding, currents, dq, winding_axis
from flux_gazer.solver import solve
from flux_gazer.postprocess import tooth_br


@pytest.mark.parametrize('poles,slots',[(4,6),(8,12),(10,12),(12,18),(16,24),(24,36)])
def test_configurable_field(poles,slots):
    p = Parameters(poles=poles,slots=slots,spacing=.025)
    phases,signs = winding(p)
    offset = winding_axis(p)
    g = Geometry(p,.1)
    assert len(g.magnets)==poles and len(g.teeth)==slots
    regions = g.regions()
    for k,a in enumerate(regions):
        assert a.is_valid
        for b in regions[k+1:]:
            assert a.intersection(b).area<1e-10
    s = solve(p,0.)
    t = np.arange(slots)*p.tooth_pitch*p.pole_pairs
    direct = tooth_br(s,s.potential([1,-.5,-.5],'current'))
    pm = tooth_br(s,s.bases[:,0])
    assert np.dot(direct,np.cos(t))>0
    assert np.dot(direct,pm)>0
    for direction in (-1,1):
        i = currents(0,1,.3,direction,pole_pairs=p.pole_pairs,winding_offset=offset)
        np.testing.assert_allclose(dq(0,i,p.pole_pairs,offset),[-np.sin(.3),direction*np.cos(.3)],atol=1e-14)
        q = tooth_br(s,s.potential(currents(0,direction=direction,pole_pairs=p.pole_pairs,winding_offset=offset),'current'))
        assert direction*np.dot(q,np.sin(t))>0
        advanced = tooth_br(s,s.potential(i,'current'))
        assert np.dot(advanced,pm)<np.dot(q,pm)
    assert s.residual<1e-9


def test_invalid_and_original_winding():
    phases,signs = winding(Parameters())
    np.testing.assert_array_equal(phases,np.arange(12)%3)
    np.testing.assert_array_equal(signs,np.ones(12))
    with pytest.raises(ValueError):
        Parameters(poles=7)
    with pytest.raises(ValueError):
        winding(Parameters(poles=12,slots=6))


@pytest.mark.parametrize('poles,slots',[(4,6),(8,12),(24,36)])
@pytest.mark.parametrize('gap',[.01,.05,.20])
def test_air_gap_envelope(poles,slots,gap):
    p = Parameters(poles=poles,slots=slots,air_gap=gap)
    for angle in (0,.17):
        g = Geometry(p,angle)
        rotor_parts = [g.rotor,*g.magnets]
        radius = max(np.linalg.norm(np.asarray(part.exterior.coords),axis=1).max()
                     for part in rotor_parts)
        assert abs(p.tooth_inner-radius-gap)<2e-5
        assert min(g.stator.distance(part) for part in rotor_parts)>=gap-2e-5
        assert abs(g.rotor.interiors[0].length-2*np.pi*p.shaft_radius)<.002


def test_air_gap_changes_field():
    values=[]
    for gap in (.01,.12):
        s=solve(Parameters(air_gap=gap,spacing=.025),0.)
        values.append(tooth_br(s,s.bases[:,0])[0])
        assert s.residual<1e-9
    assert values[0]>values[1]>0
    with pytest.raises(ValueError):
        Parameters(air_gap=0)
