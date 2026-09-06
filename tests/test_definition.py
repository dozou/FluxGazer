import json
from dataclasses import asdict,replace
import numpy as np
import pytest
from motor_sim.definition import save_definition,load_definition,standard_parameters
from motor_sim.geometry import Parameters,Geometry
from motor_sim.solver import solve
from motor_sim.postprocess import tooth_br


def test_definition_roundtrip(tmp_path):
    p=standard_parameters(poles=10,slots=12,stator_diameter=2.4,rotor_diameter=1.4,
                         shaft_diameter=.32,air_gap=.06,iron_mu=700,magnet_mu=1.1,
                         remanence=.9,current_density=4,spacing=.025,boundary=3.6)
    path=tmp_path/'モデル.json'
    save_definition(path,p)
    restored=load_definition(path)
    assert restored==p
    for a,b in zip(Geometry(p,.12).regions(),Geometry(restored,.12).regions()):
        assert a.equals_exact(b,1e-12)
    s=solve(restored,.12)
    assert np.all(np.isfinite(tooth_br(s,s.bases[:,0])))
    assert s.residual<1e-9


def test_standard_default_and_dimensions():
    p=standard_parameters()
    for key,value in asdict(Parameters()).items():
        assert np.isclose(getattr(p,key),value)
    g=Geometry(standard_parameters(stator_diameter=2.4,rotor_diameter=1.4,air_gap=.06,
                                  spacing=.025,boundary=3.6),0.)
    maximum=max(np.linalg.norm(np.asarray(a.exterior.coords),axis=1).max() for a in [g.rotor,*g.magnets])
    assert np.isclose(2*maximum,1.4)
    assert np.isclose(g.p.tooth_inner,.76)


@pytest.mark.parametrize('change',[
    lambda d:d.update(version=2),lambda d:d.update(units='mm'),
    lambda d:d['parameters'].update(iron_mu=-1),lambda d:d['parameters'].update(spacing=0),
    lambda d:d['parameters'].update(remanence=float('nan')),
    lambda d:d['parameters'].update(poles=8.0),lambda d:d['parameters'].update(slots=True),
    lambda d:d['parameters'].update(unknown=1),lambda d:d['parameters'].pop('shaft_radius'),
    lambda d:d['parameters'].update(shaft_radius=.6)])
def test_bad_definition(tmp_path,change):
    path=tmp_path/'bad.json'
    save_definition(path,Parameters())
    data=json.loads(path.read_text(encoding='utf-8'))
    change(data)
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError):
        load_definition(path)


def test_impossible_generator():
    with pytest.raises(ValueError):
        standard_parameters(rotor_diameter=1.8)
