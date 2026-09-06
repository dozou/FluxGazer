"""Report boundary and mesh sensitivity; this is not torque validation."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
from matplotlib.tri import LinearTriInterpolator
from flux_gazer.geometry import Parameters
from flux_gazer.solver import solve
from flux_gazer.postprocess import tooth_br, triangulation


def main():
    records=[]
    samples=[]
    for spacing,boundary in [(.025,3),(.018,3),(.012,3),(.018,2),(.018,4)]:
        s=solve(Parameters(spacing=spacing,boundary=boundary),.137)
        br=tooth_br(s,s.bases[:,0])
        f=LinearTriInterpolator(triangulation(s),s.bases[:,0])
        t=np.arange(36)*2*np.pi/36
        x,y=1.15*np.cos(t),1.15*np.sin(t)
        dx,dy=f.gradient(x,y)
        external=np.c_[dy,-dx]
        samples.append((br,external))
        records.append(dict(spacing=spacing,boundary=boundary,nodes=len(s.nodes),
                            residual=s.residual,tooth_br=br.tolist(),external_b_rms=float(np.sqrt(np.mean(external**2)))))
    ref,ext=samples[1]
    for record,(br,external) in zip(records,samples):
        record['tooth_relative_difference_from_default']=float(np.linalg.norm(br-ref)/np.linalg.norm(ref))
        record['external_relative_difference_from_default']=float(np.linalg.norm(external-ext)/np.linalg.norm(ext))
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/validation.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(records,indent=2))

if __name__=='__main__':
    main()
