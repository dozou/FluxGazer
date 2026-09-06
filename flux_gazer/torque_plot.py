import numpy as np
import csv
from dataclasses import asdict
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from flux_gazer.theme import colors,style_axes


class TorquePlot(FigureCanvasQTAgg):
    """Computed positions only; never mix excitation or model configurations."""
    def __init__(self):
        self.figure=Figure(figsize=(7,2.6),layout='constrained')
        super().__init__(self.figure)
        self.ax=self.figure.add_subplot(111)
        self.key=None
        self.points={}
        self.dark=False
        self.current=None
        self.x_axis='mechanical'
        self.x_limits=None
        self.y_limits=None
        self.setMinimumHeight(220)

    def record(self,key,angle,result):
        if key!=self.key:
            self.points.clear()
            self.key=key
        angle=round(float(angle)%360,6)
        self.points[angle]=(result.mean,float(min(result.values)),float(max(result.values)),
                            *map(float,result.radii),*map(float,result.values))
        self.current=angle
        if len(self.points)>720:
            del self.points[next(iter(self.points))]
        self.render()

    def clear_history(self):
        self.points.clear()
        self.current=None
        self.render()

    def set_axes(self,x_axis='mechanical',x_limits=None,y_limits=None):
        if x_axis not in ('mechanical','electrical'):
            raise ValueError('横軸の種類が不正です。')
        for limits in (x_limits,y_limits):
            if limits is not None and (len(limits)!=2 or not np.all(np.isfinite(limits)) or limits[0]>=limits[1]):
                raise ValueError('軸範囲は有限値で、最小値 < 最大値にしてください。')
        self.x_axis=x_axis
        self.x_limits=x_limits
        self.y_limits=y_limits
        self.render()

    def export_csv(self,path):
        if not self.points:
            raise ValueError('保存できる計算点がありません。再生または角度変更で計算してください。')
        p,amplitude,beta,direction,mode,source=self.key
        parameters=asdict(p)
        fields=['mechanical_angle_deg','electrical_angle_deg','plot_x','plot_x_axis',
                'torque_mean_dimensionless','torque_min_dimensionless','torque_max_dimensionless',
                'radius_1','radius_2','radius_3','torque_circle_1','torque_circle_2','torque_circle_3',
                'current_amplitude_pu','advance_deg_electrical','direction','excitation_mode','source',
                *['model_'+name for name in parameters]]
        with open(path,'w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.writer(stream)
            writer.writerow(fields)
            for angle,values in sorted(self.points.items()):
                electrical=angle*p.pole_pairs
                writer.writerow([angle,electrical,electrical if self.x_axis=='electrical' else angle,
                    self.x_axis,*values,amplitude,beta,direction,'sine' if mode==0 else 'six',source,
                    *parameters.values()])

    def render(self):
        ax=self.ax
        ax.clear()
        c=colors(self.dark)
        factor=self.key[0].pole_pairs if self.key and self.x_axis=='electrical' else 1
        ax.axhline(0,color=c['grid'],lw=.8)
        if self.points:
            angles=np.array(sorted(self.points))
            x=angles*factor
            values=np.array([self.points[a] for a in angles])
            ax.vlines(x,values[:,1],values[:,2],color=c['accent'],alpha=.45,lw=2)
            ax.plot(x,values[:,0],'.',color=c['accent'],markersize=5)
            # Connect only nearby computed positions; do not bridge unsolved angles.
            for k in range(len(x)-1):
                if angles[k+1]-angles[k]<=4.01:
                    ax.plot(x[k:k+2],values[k:k+2,0],color=c['accent'],lw=1)
            ax.plot(self.current*factor,self.points[self.current][0],'o',color='#ffb000',markersize=7)
            ax.axvline(self.current*factor,color='#ffb000',alpha=.35,lw=.8)
        label='Electrical' if self.x_axis=='electrical' else 'Mechanical'
        ax.set(xlim=self.x_limits or (0,360*factor),xlabel=f'{label} angle [deg] — computed positions',ylabel='Torque T*',
               title='Torque / dimensionless — bars: 3-circle range')
        if self.y_limits is not None:
            ax.set_ylim(*self.y_limits)
        ax.grid(True,alpha=.25,color=c['grid'])
        style_axes(self.figure,ax,self.dark)
        self.draw_idle()
