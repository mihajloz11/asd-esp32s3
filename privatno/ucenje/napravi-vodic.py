"""Generiše samostalni HTML iz vodiča i stvarnih isječaka lokalnog koda.
Pokretanje iz korijena: .venv/Scripts/python.exe privatno/ucenje/napravi-vodic.py
"""
from pathlib import Path
import html
import re
import markdown
import runpy
import ast
from html.parser import HTMLParser

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FW = 'firmware/esp32s3_asd/main/'


def excerpt(path, start, end, title):
    lines = (ROOT / path).read_text(encoding='utf-8').splitlines()
    assert 1 <= start <= end <= len(lines), (path, start, end)
    numbered = '\n'.join(lines[start-1:end])
    link = '../../' + path
    return (f'<details class="source" open><summary>{html.escape(title)} · ključni kod</summary>'
            f'<p><a href="{link}">{html.escape(str(ROOT / path))}</a> · redovi {start}–{end} '
            '(snimak pri generisanju vodiča)</p>'
            f'<pre><code>{html.escape(numbered)}</code></pre></details>')


snippets = {
    2: [(FW+'audio_i2s.h', 13, 18, 'Frekvencija uzorkovanja i kapacitet bafera'),
        (FW+'audio_i2s.c', 129, 153, 'I2S: takt, format, pinovi i lijevi slot'),
        (FW+'audio_i2s.c', 96, 107, 'Prenos u 16-bitni PCM i ring buffer')],
    4: [(FW+'psd_features_c.h', 7, 9, 'Tri glavne konstante'),
        (FW+'psd_features_c.c', 25, 49, 'Stvarni radix-2 FFT')],
    5: [(FW+'psd_features_c.c', 51, 67, 'Pravljenje Hann težina'),
        (FW+'psd_features_c.c', 209, 223, 'Prethodni + tekući hop')],
    6: [(FW+'psd_features_c.c', 86, 94, 'Hann → FFT → snaga')],
    8: [(FW+'psd_features_c.c', 100, 121, 'Prosjek snage, logaritam i uklanjanje nivoa')],
    10: [('pc/tools/gen_psd_model_header.py', 49, 73, 'Učenje na 990 normalnih snimaka'),
         (FW+'psd_features_c.c', 245, 261, 'C funkcija za Mahalanobisov skor')],
    11: [(FW+'psd_live.c', 1047, 1080, 'Izvođenje i zamrzavanje pragova')],
    12: [(FW+'asd_temporal.c', 85, 107, 'Histereza i brojanje prekoračenja'),
         (FW+'asd_interference.c', 69, 103, 'Kada prozor odlazi u HOLD')],
    13: [('pc/tests/test_psd_features_c.py', 121, 135, 'Test istog WAV-a kroz Python i C')],
    15: [('pc/asd/model.py', 19, 37, 'Istorijski Keras autoenkoder')],
}

# Kratki isječci su zajednički Markdown i HTML verziji; ništa se ne prepisuje ručno.
snippets[1] = [(FW+'app_main.c', 169, 178, 'Ulaz u samostalni PSD tok')]
snippets[2].append((FW+'psd_live.c', 489, 491, 'PCM amplituda postaje float'))
snippets[3] = [(FW+'psd_features_c.c', 91, 92, 'Jednostrani spektar: binovi do N/2')]
snippets[6] += [('pc/asd/features.py', 51, 56, 'STFT: poseban spektar za svaki frejm — istorijski frontend'),
                ('pc/tools/bench_periodicity.py', 56, 58, 'Welch i 96 traka — finalni frontend')]
snippets[7] = [('pc/asd/features.py', 63, 65, 'STFT snaga → mel filteri → logaritam — istorijski frontend'),
               ('pc/tools/bench_periodicity.py', 40, 45, 'Srednja snaga u logaritamskim intervalima — finalni frontend')]
