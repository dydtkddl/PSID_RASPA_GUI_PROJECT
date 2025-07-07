from PyQt5.QtCore import QProcess, Qt, pyqtSignal, QTimer
from PyQt5.QtCore import QThread
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QHBoxLayout,
    QFileDialog, QTextEdit, QGroupBox, QRadioButton, QButtonGroup, QTabWidget, QMessageBox,
    QSplitter, QSizePolicy, QInputDialog, QListWidget
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QPlainTextEdit
from threading import Thread
import numpy as np
from math import sin, cos, sqrt
import datetime
import tempfile
import py3Dmol
import subprocess
from .utils import resource_path, LogReaderThread
import sys
import json 
import os 
import shutil
import webbrowser
import tempfile
pi = np.pi
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class RaspaGUI(QWidget):
    append_log_signal = pyqtSignal(str)
    set_cmd_signal = pyqtSignal(str)
    ## GUI 초기화 및 WSL 환경에서 RASPA 설치 여부 확인 후 필요 시 설치 유도.
    def __init__(self):
        super().__init__()
        with open("./src/config.json" , 'r') as f:
            self.CONFIG = json.load(f)
        self.raspa_dir = self.CONFIG["raspa_dir"]
        print(f"RASPA_DIR: {self.raspa_dir}")
        self.LEFT_PANEL_WIDTH = self.CONFIG["LEFT_PANEL_WIDTH"]
        self.RIGHT_PANEL_WIDTH = self.CONFIG["RIGHT_PANEL_WIDTH"]

        self.current_cif_path = None
        self.current_cif_data = None
        self.prev_line_count = 0  # 이전에 읽은 줄 수
        # 먼저 WSL의 RASPA_DIR 읽어오기 (로그인 셸 사용)
        self.initUI()
        QTimer.singleShot(100, self.apply_splitter_sizes)
        self.append_log_signal.connect(self.log_text.append)
        self.set_cmd_signal.connect(self.current_cmd_label.setText)
        
        # RASPA 환경 설치가 되어 있지 않으면 설치 진행
        check_cmd = '[ -f $HOME/.RASPA_GUI/RASPA2/bin/simulate ]'
        if subprocess.call(check_cmd, shell=True) != 0:
            self.prompt_raspa_installation()
    # RASPA 환경이 없는 경우 설치 여부 묻는 팝업 창을 띄움.
