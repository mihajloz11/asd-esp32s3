"""Tekst master rada.

Pise se na latinici; `build_rad.py` preslovljava u cirilicu jer to trazi
uputstvo v8. Oznake u tekstu:

    *strani termin*   kurziv, ostaje latinica (uputstvo, str. 4)
    `kod`             Courier New, ostaje latinica
    **naglaseno**     bold, preslovljava se

Sve brojke imaju izvor u repou; ni jedna nije prepisana napamet. Gdje izvor
jos ne postoji stoji [TODO]; prebrojati ih sa
`grep -c "\[TODO\]" rad_tekst.py` (check_todo.py postoji samo za TELFOR).
"""
from __future__ import annotations

NASLOV_SR = ("Nenadgledana detekcija anomalija zvuka masina na mikrokontroleru "
             "ESP32-S3 sa samokalibracijom na licu mjesta")
NASLOV_SR_PRAVI = ("Nenadgledana detekcija anomalija zvuka mašina na mikrokontroleru "
                   "ESP32-S3 sa samokalibracijom na licu mjesta")
NASLOV_EN = ("Unsupervised Anomalous Sound Detection for Machine Condition "
             "Monitoring on an ESP32-S3 Microcontroller with On-Site "
             "Self-Calibration")

AUTOR = "Mihajlo Živković"
INDEKS = "E1 80/2024"          # potvrdio autor, 01.09.2026.
MENTOR = "prof. dr Ivan Mezei, red. prof."
GODINA = "2026"


def napisi(r) -> None:
    _korice(r)
    _naslovna(r)
    _kdi(r)
    _kwd(r)
    _zadatak(r)
    _izjava(r)
    _sadrzaj(r)
    _skracenice(r)
    _liste(r)
    r.pocni_tijelo()
    _uvod(r)
    _teorija(r)
    _koncept(r)
    _model(r)
    _realizacija(r)
    _protokol(r)
    _rezultati(r)
    _diskusija(r)
    _zakljucak(r)
    _literatura(r)
    _biografija(r)
    _prilozi(r)


# ==========================================================================
# prednji dio
# ==========================================================================
def _korice(r) -> None:
    r.prazan(3)
    r.naslovni_blok([
        ("Univerzitet u Novom Sadu", 14, True),
        ("Fakultet tehničkih nauka u Novom Sadu", 14, True),
        ("", 11, False),
        ("Odsek za energetiku, elektroniku i telekomunikacije", 12, False),
        ("Studijski program: Energetika, elektronika i telekomunikacije", 11, False),
        ("Modul: Embedded sistemi i algoritmi", 11, False),
    ])
    r.prazan(5)
    r.naslovni_blok([(AUTOR, 14, False)])
    r.prazan(3)
    r.naslovni_blok([(NASLOV_SR_PRAVI, 16, True)], velika=True)
    r.prazan(2)
    r.naslovni_blok([("Master rad", 14, True)], velika=True)
    r.prazan(8)
    r.naslovni_blok([(f"Novi Sad, {GODINA}.", 12, False)])


def _naslovna(r) -> None:
    r.nova_strana()
    r.prazan(2)
    r.naslovni_blok([
        ("Univerzitet u Novom Sadu", 13, True),
        ("Fakultet tehničkih nauka", 13, True),
        ("Novi Sad", 13, True),
        ("", 11, False),
        ("Odsek/smjer/usmjerenje: Energetika, elektronika i telekomunikacije / "
         "Embedded sistemi i algoritmi", 11, False),
    ])
    r.prazan(4)
    r.naslovni_blok([("Master rad", 16, True)], velika=True)
    r.prazan(3)
    r.naslovni_blok([
        (f"Kandidat: {AUTOR}", 12, False),
        (f"Broj indeksa: {INDEKS}", 12, False),
        ("", 11, False),
        (f"Tema rada: {NASLOV_SR_PRAVI}", 12, False),
        ("", 11, False),
        (f"Mentor rada: {MENTOR}", 12, False),
    ])
    r.prazan(6)
    r.naslovni_blok([
        ("Mjesto i datum:", 11, False),
        (f"Novi Sad, {GODINA}.", 11, False),
    ])


def _kdi(r) -> None:
    r.nova_strana()
    r.naslovni_blok([("Ključna dokumentacijska informacija", 13, True)],
                     velika=True)
    r.prazan()
    r.kdi_tabela([
        ("Redni broj, RBR:", ""),
        ("Identifikacioni broj, IBR:", ""),
        ("Tip dokumentacije, TD:", "Monografska dokumentacija"),
        ("Tip zapisa, TZ:", "Tekstualni štampani materijal"),
        ("Vrsta rada, VR:", "Master rad"),
        ("Autor, AU:", AUTOR),
        ("Mentor, MN:", MENTOR),
        ("Naslov rada, NR:", NASLOV_SR_PRAVI),
        ("Jezik publikacije, JP:", "srpski"),
        ("Jezik izvoda, JI:", "srpski / engleski"),
        ("Zemlja publikovanja, ZP:", "Republika Srbija"),
        ("Uže geografsko područje, UGP:", "Vojvodina"),
        ("Godina, GO:", GODINA),
        ("Izdavač, IZ:", "Autorski reprint"),
        ("Mjesto i adresa, MA:",
         "Novi Sad, Fakultet tehničkih nauka, Trg Dositeja Obradovića 6"),
        ("Fizički opis rada, FO:",
         "9 poglavlja / 47 strana / 12 citata / 20 tabela / 6 slika / "
         "0 grafika / 3 priloga"),
        ("Naučna oblast, NO:", "Elektrotehnika i računarstvo"),
        ("Naučna disciplina, ND:", "Elektronika i ugrađeni sistemi"),
        ("Predmetna odrednica / ključne riječi, PO:",
         "detekcija anomalija zvuka; nenadgledano učenje; ugrađeni sistemi; "
         "ESP32-S3; Mahalanobisova udaljenost; spektralna gustina snage; "
         "prediktivno održavanje"),
        ("UDK", ""),
        ("Čuva se, ČU:",
         "U biblioteci Fakulteta tehničkih nauka, Novi Sad"),
        ("Važna napomena, VN:", ""),
        ("Izvod, IZ:", _izvod_sr()),
        ("Datum prihvatanja teme, DP:", ""),
        ("Datum odbrane, DO:", ""),
        ("Članovi komisije, KO:", "Predsjednik: [TODO]"),
        ("", "Član: [TODO]"),
        ("", f"Član, mentor: {MENTOR}"),
        ("Potpis mentora", ""),
    ])


def _izvod_sr() -> str:
    return (
        "U radu je realizovan samostalan uređaj za nenadgledanu detekciju "
        "anomalija zvuka rotacionih mašina, zasnovan na mikrokontroleru "
        "ESP32-S3 i jednom MEMS mikrofonu. Opšti oblik varijacije normalnog "
        "rada uči se unaprijed na računaru iz 990 ispravnih snimaka iz skupa "
        "DCASE 2026 Task 2, a uređaj se pri postavljanju sam kalibriše na "
        "ventilatoru koji nikada nije čuo i sam izvodi prag odluke iz "
        "perioda u kojem su prisutna samo normalna stanja. Obilježje je "
        "spektar snage visoke rezolucije sažet u 96 logaritamskih traka, a "
        "mjera odstupanja je Mahalanobisova udaljenost od lokalno naučenog "
        "centra. Na referentnom skupu za ventilator postignut je AUC 0,867. "
        "Na stvarnom ventilatoru potvrđeno je da uređaj samostalno nauči "
        "normalno stanje, odbije nepouzdan prozor umjesto da ga tumači i "
        "pouzdano prijavi konstantnu akustičku promjenu, uz obradu od 716 ms "
        "po prozoru od 10 s i bez ijednog izgubljenog uzorka."
    )


def _izvod_en() -> str:
    return (
        "This thesis presents a self-contained device for unsupervised "
        "anomalous sound detection of rotating machinery, built around an "
        "ESP32-S3 microcontroller and a single MEMS microphone. The general "
        "shape of normal-operation variation is learned offline on a "
        "workstation from 990 healthy recordings of the DCASE 2026 Task 2 "
        "dataset, while the device calibrates itself on a previously unheard "
        "fan and derives its own decision threshold from a normal-only "
        "period. The feature is a high-resolution power spectral density "
        "summarised into 96 logarithmic bands, and the deviation measure is "
        "the Mahalanobis distance from a locally learned centre. An AUC of "
        "0.867 is achieved on the fan benchmark. On a physical fan the device "
        "is shown to learn the normal state autonomously, to reject an "
        "unreliable window instead of interpreting it, and to reliably report "
        "a constant acoustic change, with 716 ms of computation per 10 s "
        "window and no dropped samples."
    )


def _kwd(r) -> None:
    r.nova_strana()
    with r.latinicno():
        r.naslovni_blok([("KEY WORDS DOCUMENTATION", 13, True)])
        r.prazan()
        r.kdi_tabela([
            ("Accession number, ANO:", ""),
            ("Identification number, INO:", ""),
            ("Document type, DT:", "Monographic publication"),
            ("Type of record, TR:", "Textual printed material"),
            ("Contents code, CC:", "Master thesis"),
            ("Author, AU:", "Mihajlo Zivkovic"),
            ("Mentor, MN:", "Ivan Mezei, PhD, full prof."),
            ("Title, TI:", NASLOV_EN),
            ("Language of text, LT:", "Serbian"),
            ("Language of abstract, LA:", "Serbian / English"),
            ("Country of publication, CP:", "Republic of Serbia"),
            ("Locality of publication, LP:", "Vojvodina"),
            ("Publication year, PY:", GODINA),
            ("Publisher, PB:", "Author's reprint"),
            ("Publication place, PP:",
             "Novi Sad, Faculty of Technical Sciences, Trg Dositeja Obradovica 6"),
            ("Physical description, PD:",
             "9 chapters / 47 pages / 12 references / 20 tables / "
             "6 figures / 0 graphs / 3 appendices"),
            ("Scientific field, SF:", "Electrical and computer engineering"),
            ("Scientific discipline, SD:", "Electronics and embedded systems"),
            ("Subject / Keywords, S/KW:",
             "anomalous sound detection; unsupervised learning; embedded systems; "
             "ESP32-S3; Mahalanobis distance; power spectral density; predictive "
             "maintenance"),
            ("UDC", ""),
            ("Holding data, HD:",
             "Library of the Faculty of Technical Sciences, Novi Sad"),
            ("Note, N:", ""),
            ("Abstract, AB:", _izvod_en()),
            ("Accepted by sci. board on, ASB:", ""),
            ("Defended on, DE:", ""),
            ("Defense board, DB:", "President: [TODO]"),
            ("", "Member: [TODO]"),
            ("", "Member, mentor: Ivan Mezei, PhD, full prof."),
            ("Mentor's signature", ""),
        ])


def _zadatak(r) -> None:
    r.nova_strana()
    r.naslovni_blok([("Zadatak master rada", 14, True)], velika=True)
    r.prazan(2)
    r.pasus(
        "Proučiti postojeće pristupe nenadgledanoj detekciji anomalija zvuka "
        "mašina i njihova ograničenja pri prenosu na resursno ograničene "
        "platforme. Projektovati i realizovati samostalan uređaj zasnovan na "
        "mikrokontroleru ESP32-S3 i jednom MEMS mikrofonu, koji opšti model "
        "normalnog rada preuzima sa računara, a pri postavljanju se sam "
        "kalibriše na konkretnoj mašini i sam izvodi prag odluke iz perioda u "
        "kojem su prisutna samo normalna stanja.",
        uvlaka=False)
    r.pasus(
        "Realizovati kompletan tok obrade na uređaju: prihvat zvuka preko "
        "sabirnice I2S, izračunavanje spektralnog obilježja, ocjenu odstupanja "
        "i vremensko pravilo odlučivanja, uz provjere ispravnosti signala koje "
        "u slučaju nedostatka dokaza zaustavljaju tok umjesto da nastave. "
        "Sprovesti mjerenja na referentnom skupu podataka i na stvarnom "
        "ventilatoru, po unaprijed zaključanom protokolu, i prijaviti "
        "izmjerene vrijednosti zajedno sa granicama tvrdnji koje one "
        "podržavaju.", uvlaka=False)
    r.prazan(6)
    r.naslovni_blok([("Mentor:", 11, False), ("", 11, False),
                     ("_______________________________", 11, False),
                     (MENTOR, 11, False)], centar=False)


def _izjava(r) -> None:
    r.nova_strana()
    r.naslovni_blok([("Izjava o akademskoj čestitosti", 14, True)])
    r.prazan()
    r.pasus("Student: _____________________________________", uvlaka=False)
    r.pasus("Broj indeksa: _________________________________", uvlaka=False)
    r.pasus("Student/kinja osnovnih ili master akademskih studija", uvlaka=False)
    r.pasus("Autor rada pod nazivom:", uvlaka=False)
    r.pasus("__________________________________________________________________",
            uvlaka=False)
    r.pasus("__________________________________________________________________",
            uvlaka=False)
    r.prazan()
    r.pasus("Potpisivanjem izjavljujem:", uvlaka=False)
    r.stavke([
        "da je rad isključivo rezultat mog sopstvenog istraživačkog rada;",
        "da nisam koristio alate vještačke inteligencije za generisanje i/ili "
        "kreiranje dijelova rada;",
        "da sam rad i mišljenja drugih autora koje sam koristio u ovom radu "
        "naznačio ili citirao i navedeni su u spisku literature/referenci koji "
        "su sastavni dio ovog rada;",
        "da sam dobio sve dozvole za korišćenje autorskog djela koji se u "
        "cjelosti unose u predati rad i da sam to jasno naveo;",
        "da sam svjestan da je plagijat korišćenje tuđih radova u bilo kom "
        "obliku (kao citata, parafraza, slika, tabela, dijagrama, dizajna, "
        "planova, fotografija, filma, muzike, formula, veb sajtova, "
        "kompjuterskih programa i sl.) bez navođenja autora ili predstavljanje "
        "tuđih autorskih djela kao mojih, kažnjivo po zakonu (Zakon o "
        "autorskom i srodnim pravima, Službeni glasnik Republike Srbije, br. "
        "104/2009, 99/2011, 119/2012), kao i drugih zakona i odgovarajućih "
        "akata Univerziteta u Novom Sadu;",
        "da sam svjestan da plagijat uključuje i predstavljanje, upotrebu i "
        "distribuiranje rada predavača ili drugih studenata kao sopstvenih;",
        "da sam svjestan posljedica koje kod dokazanog plagijata mogu "
        "prouzrokovati na predati rad i moj status;",
        "da je elektronska verzija rada identična štampanom primjerku i "
        "pristajem na njegovo objavljivanje pod uslovima propisanim aktima "
        "Univerziteta.",
    ])
    r.prazan(2)
    r.pasus("U Novom Sadu, ______________          "
            "Potpis studenta/studentkinje", uvlaka=False)
    r.pasus("                                      "
            "________________________", uvlaka=False)


