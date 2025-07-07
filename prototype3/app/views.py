from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseNotAllowed
from django.shortcuts import render 
import json
from django.http import HttpResponse
from django.conf import settings
import os
import datetime
import os, signal
import re, json
from django.shortcuts import render, get_object_or_404,redirect
from django.http import Http404
# helpers.py  (app 디렉터리 아무 곳에 두세요)
import re
CONFIG_PATH = os.path.join(settings.BASE_DIR, 'config.json')
# 허용: 09(tab) 0A(newline) 0D(carriage return) 20~7E(표준 ASCII printable)
_control_re = re.compile(r'[^\x09\x0a\x0d\x20-\x7e]')

def sanitize(text: str) -> str:
    """브라우저에 깨지는 제어문자·NULL 제거."""
    return _control_re.sub('', text)

def raspa_alive(pid: int, target_cmd: str = 'simulate') -> bool:
    """
    True  → 시뮬레이션 프로세스가 실제로 실행 중
    False → 좀비이거나 다른 프로그램으로 재활용됐거나, 아예 사라짐
    """
    proc_path = f"/proc/{pid}"

    # 1) /proc/<pid>가 없으면 프로세스 종료
    if not os.path.exists(proc_path):
        return False

    try:
        # 2) 좀비(Z) 상태 검사
        with open(os.path.join(proc_path, "status")) as f:
            for line in f:
                if line.startswith("State:"):
                    # 예) "State:\tZ (zombie)"
                    if line.split()[1] == 'Z':
                        return False
                    break

        # 3) cmdline에 시뮬레이터 이름 포함 여부 확인
        with open(os.path.join(proc_path, "cmdline"), "rb") as f:
            cmd = f.read().split(b'\0')[0].decode()
        if target_cmd not in os.path.basename(cmd):
            return False

        # 4) 마지막으로 kill(0)로 존재 확인 (PermissionError 허용)
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    except FileNotFoundError:
        # /proc/<pid>/... 파일이 갑자기 사라진 경우
        return False
TEMPLATE_PATH = os.path.join(settings.BASE_DIR, '00_template.input')
SIMULATION_ROOT = os.path.join(settings.BASE_DIR, 'simulations')
import os
import json
import datetime
import subprocess
from django.conf import settings
from django.shortcuts import render, redirect

# 설정 JSON 경로
CONFIG_PATH = os.path.join(settings.BASE_DIR, 'config.json')
# RASPA 공유 디렉터리
RASPA_SHARE = os.path.join(settings.RASPA_DIR, 'share', 'raspa')
FORCEFIELD_DIR = os.path.join(RASPA_SHARE, 'forcefield')
MOLECULES_DIR = os.path.join(RASPA_SHARE, 'molecules', 'ExampleDefinitions')

# New Simulation 뷰
def new_simulation(request):
    if request.method == 'POST':
        post = request.POST
        # 시뮬레이션 폴더 생성
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        framework = post.get('FrameworkName', 'UnknownMOF')
        sim_dir = f"{framework}_{now}"
        out_dir = os.path.join(SIMULATION_ROOT, sim_dir)
        os.makedirs(out_dir, exist_ok=True)

        if framework != "UnKnownMOF" or framework != "" :
            print(framework)
            shutil.copy(os.path.join(RASPA_SHARE, "structures", "cif", framework+".cif"), os.path.join(out_dir, framework+".cif"))
        # 템플릿 치환 변수
        template_vars = {
            'SimulationType': 'MonteCarlo',
            'NumberOfCycles': post.get('NumberOfCycles'),
            'NumberOfInitializationCycles': post.get('NumberOfInitializationCycles'),
            'PrintEvery': post.get('PrintEvery'),
            'RestartFile': post.get('RestartFile'),
            'Forcefield': post.get('Forcefield'),
            'UseChargesFromCIFFile': post.get('UseChargesFromCIFFile'),
            'ChargeFromChargeEquilibration': post.get('ChargeFromChargeEquilibration'),
            'FrameworkName': framework,
            'UnitCells': post.get('UnitCells','').replace(',',' '),
            'ExternalTemperature(K)': post.get('ExternalTemperature(K)'),
            'ExternalPressure(kPa)': post.get('ExternalPressure(kPa)'),
            'MoleculeName': post.get('MoleculeName'),
            'MoleculeDefinition': post.get('MoleculeDefinition'),
            'FugacityCoefficient': post.get('FugacityCoefficient'),
            'TranslationProbability': post.get('TranslationProbability'),
            'RotationProbability': post.get('RotationProbability'),
            'ReinsertionProbability': post.get('ReinsertionProbability'),
            'SwapProbability': post.get('SwapProbability'),
            'CreateNumberOfMolecules': post.get('CreateNumberOfMolecules'),
        }
        # 템플릿 불러와 치환 후 저장
        with open(TEMPLATE_PATH, 'r') as f:
            tpl = f.read()
        for k,v in template_vars.items():
            tpl = tpl.replace(f"{{{k}}}", str(v or ''))
        with open(os.path.join(out_dir, 'simulation.input'),'w') as f:
            f.write(tpl)
        # RASPA 실행 (비동기)
        exe = os.path.join(settings.RASPA_DIR, 'bin', 'simulate')
        proc = subprocess.Popen([exe, 'simulation.input'], cwd=out_dir,
                                stdout=open(os.path.join(out_dir,'output.log'),'w'),
                                stderr=subprocess.STDOUT)
        with open(os.path.join(out_dir,'pid'),'w') as f:
            f.write(str(proc.pid))
        return redirect('simulation_detail', sim_name=sim_dir)

    # GET: 설정 로드 및 초기값 설정
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        conf = json.load(f)
    # defaults 가져오기
    defaults = conf.get('defaults', {})
    # Forcefield 목록
    forcefields = sorted([d for d in os.listdir(FORCEFIELD_DIR)
                          if os.path.isdir(os.path.join(FORCEFIELD_DIR, d))])
    # Molecule 목록 추출
    molecules = []
    for root,_,files in os.walk(MOLECULES_DIR):
        for fn in files:
            molecules.append(os.path.splitext(fn)[0])
    molecules = sorted(set(molecules))
    # config.field에도 selected 초기화
    for idx,f in enumerate(conf.get('field', [])):
        f.setdefault('selected', f['value'][0] if isinstance(f['value'],list) else f['value'])
    return render(request, 'app/new_simulation.html', {
        'config': conf,
        'defaults': defaults,
        'forcefields': forcefields,
        'molecules': molecules,
        'cif_dir': os.path.join(RASPA_SHARE,'structures','cif'),
    })
