"""Obrazovne ilustracije za vodič; podaci su sintetički, ne mjerenja projekta."""


def lab(key, title, instruction, controls, memory, caption, height=290):
    return f'''<div class="lab visual-lesson"><h3>{title}</h3><p>{instruction}</p>
    <div class="buttons">{controls}</div>
    <svg id="{key}Plot" viewBox="0 0 760 {height}" role="img" aria-label="{title}"></svg>
    <p id="{key}Readout" class="lesson-readout" aria-live="polite"></p>
    <p class="remember"><b>Zapamti:</b> {memory}</p><p class="caption">{caption}</p></div>'''


DIAGRAMS = {
    2: lab('sample', 'Kako talas postaje niz brojeva',
           'Pritisni „Sljedeći uzorak”. Svaka tačka je jedno očitavanje amplitude. Pokreni animaciju da vidiš kako se niz puni.',
           '<button id="sampleNext">Sljedeći uzorak</button><button id="samplePlay" aria-pressed="false">Pokreni animaciju</button><button id="sampleReset">Vrati na početak</button>',
           'PCM pamti visinu talasa u trenucima uzorkovanja, a ne spisak frekvencija.',
           'Usporena ilustracija: 16 tačaka po periodi izmišljenog talasa. Naš mikrofon daje 16000 uzoraka u sekundi. Prikazane amplitude su normalizovane, nijesu sirovi I2S bitovi.'),
    3: lab('alias', 'Nyquist: isti uzorci mogu skrivati drugi ton',
           'Izaberi ton. Plava linija je originalni idealni kosinus; tačke su uzorci pri 16 kHz. Iznad granice se pojavljuje narandžasti ton sa istim uzorcima.',
           '<label for="aliasHz">Ton </label><select id="aliasHz"><option value="2000">2 kHz</option><option value="6000">6 kHz</option><option value="10000" selected>10 kHz</option><option value="14000">14 kHz</option></select>',
           'Kada uzorci već izgledaju isto, FFT ne može pogoditi koji je originalni ton bio prisutan.',
           'Matematička ilustracija idealnog uzorkovanja, bez anti-alias filtriranja. Ne simulira interni filter INMP441 mikrofona.'),
    6: lab('spectrum', 'PSD: jedan pomiješan zvuk, dvije frekvencije',
           'Pomjeraj jačinu komponente od 300 Hz. Istovremeno gledaj oblik talasa lijevo i raspored snage desno.',
           '<label for="toneAmp">Amplituda tona 300 Hz </label><input id="toneAmp" type="range" min="0" max="100" value="50"><button id="tonePlay" aria-pressed="false">Pokreni animaciju</button>',
           'Lijevo pitaš „kako se zvuk mijenja kroz vrijeme?”, desno „gdje mu je snaga po frekvenciji?”.',
           'Idealna suma sinusoida od 100 i 300 Hz. Desno je teorijska srednja snaga A²/2 svake komponente, a ne rezultat FFT-a ili stvarno mjerenje. Stvarni konačni prozori daju šire vrhove.', 310),
    8: lab('shape', 'Glasnije nije isto što i drugačiji oblik',
           'Mijenjaj zajedničku jačinu ili uključi promjenu jedne trake. Desno se od svake vrijednosti oduzima zajednička sredina.',
           '<label for="shapeGain">Zajednički log-pomak </label><input id="shapeGain" type="range" min="0" max="30" value="10"><button id="shapeChange" aria-pressed="false">Promijeni samo treću traku</button>',
           'Zajednički pomak nestaje centriranjem. Promjena odnosa među trakama ostaje.',
           'Četiri izmišljene log-vrijednosti umjesto 96. Idealizovano, bez praznih traka i poda; u fizički korišćenom baselineu otpornost na glasnoću nije savršena.', 310),
    13: lab('parity', 'Dokaz slaganja: jedan snimak, dva računa',
            'Prođi korake redom. Ključ je da PC i pločica dobiju iste uzorke, ne dva slična snimka.',
            '<button id="parityNext">Sljedeći korak</button><button id="parityReset">Vrati na početak</button>',
            'Isti ulaz + iste postavke → poređenje izlaza ima smisla.',
            'Šema stvarne metode provjere. Brojevi u zelenoj kutiji su ilustrativni; istorijska izmjerena greška i fajlovi navedeni su u tekstu iznad.', 290),
}