def _sadrzaj(r) -> None:
    r.nova_strana()
    r.naslovni_blok([("Sadržaj", 14, True)], velika=True)
    r.prazan()
    r.sadrzaj_polje()


def _skracenice(r) -> None:
    r.nova_strana()
    r.naslovni_blok([("Lista skraćenica", 14, True)], velika=True)
    r.prazan()
    r.kdi_tabela([
        ("ASD", "*Anomalous Sound Detection* — detekcija anomalija zvuka"),
        ("AUC", "*Area Under the ROC Curve* — površina ispod ROC krive"),
        ("pAUC", "*partial AUC* — parcijalna površina ispod ROC krive"),
        ("CAL", "faza kalibracije u toku rada uređaja"),
        ("DCASE", "*Detection and Classification of Acoustic Scenes and Events*"),
        ("DET", "faza detekcije u toku rada uređaja"),
        ("DMA", "*Direct Memory Access*"),
        ("FFT", "*Fast Fourier Transform* — brza Furijeova transformacija"),
        ("I2S", "*Inter-IC Sound* — serijska sabirnica za digitalni zvuk"),
        ("I2C", "*Inter-Integrated Circuit* — serijska sabirnica"),
        ("LOO", "*leave-one-out* — izostavljanje po jednog uzorka"),
        ("MAD", "*Median Absolute Deviation* — medijana apsolutnog odstupanja"),
        ("MEMS", "*Micro-Electro-Mechanical Systems*"),
        ("NVS", "*Non-Volatile Storage* — trajna memorija u ESP-IDF okruženju"),
        ("PSD", "*Power Spectral Density* — spektralna gustina snage"),
        ("PSRAM", "*Pseudo-Static RAM*"),
        ("RMS", "*Root Mean Square* — efektivna vrijednost"),
        ("SRAM", "*Static RAM*"),
        ("UART", "*Universal Asynchronous Receiver-Transmitter*"),
        ("dBFS", "*decibels relative to full scale* — decibeli u odnosu na "
                 "punu skalu"),
    ])


def _liste(r) -> None:
    """Spisak slika i spisak tabela, odvojeno, kako trazi struktura iz
    uputstva ("Lista slika, grafika" i "Lista tabela") i kako je u zvanicnom
    FTN MSc sablonu. Polja puni Word pri pokretanju `render_check.py`."""
    r.nova_strana()
    r.naslovni_blok([("Lista slika", 14, True)], velika=True)
    r.prazan()
    r.spisak_polje(r.STIL_SLIKE)

    r.nova_strana()
    r.naslovni_blok([("Lista tabela", 14, True)], velika=True)
    r.prazan()
    r.spisak_polje(r.STIL_TABELE)


# ==========================================================================
# 1. UVOD
# ==========================================================================
def _uvod(r) -> None:
    r.naslov("Uvod")
    r.pasus(
        "Mašine sa rotacionim dijelovima mijenjaju svoj zvučni potpis prije "
        "nego što otkažu. Ležaj koji se troši, lopatica koja se iskrivi, "
        "filter koji se zapuši ili disbalans na osovini mijenjaju raspodjelu "
        "energije po frekvencijama mnogo prije nego što promjena postane "
        "vidljiva na proizvodu ili čujna čovjeku. Zbog toga je akustički "
        "nadzor privlačan oblik prediktivnog održavanja: senzor se ne montira "
        "na mašinu, ne traži zaustavljanje pogona i ne mijenja njenu "
        "konstrukciju.")
    r.pasus(
        "Istraživačka zajednica ovaj problem obrađuje pod nazivom detekcija "
        "anomalija zvuka mašina, a od 2020. godine postoji i standardizovan "
        "zadatak u okviru takmičenja DCASE [1]. Postavka je namjerno teška i "
        "realistična: za obuku su dostupni samo snimci ispravnog rada, "
        "anomalije se ne vide unaprijed, a ocjena se radi na drugom fizičkom "
        "primjerku iste vrste mašine. Taj pomak domena čini da rješenja koja "
        "dobro rade na jednoj mašini često podbace na drugoj.")
    r.pasus(
        "Praktično sva objavljena rješenja tog zadatka izvode se na "
        "grafičkim procesorima ili serverskoj klasi hardvera, često sa "
        "ansamblima dubokih modela. Industrijska primjena traži suprotno: "
        "jeftin i samostalan senzorski čvor koji radi bez mreže, bez oblaka i "
        "bez računara pored sebe. Između te dvije slike stoji jaz koji nije "
        "samo pitanje broja operacija po sekundi. Uređaj koji sam donosi "
        "odluku mora sam i da postavi prag odluke, mora da prepozna kada "
        "njegovo mjerenje nije pouzdano, i ne smije da nastavi da uči dok "
        "mašina nije u potvrđeno ispravnom stanju.")

    r.naslov("Predmet rada", 2)
    r.pasus(
        "Predmet ovog rada je projektovanje, realizacija i vrednovanje "
        "samostalnog uređaja za nenadgledanu detekciju anomalija zvuka "
        "rotacionih mašina, zasnovanog na mikrokontroleru ESP32-S3 i jednom "
        "MEMS mikrofonu. Podjela posla je sljedeća. Opšti oblik varijacije "
        "normalnog rada uči se unaprijed na računaru, iz velikog korpusa "
        "snimaka ispravnih mašina; taj naučeni opis se ugrađuje u firmver kao "
        "nepromjenjiva tabela. Sve što je specifično za konkretnu mašinu — "
        "njen centar, njen prag i njena granica pouzdanosti — uređaj mjeri sam, "
        "na licu mjesta, u prvim minutima rada pored te mašine.")
    r.pasus(
        "Za obuku opšteg modela ne koriste se anomalni snimci. Za izvođenje "
        "praga ne koriste se ciljne anomalije. To nije stilska odluka nego "
        "uslov bez kojeg bi izmjerene vrijednosti bile optimistične na način "
        "koji se u stvarnoj primjeni ne može ponoviti.")

    r.naslov("Motivacija za izbor teme", 2)
    r.pasus(
        "Tema je izabrana zbog spoja dvije oblasti koje se rijetko sreću u "
        "istom radu: obrade signala i statističkog učenja s jedne strane, i "
        "ugrađenih sistema sa strogim ograničenjima memorije i vremena s "
        "druge. Zanimalo me je koliko od jednog istraživačkog rezultata "
        "zaista preživi kada se prenese na mikrokontroler i pusti da radi bez "
        "nadzora — i šta se tačno pokvari na tom putu.")
    r.pasus(
        "Odgovor na to pitanje ispao je zanimljiviji od očekivanog. Ono što "
        "se pokvarilo nije bila tačnost modela nego politika odlučivanja oko "
        "njega. Zbog toga je značajan dio ovog rada posvećen upravo tome: "
        "kako se prag izvodi, kako se prepoznaje da mjerenje nije pouzdano i "
        "šta uređaj radi kada dokaza nema.")

    r.naslov("Cilj i doprinosi rada", 2)
    r.pasus(
        "Postavljeni istraživački cilj bio je AUC od najmanje 0,80 na "
        "ventilatoru koji nije korišćen za obuku, uz protokol mjerenja bez "
        "curenja podataka. Pored toga, rad daje sljedeće doprinose:")
    r.stavke([
        "**Kompletan lanac na mikrokontroleru.** Obilježje, ocjena "
        "odstupanja, kalibracija, izvođenje praga i vremensko pravilo "
        "odlučivanja izvršavaju se na uređaju, bez računara u putanji odluke.",
        "**Kalibracija otporna na kvar.** Tok kalibracije prekida se kada "
        "dokaza nema, umjesto da upozori i nastavi. Prag se izvodi iz "
        "odvojenog perioda i provjerava se na trećem, vremenski kasnijem "
        "periodu prije nego što uređaj uopšte pređe u nadzor.",
        "**Kapija pouzdanosti.** Prozor koji je interno nestabilan odbija se "
        "kao nepouzdan umjesto da bude protumačen. Jedan mikrofon ne može "
        "tvrditi šta je izvor smetnje, pa uređaj to i ne tvrdi.",
        "**Mjerene negativne nalaze.** Zabilježeno je i objašnjeno šest "
        "alternativnih obilježja koja su slabija od usvojenog, dvije "
        "standardne tehnike vremenskog filtriranja koje pogoršavaju sistem, i "
        "jedno robusno pravilo praga koje je oborila sopstvena provjera na "
        "pločici.",
        "**Reproducibilan artefakt.** Kompletan tok, od pripreme podataka do "
        "firmvera i zapisa fizičkih mjerenja, čuva se u javnom spremištu sa "
        "kontrolnim sumama izvora svakog mjerenja.",
    ])

    r.naslov("Pregled rada po poglavljima", 2)
    r.pasus(
        "U drugom poglavlju date su teorijske osnove: postavka zadatka DCASE, "
        "spektralna obilježja, Mahalanobisova udaljenost, regularizacija "
        "kovarijanse i metrike vrednovanja, kao i osnovne karakteristike "
        "korišćene hardverske platforme. Treće poglavlje opisuje koncept "
        "rješenja, podjelu posla između računara i uređaja i arhitekturu "
        "sistema.", uvlaka=False)
    r.pasus(
        "Četvrto poglavlje je hronološki prikaz razvoja modela, sa svim "
        "izmjerenim pokušajima — od autoenkodera do konačnog spektralnog "
        "obilježja — uključujući i one koji nisu uspjeli, jer oni objašnjavaju "
        "zašto konačno rješenje radi. Peto poglavlje opisuje realizaciju na "
        "platformi ESP32-S3: prihvat zvuka, izračunavanje obilježja, "
        "organizaciju memorije i strukturu firmvera.")
    r.pasus(
        "Šesto poglavlje uvodi protokol mjerenja i politike odlučivanja: "
        "kapiju kvaliteta kalibracije, izvođenje i provjeru praga, kapiju "
        "pouzdanosti i vremensko pravilo alarma. Sedmo poglavlje donosi "
        "rezultate — na referentnom skupu, na uređaju i na stvarnom "
        "ventilatoru. Osmo poglavlje raspravlja o rezultatima i navodi "
        "ograničenja, a deveto poglavlje daje zaključak i pravce daljeg rada.")


