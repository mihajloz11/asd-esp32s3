"""Stvarni FFT sintetičkog PCM-a za interaktivno objašnjenje, bez biblioteka."""

HTML = '''<div class="lab visual-lesson" id="fft-lanac">
<h3>PCM → prozor → FFT: prođi kroz jedan račun</h3>
<p><b>8192 je broj uzoraka koji zajedno ulaze u jedan FFT.</b> Nije frekvencija, broj sekundi ni broj traka modela. Ovdje računamo stvarni FFT izmišljenog zvuka sastavljenog od tonova 100 i 110 Hz.</p>
<div class="buttons"><button id="chainBack">Prethodni korak</button><button id="chainNext">Sljedeći korak</button><button id="chainPlay" aria-pressed="false">Pokreni animaciju</button><button id="chainReset">Počni ponovo</button></div>
<p id="chainReadout" class="lesson-readout" aria-live="polite"></p>
<svg id="chainPlot" viewBox="0 0 760 420" role="img" aria-label="Četiri koraka od PCM uzoraka do FFT spektra"></svg>
<p class="remember"><b>Dvije upotrebe riječi prozor:</b> vremenski prozor je izabranih 8192 uzorka; Hann prozor je lista 8192 težine kojima ih množimo. FFT zatim dobija tih 8192 umnožaka.</p>
<p class="caption">Primjer koristi 16 kHz i periodični Hann kao projekat. FFT radi u JavaScriptu sa decimalnim brojevima; ovo nije izvršavanje C firmvera niti novo mjerenje ventilatora. Brojevi PCM-a prikazani su kao normalizovani float.</p>
</div>
<div class="lab visual-lesson" id="fft-window">
<h3>Pojedinačno: snimak, Hann i njihov proizvod</h3>
<p>Sve tri slike imaju istu vremensku osu: cijelih 512 ms. Pomjeri uzorak od ruba do sredine i gledaj zašto ga Hann na različitim mjestima različito umanjuje.</p>
<label for="windowSample">Indeks uzorka n </label><input id="windowSample" type="range" min="0" max="8191" value="128">
<svg id="windowPlot" viewBox="0 0 760 540" role="img" aria-label="Sirovi PCM, Hann težine i prozorisani PCM na istoj vremenskoj osi"></svg>
<p id="windowReadout" class="lesson-readout" aria-live="polite"></p>
<p class="remember"><b>Ulaz u FFT je treća slika.</b> Hann nije novi snimljeni zvuk, nego unaprijed izračunata lista težina. U sredini težina iznosi 1, pa tamo uzorak ostaje isti.</p>
<p class="caption">Linije su radi preglednosti nacrtane pomoću 801 tačke. Račun koristi svih 8192 uzorka. Označena tačka i ispis koriste tačan izabrani uzorak, ne samo tačke crteža.</p>
</div>
<div class="lab visual-lesson" id="fft-bin">
<h3>Zumiraj jedan bin: šta tačno stoji u njemu?</h3>
<p>Pomjeraj bin oko dvije komponente. <b>Bin je jedno mjesto u FFT rezultatu</b>, označeno indeksom <code>k</code>. Uz njega je vezana frekvencija <code>k × 16000 / 8192</code>. Narandžasti stub je izabrani bin.</p>
<label for="binPick">Indeks bina k </label><input id="binPick" type="range" min="40" max="70" value="51">
<svg id="binPlot" viewBox="0 0 760 285" role="img" aria-label="Pojedinačni FFT binovi oko 100 i 110 herca"></svg>
<p id="binReadout" class="lesson-readout" aria-live="polite"></p>
<p class="remember"><b>Zapamti:</b> jedan ulazni PCM broj pripada jednom trenutku. Jedan izlazni FFT bin opisuje jednu frekvencijsku tačku koristeći <b>svih 8192 ulazna uzorka</b>. Nema pravila „prvi uzorak postaje prvi bin”.</p>
<p>Za bin k algoritam sabira doprinose cijelog segmenta, poredeći ih sa sinusom i kosinusom te frekvencije. Ako signal sadrži sličnu komponentu, doprinosi se manje poništavaju i bin ima veću amplitudu. FFT je brz način da se taj račun uradi za sve binove.</p>
<p class="caption">Prikazujemo skaliranu snagu (Re² + Im²), kao za jedan Hann segment u našem spektru snage. Bin nije savršen pravougaoni filter: ton može doprinijeti i susjednim binovima. Sa realnim ulazom od 8192 uzorka imamo 4097 nenegativnih binova, k=0…4096, do 8000 Hz.</p>
</div>
<div class="lab visual-lesson" id="fft-poredjenje">
<h3>Zašto 8192: ista dva tona, duže posmatranje</h3>
<p>Oba računa koriste isti sintetički zvuk, 16 kHz i Hann. Mijenja se samo broj stvarnih uzoraka. Izaberi jedan ton, pa dva bliska tona.</p>
<label for="compareTone">Zvuk </label><select id="compareTone"><option value="two" selected>100 Hz + 110 Hz</option><option value="one">Samo 100 Hz</option></select>
<svg id="comparePlot" viewBox="0 0 760 460" role="img" aria-label="Poređenje spektra za FFT 1024 i FFT 8192"></svg>
<p class="remember"><b>1024:</b> 64 ms zvuka, binovi na 15,625 Hz. <b>8192:</b> 512 ms zvuka, binovi na 1,953 Hz. Duži snimak pomaže razlikovanju bliskih tonova, ali opis obuhvata duži dio vremena.</p>
<p><b>Veza sa našim izborom:</b> ventilator ima ponavljajuće tonske komponente. Finiji spektralni opis pomogao je ispitivanom PSD pristupu, a račun je stao na ESP32. Broj 8192 je i stepen dvojke, pogodan za naš FFT. Ovo poređenje objašnjava kompromis; ne dokazuje da je 8192 najbolji za svaki zvuk, niti da je samo N donio sav razvojni dobitak.</p>
<p class="caption">Oba grafa imaju istu skalu frekvencije i snage. Isprekidane oznake su stvarne frekvencije sintetisanih tonova. Hann širi vrhove, pa razmak binova nije isto što i garantovana razlučivost. Trake vremena ispod pokazuju dužine posmatranja, ne izmjereno kašnjenje alarma.</p>
</div>'''

