import sys
import os
import subprocess
from threading import Thread
from PyQt5.QtCore import QProcess, Qt, pyqtSignal, QTimer
from PyQt5.QtCore import QThread
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QHBoxLayout,
    QFileDialog, QTextEdit, QGroupBox, QRadioButton, QButtonGroup, QTabWidget, QMessageBox,
    QSplitter, QSizePolicy, QInputDialog, QListWidget
)
from PyQt5.QtGui import QTextCursor
import numpy as np
from math import sin, cos, sqrt
pi = np.pi

import datetime
import tempfile
# 예시 (공통 인자 정의)
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
import py3Dmol


LEFT_PANEL_WIDTH = 300
RIGHT_PANEL_WIDTH = 800
def resource_path(relative_path):
    """PyInstaller에서 빌드된 실행 파일과 개발 환경 모두에서 작동하는 경로 반환 함수"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
class LogReaderThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        for line in iter(self.process.stdout.readline, ''):
            if line:
                self.log_signal.emit(line.rstrip('\n'))
        self.process.stdout.close()
        return_code = self.process.wait()
        self.finished_signal.emit(return_code)

class RaspaGUI(QWidget):
    append_log_signal = pyqtSignal(str)
    set_cmd_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.current_cif_path = None
        self.current_cif_data = None
        self.prev_line_count = 0  # 이전에 읽은 줄 수
        # 먼저 WSL의 RASPA_DIR 읽어오기 (로그인 셸 사용)
        self.raspa_dir = "$HOME/.RASPA_GUI/RASPA2"
        print(f"RASPA_DIR: {self.raspa_dir}")
        self.initUI()
        QTimer.singleShot(100, self.apply_splitter_sizes)
        self.append_log_signal.connect(self.log_text.append)
        self.set_cmd_signal.connect(self.current_cmd_label.setText)
        
        # RASPA 환경 설치가 되어 있지 않으면 설치 진행
        check_cmd = 'bash -c "[ -d $HOME/.RASPA_GUI/RASPA2 ]"'
        if subprocess.call(check_cmd, shell=True) != 0:
            self.prompt_raspa_installation()

    def list_dirs_in_wsl(self, wsl_path):
        try:
            output = subprocess.check_output(
                ['wsl', 'bash', '--login', '-c', f'source ~/.bashrc && cd {wsl_path} && ls -d */']
            ).decode().strip()
            return [d.strip('/').strip() for d in output.split('\n') if d.strip()]
        except Exception as e:
            print(f"WSL 디렉토리 읽기 실패: {e}")
            return []

    def list_files_in_wsl(self, wsl_path):
        try:
            output = subprocess.check_output(
                ['wsl', 'bash', '--login', '-c', f'source ~/.bashrc && cd {wsl_path} && ls -p | grep -v /']
            ).decode().strip()
            return [f.strip() for f in output.split('\n') if f.strip()]
        except Exception as e:
            print(f"WSL 파일 읽기 실패: {e}")
            return []

    def apply_splitter_sizes(self):
        self.splitter.setSizes([LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH])

    def update_render_style(self):
        if self.current_cif_data:
            self.render_cif_data(self.current_cif_data)

    def initUI(self):
        self.setWindowTitle("RASPA 실행 GUI")
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_widget = QWidget()
        self.left_panel = QVBoxLayout(self.left_widget)
        self.splitter.addWidget(self.left_widget)

        # 우측 패널은 QTabWidget로 세 개의 탭 구성
        self.tabs = QTabWidget()
        # 탭1: 3D vis
        self.tab_3d = QWidget()
        self.tab_3d_layout = QVBoxLayout(self.tab_3d)
        self.web_view = QWebEngineView()
        self.web_view.setMinimumWidth(600)
        self.tab_3d_layout.addWidget(self.web_view)

        # 탭2: 설치로그
        self.tab_install_log = QWidget()
        self.tab_install_log_layout = QVBoxLayout(self.tab_install_log)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.tab_install_log_layout.addWidget(self.log_text)

        # 탭3: Output 로그
        self.tab_output = QWidget()
        self.tab_output_layout = QVBoxLayout(self.tab_output)
        from PyQt5.QtWidgets import QPlainTextEdit
        self.output_log_text = QPlainTextEdit()

        self.output_log_text.setReadOnly(True)
        self.tab_output_layout.addWidget(self.output_log_text)

        self.tabs.addTab(self.tab_3d, "3D vis")
        self.tabs.addTab(self.tab_install_log, "설치로그")
        self.tabs.addTab(self.tab_output, "Output 로그")

        # 추가로 현재 실행 명령 표시
        self.current_cmd_label = QLineEdit()
        self.current_cmd_label.setReadOnly(True)
        self.current_cmd_label.setPlaceholderText("현재 실행 중인 명령")

        # 우측 레이아웃 구성
        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.tabs)
        self.right_layout.addWidget(self.current_cmd_label)
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)
        self.right_widget.setMinimumWidth(RIGHT_PANEL_WIDTH)
        self.right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.splitter.addWidget(self.right_widget)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        # 좌측 입력 필드 구성
        self.inputs = {}
        fields = [
            ("NumberOfCycles", "1000"),
            ("NumberOfInitializationCycles", "100"),
            ("PrintEvery", "100"),
            ("RestartFile", [ "no", 'yes']),
            ("UseChargesFromCIFFile", [ "no","yes"]),
            ("ChargeFromChargeEquilibration", [ "no","yes"]),
            ("FrameworkName", ""),
            ("UnitCells", "MOF선택시 자동 계산"),
            ("ExternalTemperature", "298.0"),
            ("ExternalPressure", "1.0"),
            ("FugacityCoefficient", "1.0"),
            ("TranslationProbability", "0.5"),
            ("RotationProbability", "0.5"),
            ("ReinsertionProbability", "0.5"),
            ("SwapProbability", "0.5"),
            ("CreateNumberOfMolecules", "0")
        ]
        for field, default in fields:
            hbox = QHBoxLayout()
            label = QLabel(field)
            hbox.addWidget(label)
            if isinstance(default, list):
                combo = QComboBox()
                combo.addItems(default)
                self.inputs[field] = combo
                if field == "UnitCells":
                    combo.currentIndexChanged.connect(self.unit_cells_toggle)
                hbox.addWidget(combo)
            else:
                edit = QLineEdit()
                edit.setText(default)
                self.inputs[field] = edit
                hbox.addWidget(edit)
            self.left_panel.addLayout(hbox)
        self.unit_cells_input = QLineEdit("MOF선택시 자동 계산")
        self.unit_cells_input.setVisible(True)
        self.left_panel.addWidget(self.unit_cells_input)

        # Forcefield 및 MoleculeDefinition, MoleculeName 드롭다운 구성
        forcefield_list = self.list_dirs_in_wsl(f'{self.raspa_dir}/share/raspa/forcefield')
        moldef_list = self.list_dirs_in_wsl(f'{self.raspa_dir}/share/raspa/molecules')
        self.forcefield_combo = QComboBox()
        self.forcefield_combo.addItems(forcefield_list)
        self.inputs["Forcefield"] = self.forcefield_combo
        self.left_panel.addWidget(QLabel("Forcefield"))
        self.left_panel.addWidget(self.forcefield_combo)

        self.moldef_combo = QComboBox()
        self.moldef_combo.addItems(moldef_list)
        self.moldef_combo.currentIndexChanged.connect(self.update_molecule_list)
        self.inputs["MoleculeDefinition"] = self.moldef_combo
        self.left_panel.addWidget(QLabel("MoleculeDefinition"))
        self.left_panel.addWidget(self.moldef_combo)

        self.molname_combo = QComboBox()
        self.inputs["MoleculeName"] = self.molname_combo
        self.left_panel.addWidget(QLabel("MoleculeName"))
        self.left_panel.addWidget(self.molname_combo)
        self.update_molecule_list()

        self.select_cif_button = QPushButton("CIF 파일 선택 및 시각화")
        self.select_cif_button.clicked.connect(self.select_and_render_cif)
        self.left_panel.addWidget(self.select_cif_button)

        self.style_groupbox = QGroupBox("Style")
        self.style_buttons = QButtonGroup()
        self.style_layout = QVBoxLayout()
        self.styles = ["Ball-and-stick", "Space-filling", "Stick", "Wireframe"]
        for i, style in enumerate(self.styles):
            btn = QRadioButton(style)
            if i == 0:
                btn.setChecked(True)
            self.style_buttons.addButton(btn, i)
            self.style_layout.addWidget(btn)
        self.style_groupbox.setLayout(self.style_layout)
        self.left_panel.addWidget(self.style_groupbox)
        self.style_buttons.buttonClicked.connect(self.update_render_style)

        self.run_button = QPushButton("Run RASPA")
        self.run_button.clicked.connect(self.run_raspa)
        self.left_panel.addWidget(self.run_button)

    def update_molecule_list(self):
        selected = self.inputs["MoleculeDefinition"].currentText()
        mol_path = f'{self.raspa_dir}/share/raspa/molecules/{selected}'
        files = self.list_files_in_wsl(mol_path)
        names = [os.path.splitext(f)[0] for f in files]
        self.inputs["MoleculeName"].clear()
        self.inputs["MoleculeName"].addItems(names)
    def _get_si(self):
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None
    def cif2Ucell(self, cif, cutoff, Display=False):
        print(188)
        import numpy as np
        from math import pi, sqrt, cos, sin
        # WSL에서 cat 명령어로 cif 파일 내용 읽어오기 (cif 매개변수에 확장자 제외)

        try:
            print(16)

            cmd = ["wsl", "bash", "-c", f"cat {cif}"]
            print(16)
            f_data = subprocess.check_output(cmd,
                        creationflags=CREATE_NO_WINDOW).decode("utf-8")
            print(1)
            f_cont = f_data.splitlines()
            print(1)
        except Exception as e:
            print(f"Error reading {cif}.cif via WSL: {e}")
            return None

        print(1)
        deg2rad = pi / 180.
        n_a = len('_cell_length_a')
        n_b = len('_cell_length_b')
        n_c = len('_cell_length_c')
        n_alp = len('_cell_angle_alpha')
        n_bet = len('_cell_angle_beta')
        n_gam = len('_cell_angle_gamma')
        print(1)
        
        count_compl = 0
        for line in f_cont:
            if len(line) > n_a and line[:n_a] == '_cell_length_a':
                txt_tmp = line.split()
                a = float(txt_tmp[1])
                count_compl += 1
            if len(line) > n_b and line[:n_b] == '_cell_length_b':
                txt_tmp = line.split()
                b = float(txt_tmp[1])
                count_compl += 1
            if len(line) > n_c and line[:n_c] == '_cell_length_c':
                txt_tmp = line.split()
                c = float(txt_tmp[1])
                count_compl += 1
            if len(line) > n_alp and line[:n_alp] == '_cell_angle_alpha':
                txt_tmp = line.split()
                alpha = float(txt_tmp[1]) * deg2rad
                count_compl += 1
            if len(line) > n_bet and line[:n_bet] == '_cell_angle_beta':
                txt_tmp = line.split()
                beta = float(txt_tmp[1]) * deg2rad
                count_compl += 1
            if len(line) > n_gam and line[:n_gam] == '_cell_angle_gamma':
                txt_tmp = line.split()
                gamma = float(txt_tmp[1]) * deg2rad
                count_compl += 1
            if count_compl >= 6:
                break

        if Display:
            print('a = ', a)
            print('b = ', b)
            print('c = ', c)
            print('alpha = ', alpha/deg2rad, 'dgr')
            print('beta = ', beta/deg2rad, 'dgr')
            print('gamma = ', gamma/deg2rad, 'dgr')
        
        # compute cell vectors (refer to https://en.wikipedia.org/wiki/Fractional_coordinates)
        v = sqrt(1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + 2*cos(alpha)*cos(beta)*cos(gamma))
        cell = np.zeros((3,3))
        cell[0, :] = [a, 0, 0]
        cell[1, :] = [b * cos(gamma), b * sin(gamma), 0]
        cell[2, :] = [c * cos(beta), c * (cos(alpha) - cos(beta)*cos(gamma)) / sin(gamma), c * v / sin(gamma)]
        
        # Diagonal elements 사용하여 각 방향의 셀 반복 개수를 계산
        diag = np.diag(cell)
        nx, ny, nz = tuple(int(i) for i in np.ceil(cutoff/diag * 2))
        return nx, ny, nz

    def unit_cells_toggle(self):
        mode = self.inputs["UnitCells"].currentText()
        if mode == "직접지정":
            print(12)
            self.unit_cells_input.setVisible(True)
        else:
            print(12)
            print(13)
            mof_name = self.inputs["FrameworkName"].text()
            print(14)
            cif_path = "/".join([self.raspa_dir, "share", "raspa", "structures", "cif", f"{mof_name}.cif"])
            print(15)
            try:
                print(16)
                ucell =self.cif2Ucell(cif_path, 12.0, Display=False)
                self.unit_cells_input.setText(" ".join(map(str, ucell)))
                print(ucell)
                self.unit_cells_input.setVisible(True)
                print(ucell)
            except Exception as e:
                self.unit_cells_input.setText("오류")
                self.unit_cells_input.setVisible(True)

    def select_and_render_cif(self):
        # 1. WSL에서 MOF 리스트 가져오기 (.cif 확장자만)
        try:
            output = subprocess.check_output([
                "wsl", "bash", "-c",
                f"source ~/.bashrc && cd {self.raspa_dir}/share/raspa/structures/cif && ls *.cif"
            ],
                        creationflags=CREATE_NO_WINDOW).decode().strip()
            mof_list = sorted([os.path.splitext(line)[0] for line in output.splitlines()])
        except Exception as e:
            QMessageBox.critical(self, "CIF 파일 로드 실패", f"CIF 목록을 불러오는 중 오류 발생: {e}")
            return

        # 2. 리스트와 검색창 포함된 서브 창 생성
        dialog = QWidget()
        dialog.setWindowTitle("MOF 구조 선택")
        layout = QVBoxLayout(dialog)

        search_bar = QLineEdit()
        search_bar.setPlaceholderText("MOF 이름 검색 (예: IRMOF)")
        layout.addWidget(search_bar)

        list_widget = QListWidget()
        list_widget.addItems(mof_list)
        layout.addWidget(list_widget)

        select_button = QPushButton("선택 및 시각화")
        layout.addWidget(select_button)

        def filter_list():
            query = search_bar.text().lower()
            list_widget.clear()
            list_widget.addItems([name for name in mof_list if name.lower().startswith(query)])

        search_bar.textChanged.connect(filter_list)

        def on_select():
            selected_items = list_widget.selectedItems()
            if not selected_items:
                QMessageBox.warning(dialog, "선택 없음", "구조를 선택해주세요.")
                return
            selected_name = selected_items[0].text()
            dialog.close()
            self.inputs["FrameworkName"].setText(selected_name)
            # 3. 선택한 cif를 읽고 렌더링
            cif_path = f"{self.raspa_dir}/share/raspa/structures/cif/{selected_name}.cif"
            try:
                cif_data = subprocess.check_output([
                    "wsl", "bash", "-c", f"source ~/.bashrc && cat {cif_path}"
                ],
                        creationflags=CREATE_NO_WINDOW).decode()
                self.current_cif_data = cif_data
                self.render_cif_data(cif_data)

                # 4. unitcell 자동 계산 후 반영
                ucell = self.cif2Ucell(cif_path, 12.0)
                if ucell:
                    self.unit_cells_input.setText(" ".join(map(str, ucell)))
                    self.inputs["UnitCells"].setText(" ".join(map(str, ucell)))
                    self.unit_cells_input.setVisible(True)
            except Exception as e:
                QMessageBox.critical(self, "CIF 읽기 오류", str(e))

        select_button.clicked.connect(on_select)
        dialog.setLayout(layout)
        dialog.resize(400, 500)
        dialog.show()


    def render_cif_data(self, cif_data):
        if not cif_data.strip():
            self.web_view.setHtml("<h3>CIF 데이터가 비어 있습니다</h3>")
            return
        try:
            view = py3Dmol.view(width=600, height=600)
            view.addModel(cif_data, 'cif')
            selected_id = self.style_buttons.checkedId()
            selected_style = self.styles[selected_id]
            style_map = {
                "Ball-and-stick": {'sphere': {'scale': 0.3}, 'stick': {}},
                "Space-filling": {'sphere': {'scale': 1.0}},
                "Stick": {'stick': {}},
                "Wireframe": {'line': {}}
            }
            py3dmol_style = style_map.get(selected_style, {'stick': {}})
            view.setStyle(py3dmol_style)
            view.zoomTo()
            self.web_view.setHtml(view._make_html())
        except Exception as e:
            self.web_view.setHtml(f"<h3>렌더링 실패: {e}</h3>")

    def generate_input_file(self):
        lines = []
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            lines.append(f"{key} {value}")
        input_content = "\n".join(lines)
        with open("input.data", "w") as f:
            f.write(input_content)
    def convert_win_to_wsl_path(self, win_path):
        # 예: C:\Users\xxx → /mnt/c/Users/xxx
        drive, rest = os.path.splitdrive(win_path)
        drive = drive[0].lower()
        rest = rest.replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    def on_simulation_finished(self, return_code):
        if hasattr(self, "output_timer"):
             self.output_timer.stop()
        if return_code != 0:
            self.output_log_text.appendPlainText(f"\n❌ simulate 실패 (return code: {return_code})")
        else:
            self.output_log_text.appendPlainText("\n✅ simulate 성공")
    def run_simulation_experiment(self):
        # 1. 사용자 입력값을 딕셔너리로 정리 (키는 템플릿의 {키}와 동일)
        data = {
            "NumberOfCycles": self.inputs["NumberOfCycles"].text(),
            "NumberOfInitializationCycles": self.inputs["NumberOfInitializationCycles"].text(),
            "PrintEvery": self.inputs["PrintEvery"].text(),
            "RestartFile": self.inputs["RestartFile"].currentText() if isinstance(self.inputs["RestartFile"], QComboBox) else self.inputs["RestartFile"].text(),
            "Forcefield": self.inputs["Forcefield"].currentText() if isinstance(self.inputs["Forcefield"], QComboBox) else self.inputs["Forcefield"].text(),
            "UseChargesFromCIFFile": self.inputs["UseChargesFromCIFFile"].currentText() if isinstance(self.inputs["UseChargesFromCIFFile"], QComboBox) else self.inputs["UseChargesFromCIFFile"].text(),
            "ChargeFromChargeEquilibration": self.inputs["ChargeFromChargeEquilibration"].currentText() if isinstance(self.inputs["ChargeFromChargeEquilibration"], QComboBox) else self.inputs["ChargeFromChargeEquilibration"].text(),
            "FrameworkName": self.inputs["FrameworkName"].text(),
            "UnitCells": self.unit_cells_input.text(),
            "ExternalTemperature": self.inputs["ExternalTemperature"].text(),
            "ExternalPressure": self.inputs["ExternalPressure"].text(),
            "FugacityCoefficient": self.inputs["FugacityCoefficient"].text(),
            "TranslationProbability": self.inputs["TranslationProbability"].text(),
            "RotationProbability": self.inputs["RotationProbability"].text(),
            "ReinsertionProbability": self.inputs["ReinsertionProbability"].text(),
            "SwapProbability": self.inputs["SwapProbability"].text(),
            "CreateNumberOfMolecules": self.inputs["CreateNumberOfMolecules"].text(),
            "MoleculeName": self.inputs["MoleculeName"].currentText() if isinstance(self.inputs["MoleculeName"], QComboBox) else self.inputs["MoleculeName"].text(),
            "MoleculeDefinition": self.inputs["MoleculeDefinition"].currentText() if isinstance(self.inputs["MoleculeDefinition"], QComboBox) else self.inputs["MoleculeDefinition"].text()
        }
        # 2. 템플릿 파일 읽기 ("static/00_template.input")
        template_path = resource_path("static/00_template.input")
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        sim_input_content = template.format(**data)
        # 3. 실험 폴더 이름 생성: FrameworkName_MoleculeName_ExternalPressure_ExternalTemperature_YYYYMMDD
        today = datetime.datetime.now().strftime("%Y%m%d")
        folder_name = f"{data['FrameworkName']}_{data['MoleculeName']}_{data['ExternalPressure']}_{data['ExternalTemperature']}_{today}"
        exp_folder_cmd = f"$HOME/.RASPA_GUI/00_experiments/{folder_name}"
        # 4. WSL에서 실험 폴더 생성 (mkdir -p)
        subprocess.run(["wsl", "bash", "-c", f"source ~/.bashrc && mkdir -p {exp_folder_cmd}"], check=True,
                        creationflags=CREATE_NO_WINDOW)
        # 5. simulation.input 파일을 임시 파일로 작성
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".input")
        temp_file.write(sim_input_content)
        temp_file.close()

        # ⭐ 여기서 WSL 경로로 변환
        wsl_temp_path = self.convert_win_to_wsl_path(temp_file.name)

        # 6. 해당 파일을 WSL의 실험 폴더로 복사
        subprocess.run(["wsl", "bash", "-c", f"source ~/.bashrc && cp {wsl_temp_path} {exp_folder_cmd}/simulation.input"], check=True,
                        creationflags=CREATE_NO_WINDOW)
        # 7. 로컬 임시 파일 삭제
        os.remove(temp_file.name)
        # 8. WSL에서 해당 폴더로 이동한 후 simulation 실행
# 8. WSL에서 해당 폴더로 이동한 후 simulation 실행
        sim_cmd = (
            "export RASPA_DIR=$HOME/.RASPA_GUI/RASPA2 && "
            "export LD_LIBRARY_PATH=$HOME/.RASPA_GUI/RASPA2/lib && "
            f"cd {exp_folder_cmd} && "
            "echo '>>> 현재 디렉토리: ' $(pwd) && "
            "echo '>>> 실행 중: $HOME/.RASPA_GUI/RASPA2/bin/simulate simulation.input &&' "
            f"cd {exp_folder_cmd} && $HOME/.RASPA_GUI/RASPA2/bin/simulate simulation.input"
        )
        self.exp_folder = exp_folder_cmd
        # 실행 로그 확인을 위해 subprocess.Popen + stdout/stderr 캡처
       # 기존 Popen을 실행만 하고 끝내는 subprocess.run() 대신

    ###############
    ###############
    ###############
    ###############
    ###############
    ############### cd 하고 simulate를 같은 문자열내에위치시켜야 됬음. 다른 문자열이면 후속 명령이라도 다른 셀로인식하나봄봄
    ###############
    ###############
    ###############
    ###############
    ###############
    ###############
        process = subprocess.Popen(
            ["wsl", "bash", "-c", f"source ~/.bashrc && {sim_cmd}"],
            stdout=subprocess.PIPE, ## 이게 없으니까 되네
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding= 'utf8',
            creationflags=subprocess.CREATE_NO_WINDOW  # 👈 콘솔 창 비활성화
        )
        # QThread를 이용한 로그 읽기 쓰레드 시작
        ## Popen이 실행되고 나서 stdout을 읽지 않으면 WSL 쪽에서 simulate 실행이 멈춤
        self.log_thread = LogReaderThread(process)
        self.log_thread.log_signal.connect(self.output_log_text.appendPlainText)
        self.log_thread.finished_signal.connect(self.on_simulation_finished)
        self.log_thread.start()
        self.start_polling_output_log()

    def start_polling_output_log(self):
        self.output_timer = QTimer(self)
        self.output_timer.timeout.connect(self.poll_output_log)
        self.output_timer.start(300)  # 3초마다
    def poll_output_log(self):
        output_folder = f"{self.exp_folder}/Output/System_0"
        try:
            output = subprocess.check_output(
                ["wsl", "bash", "-c", f"source ~/.bashrc && cd {output_folder} && ls *.data"],
                startupinfo=self._get_si()
            ).decode().strip()

            if not output:
                return

            data_file = output.split("\n")[0]
            file_content = subprocess.check_output(
                ["wsl", "bash", "-c", f"source ~/.bashrc && cat {output_folder}/{data_file}"],
                startupinfo=self._get_si()
            ).decode(errors='ignore').splitlines()

            new_lines = file_content[self.prev_line_count:]
            if new_lines:
                self.output_log_text.appendPlainText("\n".join(new_lines))
                self.prev_line_count += len(new_lines)

                # ⭐ "Starting simulation" 문구를 찾았으면 타이머 속도 조정
                for line in new_lines:
                    if "Starting simulation" in line:
                        self.output_timer.setInterval(300)  # 0.3초
                        break
            else:
                # 아직 output 생성 안 됐거나 progress 없음
                self.output_timer.setInterval(1500)  # 느린 폴링
        except Exception as e:
            self.output_log_text.appendPlainText(f"\n⚠️ 로그 업데이트 실패: {e}")
    # 기존 run_raspa() 함수 대신 아래로 대체
    def run_raspa(self):
        # 빈 항목 검증 (생략 가능)
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                QMessageBox.warning(self, "입력 누락", f"{key} 항목이 비어 있습니다.")
                return
            elif isinstance(widget, QComboBox) and not widget.currentText().strip():
                QMessageBox.warning(self, "입력 누락", f"{key} 항목이 선택되지 않았습니다.")
                return
        self.run_simulation_experiment()

    def prompt_raspa_installation(self):
        reply = QMessageBox.question(
            self, "RASPA 환경 감지 안됨",
            "RASPA 환경 구성이 감지되지 않습니다.\n설정을 진행하시겠습니까? (C드라이브 약 200MB 필요, 10~20분 소요)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            cpu_check = subprocess.run(["wsl", "nproc"],
                        creationflags=CREATE_NO_WINDOW, stdout=subprocess.PIPE, text=True)
            cpu_count = cpu_check.stdout.strip()
            num, ok = QInputDialog.getInt(
                self, "병렬 CPU 설정",
                f"WSL에서 사용 가능한 CPU: {cpu_count}\n사용할 CPU 개수를 입력하세요:",
                min=1, max=int(cpu_count)
            )
            if ok:
                self.check_and_install_raspa(cpu_threads=num)

    def check_and_install_raspa(self, cpu_threads=4):
        def run_setup():
            base_path = "$HOME/.RASPA_GUI"
            commands = [
                f"mkdir -p {base_path}",
                f"cd {base_path} && pwd",
                f"cd {base_path} && if [ ! -d RASPA2 ]; then git clone https://github.com/iRASPA/RASPA2.git; fi",
                "echo 'export RASPA_DIR=$HOME/.RASPA_GUI/RASPA2' >> ~/.bashrc",
                "echo 'export DYLD_LIBRARY_PATH=${RASPA_DIR}/lib' >> ~/.bashrc",
                "echo 'export LD_LIBRARY_PATH=${RASPA_DIR}/lib' >> ~/.bashrc",
                "source ~/.bashrc",
                f"cd {base_path}/RASPA2 && rm -rf autom4te.cache",
                f"cd {base_path}/RASPA2 && mkdir -p m4",
                f"cd {base_path}/RASPA2 && libtoolize",
                f"cd {base_path}/RASPA2 && aclocal",
                f"cd {base_path}/RASPA2 && autoreconf -i",
                f"cd {base_path}/RASPA2 && automake --add-missing",
                f"cd {base_path}/RASPA2 && autoconf",
                "cd $HOME/.RASPA_GUI/RASPA2 && ./configure --prefix=$HOME/.RASPA_GUI/RASPA2",
                f"cd $HOME/.RASPA_GUI/RASPA2 && make -j {cpu_threads}",
                f"cd $HOME/.RASPA_GUI/RASPA2 && make install -j {cpu_threads}"
            ]
            with open("./log.log", "w", encoding="utf-8") as log_file:
                for cmd in commands:
                    self.set_cmd_signal.emit(cmd)
                    log_file.write(f"\n[COMMAND] {cmd}\n")
                    log_file.flush()
                    process = subprocess.Popen(["wsl", "bash", "-c", cmd],
                                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        creationflags=CREATE_NO_WINDOW)
                    for line in iter(process.stdout.readline, b''):
                        decoded = line.decode(errors='ignore')
                        self.append_log_signal.emit(decoded)
                        log_file.write(decoded)
                        log_file.flush()
                    process.stdout.close()
                    process.wait()
        Thread(target=run_setup).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = RaspaGUI()
    gui.show()
    sys.exit(app.exec_())