import os, subprocess, json, tempfile
from math import pi, sqrt, cos, sin
import numpy as np
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import re
def simulations(request):
    base_dir = os.path.join(settings.BASE_DIR, 'simulations')
    sims = []

    # 각 시뮬레이션 폴더 순회
    for name in sorted(os.listdir(base_dir)):
        folder = os.path.join(base_dir, name)
        if not os.path.isdir(folder):
            continue

        # 폴더 최종 수정 시각
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(folder))
        # 2) Output 폴더가 있는지 먼저 확인
        output_dir = os.path.join(folder, 'Output')
        if not os.path.isdir(output_dir):
            status = 'NO_OUTPUT'
        else:
            # 3) PID 파일 읽어서 상태 결정
            pid_file = os.path.join(folder, 'pid')
            if os.path.exists(pid_file):
                try:
                    pid = int(open(pid_file).read().strip())
                except (ValueError, IOError):
                    pid = None

                if pid and raspa_alive(pid):
                    status = 'RUNNING'
                else:
                    status = 'FINISHED'
            else:
                # Output 은 있는데 pid 파일이 없으면 이미 완료된 것으로 간주
                status = 'FINISHED'
        # simulation.input 파싱
        sim_in = os.path.join(folder, 'simulation.input')
        framework = gas = temp = pressure = None

        if os.path.exists(sim_in):
            with open(sim_in) as f:
                for line in f:
                    # "FrameworkName     [CoreMOF]..." 
                    m = re.match(r'^\s*FrameworkName\s+(.+)$', line)
                    if m:
                        framework = m.group(1).strip()
                        continue

                    # "ExternalTemperature     298.0"
                    m = re.match(r'^\s*ExternalTemperature\s+([0-9.]+)', line)
                    if m:
                        temp = m.group(1)
                        continue

                    # "ExternalPressure        101325"
                    m = re.match(r'^\s*ExternalPressure\s+([0-9.]+)', line)
                    if m:
                        pressure = m.group(1)
                        continue

                    # "Component 0 MoleculeName             helium"
                    m = re.match(r'^\s*Component\s+\d+\s+MoleculeName\s+(.+)$', line)
                    if m:
                        gas = m.group(1).strip()
                        continue
        # CIF 렌더링용 URL (프로젝트 설정에 맞춰 조정하세요)
        movie_dir = os.path.join("simulations",name, 'Movies', 'System_0')
        cif_url = None
        if os.path.isdir(movie_dir):
            for fn in os.listdir(movie_dir):
                if fn.lower().endswith('.cif') and 'initial' in fn.lower():
                    rel = os.path.relpath(os.path.join(movie_dir, fn), settings.BASE_DIR)
                    cif_url =rel.replace(os.path.sep, '/')
                    try:
                        cif_url = "/static/" + cif_url.replace("simulations", "")
                    except:
                        pass
                    # cif_url.replace("/static/simulations/", "")
                    break
        # def extract_core(filename: str) -> str:
        #     i = filename.rfind('_')
        #     return filename[:filename.rfind('_', 0, i)]
        # cif_url = os.path.join(settings.RASPA_DIR , "share", "raspa", "structures", "cif" ,extract_core(name) + ".cif")
        sims.append({
            'name': name,
            'modified': modified,
            'framework': framework or '—',
            'gas': gas or '—',
            'temp': temp or '—',
            'pressure': pressure or '—',
            'cif_url':  cif_url,
             'status': status,
        })
    return render(request, 'app/simulations.html', {
        'simulations': sims
    })