snippets[10][0] = ('pc/tools/gen_psd_model_header.py', 59, 72, 'Standardizacija i Ledoit–Wolf na normalnim podacima')
snippets[11].insert(0, (FW+'psd_live.c', 820, 825, 'Početni CAL centar prije moguće K1 korekcije'))
snippets[11].insert(1, (FW+'psd_live.c', 829, 836, 'LOO centar bez klipa koji ocjenjujemo'))
snippets[11][-1] = (FW+'psd_live.c', 1047, 1057, 'Ulazni i izlazni percentil — prije ograničenja izlaznog praga')
snippets[12][1] = (FW+'asd_interference.c', 87, 102, 'Visok skor je već provjeren: nestabilnost aktivira HOLD')
snippets[15].append(('pc/asd/quantize.py', 22, 36, 'Keras → TFLite, opciono int8 — istorijski tok'))
snippets[16] = [('pc/asd/eval.py', 47, 56, 'Računanje ROC AUC i pAUC')]


def markdown_excerpts(number):
    blocks = []
    for path, start, end, title in snippets.get(number, []):
        lines = (ROOT / path).read_text(encoding='utf-8').splitlines()
        assert 1 <= start <= end <= len(lines)
        code = '\n'.join(lines[start-1:end])
        language = 'python' if path.endswith('.py') else 'c'
        blocks.append(f'### Ključni kod: {title}\n\n'
                      f'**Puna putanja:** `{ROOT / path}`\n\n'
                      f'**Redovi:** {start}–{end}. Doslovni isječak; okolni kod je izostavljen.\n\n'
                      f'```{language}\n{code}\n```')
    return '\n\n'.join(blocks)


class LessonMarkdown(HTMLParser):
    """Prenosi tekst ilustracija u MD; SVG crteže zamjenjuju postojeće slike."""
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('svg', 'script', 'style'):
            self.skip += 1
        if self.skip:
            return
        if tag == 'h3':
            self.parts.append('\n\n### ')
        elif tag in ('p', 'div'):
            self.parts.append('\n\n')
        elif tag in ('b', 'strong'):
            self.parts.append('**')
        elif tag == 'code':
            self.parts.append('`')
        elif tag in ('button', 'label', 'option', 'span'):
            self.parts.append(' ')
        elif tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('svg', 'script', 'style'):
            self.skip -= 1
            return
        if self.skip:
            return
        if tag in ('h3', 'p', 'div'):
            self.parts.append('\n\n')
        elif tag in ('b', 'strong'):
            self.parts.append('**')
        elif tag == 'code':
            self.parts.append('`')
        elif tag in ('button', 'label', 'option', 'span'):
            self.parts.append(' · ')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def markdown(self):
        text = re.sub(r'[ \t]+', ' ', ''.join(self.parts))
        text = '\n'.join(line.strip().strip('·').strip() for line in text.splitlines())
        return re.sub(r'\n{3,}', '\n\n', text).strip()


def lesson_markdown(fragment):
    parser = LessonMarkdown()
    parser.feed(fragment)
    return parser.markdown()


def animation_steps(script, name):
    match = re.search(r'const ' + re.escape(name) + r'\s*=\s*(\[.*?\]);', script, re.S)
    if not match:
        raise ValueError(f'Nedostaju koraci animacije: {name}')
    return '\n\n**Tekst koraka animacije:**\n\n' + '\n\n'.join(
        f'- {text}' for text in ast.literal_eval(match.group(1)))