# ==========================================================================
# 2. TEORIJSKE OSNOVE
# ==========================================================================
def _teorija(r) -> None:
    r.naslov("Teorijske osnove")
    r.pasus(
        "U ovom poglavlju izloženi su pojmovi na kojima počiva rješenje: "
        "postavka zadatka nenadgledane detekcije anomalija zvuka, spektralna "
        "obilježja i njihova rezolucija, statistička mjera odstupanja i njena "
        "regularizacija, metrike vrednovanja i karakteristike korišćene "
        "hardverske platforme.")

    r.naslov("Postavka zadatka", 2)
    r.pasus(
        "Detekcija anomalija zvuka mašina svodi se na sljedeće: na osnovu "
        "kratkog zvučnog isječka odrediti da li mašina radi normalno. "
        "Otežavajuća okolnost je što se anomalije ne mogu unaprijed prikupiti "
        "— kvarovi su rijetki, raznovrsni i skupi da bi se namjerno izazivali. "
        "Zbog toga se model uči isključivo iz normalnih snimaka, a anomalija "
        "se definiše kao odstupanje od naučenog opisa normalnog stanja.")
    r.pasus(
        "Skup podataka korišćen u ovom radu je razvojni skup takmičenja DCASE "
        "2026, zadatak 2 [1]. Postavka je *first-shot*: model se ocjenjuje na "
        "vrsti mašine i na fizičkom primjerku koji nisu korišćeni za "
        "podešavanje. Skup razlikuje izvorni i ciljni domen, gdje ciljni domen "
        "predstavlja drugi primjerak iste vrste mašine ili promijenjene uslove "
        "rada, čime se namjerno uvodi pomak domena [2], [3].")
    r.pasus(
        "Za ventilator, koji je predmet ovog rada, izvorni domen sadrži 990 "
        "snimaka normalnog rada. Svaki snimak traje 10 s i uzorkovan je na "
        "16 kHz. Ciljni domen sadrži manji broj normalnih snimaka i skup "
        "anomalnih snimaka koji se otvara tek u završnoj fazi ocjene.")

    r.naslov("Spektralna obilježja i rezolucija", 2)
    r.pasus(
        "Uobičajeno obilježje u ovoj oblasti je logaritamski mel spektrogram, "
        "koji oponaša nelinearnu frekvencijsku osjetljivost ljudskog sluha "
        "[1]. Mel skala namjerno spaja susjedne frekvencije na višim "
        "opsezima, što je korisno za govor i muziku, ali nije nužno korisno za "
        "mašinu čiji potpis čine uske harmonijske linije.")
    r.pasus(
        "Alternativa korišćena u ovom radu je procjena spektralne gustine "
        "snage Velčovim postupkom [4]. Signal se dijeli na preklapajuće "
        "segmente, nad svakim se računa periodogram, a rezultati se usrednjavaju. "
        "Time se smanjuje varijansa procjene po cijenu frekvencijske "
        "rezolucije, a odnos je pod kontrolom preko dužine segmenta. Za dužinu "
        "segmenta od 8192 uzorka i frekvenciju odabiranja od 16 kHz, razmak "
        "između susjednih tačaka spektra dat je izrazom (1):")
    r.jednacina("Δf = fs / N = 16000 / 8192 ≈ 1,95 Hz", 1)
    r.pasus(
        "Za poređenje, uobičajena dužina prozora od 1024 uzorka daje razmak od "
        "15,6 Hz. Razlika je odlučujuća kada su nosioci informacije uske "
        "harmonijske linije osnovne frekvencije obrtanja, što je slučaj kod "
        "ventilatora. Ta veza između fizike mašine i izbora rezolucije "
        "detaljno je izmjerena u četvrtom poglavlju.", uvlaka=False)

    r.naslov("Mahalanobisova udaljenost", 2)
    r.pasus(
        "Nakon što je isječak sveden na vektor obilježja, potrebna je mjera "
        "koliko taj vektor odstupa od naučenog normalnog stanja. Euklidska "
        "udaljenost nije prikladna jer tretira sve dimenzije jednako i "
        "zanemaruje njihove međusobne veze. Mahalanobisova udaljenost [7] uzima "
        "u obzir kovarijansnu strukturu podataka, izraz (2):")
    r.jednacina("s(x) = (z − c)ᵀ P (z − c)", 2)
    r.pasus(
        "gdje je *z* standardizovani vektor obilježja, *c* lokalni centar "
        "naučen na konkretnoj mašini, a *P* inverzna kovarijansna matrica "
        "(matrica preciznosti) naučena unaprijed na velikom korpusu ispravnih "
        "snimaka. Vrijednost *s(x)* je kvadrirana Mahalanobisova udaljenost i "
        "koristi se kao mjera odstupanja.", uvlaka=False)
    r.pasus(
        "Značajna osobina ove mjere je da je **dvostrana po konstrukciji**: "
        "udaljenost raste i kada obilježje poraste i kada opadne u odnosu na "
        "centar. To odgovara stvarnosti, jer se kvar može ispoljiti i kao "
        "pojačanje i kao slabljenje pojedinih komponenti spektra.")

    r.naslov("Regularizacija kovarijanse", 2)
    r.pasus(
        "Procjena kovarijansne matrice iz konačnog uzorka je nepouzdana kada "
        "je broj dimenzija uporediv sa brojem uzoraka. Empirijska matrica "
        "postaje loše uslovljena ili singularna, a njen inverz numerički "
        "neupotrebljiv. Postupak Ledoa i Volfa [5] rješava to skupljanjem "
        "empirijske matrice prema strukturisanoj meti, sa koeficijentom koji "
        "se bira analitički tako da minimizuje očekivanu kvadratnu grešku.")
    r.pasus(
        "Ovaj postupak nije kozmetički detalj. U četvrtom poglavlju je "
        "izmjereno da je jedan raniji negativan rezultat — obilježje sa više "
        "dimenzija koje je izgledalo lošije — zapravo bio posljedica loše "
        "uslovljene kovarijanse, a ne loše ideje. Kada je skupljanje uvedeno, "
        "veći broj dimenzija prestao je da bude kazna.")

    r.naslov("Metrike vrednovanja", 2)
    r.pasus(
        "Osnovna metrika je površina ispod ROC krive (AUC). Ona mjeri "
        "vjerovatnoću da nasumično izabrani anomalni isječak dobije veću "
        "ocjenu od nasumično izabranog normalnog, dakle kvalitet rangiranja "
        "kroz sve moguće pragove. Vrijednost 0,50 odgovara slučajnom "
        "rangiranju. Važno je da AUC **ne** predstavlja procenat tačnosti i da "
        "ne govori ništa o tome kako će sistem raditi sa konkretnim izabranim "
        "pragom.")
    r.pasus(
        "Parcijalna površina pAUC računa se samo u oblasti niske stope lažnih "
        "uzbuna i bolje odgovara praktičnoj upotrebi, gdje je veliki broj "
        "lažnih alarma neprihvatljiv. U ovom radu se prijavljuje "
        "standardizovani pAUC pri stopi lažnih uzbuna do 0,1.")
    r.pasus(
        "Za stvarni uređaj ni AUC ni pAUC nisu dovoljni. Poslije izbora praga "
        "obavezno se prijavljuju i broj alarmnih prozora, broj alarmnih "
        "epizoda, kašnjenje detekcije i vrijeme oporavka. Razlika između "
        "alarmnog prozora i alarmne epizode je suštinska: uzastopni prozori "
        "iznad praga pripadaju istoj epizodi dok se alarm ne ugasi, pa "
        "predstavljanje broja prozora kao broja epizoda precjenjuje učestalost "
        "alarma za red veličine.")

    r.naslov("Hardverska platforma", 2)
    r.pasus(
        "Ciljna platforma je modul ESP32-S3-WROOM-1 N32R16V [8]. Sadrži "
        "dvojezgarni procesor *Xtensa LX7* na 240 MHz, 512 KB interne "
        "statičke memorije, 32 MB fleš memorije i 16 MB oktalne "
        "pseudostatičke memorije. Za ovaj rad su bitne tri osobine: "
        "hardverska podrška za sabirnicu I2S sa prenosom preko DMA, dovoljno "
        "radne memorije za spektar visoke rezolucije, i skup vektorskih "
        "instrukcija koji ubrzava operacije nad nizovima brojeva.")
    r.pasus(
        "Kao izvor zvuka koristi se digitalni MEMS mikrofon INMP441 [10]. On "
        "daje "
        "24-bitni podatak preko sabirnice I2S, bez potrebe za analognim "
        "pojačavačem ili spoljnim analogno-digitalnim pretvaračem. Time se iz "
        "lanca uklanja najveći izvor šuma i neponovljivosti kod jeftinih "
        "akustičkih sistema. Karakteristike platforme date su u Tabeli 2.1.")
    r.tabela(
        "Karakteristike korišćene platforme",
        ["Stavka", "Vrijednost"],
        [
            ["Modul", "ESP32-S3-WROOM-1 N32R16V"],
            ["Procesor", "dvojezgarni Xtensa LX7, 240 MHz"],
            ["Interna memorija", "512 KB SRAM"],
            ["Spoljna memorija", "16 MB oktalni PSRAM, 32 MB fleš"],
            ["Mikrofon", "INMP441, digitalni MEMS, I2S"],
            ["Frekvencija odabiranja", "16 kHz, 16 bita po uzorku"],
            ["Razvojno okruženje", "ESP-IDF v5.5.5"],
        ])
    r.pasus(
        "Zabranjeni su pinovi 35, 36 i 37, koje modul koristi za oktalnu "
        "pseudostatičku memoriju. Raspored ostalih pinova dat je u petom "
        "poglavlju.", uvlaka=False)


# ==========================================================================
# 3. KONCEPT RJEŠENJA
# ==========================================================================
def _koncept(r) -> None:
    r.naslov("Koncept rješenja")
    r.pasus(
        "Osnovna zamisao rješenja je podjela posla na ono što se može naučiti "
        "unaprijed i ono što se mora izmjeriti na licu mjesta. Ta podjela "
        "nije proizvoljna nego slijedi iz mjerenja opisanog u četvrtom "
        "poglavlju: oblik varijacije normalnog rada traži stotine snimaka i "
        "uči se jednom, dok je položaj centra specifičan za svaki primjerak "
        "mašine i dovoljno ga je izmjeriti iz desetak isječaka.")

    r.naslov("Podjela posla između računara i uređaja", 2)
    r.pasus(
        "Na računaru se, iz 990 snimaka normalnog rada izvornog domena, uče "
        "dvije stvari: parametri standardizacije po dimenzijama i matrica "
        "preciznosti dobijena postupkom Ledoa i Volfa. Obje se ugrađuju u "
        "firmver kao konstantne tabele. Matrica preciznosti dimenzija 96×96 "
        "zauzima 36 864 B, a parametri standardizacije 768 B, što je "
        "zanemarljivo u odnosu na raspoloživu fleš memoriju.")
    r.pasus(
        "Na uređaju se, u prvim minutima rada pored konkretne mašine, mjere "
        "tri stvari: lokalni centar iz deset ispravnih isječaka, prag odluke "
        "iz odvojenog perioda normalnog rada, i granica pouzdanosti pojedinog "
        "prozora. Sve tri veličine su specifične za tu mašinu, taj položaj "
        "mikrofona i tu prostoriju, i nijedna se ne prenosi između postavki. "
        "Podjela posla prikazana je na Slici 3.1.")
    r.slika("slike/sl_sistem.png",
            "Podjela posla: opšti model se uči na računaru i ugrađuje u "
            "firmver, a centar, prag i granica pouzdanosti mjere se na licu "
            "mjesta")

    r.naslov("Tok rada uređaja", 2)
    r.pasus(
        "Uređaj se poslije uključenja nalazi u stanju čekanja i ne donosi "
        "nikakve zaključke. Kalibracija se pokreće isključivo svjesnom "
        "radnjom operatera — pritiskom na taster — i to je namjerno, jer "
        "automatsko pokretanje bi omogućilo da uređaj nauči neispravno stanje "
        "kao normalno. Poslije pokretanja tok prolazi kroz sljedeće faze:")
    r.stavke([
        "`SETTLE` — kratko smirivanje poslije uključenja mikrofona, jer "
        "prelazna pojava pri uključenju kvari prvi blok mjerenja;",
        "`CENTER_LEARNING` — deset isječaka od po 10 s iz kojih se računa "
        "lokalni centar;",
        "`COMMISSION_DERIVE` — 44 prozora u kojima su prisutna samo normalna "
        "stanja i iz kojih se izvodi prag;",
        "`COMMISSION_VERIFY` — 22 dodatna, vremenski kasnija normalna "
        "prozora na kojima se izvedeni prag provjerava;",
        "`MONITORING` — redovan nadzor, u kojem se centar i prag više ne "
        "mijenjaju.",
    ])
    r.pasus(
        "Ključna osobina ovog toka je da su izvođenje praga i njegova "
        "provjera **razdvojeni u vremenu i po podacima**. Prag izveden na "
        "jednom skupu prozora provjerava se na drugom, kasnijem skupu. Ako na "
        "toj provjeri padne, kalibracija se odbija i uređaj ne prelazi u "
        "nadzor. Prag se pritom ne podešava da bi provjera prošla; to bi "
        "poništilo smisao provjere.")

    r.naslov("Hijerarhija odlučivanja", 2)
    r.pasus(
        "Odluka se ne donosi u jednom koraku nego kroz hijerarhiju u kojoj "
        "svaki nivo može zaustaviti dalje zaključivanje. Redoslijed je "
        "sljedeći: ispravnost signala, prisustvo mašine, pouzdanost prozora, "
        "pa tek onda odstupanje od naučenog stanja.")
    r.stavke([
        "**Ispravnost signala.** Provjerava se broj primljenih uzoraka, "
        "prisustvo zaglavljenih i nultih vrijednosti, zasićenje i konačnost "
        "izračunatih veličina. Neispravan signal zaustavlja tok.",
        "**Prisustvo mašine.** Nivo ispod kalibrisane srednje vrijednosti "
        "umanjene za 11 dB, i to u tri uzastopna prozora, znači da mašina "
        "više ne radi. Uređaj tada ne prijavljuje anomaliju nego odsustvo "
        "mašine, jer to nisu iste tvrdnje.",
        "**Pouzdanost prozora.** Ako se pet potprozora unutar jednog mjerenja "
        "međusobno previše razlikuju, prozor se proglašava nepouzdanim i ne "
        "ulazi u građenje alarma. Uređaj ne tvrdi šta je izvor te "
        "nestabilnosti, jer jedan mikrofon to ne može utvrditi.",
        "**Odstupanje.** Tek prozor koji je prošao sva tri prethodna nivoa "
        "poredi se sa pragom.",
    ])
    r.pasus(
        "Sistem je projektovan tako da nedostatak dokaza vodi u zaustavljanje, "
        "a ne u pretpostavku da je sve u redu. To načelo je u kodu sprovedeno "
        "dosljedno i provjerava se automatski pri svakoj izmjeni.")


