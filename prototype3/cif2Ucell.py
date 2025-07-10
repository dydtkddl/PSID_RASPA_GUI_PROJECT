#!/usr/bin/env python3
import os
import sys
import subprocess
import numpy as np
from math import pi, sqrt, cos, sin

# Windows에서 CREATE_NO_WINDOW 사용 가능하도록
try:
    from subprocess import CREATE_NO_WINDOW
except ImportError:
    CREATE_NO_WINDOW = 0

def cif2Ucell(cif, cutoff, Display=False):
    # 확장자 자동 추가
    if not cif.endswith(".cif"):
        cif += ".cif"
    if not os.path.exists(cif):
        raise FileNotFoundError(f"{cif} not found")
    # CIF 내용 읽기
    cmd = ["cat", cif]
    f_data = subprocess.check_output(cmd, creationflags=CREATE_NO_WINDOW).decode("utf-8")
    f_cont = f_data.splitlines()

    # 셀 파라미터 파싱
    deg2rad = pi / 180.
    n_a   = len('_cell_length_a')
    n_b   = len('_cell_length_b')
    n_c   = len('_cell_length_c')
    n_alp = len('_cell_angle_alpha')
    n_bet = len('_cell_angle_beta')
    n_gam = len('_cell_angle_gamma')

    count_compl = 0
    for line in f_cont:
        if line.startswith('_cell_length_a'):
            a = float(line.split()[1]); count_compl += 1
        elif line.startswith('_cell_length_b'):
            b = float(line.split()[1]); count_compl += 1
        elif line.startswith('_cell_length_c'):
            c = float(line.split()[1]); count_compl += 1
        elif line.startswith('_cell_angle_alpha'):
            alpha = float(line.split()[1]) * deg2rad; count_compl += 1
        elif line.startswith('_cell_angle_beta'):
            beta  = float(line.split()[1]) * deg2rad; count_compl += 1
        elif line.startswith('_cell_angle_gamma'):
            gamma = float(line.split()[1]) * deg2rad; count_compl += 1
        if count_compl >= 6:
            break

    if Display:
        print(f"a = {a}")
        print(f"b = {b}")
        print(f"c = {c}")
        print(f"alpha = {alpha/deg2rad}°")
        print(f"beta  = {beta/deg2rad}°")
        print(f"gamma = {gamma/deg2rad}°")

    # 셀 벡터 계산 (위키 백과 Fractional coordinates 참조)
    v = sqrt(1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2
             + 2*cos(alpha)*cos(beta)*cos(gamma))
    cell = np.zeros((3,3))
    cell[0] = [a, 0, 0]
    cell[1] = [b * cos(gamma), b * sin(gamma), 0]
    cell[2] = [c * cos(beta),
               c * (cos(alpha) - cos(beta)*cos(gamma)) / sin(gamma),
               c * v / sin(gamma)]

    # 각 축별 반복 수 계산
    diag = np.diag(cell)
    nx, ny, nz = (int(np.ceil(cutoff/diag_i * 2)) for diag_i in diag)
    return nx, ny, nz

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Compute number of repetitions (nx, ny, nz) for a CIF unit cell")
    parser.add_argument("cif",      help="CIF file path (with or without .cif extension)")
    parser.add_argument("cutoff",   type=float, help="Cutoff distance (Å)")
    parser.add_argument("--display", action="store_true",
                        help="Print parsed cell parameters as well")
    args = parser.parse_args()

    try:
        nx, ny, nz = cif2Ucell(args.cif, args.cutoff, Display=args.display)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 결과 출력
    print(nx, ny, nz)

if __name__ == "__main__":
    main()