def cif2ucell(cif_path, cutoff, Display=False):
    """CIF 파일을 읽어 unit cell 반복 횟수(nx, ny, nz)를 계산합니다.
    중간 계산 값을 상세히 출력하도록 수정됨."""
    deg2rad = pi / 180.0

    # 1) CIF 읽기
    print(f"▶ Reading CIF file: {cif_path}")
    if not os.path.exists(cif_path):
        raise FileNotFoundError(f"{cif_path} not found")
    f_data = subprocess.check_output(["cat", cif_path]).decode("utf-8")
    lines = f_data.splitlines()
    print(f"   → Total lines read: {len(lines)}")

    # 2) cell parameters 파싱
    a = b = c = None
    alpha = beta = gamma = None
    count = 0
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue

        key, val = parts[0], parts[1]
        if key == '_cell_length_a':
            a = float(val); count += 1
        elif key == '_cell_length_b':
            b = float(val); count += 1
        elif key == '_cell_length_c':
            c = float(val); count += 1
        elif key == '_cell_angle_alpha':
            alpha = float(val) * deg2rad; count += 1
        elif key == '_cell_angle_beta':
            beta = float(val) * deg2rad; count += 1
        elif key == '_cell_angle_gamma':
            gamma = float(val) * deg2rad; count += 1

        if count >= 6:
            break

    print(f"▶ Parsed cell parameters:")
    print(f"   a = {a:.6f}, b = {b:.6f}, c = {c:.6f}")
    print(f"   α = {alpha:.6f} rad, β = {beta:.6f} rad, γ = {gamma:.6f} rad")

    # 3) cell 벡터 및 반복 횟수 계산
    v = sqrt(
        1.0
        - cos(alpha)**2
        - cos(beta)**2
        - cos(gamma)**2
        + 2.0 * cos(alpha) * cos(beta) * cos(gamma)
    )
    print(f"▶ Volume factor v = {v:.6f}")

    cell = np.zeros((3,3))
    cell[0,:] = [a, 0.0, 0.0]
    cell[1,:] = [b * cos(gamma), b * sin(gamma), 0.0]
    cell[2,:] = [
        c * cos(beta),
        c * (cos(alpha) - cos(beta) * cos(gamma)) / sin(gamma),
        c * v / sin(gamma)
    ]
    print("▶ Cell vectors (rows = a⃗, b⃗, c⃗):")
    for i, vec in enumerate(cell):
        print(f"   v{i+1} = [{vec[0]:.6f}, {vec[1]:.6f}, {vec[2]:.6f}]")

    diag = np.diag(cell)
    print(f"▶ Diagonal lengths (|a⃗|, |b⃗|, |c⃗|): {diag}")

    # 4) 반복 횟수
    nx = int(np.ceil(cutoff / diag[0] * 2))
    ny = int(np.ceil(cutoff / diag[1] * 2))
    nz = int(np.ceil(cutoff / diag[2] * 2))
    print(f"▶ Cutoff = {cutoff}")
    print(f"▶ Replication factors: nx = {nx}, ny = {ny}, nz = {nz}")

    if Display:
        print("▶ Display mode ON, returning full cell matrix and rep factors.")
        return cell, (nx, ny, nz)

    return nx, ny, nz

