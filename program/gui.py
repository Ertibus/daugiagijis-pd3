from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import *
import sys
from taskmgr import TaskManager
import threading
import time
class Updates(QThread):
    is_active = False
    _signal = pyqtSignal(str)
    _msg_queue = []
    def __init__(self):
        super(Updates, self).__init__()

    def __del__(self):
        self.wait()

    def run(self):
        is_active = True
        while is_active or _msg_queue:
            if not self._msg_queue:
                time.sleep(0.1)
                continue
            msg = self._msg_queue.pop(0)
            self._signal.emit(msg)

    def msger(self, msg):
        self._msg_queue.append(msg)

class PyQtGUI(QWidget):
    _is_working = False
    _is_paused = False
    _output_log = None
    _sys_err_label = None
    _progress_bar = None
    _pause_proc_button = None
    _stop_proc_button = None
    _thread = None
    _taskmgr = None
    _start = 0

    _flag_init = False
    _flag_out = False

    def __init__(self):
        super().__init__()
        self._is_working = False

        self._sys_err_label = QLabel()
        self._sys_err_label.setAlignment(QtCore.Qt.AlignCenter)
        self._sys_err_label.setStyleSheet(
            """
            QLabel {
                color: red
            }
            """
        )

        self._thread = Updates()
        self._thread._signal.connect(self.msg_listener)

        self._taskmgr = TaskManager(self.update_listener, self._thread.msger)

        self.initUI()
    
    def closeEvent(self, event):
        if self._is_working:
            self._sys_err_label.setText("Can exist the program while it is in progress!")
            event.ignore()
            return
        event.accept()

    def msg_listener(self, msg):
        self._output_log.append(f'{round(time.perf_counter() - self._start, 3)}:\t{msg}')

    def update_listener(self, progress):
        self._progress_bar.setValue(progress)
        if progress == 100:
            self.reset_buttons()

    def reset_buttons(self):
        self._thread.is_active = False
        self._is_working = False
        self._pause_proc_button.setEnabled(False)
        self._pause_proc_button.setText("Pause")
        self._stop_proc_button.setEnabled(False)

    def clear_sys_label(self):
        self._sys_err_label.setText(" ")

    def initUI(self):
        def _select_init_arff():
            self.clear_sys_label();
            file, check = QFileDialog.getOpenFileName(None, 'Select arff to read', str(sys.path[0]), 'ARFF Files (*.arff)')
            if not check:
                return
            attributes_listbox.clear()
            in_selected_arff.setText(file)
            for att in self._taskmgr.get_init_file(file):
                item = QListWidgetItem("%s" % (str(att)))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                attributes_listbox.addItem(item)
            self._flag_init = True

        def _select_out_arff():
            self.clear_sys_label();
            file, check = QFileDialog.getSaveFileName(None, 'Select save location', str(sys.path[0]), 'ARFF Files (*.arff)')
            if not check:
                return
            out_selected_arff.setText(file)
            self._flag_out = True

        def _start_process():
            if self._is_working:
                self._sys_err_label.setText("Can't start a new task without finishing or stopping the previous one")
                return

            if not self._flag_init: 
                self._sys_err_label.setText("No Starting Directory selected!")
                return
            if not self._flag_out: 
                self._sys_err_label.setText("No Output Directory selected!")
                return

            selected = []
            for i in range(attributes_listbox.count()):
                if attributes_listbox.item(i).checkState() == Qt.Checked:
                    selected.append(i)

            if len(selected) == 0:
                self._sys_err_label.setText("No attributes selected!")
                return


            self.clear_sys_label();
            self._is_working = True
            self._pause_proc_button.setEnabled(True)
            self._stop_proc_button.setEnabled(True)
            self._output_log.clear()
            self._thread.start()
            
            self._start = time.perf_counter()

            try:
                self._taskmgr.start_process(out_selected_arff.text(), selected)
            except Exception as err:
                _stop_process()
                self._sys_err_label.setText(f'{err}')

        def _pause_process():
            if self._is_paused:
                self._is_paused = False
                self._pause_proc_button.setText("Pause")
            else:
                self._is_paused = True
                self._pause_proc_button.setText("Resume")
            self._taskmgr.pause_process(self._is_paused)
            
        def _stop_process():
            self.reset_buttons()
            self._taskmgr.stop_process()

        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)

        inout_vbox = QVBoxLayout()
        input_hbox = QHBoxLayout()

        in_select_arff_button = QPushButton('Select')
        in_select_arff_button.clicked.connect(_select_init_arff)
        input_hbox.addWidget(in_select_arff_button)

        in_selected_arff_label = QLabel('Selected init arff:')
        input_hbox.addWidget(in_selected_arff_label)

        in_selected_arff = QLineEdit()
        in_selected_arff.setReadOnly(True)
        in_selected_arff.setPlaceholderText("Press 'Select' to choose the starting arff")
        input_hbox.addWidget(in_selected_arff)
        input_hbox.addStretch()
        
        output_hbox = QHBoxLayout()

        out_select_arff_button = QPushButton('Select')
        out_select_arff_button.clicked.connect(_select_out_arff)
        output_hbox.addWidget(out_select_arff_button)

        out_selected_arff_label = QLabel('Selected out arff:')
        output_hbox.addWidget(out_selected_arff_label)

        out_selected_arff = QLineEdit()
        out_selected_arff.setReadOnly(True)
        out_selected_arff.setPlaceholderText("Press 'Select' to choose the output arff")
        output_hbox.addWidget(out_selected_arff)
        output_hbox.addStretch()

        inout_vbox.addLayout(input_hbox)
        inout_vbox.addLayout(output_hbox)

        attribute_vbox = QVBoxLayout()
        attributes_listbox = QListWidget()
        attribute_vbox.addWidget(attributes_listbox)
        
        output_log_vbox = QVBoxLayout()

        ctrl_button_hbox = QHBoxLayout()

        start_proc_button = QPushButton('Start')
        start_proc_button.clicked.connect(_start_process)
        ctrl_button_hbox.addWidget(start_proc_button)

        self._pause_proc_button = QPushButton('Pause')
        self._pause_proc_button.setEnabled(False)
        self._pause_proc_button.clicked.connect(_pause_process)
        ctrl_button_hbox.addWidget(self._pause_proc_button)

        self._stop_proc_button = QPushButton('Stop')
        self._stop_proc_button.setEnabled(False)
        self._stop_proc_button.clicked.connect(_stop_process)
        ctrl_button_hbox.addWidget(self._stop_proc_button)

        output_log_vbox.addLayout(ctrl_button_hbox)

        self._output_log = QTextEdit()
        self._output_log.setReadOnly(True)
        output_log_vbox.addWidget(self._output_log)
        output_log_vbox.addWidget(self._progress_bar)

        main_vbox = QVBoxLayout()

        input_gbox = QGroupBox("Input")
        input_gbox.setLayout(inout_vbox)
        main_vbox.addWidget(input_gbox)

        attributes_group = QGroupBox("Attributes")
        attributes_group.setLayout(attribute_vbox)
        main_vbox.addWidget(attributes_group)

        output_group = QGroupBox("Output")
        output_group.setLayout(output_log_vbox)
        main_vbox.addWidget(output_group)

        main_vbox.addWidget(self._sys_err_label)

        self.setLayout(main_vbox)
        self.setWindowTitle("PD3 arff")
        self.setGeometry(300, 300, 1024, 640)
        self.show()

def main():
    app = QApplication(sys.argv)
    ex = PyQtGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