JS = r'''
function lessonFFT(n,two=true){
 const re=new Float64Array(n),im=new Float64Array(n),raw=new Float64Array(n),win=new Float64Array(n);
 for(let i=0;i<n;i++){raw[i]=.5*Math.sin(2*Math.PI*100*i/16000)+(two?.5*Math.sin(2*Math.PI*110*i/16000):0);win[i]=.5-.5*Math.cos(2*Math.PI*i/n);re[i]=raw[i]*win[i]}
 for(let i=1,j=0;i<n;i++){let b=n>>1;for(;j&b;b>>=1)j^=b;j^=b;if(i<j){[re[i],re[j]]=[re[j],re[i]]}}
 for(let size=2;size<=n;size*=2){const angle=-2*Math.PI/size;for(let start=0;start<n;start+=size)for(let j=0;j<size/2;j++){let wr=Math.cos(angle*j),wi=Math.sin(angle*j),a=start+j,b=a+size/2,tr=re[b]*wr-im[b]*wi,ti=re[b]*wi+im[b]*wr;re[b]=re[a]-tr;im[b]=im[a]-ti;re[a]+=tr;im[a]+=ti}}
 const power=new Float64Array(n/2+1);for(let k=0;k<power.length;k++)power[k]=(re[k]**2+im[k]**2)*(k===0||k===n/2?1:2)/((n/2)**2);
 return {n,raw,win,re,im,power};
}
const fftExample=lessonFFT(8192);
let chainStep=0;
const chainText=[
 '1 / 4 · PCM: niz amplituda po vremenu. Ispod je uvećano prvih 160 uzoraka (10 ms). To je samo mali dio ulaza, ne cijelih 8192.',
 '2 / 4 · Izdvoji 8192 uzorka, od indeksa 0 do 8191. Oni pokrivaju 512 ms pri 16000 uzoraka/s. Svaki uzorak čeka svoje mjesto u FFT ulazu.',
 '3 / 4 · Primijeni Hann: x[n] × w[n]. Rubovi se utišavaju, sredina zadržava punu težinu. To smanjuje problem naglog spoja kraja i početka segmenta.',
 '4 / 4 · FFT mijenja opis: sa amplituda kroz vrijeme prelazimo na kompleksne vrijednosti po frekvenciji. Iz njih računamo snagu i crtamo binove. Ovdje vidiš samo opseg 60–150 Hz.'
];
function spectrumBins(s,data,x,y,w,h,selected=-1,min=60,max=150){
 line(s,x,y+h,x+w,y+h);for(let f=min;f<=max;f+=30){let px=x+(f-min)/(max-min)*w;line(s,px,y,px,y+h,'#e0e9e6');txt(s,px-10,y+h+23,f+' Hz')}
 txt(s,x,y-12,'snaga (ista skala)');
 for(let k=Math.ceil(min*data.n/16000);k<=Math.floor(max*data.n/16000);k++){let px=x+(k*16000/data.n-min)/(max-min)*w,py=y+h-data.power[k]/.25*h;line(s,px,y+h,px,py,k===selected?'#bb5e17':'#087e8b',k===selected?5:2);dot(s,px,py,k===selected?'#bb5e17':'#087e8b',k===selected?6:3)}
}
function drawChain(){const s=$('chainPlot');s.replaceChildren();for(let i=0;i<4;i++)box(s,15+i*187,12,174,44,['1. PCM','2. 8192 uzorka','3. Hann','4. FFT binovi'][i],i===chainStep);
 if(chainStep===0){line(s,35,195,725,195);const p=[];for(let i=0;i<160;i++){let x=35+i/159*690,y=195-fftExample.raw[i]*95;p.push([x,y]);if(i%4===0){line(s,x,195,x,y,'#afc7c8');dot(s,x,y,'#087e8b',3)}}curve(s,p,'#087e8b');txt(s,35,90,'Uvećano: prvih 10 ms · radi preglednosti označena svaka četvrta tačka');txt(s,35,325,'PCM: '+Array.from(fftExample.raw.slice(0,7),v=>v.toFixed(3)).join('  ')+' …');txt(s,35,365,'Vodoravno: vrijeme. Uspravno: amplituda, ne frekvencija.')}
 if(chainStep===1){txt(s,35,105,'Jedan vremenski segment = tačno 8192 stvarna uzorka');box(s,35,133,690,65,'[ x[0], x[1], x[2], …, x[8190], x[8191] ]',true);line(s,35,255,725,255,'#087e8b',5);txt(s,35,285,'0 ms');txt(s,640,285,'512 ms');txt(s,35,330,'8192 / 16000 = 0,512 s. Posljednji uzorak je na 511,9375 ms.');txt(s,35,365,'Hop od 4096 uzoraka pomjera sljedeći segment za 256 ms.')}
 if(chainStep===2){txt(s,35,91,'Hann težina kroz cijeli segment: 0 → 1 → skoro 0');const p=[];for(let i=0;i<=256;i++)p.push([35+i/256*690,230-(.5-.5*Math.cos(2*Math.PI*i/256))*110]);curve(s,p,'#bb5e17',3);line(s,35,230,725,230);txt(s,35,256,'početak');txt(s,330,256,'sredina');txt(s,670,256,'kraj');const n=128;txt(s,35,305,`Primjer n=${n}: PCM ${fftExample.raw[n].toFixed(4)} × težina ${fftExample.win[n].toFixed(4)}`);txt(s,35,337,`→ FFT ulaz ${(fftExample.raw[n]*fftExample.win[n]).toFixed(6)}. Isti postupak ponovimo za svih 8192.`);txt(s,35,375,'Ne brišemo rubne uzorke — množimo ih manjim brojem.')}
 if(chainStep===3){spectrumBins(s,fftExample,45,115,660,185);txt(s,35,363,'Svaki stub: jedan bin. Dvije grupe vrhova odgovaraju tonovima 100 i 110 Hz.');txt(s,35,393,'Ovo je jedan segment; Welch kasnije prosječi snage više segmenata.')}
 $('chainReadout').textContent=chainText[chainStep];$('chainBack').disabled=chainStep===0;$('chainNext').disabled=chainStep===3;
}
function nextChain(){chainStep=Math.min(3,chainStep+1);drawChain();if(chainStep===3)stopLesson('chainPlay')}
$('chainNext').addEventListener('click',nextChain);$('chainBack').addEventListener('click',()=>{stopLesson('chainPlay');chainStep=Math.max(0,chainStep-1);drawChain()});$('chainReset').addEventListener('click',()=>{stopLesson('chainPlay');chainStep=0;drawChain()});$('chainPlay').addEventListener('click',()=>{if(chainStep===3){chainStep=0;drawChain()}toggleLesson('chainPlay',nextChain,2600)});
function drawOneBin(){const s=$('binPlot'),k=+$('binPick').value;s.replaceChildren();spectrumBins(s,fftExample,45,55,660,175,k,75,150);$('binReadout').textContent=`Bin k=${k}: frekvencija ${(k*16000/8192).toFixed(3)} Hz. Re=${fftExample.re[k].toFixed(2)}, Im=${fftExample.im[k].toFixed(2)}. Skalirana snaga=${fftExample.power[k].toFixed(6)}. Susjedni bin je udaljen 1,953125 Hz.`}
$('binPick').addEventListener('input',drawOneBin);
function drawWindowParts(){const s=$('windowPlot'),n=+$('windowSample').value;s.replaceChildren();const defs=[[105,'1. PCM x[n] · snimljene amplitude','#087e8b',i=>fftExample.raw[i]],[265,'2. Hann w[n] · težine od 0 do 1','#bb5e17',i=>fftExample.win[i]],[425,'3. x[n] × w[n] · ovo šaljemo FFT-u','#087e8b',i=>fftExample.raw[i]*fftExample.win[i]]];for(const [cy,label,col,value]of defs){txt(s,35,cy-67,label);line(s,40,cy,720,cy);const points=[];for(let j=0;j<=800;j++){const i=Math.round(j/800*8191);points.push([40+i/8192*680,cy-value(i)*51])}curve(s,points,col,1.6);const px=40+n/8192*680;line(s,px,cy-55,px,cy+55,'#697e83');dot(s,px,cy-value(n)*51,'#af3c27',5);txt(s,40,cy+75,'0 ms');txt(s,345,cy+75,'256 ms');txt(s,655,cy+75,'512 ms')}$('windowReadout').textContent=`n=${n}, vrijeme ${(n/16).toFixed(3)} ms: PCM ${fftExample.raw[n].toFixed(5)} × Hann ${fftExample.win[n].toFixed(5)} = ${(fftExample.raw[n]*fftExample.win[n]).toFixed(6)}.`}
$('windowSample').addEventListener('input',drawWindowParts);drawWindowParts();
function drawFFTComparison(){const s=$('comparePlot'),two=$('compareTone').value==='two';s.replaceChildren();for(const [n,y]of[[1024,50],[8192,232]]){const d=lessonFFT(n,two);txt(s,35,y-25,`N=${n} · ${n/16} ms · razmak ${(16000/n).toFixed(3)} Hz`);spectrumBins(s,d,45,y+12,660,102);for(const f of two?[100,110]:[100]){const x=45+(f-60)/90*660;const l=line(s,x,y+8,x,y+114,'#bb5e17');l.setAttribute('stroke-dasharray','4 5')}}
 txt(s,35,396,'Trajanje na istoj vremenskoj skali:');el(s,'rect',{x:310,y:380,width:48,height:13,fill:'#bb5e17'});txt(s,365,392,'64 ms');el(s,'rect',{x:310,y:417,width:384,height:13,fill:'#087e8b'});txt(s,590,451,'512 ms');}
$('compareTone').addEventListener('change',drawFFTComparison);drawChain();drawOneBin();drawFFTComparison();
'''