diagrams = {
1: '''<div class="flow" aria-label="Put signala"><span>Zvuk</span><b>→</b><span>I2S / PCM</span><b>→</b><span>Welch / 96 brojeva</span><b>→</b><span>Skor</span><b>→</b><span>Pouzdano i trajno?</span><b>→</b><span>Alarm</span></div>''',
4: '''<div class="lab"><h3>Promijeni N, a uzorkovanje ostaje 16 kHz</h3><label for="fftN">Dužina FFT-a </label><select id="fftN"><option>1024</option><option>2048</option><option>4096</option><option selected>8192</option><option>16384</option></select><p id="fftReadout" aria-live="polite"></p><svg id="fftPlot" viewBox="0 0 720 180" role="img" aria-label="Frekvencijske tačke između 100 i 200 herca"></svg><p class="caption">Tačke su FFT binovi u opsegu 100–200 Hz. Gušće tačke znače finiji razmak; ovo nije simulacija razdvajanja dva tona.</p></div>''',
5: '''<div class="lab"><h3>Isti uzorak, dvije različite težine</h3><label for="hannX">Položaj uzorka u zajedničkom dijelu </label><input id="hannX" type="range" min="4096" max="8191" value="6144"><svg id="hannPlot" viewBox="0 0 720 250" role="img" aria-label="Dva Hann prozora pomjerena za polovinu dužine"></svg><p id="hannReadout" aria-live="polite"></p><p class="caption">Plavo: segment [A B]. Narandžasto: segment [B C]. Mijenjaj položaj uzorka i gledaj kako se težine dopunjuju. Za Welch prosječimo snage, ne sabiramo prozore da vratimo originalni signal.</p></div>''',
9: '''<div class="lab"><h3>Isti lenjir, različita neobičnost</h3><svg id="distancePlot" viewBox="0 0 720 320" role="img" aria-label="Izdužen oblak normalnog rada i dvije jednako udaljene tačke"></svg><label for="rho">Koliko snažno trake rastu zajedno </label><input id="rho" type="range" min="0" max="90" value="80"><p id="distanceReadout" aria-live="polite"></p><p class="caption">Ilustrativne dvije dimenzije, nije mjerenje našeg ventilatora. Matrica je [[1, ρ], [ρ, 1]]. Elipsa označava isti Mahalanobisov skor 4. Prikazane tačke imaju istu euklidsku udaljenost od centra.</p></div>''',
12: '''<div class="lab"><h3>Ručno isprobaj pravilo alarma</h3><p>Ilustrativni pragovi: ulaz 100, izlaz 50. Jedan klik predstavlja jedan približno 10-sekundni prozor.</p><div class="buttons"><button data-step="high">Skor 120 · pouzdan</button><button data-step="mid">Skor 80 · pouzdan</button><button data-step="low">Skor 40 · pouzdan</button><button data-step="hold">Skor 120 · HOLD</button><button data-step="reset">Počni ponovo</button></div><p id="alarmReadout" aria-live="polite"></p><div id="alarmHistory" class="history"></div><p class="caption">Pojednostavljen prikaz vremenskog pravila i HOLD-a. Ne simulira cijeli firmware: greške senzora, odsustvo mašine, commissioning i trajni događaji imaju dodatnu logiku.</p></div>''',
}

