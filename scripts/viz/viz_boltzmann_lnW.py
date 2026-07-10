"""
viz_boltzmann_lnW.py
====================
Entropía de Boltzmann termodinámica  S_B = ln W  para los dos modelos.

W = N! / (n_1! · n_2! · ... · n_k!)  — número de microestados compatibles
con el histograma de energías de bono observado.

Relación de Stirling (N grande):  S_B = ln W ≈ N · H_hist
donde  H_hist = -Σ p_k ln p_k  con  p_k = n_k / N  (histograma de frecuencias).

NOTA: bond_shannon_entropy (ya existente) usa p_i = |E_i|/Σ|E_j|, que es
una entropía ponderada por magnitud de energía, NO el histograma de frecuencias.
Ambas son métricas válidas pero miden cosas distintas.

Genera:
  results/entropy_boltzmann_lnW.png
"""
import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_entropy import board_from_stones
from compare_per_bond import (
    H_nuestro, H_alvarado, SPIN_VALS,
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_histogram_entropy,
    bond_boltzmann_lnW, bond_T_eff,
)
from analysis_patterns import PATTERNS, BOARD_SIZE

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

BG   = '#FAFAF8'
C_M1 = '#1D4ED8'
C_AL = '#D97706'


# ─────────────────────────────────────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────────────────────────────────────

# Tabla de interacción (9 pares base)
PAIRS    = [(s0, s1) for s0 in SPIN_VALS for s1 in SPIN_VALS]
VALS_M1  = np.array([H_nuestro(s0, s1)  for s0, s1 in PAIRS])
VALS_AL  = np.array([H_alvarado(s0, s1) for s0, s1 in PAIRS])

S_tab_lnW_M1  = bond_boltzmann_lnW(VALS_M1)
S_tab_lnW_AL  = bond_boltzmann_lnW(VALS_AL)
S_tab_hist_M1 = bond_histogram_entropy(VALS_M1)
S_tab_hist_AL = bond_histogram_entropy(VALS_AL)
S_tab_wsh_M1  = bond_shannon_entropy(VALS_M1)   # ponderada |E|
S_tab_wsh_AL  = bond_shannon_entropy(VALS_AL)

# 19 patrones
records = []
for pid, desc, stones in PATTERNS:
    board  = board_from_stones(BOARD_SIZE, stones)
    bM1    = all_bond_energies_nuestro(board)
    bAL    = all_bond_energies_alvarado(board)
    N      = len(bM1)   # mismo N para ambos (mismo tablero)
    lnW_M1 = bond_boltzmann_lnW(bM1)
    lnW_AL = bond_boltzmann_lnW(bAL)
    h_M1   = bond_histogram_entropy(bM1)
    h_AL   = bond_histogram_entropy(bAL)
    w_M1   = bond_shannon_entropy(bM1)
    w_AL   = bond_shannon_entropy(bAL)
    records.append({
        'id':   pid,  'desc': desc,  'n': len(stones),
        'N':    N,
        'lnW_M1': lnW_M1,   'lnW_AL': lnW_AL,
        'h_M1':   h_M1,     'h_AL':   h_AL,     # histograma
        'w_M1':   w_M1,     'w_AL':   w_AL,     # ponderada |E|
        'lnW_pb_M1': lnW_M1 / N if N > 0 else 0,
        'lnW_pb_AL': lnW_AL / N if N > 0 else 0,
    })

IDS      = [r['id']        for r in records]
lnW_M1   = np.array([r['lnW_M1']    for r in records])
lnW_AL   = np.array([r['lnW_AL']    for r in records])
h_M1     = np.array([r['h_M1']      for r in records])
h_AL     = np.array([r['h_AL']      for r in records])
w_M1     = np.array([r['w_M1']      for r in records])
w_AL     = np.array([r['w_AL']      for r in records])
pb_M1    = np.array([r['lnW_pb_M1'] for r in records])
pb_AL    = np.array([r['lnW_pb_AL'] for r in records])
N_bonds  = np.array([r['N']         for r in records])
N_stones = np.array([r['n']         for r in records])
DIFF_lnW = lnW_M1 - lnW_AL


def spine_clean(ax):
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)


