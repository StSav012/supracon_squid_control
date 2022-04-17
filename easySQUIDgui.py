# -*- coding: utf-8 -*-
import sys
from typing import cast

import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from supracon_squid import SupraConSQUID
from value_label import ValueLabel


class GUI(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super(GUI, self).__init__()

        self.settings: QtCore.QSettings = QtCore.QSettings('SavSoft', 'easy''SQUID''control', self)

        self.central_widget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.main_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.central_widget)
        self.heat_widget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.parameters_widget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.left_controls_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.right_controls_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        self.figure: pg.PlotWidget = pg.PlotWidget(self.central_widget)

        self.parameters_box: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self.central_widget)
        self.label_amplitude: ValueLabel = ValueLabel(self.parameters_box)
        self.label_offset: ValueLabel = ValueLabel(self.parameters_box)
        self.button_sampling: QtWidgets.QPushButton = QtWidgets.QPushButton(self.parameters_box)
        self.button_auto_reset: QtWidgets.QPushButton = QtWidgets.QPushButton(self.parameters_box)

        self.parameters_control_box: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self.parameters_widget)
        self.spin_detector_bias: pg.SpinBox = pg.SpinBox(self.parameters_control_box)
        self.spin_bias: pg.SpinBox = pg.SpinBox(self.parameters_control_box)
        self.spin_offset: pg.SpinBox = pg.SpinBox(self.parameters_control_box)
        self.spin_flux: pg.SpinBox = pg.SpinBox(self.parameters_control_box)
        self.spin_ac_flux_amplitude: pg.SpinBox = pg.SpinBox(self.parameters_control_box)

        self.heat_control_box: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self.heat_widget)
        self.button_heat_squid: QtWidgets.QPushButton = QtWidgets.QPushButton(self.heat_control_box)
        self.button_heat_detector: QtWidgets.QPushButton = QtWidgets.QPushButton(self.heat_control_box)

        self.channel_control_box: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self.central_widget)
        self.channel_select: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self.channel_control_box)
        self.channel_key_reset_fll: QtWidgets.QPushButton = QtWidgets.QPushButton(self.channel_control_box)
        self.channel_key_ac_flux: QtWidgets.QPushButton = QtWidgets.QPushButton(self.channel_control_box)
        self.channel_key_test_in: QtWidgets.QPushButton = QtWidgets.QPushButton(self.channel_control_box)
        self.channel_key_bias_off: QtWidgets.QPushButton = QtWidgets.QPushButton(self.channel_control_box)
        self.channel_key_fast_reset_fll: QtWidgets.QPushButton = QtWidgets.QPushButton(self.channel_control_box)

        self.setup_ui_appearance()
        self.load_settings()
        self.setup_actions()

    def setup_ui_appearance(self) -> None:
        self.setWindowTitle('easy''SQUID''control')
        # self.setWindowIcon(QtGui.QIcon('lsn.png'))

        x_axis: pg.AxisItem = self.figure.getAxis('bottom')
        x_axis.setLabel(text='Time', units='s')
        y_axis: pg.AxisItem = self.figure.getAxis('left')
        y_axis.setLabel(text='Amplitude', units='V')

        self.label_amplitude.title = 'Amplitude:'
        self.label_amplitude.suffix = 'V'
        self.label_offset.title = 'Offset:'
        self.label_offset.suffix = 'V'

        self.figure.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

        self.main_layout.addLayout(self.left_controls_layout)
        self.main_layout.addLayout(self.right_controls_layout)
        self.main_layout.setStretch(1, 1)
        self.left_controls_layout.addWidget(self.parameters_control_box)
        self.left_controls_layout.addWidget(self.heat_control_box)
        self.right_controls_layout.addWidget(self.figure)
        self.right_controls_layout.addWidget(self.parameters_box)
        self.right_controls_layout.addWidget(self.channel_control_box)

        self.button_sampling.setText('Sampling')
        self.button_auto_reset.setText('AutoReset')

        self.button_sampling.setCheckable(True)
        self.button_auto_reset.setCheckable(True)

        self.parameters_box.setLayout(QtWidgets.QHBoxLayout())
        self.parameters_box.layout().addWidget(self.button_sampling)
        self.parameters_box.layout().addWidget(self.label_amplitude)
        self.parameters_box.layout().addWidget(self.label_offset)
        self.parameters_box.layout().addWidget(self.button_auto_reset)

        self.parameters_control_box.setLayout(QtWidgets.QFormLayout())
        self.parameters_control_box.layout().addRow('Det.-BIAS [μA]', self.spin_detector_bias)
        self.parameters_control_box.layout().addRow('BIAS', self.spin_bias)
        self.parameters_control_box.layout().addRow('OFFSET', self.spin_offset)
        self.parameters_control_box.layout().addRow('FLUX', self.spin_flux)
        self.parameters_control_box.layout().addRow('AC FLUX Amplitude', self.spin_ac_flux_amplitude)

        self.button_heat_squid.setText('Heat SQUID')
        self.button_heat_detector.setText('Heat Detector')

        self.button_heat_squid.setCheckable(True)
        self.button_heat_detector.setCheckable(True)

        self.heat_control_box.setLayout(QtWidgets.QVBoxLayout())
        self.heat_control_box.layout().addWidget(self.button_heat_squid)
        self.heat_control_box.layout().addWidget(self.button_heat_detector)

        self.channel_key_reset_fll.setText('Reset FLL')
        self.channel_key_ac_flux.setText('AC FLUX')
        self.channel_key_test_in.setText('Test In')
        self.channel_key_bias_off.setText('BIAS off')
        self.channel_key_fast_reset_fll.setText('Fast Reset FLL')

        self.channel_key_reset_fll.setCheckable(True)
        self.channel_key_ac_flux.setCheckable(True)
        self.channel_key_test_in.setCheckable(True)
        self.channel_key_bias_off.setCheckable(True)

        self.channel_select.setRange(1, 7)

        self.channel_control_box.setLayout(QtWidgets.QVBoxLayout())
        self.channel_control_box.layout().addWidget(self.channel_select)
        self.channel_control_box.layout().addWidget(self.channel_key_reset_fll)
        self.channel_control_box.layout().addWidget(self.channel_key_ac_flux)
        self.channel_control_box.layout().addWidget(self.channel_key_test_in)
        self.channel_control_box.layout().addWidget(self.channel_key_bias_off)
        self.channel_control_box.layout().addWidget(self.channel_key_fast_reset_fll)

        self.setCentralWidget(self.central_widget)

    def setup_actions(self):
        pass

    def load_settings(self) -> None:
        self.settings.beginGroup('window')
        self.restoreGeometry(cast(QtCore.QByteArray, self.settings.value('geometry', QtCore.QByteArray())))
        self.restoreState(cast(QtCore.QByteArray, self.settings.value('state', QtCore.QByteArray())))
        self.settings.endGroup()

    def save_settings(self) -> None:
        self.settings.beginGroup('window')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('state', self.saveState())
        self.settings.endGroup()
        self.settings.sync()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.button_sampling.setChecked(False)
        self.save_settings()
        event.accept()


class App(GUI):
    def __init__(self) -> None:
        super().__init__()
        self.squid: SupraConSQUID = SupraConSQUID(port='')


if __name__ == '__main__':
    app: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
    window: App = App()
    window.show()
    app.exec()
