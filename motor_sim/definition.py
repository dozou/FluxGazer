"""Versioned, data-only standard geometry definitions (dimensionless lengths)."""
import json
from dataclasses import asdict, fields
from pathlib import Path
import numpy as np
from motor_sim.geometry import Parameters, Geometry
from motor_sim.excitation import winding


FORMAT = 'motor_sim.standard_spm'


def validate_parameters(p):
    for field in fields(p):
        value = getattr(p,field.name)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
            raise ValueError(f'{field.name}: 有限の数値が必要です。')
    if type(p.poles) is not int or type(p.slots) is not int:
        raise ValueError('極数・スロット数は整数が必要です。')
    if not .4 <= p.yoke_outer <= 2:
        raise ValueError('固定子外半径は0.4～2.0の範囲です。')
    if not 0 < p.shaft_radius < p.tooth_inner-p.air_gap < p.tooth_inner < p.yoke_inner < p.yoke_outer:
        raise ValueError('軸穴・ロータ・歯先・ヨークの径方向寸法を確認してください。')
    if not p.tooth_inner < p.coil_inner < p.coil_outer < p.yoke_inner < p.tooth_outer < p.yoke_outer:
        raise ValueError('歯とコイルの径方向配置が不正です。')
    if not 0 < p.tooth_half_width < p.coil_v_inner < p.coil_v_outer:
        raise ValueError('歯とコイルの接線方向寸法が不正です。')
    if not 0 < p.magnet_height <= p.magnet_half_width or p.apothem<=0:
        raise ValueError('磁石の高さは正で半幅以下、アポセムは正としてください。')
    if not .008*p.yoke_outer <= p.spacing <= .06*p.yoke_outer:
        raise ValueError('メッシュ間隔は固定子外半径の0.008～0.06倍としてください。')
    if not 1.5*p.yoke_outer <= p.boundary <= 6*p.yoke_outer:
        raise ValueError('外側境界は固定子外半径の1.5～6倍としてください。')
    if not 1 <= p.iron_mu <= 10000 or not 1 <= p.magnet_mu <= 10:
        raise ValueError('比透磁率の範囲：鉄心1～10000、磁石1～10。')
    if not 0 <= p.remanence <= 5 or not 0 <= p.current_density <= 100:
        raise ValueError('残留磁束密度は0～5、電流密度基準は0～100です。')
    winding(p)
    geometry = Geometry(p,0.)
    regions = geometry.regions()
    for k,a in enumerate(regions):
        if not a.is_valid or a.is_empty or a.geom_type != 'Polygon':
            raise ValueError('生成した材料領域が有効な単一ポリゴンではありません。')
        if not geometry.domain.contains(a):
            raise ValueError('材料領域が計算領域からはみ出しています。')
        for b in regions[k+1:]:
            if a.intersection(b).area > 1e-10*p.yoke_outer**2:
                raise ValueError('材料領域が重なっています。径・幅・スロット数を調整してください。')
    return p


def standard_parameters(*, poles=8, slots=12, stator_diameter=2., rotor_diameter=1.18,
                        air_gap=.05, shaft_diameter=.30, iron_mu=800., magnet_mu=1.05,
                        remanence=1., current_density=5., spacing=.018, boundary=3.):
    """Rotor diameter includes magnets; yoke ratios remain fixed.

    Tooth and coil radial positions follow the tooth-tip/yoke interval.
    """
    outer = stator_diameter/2
    tip = rotor_diameter/2+air_gap
    yoke = .85*outer
    span = yoke-tip
    p = Parameters(poles=poles,slots=slots,air_gap=air_gap,yoke_outer=outer,
        yoke_inner=yoke,tooth_inner=tip,tooth_outer=.88*outer,
        tooth_half_width=.065*outer,coil_inner=tip+span*(.04/.21),
        coil_outer=tip+span*(.18/.21),coil_v_inner=.078*outer,
        coil_v_outer=.12*outer,apothem=.47*outer,shaft_radius=shaft_diameter/2,
        magnet_half_width=.16*outer,magnet_height=.12*outer,
        iron_mu=iron_mu,magnet_mu=magnet_mu,remanence=remanence,
        current_density=current_density,spacing=spacing,boundary=boundary)
    return validate_parameters(p)


def save_definition(path,p):
    validate_parameters(p)
    document = {'format':FORMAT,'version':1,'units':'dimensionless',
                'winding':'nearest_signed_phase_belt_v1','parameters':asdict(p)}
    Path(path).write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load_definition(path):
    if Path(path).stat().st_size > 100_000:
        raise ValueError('定義ファイルが大きすぎます（上限100 kB）。')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:
                raise ValueError(f'重複キー: {key}')
            result[key]=value
        return result
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)
    if not isinstance(data,dict) or set(data)!={'format','version','units','winding','parameters'}:
        raise ValueError('定義ファイルの項目が不正です。')
    if data['format']!=FORMAT or type(data['version']) is not int or data['version']!=1:
        raise ValueError('未対応の形状形式またはバージョンです。')
    if data['units']!='dimensionless' or data['winding']!='nearest_signed_phase_belt_v1':
        raise ValueError('未対応の単位または巻線定義です。')
    values=data['parameters']
    if not isinstance(values,dict) or set(values)!={f.name for f in fields(Parameters)}:
        raise ValueError('パラメータに不足または未知の項目があります。')
    for key,value in values.items():
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not np.isfinite(value):
            raise ValueError(f'{key}: 有限の数値が必要です。')
    return validate_parameters(Parameters(**values))