# ─────────────────────────────────────────────────────────────────────────────
# FIGURA  (3 filas × 3 cols)
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 20), facecolor=BG)
fig.suptitle(
    'Entropía de Boltzmann  $S_B = \\ln W$  —  Nuestro Modelo M1  vs  Atomic-Go\n'
    r'$W = N\,!\;/\;\prod_k n_k\,!$'
    r'   $\;\;n_k$ = bonos con energía $E_k$'
    r'   $\;\;S_B \approx N \cdot H_{hist}$  (Stirling)',
    fontsize=13, fontweight='bold', y=0.998,
)

gs = gridspec.GridSpec(
    3, 3,
    height_ratios=[1.10, 0.95, 0.95],
    hspace=0.52, wspace=0.30,
    left=0.06, right=0.97,
    top=0.966, bottom=0.05,
)
x = np.arange(len(records))
w = 0.38


# ═══════════════════════════════════════════════════════════════════════════
# FILA 0 — S_B = ln W por los 19 patrones + diferencia
# ═══════════════════════════════════════════════════════════════════════════

ax_main = fig.add_subplot(gs[0, :2])
ax_main.set_facecolor('#F4F4F2')
b1 = ax_main.bar(x - w/2, lnW_M1, w, color=C_M1, alpha=0.85,
                 label='Nuestro M1', ec='white', lw=0.5, zorder=3)
b2 = ax_main.bar(x + w/2, lnW_AL, w, color=C_AL, alpha=0.85,
                 label='Atomic-Go (Alvarado)', ec='white', lw=0.5,
                 zorder=3, hatch='///')
ax_main.set_xticks(x)
ax_main.set_xticklabels(IDS, fontsize=10)
ax_main.set_ylabel('$S_B = \\ln W$  (nats)', fontsize=11)
ax_main.set_title(
    'Entropía de Boltzmann  $S_B = \\ln W$  por patrón de apertura\n'
    'Extensiva: escala con $N$ · Alvarado = 0 cuando no hay interacciones activas',
    fontsize=11, fontweight='bold', pad=5)
ax_main.legend(fontsize=10, loc='upper left', framealpha=0.92)
ax_main.grid(axis='y', alpha=0.25)
spine_clean(ax_main)
for bar, v in zip(b1, lnW_M1):
    ax_main.text(bar.get_x() + bar.get_width()/2, v + 0.3,
                 f'{v:.1f}', ha='center', fontsize=6.5,
                 color=C_M1, fontweight='bold')
for bar, v in zip(b2, lnW_AL):
    if v > 0.5:
        ax_main.text(bar.get_x() + bar.get_width()/2, v + 0.3,
                     f'{v:.1f}', ha='center', fontsize=6.5,
                     color=C_AL, fontweight='bold')

# Diferencia
ax_diff = fig.add_subplot(gs[0, 2])
ax_diff.set_facecolor('#F4F4F2')
cols_d = [C_M1 if d > 0 else C_AL for d in DIFF_lnW]
ax_diff.barh(x, DIFF_lnW, color=cols_d, alpha=0.85, ec='white', lw=0.5, zorder=3)
ax_diff.axvline(0, color='#333', lw=1.4)
ax_diff.set_yticks(x)
ax_diff.set_yticklabels(IDS, fontsize=9)
ax_diff.set_xlabel('$S_B^{M1} - S_B^{AL}$  (nats)', fontsize=9)
ax_diff.set_title(f'Diferencia  $\\Delta S_B$\nM1 > AL en {int((DIFF_lnW>0).sum())}/19',
                  fontsize=10, fontweight='bold', pad=5)
ax_diff.invert_yaxis()
ax_diff.grid(axis='x', alpha=0.25)
for xi_p, d in enumerate(DIFF_lnW):
    ax_diff.text(d + (0.3 if d >= 0 else -0.3), xi_p, f'{d:+.1f}',
                 ha='left' if d >= 0 else 'right', va='center',
                 fontsize=7, fontweight='bold',
                 color=C_M1 if d > 0 else C_AL)
spine_clean(ax_diff)


# ═══════════════════════════════════════════════════════════════════════════
# FILA 1 — Verificación Stirling + comparación con S_Shannon ponderada
# ═══════════════════════════════════════════════════════════════════════════

# Panel izquierdo: S_B/N (barras) vs H_hist (puntos) — verifica Stirling
ax_stir = fig.add_subplot(gs[1, :2])
ax_stir.set_facecolor('#F4F4F2')

