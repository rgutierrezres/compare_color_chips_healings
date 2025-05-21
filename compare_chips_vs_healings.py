#!/usr/bin/env python3
import csv
import os
import sys
import math
import statistics
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None


def browse_files():
    """
    Open a GUI dialog to select 2+ .lab/.txt files.
    """
    if not tk:
        print("ERROR: tkinter not available for file browsing.", file=sys.stderr)
        sys.exit(1)
    root = tk.Tk(); root.withdraw()
    paths = filedialog.askopenfilenames(
        title="Select Barbieri .lab/.txt files (select 2 or more)",
        filetypes=[("Lab files","*.lab *.txt"),("All files","*.*")]
    )
    if not paths or len(paths) < 2:
        print("ERROR: Please select at least two files.", file=sys.stderr)
        sys.exit(1)
    return list(paths)


def ask_save_path(default_name):
    """
    Prompt GUI Save As or console input for output CSV path.
    """
    if tk:
        root = tk.Tk(); root.withdraw()
        save_path = filedialog.asksaveasfilename(
            title="Select output CSV location",
            defaultextension='.csv',
            initialfile=default_name,
            filetypes=[('CSV files','*.csv'),('All files','*.*')]
        )
        if save_path:
            return save_path
        print("No save path selected; exiting.", file=sys.stderr)
        sys.exit(1)
    else:
        choice = input(f"Enter output CSV path (default: {default_name}): ").strip()
        return choice or default_name


def read_lab_file(path):
    """
    Parse a Barbieri .lab/.txt file and return list of (Sample_ID, Chip Coord, L, A, B).
    """
    if not os.path.isfile(path):
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        in_data = False
        for line in f:
            line = line.strip()
            if line == 'BEGIN_DATA': in_data = True; continue
            if line == 'END_DATA': break
            if not in_data or not line: continue
            parts = line.split()
            if len(parts) < 5: continue
            sid, name, lval, aval, bval = parts[:5]
            coord = ",".join(list(name))
            try:
                L, A, B = map(float,(lval,aval,bval))
            except ValueError:
                continue
            data.append((sid,coord,L,A,B))
    return data