####################
####   Install   ###
####################
    def prompt_raspa_installation(self):
        reply = QMessageBox.question(
            self, "RASPA 환경 감지 안됨",
            "RASPA 환경 구성이 감지되지 않습니다.\n설정을 진행하시겠습니까? (C드라이브 약 200MB 필요, 10~20분 소요)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            cpu_check = subprocess.run(["nproc"],
                        creationflags=CREATE_NO_WINDOW, stdout=subprocess.PIPE, text=True)
            cpu_count = cpu_check.stdout.strip()
            num, ok = QInputDialog.getInt(
                self, "병렬 CPU 설정",
                f"WSL에서 사용 가능한 CPU: {cpu_count}\n사용할 CPU 개수를 입력하세요:",
                min=1, max=int(cpu_count)
            )
            if ok:
                self.check_and_install_raspa(cpu_threads=num)
        ##RASPA 설치 전체 자동화 프로세스 수행:
        # .bashrc 업데이트
        # git clone, autoconf, make, make install
        # 설치 로그 파일 저장 및 실시간 GUI 로그 출력
    def check_and_install_raspa(self, cpu_threads=4):
        def run_setup():
            self.tabs.setCurrentWidget(self.tab_install_log)
            self.append_log_signal.emit("🔧 RASPA 설치를 시작합니다...\n")

            base_path = "$HOME/.RASPA_GUI"
            commands = [
                f"mkdir -p {base_path}",
                f"cd {base_path} && pwd",
                f"cd {base_path} && if [ ! -d RASPA2 ]; then git clone https://github.com/iRASPA/RASPA2.git; fi",
                f"echo 'export RASPA_DIR={self.raspa_dir}' >> ~/.bashrc",
                "echo 'export DYLD_LIBRARY_PATH=${RASPA_DIR}/lib' >> ~/.bashrc",
                "echo 'export LD_LIBRARY_PATH=${RASPA_DIR}/lib' >> ~/.bashrc",
                "bash -c 'source ~/.bashrc'",
                f"cd {self.raspa_dir} && rm -rf autom4te.cache",
                f"cd {self.raspa_dir} && mkdir -p m4",
                f"cd {self.raspa_dir} && libtoolize",
                f"cd {self.raspa_dir} && aclocal",
                f"cd {self.raspa_dir} && autoreconf -i",
                f"cd {self.raspa_dir} && automake --add-missing",
                f"cd {self.raspa_dir} && autoconf",
                f"cd {self.raspa_dir} && ./configure --prefix={self.raspa_dir}",
                f"cd {self.raspa_dir} && make -j {cpu_threads}",
                f"cd {self.raspa_dir} && make install -j {cpu_threads}",
                f"cd {self.raspa_dir} && cd share/raspa/forcefield/ && mkdir GarciaPerez2006ForceField && cd GarciaPerez2006ForceField && wget https://github.com/dydtkddl/PSID_server_room/blob/main/simulations/%5B02%5DRASPA/share/raspa/forcefield/GarciaPerez2006ForceField/force_field_mixing_rules.def && wget https://github.com/dydtkddl/PSID_server_room/blob/main/simulations/%5B02%5DRASPA/share/raspa/forcefield/GarciaPerez2006ForceField/pseudo_atoms.def",
                "sudo apt install firefox"
            ]

            with open("./log.log", "w", encoding="utf-8") as log_file:
                for cmd in commands:
                    self.set_cmd_signal.emit(f"> 실행 중: {cmd}")
                    log_file.write(f"\n[COMMAND] {cmd}\n")
                    log_file.flush()

                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        encoding='utf-8'
                    )

                    for line in iter(process.stdout.readline, ''):
                        self.append_log_signal.emit(line)
                        log_file.write(line)
                        log_file.flush()

                    process.stdout.close()
                    retcode = process.wait()

                    # 에러 감지 시 강조 출력
                    if retcode != 0:
                        error_msg = f"\n> 실패: '{cmd}' (exit code: {retcode})\n"
                        self.append_log_signal.emit(error_msg)
                        log_file.write(error_msg)
                        log_file.flush()
                        break  # 에러 발생 시 즉시 중단

                else:
                    self.append_log_signal.emit("\n> RASPA 설치가 성공적으로 완료되었습니다.\n")
                    log_file.write("\n[SUCCESS] RASPA installation completed.\n")
            self.update_after_installation()
            
        Thread(target=run_setup).start()
    def update_after_installation(self):
        forcefield_list = self.list_dirs_in_wsl(f'{self.raspa_dir}/share/raspa/forcefield')
        moldef_list = self.list_dirs_in_wsl(f'{self.raspa_dir}/share/raspa/molecules')

        self.forcefield_combo.clear()
        self.forcefield_combo.addItems(forcefield_list)

        self.moldef_combo.clear()
        self.moldef_combo.addItems(moldef_list)

        self.update_molecule_list()
############################
####   linux command   ###
############################
    def list_dirs_in_wsl(self, wsl_path):
        try:
            output = subprocess.check_output(
                f'cd {wsl_path} && ls -d */',
                shell=True,
                encoding='utf-8'
            ).strip()
            return [d.strip('/').strip() for d in output.split('\n') if d.strip()]
        except Exception as e:
            print(f"디렉토리 읽기 실패: {e}")
            return []
    ## 지정한 WSL 경로의 파일 목록 반환 (ls -p | grep -v /)
    def list_files_in_wsl(self, wsl_path):
        try:
            output = subprocess.check_output(
                f'cd {wsl_path} && ls -p | grep -v /',
                shell=True,
                encoding='utf-8'
            ).strip()
            return [f.strip() for f in output.split('\n') if f.strip()]
        except Exception as e:
            print(f"파일 읽기 실패: {e}")
            return []
    ## 좌우 패널의 기본 크기 설정 (splitter.setSizes() 이용).