css = '''
:root{--ink:#183239;--muted:#526b71;--line:#d6e1df;--accent:#086d78;--paper:#fff;--bg:#f1f5f3;--orange:#bb5e17}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--bg);font:17px/1.75 system-ui,Segoe UI,sans-serif}a{color:var(--accent)}aside{position:fixed;left:0;top:0;bottom:0;width:280px;overflow:auto;padding:28px 22px;background:#102e35;color:#dfefeb}aside a{display:block;color:#d9eae8;text-decoration:none;font-size:13px;line-height:1.5;padding:7px 0;border-bottom:1px solid #ffffff12}aside a:hover{color:#80e4ce}aside .brand{font-size:22px;line-height:1.3;font-weight:700;margin:0 0 12px}aside small{color:#a6c2c3}main{max-width:1150px;margin:0 auto 0 300px;padding:36px 46px 80px}header{padding:25px 0 35px}h1{font-size:46px;line-height:1.16;letter-spacing:-1.5px;max-width:800px}h2{font-size:29px;line-height:1.3;margin:0 0 24px;letter-spacing:-.5px}h3{line-height:1.4;font-size:20px}p{margin:16px 0}section{background:var(--paper);padding:34px 38px;margin:0 0 26px;border:1px solid var(--line);border-radius:15px;scroll-margin-top:20px}section:target{border-color:var(--accent)}.tag{font:700 12px/1.5 system-ui;letter-spacing:2px;text-transform:uppercase;color:var(--accent)}.toolbar{display:flex;gap:10px;flex-wrap:wrap}button,select{font:inherit;color:var(--ink);border:1px solid #b9ceca;background:white;padding:9px 13px;border-radius:8px;cursor:pointer}button:hover{background:#e1f2ed}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #edb252;outline-offset:3px}input[type=range]{width:min(310px,100%);accent-color:var(--accent);vertical-align:middle}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;margin:22px 0}th,td{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#edf4f1}code{font: .87em/1.6 Consolas,monospace;overflow-wrap:anywhere;background:#edf3f1;padding:2px 4px;border-radius:4px}pre{overflow:auto;padding:20px;background:#112e36;color:#e4f3ef;border-radius:9px;font-size:13px;line-height:1.6}pre code{background:none;padding:0;color:inherit;white-space:pre;overflow-wrap:normal}.source{margin:15px 0;border:1px solid #c9dad5;border-radius:9px;padding:12px 16px;font-size:14px}.source summary{cursor:pointer;font-weight:650}.source p{font-size:12px;overflow-wrap:anywhere}.lab{padding:23px;background:#eff7f4;border:1px solid #b9d8cf;border-radius:12px;margin:26px 0}.lab svg{display:block;width:100%;height:auto;margin:20px 0}svg text{font-family:system-ui,sans-serif;font-size:13px;fill:#344f57}.caption{font-size:13px;color:var(--muted)}.flow{display:flex;gap:9px;align-items:center;flex-wrap:wrap;padding:20px 0}.flow span{padding:9px 12px;background:#dff1eb;border-radius:7px;font-size:14px;font-weight:600}.buttons{display:flex;gap:8px;flex-wrap:wrap}.buttons button{font-size:14px}.history{display:flex;gap:6px;flex-wrap:wrap;min-height:42px}.history span{padding:4px 8px;background:#d6e9e4;font-size:13px;border-radius:5px}.history .warn{background:#ffe2a9}.history .alarm{background:#ffc7c1}.formula{font-weight:650}.compact section p,.compact section li{line-height:1.6}.compact .source{display:none}noscript{display:block;padding:15px;background:#ffe2a9}footer{font-size:13px;color:var(--muted)}
@media(min-width:1500px){main{margin-left:calc(280px + (100vw - 1450px)/2)}}
@media(max-width:1000px){aside{position:static;width:auto;max-height:270px}aside nav{columns:2}main{margin:0;padding:22px}h1{font-size:36px}section{padding:24px}}
@media(max-width:580px){body{font-size:16px}main{padding:12px}section{padding:20px 16px}h1{font-size:32px}h2{font-size:25px}table{display:block;overflow:auto}aside nav{columns:1}section li{margin:8px 0}.lab{padding:14px}}
@media print{aside,.toolbar,.buttons,input,select{display:none}main{margin:0;padding:0;max-width:none}body{font-size:11pt;background:white}h1{font-size:27pt}section{padding:15px 0;border:0;border-bottom:1px solid #ccc;break-inside:auto}h2,h3{break-after:avoid}a{color:inherit}pre{white-space:pre-wrap}details:not([open]){display:none}.lab{break-inside:avoid}header{padding:0}}
'''