# ==========================================================================
# 4. RAZVOJ MODELA
# ==========================================================================
def _model(r) -> None:
    r.naslov("Razvoj modela — svi izmjereni pokušaji")
    r.pasus(
        "Ovo poglavlje prikazuje put od prvog pokušaja do konačnog rješenja, "
        "sa svim međurezultatima. Neuspjeli pokušaji nisu izostavljeni, iz dva "
        "razloga. Prvo, oni objašnjavaju zašto konačno rješenje izgleda baš "
        "tako. Drugo, negativan rezultat koji nije zapisan vraća se kasnije "
        "kao „nova ideja“ i troši vrijeme po drugi put.")
    r.pasus(
        "Sve vrijednosti u ovom poglavlju su AUC na ciljnom domenu ventilatora "
        "— dakle na primjerku koji model nije čuo — osim gdje je izričito "
        "navedeno drugačije. Protokol lokalne kalibracije je isti kod svih "
        "pristupa: *k* isječaka ciljne mašine koristi se samo za mjerenje "
        "centra, ocjena se radi na preostalim normalnim i svim anomalnim "
        "isječcima, isječak korišćen za kalibraciju se nikada ne ocjenjuje, a "
        "postupak se ponavlja 20 do 100 puta sa različitim izborom.")

    r.naslov("Pravilo poštenog poređenja", 2)
    r.pasus(
        "Prije prikaza rezultata potrebno je navesti pravilo koje je naučeno "
        "na sopstvenoj grešci. Poređenja metoda važe samo na **uparenim "
        "izborima kalibracionih isječaka**. Isti postupak je pod jednim "
        "skupom izbora dao AUC 0,674, a pod drugim 0,643. Ta razlika od tri "
        "poena je čist šum izbora isječaka, a prije nego što je to uočeno "
        "bila je zavedena kao razlika između metoda.")
    r.pasus(
        "Zbog toga se uz srednju vrijednost AUC obavezno prijavljuje i "
        "standardna devijacija preko podjela, a poređenja se rade na istim "
        "podjelama za sve metode.")

    r.naslov("Faza 1 — neuronske mreže", 2)
    r.pasus(
        "Polazno stanje bio je autoenkoder, standardna osnova takmičenja "
        "DCASE. Mjerenja su data u Tabeli 4.1.")
    r.tabela(
        "Rezultati pristupa zasnovanih na neuronskim mrežama",
        ["Pristup", "AUC"],
        [
            ["Autoenkoder (osnova DCASE)", "0,451"],
            ["Naučena ugradnja preko svih 7 mašina", "0,495"],
            ["Klasifikator brzine ventilatora", "0,530"],
            ["Samonadzirano učenje", "≈ 0,50"],
        ], desno={1})
    r.pasus(
        "Autoenkoder uči da prekopira spektar. Mreža koja dobro kopira ne mora "
        "razumjeti mašinu — dovoljno joj je da zapamti prosječan oblik. Na "
        "istom snimku izmjerena je greška rekonstrukcije 2,53 za ispravan i "
        "2,57 za neispravan ventilator, dakle razlika od 1,6 %. Greška "
        "rekonstrukcije nije mjera zdravlja mašine.", uvlaka=False)
    r.pasus(
        "Naučena ugradnja pada iz drugog razloga. Mreža je učena da razlikuje "
        "tipove mašina i radne režime, a taj zadatak je prelak: dovoljno joj "
        "je da nauči „ovo je ventilator, ovo je reduktor“. Da bi to postigla, "
        "ona namjerno odbacuje varijaciju unutar jedne mašine — a upravo ta "
        "varijacija razlikuje ispravan od neispravnog primjerka.")

    r.naslov("Faza 2 — statistika nad mel sažetkom", 2)
    r.pasus(
        "Mreža je napuštena. Isječak se sažima u srednju vrijednost i "
        "standardnu devijaciju po mel traci, kovarijansa se uči unaprijed na "
        "990 izvornih snimaka, a na uređaju se mjeri samo centar. Rezultati su "
        "u Tabeli 4.2.")
    r.tabela(
        "Statistički pristupi nad log-mel sažetkom",
        ["Pristup", "AUC", "Zaključak"],
        [
            ["Sažetak 1280 + puna kovarijansa", "0,643–0,674", "prvi upotrebljiv rezultat"],
            ["Sažetak + dijagonalna kovarijansa", "0,595", "signal je u vezama među trakama"],
            ["Miješanje naučene i izmjerene kovarijanse", "0,674", "čisto naučena je najbolja"],
            ["Oduzimanje sredine po traci", "0,544", "briše i korisnu informaciju"],
            ["Bogatiji sažetak (percentili, dinamika)", "0,578", "pogrešno protumačeno, vidi 4.4"],
            ["Kalibracija po radnom režimu", "0,582", "mali dobitak"],
            ["Zbir najvećih odstupanja", "0,645", "kvar nije lokalizovan u par traka"],
        ], desno={1})
    r.pasus(
        "Ključni nalaz ove faze je poređenje pune i dijagonalne kovarijanse na "
        "izvornom domenu: 0,855 naspram 0,543. Informaciju nose **korelacije "
        "između traka**, ne pojedinačna rasipanja. Odatle slijedi podjela "
        "posla koja je ostala do kraja rada: oblik varijacije se uči unaprijed "
        "jer traži stotine snimaka, a centar se mjeri na licu mjesta jer je za "
        "njega dovoljno desetak.", uvlaka=False)

    r.naslov("Faza 3 — sistematska runda nad ocjenjivačem", 2)
    r.pasus(
        "Sprovedeno je šest serija eksperimenata nad zadnjim dijelom obrade, "
        "sve na uparenim izborima kalibracionih isječaka. U Tabeli 4.3 "
        "prikazani su samo nalazi koji mijenjaju sliku.")
    r.tabela(
        "Izbor iz rundi nad ocjenjivačem",
        ["Pristup", "AUC", "Zaključak"],
        [
            ["Skupljanje po Ledou i Volfu, prostor 256", "0,673", "+3 poena, 19/20 pobjeda"],
            ["Niskorangovana kovarijansa (q = 32)", "0,672", "isti dobitak, jeftinije"],
            ["Medijana kalibracionog centra", "0,716", "+3, potvrđeno na 7 mašina"],
            ["Vinsorizovana sredina centra", "0,671–0,684", "medijana je bolja"],
            ["Najbliži susjedi na kalibracione isječke", "0,565–0,585", "minimalna udaljenost šteti"],
            ["Potprozori 2 s i percentil", "0,504–0,544", "razvodnjavanje ne pomaže"],
            ["Modulacioni spektar mel energija", "0,550", "ne"],
            ["Sprega susjednih traka", "0,460", "ispod slučajnog"],
            ["Vremenska autokorelacija traka", "0,434", "ispod slučajnog"],
            ["Robusna kovarijansa (MinCovDet)", "0,607–0,682", "lošije od Ledoa i Volfa"],
            ["Rang-ansambli mel varijanti", "0,578–0,684", "slabiji član vuče jačeg nadolje"],
        ], desno={1})
    r.pasus(
        "Nalaz o skupljanju kovarijanse mijenja tumačenje ranijeg negativnog "
        "rezultata. „Bogatiji sažetak“ iz druge faze nije pao zato što je "
        "ideja loša, nego zato što je matrica dimenzija 1280×1280 procijenjena "
        "iz 990 snimaka matematički neodrživa. Kada je skupljanje uvedeno, "
        "veći broj dimenzija prestao je da bude kazna.", uvlaka=False)
    r.pasus(
        "Dvanaest varijanti staje na AUC 0,716. Taj plato je bio jasan signal "
        "da uzrok ograničenja nije u ocjenjivaču.")

    r.naslov("Faza 4 — promjena obilježja i proboj", 2)
    r.pasus(
        "Do ovog trenutka svi pristupi dijelili su isti log-mel ulaz sa "
        "prozorom od 1024 uzorka i 128 mel traka. Prešlo se na spektar visoke "
        "rezolucije: Velčova procjena sa segmentom od 8192 uzorka i "
        "preklapanjem od 50 %, sažeta u 96 logaritamski raspoređenih traka od "
        "10 do 4000 Hz, logaritmovana i normalizovana oduzimanjem skalarne "
        "srednje vrijednosti isječka. Izmjerene varijante daje Tabela 4.4.")
    r.tabela(
        "Varijante spektralnog obilježja visoke rezolucije",
        ["Varijanta", "AUC", "Zaključak"],
        [
            ["`psd_shape`", "0,864 ± 0,025", "konačni izbor"],
            ["`psd_raw` (bez normalizacije nivoa)", "0,841", "proboj ne zavisi samo od normalizacije"],
            ["`periodic` (uz anvelopu i skalare)", "0,827", "anvelopa kvari"],
            ["Spektar anvelope sam", "0,513", "modulacija ne nosi signal"],
            ["`psd_shape` + medijana centra", "0,855", "medijana ovdje ne pomaže"],
            ["Ansambl `psd_shape` + `mel256`", "0,784", "slabiji član kvari jačeg"],
        ], desno={1})
    r.pasus(
        "Razlog zbog kojeg ovo radi je fizički, a ne algoritamski. Ventilator "
        "je rotaciona mašina i njegov potpis čine uske harmonijske linije "
        "osnovne frekvencije obrtanja. Prethodni ulaz je imao razmak tačaka "
        "spektra od 15,6 Hz, a mel trake dodatno spajaju susjedne frekvencije, "
        "pa se te linije razmažu prije nego što model uopšte išta vidi. "
        "Rezolucija od 1,95 Hz ih razdvaja, što se vidi na Slici 4.1.",
        uvlaka=False)
    r.slika("slike/sl_rezolucija.png",
            "Spektar normalnog rada ventilatora pri dvije rezolucije; pri "
            "razmaku od 15,6 Hz harmonijske linije se stapaju, a pri 1,95 Hz "
            "ostaju razdvojene")
    r.pasus(
        "Zanimljivo je da medijana centra, koja je u mel prostoru donosila tri "
        "poena, u ovom prostoru ne donosi ništa. Objašnjenje je da je medijana "
        "pomagala zato što je mel prostor bio šumniji; u čistijem spektralnom "
        "prostoru robusnost više nema šta da popravlja. Koliko kalibracija "
        "mora da traje pokazuje Tabela 4.5.")
    r.tabela(
        "Zavisnost AUC od trajanja kalibracije (konačno obilježje)",
        ["Trajanje kalibracije", "50 s", "100 s", "200 s", "300 s", "400 s"],
        [["AUC", "0,834", "0,853", "0,864", "0,866", "0,875"]],
        desno={1, 2, 3, 4, 5})
    r.pasus(
        "Već 50 s kalibracije prelazi postavljeni cilj od 0,80, a kriva je "
        "ravna poslije 200 s. Trajanje kalibracije zato nije usko grlo, što je "
        "bilo važno za odluku o tome koliko dugo uređaj mora da sluša prije "
        "nego što postane upotrebljiv.", uvlaka=False)

    r.naslov("Granica važenja: pobjeda za ventilator, ne uopšte", 2)
    r.pasus(
        "Do ovog trenutka obilježje je bilo mjereno samo na ventilatoru. "
        "Poslije mjerenja na svih sedam mašina razvojnog skupa slika je bitno "
        "drugačija, i to je nalaz koji se mora navesti uz svaku tvrdnju o "
        "kvalitetu rješenja. Poređenje po mašinama daje Tabela 4.6.")
    r.tabela(
        "Poređenje obilježja po mašinama, kanonska evaluacija "
        "(*k* = 20, 100 podjela)",
        ["Mašina", "`psd_shape`", "`mel1280`", "`mel256`"],
        [
            ["**fan**", "**0,867**", "0,627", "0,590"],
            ["sliderEmu", "0,585", "0,559", "0,563"],
            ["gearboxEmu", "0,544", "0,611", "0,581"],
            ["valveEmu", "0,738", "0,765", "0,770"],
            ["bearingEmu", "0,506", "0,576", "0,569"],
            ["ToyCar", "0,448", "0,539", "0,536"],
            ["ToyCarEmu", "0,376", "0,552", "0,518"],
        ], desno={1, 2, 3})
    r.pasus(
        "Obilježje `psd_shape` pobjeđuje na dvije od sedam mašina, a po "
        "harmonijskoj sredini — koja je zvanična mjera takmičenja — lošije je "
        "od mel osnove. Fizički razlog je očekivan: uske harmonijske linije "
        "postoje kod rotacionih mašina, ali ne kod ventila koji je impulsivan, "
        "klizača kod kojeg dominira trenje, ili igračke. Tamo visoka "
        "frekvencijska rezolucija ne donosi ništa, a troši dimenzije i "
        "pogoršava procjenu kovarijanse.", uvlaka=False)
    r.pasus(
        "Za ovaj rad to znači sljedeće. Uređaj je namijenjen ventilatorima, pa "
        "izbor obilježja ostaje ispravan i tvrdnja o AUC 0,867 **važi za "
        "ventilator**. Tvrdnja da je ovo obilježje opšte poboljšanje detekcije "
        "anomalija zvuka **ne stoji** i tako se i piše. Ako bi se sistem širio "
        "na drugi tip mašine, obilježje bi se biralo po tipu, a takav izbor je "
        "moguće napraviti bez ijedne ciljne oznake, samo iz izvornog domena.")

    r.naslov("Faza 5 — šest unaprijed navedenih alternativa", 2)
    r.pasus(
        "Sve prethodne faze bile su pokušaji da se nađe bolje obilježje, i "
        "svaki je bio motivisan onim što je prethodni propustio. Ova faza je "
        "prvi put postupila obrnuto: uzeto je šest pravaca koje je plan naveo "
        "**unaprijed**, izmjereni su svi odjednom pod istim podjelama, i "
        "rezultat je objavljen kakav god bio. Kandidati su bili u kodu prije "
        "nego što je ijedan anomalni isječak otvoren, a lista se nije mijenjala "
        "prema rezultatu. Rezultati svih šest dati su u Tabeli 4.7.")
    r.tabela(
        "Šest unaprijed navedenih alternativa (*k* = 10, 20 podjela)",
        ["Kandidat", "Ideja", "AUC", "Razlika"],
        [
            ["`psd_shape`", "dosadašnje obilježje", "0,856 ± 0,024", "—"],
            ["`psd_order`", "spektar u jedinicama reda", "0,639", "−0,217"],
            ["`psd_regime`", "zaseban centar po režimu", "0,856", "0,000"],
            ["`psd_logratio`", "odnos dva kanala", "0,719", "−0,137"],
            ["`psd_coherence`", "koherencija dva kanala", "0,751", "−0,105"],
            ["`psd_masked`", "maska buke iz drugog kanala", "0,450", "−0,406"],
            ["`transient`", "spektralni fluks, kurtozis", "0,565", "−0,291"],
            ["`psd_plus_transient`", "spori i brzi put", "0,857", "+0,001"],
        ], desno={2, 3})
    r.pasus(
        "Nijedan kandidat ne pobjeđuje. Jedini pozitivan pomak od 0,001 je "
        "dvadeset puta manji od sopstvenog rasipanja po podjeli, pa nije "
        "poboljšanje nego šum.", uvlaka=False)
    r.pasus(
        "Mehanizam pada svakog kandidata je zabilježen, jer je to korisnije od "
        "same brojke. Pristupi zasnovani na redu i režimu počivaju na "
        "pretpostavci da oznake brzine u skupu znače različitu obrtnu brzinu. "
        "Procjena osnovne frekvencije dala je 34,0 Hz za sve tri brzine. Prvi "
        "refleks je bio da je procjena pokvarena, pa je urađena kontrola "
        "nezavisna od nje — položaj tonalnih vrhova iznad spektralne pozadine. "
        "Vrhovi se poklapaju unutar jedne tačke spektra za sve tri brzine. "
        "Brzine se, dakle, u ovom skupu ne razlikuju po obrtnoj frekvenciji "
        "nego po širokopojasnom nivou; procjena je bila ispravna, a "
        "preslikavanje ose je samo izgubilo rezoluciju.")
    r.pasus(
        "Dvokanalni pristupi su svi slabiji od bližeg kanala samog. Varijanta "
        "sa maskom pala je ispod slučajnog pogađanja, i razlog je poučan: "
        "maska potiskuje trake u kojima je dalji kanal uporediv sa bližim, a "
        "ventilator je glasan u oba kanala. Maska je zato potiskivala baš "
        "signal. Tranzijentni put mjeri udarnost, a anomalije ovog ventilatora "
        "su tonalne i širokopojasne, pa mjeri nešto što u ovim podacima ne "
        "postoji.")
    r.pasus(
        "Ova faza nije dala bolji model, ali je dala dvije druge stvari. Prva "
        "je potvrda da su ograničenja u firmveru bila ispravna: firmver je "
        "odbijao da tvrdi promjenu brzine, ambijentalnu buku ili mehaničku "
        "anomaliju kao kategoriju, jer dokaza nije bilo. Ova faza je dokaze "
        "potražila po sve tri linije i nije ih našla. Druga je preusmjeravanje "
        "na pravo usko grlo: kada šest alternativa ne pomjeri obilježje, a "
        "prag se između dvije kalibracije razlikuje šesnaest puta, dalje "
        "ulaganje u obilježje nema smisla.")

    r.naslov("Faza 6 — vremensko pravilo odlučivanja", 2)
    r.pasus(
        "Ova faza ne mijenja obilježje nego način na koji se od niza ocjena "
        "pravi alarm. Dotadašnje pravilo — tri uzastopna prozora iznad praga — "
        "uvedeno je kao razumna pretpostavka i nikada nije bilo izmjereno. "
        "Očekivanje je bilo da će eksponencijalno usrednjavanje i kumulativna "
        "suma biti nadogradnja. Izmjerena pravila poredi Tabela 4.8.")
    r.tabela(
        "Vremenska pravila odlučivanja (40 podjela, 2000 normalnih prozora)",
        ["Pravilo", "Lažnih/h", "Tuđa mašina/h", "Odziv na pobudu od 1 prozora"],
        [
            ["3 uzastopna prozora", "0,00", "11,16", "0,004"],
            ["4 uzastopna prozora", "0,00", "10,98", "0,000"],
            ["**Histereza + 3 uzastopna**", "**0,00**", "**5,40**", "**0,000**"],
            ["Eksponencijalno usrednjavanje + 3", "5,40", "6,48", "0,592"],
            ["Kumulativna suma", "5,40", "11,16", "0,721"],
        ], desno={1, 2, 3})
    r.pasus(
        "Izmjereno je suprotno od očekivanog. Obje standardne tehnike po "
        "konstrukciji prenose informaciju kroz vrijeme: kod eksponencijalnog "
        "usrednjavanja pobuda od jednog prozora ostaje u statistici nekoliko "
        "prozora i sama dopuni niz od tri, a kod kumulativne sume se "
        "akumulira. Obje su napravljene da uhvate **mali trajni** pomjeraj u "
        "šumu, a ovdje je zadatak obrnut — odbaciti **veliku kratku** pobudu.",
        uvlaka=False)
    r.pasus(
        "Usvojena je histereza sa razdvojenim pragom ulaska i izlaska, koja ne "
        "unosi memoriju o veličini pobude, a prepolovljuje broj alarmnih "
        "epizoda kada se akustika pomjeri. Ovo je najjasniji primjer pravila "
        "da standardna tehnika nije isto što i prikladna tehnika.")

    r.naslov("Sažetak napretka", 2)
    r.pasus(
        "Tabela 4.9 sažima napredak kroz faze razvoja, a Slika 4.2 isti "
        "napredak prikazuje grafički.", uvlaka=False)
    r.tabela(
        "Napredak kroz faze razvoja",
        ["Faza", "Najbolji AUC", "Prava prepreka"],
        [
            ["1. Neuronske mreže", "0,530", "zadatak učenja ne odgovara zadatku detekcije"],
            ["2. Statistika nad mel sažetkom", "0,674", "—"],
            ["3. Ocjenjivač", "0,716", "uslovljenost kovarijanse, pa plato"],
            ["4. **Obilježje**", "**0,864**", "**rezolucija po frekvenciji**"],
            ["5. Šest alternativa", "0,857", "nijedna ne pobjeđuje — prepreka nije obilježje"],
            ["6. Vremensko pravilo", "—", "pravilo alarma; usvojena histereza"],
        ], desno={1})
    r.slika("slike/sl_napredak.png",
            "Napredak najboljeg izmjerenog AUC kroz faze razvoja; jedina "
            "promjena obilježja donijela je veći pomak od dvanaest varijanti "
            "ocjenjivača zajedno")
    r.pasus(
        "Napredak od 0,451 do 0,864 postignut je uz potvrđen rad na uređaju. "
        "Iz ovog puta izdvajaju se pouke koje vrijede i van ovog rada. "
        "Obilježje nosi više od ocjenjivača: dvanaest varijanti ocjenjivača "
        "dalo je sedam poena, a jedna promjena obilježja petnaest. Negativan "
        "rezultat na bliskim parametrima ne zatvara pravac — u ranijoj tabeli "
        "neuspjeha stajalo je da finiji prozor od 4096 uzoraka sa linearnim "
        "trakama daje 0,50 do 0,64, i to je zaustavilo istraživanje na duže "
        "vrijeme, a pobjednik je bio dva parametra dalje. Konačno, "
        "„verifikovano“ ne znači „optimalno“: raniji ulaz je bio potvrđen "
        "poređenjem računara i uređaja i zato tretiran kao nedodirljiv, ali "
        "verifikacija dokazuje da je implementacija tačna, ne da je izbor "
        "dobar.", uvlaka=False)