bp1 = ax_stir.bar(x - w/2, pb_M1, w, color=C_M1, alpha=0.60,
                  label='$S_B/N$ — M1', ec='white', lw=0.5, zorder=3)
bp2 = ax_stir.bar(x + w/2, pb_AL, w, color=C_AL, alpha=0.60,
                  label='$S_B/N$ — Alvarado', ec='white', lw=0.5,
                  zorder=3, hatch='///')
ax_stir.plot(x - w/2, h_M1, 'o', color=C_M1, ms=5.5, zorder=5,
             label='$H_{hist}$ — M1', markeredgecolor='white', markeredgewidth=0.6)
ax_stir.plot(x + w/2, h_AL, 'D', color=C_AL, ms=5.5, zorder=5,
             label='$H_{hist}$ — Alvarado', markeredgecolor='white', markeredgewidth=0.6)
ax_stir.set_xticks(x)
ax_stir.set_xticklabels(IDS, fontsize=10)
ax_stir.set_ylabel('nats / bono', fontsize=11)
ax_stir.set_title(
    'Stirling:  $S_B/N$ (barras) $\\approx$ $H_{hist}=-\\Sigma p_k\\ln p_k$ (puntos)   con   $p_k = n_k/N$\n'
    'La superposición confirma la igualdad. '
    'Distinto de $S_{Shannon}^{(w)}$ (ponderada por $|E|$).',
    fontsize=10.5, fontweight='bold', pad=5)
ax_stir.legend(fontsize=8.5, loc='upper left', framealpha=0.92, ncol=2)
ax_stir.grid(axis='y', alpha=0.25)
spine_clean(ax_stir)
ax_stir.text(0.99, 0.97,
    f'Tabla base (9 pares):\n'
    f'  M1:  $S_B$={S_tab_lnW_M1:.3f}  $H_{{hist}}$={S_tab_hist_M1:.3f}  $S_B/9$={S_tab_lnW_M1/9:.3f}\n'
    f'  AL:  $S_B$={S_tab_lnW_AL:.3f}  $H_{{hist}}$={S_tab_hist_AL:.3f}  $S_B/9$={S_tab_lnW_AL/9:.3f}',
    transform=ax_stir.transAxes, ha='right', va='top',
    fontsize=8.5, color='#333',
    bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='#999', lw=1.2))

# Scatter Stirling: S_B/N vs H_hist
ax_sc_stir = fig.add_subplot(gs[1, 2])
ax_sc_stir.set_facecolor('#F4F4F2')
all_pb  = np.concatenate([pb_M1, pb_AL])
all_h   = np.concatenate([h_M1,  h_AL])
lim_s   = [0, max(all_pb.max(), all_h.max()) * 1.06]
ax_sc_stir.plot(lim_s, lim_s, '--', color='#888', lw=1.5, label='$y=x$ (Stirling exacto)')
ax_sc_stir.scatter(h_M1, pb_M1, color=C_M1, s=70, ec='white', lw=0.8,
                   zorder=4, label='M1')
ax_sc_stir.scatter(h_AL, pb_AL, color=C_AL, s=70, ec='white', lw=0.8,
                   zorder=4, marker='D', label='Alvarado')
for r in records:
    ax_sc_stir.text(r['h_M1'] + 0.001, r['lnW_pb_M1'] + 0.001,
                    r['id'], fontsize=6.5, color=C_M1)
r_stir_M1 = np.corrcoef(h_M1, pb_M1)[0, 1] if h_M1.std() > 0 else 1.0
r_stir_AL = np.corrcoef(h_AL, pb_AL)[0, 1] if h_AL.std() > 0 else 1.0
ax_sc_stir.set_xlabel('$H_{hist}$  (nats)', fontsize=10)
ax_sc_stir.set_ylabel('$S_B / N$  (nats/bono)', fontsize=10)
ax_sc_stir.set_title('Verificación Stirling\n$\\ln W / N$ vs $H_{hist}$',
                     fontsize=10, fontweight='bold', pad=5)