js = r'''
const $=id=>document.getElementById(id);
const ns='http://www.w3.org/2000/svg';
function el(svg,tag,attrs,text){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,(k==='fill'||k==='stroke')?studioColor(v):v);if(text!==undefined)e.textContent=text;svg.appendChild(e);return e}
function line(s,x1,y1,x2,y2,c='#b5c9c4',w=1){return el(s,'line',{x1,y1,x2,y2,stroke:c,'stroke-width':w})}
function txt(s,x,y,t){return el(s,'text',{x,y},t)}
function drawFFT(){const n=+$('fftN').value,df=16000/n,s=$('fftPlot');s.replaceChildren();line(s,40,125,680,125);for(let f=100;f<=200;f+=25){line(s,40+(f-100)*6.4,120,40+(f-100)*6.4,130);txt(s,28+(f-100)*6.4,154,f+' Hz')}for(let k=Math.ceil(100/df);k*df<=200;k++){let x=40+(k*df-100)*6.4;line(s,x,65,x,122,'#087e8b',2);el(s,'circle',{cx:x,cy:65,r:3,fill:'#087e8b'})}txt(s,40,30,'Isti frekvencijski opseg, drugačiji razmak binova');$('fftReadout').textContent=`N = ${n} → segment ${(n/16).toFixed(0)} ms → razmak ${df.toFixed(3)} Hz. Hop pri 50% preklapanja: ${(n/32).toFixed(0)} ms.`}
function drawHann(){const s=$('hannPlot'),n=8192,pos=+$('hannX').value;s.replaceChildren();const xx=x=>40+x/12288*630,yy=w=>185-w*135;line(s,40,185,680,185);for(let j=0;j<3;j++){txt(s,xx(j*4096+2048),218,['A','B','C'][j]);line(s,xx(j*4096),190,xx(j*4096),197)}for(let q=0;q<2;q++){let pts=[];for(let i=0;i<=256;i++){const u=i/256;pts.push(`${xx(q*4096+u*n)},${yy(.5-.5*Math.cos(2*Math.PI*u))}`)}el(s,'polyline',{points:pts.join(' '),fill:'none',stroke:q?'#bb5e17':'#087e8b','stroke-width':3})}const w1=.5-.5*Math.cos(2*Math.PI*pos/n),w2=.5-.5*Math.cos(2*Math.PI*(pos-4096)/n);line(s,xx(pos),30,xx(pos),188,'#546b72',1);el(s,'circle',{cx:xx(pos),cy:yy(w1),r:6,fill:'#087e8b'});el(s,'circle',{cx:xx(pos),cy:yy(w2),r:6,fill:'#bb5e17'});txt(s,40,24,'Hann težina: 0 na rubu, 1 u sredini');$('hannReadout').textContent=`Uzorak ${pos}: plava težina ${w1.toFixed(3)} + narandžasta ${w2.toFixed(3)} = ${(w1+w2).toFixed(3)}. Uzorak nije izrezan iz snimka.`}
function drawDistance(){const s=$('distancePlot'),r=+$('rho').value/100;s.replaceChildren();const cx=340,cy=160,k=48;line(s,120,cy,560,cy);line(s,cx,305,cx,15);txt(s,566,cy,'traka 1');txt(s,cx+10,20,'traka 2');const pts=[];for(let i=0;i<=150;i++){let t=i/150*2*Math.PI,a=2*Math.sqrt(1+r)*Math.cos(t),b=2*Math.sqrt(1-r)*Math.sin(t);pts.push(`${cx+k*(a+b)/Math.sqrt(2)},${cy-k*(a-b)/Math.sqrt(2)}`)}el(s,'polygon',{points:pts.join(' '),fill:'#cee9e0',stroke:'#398b77','stroke-width':2});el(s,'circle',{cx,cy,r:Math.sqrt(8)*k,fill:'none',stroke:'#7d9ba0','stroke-dasharray':'5 5'});for(const [x,y,label,c]of[[2,2,'A: zajedno rastu','#087e8b'],[2,-2,'B: suprotno se mijenjaju','#bb5e17']]){el(s,'circle',{cx:cx+x*k,cy:cy-y*k,r:6,fill:c});txt(s,cx+x*k+12,cy-y*k,label)}$('distanceReadout').textContent=`ρ = ${r.toFixed(2)}. Euklidska udaljenost za A i B: √8 ≈ 2,83. Kvadrirani Mahalanobis: A = ${(8/(1+r)).toFixed(2)}, B = ${(8/(1-r)).toFixed(2)}. ${r===0?'Bez korelacije ova razlika nestaje.':'Odstupanje protiv uobičajene veze dobija veći skor.'}`}
let run=0,active=false,count=0;
function alarm(kind){if(kind==='reset'){run=0;active=false;count=0;$('alarmHistory').replaceChildren();$('alarmReadout').textContent='Brojač 0/3 · nema alarma.';return}count++;let score={high:120,mid:80,low:40}[kind];if(kind==='hold')run=0;else if(active){if(score<=50){active=false;run=0}}else{run=score>100?run+1:0;if(run>=3)active=true}let status=kind==='hold'?(active?'HOLD · postojeći alarm ostaje':'HOLD · bez novog alarma'):(active?'ALARM':'nema alarma');$('alarmReadout').textContent=`Prozor ${count} · ${status} · brojač ${run}/3`;let chip=document.createElement('span');chip.className=kind==='hold'?'warn':active?'alarm':'';chip.textContent=`${count}: ${kind==='hold'?'HOLD':score}${active?' ●':''}`;$('alarmHistory').appendChild(chip);if($('alarmHistory').children.length>18)$('alarmHistory').firstChild.remove()}
$('fftN').addEventListener('change',drawFFT);$('hannX').addEventListener('input',drawHann);$('rho').addEventListener('input',drawDistance);document.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>alarm(b.dataset.step)));$('print').addEventListener('click',()=>window.print());$('codes').addEventListener('click',()=>{const ds=[...document.querySelectorAll('details.source')],open=ds.some(d=>!d.open);ds.forEach(d=>d.open=open);$('codes').textContent=open?'Zatvori sve isječke koda':'Otvori sve isječke koda'});drawFFT();drawHann();drawDistance();alarm('reset');
'''