# ==========================================================================
# 5. REALIZACIJA
# ==========================================================================
def _realizacija(r) -> None:
    r.naslov("Realizacija na platformi ESP32-S3")
    r.pasus(
        "U ovom poglavlju opisana je realizacija na ciljnoj platformi: "
        "povezivanje mikrofona, prihvat zvuka, izračunavanje obilježja, "
        "organizacija memorije i struktura firmvera. Prikazana su i mjerenja "
        "vremena izvršavanja i tačnosti u odnosu na referentnu implementaciju "
        "na računaru.")

    r.naslov("Povezivanje i raspored pinova", 2)
    r.pasus(
        "Mikrofon INMP441 povezuje se na sabirnicu I2S sa tri signalne linije "
        "i napajanjem. Linija za izbor kanala vezuje se na masu, čime se bira "
        "lijevi kanal koji firmver čita; ako ta linija ostane nepovezana, "
        "uređaj prima tišinu, što je greška koja se lako previdi jer sistem "
        "nastavlja da radi. Raspored pinova dat je u Tabeli 5.1.")
    r.tabela(
        "Povezivanje mikrofona INMP441",
        ["Pin mikrofona", "Pin ESP32-S3", "Napomena"],
        [
            ["VDD", "3V3", "uz 100 nF i 10 µF što bliže mikrofonu"],
            ["GND", "GND", "zajednička masa"],
            ["SCK", "GPIO 4", "bit takt sabirnice I2S"],
            ["WS", "GPIO 5", "izbor riječi"],
            ["SD", "GPIO 6", "podatak, ka mikrokontroleru"],
            ["`L/R`", "GND", "izbor lijevog kanala"],
        ])
    r.pasus(
        "Signalne veze do mikrofona drže se kraćim od 10 cm zbog integriteta "
        "digitalnog signala. Taster za pokretanje kalibracije vezan je na "
        "GPIO 10 prema masi, uz unutrašnji *pull-up* otpornik, a dvije "
        "svjetleće diode na GPIO 2 i GPIO 11 preko otpornika od 220 do 330 Ω. "
        "Pinovi 35, 36 i 37 se ne koriste jer ih zauzima oktalna "
        "pseudostatička memorija. Cijela šema povezivanja data je na "
        "Slici 5.1.", uvlaka=False)
    r.slika("slike/sl_sema.png",
            "Šema povezivanja mikrofona, tastera i signalnih dioda na modul "
            "ESP32-S3")

    r.naslov("Prihvat zvuka", 2)
    r.pasus(
        "Zvuk se prihvata preko sabirnice I2S sa prenosom preko direktnog "
        "pristupa memoriji, u kružni bafer. Čitanje je ograničeno vremenski: "
        "ako podaci ne stignu u očekivanom roku, tok se zaustavlja sa "
        "izričitim razlogom umjesto da blokira ili tiho vrati prazan bafer. "
        "Uz svaki prozor prijavljuje se i broj izgubljenih uzoraka u odnosu na "
        "prethodni prozor.")
    r.pasus(
        "Ta razlika je važnija nego što izgleda. Kumulativni brojač "
        "izgubljenih uzoraka pokazuje veliku vrijednost jer uređaj u praznom "
        "hodu, dok čeka pritisak tastera, ne prazni kružni bafer. To nisu "
        "izgubljeni mjerni uzorci. Mjerodavna je razlika po prozoru tokom "
        "mjerenja, i ona je u svim prijavljenim rezultatima jednaka nuli.")

    r.naslov("Izračunavanje obilježja", 2)
    r.pasus(
        "Obilježje se računa u sljedećim koracima. Prozor od 10 s pokriva se "
        "sa 39 preklapajućih segmenata dužine 8192 uzorka sa korakom od 4096. "
        "Nad svakim segmentom primjenjuje se prozorska funkcija i brza "
        "Furijeova transformacija, a kvadrati modula se usrednjavaju. Dobijeni "
        "spektar se sažima u 96 logaritamski raspoređenih traka između 10 i "
        "4000 Hz, logaritmuje i normalizuje oduzimanjem skalarne srednje "
        "vrijednosti.")
    r.pasus(
        "Dobijeni vektor se standardizuje parametrima naučenim na računaru, "
        "poslije čega se računa kvadrirana Mahalanobisova udaljenost od "
        "lokalnog centra prema izrazu (2). Sav račun je u pokretnom zarezu "
        "jednostruke tačnosti. Izmjerena vremena izračunavanja daje "
        "Tabela 5.2.")
    r.tabela(
        "Mjerenja izračunavanja obilježja na uređaju",
        ["Veličina", "Vrijednost"],
        [
            ["Vrijeme obrade po prozoru od 10 s", "716 ms"],
            ["Rezerva u realnom vremenu", "oko 14 puta"],
            ["Razlika računar–uređaj, digitalni ulaz", "9,5 · 10⁻⁷"],
            ["Razlika računar–uređaj, živi mikrofon", "1,7 · 10⁻⁶"],
            ["Izgubljenih uzoraka po prozoru", "0"],
        ], desno={1})
    r.pasus(
        "Rezerva od oko četrnaest puta znači da uređaj obradi prozor od 10 s "
        "za 0,72 s, pa ostaje dovoljno vremena za sve ostale poslove i za "
        "znatno složeniji nastavak obrade ako bi bio potreban. Poklapanje sa "
        "referentnom implementacijom na računaru na šest značajnih cifara "
        "potvrđuje da je prenos obilježja na uređaj tačan.", uvlaka=False)

    r.naslov("Organizacija memorije", 2)
    r.pasus(
        "Matrica preciznosti od 96×96 vrijednosti u pokretnom zarezu zauzima "
        "36 864 B i smještena je u fleš memoriju kao konstantna tabela, "
        "zajedno sa parametrima standardizacije. Lokalni centar od 96 "
        "vrijednosti zauzima 384 B i drži se u radnoj memoriji. Baferi za "
        "spektar i međurezultate transformacije smješteni su u internu "
        "statičku memoriju zbog brzine pristupa, dok kružni bafer za zvuk "
        "koristi pseudostatičku memoriju.")
    r.pasus(
        "Konačni binarni fajl firmvera, u konfiguraciji sa istraživačkom "
        "telemetrijom, zauzima 354 784 B. To je mali dio raspoložive fleš "
        "particije, pa memorija nije ograničavajući činilac ovog rješenja.")

    r.naslov("Struktura firmvera", 2)
    r.pasus(
        "Firmver je organizovan tako da je svaki dio politike odlučivanja "
        "zaseban modul sa jasnim ulazom i izlazom, što je omogućilo da se "
        "isti moduli provjeravaju na računaru bez pločice. Konačni tok "
        "obuhvata module za prihvat zvuka, provjeru kvaliteta signala, "
        "izračunavanje obilježja, kalibraciju, izvođenje praga, kapiju "
        "pouzdanosti, vremensku odluku i operaterski interfejs. Uloga svakog "
        "modula data je u Tabeli 5.3.")
    r.tabela(
        "Moduli konačnog toka",
        ["Modul", "Uloga"],
        [
            ["`audio_i2s.c`", "prihvat zvuka sa vremenskim ograničenjem"],
            ["`audio_quality_state.c`", "provjere ispravnosti signala"],
            ["`psd_features_c.c`", "izračunavanje spektralnog obilježja"],
            ["`psd_live.c`", "glavni tok, kalibracija i izvođenje praga"],
            ["`asd_calibration_quality.c`", "kapija kvaliteta kalibracije"],
            ["`asd_commissioning.c`", "faze izvođenja i provjere praga"],
            ["`asd_interference.c`", "kapija pouzdanosti prozora"],
            ["`asd_temporal.c`", "vremensko pravilo odlučivanja"],
            ["`asd_events.c`", "semantika događaja i stanja"],
            ["`asd_operator.c`", "taster, diode i operaterski tok"],
        ])
    r.pasus(
        "Firmver je pisan za okruženje ESP-IDF [9]. Svaki modul koji donosi "
        "odluku ima parnjaka u testovima na računaru, "
        "koji se preko sučelja za pozivanje funkcija iz dijeljene biblioteke "
        "poredi sa referentnom implementacijom u Pythonu. Time se izbjegava "
        "situacija u kojoj se ista logika neprimjetno razilazi između dvije "
        "implementacije.", uvlaka=False)

    r.naslov("Telemetrija i zapis mjerenja", 2)
    r.pasus(
        "Uređaj tokom rada preko serijske veze emituje strukturisane zapise sa "
        "izričitom oznakom verzije protokola. Zapisi pokrivaju kvalitet "
        "signala, stanje i prelaze između stanja, događaje, prisustvo mašine, "
        "vremensku odluku, kapiju pouzdanosti i sažetak kalibracije. Računar "
        "te zapise samo prima i provjerava; on ne učestvuje u odlučivanju.")
    r.pasus(
        "Provjera je namjerno stroga. Nepoznat zapis, nedostajuće polje, "
        "vrijednost koja nije konačan broj ili redoslijed koji krši protokol "
        "obaraju cio zapis mjerenja kao nevalidan. Tokom razvoja je to više "
        "puta oborilo mjerenja koja su na prvi pogled izgledala uredno, i "
        "svaki takav slučaj je zabilježen.")
    r.pasus(
        "U razvojnoj konfiguraciji uređaj dodatno emituje i sam vektor od 96 "
        "obilježja, kao i pet potvektora po prozoru. Ti podaci se čuvaju uz "
        "svaki zapis mjerenja i omogućavaju da se svaka odluka naknadno "
        "rekonstruiše na računaru, bez ponavljanja fizičkog eksperimenta.")


