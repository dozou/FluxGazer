"""Limited torque sensitivity study, not a cogging torque certification."""
import json
from pathlib import Path
from flux_gazer.geometry import Parameters
from flux_gazer.solver import solve
from flux_gazer.excitation import currents
from flux_gazer.torque import maxwell_torque


def main():
    records=[]
    for spacing,boundary in [(.025,3),(.018,3),(.012,3),(.018,2),(.018,4)]:
        s=solve(Parameters(spacing=spacing,boundary=boundary),.137)
        record=dict(spacing=spacing,boundary=boundary,nodes=len(s.nodes))
        for source in ('both','pm','current'):
            t=maxwell_torque(s,s.potential(currents(.137),source))
            record[source]=dict(mean=t.mean,radii=t.radii.tolist(),values=t.values.tolist(),spread=t.spread)
        records.append(record)
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/torque-validation.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    for r in records:
        print(r['spacing'],r['boundary'],'T*',r['both']['mean'],'spread',r['both']['spread'],'PM-only',r['pm']['mean'])


if __name__=='__main__':
    main()
