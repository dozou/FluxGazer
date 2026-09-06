import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import time
import numpy as np
import csv
import pytest
from PySide6.QtWidgets import QApplication
from motor_sim.gui import Window
from motor_sim.geometry import Parameters
from motor_sim.plot_settings import AxisDialog


def test_gui_controls(tmp_path):
    app = QApplication.instance() or QApplication([])
    w = Window(Parameters(spacing=.025))
    assert w.windowTitle()=='FluxGazer — Electric Motor Simulation'
    w.show()
    def wait():
        deadline = time.monotonic()+30
        while w.busy and time.monotonic()<deadline:
            app.processEvents()
            time.sleep(.01)
        assert not w.busy and w.solution is not None
    try:
        wait()
        w.amplitude.setValue(0)
        w.source.setCurrentIndex(2)
        assert np.max(np.abs(w.br))==0
        assert w.torque.mean==0
        w.amplitude.setValue(1.5)
        w.beta.setValue(30)
        w.mode.setCurrentIndex(1)
        w.direction.setCurrentIndex(1)
        w.angle.setValue(14)
        wait()
        assert np.isclose(w.solution.geometry.angle,np.deg2rad(14))
        w.lines.setChecked(False)
        w.vectors.setChecked(False)
        w.full.setChecked(True)
        w.redraw()
        assert w.ax.get_xlim()==(-3.,3.)
        w.toggle_play()
        w.tick()
        w.toggle_play()
        wait()
        assert w.angle.value()==12
        assert 'T* =' in w.torque_label.text()
        w.source.setCurrentIndex(0)
        w.mode.setCurrentIndex(0)
        w.direction.setCurrentIndex(0)
        w.amplitude.setValue(1)
        w.beta.setValue(0)
        w.lines.setChecked(True)
        w.vectors.setChecked(True)
        w.full.setChecked(False)
        app.processEvents()
        Path('artifacts').mkdir(exist_ok=True)
        w.grab().save('artifacts/gui.png')
        w.poles.setCurrentText('10')
        w.slots.setCurrentText('12')
        w.apply_model.click()
        # Applying another configuration during a solve must discard the stale result.
        w.poles.setCurrentText('12')
        w.slots.setCurrentText('18')
        w.air_gap.setValue(.08)
        w.apply_model.click()
        wait()
        assert w.solution.geometry.p.poles==12
        assert w.solution.geometry.p.air_gap==.08
        assert len(w.br)==18 and w.table.rowCount()==18
        assert 'θe = 6 θm' in w.info.text()
        w.slots.setCurrentText('6')
        w.apply_model.click()
        assert w.parameters.slots==18
        assert w.model_error.text()
        app.processEvents()
        w.grab().save('artifacts/gui-configurable.png')
        w.tabs.setCurrentIndex(1)
        editor=w.editor
        editor.inputs['stator_diameter'].setValue(2.4)
        editor.inputs['rotor_diameter'].setValue(1.4)
        editor.inputs['boundary'].setValue(3.6)
        editor.inputs['spacing'].setValue(.025)
        editor.inputs['iron_mu'].setValue(600)
        path=tmp_path/'generated.json'
        assert editor.export_file(path)
        app.processEvents()
        w.grab().save('artifacts/editor.png')
        assert w.load_file(path)
        wait()
        assert w.parameters.iron_mu==600
        assert w.solution.geometry.p==editor.model
        assert w.tabs.currentIndex()==0
        assert np.all(np.isfinite(w.br))
        original=w.parameters
        path.write_text('{bad json',encoding='utf-8')
        assert not w.load_file(path)
        assert w.parameters==original
        editor.inputs['rotor_diameter'].setValue(3.5)
        assert not editor.export_file(tmp_path/'invalid.json')
        assert not (tmp_path/'invalid.json').exists()
        w.dark_mode.setChecked(True)
        for angle in (20,22,24):
            w.angle.setValue(angle)
            wait()
        points=dict(w.torque_plot.points)
        assert all(angle in points for angle in (20,22,24))
        assert np.isclose(points[24][0],w.torque.mean)
        dialog=AxisDialog(w.torque_plot,w)
        dialog.kind.setCurrentIndex(1)
        for auto,boxes in dialog.ranges:
            auto.setChecked(False)
        for box,value in zip(dialog.ranges[0][1],(70,110)):
            box.setValue(value)
        for box,value in zip(dialog.ranges[1][1],(-.3,.3)):
            box.setValue(value)
        dialog.apply()
        assert w.torque_plot.ax.get_xlim()==(70,110)
        assert w.torque_plot.ax.get_ylim()==(-.3,.3)
        csv_path=tmp_path/'トルク.csv'
        w.torque_plot.export_csv(csv_path)
        with csv_path.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream))
        assert len(rows)==len(points)
        row=next(row for row in rows if float(row['mechanical_angle_deg'])==24)
        assert float(row['plot_x'])==24*w.parameters.pole_pairs
        assert float(row['torque_mean_dimensionless'])==w.torque.mean
        assert float(row['torque_circle_1'])==w.torque.values[0]
        assert float(row['model_iron_mu'])==w.parameters.iron_mu
        with pytest.raises(ValueError):
            w.torque_plot.set_axes(y_limits=(1,-1))
        assert w.torque_plot.y_limits==(-.3,.3)
        w.lines.setChecked(False)
        assert w.torque_plot.points==points
        assert w.torque_plot.ax.get_ylim()==(-.3,.3)
        w.lines.setChecked(True)
        app.processEvents()
        w.grab().save('artifacts/dark-torque.png')
        w.tabs.setCurrentIndex(1)
        app.processEvents()
        w.grab().save('artifacts/dark-editor.png')
        w.tabs.setCurrentIndex(0)
        w.dark_mode.setChecked(False)
        assert w.torque_plot.points==points
        app.processEvents()
        w.grab().save('artifacts/light-torque.png')
        w.amplitude.setValue(.7)
        assert len(w.torque_plot.points)==1
        w.torque_plot.clear_history()
        assert not w.torque_plot.points
        with pytest.raises(ValueError):
            w.torque_plot.export_csv(tmp_path/'empty.csv')
        assert not (tmp_path/'empty.csv').exists()
        w.torque_plot.set_axes()
        assert w.torque_plot.ax.get_xlim()==(0,360)
    finally:
        w.close()