# ==========================================================================
# 6. PROTOKOL I POLITIKE
# ==========================================================================
def _protokol(r) -> None:
    r.naslov("Protokol mjerenja i politike odlučivanja")
    r.pasus(
        "Ovo poglavlje opisuje pravila po kojima uređaj donosi odluke i "
        "pravila po kojima se mjerenja proglašavaju validnim. Ona su nastala "
        "kao odgovor na konkretne izmjerene probleme, pa je uz svako pravilo "
        "naveden i razlog njegovog postojanja.")

    r.naslov("Zašto je politika praga postala glavni problem", 2)
    r.pasus(
        "Prvi test na stvarnom ventilatoru pokazao je razdvajanje između "
        "izazvane promjene protoka i normalnog rada sa AUC 0,999, dakle skoro "
        "savršeno rangiranje. Istovremeno je 54 od 60 prozora normalnog rada "
        "bilo iznad praga, dakle 90 % lažnih uzbuna. Rangiranje i politika "
        "praga su dvije različite stvari, i to mjerenje ih je prvi put "
        "razdvojilo.")
    r.pasus(
        "Uzrok je fizički. Kalibracija je gledala 100 s, a ventilator izluta "
        "izvan tog opsega kroz deset minuta rada. Nivo signala pritom ostaje "
        "praktično nepromijenjen — ne mijenja se jačina nego položaj "
        "harmonijskih linija, što uho ne primjećuje, a Mahalanobisova "
        "udaljenost preko 96 traka vidi kao veliku promjenu. Pored toga, prag "
        "izveden iz dvije uzastopne kalibracije razlikovao se šesnaest puta.")
    r.pasus(
        "Iz toga slijedi pravilo koje je usvojeno i nije se mijenjalo: prag se "
        "izvodi iz odvojenog, dovoljno dugog perioda u kojem su prisutna samo "
        "normalna stanja, zamrzava se prije bilo kakvog izlaganja izazvanoj "
        "promjeni, i **ne podešava se naknadno**. Ako provjera padne, mjerenje "
        "se odbacuje, a ne prag.")

    r.naslov("Kapija kvaliteta kalibracije", 2)
    r.pasus(
        "Prvi filter primjenjuje se na samu kalibraciju. Nad deset "
        "kalibracionih isječaka računa se ocjena svakog isječka u odnosu na "
        "centar dobijen iz preostalih devet, čime se dobija mjera unutrašnje "
        "usaglašenosti. Ako je koeficijent varijacije tih ocjena veći od 0,6, "
        "kalibracija se odbija.")
    r.pasus(
        "Ovo pravilo je u praksi oborilo veliki broj kalibracija, i uzrok je "
        "detaljno izmjeren. Devet od deset isječaka je uvijek uredno, a strada "
        "tačno jedan, i uvijek u istom uskom pojasu od 66 do 75 Hz, što "
        "odgovara frekvenciji obrtanja ventilatora. Rasipanje te jedne trake "
        "kroz deset isječaka iznosi 0,08 dB u snimku koji prolazi, a 0,23 do "
        "0,33 dB u odbijenima. Dovoljan je, dakle, jedan skok od oko 0,7 dB u "
        "jednoj od 96 traka da kalibracija padne.")
    r.pasus(
        "Razlog te osjetljivosti je što je kovarijansa naučena na drugim "
        "ventilatorima i u toj traci ima vrlo malu varijansu, pa "
        "Mahalanobisova udaljenost tamo kažnjava nesrazmjerno. To je svojstvo "
        "metode i tako se i prijavljuje.")
    r.pasus(
        "Rješenje nije bilo pomjeranje granice, jer bi to ukinulo zaštitu od "
        "toga da centar nauči nešto što nije normalno stanje. Umjesto toga, "
        "kapiji je dozvoljeno da izbaci **najviše dva** najgora kalibraciona "
        "isječka, uz ponovno računanje centra i svih ocjena poslije svakog "
        "izbacivanja. Preostali isječci moraju proći istu, nepromijenjenu "
        "granicu. Treća nestabilnost obara kalibraciju kao i ranije, a svako "
        "izbacivanje se zapisuje u telemetriju.")

    r.naslov("Izvođenje i provjera praga", 2)
    r.pasus(
        "Poslije prihvaćene kalibracije uređaj prikuplja 44 prozora u kojima "
        "su prisutna samo normalna stanja. Iz raspodjele ocjena tih prozora "
        "izvode se dva praga: prag ulaska u alarm kao empirijski 99. "
        "percentil, i prag izlaska kao 95. percentil, ograničen odozdo "
        "medijanom a odozgo na polovinu praga ulaska. Centar ostaje onaj koji "
        "je kapija kvaliteta prihvatila; ne mijenja se u ovoj fazi.")
    r.pasus(
        "Razdvojeni pragovi ulaska i izlaska daju histerezu iz šeste faze "
        "razvoja modela. Ograničenje odozgo na polovinu praga ulaska uvedeno "
        "je poslije mjerenja u kojem je prag izlaska bio postavljen previsoko, "
        "pa se alarm iz prve izazvane promjene nikada nije ugasio i sljedeća "
        "dva bloka mjerenja nisu imala u šta da uđu.")
    r.pasus(
        "Izvedeni prag se zatim provjerava na 22 dodatna, **vremenski "
        "kasnija** normalna prozora. Provjera je stroga: nijedan alarm nije "
        "dozvoljen. Ako se alarm pojavi, kalibracija se odbija sa izričitim "
        "razlogom i uređaj ne prelazi u nadzor.")
    r.pasus(
        "Ta provjera nije formalnost. Tokom razvoja je isprobano robusnije "
        "pravilo praga, zasnovano na medijani i medijani apsolutnog "
        "odstupanja, sa empirijskim percentilom kao gornjom granicom. Na "
        "pločici je to pravilo dalo prag od 791, dok su normalni prozori u "
        "istoj sesiji bili između 2083 i 7766. Provjera je kalibraciju odbila "
        "prije nego što je nastao ijedan prozor nadzora. Uzrok je što medijana "
        "apsolutnog odstupanja opisuje samo tijelo raspodjele, a rep raspodjele "
        "kod ovog ventilatora je znatno duži od trostruke robusne devijacije, "
        "pa robusna granica sječe ispod normalnog radnog opsega. Empirijski "
        "percentil taj rep poštuje jer se računa iz stvarnih vrijednosti.")
    r.pasus(
        "Robusno pravilo je poslije toga uklonjeno iz konačnog toka, ali je "
        "zadržano u spremištu sa svojim testom, da bi ovaj negativan rezultat "
        "mogao da se ponovi.")

    r.naslov("Kapija pouzdanosti", 2)
    r.pasus(
        "Prozor od 10 s dijeli se na pet potprozora, i za svaki se računa "
        "obilježje. Ako se ta obilježja međusobno previše razlikuju, prozor je "
        "interno nestabilan i njegova ocjena nije pouzdana mjera stanja "
        "mašine. Takav prozor prelazi u posebno stanje i **ne ulazi u građenje "
        "alarma**.")
    r.pasus(
        "Granica te nestabilnosti izvodi se po sesiji, kao najveća "
        "izmjerena nestabilnost među deset kalibracionih prozora pomnožena sa "
        "1,25. Raniji pokušaj sa apsolutnom granicom nije radio, jer je "
        "granica nosila skalu prethodnog položaja mikrofona i prestajala da "
        "važi čim se postavka promijeni.")
    r.pasus(
        "Ovo stanje ima jasno određeno značenje i jednako jasno određena "
        "ograničenja. Ono suspenduje građenje alarma, ali **ne briše** već "
        "aktivan alarm i **ne mijenja** naučeni centar ni prag. Uređaj pritom "
        "ne tvrdi šta je izazvalo nestabilnost. Jedan mikrofon ne može "
        "razlikovati govor od udarca ili od promjene na mašini, i sistem koji "
        "bi to tvrdio davao bi dijagnozu bez dokaza. Ako nestabilnost potraje "
        "šest uzastopnih prozora, izdaje se upozorenje da nadzor duže vrijeme "
        "nije pouzdan, što je tvrdnja koju jedan mikrofon jeste u stanju da "
        "podrži.")

    r.naslov("Vremensko pravilo i semantika događaja", 2)
    r.pasus(
        "Alarm se podiže tek poslije tri uzastopna pouzdana prozora iznad "
        "praga ulaska, a gasi se kada ocjena padne ispod praga izlaska. "
        "Poslije dvanaest alarmnih prozora, dakle oko dva minuta neprekidnog "
        "odstupanja, izdaje se dodatna oznaka trajnog odstupanja. Stanje "
        "pritom ostaje anomalija.")
    r.pasus(
        "Namjerno se razlikuje trajno akustičko odstupanje od terminalnog "
        "problema. Terminalno stanje rezervisano je za grešku senzora ili "
        "toka: isteklo vrijeme čekanja na zvuk, vrijednost koja nije konačan "
        "broj, gubitak prisustva mašine ili odbijena kalibracija. Dugotrajna "
        "akustička promjena prijavljuje se kao anomalija sa oznakom "
        "nepoznate promjene.")
    r.pasus(
        "Razlog za tu podjelu je principijelan. Jedan mikrofon može potvrditi "
        "da se promjena održava, ali ne može dokazati da je uzrok mehanički "
        "kvar. Uređaj koji bi lampicu „kvar“ palio na osnovu zvuka tvrdio bi "
        "više nego što je izmjerio.")

    r.naslov("Protokol fizičkog mjerenja", 2)
    r.pasus(
        "Fizička mjerenja izvode se po unaprijed zaključanom protokolu. "
        "Operater potvrđuje postavku, pokreće mjerenje, a zatim redom označava "
        "uslove: normalnu osnovu, izazvanu promjenu, oporavak, ambijentalne "
        "smetnje i završni oporavak. Oznake uslova upisuju se na računaru u "
        "trenutku kada operater unese komandu.")
    r.pasus(
        "Prvi i posljednji prozor svakog bloka označavaju se kao prelazni i "
        "izbacuju se iz metrika. Razlog je što se oznaka uslova upisuje na "
        "granici, pa prozor od 10 s koji je zahvata sadrži oba stanja. Bez tog "
        "pravila bi granični prozori sistematski kvarili obje strane poređenja.")
    r.pasus(
        "Uz svako mjerenje čuva se potpuna evidencija porijekla: identifikator "
        "izmjene izvornog koda, kontrolna suma razlike u odnosu na tu izmjenu, "
        "kontrolna suma svakog izvornog fajla koji učestvuje u odluci, "
        "kontrolna suma binarnog fajla firmvera, sirovi bajtovi sa serijske "
        "veze i izvedene tabele. Time se svako mjerenje može naknadno vezati "
        "za tačno određeno stanje sistema.")