@require_POST
def ucell_api(request):
    print("1) API entry")
    
    # 2) 파일 수신 확인
    cif_file = request.FILES.get('cif_file')
    print("2) cif_file:", cif_file)
    
    # 3) cutoff 파라미터 확인
    cutoff_str = request.POST.get('cutoff')
    print("3) cutoff (raw):", cutoff_str)
    
    # 4) 필수 파라미터 검증
    if cif_file is None or cutoff_str is None:
        print("4) ERROR: missing cif_file or cutoff")
        return JsonResponse({'error': 'missing cif_file or cutoff'}, status=400)
    print("4) parameters OK")
    
    # 5) suffix 결정
    suffix = os.path.splitext(cif_file.name)[1] or '.cif'
    print("5) suffix:", suffix)
    
    # 6) 임시 파일 생성 및 저장
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            print("6) tmp path:", tmp.name)
            for i, chunk in enumerate(cif_file.chunks()):
                tmp.write(chunk)
                print(f"   - wrote chunk {i}, size={len(chunk)}")
            tmp_path = tmp.name
        print("6) tmp file saved:", tmp_path)
    except Exception as e:
        print("6) ERROR writing tmp file:", e)
        return JsonResponse({'error': f"temp file write error: {e}"}, status=500)
    
    # 7) cutoff 변환
    try:
        cutoff = float(cutoff_str)
        print("7) cutoff (float):", cutoff)
    except ValueError as e:
        print("7) ERROR converting cutoff:", e)
        os.remove(tmp_path)
        return JsonResponse({'error': f"invalid cutoff value: {cutoff_str}"}, status=400)
    
    # 8) cif2ucell 호출
    try:
        print("8) calling cif2ucell...")
        nx, ny, nz = cif2ucell(tmp_path, cutoff)
        print("8) cif2ucell result:", nx, ny, nz)
    except Exception as e:
        print("8) ERROR in cif2ucell:", e)
        os.remove(tmp_path)
        return JsonResponse({'error': str(e)}, status=500)
    
    # 9) 임시 파일 삭제
    try:
        os.remove(tmp_path)
        print("9) tmp file removed:", tmp_path)
    except OSError as e:
        print("9) WARNING removing tmp file:", e)
    
    # 10) 응답 전송
    print("10) sending response")
    return JsonResponse({'nx': nx, 'ny': ny, 'nz': nz})

cycle_re = re.compile(
    r'^Cycle\s+(\d+).+?Loading\s*=\s*([0-9.]+).+?Energy\s*=\s*([-0-9.]+)',
    re.I
)
import re, json, glob
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET

# ──────────────────────────────────────────────
# 정규식 ― .data 파일 한 줄에서 Cycle, Loading, Energy 를 뽑음
data_re = re.compile(
    r'^\s*(\d+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)'
)  # ex) 1000   1.234e+01   -5678.9

# ── 0) 상단에 새 정규식 추가 ───────────────────────────
cycle_re   = re.compile(r'^Current cycle:\s*(\d+)\s+out of\s+(\d+)', re.I)
ads_re_blk = re.compile(r'^Component \d+ \(([^)]+)\)', re.I)
ads_re_val = re.compile(r'absolute adsorption:.*?\(avg\.\s*([0-9.eE+-]+)', re.I)
from collections import defaultdict
from typing import Dict, Any, List

def extract_detail_siminput(folder: str) -> Dict[str, Any]:
    """
    simulation.input 파일을 파싱해 모든 설정값을 dict 형태로 반환.
    
    반환 구조
    ----------
    {
      "global": { ... },
      "frameworks": [
          {"index": 0, "FrameworkName": "...", "UnitCells": "3 2 2", ...},
          ...
      ],
      "components": [
          {"index": 0, "MoleculeName": "...", "RotationProbability": "0.5", ...},
          ...
      ]
    }
    """
    sim_input = os.path.join(folder, "simulation.input")
    if not os.path.exists(sim_input):
        raise FileNotFoundError(f"{sim_input} not found")

    # 결과 컨테이너
    result: Dict[str, Any] = {
        "global": {},
        "frameworks": [],
        "components": []
    }

    # 현재 파싱 중인 섹션 상태
    current_section = "global"
    current_dict = result["global"]
    current_index = None  # Framework/Component 번호

    # 패턴: "Key    value" (공백·탭 구분, 주석 없이)
    kv_pattern = re.compile(r"^\s*([\w]+(?:\s+[\w]+)*)\s+(.+?)\s*$")

    with open(sim_input, "r") as f:
        for raw in f:
            line = raw.strip()

            # 빈 줄 건너뛰기
            if not line:
                continue

            # 주석 줄(Section 헤더 포함) 처리
            if line.startswith("#"):
                # Section 헤더 예) "# Framework 0", "# Component 0"
                if line.startswith("# Framework"):
                    current_section = "framework"
                    current_index = int(line.split()[2])
                    # 새 딕셔너리 생성
                    current_dict = {"index": current_index}
                    result["frameworks"].append(current_dict)
                elif line.startswith("# Component"):
                    current_section = "component"
                    current_index = int(line.split()[2])
                    current_dict = {"index": current_index}
                    result["components"].append(current_dict)
                # 기타 주석은 무시
                continue

            # 실제 키–값 패턴 매칭
            m = kv_pattern.match(line)
            if m:
                key, value = m.groups()
                current_dict[key.strip()] = value.strip()

    return result
import re
from typing import List, Tuple, Optional

