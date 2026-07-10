"""
viz_entropy_comparison.py
==========================
Comparacion de entropias entre los dos modelos con TRES metricas:

  S_Shannon   — entropia de Shannon sobre |energia de bono|  (sube con el juego)
  S_Boltzmann — entropia termodinamica con distribucion de Gibbs a T_eff
  T_eff       — temperatura efectiva del campo de bonos = sigma^2(E)/|mean(E)|

Estructura del PNG (4 filas):
  Fila 1  Entropia de la tabla de interaccion (9 pares base)
  Fila 2  Shannon S por 19 patrones
  Fila 3  Boltzmann S_B + T_eff por 19 patrones
  Fila 4  Dispersiones comparativas

Salida: results/entropy_comparison.png
"""
import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_entropy    import board_from_stones
from compare_per_bond  import (
    H_nuestro, H_alvarado, SPIN_VALS, SPIN_MINI,
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy, bond_T_eff,
)
from analysis_patterns import PATTERNS, BOARD_SIZE

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

BG   = '#FAFAF8'
C_M1 = '#1D4ED8'
C_AL = '#D97706'
ECOL = {-2:'#1848c4', -1:'#5ba4f5', 0:'#D5D5D5', +1:'#f58b5b', +2:'#c41818'}

# ─────────────────────────────────────────────────────────────────────────────
# DATOS: tabla de interaccion (9 pares)
# ─────────────────────────────────────────────────────────────────────────────
PAIRS   = [(s0, s1) for s0 in SPIN_VALS for s1 in SPIN_VALS]
VALS_M1 = np.array([H_nuestro(s0, s1) for s0, s1 in PAIRS])
VALS_AL = np.array([H_alvarado(s0, s1) for s0, s1 in PAIRS])

def table_entropy_shannon(vals):
    unique, counts = np.unique(vals, return_counts=True)
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p))), unique, counts

def table_entropy_boltzmann(vals, T=None):
    return bond_boltzmann_entropy(vals, T=T)

S_tab_sh_M1, uniq_M1, cnt_M1 = table_entropy_shannon(VALS_M1)
S_tab_sh_AL, uniq_AL, cnt_AL = table_entropy_shannon(VALS_AL)
S_tab_bo_M1 = table_entropy_boltzmann(VALS_M1)
S_tab_bo_AL = table_entropy_boltzmann(VALS_AL)
T_tab_M1    = bond_T_eff(VALS_M1)
T_tab_AL    = bond_T_eff(VALS_AL)

# ─────────────────────────────────────────────────────────────────────────────
# DATOS: 19 patrones
# ─────────────────────────────────────────────────────────────────────────────
records = []
for pid, desc, stones in PATTERNS:
    board = board_from_stones(BOARD_SIZE, stones)
    bM1   = all_bond_energies_nuestro(board)
    bAL   = all_bond_energies_alvarado(board)
    T_M1  = bond_T_eff(bM1)
    T_AL  = bond_T_eff(bAL)
    records.append({
        'id': pid, 'desc': desc, 'n': len(stones),
        'S_sh_M1': bond_shannon_entropy(bM1),
        'S_sh_AL': bond_shannon_entropy(bAL),
        'S_bo_M1': bond_boltzmann_entropy(bM1),
        'S_bo_AL': bond_boltzmann_entropy(bAL),
        'T_M1': T_M1 if np.isfinite(T_M1) else 99.0,
        'T_AL': T_AL if np.isfinite(T_AL) else 99.0,
    })

IDS      = [r['id']      for r in records]
S_sh_M1  = np.array([r['S_sh_M1'] for r in records])
S_sh_AL  = np.array([r['S_sh_AL'] for r in records])
S_bo_M1  = np.array([r['S_bo_M1'] for r in records])
S_bo_AL  = np.array([r['S_bo_AL'] for r in records])
T_M1_arr = np.array([r['T_M1']    for r in records])
T_AL_arr = np.array([r['T_AL']    for r in records])
N_stones = np.array([r['n']       for r in records])

