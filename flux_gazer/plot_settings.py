from PySide6 import QtWidgets


class AxisDialog(QtWidgets.QDialog):
    def __init__(self,plot,parent=None):
        super().__init__(parent)
        self.setWindowTitle('トルクグラフの軸設定')
        self.plot=plot
        form=QtWidgets.QFormLayout(self)
        self.kind=QtWidgets.QComboBox()
        self.kind.addItems(['機械角 [deg]','電気角 [deg]（折り返しなし）'])
        self.kind.setCurrentIndex(plot.x_axis=='electrical')
        form.addRow('横軸',self.kind)
        self.ranges=[]
        for label,limits,current in [('横軸',plot.x_limits,plot.ax.get_xlim()),('縦軸 T*',plot.y_limits,plot.ax.get_ylim())]:
            automatic=QtWidgets.QCheckBox('自動（横軸は機械1回転分）' if label=='横軸' else '自動')
            automatic.setChecked(limits is None)
            form.addRow(label,automatic)
            boxes=[]
            for name,value in zip(['最小','最大'],limits or current):
                box=QtWidgets.QDoubleSpinBox()
                box.setDecimals(9)
                box.setRange(-1e9,1e9)
                box.setValue(float(value))
                box.setEnabled(not automatic.isChecked())
                automatic.toggled.connect(lambda checked,b=box:b.setEnabled(not checked))
                form.addRow(name,box)
                boxes.append(box)
            self.ranges.append((automatic,boxes))
        note=QtWidgets.QLabel('軸設定は表示だけを変更します。CSVには非表示範囲の計算点も保存します。\n電気角は極対数×機械角です。縦軸は無次元トルクです。')
        note.setWordWrap(True)
        form.addRow(note)
        self.error=QtWidgets.QLabel()
        form.addRow(self.error)
        buttons=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def apply(self):
        limits=[None if auto.isChecked() else tuple(box.value() for box in boxes) for auto,boxes in self.ranges]
        try:
            self.plot.set_axes('electrical' if self.kind.currentIndex() else 'mechanical',*limits)
            self.accept()
        except ValueError as exc:
            self.error.setText(str(exc))