def extract_loading(text: str) -> List[Tuple[str, int, float, Optional[float]]]:
    """
    (phase, cycle, mol/kg, avg_mol/kg) 시계열 추출

    phase : 'init'   → 초기 블록
            'normal' → 러닝(실제 생산) 블록
    """
    series: List[Tuple[str, int, float, Optional[float]]] = []

    # ── 패턴 ──────────────────────────────────────────────
    pat_init_cycle  = re.compile(r"^\[Init\]\s*Current cycle:\s+(\d+)\s+out of", re.M)
    pat_cycle       = re.compile(r"^Current cycle:\s+(\d+)\s+out of", re.M)

    pat_ads_init    = re.compile(r"\[mol/uc\],\s+([-\d.Ee+]+)\s+\[mol/kg\]", re.M)
    pat_ads_normal  = re.compile(
        r"\[mol/uc\],\s+([-\d.Ee+]+)\s+\(avg\.\s+([-\d.Ee+]+)\)\s+\[mol/kg\]", re.M
    )
    # ─────────────────────────────────────────────────────

    current_cycle: Optional[int] = None
    phase: Optional[str] = None

    for line in text.splitlines():
        # 사이클 헤더 감지
        if (m := pat_init_cycle.match(line)):
            current_cycle = int(m.group(1))
            phase = 'init'
            continue
        if (m := pat_cycle.match(line)):
            current_cycle = int(m.group(1))
            phase = 'normal'
            continue

        # adsorption 행 파싱
        if current_cycle is not None and phase:
            if phase == 'init':
                if (m := pat_ads_init.search(line)):
                    molkg = float(m.group(1))
                    series.append((phase, current_cycle, molkg, None))
                    current_cycle = None
            else:  # 'normal'
                if (m := pat_ads_normal.search(line)):
                    molkg = float(m.group(1))
                    avg_molkg = float(m.group(2))
                    series.append((phase, current_cycle, molkg, avg_molkg))
                    current_cycle = None

    return series


def simulation_detail(request, sim_name):
    folder = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
    if not os.path.isdir(folder):
        raise Http404("Simulation not found")

    log_path   = os.path.join(folder, 'output.log')
    system_dir = os.path.join(folder, 'Output', 'System_0')

    # 1) 실행 로그 전문
    log_text = ''
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
            log_text = sanitize(fp.read())  
        # ── (2) loading 파싱 추가 ──
    print(os.listdir(folder) )
    ciffile = [ x for x in os.listdir(folder) if ".cif" in x ][0]
    with open(os.path.join(folder, ciffile) , 'r') as f:
        ciftext = f.read()
    # 2) 최신 .data 파일 전문
    data_file = ''
    data_text = ''
    if os.path.isdir(system_dir):
        data_file = os.path.join(system_dir, os.listdir(system_dir)[0])
        if data_file:
            with open(data_file, 'r', encoding='utf-8', errors='ignore') as fp:
                data_text = fp.read()
    loading_series = extract_loading(data_text )
    siminput_info = extract_detail_siminput(folder)
    print(loading_series, siminput_info)
    # 3) 상태
    status = 'NO_OUTPUT'
    pid_path = os.path.join(folder, 'pid')
    if os.path.isdir(system_dir):
        status = 'FINISHED'
        if os.path.exists(pid_path):
            try:
                pid = int(open(pid_path).read().strip())
                status = 'RUNNING' if raspa_alive(pid) else 'FINISHED'
            except:
                pass

    return render(request,'app/simulation_detail.html',{
        'sim_name': sim_name,
        'status':   status,
        'log_text': log_text,
        'data_text': data_text,
        'siminput_info': json.dumps(siminput_info),       # ★ 추가
        'load_series': json.dumps(loading_series),
        "NumberOfInitializationCycles"   :  siminput_info["global"]["NumberOfInitializationCycles"],
              # ★ 추가
              "ciftext" : ciftext
    })