ax_sc_stir.text(0.97, 0.08,
                f'r_M1 = {r_stir_M1:.3f}\nr_AL  = {r_stir_AL:.3f}',
                transform=ax_sc_stir.transAxes, ha='right', va='bottom',
                fontsize=9.5, fontweight='bold', color='#333',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#CCC'))
ax_sc_stir.legend(fontsize=8.5, loc='upper left', framealpha=0.92)
ax_sc_stir.set_xlim(lim_s); ax_sc_stir.set_ylim(lim_s)
spine_clean(ax_sc_stir)


# ═══════════════════════════════════════════════════════════════════════════
# FILA 2 — Scatter S_B M1 vs AL + extensividad + tabla resumen
# ═══════════════════════════════════════════════════════════════════════════

# Scatter S_B: M1 vs Alvarado
ax_sc = fig.add_subplot(gs[2, 0])
ax_sc.set_facecolor('#F4F4F2')
lim_sc = [0, max(lnW_M1.max(), lnW_AL.max()) * 1.06]
ax_sc.plot(lim_sc, lim_sc, '--', color='#888', lw=1.2, label='igualdad')
sc = ax_sc.scatter(lnW_AL, lnW_M1, c=N_stones, cmap='viridis',
                   s=80, ec='white', lw=0.8, zorder=4)
plt.colorbar(sc, ax=ax_sc, shrink=0.75, pad=0.01, label='Nº piedras')
for r in records:
    ax_sc.text(r['lnW_AL'] + 0.3, r['lnW_M1'] + 0.3, r['id'],
               fontsize=7.5, color='#333')
r_sc = np.corrcoef(lnW_M1, lnW_AL)[0, 1]
xs = np.linspace(lim_sc[0], lim_sc[1], 100)
m_sc, b_sc = np.polyfit(lnW_AL, lnW_M1, 1)
ax_sc.plot(xs, m_sc * xs + b_sc, '-', color='#7C3AED', lw=1.2, alpha=0.7,
           label=f'r = {r_sc:.2f}')
ax_sc.set_xlabel('$S_B$  Alvarado  (nats)', fontsize=10)
ax_sc.set_ylabel('$S_B$  M1  (nats)', fontsize=10)
ax_sc.set_title('$S_B$ M1 vs Alvarado\n(M1 siempre $\\geq$ Alvarado)',
                fontsize=10, fontweight='bold', pad=5)
ax_sc.legend(fontsize=8.5, loc='upper left', framealpha=0.92)
ax_sc.set_xlim(lim_sc); ax_sc.set_ylim(lim_sc)
spine_clean(ax_sc)

# Extensividad: S_B vs N_bonds con líneas de referencia H_hist
ax_ext = fig.add_subplot(gs[2, 1])
ax_ext.set_facecolor('#F4F4F2')
ax_ext.scatter(N_bonds, lnW_M1, color=C_M1, s=80, ec='white', lw=0.8,
               zorder=4, label='M1')
ax_ext.scatter(N_bonds, lnW_AL, color=C_AL, s=80, ec='white', lw=0.8,
               zorder=4, marker='D', label='Alvarado')
for r in records:
    ax_ext.text(r['N'] + 0.5, r['lnW_M1'] + 0.3, r['id'],
                fontsize=6.5, color=C_M1)
N_range = np.linspace(N_bonds.min() * 0.95, N_bonds.max() * 1.02, 100)
mean_h_M1 = h_M1.mean()
mean_h_AL = h_AL[h_AL > 0].mean() if (h_AL > 0).any() else 0
ax_ext.plot(N_range, N_range * mean_h_M1, '--', color=C_M1, lw=1.2, alpha=0.7,
            label=f'N·$\\langle H_{{hist}}\\rangle_{{M1}}$={mean_h_M1:.2f}')
if mean_h_AL > 0:
    ax_ext.plot(N_range, N_range * mean_h_AL, '--', color=C_AL, lw=1.2, alpha=0.7,
                label=f'N·$\\langle H_{{hist}}\\rangle_{{AL}}$={mean_h_AL:.2f}')
ax_ext.set_xlabel('$N_{bonos}$ (total de bonos del tablero)', fontsize=10)
ax_ext.set_ylabel('$S_B = \\ln W$  (nats)', fontsize=10)
ax_ext.set_title('Extensividad:  $S_B$ crece con $N$\n'
                 'líneas = $N \\cdot \\langle H_{hist}\\rangle$  (predicción Stirling)',
                 fontsize=10, fontweight='bold', pad=5)
ax_ext.legend(fontsize=7.5, loc='upper left', framealpha=0.92)
ax_ext.grid(alpha=0.2)
spine_clean(ax_ext)

# Tabla resumen
ax_tab = fig.add_subplot(gs[2, 2])
ax_tab.axis('off')
ax_tab.set_title('Resumen — Tabla base (9 pares)', fontsize=10,
                 fontweight='bold', pad=5)
tab_rows = [
    ('Métrica',                  'M1',                        'Alvarado'),
    ('Valores posibles',         '{−2,−1,0,+1,+2}',          '{−1,0,+1}'),
    ('$S_B = \\ln W$',           f'{S_tab_lnW_M1:.4f}',      f'{S_tab_lnW_AL:.4f}'),
    ('$H_{hist}$ (frecuencias)', f'{S_tab_hist_M1:.4f}',     f'{S_tab_hist_AL:.4f}'),
    ('$S_B / N$',                f'{S_tab_lnW_M1/9:.4f}',    f'{S_tab_lnW_AL/9:.4f}'),
    ('$S_{sh}^{(w)}$ (|E|)',     f'{S_tab_wsh_M1:.4f}',      f'{S_tab_wsh_AL:.4f}'),
    ('$W = e^{S_B}$',            f'{np.exp(S_tab_lnW_M1):.0f}',
                                  f'{np.exp(S_tab_lnW_AL):.0f}'),
]
dy = 0.126; y0 = 0.94
for k, row in enumerate(tab_rows):
    y = y0 - k * dy
    is_hdr = (k == 0)
    for xi_c, (txt, col) in enumerate(zip(row, [0.01, 0.48, 0.76])):
        fw = 'bold' if (is_hdr or xi_c == 0) else 'normal'
        fs = 9 if (is_hdr or xi_c == 0) else 8.5
        fc = '#111' if xi_c == 0 else (C_M1 if xi_c == 1 else C_AL)
        ax_tab.text(col, y, txt, transform=ax_tab.transAxes,
                    ha='left', va='top', fontsize=fs, fontweight=fw, color=fc)
    if k == 0:
        ax_tab.plot([0, 1], [y - 0.01, y - 0.01], color='#888', lw=0.8,
                    transform=ax_tab.transAxes, clip_on=False)

ax_tab.text(0.5, 0.01,
    '$S_B = k_B \\ln W$  (Boltzmann 1877)\n'
    '$H_{hist}$: frecuencias   $S_{sh}^{(w)}$: ponderada $|E|$\n'
    'Stirling:  $S_B \\approx N \\cdot H_{hist}$',
    transform=ax_tab.transAxes, ha='center', va='bottom',
    fontsize=8.5, color='#444', style='italic',
    bbox=dict(boxstyle='round,pad=0.3', fc='#EFF6FF', ec='#1D4ED8', lw=1))

# ─────────────────────────────────────────────────────────────────────────────
out = os.path.join(RESULTS, 'entropy_boltzmann_lnW.png')
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
print(f'Guardado: {out}')
plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
print('\n== Tabla base (9 pares) ==')
print(f'            S_B=lnW    H_hist   S_B/N    W=e^S_B')
print(f'  M1    :  {S_tab_lnW_M1:8.4f}  {S_tab_hist_M1:7.4f}  '
      f'{S_tab_lnW_M1/9:7.4f}   {np.exp(S_tab_lnW_M1):.0f}')
print(f'  Alvar :  {S_tab_lnW_AL:8.4f}  {S_tab_hist_AL:7.4f}  '
      f'{S_tab_lnW_AL/9:7.4f}   {np.exp(S_tab_lnW_AL):.0f}')

print(f'\n== 19 patrones ==')
print(f'{"ID":<5} {"lnW_M1":>8} {"lnW_AL":>8} {"H_hist_M1":>10} {"H_hist_AL":>10} '
      f'{"lnW/N_M1":>9} {"lnW/N_AL":>9}')
print('-' * 64)
for r in records:
    print(f'{r["id"]:<5} {r["lnW_M1"]:>8.2f} {r["lnW_AL"]:>8.2f} '
          f'{r["h_M1"]:>10.4f} {r["h_AL"]:>10.4f} '
          f'{r["lnW_pb_M1"]:>9.4f} {r["lnW_pb_AL"]:>9.4f}')

r_cross    = np.corrcoef(lnW_M1, lnW_AL)[0, 1]
print(f'\nCorrelación S_B: M1 vs Alvarado:   r = {r_cross:.3f}')
print(f'M1 > Alvarado en: {(lnW_M1 > lnW_AL).sum()}/19 patrones')