DIAGRAMS[6] += lab('welch', 'Welch: više spektara → jedan prosjek',
    'Dodaj spektar sljedećeg segmenta. Siva linija pokazuje trenutni segment; plava prosjek svih do sada dodatih segmenata.',
    '<button id="welchNext">Dodaj sljedeći segment</button><button id="welchPlay" aria-pressed="false">Pokreni animaciju</button><button id="welchReset">Vrati na početak</button>',
    'Ponavljajuća struktura ostaje u prosjeku; promjenljiva kolebanja se ublažavaju.',
    'Sintetički spektri za prikaz prosječenja, bez izračunavanja FFT-a. U projektu prosječimo 38 preklopljenih segmenata; oni nijesu nezavisni. Prosjek ne garantuje uklanjanje svake buke.')

CSS = '''
.lesson-readout{min-height:3.5em;padding:12px 15px;border-left:4px solid #087e8b;background:#fff}
.remember{padding:12px 15px;background:#d8ede4;border-radius:8px}
.visual-lesson button[aria-pressed=true]{background:#183f49;color:white}
.visual-lesson svg{background:#fff;border-radius:8px}
.visual-lesson label{align-self:center}.visual-lesson .buttons{align-items:center}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''

DIAGRAMS[10] = lab('shrink', 'Ledoit–Wolf: ublaži nesigurne veze',
    'Pomjeraj jačinu skupljanja. Izdužena elipsa postepeno postaje pravilnija: vrlo uski smjer više ne dobija ekstremnu težinu.',
    '<label for="shrinkAmount">Ilustrativno skupljanje </label><input id="shrinkAmount" type="range" min="0" max="100" value="20">',
    'Skupljanje stabilizuje procjenu kovarijanse. Ne uči gdje je kvar.',
    'Dvodimenzionalni primjer: (1 − α) × kovarijansa + α × I, sa varijansama 1. U pravom Ledoit–Wolf postupku α se procjenjuje iz podataka; ne bira se ovim klizačem.')
DIAGRAMS[15] = lab('ae', 'Autoenkoder: original → uski kod → rekonstrukcija',
    'Uporedi ulaz i rekonstrukciju. Isprobaj anomaliju koju mreža takođe dobro kopira: mala greška tada nije dokaz normalnog rada.',
    '<label for="aeCase">Primjer </label><select id="aeCase"><option value="normal">Normalan zvuk, dobra kopija</option><option value="bad">Anomalija, loša kopija</option><option value="miss">Anomalija, dobra kopija</option></select>',
    'Autoenkoderov skor mjeri grešku kopiranja. To nije direktna mjera zdravlja mašine.',
    'Izmišljeni vektori od četiri broja, bez izvršavanja neuronske mreže. Služe samo da pokažu ideju i mogući promašaj.', 310)
DIAGRAMS[16] = lab('roc', 'Prag: više detekcija ili manje lažnih alarma?',
    'Svaka tačka je jedan snimak. Plavo označava stvarno normalne snimke, narandžasto stvarne anomalije. Sve desno od praga označavamo kao anomaliju.',
    '<label for="rocThreshold">Prag skora </label><input id="rocThreshold" type="range" min="0" max="100" value="55">',
    'Niži prag hvata više anomalija, ali može označiti i više normalnih snimaka.',
    'Mali izmišljeni skup za objašnjenje TPR/FPR. Ovo je odluka po jednom skoru, bez pravila tri prozora; nije stvarni ROC rezultat projekta.')

JS = r'''
// Ilustracije imaju eksplicitno pokretanje. U pozadini se automatski zaustavljaju.
const lessonTimers = new Map();
function stopLesson(id){if(lessonTimers.has(id)){clearInterval(lessonTimers.get(id));lessonTimers.delete(id)}const b=$(id);b.textContent='Pokreni animaciju';b.setAttribute('aria-pressed','false')}
function toggleLesson(id,step,ms){if(lessonTimers.has(id)){stopLesson(id);return}$(id).textContent='Zaustavi animaciju';$(id).setAttribute('aria-pressed','true');lessonTimers.set(id,setInterval(step,ms))}
document.addEventListener('visibilitychange',()=>{if(document.hidden)[...lessonTimers.keys()].forEach(stopLesson)});
const lessonObserver=typeof IntersectionObserver==='undefined'?null:new IntersectionObserver(entries=>{for(const e of entries)if(!e.isIntersecting)e.target.querySelectorAll('button[aria-pressed="true"]').forEach(b=>{if(lessonTimers.has(b.id))stopLesson(b.id)})});
document.querySelectorAll('.visual-lesson').forEach(e=>lessonObserver?.observe(e));
function curve(s,points,color,width=2,dash=''){el(s,'polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':width,'stroke-dasharray':dash})}
function dot(s,x,y,color,r=4){el(s,'circle',{cx:x,cy:y,r,fill:color})}
function box(s,x,y,w,h,label,lit){el(s,'rect',{x,y,width:w,height:h,rx:8,fill:lit?'#d8ede4':'#edf1f0',stroke:lit?'#087e8b':'#b6c7c3','stroke-width':2});txt(s,x+12,y+28,label)}
let sampleCount=1;
function drawSamples(){const s=$('samplePlot');s.replaceChildren();txt(s,30,28,'Visina talasa = amplituda');line(s,40,120,720,120);txt(s,610,193,'vrijeme →');const points=[];for(let i=0;i<=400;i++){let u=i/400;points.push([40+u*680,120-65*Math.sin(u*4*Math.PI)])}curve(s,points,'#afc7c8');const values=[];for(let i=0;i<sampleCount;i++){const v=Math.sin(i*Math.PI/8),x=40+i/32*680;line(s,x,120,x,120-65*v,'#087e8b',2);dot(s,x,120-65*v,'#087e8b');values.push(v.toFixed(2))}txt(s,30,232,'PCM niz: '+values.slice(-8).join('   '));txt(s,30,261,'Tačke su vrijednosti koje ostaju sačuvane. Linija između njih je ilustracija.');$('sampleReadout').textContent=`Sačuvano uzoraka: ${sampleCount}. Posljednja amplituda: ${values.at(-1)}. Niz se puni redom, po vremenu.`}
function nextSample(){if(sampleCount>=33){stopLesson('samplePlay');return}sampleCount++;drawSamples();if(sampleCount===33)stopLesson('samplePlay')}
$('sampleNext').addEventListener('click',nextSample);$('samplePlay').addEventListener('click',()=>{if(sampleCount===33)sampleCount=0;toggleLesson('samplePlay',nextSample,180)});$('sampleReset').addEventListener('click',()=>{stopLesson('samplePlay');sampleCount=1;drawSamples()});
function drawAlias(){const s=$('aliasPlot'),f=+$('aliasHz').value,fa=f>8000?16000-f:f;s.replaceChildren();txt(s,30,27,'Originalni ton: '+f+' Hz · uzorkovanje: 16000 Hz');line(s,40,130,720,130);const pts=[],other=[];for(let i=0;i<=1000;i++){let t=i/1000*.001;pts.push([40+t/.001*680,130-65*Math.cos(2*Math.PI*f*t)]);other.push([40+t/.001*680,130-65*Math.cos(2*Math.PI*fa*t)])}curve(s,pts,'#087e8b',2);if(f>8000)curve(s,other,'#bb5e17',3,'6 4');for(let i=0;i<=16;i++){let t=i/16000;dot(s,40+t/.001*680,130-65*Math.cos(2*Math.PI*f*t),'#183239',5)}txt(s,40,223,'0 ms');txt(s,674,223,'1 ms');txt(s,40,253,'● uzorci    plavo: original    narandžasto: preslikani ton');$('aliasReadout').textContent=f>8000?`${f/1000} kHz i ${fa/1000} kHz daju iste tačke u ovom primjeru. Izgubljenu razliku ne vraćamo kasnijom obradom.`:`${f/1000} kHz je ispod Nyquistove granice od 8 kHz. U ovom prikazu nema preslikavanja iznad granice.`}
$('aliasHz').addEventListener('change',drawAlias);
let tonePhase=0;
function drawSpectrum(){const s=$('spectrumPlot'),a=+$('toneAmp').value/100;s.replaceChildren();txt(s,25,28,'VRIJEME · suma dva tona');txt(s,428,28,'FREKVENCIJA · snaga po tonu');line(s,35,143,345,143);line(s,425,238,715,238);const points=[];for(let i=0;i<=600;i++){let t=i/600*.02;const value=Math.sin(2*Math.PI*100*t+tonePhase)+a*Math.sin(2*Math.PI*300*t+3*tonePhase);points.push([35+i/600*310,143-value*45])}curve(s,points,'#087e8b',2);for(const [x,p,label,col]of[[483,.5,'100 Hz','#087e8b'],[629,a*a/2,'300 Hz','#bb5e17']]){el(s,'rect',{x:x-18,y:238-p*340,width:36,height:p*340,fill:col});txt(s,x-24,263,label);txt(s,x-18,Math.max(50,228-p*340),p.toFixed(3))}txt(s,35,263,'0');txt(s,295,263,'20 ms');$('spectrumReadout').textContent=`100 Hz: amplituda 1 → snaga 0,500. 300 Hz: amplituda ${a.toFixed(2)} → snaga ${(a*a/2).toFixed(3)}. Dupla amplituda znači četiri puta veću snagu.`}
$('toneAmp').addEventListener('input',drawSpectrum);$('tonePlay').addEventListener('click',()=>toggleLesson('tonePlay',()=>{tonePhase+=.12;drawSpectrum()},100));
let welchCount=1;
function syntheticPower(segment,k){const baseline=.12+.7*Math.exp(-(((k-9)/2)**2))+.42*Math.exp(-(((k-25)/3)**2));return Math.max(.015,baseline+.1*Math.sin(k*1.7+segment*2.3)+.07*Math.cos(k*.9+segment*1.2))}
function drawWelch(){const s=$('welchPlot');s.replaceChildren();const current=[],average=[];for(let k=0;k<36;k++){let mean=0;for(let j=0;j<welchCount;j++)mean+=syntheticPower(j,k);mean/=welchCount;current.push([40+k*19,225-syntheticPower(welchCount-1,k)*175]);average.push([40+k*19,225-mean*175])}txt(s,30,28,'Sivo: posljednji segment · plavo: prosjek '+welchCount+' segmenta');line(s,40,225,715,225);curve(s,current,'#adb8b8',2);curve(s,average,'#087e8b',3);txt(s,40,259,'niže frekvencije');txt(s,585,259,'više frekvencije');$('welchReadout').textContent=`Dodato ${welchCount}/38 spektara. Za svaki frekvencijski bin sabiramo snage pa dijelimo brojem segmenata. Ne prosječimo PCM talase.`}
function nextWelch(){if(welchCount>=38){stopLesson('welchPlay');return}welchCount++;drawWelch();if(welchCount===38)stopLesson('welchPlay')}
$('welchNext').addEventListener('click',nextWelch);$('welchPlay').addEventListener('click',()=>{if(welchCount===38)welchCount=0;toggleLesson('welchPlay',nextWelch,220)});$('welchReset').addEventListener('click',()=>{stopLesson('welchPlay');welchCount=1;drawWelch()});
let shapeChanged=false;
function drawShape(){const s=$('shapePlot'),gain=+$('shapeGain').value/10,raw=[2,4,6+(shapeChanged?2:0),4].map(v=>v+gain),mean=raw.reduce((a,b)=>a+b)/4,out=raw.map(v=>v-mean);s.replaceChildren();txt(s,25,28,'PRIJE · log-vrijednosti traka');txt(s,422,28,'POSLIJE · oduzeta sredina');line(s,35,242,330,242);line(s,425,157,720,157);for(let i=0;i<4;i++){let x=60+i*68;el(s,'rect',{x,y:242-raw[i]*15,width:38,height:raw[i]*15,fill:i===2?'#bb5e17':'#087e8b'});txt(s,x,232-raw[i]*15,raw[i].toFixed(1));txt(s,x,273,'T'+(i+1));x+=390;el(s,'rect',{x,y:out[i]>=0?157-out[i]*22:157,width:38,height:Math.abs(out[i])*22,fill:i===2?'#bb5e17':'#087e8b'});txt(s,x, out[i]>=0?147-out[i]*22:177-out[i]*22,out[i].toFixed(1));txt(s,x,273,'T'+(i+1))}$('shapeReadout').textContent=`Sredina = ${mean.toFixed(1)}. Poslije centriranja: [${out.map(v=>v.toFixed(1)).join(', ')}]. ${shapeChanged?'Promjena treće trake ostaje vidljiva.':'Zajednički pomak ne mijenja desni prikaz.'}`}
$('shapeGain').addEventListener('input',drawShape);$('shapeChange').addEventListener('click',()=>{shapeChanged=!shapeChanged;$('shapeChange').setAttribute('aria-pressed',String(shapeChanged));$('shapeChange').textContent=shapeChanged?'Vrati treću traku':'Promijeni samo treću traku';drawShape()});
let parityStep=0;
const parityDescriptions=['1. Pločica snimi jedan PCM niz iz mikrofona. Taj niz je zajednički ulaz za poređenje.','2. Pločica iz tog PCM-a izračuna svojih 96 obilježja.','3. Prenese isti PCM i svoj rezultat na PC. Kontrolni zbir provjerava preneseni niz.','4. PC nad tim PCM-om ponovi račun sa istim postavkama.','5. Upoređujemo odgovarajuća obilježja i tražimo najveću apsolutnu razliku. Male float razlike nijesu isto što i bit-identičnost.'];
function drawParity(){const s=$('parityPlot');s.replaceChildren();box(s,25,90,160,55,'Isti PCM niz',true);line(s,185,118,245,60,'#086d78',2);line(s,185,118,245,181,'#086d78',2);box(s,245,32,200,58,'C na ESP32',parityStep>=1);box(s,245,153,200,58,'Python na PC-u',parityStep>=3);line(s,445,61,500,118,'#086d78',2);line(s,445,182,500,118,'#086d78',2);box(s,500,90,230,55,'Poređenje 96 brojeva',parityStep>=4);txt(s,260,118,'prenosi se isti snimak');if(parityStep>=4)txt(s,475,205,'npr. 0,123400 ↔ 0,123401');txt(s,30,259,'Korak '+(parityStep+1)+' od 5');$('parityReadout').textContent=parityDescriptions[parityStep];$('parityNext').disabled=parityStep===4}
$('parityNext').addEventListener('click',()=>{parityStep=Math.min(4,parityStep+1);drawParity()});$('parityReset').addEventListener('click',()=>{parityStep=0;drawParity()});
drawSamples();drawAlias();drawSpectrum();drawWelch();drawShape();drawParity();