# Dodatne ilustracije se ugrađuju direktno: HTML ostaje samostalan i offline.
visuals = runpy.run_path(str(HERE / 'vizuelni-dodaci.py'))
for chapter, visual in visuals['DIAGRAMS'].items():
    diagrams[chapter] = diagrams.get(chapter, '') + visual
css += visuals['CSS']
js += visuals['JS']
fft_lesson = runpy.run_path(str(HERE / 'fft-lekcija.py'))
diagrams[4] = fft_lesson['HTML'] + diagrams.get(4, '')
js += fft_lesson['JS']
studio = runpy.run_path(str(HERE / 'studio-izgled.py'))
css += studio['CSS']
js += studio['JS']


def svg_frame(title, body, height=310):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 {height}" '
            f'role="img" aria-label="{title}"><title>{title}</title>'
            '<style>text{font:16px system-ui,sans-serif;fill:#183239}.small{font-size:13px}</style>'
            f'<rect width="760" height="{height}" rx="12" fill="#eff7f4"/>{body}</svg>')


mel_shapes = ''
for a, b, c in [(45, 95, 165), (95, 165, 270), (165, 270, 425), (270, 425, 700)]:
    mel_shapes += f'<polygon points="{a},125 {b},55 {c},125" fill="#087e8b" fill-opacity=".12" stroke="#087e8b" stroke-width="2"/>'
for a, b in zip([45, 95, 165, 270, 425], [95, 165, 270, 425, 700]):
    mel_shapes += f'<rect x="{a}" y="205" width="{b-a}" height="50" fill="#bb5e17" fill-opacity=".12" stroke="#bb5e17" stroke-width="2"/>'
static_images = {
    7: ('mel-i-psd-trake.svg', 'Mel filteri i PSD intervali — konceptualna šema', svg_frame(
        'Mel filteri i PSD intervali', '<text x="30" y="30">Mel: preklopljeni filteri, frekvencije dobijaju različite težine</text>'
        + mel_shapes + '<text x="30" y="175">Naš PSD: odvojeni intervali, prosjek binova unutar intervala</text>'
        '<text class="small" x="30" y="290">Šematski prikaz nekoliko traka; nije stvarna skala svih 128 / 96 traka.</text>')),
    11: ('pc-i-esp32-ucenje.svg', 'Šta uči PC, a šta ESP32', svg_frame(
        'Podjela učenja između PC-a i ESP32',
        '<rect x="25" y="25" width="710" height="98" rx="10" fill="#d5eae4"/>'
        '<text x="45" y="53">PC · 990 normalnih source snimaka</text>'
        '<text x="45" y="82">Standardizacija + Ledoit–Wolf → matrica i parametri u C zaglavlju</text>'
        '<text class="small" x="45" y="107">Izvoz na uređaj; kovarijansa se ne uči ponovo uživo.</text>'
        '<path d="M380 124 V156 M373 147 L380 157 L387 147" fill="none" stroke="#086d78" stroke-width="3"/>'
        '<rect x="25" y="166" width="710" height="123" rx="10" fill="#e5ebe1"/>'
        '<text x="45" y="193">ESP32 · normalan zvuk konkretne postavke</text>'
        '<text x="45" y="223">CAL: centar → DERIVE: pragovi → VERIFY: provjera</text>'
        '<text x="45" y="253">DET: zamrznut profil + novi zvuk → skor i odluka</text>'
        '<text class="small" x="45" y="277">Ciljane anomalije ne ulaze u učenje centra ili pragova.</text>')),
}
for filename, _, drawing in static_images.values():
    (HERE / filename).write_text(drawing, encoding='utf-8')