################
####   UI   ###
################
    def apply_splitter_sizes(self):
        self.splitter.setSizes([self.LEFT_PANEL_WIDTH, self.RIGHT_PANEL_WIDTH])
    ## 선택한 py3Dmol 스타일에 따라 구조 시각화 재렌더링.
    def update_render_style(self):
        if self.current_cif_data:
            self.render_cif_data(self.current_cif_data)
    # 전체 GUI 위젯 구성.
    # 좌측 패널: 사용자 입력 및 구조 선택
    # 우측 패널: 탭 구성 (3D view, 설치 로그, Output 로그)
    def initUI(self):
        self.setWindowTitle("RASPA GUI")
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
        self.right_widget.setMinimumWidth(self.RIGHT_PANEL_WIDTH)
        self.right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.splitter.addWidget(self.right_widget)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        # 좌측 입력 필드 구성
        self.inputs = {}
        fields = self.CONFIG["field"]
        for f in fields:
            field = f["key"]
            default = f["value"]
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
        print(forcefield_list)
        moldef_list = self.list_dirs_in_wsl(f'{self.raspa_dir}/share/raspa/molecules')
        # 기본값 로드
        defaults = self.CONFIG.get("defaults", {})
        default_forcefield = defaults.get("Forcefield", "")
        default_moldef = defaults.get("MoleculeDefinition", "")
        default_molname = defaults.get("MoleculeName", "")
        # Forcefield
        self.forcefield_combo = QComboBox()
        self.forcefield_combo.addItems(forcefield_list)
        if default_forcefield in forcefield_list:
            self.forcefield_combo.setCurrentText(default_forcefield)
        self.inputs["Forcefield"] = self.forcefield_combo
        self.left_panel.addWidget(QLabel("Forcefield"))
        self.left_panel.addWidget(self.forcefield_combo)

        # MoleculeDefinition
        self.moldef_combo = QComboBox()
        self.moldef_combo.addItems(moldef_list)
        if default_moldef in moldef_list:
            self.moldef_combo.setCurrentText(default_moldef)
        self.moldef_combo.currentIndexChanged.connect(self.update_molecule_list)
        self.inputs["MoleculeDefinition"] = self.moldef_combo
        self.left_panel.addWidget(QLabel("MoleculeDefinition"))
        self.left_panel.addWidget(self.moldef_combo)

        # MoleculeName: moldef 콤보박스 이후 update_molecule_list 호출 시점에 설정
        self.molname_combo = QComboBox()
        self.inputs["MoleculeName"] = self.molname_combo
        self.left_panel.addWidget(QLabel("MoleculeName"))
        self.left_panel.addWidget(self.molname_combo)
        self.update_molecule_list()
        if default_molname:
            self.molname_combo.setCurrentText(default_molname)

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
    ## MoleculeDefinition 선택에 따라 해당 디렉토리 내 molecule 리스트를 업데이트.
    def update_molecule_list(self):
        selected = self.inputs["MoleculeDefinition"].currentText()
        mol_path = f'{self.raspa_dir}/share/raspa/molecules/{selected}'
        files = self.list_files_in_wsl(mol_path)
        names = [os.path.splitext(f)[0] for f in files]
        self.inputs["MoleculeName"].clear()
        self.inputs["MoleculeName"].addItems(names)
    ## Windows용 STARTUPINFO() 설정 반환 (콘솔 숨기기 목적).
    def _get_si(self):
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None
    ## CIF 파일로부터 격자 벡터 정보를 읽어들여 cutoff 길이에 기반한 UnitCell 반복 개수 계산.
    def cif2Ucell(self, cif, cutoff, Display=False):
        from math import pi, sqrt, cos, sin
        # WSL에서 cat 명령어로 cif 파일 내용 읽어오기 (cif 매개변수에 확장자 제외)
        try:
            # 확장자가 없으면 자동 추가
            if not cif.endswith(".cif"):
                cif += ".cif"
            
            if not os.path.exists(cif):
                raise FileNotFoundError(f"{cif} not found")

            # subprocess에서 shell=False 권장
            cmd = ["cat", cif]
            f_data = subprocess.check_output(cmd, creationflags=CREATE_NO_WINDOW).decode("utf-8")
            f_cont = f_data.splitlines()

        except Exception as e:
            print(f"Error reading {cif} via WSL: {e}")
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
    ## UnitCell 모드가 '직접지정'이 아닌 경우, CIF 기반 자동 계산 실행.
    def unit_cells_toggle(self):
        mode = self.inputs["UnitCells"].currentText()
        if mode == "직접지정":
            print(12)
            self.unit_cells_input.setVisible(True)
        else:
            mof_name = self.inputs["FrameworkName"].text()
            cif_path = os.path.join(os.environ["HOME"], ".RASPA_GUI", "RASPA2", "share", "raspa", "structures", "cif", "CAN-12.cif")
            try:
                ucell =self.cif2Ucell(cif_path, 12.0, Display=False)
                self.unit_cells_input.setText(" ".join(map(str, ucell)))
                print(ucell)
                self.unit_cells_input.setVisible(True)
                print(ucell)
            except Exception as e:
                self.unit_cells_input.setText("오류")
                self.unit_cells_input.setVisible(True)
    ## 사용자로 하여금 MOF 구조 선택 및 py3Dmol 시각화 실행.
    # .cif 파일 내용 로드 + 구조 렌더링 + UnitCell 자동 계산 수행.
    def select_and_render_cif(self):
        # 1. MOF 리스트 가져오기 (.cif 확장자만)
        try:
            cmd = f"cd {self.raspa_dir}/share/raspa/structures/cif && ls *.cif"
            output = subprocess.check_output(
                cmd, shell=True, encoding="utf-8"
            ).strip()
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
            cif_path = os.path.join(os.environ["HOME"], ".RASPA_GUI", "RASPA2", "share", "raspa", "structures", "cif", "CAN-12.cif")
            try:
                cif_data = subprocess.check_output(
                    f"cat {cif_path}", shell=True, encoding="utf-8"
                )
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

    ## 전달받은 CIF 문자열 데이터를 py3Dmol로 렌더링 후 웹뷰에 표시.
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
    # def render_cif_data(self, cif_data):
    #     if not cif_data.strip():
    #         QMessageBox.warning(self, "CIF 데이터 오류", "CIF 데이터가 비어 있습니다.")
    #         return

    #     try:
    #         view = py3Dmol.view(width=800, height=600)
    #         view.addModel(cif_data, 'cif')
    #         selected_id = self.style_buttons.checkedId()
    #         selected_style = self.styles[selected_id]
    #         style_map = {
    #             "Ball-and-stick": {'sphere': {'scale': 0.3}, 'stick': {}},
    #             "Space-filling": {'sphere': {'scale': 1.0}},
    #             "Stick": {'stick': {}},
    #             "Wireframe": {'line': {}}
    #         }
    #         view.setStyle(style_map.get(selected_style, {'stick': {}}))
    #         view.zoomTo()

    #         html = view._make_html()

    #         with tempfile.NamedTemporaryFile(mode='w', suffix=".html", delete=False, encoding='utf-8') as tmp:
    #             tmp.write(html)
    #             tmp_path = tmp.name

    #         # 외부 웹브라우저로 자동 열기
                        
    #         # 강제로 Firefox로 열기
    #         webbrowser.get("firefox").open(f"file://{tmp_path}")


    #         self.append_log_signal.emit("🌐 외부 브라우저로 구조 시각화를 띄웠습니다.")
    #     except Exception as e:
    #         QMessageBox.critical(self, "렌더링 실패", f"py3Dmol 렌더링 중 오류 발생: {e}")

    ## 현재 입력값을 모아 RASPA용 input.data 파일 생성.
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

    # 시뮬레이션 완료 후 타이머 종료 및 성공/실패 로그 출력.
    def on_simulation_finished(self, return_code):
        if hasattr(self, "output_timer"):
             self.output_timer.stop()
        if return_code != 0:
            self.output_log_text.appendPlainText(f"\n> simulate 실패 (return code: {return_code})")
        else:
            self.output_log_text.appendPlainText("\n> simulate 성공")

    # 전체 실행 절차:
    # 입력 수집 및 템플릿 렌더링
    # WSL 경로에 실험 디렉토리 생성
    # 입력 파일 전송
    # simulate 실행 명령어 구성 및 subprocess 실행
    # stdout/stderr 스트리밍 및 로그 쓰레드 시작

    def run_simulation_experiment(self):
        # 1. 사용자 입력값 수집
        data = { key: (widget.currentText() if isinstance(widget, QComboBox) else widget.text())
                for key, widget in self.inputs.items() }
        data["UnitCells"] = self.unit_cells_input.text()

        # 2. 템플릿 처리
        with open(resource_path("static/00_template.input"), "r", encoding="utf-8") as f:
            sim_input_content = f.read().format(**data)

        # 3. 실험 폴더 이름 생성
        today = datetime.datetime.now().strftime("%Y%m%d")
        folder_name = f"{data['FrameworkName']}_{data['MoleculeName']}_{data['ExternalPressure(kPa)']}_{data['ExternalTemperature(K)']}_{today}"
        exp_folder = os.path.expandvars(f"$HOME/.RASPA_GUI/00_experiments/{folder_name}")

        # 4. 폴더 생성
        subprocess.run(f"mkdir -p {exp_folder}", shell=True, check=True)

        # 5. simulation.input 생성 및 복사
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".input")
        temp_file.write(sim_input_content)
        temp_file.close()

        shutil.copy(temp_file.name, os.path.join(exp_folder, "simulation.input"))
        os.remove(temp_file.name)

        # 6. 시뮬레이션 명령어 실행
        sim_cmd = (
            f"cd {exp_folder} && "
            f"$RASPA_DIR/bin/simulate simulation.input"
        )
        self.tabs.setCurrentWidget(self.tab_output)
        print(sim_cmd)
        self.exp_folder = exp_folder

        # 7. subprocess 실행
        process = subprocess.Popen(
            sim_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )

        # 8. 로그 쓰레드 시작
        self.log_thread = LogReaderThread(process)
        self.log_thread.log_signal.connect(self.output_log_text.appendPlainText)
        self.log_thread.finished_signal.connect(self.on_simulation_finished)
        self.log_thread.start()
        self.start_polling_output_log()

    ## QTimer를 통해 Output/System_0 디렉토리의 로그 파일을 주기적으로 확인.
    def start_polling_output_log(self):
        self.output_timer = QTimer(self)
        self.output_timer.timeout.connect(self.poll_output_log)
        self.output_timer.start(300)  # 3초마다
    # 새로운 .data 파일이 생기면, 그 중 새로 생성된 줄만 읽어서 로그에 추가.
    def poll_output_log(self):
        output_folder = f"{self.exp_folder}/Output/System_0"
        try:
            result = subprocess.check_output(
                f"cd {output_folder} && ls *.data",
                shell=True,
                encoding='utf-8'
            ).strip()

            if not result:
                return

            data_file = result.split("\n")[0]
            lines = subprocess.check_output(
                f"cat {output_folder}/{data_file}",
                shell=True,
                encoding='utf-8',
                errors='ignore'
            ).splitlines()

            new_lines = lines[self.prev_line_count:]
            if new_lines:
                self.output_log_text.appendPlainText("\n".join(new_lines))
                self.prev_line_count += len(new_lines)

                if any("Starting simulation" in line for line in new_lines):
                    self.output_timer.setInterval(300)
            else:
                self.output_timer.setInterval(1500)
        except Exception as e:
            self.output_log_text.appendPlainText(f"\n> 로그 업데이트 실패: {e}")

    # 기존 run_raspa() 함수 대신 아래로 대체
    # 입력 필드 누락 검증 → run_simulation_experiment() 실행.
    def run_raspa(self):
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                QMessageBox.warning(self, "입력 누락", f"{key} 항목이 비어 있습니다.")
                return
            elif isinstance(widget, QComboBox) and not widget.currentText().strip():
                QMessageBox.warning(self, "입력 누락", f"{key} 항목이 선택되지 않았습니다.")
                return
        self.run_simulation_experiment()