# ─── 실시간 폴링 API ────────────────────────────────────────────
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def simulation_log_api(request, sim_name):
    """
    실시간 폴링
    리턴 JSON 구조
    -----------------------------------------------------------------------
    append      : 새로 추가된 output.log 문자열
    offset      : 다음 요청용 바이트 오프셋
    data_append : 새로 추가된 *.data 문자열
    data_bytes  : 다음 요청용 바이트 오프셋
    progress    : {'cur': int, 'tot': int}  |  None
    ads_avg     : float | None
    new_pts     : [{'cycle': int, 'comp': str, 'val': float}, …]  (로드 그래프용)
    -----------------------------------------------------------------------
    """
    root        = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
    log_path    = os.path.join(root, 'output.log')
    system_dir  = os.path.join(root, 'Output', 'System_0')

    # ── 1) output.log 추가분 ──────────────────────────────────
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    append  = ''
    new_pts = []                             # loading 그래프용
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
            fp.seek(offset)
            append = sanitize(fp.read())
            offset += len(append)
        if append:                           # 새 로그에서 loading 추출
            _, new_pts = extract_loading(append)

    # ── 2) System_0 .data 추가분 ────────────────────────────
    try:
        data_bytes = int(request.GET.get('data_bytes', 0))
    except ValueError:
        data_bytes = 0

    data_append = ''
    progress = None
    ads_avg  = None
    progress_re = re.compile(r'Current cycle:\s*(\d+)\s+out of\s+(\d+)', re.I)
    # 2) 절대 adsorption 평균: "absolute adsorption: 0.125 ... (avg. 0.10110) [mol/uc]"
    ads_avg_re = re.compile(r'absolute adsorption:.*?\(avg\.\s*([0-9.eE+-]+)\)', re.I)

    if os.path.isdir(system_dir):
        # 첫 번째 파일만 사용
        data_file = os.path.join(system_dir, os.listdir(system_dir)[0])
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8', errors='ignore') as fp:
                fp.seek(data_bytes)
                data_append = sanitize(fp.read())
                data_bytes += len(data_append)

            # 최근 50줄 안에서 진행·ads 평균 값 찾기
            for line in data_append.splitlines()[-50:]:
                if (m := progress_re.search(line)):
                    progress = {'cur': int(m.group(1)),
                                'tot': int(m.group(2))}
                elif (m := ads_avg_re.search(line)):
                    ads_avg = float(m.group(1))

    return JsonResponse({
        'append': append,
        'offset': offset,
        'data_append': data_append,
        'data_bytes': data_bytes,
        'progress': progress,
        'ads_avg': ads_avg,
        'new_pts': new_pts
    })

# System_0/*.data → [{cycle, loading, energy}, …] 파서
# def parse_data_file(data_path):
#     parsed = []
#     if not os.path.exists(data_path):
#         return parsed
#     with open(data_path, 'r', encoding='utf-8', errors='ignore') as fp:
#         print(111111111111111)
#         for line in fp:
#             m = data_re.match(line)
#             if m:
#                 c, l, e = m.groups()
#                 parsed.append({
#                     'cycle': int(c),
#                     'loading': float(l),
#                     'energy': float(e),
#                 })
#     return parsed

# # ──────────────────────────────────────────────
# # 상세 페이지
# # ──────────────────────────────────────────────
# def simulation_detail(request, sim_name):
#     folder = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
#     if not os.path.isdir(folder):
#         raise Http404("Simulation not found")

#     log_path   = os.path.join(folder, 'output.log')
#     system_dir = os.path.join(folder, 'Output', 'System_0')

#     # 1) 실행 로그
#     log_text = ''
#     if os.path.exists(log_path):
#         with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
#             log_text = fp.read()

#     # 2) .data 파일 선택 (여러 개일 수 있음 → 가장 마지막으로 수정된 파일 하나를 pick)
#     data_file = ''
#     data_json = '[]'
#     if os.path.isdir(system_dir):
#         data_file = os.path.join(system_dir, os.listdir(system_dir)[0])      # 최신
#         data_parsed = parse_data_file(data_file)
#         print(data_file,111)
#         print(data_parsed,12312)
#         data_json = json.dumps(data_parsed)

#     # 3) 상태 판정
#     pid_path = os.path.join(folder, 'pid')
#     status = 'NO_OUTPUT'
#     if os.path.isdir(system_dir):
#         status = 'FINISHED'
#         if os.path.exists(pid_path):
#             try:
#                 pid = int(open(pid_path).read().strip())
#                 status = 'RUNNING' if pid_alive(pid) else 'FINISHED'
#             except:
#                 pass

#     ctx = {
#         'sim_name': sim_name,
#         'status':   status,
#         'log_text': log_text,
#         'data_json': data_json,
#     }
#     return render(request, 'app/simulation_detail.html', ctx)

# # ──────────────────────────────────────────────
# # 실시간 폴링 API
# # ──────────────────────────────────────────────
# @require_GET
# def simulation_log_api(request, sim_name):
#     """
#     GET /simulations/<sim_name>/log/?offset=<B>&last_cycle=<N>
#     - output.log append      → key 'append'
#     - System_0 .data 신규행 → key 'new_cycles'
#     """
#     folder     = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
#     log_path   = os.path.join(folder, 'output.log')
#     system_dir = os.path.join(folder, 'Output', 'System_0')
#     # 1) 로그 append
#     try:
#         offset = int(request.GET.get('offset', 0))
#     except ValueError:
#         offset = 0
#     append = ''
#     if os.path.exists(log_path):
#         with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
#             fp.seek(offset)
#             append = fp.read()
#             offset += len(append)