DIFF_sh = S_sh_M1 - S_sh_AL
DIFF_bo = S_bo_M1 - S_bo_AL

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 24), facecolor=BG)
fig.suptitle(
    'Análisis de Entropía: Nuestro Modelo M1  vs  Atomic-Go (Alvarado 2019)\n'
    'Shannon  ·  Boltzmann  ·  Temperatura efectiva',
    fontsize=15, fontweight='bold', y=0.992,
)

gs = gridspec.GridSpec(
    4, 3,
    height_ratios=[0.80, 1.10, 1.10, 0.90],
    hspace=0.52, wspace=0.30,
    left=0.05, right=0.97,
    top=0.970, bottom=0.04,
)


# ═══════════════════════════════════════════════════════════════════════════
# FILA 0 — Entropía de la tabla de interacción (9 pares base)
# ═══════════════════════════════════════════════════════════════════════════

def draw_value_hist(ax, vals, unique, counts, color, title, formula,
                    S_sh, S_bo, T_eff_val):
    ax.set_facecolor('#F4F4F2')
    freqs = counts / counts.sum()
    bar_colors = [ECOL.get(int(round(u)), '#CCC') for u in unique]
    xlabels = [f'{int(u):+d}' if u != 0 else '0' for u in unique]
    bars = ax.bar(xlabels, freqs, color=bar_colors, ec='white', lw=0.8,
                  width=0.6, zorder=3)
    for bar, f, c in zip(bars, freqs, counts):
        ax.text(bar.get_x() + bar.get_width()/2, f + 0.007,
                f'{f:.2f}\n({c}/9)', ha='center', va='bottom',
                fontsize=8, fontweight='bold', color='#222')
    ax.set_ylim(0, max(freqs) * 1.55)
    ax.set_ylabel('Frecuencia  p', fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold', pad=5, color='#111')
    ax.text(0.5, 0.98, formula, transform=ax.transAxes,
            ha='center', va='top', fontsize=8, color='#666', style='italic')
    ax.grid(axis='y', alpha=0.3, lw=0.7)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    T_str = f'{T_eff_val:.3f}' if T_eff_val < 50 else '∞'
    txt = (f'S_Shannon  = {S_sh:.3f} nats\n'
           f'S_Boltzmann = {S_bo:.3f} nats\n'
           f'T_eff        = {T_str}')
    ax.text(0.97, 0.97, txt, transform=ax.transAxes, ha='right', va='top',
            fontsize=9.5, fontweight='bold', color=color,
            bbox=dict(boxstyle='round,pad=0.4', fc='white', ec=color, lw=1.8))

draw_value_hist(ax=fig.add_subplot(gs[0, 0]),
                vals=VALS_M1, unique=uniq_M1, counts=cnt_M1,
                color=C_M1, title='Nuestro Modelo M1',
                formula='H = sᵢ + 2sⱼ − sᵢsⱼ² − sᵢ²sⱼ',
                S_sh=S_tab_sh_M1, S_bo=S_tab_bo_M1, T_eff_val=T_tab_M1)

draw_value_hist(ax=fig.add_subplot(gs[0, 1]),
                vals=VALS_AL, unique=uniq_AL, counts=cnt_AL,
                color=C_AL, title='Atomic-Go  (Alvarado)',
                formula='H = xᵢ · xⱼ',
                S_sh=S_tab_sh_AL, S_bo=S_tab_bo_AL, T_eff_val=T_tab_AL)

# Panel comparativo de la tabla
ax_meta = fig.add_subplot(gs[0, 2])
ax_meta.set_facecolor('#F4F4F2')
ax_meta.axis('off')
ax_meta.set_title('Comparación — 9 pares base', fontsize=11, fontweight='bold', pad=5)
rows = [
    ('',                'M1',                     'Alvarado'),
    ('Valores posibles', '{−2,−1,0,+1,+2}',       '{−1,0,+1}'),
    ('S_Shannon  (nats)', f'{S_tab_sh_M1:.3f}',   f'{S_tab_sh_AL:.3f}'),
    ('S_Boltzmann (nats)', f'{S_tab_bo_M1:.3f}',  f'{S_tab_bo_AL:.3f}'),
    ('T_eff',            f'{T_tab_M1:.3f}' if T_tab_M1<50 else '∞',
                         f'{T_tab_AL:.3f}' if T_tab_AL<50 else '∞'),
    ('Vacío activo',     'Sí',                     'No'),
    ('Simetría',         'Asimétrico',             'Simétrico'),
]
dy = 0.138; y0 = 0.95
for k, row in enumerate(rows):
    y = y0 - k * dy
    is_hdr = (k == 0)
    for xi, (txt, col) in enumerate(zip(row, [0.02, 0.46, 0.77])):
        fw = 'bold' if (is_hdr or xi == 0) else 'normal'
        fs = 9.5 if (is_hdr or xi == 0) else 9
        fc = '#111' if xi == 0 else (C_M1 if xi == 1 else C_AL)
        ax_meta.text(col, y, txt, transform=ax_meta.transAxes,
                     ha='left', va='top', fontsize=fs, fontweight=fw, color=fc)
    if k == 0:
        ax_meta.plot([0, 1], [y - 0.008, y - 0.008], color='#888', lw=0.8,
                     transform=ax_meta.transAxes, clip_on=False)

ax_meta.text(0.5, 0.01,
    'S_Boltzmann < S_Shannon → la distribución de Gibbs\n'
    'concentra más peso en bonos de baja energía',
    transform=ax_meta.transAxes, ha='center', va='bottom',
    fontsize=8.5, color='#555', style='italic',
    bbox=dict(boxstyle='round,pad=0.3', fc='#FEF9E7', ec='#D4AC0D', lw=1))


# ═══════════════════════════════════════════════════════════════════════════
# FILA 1 — Shannon S por 19 patrones
# ═══════════════════════════════════════════════════════════════════════════

ax_sh  = fig.add_subplot(gs[1, :2])
ax_shd = fig.add_subplot(gs[1, 2])

x = np.arange(len(records)); w = 0.38
ax_sh.set_facecolor('#F4F4F2')
b1 = ax_sh.bar(x - w/2, S_sh_M1, w, color=C_M1, alpha=0.85, label='Nuestro M1',
               ec='white', lw=0.5, zorder=3)
b2 = ax_sh.bar(x + w/2, S_sh_AL, w, color=C_AL, alpha=0.85, label='Atomic-Go',
               ec='white', lw=0.5, zorder=3)
ax_sh.set_xticks(x); ax_sh.set_xticklabels(IDS, fontsize=10)
ax_sh.set_ylabel('S_Shannon  (nats)', fontsize=10)
ax_sh.set_title(
    'Entropía de Shannon  S = −Σ pᵢ ln pᵢ  con  pᵢ = |Eᵢ|/Σ|Eⱼ|\n'
    '19 patrones de apertura  |  mide dispersión de la magnitud de energía',
    fontsize=10, fontweight='bold', pad=5)
ax_sh.legend(fontsize=10, loc='upper left', framealpha=0.92)
ax_sh.grid(axis='y', alpha=0.25)
for sp in ['top','right']: ax_sh.spines[sp].set_visible(False)

for bar, v in zip(b1, S_sh_M1):
    if v > 0.05:
        ax_sh.text(bar.get_x()+bar.get_width()/2, v+0.01, f'{v:.2f}',
                   ha='center', fontsize=6.5, color=C_M1, fontweight='bold')
for bar, v in zip(b2, S_sh_AL):
    if v > 0.05:
        ax_sh.text(bar.get_x()+bar.get_width()/2, v+0.01, f'{v:.2f}',
                   ha='center', fontsize=6.5, color=C_AL, fontweight='bold')

# Diferencia Shannon
ax_shd.set_facecolor('#F4F4F2')
cols_d = [C_M1 if d > 0 else C_AL for d in DIFF_sh]
ax_shd.barh(x, DIFF_sh, color=cols_d, alpha=0.85, ec='white', lw=0.5, zorder=3)
ax_shd.axvline(0, color='#333', lw=1.4)
ax_shd.set_yticks(x); ax_shd.set_yticklabels(IDS, fontsize=9)
ax_shd.set_xlabel('S_M1 − S_Alvarado (nats)', fontsize=9)
ax_shd.set_title('Diferencia ΔS_Shannon\nM1 siempre mayor (19/19)', fontsize=10, fontweight='bold', pad=5)
ax_shd.invert_yaxis()
ax_shd.grid(axis='x', alpha=0.25)
for xi_p, d in enumerate(DIFF_sh):
    ax_shd.text(d + (0.006 if d >= 0 else -0.006), xi_p, f'{d:+.2f}',
                ha='left' if d >= 0 else 'right', va='center',
                fontsize=7, fontweight='bold', color=C_M1 if d > 0 else C_AL)
for sp in ['top','right']: ax_shd.spines[sp].set_visible(False)


# ═══════════════════════════════════════════════════════════════════════════
# FILA 2 — Boltzmann S_B + T_eff por 19 patrones
# ═══════════════════════════════════════════════════════════════════════════

ax_bo  = fig.add_subplot(gs[2, :2])
ax_T   = fig.add_subplot(gs[2, 2])

ax_bo.set_facecolor('#F4F4F2')
b3 = ax_bo.bar(x - w/2, S_bo_M1, w, color=C_M1, alpha=0.85, label='Nuestro M1',
               ec='white', lw=0.5, zorder=3)
b4 = ax_bo.bar(x + w/2, S_bo_AL, w, color=C_AL, alpha=0.85, label='Atomic-Go',
               ec='white', lw=0.5, zorder=3, hatch='///')
ax_bo.set_xticks(x); ax_bo.set_xticklabels(IDS, fontsize=10)
ax_bo.set_ylabel('S_Boltzmann  (nats)', fontsize=10)
ax_bo.set_title(
    'Entropía de Boltzmann  S_B = −Σ pᵢ ln pᵢ  con  pᵢ = e^(−Eᵢ/T_eff) / Z\n'
    'T_eff calculada de los bonos del mismo patrón  |  captura el "enfriamiento"',
    fontsize=10, fontweight='bold', pad=5)
ax_bo.legend(fontsize=10, loc='upper right', framealpha=0.92)
ax_bo.grid(axis='y', alpha=0.25)
for sp in ['top','right']: ax_bo.spines[sp].set_visible(False)

for bar, v in zip(b3, S_bo_M1):
    if v > 0.05:
        ax_bo.text(bar.get_x()+bar.get_width()/2, v+0.01, f'{v:.2f}',
                   ha='center', fontsize=6.5, color=C_M1, fontweight='bold')
for bar, v in zip(b4, S_bo_AL):
    if v > 0.05:
        ax_bo.text(bar.get_x()+bar.get_width()/2, v+0.01, f'{v:.2f}',
                   ha='center', fontsize=6.5, color=C_AL, fontweight='bold')

# T_eff por patron
ax_T.set_facecolor('#F4F4F2')
T_M1_plot = np.clip(T_M1_arr, 0, 10)
T_AL_plot = np.clip(T_AL_arr, 0, 10)
ax_T.barh(x - 0.2, T_M1_plot, 0.38, color=C_M1, alpha=0.85, label='M1', ec='white')
ax_T.barh(x + 0.2, T_AL_plot, 0.38, color=C_AL, alpha=0.85, label='Alvarado',
          ec='white', hatch='///')
ax_T.set_yticks(x); ax_T.set_yticklabels(IDS, fontsize=9)
ax_T.set_xlabel('T_eff = σ²(E) / |⟨E⟩|', fontsize=9)
ax_T.set_title('Temperatura efectiva\npor patrón (clip a 10)', fontsize=10, fontweight='bold', pad=5)
ax_T.invert_yaxis()
ax_T.legend(fontsize=8.5, loc='lower right', framealpha=0.92)
ax_T.grid(axis='x', alpha=0.25)
# Marcar saturados (T > 10)
for i, (tM, tA) in enumerate(zip(T_M1_arr, T_AL_arr)):
    if tM > 10: ax_T.text(9.8, i - 0.2, '∞', ha='right', va='center',
                           fontsize=8, color=C_M1, fontweight='bold')
    if tA > 10: ax_T.text(9.8, i + 0.2, '∞', ha='right', va='center',
                           fontsize=8, color=C_AL, fontweight='bold')
for sp in ['top','right']: ax_T.spines[sp].set_visible(False)


# ═══════════════════════════════════════════════════════════════════════════
# FILA 3 — Dispersiones comparativas
# ═══════════════════════════════════════════════════════════════════════════

ax_sc1 = fig.add_subplot(gs[3, 0])   # S_Shannon:  M1 vs Alvarado
ax_sc2 = fig.add_subplot(gs[3, 1])   # S_Boltzmann: M1 vs Alvarado
ax_sc3 = fig.add_subplot(gs[3, 2])   # S_Shannon vs S_Boltzmann por modelo

def scatter_setup(ax, xlabel, ylabel, title):
    ax.set_facecolor('#F4F4F2')
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold', pad=5)
    ax.grid(alpha=0.2);
    for sp in ['top','right']: ax.spines[sp].set_visible(False)

# Scatter 1: Shannon M1 vs Alvarado
scatter_setup(ax_sc1, 'S_Shannon  Alvarado  (nats)',
              'S_Shannon  M1  (nats)', 'Shannon: M1 vs Alvarado')
lim = [min(S_sh_M1.min(), S_sh_AL.min())*0.9, max(S_sh_M1.max(), S_sh_AL.max())*1.08]
ax_sc1.plot(lim, lim, '--', color='#888', lw=1.2, label='igualdad')
sc1 = ax_sc1.scatter(S_sh_AL, S_sh_M1, c=N_stones, cmap='viridis',
                     s=80, ec='white', lw=0.8, zorder=4)
plt.colorbar(sc1, ax=ax_sc1, shrink=0.7, pad=0.01, label='Nº piedras')
for r, xp, yp in zip(records, S_sh_AL, S_sh_M1):
    ax_sc1.text(xp+0.003, yp+0.003, r['id'], fontsize=7.5, color='#333')
m1, b1r = np.polyfit(S_sh_AL, S_sh_M1, 1)
xs = np.linspace(lim[0], lim[1], 100)
ax_sc1.plot(xs, m1*xs+b1r, '-', color='#7C3AED', lw=1.2, alpha=0.6,
            label=f'r={np.corrcoef(S_sh_M1,S_sh_AL)[0,1]:.2f}')
ax_sc1.legend(fontsize=8); ax_sc1.set_xlim(lim); ax_sc1.set_ylim(lim)
ax_sc1.fill_between(lim, lim, [lim[1]]*2, color=C_M1, alpha=0.04)
ax_sc1.text(lim[0]+(lim[1]-lim[0])*0.1, lim[1]*0.97, 'M1 > AL',
            fontsize=8, color=C_M1, alpha=0.6, va='top')

# Scatter 2: Boltzmann M1 vs Alvarado
scatter_setup(ax_sc2, 'S_Boltzmann  Alvarado  (nats)',
              'S_Boltzmann  M1  (nats)', 'Boltzmann: M1 vs Alvarado')
lim2 = [min(S_bo_M1.min(), S_bo_AL.min())*0.88,
         max(S_bo_M1.max(), S_bo_AL.max())*1.08]
ax_sc2.plot(lim2, lim2, '--', color='#888', lw=1.2, label='igualdad')
sc2 = ax_sc2.scatter(S_bo_AL, S_bo_M1, c=N_stones, cmap='viridis',
                     s=80, ec='white', lw=0.8, zorder=4)
plt.colorbar(sc2, ax=ax_sc2, shrink=0.7, pad=0.01, label='Nº piedras')
for r, xp, yp in zip(records, S_bo_AL, S_bo_M1):
    ax_sc2.text(xp+0.01, yp+0.01, r['id'], fontsize=7.5, color='#333')
m2, b2r = np.polyfit(S_bo_AL, S_bo_M1, 1)
ax_sc2.plot(xs if lim2 == lim else np.linspace(lim2[0], lim2[1], 100),
            m2*np.linspace(lim2[0], lim2[1], 100)+b2r,
            '-', color='#7C3AED', lw=1.2, alpha=0.6,
            label=f'r={np.corrcoef(S_bo_M1,S_bo_AL)[0,1]:.2f}')
ax_sc2.legend(fontsize=8); ax_sc2.set_xlim(lim2); ax_sc2.set_ylim(lim2)

# Scatter 3: S_Shannon vs S_Boltzmann por modelo
scatter_setup(ax_sc3, 'S_Shannon  (nats)', 'S_Boltzmann  (nats)',
              'Shannon vs Boltzmann por modelo\n(¿se mueven juntas o en sentido contrario?)')
ax_sc3.scatter(S_sh_M1, S_bo_M1, color=C_M1, s=80, ec='white',
               lw=0.8, zorder=4, label='Nuestro M1')
ax_sc3.scatter(S_sh_AL, S_bo_AL, color=C_AL, s=80, ec='white',
               lw=0.8, zorder=4, marker='D', label='Alvarado')
for r, xm, ym, xa, ya in zip(records, S_sh_M1, S_bo_M1, S_sh_AL, S_bo_AL):
    ax_sc3.text(xm+0.003, ym+0.003, r['id'], fontsize=6.5, color=C_M1)
    ax_sc3.text(xa+0.003, ya+0.003, r['id'], fontsize=6.5, color=C_AL)
r_M1 = np.corrcoef(S_sh_M1, S_bo_M1)[0,1]
r_AL = np.corrcoef(S_sh_AL, S_bo_AL)[0,1]
ax_sc3.text(0.97, 0.10,
    f'r_M1 = {r_M1:.2f}\nr_AL  = {r_AL:.2f}',
    transform=ax_sc3.transAxes, ha='right', va='bottom',
    fontsize=9.5, fontweight='bold', color='#333',
    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#CCC'))
ax_sc3.legend(fontsize=8.5, loc='upper left', framealpha=0.92)


# ─────────────────────────────────────────────────────────────────────────────
out = os.path.join(RESULTS, 'entropy_comparison.png')
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
print(f'Guardado: {out}')
plt.close(fig)

print('\n== Tabla de interaccion (9 pares) ==')
print(f'           S_Shannon   S_Boltzmann   T_eff')
print(f'  M1    :  {S_tab_sh_M1:.4f}     {S_tab_bo_M1:.4f}     '
      f'{"inf" if T_tab_M1>50 else f"{T_tab_M1:.3f}"}')
print(f'  Alvara:  {S_tab_sh_AL:.4f}     {S_tab_bo_AL:.4f}     '
      f'{"inf" if T_tab_AL>50 else f"{T_tab_AL:.3f}"}')
print(f'\n== 19 patrones ==')
print(f'{"ID":<5} {"S_sh_M1":>9} {"S_sh_AL":>9} {"S_bo_M1":>9} {"S_bo_AL":>9} {"T_M1":>7} {"T_AL":>7}')
print('-'*60)
for r in records:
    T_m = f'{r["T_M1"]:.2f}' if r['T_M1'] < 50 else 'inf'
    T_a = f'{r["T_AL"]:.2f}' if r['T_AL'] < 50 else 'inf'
    print(f'{r["id"]:<5} {r["S_sh_M1"]:>9.4f} {r["S_sh_AL"]:>9.4f} '
          f'{r["S_bo_M1"]:>9.4f} {r["S_bo_AL"]:>9.4f} {T_m:>7} {T_a:>7}')
print(f'\nCorrelacion S_sh vs S_bo:  M1 r={r_M1:.3f}   Alvarado r={r_AL:.3f}')
