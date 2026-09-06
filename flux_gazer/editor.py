"""Standard geometry generator. Editing never mutates the running simulation."""
from PySide6 import QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from flux_gazer.definition import standard_parameters, save_definition, load_definition
from flux_gazer.geometry import Geometry
from flux_gazer.drawing import draw_polygon
from flux_gazer.excitation import winding
from flux_gazer.theme import colors,style_axes


class ModelEditor(QtWidgets.QWidget):
    apply_requested = QtCore.Signal(object)

    def __init__(self,p,parent=None):
        super().__init__(parent)
        self.model=p
        self.dark=False
        self.dirty=False
        root=QtWidgets.QHBoxLayout(self)
        self.figure=Figure(figsize=(7,7))
        self.canvas=FigureCanvasQTAgg(self.figure)
        self.ax=self.figure.add_subplot(111)
        root.addWidget(self.canvas,1)
        controls=QtWidgets.QWidget()
        form=QtWidgets.QFormLayout(controls)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(380)
        root.addWidget(scroll)
        note=QtWidgets.QLabel('標準SPM形状生成・線形材料定義\n長さ・径・Br・Jは無次元です。\nロータ径は磁石を含む回転包絡径。\n歯先径 = ロータ径 + 2 × 空隙。\nヨーク・歯幅は標準比率で生成します。')
        form.addRow(note)
        self.inputs={}
        for key,label,low,high,step,decimals in [
            ('poles','極数',4,24,2,0),('slots','スロット数',6,36,3,0),
            ('stator_diameter','固定子外径 / L₀',.8,4,.1,4),
            ('rotor_diameter','ロータ包絡外径 / L₀',.2,3.5,.02,4),
            ('air_gap','最小空隙 / L₀',.01,.2,.01,4),
            ('shaft_diameter','軸穴径 / L₀',.02,1.5,.02,4),
            ('iron_mu','鉄心 比透磁率',1,10000,100,3),
            ('magnet_mu','磁石 比透磁率',1,10,.01,4),
            ('remanence','残留磁束密度 基準',0,5,.1,4),
            ('current_density','1 p.u. 電流密度 基準',0,100,1,4),
            ('spacing','メッシュ点間隔 / L₀',.0032,.12,.002,5),
            ('boundary','計算領域 半幅 / L₀',.6,12,.2,4)]:
            widget=QtWidgets.QDoubleSpinBox()
            widget.setRange(low,high)
            widget.setDecimals(decimals)
            widget.setSingleStep(step)
            widget.valueChanged.connect(self.mark_dirty)
            self.inputs[key]=widget
            form.addRow(label,widget)
        for label,method in [('生成・プレビュー',self.generate),('定義ファイル出力…',self.export_dialog),
                             ('定義ファイルを開く…',self.open_dialog),('シミュレーションへ適用',self.apply_model)]:
            button=QtWidgets.QPushButton(label)
            button.clicked.connect(method)
            form.addRow(button)
        self.status=QtWidgets.QLabel()
        self.status.setWordWrap(True)
        form.addRow(self.status)
        self.set_model(p)

    def mark_dirty(self,*_):
        self.dirty=True
        if hasattr(self,'status'):
            self.status.setText('未生成の変更があります。プレビューは直前の有効な形状です。')

    def set_model(self,p):
        values=dict(poles=p.poles,slots=p.slots,stator_diameter=2*p.yoke_outer,
                    rotor_diameter=2*(p.tooth_inner-p.air_gap),shaft_diameter=2*p.shaft_radius,
                    air_gap=p.air_gap,iron_mu=p.iron_mu,magnet_mu=p.magnet_mu,remanence=p.remanence,
                    current_density=p.current_density,spacing=p.spacing,boundary=p.boundary)
        for key,value in values.items():
            self.inputs[key].setValue(value)
        self.model=p
        self.dirty=False
        self.preview()

    def generate(self):
        try:
            if self.dirty:
                values={key:widget.value() for key,widget in self.inputs.items()}
                values['poles']=int(values['poles'])
                values['slots']=int(values['slots'])
                model=standard_parameters(**values)
                self.model=model
                self.dirty=False
            self.preview()
            return True
        except (ValueError,TypeError) as exc:
            self.status.setText('生成できません：'+str(exc))
            return False

    def preview(self):
        p=self.model
        g=Geometry(p,0.)
        self.ax.clear()
        c=colors(self.dark)
        draw_polygon(self.ax,g.stator,c['iron'])
        draw_polygon(self.ax,g.rotor,c['rotor'])
        for k,magnet in enumerate(g.magnets):
            draw_polygon(self.ax,magnet,c['magnet_n'] if k%2==0 else c['magnet_s'])
        phases,_=winding(p)
        for coil,k,_ in g.coils:
            draw_polygon(self.ax,coil,['#e8ad51','#87c994','#b4a0dd'][phases[k]])
        limit=1.15*p.yoke_outer
        self.ax.set(xlim=(-limit,limit),ylim=(-limit,limit),aspect='equal',xlabel='x / L₀',ylabel='y / L₀',
                    title=f'{p.poles}P{p.slots}S / stator D={2*p.yoke_outer:g} / rotor D={2*(p.tooth_inner-p.air_gap):g}')
        self.canvas.draw_idle()
        style_axes(self.figure,self.ax,self.dark)
        self.status.setText('生成済み。形状・材料・巻線規約・メッシュ条件をJSONに保存できます。')

    def export_file(self,path):
        if not self.generate():
            return False
        try:
            save_definition(path,self.model)
            self.status.setText(f'保存しました：{path}')
            return True
        except (OSError,ValueError) as exc:
            self.status.setText('保存できません：'+str(exc))
            return False

    def export_dialog(self):
        if not self.generate():
            return
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'定義ファイル出力','motor.json','Motor definition (*.json)')
        if path:
            self.export_file(path)

    def open_dialog(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'定義ファイルを開く','','Motor definition (*.json)')
        if path:
            try:
                self.set_model(load_definition(path))
            except (OSError,ValueError,TypeError) as exc:
                self.status.setText('読み込めません：'+str(exc))

    def apply_model(self):
        if self.generate():
            self.apply_requested.emit(self.model)