#     # 2) 데이터 신규 행
#     try:
#         last_cycle = int(request.GET.get('last_cycle', -1))
#     except ValueError:
#         last_cycle = -1
#     new_cycles = []
#     data_file = ''
#     print(os.listdir(system_dir))
#     if os.path.isdir(system_dir):
#         data_file = os.path.join(system_dir, os.listdir(system_dir)[0])
#         with open(data_file, 'r', encoding='utf-8', errors='ignore') as fp:
#             for line in fp:
#                 m = data_re.match(line)
#                 if m:
#                     c, l, e = m.groups()
#                     c = int(c)
#                     if c > last_cycle:
#                         new_cycles.append({'cycle': c,
#                                             'loading': float(l),
#                                             'energy':  float(e)})

#     return JsonResponse({
#         'append': append,
#         'offset': offset,
#         'new_cycles': new_cycles,
#     })
# def parse_output_log(log_path):
#     """
#     output.log 에서 Cycle N … Loading=x, Energy=y … 형식 데이터를 뽑아
#     [{'cycle': N, 'loading': x, 'energy': y}, …] 로 반환.
#     """
#     if not os.path.exists(log_path):
#         return []

#     parsed = []
#     with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
#         for line in fp:
#             m = cycle_re.search(line)
#             if m:
#                 cycle, loading, energy = m.groups()
#                 parsed.append({
#                     'cycle': int(cycle),
#                     'loading': float(loading),
#                     'energy':  float(energy),
#                 })
#     return parsed

# # ------------------------------------------------------------------
# # 2) 상세 페이지 뷰
# # ------------------------------------------------------------------
# def simulation_detail(request, sim_name):
#     """
#     /simulations/<sim_name>/  — 상세 페이지
#     """
#     folder = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
#     if not os.path.isdir(folder):
#         raise Http404("Simulation not found")

#     log_path  = os.path.join(folder, 'output.log')
#     pid_path  = os.path.join(folder, 'pid')

#     # 로그 전체(뷰어 용)
#     log_text = ''
#     if os.path.exists(log_path):
#         with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
#             log_text = fp.read()

#     # 주기별 데이터
#     cycle_data = parse_output_log(log_path)   # list[dict]

#     # 최신 상태판정 ― 기존 helpers 재사용
#     status = 'NO_OUTPUT'
#     if os.path.exists(os.path.join(folder, 'Output')):
#         status = 'FINISHED'
#         if os.path.exists(pid_path):
#             try:
#                 pid = int(open(pid_path).read().strip())
#                 status = 'RUNNING' if pid_alive(pid) else 'FINISHED'
#             except:
#                 pass

#     context = {
#         'sim_name': sim_name,
#         'status':   status,
#         'log_text': log_text,
#         'cycle_json': json.dumps(cycle_data),  # → JS 로 그대로 보냄
#     }
#     return render(request, 'app/simulation_detail.html', context)

# from django.http import JsonResponse
# from django.views.decorators.http import require_GET

# @require_GET
# def simulation_log_api(request, sim_name):
#     """
#     GET /simulations/<sim_name>/log/?offset=<int>
#     - offset 바이트부터의 추가분만 돌려준다.
#     - cycle_parsed: [{cycle,loading,energy}, …] (신규 행만)
#     """
#     folder   = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
#     log_path = os.path.join(folder, 'output.log')
#     if not os.path.exists(log_path):
#         return JsonResponse({'append': '', 'cycle_parsed': []})

#     # 요청 쿼리 offset
#     try:
#         offset = int(request.GET.get('offset', 0))
#     except ValueError:
#         offset = 0

#     # 파일 끝까지 읽기
#     with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
#         fp.seek(offset)
#         append_text = fp.read()
#         new_offset  = offset + len(append_text)

#     # 추가된 줄에서 cycle 파싱
#     new_cycles = []
#     for line in append_text.splitlines():
#         m = cycle_re.search(line)
#         if m:
#             c,l,e = m.groups()
#             new_cycles.append({'cycle':int(c),'loading':float(l),'energy':float(e)})