md_path = HERE / 'VODIC-KROZ-PROJEKAT.md'
md = md_path.read_text(encoding='utf-8')
# Uklanjamo samo svoje generisane dodatke, pa je ponovno pokretanje bez duplikata.
md = re.sub(r'\n<!-- BEGIN KEY CODE -->.*?<!-- END KEY CODE -->\n', '', md, flags=re.S)
chunks = re.split(r'(?m)^## ', md)
sections, nav, updated = [], [], [chunks[0]]
for chunk in chunks[1:]:
    title, body = chunk.split('\n', 1)
    number = int(title.split('.')[0])
    nav.append(f'<a href="#s{number}">{html.escape(title)}</a>')
    # Isti tekst ilustracija i isti redosljed kao u HTML-u, bez ručnog prepisivanja.
    addition = lesson_markdown(diagrams.get(number, ''))
    if number == 4:
        addition += animation_steps(fft_lesson['JS'], 'chainText')
    if number == 13:
        addition += animation_steps(visuals['JS'], 'parityDescriptions')
    code_text = markdown_excerpts(number)
    if code_text:
        addition += '\n\n' + code_text
    if number in static_images:
        filename, caption, _ = static_images[number]
        addition += f'\n\n![{caption}]({filename})\n\n*{caption}.*'
    if addition:
        # Originalni tekst ostaje doslovno isti; dodaci idu ispod objašnjenja.
        body += '\n<!-- BEGIN KEY CODE -->\n' + addition + '\n<!-- END KEY CODE -->\n'
    updated.append('## ' + title + '\n' + body)
    html_body = re.sub(r'\n<!-- BEGIN KEY CODE -->.*?<!-- END KEY CODE -->\n', '', body, flags=re.S)
    rendered = markdown.markdown(html_body, extensions=['tables', 'fenced_code'])
    extra = diagrams.get(number, '')
    for args in snippets.get(number, []):
        extra += excerpt(*args)
    if number in static_images:
        _, caption, drawing = static_images[number]
        extra += f'<div class="lab">{drawing}<p class="caption">{caption}</p></div>'
    sections.append(f'<section id="s{number}"><h2>{html.escape(title)}</h2>{rendered}{extra}</section>')

page = f'''<!doctype html>
<html lang="sr-Latn"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Jednostavan vodič kroz ESP32-S3 detektor zvuka ventilatora, sa stvarnim kodom i interaktivnim ilustracijama."><title>Od zvuka do alarma · vodič kroz projekat</title><style>{css}</style></head>
<body><aside><p class="brand">Od zvuka<br>do alarma.</p><small>ESP32-S3 · vodič za razumijevanje<br>i razgovor sa profesorom</small><nav aria-label="Sadržaj">{''.join(nav)}</nav></aside>
<main><header><p class="tag">Tvoj projekat, korak po korak</p><h1>Razumij prvo.<br>Onda pokaži u kodu.</h1><p>Od mikrofona i uzoraka do spektra, modela i odluke. Kratke cjeline, pitanja za samoprovjeru i 17 interaktivnih ilustracija kroz cijeli vodič.</p><p class="caption">Provjereno prema lokalnom kodu i zapisima 23.09.2026. · Finalni tok: ASD_PSD_LIVE · Sve radi lokalno, bez interneta. Isječci su preuzeti iz stvarnih fajlova; ilustracije su obrazovne, nijesu eksperimentalni rezultati.</p><div class="toolbar"><button id="print">Štampaj / sačuvaj PDF</button><button id="codes">Zatvori sve isječke koda</button><a href="VODIC-KROZ-PROJEKAT.md">Markdown verzija</a></div></header><noscript>Tekst i kod možeš čitati bez JavaScripta. Interaktivne ilustracije zahtijevaju uključen JavaScript.</noscript>{''.join(sections)}<footer>Izvor teksta: VODIC-KROZ-PROJEKAT.md. Za osvježavanje isječaka poslije promjene koda pokreni napravi-vodic.py. Brojevi redova pripadaju stanju pri generisanju.</footer></main><script>{js}</script></body></html>'''
page = page.replace('</header>', '</header>' + studio['HEADER'], 1)
md_path.write_text(''.join(updated), encoding='utf-8')
output = HERE / 'VODIC-KROZ-PROJEKAT.html'
output.write_text(page, encoding='utf-8')
print(f'Generated {output.name}: {len(sections)} sections, {sum(map(len,snippets.values()))} source excerpts, {len(page.encode("utf-8"))} bytes')
