"""Obnovi SVG i PNG skice za vodič za razgovor sa profesorom."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parent / 'slike'
OUT.mkdir(exist_ok=True)
BLUE, TEAL, ORANGE = '#2563eb', '#089187', '#d97706'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.labelcolor': '#334155', 'text.color': '#172b45',
                     'axes.edgecolor': '#94a3b8', 'svg.fonttype': 'none',
                     'figure.facecolor': '#f8fafc', 'axes.facecolor': '#f8fafc'})

def save(fig, name, note):
    fig.text(.05, .025, note, fontsize=10, color='#64748b')
    fig.savefig(OUT / (name + '.svg'), bbox_inches='tight')
    svg = OUT / (name + '.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    fig.savefig(OUT / (name + '.png'), dpi=160, bbox_inches='tight')
    plt.close(fig)

# Isti sintetički signal daje i talas i spektar.
fs, n = 16000, 8192
t = np.arange(n) / fs
y = .4*np.sin(2*np.pi*50*t) + np.sin(2*np.pi*100*t) + .6*np.sin(2*np.pi*200*t)
w = .5-.5*np.cos(2*np.pi*np.arange(n)/n)
p = np.abs(np.fft.rfft(y*w))**2
f = np.fft.rfftfreq(n, 1/fs)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
fig.subplots_adjust(bottom=.23, top=.76, wspace=.3)
fig.suptitle('Isti komad zvuka: vrijeme → frekvencija', fontsize=20, fontweight='bold')
ax[0].plot(t*1000, y, color=BLUE, lw=1)
ax[0].set(xlabel='Vrijeme [ms]', ylabel='Amplituda', xlim=(0,512), title='PCM • 8192 uzorka = 512 ms')
ax[1].plot(f, p/p.max(), color=TEAL, lw=2)
ax[1].set(xlim=(0,260), ylim=(0,1.15), xlabel='Frekvencija [Hz]', ylabel='Relativna snaga', title='Hann → FFT → |FFT|²')
ax[1].set_xticks([0,50,100,200,250])
for hz in [50,100,200]:
    k = np.argmin(abs(f-hz))
    ax[1].annotate(f'{hz} Hz', (f[k], p[k]/p.max()), xytext=(0,12), textcoords='offset points', ha='center', fontsize=10)
for a in ax: a.grid(alpha=.15)
save(fig, 'pcm-fft', 'Sintetički primjer: zbir tonova 50, 100 i 200 Hz; nije snimak ventilatora. Snaga je skalirana na maksimum.')

fig, axes = plt.subplots(4, 1, figsize=(12,7), sharex=True, gridspec_kw={'height_ratios':[.65,1,1,1]})
fig.subplots_adjust(left=.14, bottom=.18, top=.85, hspace=.4)
fig.suptitle('50% preklapanja: isti uzorci, druge Hann težine', fontsize=19, fontweight='bold')
colors = ['#dbeafe','#fde68a','#ccfbf1','#e2e8f0']
for j, letter in enumerate('ABCD'):
    axes[0].add_patch(Rectangle((j,0),1,1,facecolor=colors[j],edgecolor='white',lw=3))
    axes[0].text(j+.5,.5,letter,ha='center',va='center',fontweight='bold',fontsize=15)
axes[0].set_ylim(0,1)
axes[0].set_ylabel('PCM blokovi',rotation=0,labelpad=48,va='center')
axes[0].set_yticks([])
for i, a in enumerate(axes[1:]):
    x = np.linspace(0,2,500)
    h = .5-.5*np.cos(np.pi*x)
    a.axvspan(1,2,color='#fef3c7',alpha=.8)
    a.fill_between(x+i,h,color=[BLUE,TEAL,ORANGE][i],alpha=.13)
    a.plot(x+i,h,color=[BLUE,TEAL,ORANGE][i],lw=2.5)
    a.set(ylim=(0,1.15),yticks=[0,1])
    a.set_ylabel(f'Segment {i+1}\ntežina',rotation=0,labelpad=48,va='center')
    a.text(i+1,1.03,f'{"ABCD"[i]} + {"ABCD"[i+1]} • 8192 uzorka',ha='center',fontsize=10)
    a.grid(axis='x',alpha=.2)
axes[1].text(1.5,.72,'B: težina opada',ha='center',fontsize=10, bbox=dict(facecolor='#fef3c7',edgecolor='none',alpha=.9))
axes[2].text(1.5,.72,'B: težina raste',ha='center',fontsize=10, bbox=dict(facecolor='#fef3c7',edgecolor='none',alpha=.9))
axes[-1].set(xlim=(0,4),xticks=[0,1,2,3,4],xticklabels=['0','4096','8192','12288','16384'],xlabel='Položaj uzorka u toku • svaki novi segment počinje 4096 uzoraka kasnije')
save(fig, 'hann-preklapanje', 'Žuto označava isti blok B. Koristi se cijeli ponderisani segment; krajevi Hann prozora imaju težinu približno 0.')

fig, ax = plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1.2,1]})
fig.subplots_adjust(left=.12,bottom=.25,top=.75,wspace=.48)
fig.suptitle('Zadržim vrijeme ili prosječim snagu?',fontsize=20,fontweight='bold')
data = np.array([[1,5,1],[1,5,5],[1,5,1]])
ax[0].imshow(data,cmap='Blues',vmin=0,vmax=5,aspect='auto')
ax[0].set(xticks=[0,1,2],xticklabels=['f₁','f₂','f₃'],yticks=[0,1,2],yticklabels=['Vrijeme 1','Vrijeme 2','Vrijeme 3'],xlabel='Frekvencijski bin',title='Snaga STFT-a • svaki segment ostaje')
for i in range(3):
    for j in range(3): ax[0].text(j,i,str(data[i,j]),ha='center',va='center',color='white' if data[i,j]>3 else '#172b45',fontsize=17)
means = data.mean(axis=0)
ax[1].bar(range(3),means,color=[BLUE,TEAL,BLUE],width=.55)
ax[1].set(xticks=[0,1,2],xticklabels=['f₁','f₂','f₃'],ylim=(0,6),ylabel='Prosječna snaga',xlabel='Frekvencijski bin',title='Welch • jedan prosječan spektar')
for j,v in enumerate(means): ax[1].text(j,v+.15,f'{v:.2f}'.rstrip('0').rstrip('.').replace('.',','),ha='center')
ax[1].grid(axis='y',alpha=.15)
fig.text(.52,.46,'→',fontsize=32,ha='center',color=TEAL)
save(fig,'stft-welch','Ilustrativne snage, ista skala: za f₃ prosjek je (1 + 5 + 1) / 3 = 2,33. Welch prosječi snage, a ne PCM uzorke.')

fig, ax = plt.subplots(figsize=(12,4.8))
fig.subplots_adjust(left=.09,bottom=.25,top=.76,right=.97)
fig.suptitle('Mel filteri: preklopljene frekvencijske trake',fontsize=20,fontweight='bold')
melmax = 2595*np.log10(1+4000/700)
edges = 700*(10**(np.linspace(0,melmax,8)/2595)-1)
for j in range(6):
    c = [BLUE,TEAL,ORANGE][j%3]
    ax.fill(edges[j:j+3],[0,1,0],color=c,alpha=.12)
    ax.plot(edges[j:j+3],[0,1,0],color=c,lw=2)
    ax.text(edges[j+1],1.055,str(j+1),ha='center',color=c)
ax.set(xlim=(0,4000),ylim=(0,1.18),yticks=[0,.5,1],xlabel='Frekvencija [Hz] • linearna osa',ylabel='Težina filtera',title='Jednaki razmaci na mel skali → sve širi trouglovi na Hz osi')
ax.grid(alpha=.15)
save(fig,'mel-filteri','Ilustracija sa 6 filtera: mel traka = zbir snaga FFT binova pomnoženih težinama filtera. Ovo je raniji log-mel tok.')
print(f'Saved 4 SVG and 4 PNG images: {OUT}')