function drawShrink(){const s=$('shrinkPlot'),a=+$('shrinkAmount').value/100,r=.95*(1-a);s.replaceChildren();line(s,190,150,570,150);line(s,380,30,380,270);for(const [rho,color,dash]of[[.95,'#a9baba','5 4'],[r,'#087e8b','']]){const p=[];for(let i=0;i<=120;i++){let t=i/120*2*Math.PI,u=Math.sqrt(1+rho)*Math.cos(t),v=Math.sqrt(1-rho)*Math.sin(t);p.push([380+95*(u+v)/Math.sqrt(2),150-95*(u-v)/Math.sqrt(2)])}curve(s,p,color,3,dash)}txt(s,30,28,'Isprekidano: početna procjena · plavo: poslije skupljanja');$('shrinkReadout').textContent=`α = ${a.toFixed(2)}. Veza van dijagonale: 0,95 → ${r.toFixed(2)}. Odnos najveće i najmanje sopstvene vrijednosti: ${((1+r)/(1-r)).toFixed(1)}. Manji odnos ovdje znači bolje uslovljenu matricu.`}
$('shrinkAmount').addEventListener('input',drawShrink);
function drawAE(){const s=$('aePlot'),mode=$('aeCase').value,x=mode==='normal'?[2,4,3,2]:[2,7,1,4],y=mode==='bad'?[2,4,3,2]:x.map((v,i)=>v+[.1,-.1,.1,-.1][i]);s.replaceChildren();box(s,25,20,195,48,'Ulaz: 4 broja',true);box(s,290,20,170,48,'Uski kod',true);box(s,525,20,210,48,'Rekonstrukcija',true);line(s,220,44,290,44,'#087e8b',2);line(s,460,44,525,44,'#087e8b',2);txt(s,30,105,'Plavo: original · narandžasto: rekonstrukcija');for(let i=0;i<4;i++){let p=125+i*155;el(s,'rect',{x:p,y:265-x[i]*18,width:32,height:x[i]*18,fill:'#087e8b'});el(s,'rect',{x:p+36,y:265-y[i]*18,width:32,height:y[i]*18,fill:'#bb5e17'});txt(s,p,289,'traka '+(i+1))}let mse=x.reduce((sum,v,i)=>sum+(v-y[i])**2,0)/4;$('aeReadout').textContent=`Srednja kvadratna greška = ${mse.toFixed(3)}. ${mode==='miss'?'Anomalija je dobro rekonstruisana: ovaj skor je može propustiti.':mode==='bad'?'Loša rekonstrukcija daje veći skor.':'Normalan ulaz je dobro rekonstruisan.'}`}
$('aeCase').addEventListener('change',drawAE);
const rocNormal=[12,22,35,45,58,68],rocAnomaly=[38,52,62,74,85,94];
function drawROC(){const s=$('rocPlot'),t=+$('rocThreshold').value;s.replaceChildren();txt(s,30,28,'STVARNE OZNAKE · redove znamo samo pri evaluaciji');txt(s,30,77,'normalno');txt(s,30,157,'anomalija');for(const [values,y,col]of[[rocNormal,105,'#087e8b'],[rocAnomaly,185,'#bb5e17']]){line(s,45,y,715,y);for(const v of values){dot(s,45+v*6.7,y,col,7);txt(s,37+v*6.7,y+27,String(v))}}line(s,45+t*6.7,55,45+t*6.7,230,'#183239',3);txt(s,35,265,'skor 0');txt(s,635,265,'skor 100');let fp=rocNormal.filter(v=>v>t).length,tp=rocAnomaly.filter(v=>v>t).length;$('rocReadout').textContent=`Prag ${t}: uhvaćeno ${tp}/6 anomalija (TPR ${(tp/6*100).toFixed(0)}%), pogrešno označeno ${fp}/6 normalnih (FPR ${(fp/6*100).toFixed(0)}%). Tačno na pragu ne proglašavamo anomaliju.`}
$('rocThreshold').addEventListener('input',drawROC);drawShrink();drawAE();drawROC();
'''
