import numpy as np


def currents(angle, amplitude=1., beta=0., direction=1, mode='sine', pole_pairs=4, winding_offset=0.):
    """Angles in radians. Reverse retains negative d at positive beta."""
    phase = pole_pairs*angle - winding_offset + direction*(np.pi/2+beta)
    values = np.cos(phase - np.arange(3)*2*np.pi/3)
    if mode == 'six':
        out = np.zeros(3)
        out[np.argmax(values)], out[np.argmin(values)] = amplitude, -amplitude
        return out
    return amplitude*values


def dq(angle, values, pole_pairs=4, winding_offset=0.):
    phase = pole_pairs*angle - winding_offset - np.arange(3)*2*np.pi/3
    return np.array([2/3*np.dot(values,np.cos(phase)),
                     -2/3*np.dot(values,np.sin(phase))])


def winding(parameters):
    """Nearest signed phase belt to each tooth's electrical position.

    Reject unbalanced/degenerate combinations rather than imply a usable winding.
    """
    theta = np.arange(parameters.slots)*parameters.tooth_pitch*parameters.pole_pairs
    axes = np.arange(3)*2*np.pi/3
    # Assign exact belt-boundary ties consistently toward increasing angle.
    belt = np.floor(np.round(theta/(np.pi/3),12)+.5).astype(int)%6
    phase = np.array([0,2,1,0,2,1])[belt]
    signs = np.array([1,-1,1,-1,1,-1])[belt]
    counts = np.bincount(phase,minlength=3)
    if np.any(counts != counts[0]):
        raise ValueError('この極数・スロット数では自動巻線が三相対称になりません。別の組合せを選んでください。')
    phasors = np.array([np.sum(signs[phase==j]*np.exp(1j*theta[phase==j])) for j in range(3)])
    aligned = phasors*np.exp(-1j*axes)
    if abs(aligned[0])<1e-8 or not np.allclose(aligned,aligned[0],atol=1e-8):
        raise ValueError('この組合せは対称な回転磁界用の自動巻線に対応していません。')
    return phase,signs


def winding_axis(parameters):
    phases,signs = winding(parameters)
    theta = np.arange(parameters.slots)*parameters.tooth_pitch*parameters.pole_pairs
    return float(np.angle(np.sum(signs[phases==0]*np.exp(1j*theta[phases==0]))))