def main():
    # 1) Select files
    files = browse_files()
    print("\nSelected files:")
    for idx, path in enumerate(files,1):
        print(f"  [{idx}] {os.path.basename(path)}")

    # 2) Identify Original group
    orig_input = input("Enter numbers of Original group files (comma-separated): ").strip()
    try:
        orig_idxs = [int(x)-1 for x in orig_input.replace(';',',').split(',')]
        originals = [files[i] for i in orig_idxs]
    except:
        print("Invalid Original group selection; exiting.", file=sys.stderr)
        sys.exit(1)

    # 3) Identify Healing group
    heal_input = input("Enter numbers of Healing group files (comma-separated): ").strip()
    try:
        heal_idxs = [int(x)-1 for x in heal_input.replace(';',',').split(',')]
        healings = [files[i] for i in heal_idxs]
    except:
        print("Invalid Healing group selection; exiting.", file=sys.stderr)
        sys.exit(1)

    # Validate groups
    if set(originals) & set(healings):
        print("Groups overlap! Original and Healing must be disjoint.", file=sys.stderr)
        sys.exit(1)
    if not originals or not healings:
        print("Each group must have at least one file.", file=sys.stderr)
        sys.exit(1)

    # 4) Choose output path
    default_csv = "orig_vs_heal_summary.csv"
    out_csv = ask_save_path(default_csv)

    # 5) Read all selected files
    data_map = {p: read_lab_file(p) for p in set(originals+healings)}

    # 6) Compute and write comparisons
    global_deltas = []
    with open(out_csv,'w',newline='',encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow([
            'Original File','Healing File','Sample_ID','Chip Coordinate',
            'Orig L','Orig A','Orig B','Heal L','Heal A','Heal B',
            'ΔL','ΔA','ΔB','ΔE'
        ])

        # Pairwise Original vs Healing
        for orig in originals:
            for heal in healings:
                # Collect deltas for this pair
                pair_deltas = []
                heal_dict = {(s,c):(L,A,B) for s,c,L,A,B in data_map[heal]}
                for sid,coord,L_o,A_o,B_o in data_map[orig]:
                    key=(sid,coord)
                    if key not in heal_dict: continue
                    L_h,A_h,B_h = heal_dict[key]
                    dL=L_h-L_o; dA=A_h-A_o; dB=B_h-B_o
                    dE=math.sqrt(dL**2+dA**2+dB**2)
                    pair_deltas.append((dL,dA,dB,dE))
                    global_deltas.append((dL,dA,dB,dE))
                    writer.writerow([
                        os.path.basename(orig),os.path.basename(heal),
                        sid,coord,
                        f"{L_o:.6f}",f"{A_o:.6f}",f"{B_o:.6f}",
                        f"{L_h:.6f}",f"{A_h:.6f}",f"{B_h:.6f}",
                        f"{dL:.6f}",f"{dA:.6f}",f"{dB:.6f}",f"{dE:.6f}"
                    ])
                # Summary for this pair
                writer.writerow([])
                writer.writerow([f"Summary {os.path.basename(orig)} vs {os.path.basename(heal)}"])
                if pair_deltas:
                    n=len(pair_deltas)
                    dL_vals=[d[0] for d in pair_deltas]
                    dA_vals=[d[1] for d in pair_deltas]
                    dB_vals=[d[2] for d in pair_deltas]
                    dE_vals=[d[3] for d in pair_deltas]
                    writer.writerow([
                        'Avg ΔL',f"{statistics.mean(dL_vals):.6f}",
                        'Std ΔL',f"{statistics.pstdev(dL_vals):.6f}"
                    ])
                    writer.writerow([
                        'Avg ΔA',f"{statistics.mean(dA_vals):.6f}",
                        'Std ΔA',f"{statistics.pstdev(dA_vals):.6f}"
                    ])
                    writer.writerow([
                        'Avg ΔB',f"{statistics.mean(dB_vals):.6f}",
                        'Std ΔB',f"{statistics.pstdev(dB_vals):.6f}"
                    ])
                    writer.writerow([
                        'Avg ΔE',f"{statistics.mean(dE_vals):.6f}",
                        'Std ΔE',f"{statistics.pstdev(dE_vals):.6f}"
                    ])
                    pct3=sum(1 for x in dE_vals if x>3)/n*100
                    pct6=sum(1 for x in dE_vals if x>6)/n*100
                    writer.writerow([
                        'Pct ΔE>3',f"{pct3:.2f}%",
                        'Pct ΔE>6',f"{pct6:.2f}%"
                    ])
                else:
                    writer.writerow(['No matching samples for this pair.'])
                writer.writerow([])

        # 7) Global summary of all comparisons
        writer.writerow(['Overall Summary Original vs Healing'])
        if global_deltas:
            n_all=len(global_deltas)
            dL_all=[d[0] for d in global_deltas]
            dA_all=[d[1] for d in global_deltas]
            dB_all=[d[2] for d in global_deltas]
            dE_all=[d[3] for d in global_deltas]
            writer.writerow([
                'Avg ΔL',f"{statistics.mean(dL_all):.6f}",
                'Std ΔL',f"{statistics.pstdev(dL_all):.6f}"
            ])
            writer.writerow([
                'Avg ΔA',f"{statistics.mean(dA_all):.6f}",
                'Std ΔA',f"{statistics.pstdev(dA_all):.6f}"
            ])
            writer.writerow([
                'Avg ΔB',f"{statistics.mean(dB_all):.6f}",
                'Std ΔB',f"{statistics.pstdev(dB_all):.6f}"
            ])
            writer.writerow([
                'Avg ΔE',f"{statistics.mean(dE_all):.6f}",
                'Std ΔE',f"{statistics.pstdev(dE_all):.6f}"
            ])
            pct3_all=sum(1 for x in dE_all if x>3)/n_all*100
            pct6_all=sum(1 for x in dE_all if x>6)/n_all*100
            writer.writerow([
                'Pct ΔE>3',f"{pct3_all:.2f}%",
                'Pct ΔE>6',f"{pct6_all:.2f}%"
            ])
        else:
            writer.writerow(['No comparisons made.'])

    print(f"✅ Wrote CSV with per-pair summaries: {out_csv}")

if __name__=='__main__':
    main()