# ==========================================================================
# 7. REZULTATI
# ==========================================================================
def _rezultati(r) -> None:
    r.naslov("Rezultati")
    r.pasus(
        "Rezultati se prijavljuju u tri odvojena nivoa: na referentnom skupu "
        "podataka, na uređaju uz reprodukciju zvuka preko zvučnika, i na "
        "stvarnom ventilatoru. Ta tri nivoa se ne smiju miješati jer mjere "
        "različite stvari, a razlike među njima su same po sebi nalaz.")

    r.naslov("Referentni skup podataka", 2)
    r.pasus(
        "Razvojni skup DCASE 2026 sastavljen je od snimaka stvarnih industrijskih "
        "mašina [3] i minijaturnih mašina iz skupa ToyADMOS2 [6], pa "
        "obuhvata i domenski pomak koji se u radu mjeri. Obrada na računaru "
        "oslanja se na biblioteke SciPy [12] za spektralnu procjenu i "
        "scikit-learn [11] za procjenu kovarijanse. "
        "Kanonska evaluacija poredi tri obilježja pod istim ocjenjivačem, na "
        "sto unaprijed određenih podjela, sa 20 isječaka za lokalnu "
        "kalibraciju. Anomalni isječci se učitavaju tek u završnoj fazi, "
        "poslije zamrzavanja liste metoda, podjela i modela. Postupak se "
        "prekida ako otkrije anomaliju u kohorti za obuku ili preklapanje "
        "kalibracionih i ocjenjivanih isječaka. Rezultati su u Tabeli 7.1.")
    r.tabela(
        "Kanonska evaluacija: AUC po mašini i obilježju "
        "(*k* = 20, 100 podjela)",
        ["Mašina", "`psd_shape`", "`mel1280`", "`mel256`"],
        [
            ["**fan**", "**0,867 ± 0,027**", "0,627 ± 0,035", "0,590 ± 0,034"],
            ["valveEmu", "0,738 ± 0,041", "0,765 ± 0,031", "0,770 ± 0,032"],
            ["sliderEmu", "0,585 ± 0,030", "0,559 ± 0,030", "0,563 ± 0,028"],
            ["gearboxEmu", "0,544 ± 0,040", "0,611 ± 0,048", "0,581 ± 0,047"],
            ["bearingEmu", "0,506 ± 0,027", "0,576 ± 0,026", "0,569 ± 0,026"],
            ["ToyCar", "0,448 ± 0,031", "0,539 ± 0,026", "0,536 ± 0,026"],
            ["ToyCarEmu", "0,376 ± 0,066", "0,552 ± 0,094", "0,518 ± 0,094"],
        ], desno={1, 2, 3})
    r.pasus(
        "Za ventilator, koji je predmet ovog rada, postignut je AUC 0,867 uz "
        "standardizovani pAUC pri stopi lažnih uzbuna do 0,1 od 0,667. "
        "Postavljeni cilj od 0,80 je time premašen. Konfiguracija ugrađena u "
        "firmver koristi deset kalibracionih isječaka i za nju je izmjeren AUC "
        "0,856 ± 0,024 na 20 podjela; ta razlika je cijena kraće kalibracije i "
        "navodi se odvojeno da se ne bi predstavljala jača konfiguracija od "
        "one koja stvarno radi na uređaju.", uvlaka=False)

    r.naslov("Mjerenje na uređaju preko zvučnika", 2)
    r.pasus(
        "Prije nego što je nabavljen ventilator, uređaj je provjeravan "
        "reprodukcijom snimaka iz skupa podataka preko zvučnika. To mjerenje "
        "je dalo AUC 0,716 umjesto 0,864, i uzrok je izmjeren, a ne "
        "pretpostavljen. Rasipanje ocjena kroz akustički kanal daje "
        "Tabela 7.2.")
    r.tabela(
        "Rasipanje ocjena kroz akustički kanal",
        ["Put signala", "Ocjena normalnog", "Ocjena anomalije"],
        [
            ["Računar, digitalni zvuk", "79", "117"],
            ["Uređaj, preko zvučnika", "1 300 – 4 000", "2 500 – 4 100"],
        ], desno={1, 2})
    r.pasus(
        "Anomalija iz skupa podataka pomjera ocjenu za oko 48 %, a akustički "
        "kanal pravi rasipanje za red veličine veće. Signal nije nestao nego "
        "je zatrpan. Isti uređaj zaustavljenu mašinu prepoznaje bez greške, "
        "jer je ta promjena mnogo grublja od šuma kanala.", uvlaka=False)
    r.pasus(
        "Kontrolisanim sintetičkim kvarom rastuće jačine izmjeren je i prag "
        "osjetljivosti cijelog lanca. Anomalija iz skupa podataka odgovara "
        "kvaru jačine oko −30 dB, a preko zvučnika je potrebno oko −15 dB da "
        "bi se alarm podigao. Razlika od oko 15 dB objašnjava sve prolaze bez "
        "detekcije i mjerljivo razdvaja tvrdnju „model ne valja“ od tvrdnje "
        "„ovaj kvar je pretih za ovaj put zvuka“.")
    r.pasus(
        "Reprodukcija zvučnikom je konfaund kojeg u stvarnoj primjeni nema, "
        "jer uređaj tamo sluša mašinu direktno, bez dvostrukog prolaza kroz "
        "elektroakustiku. Zbog toga se ovaj rezultat prijavljuje odvojeno i ne "
        "koristi se kao ocjena kvaliteta modela.")

    r.naslov("Prvi test na stvarnom ventilatoru", 2)
    r.pasus(
        "Prvi test u kojem mikrofon sluša stvarni ventilator izveden je sa "
        "mikrofonom na 20 cm od osovine, pod uglom od 90° u odnosu na osu "
        "duvanja. Bočni položaj je izabran jer u struji vazduha turbulencija "
        "na membrani nadjača zvuk mašine. Izazvana promjena je papirić uz "
        "usisnu stranu rešetke, bez kontakta sa lopaticama, ponovljen tri "
        "puta. Ocjene po blokovima date su u Tabeli 7.3.")
    r.tabela(
        "Prvi fizički test: ocjene po blokovima",
        ["Blok", "Prozora", "Medijana", "Min", "Maks"],
        [
            ["Normalna osnova", "60", "876", "180", "16 152"],
            ["Izazvana promjena 1", "6", "29 899", "2 197", "40 812"],
            ["Oporavak 1", "9", "2 883", "553", "27 200"],
            ["Izazvana promjena 2", "6", "30 050", "953", "40 217"],
            ["Oporavak 2", "9", "624", "409", "28 173"],
            ["Izazvana promjena 3", "6", "47 299", "1 111", "48 827"],
            ["Oporavak 3", "10", "718", "643", "48 204"],
            ["Razgovor na 2 m", "6", "11 946", "10 751", "18 202"],
            ["Oporavak", "9", "1 155", "785", "1 581"],
        ], desno={1, 2, 3, 4})
    r.pasus(
        "Odziv na izazvanu promjenu u odnosu na medijanu osnove iznosi 34, 34 "
        "i 54 puta, a prva dva ponavljanja razlikuju se za 0,5 %. Razdvajanje "
        "izazvane promjene od normalnog rada, bez prelaznih prozora, daje AUC "
        "0,999. Razdvajanje izazvane promjene od razgovora daje 0,979, ali iz "
        "svega 48 parova, pa je to indikacija a ne dokaz.", uvlaka=False)
    r.pasus(
        "Istovremeno je 54 od 60 prozora normalnog rada bilo iznad praga. Taj "
        "test je time dao dva razdvojena nalaza: obilježje radi na stvarnom "
        "ventilatoru, a tadašnja politika praga ne radi. Iz drugog nalaza "
        "nastale su politike opisane u šestom poglavlju.")

    r.naslov("Završna validacija na ventilatoru", 2)
    r.pasus(
        "Poslije uvođenja politika iz šestog poglavlja izvedena su dva "
        "validna mjerenja, oba iz **istog binarnog fajla** firmvera. Postavka "
        "je bila ista u oba: mikrofon na 40 cm, ugao 9°, ventilator napajan "
        "preko punjača, u sobi sa zatvorenim prozorom.")

    r.naslov("Mjerenje sa izazvanom promjenom protoka", 3)
    r.pasus(
        "U ovom mjerenju kapija kvaliteta kalibracije je izbacila dva "
        "kalibraciona isječka. Koeficijent varijacije je time pao sa 0,84 na "
        "0,43, čime je kalibracija prihvaćena; bez tog pravila mjerenje ne bi "
        "ni došlo do faze nadzora. Izvedeni prag ulaska iznosi 8084, a prag "
        "izlaska 3707. Ocjene po označenim uslovima daje Tabela 7.4.")
    r.tabela(
        "Ocjene po označenim uslovima, mjerenje sa izazvanom promjenom "
        "(prag ulaska 8084)",
        ["Uslov", "Prozora", "Nepouzdanih", "Alarmnih", "Medijana ocjene"],
        [
            ["Normalna osnova", "5", "0", "0", "1 190"],
            ["Izazvana promjena 1", "5", "4", "0", "26 399"],
            ["Oporavak 1", "5", "0", "0", "2 837"],
            ["Izazvana promjena 2", "5", "3", "0", "60 050"],
            ["Oporavak 2", "5", "1", "0", "2 663"],
            ["Izazvana promjena 3", "5", "2", "**2**", "14 389"],
            ["Oporavak 3", "5", "0", "2", "3 636"],
            ["Razgovor", "5", "4", "0", "36 838"],
            ["Oporavak poslije razgovora", "5", "1", "0", "3 039"],
            ["Vrata", "3", "1", "0", "4 366"],
            ["Završni oporavak", "6", "1", "0", "2 864"],
        ], desno={1, 2, 3, 4})
    r.pasus(
        "Model je promjenu vidio u sva tri bloka: medijane 26 399, 60 050 i "
        "14 389 naspram normalne 1190. Alarm ipak nije podignut u prva dva "
        "bloka, jer je kapija pouzdanosti odbila četiri odnosno tri od pet "
        "prozora kao nestabilne, pa brojač uzastopnih prekoračenja nikada nije "
        "stigao do tri. Treći blok je bio najmirniji i alarm je podignut "
        "poslije tri uzastopna pouzdana prozora.", uvlaka=False)
    r.pasus(
        "Ovo nije promašaj detekcije nego projektovano ponašanje. Papirić se "
        "drži rukom, pa izazvana promjena po konstrukciji nije konstantna, a "
        "sistem odbija da nestabilan prozor proglasi anomalijom. Alarm se "
        "zatim prenio dva prozora u fazu oporavka i ugasio se kada je ocjena "
        "pala ispod praga izlaska, uz medijanu vremena oporavka od 10,1 s.")
    r.pasus(
        "Razgovor i otvaranje vrata nisu podigli alarm iako su im ocjene bile "
        "visoke, 36 838 odnosno 4366. Četiri od pet prozora razgovora "
        "proglašena su nepouzdanim. To je tražena osobina: smetnja se odbija "
        "kao nepouzdana, umjesto da bude protumačena kao stanje mašine. Cijela "
        "trasa mjerenja prikazana je na Slici 7.1.")
    r.slika("slike/sl_run_papiric.png",
            "Trasa ocjene tokom mjerenja sa izazvanom promjenom protoka; "
            "označeni su prag ulaska, prag izlaska, nepouzdani prozori i "
            "alarmna epizoda")

    r.naslov("Mjerenje sa konstantnom promjenom", 3)
    r.pasus(
        "Da bi se provjerilo ponašanje pri promjeni koja jeste konstantna, "
        "izvedeno je drugo mjerenje u kojem je izvor promjene bio konstantan "
        "ton od 1 kHz sa zvučnika, na fiksnoj jačini i položaju. Kalibracija "
        "je u ovom mjerenju prošla bez izbacivanja isječaka, sa koeficijentom "
        "varijacije 0,43. Izvedeni prag ulaska iznosi 21 810, a prag izlaska "
        "10 905. Ocjene po označenim uslovima daje Tabela 7.5.")
    r.tabela(
        "Ocjene po označenim uslovima, mjerenje sa konstantnim tonom "
        "(prag ulaska 21 810)",
        ["Uslov", "Prozora", "Nepouzdanih", "Alarmnih", "Medijana", "Opseg"],
        [
            ["Normalna osnova", "6", "0", "0", "7 164", "6 712 – 8 171"],
            ["Konstantan ton", "45", "8", "14", "22 629", "6 890 – 87 152"],
            ["Poslije tona", "51", "8", "51", "32 884", "12 266 – 127 539"],
        ], desno={1, 2, 3, 4})
    r.pasus(
        "Alarm je podignut poslije tri uzastopna pouzdana prozora iznad praga, "
        "dakle poslije oko 30 s od trenutka kada je ton postao dovoljno jak. "
        "Poslije dvanaest alarmnih prozora, odnosno oko dva minuta, emitovana "
        "je oznaka trajnog odstupanja. Kroz cijelo mjerenje nije izgubljen "
        "nijedan uzorak, a istraživačka telemetrija je kompletna za svih 125 "
        "prozora.", uvlaka=False)
    r.pasus(
        "Prvih devet prozora tona dalo je ocjene između 6890 i 15 582, dakle "
        "unutar normalnog opsega, jer je zvučnik bio na premaloj jačini. "
        "Poslije pojačanja ocjena skače na stabilnih 30 000 do 33 000. To je "
        "koristan negativan podatak: promjena mora biti dovoljno jaka u odnosu "
        "na sopstveni šum ventilatora, a prag nije apsolutna osjetljivost. "
        "Trasa cijelog mjerenja je na Slici 7.2.")
    r.slika("slike/sl_run_ton.png",
            "Trasa ocjene tokom mjerenja sa konstantnim tonom; alarm se "
            "podiže poslije tri uzastopna pouzdana prozora, a oznaka trajnog "
            "odstupanja poslije dvanaest")
    r.pasus(
        "Poslije gašenja tona ocjena je pala sa oko 40 000 na 12 266 do "
        "19 561, dakle ispod praga ulaska ali iznad praga izlaska, pa je alarm "
        "ostao zaključan do kraja mjerenja. Histereza je radila kako je "
        "projektovana, ali je mjerenje završeno prije nego što je ocjena pala "
        "ispod praga izlaska, pa vrijeme oporavka za ovaj izvor promjene nije "
        "izmjereno.")

    r.naslov("Sažetak fizičkih mjerenja", 2)
    r.pasus(
        "Tabela 7.6 sažima oba validna mjerenja na ventilatoru, jedno "
        "pored drugog.", uvlaka=False)
    r.tabela(
        "Sažetak dva validna mjerenja na ventilatoru",
        ["Veličina", "Izazvana promjena protoka", "Konstantan ton"],
        [
            ["Kalibracija", "prihvaćena poslije izbacivanja 2 isječka", "prihvaćena bez izbacivanja"],
            ["Koeficijent varijacije", "0,84 → 0,43", "0,43"],
            ["Prag ulaska / izlaska", "8 084 / 3 707", "21 810 / 10 905"],
            ["Prozora nadzora", "65", "115"],
            ["Alarmnih prozora / epizoda", "3 / 2", "64 / 2"],
            ["Medijana oporavka", "10,1 s", "nije izmjerena"],
            ["Izgubljenih uzoraka", "0", "0"],
            ["Trajno odstupanje prijavljeno", "ne", "da"],
        ])
    r.pasus(
        "Oba mjerenja su označena kao validan fizički rezultat, što znači da "
        "su prošla sve provjere protokola: potpun rukohvat sa firmverom, "
        "prihvaćenu kalibraciju, potpunu i saglasnu telemetriju i odsustvo "
        "izgubljenih uzoraka.", uvlaka=False)

    r.naslov("Provjere na računaru", 2)
    r.pasus(
        "Uz fizička mjerenja, sistem se provjerava i automatski. Skup testova "
        "na računaru sadrži 478 provjera i pokriva poređenje implementacija u "
        "Pythonu i u jeziku C preko dijeljene biblioteke, ugovore protokola, "
        "politike odlučivanja i oba fizička mjerenja kao zamrznutu regresiju. "
        "Poseban alat provjerava da su brojevi u firmveru, u zamrznutim "
        "politikama i u alatima za obradu međusobno saglasni.")
    r.pasus(
        "Ove provjere ne dokazuju ništa fizičko i to je izričito zapisano i u "
        "samoj konfiguraciji neprekidne integracije. Uspješna izgradnja i "
        "zeleni testovi ne dokazuju ni upis firmvera, ni rad na pločici, ni "
        "ponašanje pored stvarne mašine.")


# ==========================================================================
# 8. DISKUSIJA
# ==========================================================================
def _diskusija(r) -> None:
    r.naslov("Diskusija i ograničenja")
    r.pasus(
        "U ovom poglavlju rezultati se tumače, a zatim se navode ograničenja "
        "koja se ne smiju izostaviti pri njihovom čitanju.")

    r.naslov("Šta rezultati pokazuju", 2)
    r.pasus(
        "Osnovna tvrdnja koju mjerenja podržavaju je da je moguće napraviti "
        "samostalan akustički nadzor rotacione mašine na mikrokontroleru "
        "vrijednosti nekoliko desetina evra, bez mreže i bez računara u "
        "putanji odluke. Uređaj sam uči normalno stanje mašine koju nikada "
        "nije čuo, sam izvodi prag iz perioda u kojem su prisutna samo "
        "normalna stanja, i pouzdano prijavljuje konstantnu akustičku "
        "promjenu.")
    r.pasus(
        "Druga tvrdnja tiče se odnosa modela i politike oko njega. Kroz cio "
        "rad je model bio bolji nego što je sistem bio upotrebljiv. "
        "Razdvajanje izazvane promjene od normalnog rada bilo je gotovo "
        "savršeno već u prvom fizičkom testu, dok je istovremeno 90 % "
        "normalnih prozora bilo iznad praga. Poboljšanja koja su sistem "
        "učinila upotrebljivim nisu bila poboljšanja modela nego politike: "
        "odvojen period za izvođenje praga, nezavisna provjera tog praga, "
        "histereza, kapija pouzdanosti i pravilo o odbacivanju najviše dva "
        "kalibraciona isječka.")
    r.pasus(
        "Treća tvrdnja tiče se vrijednosti provjera koje se aktiviraju rijetko. "
        "Provjera praga na odvojenom periodu djelovala je kao formalnost sve "
        "dok nije oborila robusno pravilo koje je na papiru izgledalo bolje od "
        "usvojenog. To je najjasnija potvrda da kapija koja se ne aktivira "
        "godinama i dalje ima svrhu.")

    r.naslov("Poređenje sa postojećim radovima", 2)
    r.pasus(
        "U odnosu na objavljena rješenja zadatka DCASE, ovaj rad ne "
        "konkuriše po tačnosti. Vodeći sistemi koriste ansamble dubokih "
        "modela sa samonadziranim predtreniranjem i postižu znatno više "
        "vrijednosti harmonijske sredine preko svih mašina. Doprinos ovog rada "
        "je u drugoj ravni: pokazuje šta se pokvari kada se jedan takav "
        "pristup, sveden na najjednostavniji oblik, stvarno pusti da radi bez "
        "nadzora na mikrokontroleru.")
    r.pasus(
        "U odnosu na postojeće radove iz oblasti minijaturnog mašinskog "
        "učenja, razlika je u tome što se ovdje ne prijavljuje samo da model "
        "staje u memoriju i radi u realnom vremenu. Prijavljuje se i kako se "
        "prag izvodi bez ijedne anomalije, kako se prepoznaje da mjerenje nije "
        "pouzdano, i šta uređaj radi kada dokaza nema.")

    r.naslov("Ograničenja", 2)
    r.pasus(
        "Ograničenja su navedena bez ublažavanja, jer bi njihovo izostavljanje "
        "učinilo rezultate neupotrebljivim za bilo koga ko bi htio da ih "
        "ponovi.")
    r.stavke([
        "**Jedna vrsta mašine.** Izbor obilježja je pobjeda za ventilator, a "
        "izmjereno je da nije opšte poboljšanje. Po harmonijskoj sredini preko "
        "sedam mašina, usvojeno obilježje je lošije od mel osnove.",
        "**Jedan primjerak, jedna prostorija.** Fizička mjerenja izvedena su "
        "na jednom ventilatoru u jednoj sobi. O generalizaciji na drugi "
        "primjerak, drugu prostoriju ili drugi nivo pozadinske buke ne može se "
        "tvrditi ništa.",
        "**Izazvana promjena nije potvrđen kvar.** Papirić uz usisnu stranu i "
        "pušteni ton su kontrolisane, bezbjedne promjene. Nazivati ih kvarom "
        "bez nezavisne stručne potvrde bilo bi netačno.",
        "**Mali uzorci.** Pojedini blokovi mjerenja imaju po pet prozora. "
        "Vrijednosti izvedene iz njih imaju širok interval povjerenja i "
        "predstavljaju funkcionalnu provjeru, ne procjenu stope.",
        "**Stopa lažnih uzbuna nije procijenjena dugoročno.** Odsustvo alarma "
        "tokom nekoliko desetina minuta normalnog rada nije dokaz male "
        "dugoročne stope; jednostrana gornja granica pri takvom trajanju "
        "mjerenja ostaje visoka.",
        "**Vrijeme oporavka poslije jakog izvora promjene nije izmjereno**, "
        "jer je mjerenje završeno dok je ocjena još bila između praga izlaska "
        "i praga ulaska.",
        "**Osjetljivost kapije kvaliteta kalibracije.** Jedan isječak od "
        "deset, sa odstupanjem od oko 0,7 dB u jednoj od 96 traka, dovoljan je "
        "da obori kalibraciju. Pravilo o odbacivanju dva isječka liječi "
        "posljedicu, ne uzrok.",
        "**Numeričke politike nisu zamrznute za proizvodnju.** Pravilo "
        "izvođenja praga je potvrđeno na dva mjerenja, ali zamrzavanje za "
        "proizvodnu upotrebu traži novu verziju politike i novo, unaprijed "
        "prijavljeno mjerenje.",
    ])

    r.naslov("Šta nije provjereno na hardveru", 2)
    r.pasus(
        "Sljedeće stavke su realizovane u kodu i provjerene na računaru, ali "
        "nisu potvrđene na potpuno sastavljenom hardveru, pa se tako i "
        "prijavljuju: potpuno samostalan rad sa zalemljenim tasterom i "
        "signalnim diodama, ponašanje pri prekidu veze sa mikrofonom, "
        "ponašanje pri nestanku napajanja i pri ponovnom pokretanju, i "
        "mjerenje potrošnje cijelog lanca. Nijedan uspješan test na računaru "
        "ne zamjenjuje te provjere.")


