import sys
import traceback
from dataclasses import replace
from pathlib import Path as FilePath
import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from flux_gazer import APP_NAME
from flux_gazer.geometry import Parameters
from flux_gazer.cache import FieldCache
from flux_gazer.excitation import currents, dq, winding, winding_axis
from flux_gazer.postprocess import triangulation, tooth_br
from flux_gazer.definition import load_definition, validate_parameters
from flux_gazer.editor import ModelEditor
from flux_gazer.drawing import draw_polygon
from flux_gazer.torque import maxwell_torque
from flux_gazer.theme import colors,style_axes,set_widget_theme
from flux_gazer.torque_plot import TorquePlot
from flux_gazer.plot_settings import AxisDialog


class Worker(QtCore.QObject):
    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.cache = FieldCache()

    @QtCore.Slot(object)
    def compute(self, request):
        try:
            serial, p, angle = request
            self.done.emit((serial,self.cache.get(p,angle)))
        except Exception:
            self.failed.emit(traceback.format_exc())


class Window(QtWidgets.QMainWindow):
    requested = QtCore.Signal(object)

    def __init__(self, parameters=None):
        super().__init__()
        # Offscreen Qt may select a font without Japanese glyphs on Windows.
        font_path = FilePath('C:/Windows/Fonts/meiryo.ttc')
        if font_path.exists():
            font_id = QtGui.QFontDatabase.addApplicationFont(str(font_path))
            families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.setFont(QtGui.QFont(families[0],9))
        self.parameters = parameters or Parameters()
        self.setWindowTitle(f'{APP_NAME} — Electric Motor Simulation')
        self.resize(1200,850)
        self.solution = None
        self.busy = False
        self.serial = 0
        self.playing = False
        self.figure = Figure(figsize=(8,8),facecolor='#fafafa')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        plots = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        plots.addWidget(self.canvas)
        self.torque_plot = TorquePlot()
        plots.addWidget(self.torque_plot)
        plots.setSizes([570,250])
        layout.addWidget(plots,1)
        controls = QtWidgets.QWidget()
        form = QtWidgets.QVBoxLayout(controls)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(385)
        layout.addWidget(scroll)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(panel,'シミュレーション')
        self.editor = ModelEditor(self.parameters)
        self.tabs.addTab(self.editor,'標準形状・物性定義')
        self.editor.apply_requested.connect(self.install_model)
        self.setCentralWidget(self.tabs)
        self.dark_mode = QtWidgets.QCheckBox('ダークモード')
        self.dark_mode.setChecked(self.palette().color(QtGui.QPalette.ColorRole.Window).lightness()<128)
        form.addWidget(self.dark_mode)
        self.dark_mode.toggled.connect(self.apply_theme)
        clear_graph = QtWidgets.QPushButton('トルクグラフをクリア')
        clear_graph.clicked.connect(self.torque_plot.clear_history)
        form.addWidget(clear_graph)
        export_graph=QtWidgets.QPushButton('トルク点列をCSV保存…')
        export_graph.clicked.connect(self.export_torque)
        form.addWidget(export_graph)
        axes_button=QtWidgets.QPushButton('トルクグラフの軸設定…')
        axes_button.clicked.connect(self.configure_axes)
        form.addWidget(axes_button)
        self.graph_status=QtWidgets.QLabel()
        self.graph_status.setWordWrap(True)
        self.graph_status.setMaximumWidth(350)
        form.addWidget(self.graph_status)
        self.load_button = QtWidgets.QPushButton('定義ファイル読込…')
        self.load_button.clicked.connect(self.load_dialog)
        form.addWidget(self.load_button)
        self.heading = QtWidgets.QLabel('SPM / 無次元・線形静磁界 FEM')
        form.addWidget(self.heading)
        configuration = QtWidgets.QHBoxLayout()
        self.poles = QtWidgets.QComboBox()
        self.poles.addItems([str(n) for n in range(4,25,2)])
        self.poles.setCurrentText(str(self.parameters.poles))
        self.slots = QtWidgets.QComboBox()
        self.slots.addItems([str(n) for n in range(6,37,3)])
        self.slots.setCurrentText(str(self.parameters.slots))
        configuration.addWidget(QtWidgets.QLabel('極数'))
        configuration.addWidget(self.poles)
        configuration.addWidget(QtWidgets.QLabel('スロット数'))
        configuration.addWidget(self.slots)
        self.apply_model = QtWidgets.QPushButton('適用')
        configuration.addWidget(self.apply_model)
        form.addLayout(configuration)
        self.air_gap = self.spin(form,'エアギャップ / L₀（回転包絡面～歯先）',.01,.20,
                                 self.parameters.air_gap,.01)
        self.air_gap.setDecimals(3)
        self.model_error = QtWidgets.QLabel()
        self.model_error.setWordWrap(True)
        self.model_error.setMaximumWidth(350)
        form.addWidget(self.model_error)
        self.apply_model.clicked.connect(self.configure_model)
        self.angle = self.spin(form,'ロータ機械角 [deg]',0,359.9,0,2)
        self.amplitude = self.spin(form,'電流振幅 [p.u.]',0,1.5,1,.1)
        self.beta = self.spin(form,'進角 β [電気 deg]',-60,60,0,5)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(['正弦波','六ステップ120°'])
        form.addWidget(self.mode)
        self.direction = QtWidgets.QComboBox()
        self.direction.addItems(['正転 CCW','逆転 CW'])
        form.addWidget(self.direction)
        self.source = QtWidgets.QComboBox()
        self.source.addItems(['永久磁石＋固定子電流','永久磁石のみ','固定子電流のみ'])
        form.addWidget(self.source)
        self.lines = QtWidgets.QCheckBox('磁力線（Az等値線）')
        self.vectors = QtWidgets.QCheckBox('歯の径方向磁束密度 Br')
        self.full = QtWidgets.QCheckBox('計算領域全体を表示')
        for widget in (self.lines,self.vectors,self.full):
            form.addWidget(widget)
        self.lines.setChecked(True)
        self.vectors.setChecked(True)
        self.play = QtWidgets.QPushButton('再生／一時停止')
        form.addWidget(self.play)
        self.play.clicked.connect(self.toggle_play)
        self.info = QtWidgets.QLabel()
        self.info.setWordWrap(True)
        self.info.setMinimumWidth(300)
        form.addWidget(self.info)
        self.torque_label = QtWidgets.QLabel()
        self.torque_label.setWordWrap(True)
        self.torque_label.setMaximumWidth(350)
        form.addWidget(self.torque_label)
        self.table = QtWidgets.QTableWidget(self.parameters.slots,2)
        self.table.setHorizontalHeaderLabels(['歯／相','Br [無次元]'])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setMaximumHeight(310)
        form.addWidget(self.table)
        note = QtWidgets.QLabel('矢印は力・磁束Φではありません。\n矢印倍率：0.18 × Br（全フレーム共通）\nアニメーションは位置走査であり、\n実回転数・運動応答ではありません。\n表示端を横切る磁力線は領域外へ続きます。')
        note.setWordWrap(True)
        form.addWidget(note)
        form.addStretch()
        self.thread = QtCore.QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.requested.connect(self.worker.compute)
        self.worker.done.connect(self.accept)
        self.worker.failed.connect(self.error)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.angle.valueChanged.connect(self.request)
        for widget in (self.amplitude,self.beta):
            widget.valueChanged.connect(self.redraw)
        for widget in (self.mode,self.direction,self.source):
            widget.currentIndexChanged.connect(self.redraw)
        for widget in (self.lines,self.vectors,self.full):
            widget.toggled.connect(self.redraw)
        self.canvas.mpl_connect('motion_notify_event',self.hover)
        self.apply_theme()
        self.request()

    def apply_theme(self,*_):
        dark=self.dark_mode.isChecked()
        set_widget_theme(self,dark)
        c=colors(dark)
        self.torque_label.setStyleSheet(f'color: {c["fg"]}; background: {c["panel"]}; padding: 6px;')
        self.editor.dark=dark
        # Theme changes must not clear an editor validation/dirty message.
        status=self.editor.status.text()
        self.editor.preview()
        self.editor.status.setText(status)
        self.torque_plot.dark=dark
        self.torque_plot.render()
        if self.solution is not None:
            self.redraw()
        else:
            style_axes(self.figure,self.ax,dark)

    def configure_axes(self):
        AxisDialog(self.torque_plot,self).exec()

    def export_torque(self):
        if not self.torque_plot.points:
            self.graph_status.setText('保存できる計算点がありません。')
            return
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'トルク点列を保存','torque.csv','CSV (*.csv)')
        if path:
            try:
                self.torque_plot.export_csv(path)
                self.graph_status.setText(f'保存しました：{path}')
            except (OSError,ValueError) as exc:
                self.graph_status.setText('保存できません：'+str(exc))

    def configure_model(self):
        self.playing = False
        try:
            parameters = replace(self.parameters,poles=int(self.poles.currentText()),
                                 slots=int(self.slots.currentText()),air_gap=self.air_gap.value())
            validate_parameters(parameters)
        except ValueError as exc:
            self.model_error.setText(str(exc))
            return
        self.model_error.setText('形状・空隙・巻線を適用。歯ラベルは相と巻方向です。')
        self.parameters = parameters
        self.request()

    def install_model(self,parameters):
        validate_parameters(parameters)
        self.playing = False
        self.parameters = parameters
        self.poles.setCurrentText(str(parameters.poles))
        self.slots.setCurrentText(str(parameters.slots))
        self.air_gap.setValue(parameters.air_gap)
        self.model_error.setText('定義モデルを適用しました。計算中は直前のモデルを表示します。')
        self.tabs.setCurrentIndex(0)
        self.request()

    def load_file(self,path):
        try:
            parameters = load_definition(path)
            self.install_model(parameters)
            self.model_error.setText(f'読込済み：{path}')
            return True
        except (OSError,ValueError,TypeError) as exc:
            self.model_error.setText('読込できません：'+str(exc))
            return False

    def load_dialog(self):
        path,_ = QtWidgets.QFileDialog.getOpenFileName(self,'定義ファイル読込','','Motor definition (*.json)')
        if path:
            self.load_file(path)

    def spin(self, form, label, low, high, value, step):
        form.addWidget(QtWidgets.QLabel(label))
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(low,high)
        widget.setSingleStep(step)
        widget.setValue(value)
        form.addWidget(widget)
        return widget

    def request(self, *_):
        if self.busy:
            return
        self.busy = True
        self.serial += 1
        self.info.setText('FEM計算中…（表示は直前に完了した角度）')
        self.requested.emit((self.serial,self.parameters,np.deg2rad(self.angle.value())))

    def accept(self, result):
        self.busy = False
        _, solution = result
        if solution.geometry.p != self.parameters or abs(solution.geometry.angle-np.deg2rad(self.angle.value()))>1e-10:
            self.request()
            return
        self.solution = solution
        self.redraw()

    def error(self, message):
        self.busy = False
        self.playing = False
        self.info.setText('計算失敗：'+message)

    def toggle_play(self):
        self.playing = not self.playing

    def tick(self):
        if self.playing and not self.busy:
            step = 2 if self.direction.currentIndex()==0 else -2
            self.angle.setValue((self.angle.value()+step)%360)

    def redraw(self, *_):
        if self.solution is None:
            return
        sol = self.solution
        g = sol.geometry
        p = g.p
        phases, signs = winding(p)
        offset = winding_axis(p)
        names = [f'{"UVW"[phase]}{"+" if sign>0 else "−"}' for phase,sign in zip(phases,signs)]
        self.names = names
        self.heading.setText(f'{p.poles}極{p.slots}スロット SPM / 空隙 {p.air_gap:.3f} L₀')
        self.table.setRowCount(p.slots)
        sign = 1 if self.direction.currentIndex()==0 else -1
        i = currents(g.angle,self.amplitude.value(),np.deg2rad(self.beta.value()),sign,
                     'sine' if self.mode.currentIndex()==0 else 'six',p.pole_pairs,offset)
        source = ['both','pm','current'][self.source.currentIndex()]
        potential = sol.potential(i,source)
        self.torque = maxwell_torque(sol,potential)
        history_key=(p,self.amplitude.value(),self.beta.value(),sign,self.mode.currentIndex(),source)
        self.torque_plot.record(history_key,np.rad2deg(g.angle),self.torque)
        self.torque_label.setText(
            f'ロータトルク T* = {self.torque.mean:+.5e}\n'
            f'評価円3本の範囲：{min(self.torque.values):+.3e} ～ {max(self.torque.values):+.3e}\n'
            f'無次元・参考値／正＝反時計回り\n'
            f'現在の励磁表示から算出。Nm・実機予測ではありません。')
        self.br = tooth_br(sol,potential)
        ax = self.ax
        ax.clear()
        c=colors(self.dark_mode.isChecked())
        draw_polygon(ax,g.stator,c['iron'])
        draw_polygon(ax,g.rotor,c['rotor'])
        for k, magnet in enumerate(g.magnets):
            draw_polygon(ax,magnet,c['magnet_n'] if k%2==0 else c['magnet_s'])
            ax.text(magnet.centroid.x,magnet.centroid.y,'N' if k%2==0 else 'S',ha='center',va='center',fontsize=8,color=c['fg'])
        for coil,k,side in g.coils:
            draw_polygon(ax,coil,['#e8ad51','#87c994','#b4a0dd'][phases[k]])
        if self.lines.isChecked() and np.ptp(potential)>1e-10:
            # Fixed contour interval, including tiny exterior leakage levels.
            positive = np.r_[[.00001,.00002,.00005,.0001,.0002,.0005,.001,.002,.004],np.arange(.008,.301,.008)]
            levels = np.r_[-positive,positive]
            levels = np.sort(levels)
            levels = levels[(levels>potential.min())&(levels<potential.max())]
            if len(levels):
                ax.tricontour(triangulation(sol),potential,levels=levels,colors=c['flux'],linewidths=.65,alpha=.8)
        t = np.arange(p.slots)*p.tooth_pitch
        arrow_radius = p.tooth_inner+(p.yoke_inner-p.tooth_inner)*(.10/.21)
        if self.vectors.isChecked():
            ax.quiver(arrow_radius*np.cos(t),arrow_radius*np.sin(t),.18*self.br*np.cos(t),.18*self.br*np.sin(t),
                      angles='xy',scale_units='xy',scale=1,color='#ffad00',edgecolor='#251700',
                      linewidth=.7,width=.009,zorder=10,minlength=0)
        for k,a in enumerate(t):
            ax.text(.94*p.yoke_outer*np.cos(a),.94*p.yoke_outer*np.sin(a),f'{k}{names[k]}',ha='center',va='center',fontsize=8,color=c['fg'])
            self.table.setItem(k,0,QtWidgets.QTableWidgetItem(f'{k} / {names[k]}'))
            self.table.setItem(k,1,QtWidgets.QTableWidgetItem(f'{self.br[k]:+.6f}'))
        limit = p.boundary if self.full.isChecked() else 1.22*p.yoke_outer
        ax.set(xlim=(-limit,limit),ylim=(-limit,limit),aspect='equal',xlabel='x / L₀',ylabel='y / L₀')
        ax.set_title(f'Quasi-static position: {np.rad2deg(g.angle):.1f}° mech / {np.rad2deg(p.pole_pairs*g.angle)%360:.1f}° elec')
        d,q = dq(g.angle,i,p.pole_pairs,offset)
        label = '瞬時Park値' if self.mode.currentIndex() else '正弦波 dq'
        self.info.setText(f'θe = {p.pole_pairs} θm\n相電流参照 U/V/W = {i[0]:+.3f}, {i[1]:+.3f}, {i[2]:+.3f}\n'
                          f'{label}: id={d:+.3f}, iq={q:+.3f}\n'
                          f'φ=θe−δ {"+" if sign==1 else "−"} (90°+β), δ={np.rad2deg(offset):.1f}°\n'
                          f'{len(sol.nodes):,} nodes / {len(sol.triangles):,} elements\n'
                          f'相対残差 {sol.residual:.2e}（精度保証ではない）\n境界 ±{p.boundary:g}: Az=0')
        style_axes(self.figure,ax,self.dark_mode.isChecked())
        self.canvas.draw_idle()

    def hover(self,event):
        if event.xdata is None or self.solution is None:
            return
        p = self.solution.geometry.p
        k = int(np.round(np.arctan2(event.ydata,event.xdata)/p.tooth_pitch))%p.slots
        if p.tooth_inner*.95<np.hypot(event.xdata,event.ydata)<p.yoke_outer:
            self.canvas.setToolTip(f'歯{k} / {self.names[k]}: Br={self.br[k]:+.6f}（無次元、外向き正）')
        else:
            self.canvas.setToolTip('')

    def closeEvent(self,event):
        self.timer.stop()
        self.thread.quit()
        self.thread.wait()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    window = Window()
    window.show()
    sys.exit(app.exec())