#     return JsonResponse({
#         'append': append_text,
#         'offset': new_offset,
#         'cycle_parsed': new_cycles,
#     })
import shutil
def delete_simulation(request, sim_name):
    """
    Deletes the simulation folder named sim_name and redirects back to the list.
    Only accepts POST.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    sim_path = os.path.join(SIMULATION_ROOT, sim_name)
    if os.path.isdir(sim_path):
        try:
            shutil.rmtree(sim_path)
        except Exception as e:
            # Optionally log the exception here
            pass

    return redirect('simulations')

import os, json
import datetime
from django.conf import settings
from django.shortcuts import render, redirect

CONFIG_PATH = os.path.join(settings.BASE_DIR, 'config.json')
import os, json
from django.conf import settings
from django.shortcuts import render, redirect

CONFIG_PATH = os.path.join(settings.BASE_DIR, 'config.json')

# 공유 디렉터리 경로 상수
RASPA_SHARE = os.path.join(settings.RASPA_DIR, 'share', 'raspa')
FORCEFIELD_DIR = os.path.join(RASPA_SHARE, 'forcefield')
MOLECULES_DIR = os.path.join(RASPA_SHARE, 'molecules')


def settings_view(request):
    # 1) JSON 불러오기
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        conf = json.load(f)

    # 필드별 is_list, selected 초기화
    for field in conf.get('field', []):
        field['is_list'] = isinstance(field.get('value'), list)
        if field['is_list']:
            field.setdefault('selected', field['value'][0])
        else:
            field.setdefault('selected', field['value'])

    # 2) Forcefield 목록, Molecule 목록 동적 생성
    forcefields = sorted(os.listdir(FORCEFIELD_DIR))
    # molecules 하위 폴더(예: 개별 기준) 모두 탐색 후 파일명 확장자 제거하여 리스트
    molecules = []
    for root, _, files in os.walk(MOLECULES_DIR):
        for fn in files:
            name, ext = os.path.splitext(fn)
            if ext.lower() in ['.foam', '.cif', '.mol'] or ext:
                molecules.append(name)
    molecules = sorted(set(molecules))

    if request.method == 'POST':
        data = request.POST
        # Paths & Panels
        conf['raspa_dir'] = data.get('raspa_dir', conf['raspa_dir'])
        conf['LEFT_PANEL_WIDTH'] = int(data.get('LEFT_PANEL_WIDTH', conf.get('LEFT_PANEL_WIDTH',0)))
        conf['RIGHT_PANEL_WIDTH'] = int(data.get('RIGHT_PANEL_WIDTH', conf.get('RIGHT_PANEL_WIDTH',0)))
        # Fields
        for idx, field in enumerate(conf['field']):
            key = f'field_{idx}'
            if key in data:
                field['selected'] = data[key]
        # Defaults
        for k in conf.get('defaults', {}):
            formkey = f'defaults_{k}'
            if formkey in data:
                conf['defaults'][k] = data[formkey]

        # JSON 저장
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(conf, f, indent=2, ensure_ascii=False)

        return redirect('settings')

    # GET 요청: 폼 렌더
    return render(request, 'app/settings.html', {
        'conf': conf,
        'forcefields': forcefields,
        'molecules': molecules,
    })


def delete_simulations(request):
    """
    POST로 받은 시뮬레이션 이름 리스트를 삭제하고,
    { deleted: [...] } 형식의 JSON 응답을 반환합니다.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        data = json.loads(request.body)
        names = data.get('names', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    deleted = []
    for name in names:
        path = os.path.join(SIMULATION_ROOT, name)
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                deleted.append(name)
            except Exception:
                pass

    return JsonResponse({'deleted': deleted})


# views.py (simulation_log_api 아래쯤 편한 곳에 삽입)
from django.views.decorators.http import require_GET
from django.http import JsonResponse

@require_GET
def simulation_refresh_api(request, sim_name):
    """
    GET  /simulations/<sim_name>/refresh/
    ▶ 상태·전체 로그·데이터·로딩 시계열을 한 번에 내려준다
    {
      status: "RUNNING" | "FINISHED" | …,
      log_text:   "<string>",
      data_text:  "<string>",
      load_series:[["phase",cycle,molkg,avg?], …]
    }
    """
    root        = os.path.join(settings.BASE_DIR, 'simulations', sim_name)
    log_path    = os.path.join(root, 'output.log')
    system_dir  = os.path.join(root, 'Output', 'System_0')

    # ── 1) 상태 판정 ──────────────────────────────────────────
    status = 'NO_OUTPUT'
    pid_path = os.path.join(root, 'pid')
    if os.path.isdir(system_dir):
        status = 'FINISHED'
        if os.path.exists(pid_path):
            try:
                pid = int(open(pid_path).read().strip())
                status = 'RUNNING' if raspa_alive(pid) else 'FINISHED'
            except:
                pass

    # ── 2) 로그 전문 / 데이터 전문 ───────────────────────────
    log_text = ''
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as fp:
            log_text = sanitize(fp.read())

    data_text = ''
    load_series = []
    if os.path.isdir(system_dir):
        data_file = os.path.join(system_dir, os.listdir(system_dir)[0])
        if data_file:
            with open(data_file, 'r', encoding='utf-8', errors='ignore') as fp:
                data_text = fp.read()
            load_series = extract_loading(data_text)

    return JsonResponse({
        'status': status,
        'log_text': log_text,
        'data_text': data_text,
        'load_series': load_series,
    })