# ==========================================================================
# 9. ZAKLJUČAK
# ==========================================================================
def _zakljucak(r) -> None:
    r.naslov("Zaključak")
    r.pasus(
        "U radu je realizovan samostalan uređaj za nenadgledanu detekciju "
        "anomalija zvuka rotacionih mašina na mikrokontroleru ESP32-S3 sa "
        "jednim MEMS mikrofonom. Opšti oblik varijacije normalnog rada uči se "
        "unaprijed na računaru iz 990 snimaka ispravnog rada, a sve što je "
        "specifično za konkretnu mašinu — centar, prag i granica pouzdanosti — "
        "uređaj mjeri sam, u prvim minutima rada pored te mašine.")
    r.pasus(
        "Postavljeni istraživački cilj od AUC 0,80 je premašen: na referentnom "
        "skupu za ventilator postignut je AUC 0,867 uz standardizovani pAUC od "
        "0,667. Na stvarnom ventilatoru potvrđeno je da uređaj samostalno "
        "nauči normalno stanje, izvede prag iz perioda u kojem su prisutna "
        "samo normalna stanja, odbije nepouzdan prozor umjesto da ga tumači, i "
        "pouzdano prijavi konstantnu akustičku promjenu, uz obradu od 716 ms "
        "po prozoru od 10 s i bez ijednog izgubljenog uzorka.")
    r.pasus(
        "Rad pokazuje i nešto što se rjeđe prijavljuje. Kroz cijeli razvoj "
        "usko grlo nije bio model nego politika odlučivanja oko njega. "
        "Dvanaest varijanti ocjenjivača donijelo je sedam poena, jedna "
        "promjena obilježja petnaest, a upotrebljivost sistema donijela su "
        "pravila koja uopšte ne mijenjaju model: odvojen period za izvođenje "
        "praga, nezavisna provjera tog praga na kasnijim podacima, histereza, "
        "kapija pouzdanosti i ograničeno odbacivanje kalibracionih isječaka.")
    r.pasus(
        "Zabilježeni su i negativni rezultati, sa mehanizmom a ne samo sa "
        "brojkom: šest unaprijed navedenih alternativnih obilježja od kojih "
        "nijedno ne pobjeđuje, dvije standardne tehnike vremenskog filtriranja "
        "koje pogoršavaju sistem jer su napravljene za obrnut zadatak, i jedno "
        "robusno pravilo praga koje je oborila sopstvena provjera na pločici. "
        "Taj posljednji slučaj je ujedno i najjača potvrda da provjere koje se "
        "rijetko aktiviraju imaju smisla.")

    r.naslov("Pravci daljeg rada", 2)
    r.pasus("Iz izmjerenih ograničenja proizlaze sljedeći pravci:", uvlaka=False)
    r.stavke([
        "**Drugi primjerak i druga prostorija.** To je jedini put do bilo "
        "kakve tvrdnje o generalizaciji, i najvažniji sljedeći korak.",
        "**Duže normalno mjerenje.** Stopa lažnih uzbuna traži red veličine "
        "duže mjerenje od dosadašnjih da bi se mogla procijeniti sa smislenim "
        "intervalom.",
        "**Izbor obilježja po tipu mašine.** Izmjereno je da se izbor može "
        "napraviti samo iz izvornog domena, bez ijedne ciljne oznake, i da "
        "takav izbor nadmašuje bilo koji fiksni.",
        "**Uzrok osjetljivosti kapije kvaliteta.** Ispad u uskom pojasu oko "
        "frekvencije obrtanja je izmjeren i objašnjen kao svojstvo "
        "Mahalanobisove udaljenosti sa stranom kovarijansom, ali nije "
        "uklonjen.",
        "**Trajno čuvanje naučenog profila.** Modul za upis u trajnu memoriju "
        "je realizovan i provjeren na računaru, ali se u razvojnoj "
        "konfiguraciji namjerno ne koristi dok politika ne bude zamrznuta.",
        "**Mjerenje potrošnje i rad na bateriji**, kao uslov za primjenu na "
        "mjestima bez stalnog napajanja.",
    ])


# ==========================================================================
# literatura, biografija, prilozi
# ==========================================================================
def _literatura(r) -> None:
    r.naslov("Literatura", numerisi=False)
    r.prazan()
    reference = [
        "T. Nishida et al., „Description and discussion on DCASE 2026 Challenge "
        "Task 2: Noise-aware unsupervised anomalous sound detection for machine "
        "condition monitoring“, arXiv:2606.01578, 2026.",
        "N. Harada et al., „First-shot anomaly sound detection for machine "
        "condition monitoring: A domain generalization baseline“, *EUSIPCO "
        "2023*, str. 191–195, doi: 10.23919/EUSIPCO58844.2023.10289721.",
        "K. Dohi et al., „MIMII DG: Sound dataset for malfunctioning "
        "industrial machine investigation and inspection for domain "
        "generalization task“, *DCASE Workshop 2022*, str. 1–5.",
        "P. D. Welch, „The use of the fast Fourier transform for the "
        "estimation of power spectra: A method based on time averaging over "
        "short, modified periodograms“, *IEEE Trans. Audio Electroacoust.*, "
        "vol. 15, br. 2, str. 70–73, 1967, doi: 10.1109/TAU.1967.1161901.",
        "O. Ledoit i M. Wolf, „A well-conditioned estimator for "
        "large-dimensional covariance matrices“, *J. Multivariate Anal.*, "
        "vol. 88, br. 2, str. 365–411, 2004, "
        "doi: 10.1016/S0047-259X(03)00096-4.",
        "N. Harada et al., „ToyADMOS2: Another dataset of miniature-machine "
        "operating sounds for anomalous sound detection under domain shift "
        "conditions“, *DCASE Workshop 2021*, str. 1–5, "
        "doi: 10.5281/zenodo.5770113.",
        "P. C. Mahalanobis, „On the generalised distance in statistics“, "
        "*Proc. Natl. Inst. Sci. India*, vol. 2, br. 1, str. 49–55, 1936.",
        "Espressif Systems, *ESP32-S3 Series Datasheet*, dostupno na: "
        "https://www.espressif.com/ (pristupljeno u avgustu 2026).",
        "Espressif Systems, *ESP-IDF Programming Guide v5.5*, dostupno na: "
        "https://docs.espressif.com/projects/esp-idf/ (pristupljeno u avgustu "
        "2026).",
        "InvenSense, *INMP441 Omnidirectional Microphone with Bottom Port and "
        "I2S Digital Output — Datasheet*, dokument DS-INMP441.",
        "F. Pedregosa et al., „Scikit-learn: Machine learning in Python“, "
        "*J. Mach. Learn. Res.*, vol. 12, str. 2825–2830, 2011.",
        "P. Virtanen et al., „SciPy 1.0: Fundamental algorithms for "
        "scientific computing in Python“, *Nature Methods*, vol. 17, "
        "str. 261–272, 2020, doi: 10.1038/s41592-019-0686-2.",
    ]
    with r.latinicno():
        for i, ref in enumerate(reference, 1):
            r.referenca(i, ref)


def _biografija(r) -> None:
    r.naslov("Biografija", numerisi=False)
    r.prazan()
    r.pasus(
        "Mihajlo Živković rođen je 11. aprila 2001. godine u Zvorniku. Osnovne "
        "akademske studije završio je na Fakultetu tehničkih nauka u Novom "
        "Sadu, na studijskom programu Mehatronika, robotika i automatizacija, "
        "sa prosječnom ocjenom 9,60. Master akademske studije upisao je 2024. "
        "godine na studijskom programu Energetika, elektronika i "
        "telekomunikacije, modul Embedded sistemi i algoritmi.", uvlaka=False)
    r.pasus(
        "Tokom studija radio je kao inženjer primjene u kompaniji Festo "
        "Srbija, gdje se bavio programibilnim logičkim kontrolerima, "
        "industrijskim sabirnicama i sistemima za rukovanje materijalom. Od "
        "2025. godine radi kao inženjer za ugrađeni Linux i Android u "
        "kompaniji Ikotek, na platformama zasnovanim na procesorima "
        "Qualcomm.")
    r.pasus(
        "Oblasti interesovanja su mu ugrađeni sistemi, obrada signala, "
        "mašinsko učenje na resursno ograničenim uređajima i sistemsko "
        "programiranje.")


def _prilozi(r) -> None:
    r.naslov("Prilozi", numerisi=False)
    r.prazan()

    r.prilog("A")
    r.naslov("Prilog A — sadržaj digitalnog priloga", 2, numerisi=False)
    r.pasus(
        "Zbog obima, izvorni kod, zapisi mjerenja i sirovi podaci dostavljaju "
        "se u digitalnom obliku. Struktura priloga je sljedeća:", uvlaka=False)
    r.kod("""
pc/asd/         Python paket: obilježja, podaci, model, obuka, ocjena,
                protokol izvršavanja, vođeni test, politika kalibracije
pc/tools/       generatori C zaglavlja, alati za mjerenje, host eksperiment
pc/config/      zaključane politike u JSON obliku
pc/tests/       testovi na računaru i poređenje Python-C
firmware/esp32s3_asd/   izvorni kod firmvera za ESP-IDF v5.x
docs/           dokumentacija razvoja, problemi i rješenja
results/        zapisi mjerenja, uključujući fizičke runove
radovi/         ovaj rad i rad za konferenciju
""")
    r.pasus(
        "Adresa spremišta: `https://github.com/mihajloz11/asd-esp32s3`. "
        "[TODO] spremište je u trenutku pisanja privatno; otvoriti ga "
        "prije predaje ili priložiti sadržaj na digitalnom nosaču.",
        uvlaka=False)

    r.prilog("B")
    r.naslov("Prilog B — sažetak politika i njihovih verzija", 2, numerisi=False)
    r.pasus(
        "Tabela B.1 daje sve zaključane politike i njihove verzije.",
        uvlaka=False)
    r.tabela(
        "Zaključane politike i njihove verzije",
        ["Politika", "Verzija", "Šta određuje"],
        [
            ["Kvalitet signala", "`asd-quality-policy-v1.1.0`",
             "pragovi ispravnosti signala i praga nivoa"],
            ["Kvalitet kalibracije", "`asd-commissioning-policy-v1.0.0`",
             "granica koeficijenta varijacije"],
            ["Prisustvo mašine", "`asd-presence-policy-v1`",
             "margina od 11 dB i tri uzastopna prozora"],
            ["Vremenska odluka", "`asd-temporal-policy-v2`",
             "tri uzastopna prozora i histereza"],
            ["Kapija pouzdanosti", "`asd-interference-policy-v3.0.0`",
             "množilac 1,25 nad kalibracionim maksimumom"],
            ["Protokol uređaja", "`asd-quality-v1.6.0`",
             "format telemetrije i stanja"],
            ["Protokol mjerenja", "`physical-fan-v1.9.0`",
             "pravila validnosti fizičkog mjerenja"],
        ])
    r.pasus(
        "Sve navedene politike nose izričitu oznaku da ciljne anomalije nisu "
        "korišćene za njihovo izvođenje, i ta oznaka se provjerava automatski "
        "pri svakoj izmjeni.", uvlaka=False)

    r.prilog("C")
    r.naslov("Prilog C — primjer zapisa telemetrije", 2, numerisi=False)
    r.pasus(
        "Uređaj emituje strukturisane zapise sa izričitom oznakom verzije "
        "protokola. Listing C.1 je izvod iz stvarnog mjerenja, sa sažetkom "
        "kalibracije, izvedenim pragom i podizanjem alarma.", uvlaka=False)
    r.kod("""
CALTRIM  protocol=asd-quality-v1.6.0 policy=k1-two-clip-trim-v1
         discarded_count=2 retained=8 raw_loo_cv=0.841676
QUALITY  protocol=asd-quality-v1.6.0 phase=CAL_SUMMARY result=OBSERVED
         loo_mean=290.661407 loo_sd=123.838638 loo_cv=0.426058
ADAPTTHR n=44 mean=1041.676880 sd=1637.902954 p=0.9900 thr=8084.49365
PROFILE  center_windows=10 derive_windows=44 verify_windows=22
         threshold_enter=8084.49365 threshold_exit=3707.34448
EVENT    type=ANOMALY_ENTERED state=ANOMALY phase=DET
         reason=THRESHOLD_PERSISTENCE event=UNKNOWN_CHANGE
""", potpis="Izvod iz telemetrije stvarnog mjerenja")
