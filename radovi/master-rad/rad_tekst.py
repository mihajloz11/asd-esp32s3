"""Tekst master rada.

Pise se na latinici; `build_rad.py` preslovljava u cirilicu jer to trazi
uputstvo v8. Oznake u tekstu:

    *strani termin*   kurziv, ostaje latinica (uputstvo, str. 4)
    `kod`             Courier New, ostaje latinica
    **naglaseno**     bold, preslovljava se

Izvori rezultata i preostale formalne stavke navedeni su u PREOSTALO-RAD.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rezultati import thesis_rows

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


# prednji dio
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
         "9 poglavlja / {{PAGES}} strana / 12 citata / 20 tabela / 6 slika / "
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
        "U radu je realizovan prototip za nenadgledanu detekciju anomalija zvuka "
        "ventilatora na mikrokontroleru ESP32-S3 sa jednim MEMS mikrofonom. "
        "Globalni model uči se iz 990 normalnih snimaka DCASE 2026, a centar i "
        "pragovi iz normalnog zvuka konkretne postavke. Koriste se 96 logaritamskih"
        " spektralnih traka i kvadrirana Mahalanobisova udaljenost. Razvojni AUC "
        "iznosi 0,856 za deset kalibracionih prozora; odvojena referenca sa "
        "dvadeset prozora daje 0,867. U dvije završne fizičke probe prihvaćeni su "
        "kalibracija i zapis telemetrije. Proba tonom daje alarm i trajno "
        "odstupanje, dok proba papirićem detektuje jedan od tri bloka i ne prolazi "
        "zadate kriterije. Obrada obilježja i ocjene traje oko 716 ms po prozoru od"
        " 10 s. Nema prijavljenih gubitaka uzoraka, ali dugoročna pouzdanost i "
        "detekcija potvrđenih kvarova nisu utvrđene."
    )


def _izvod_en() -> str:
    return (
        "This thesis presents an unsupervised fan sound anomaly-detection prototype"
        " using an ESP32-S3 and one MEMS microphone. A global model is fitted on "
        "990 normal DCASE 2026 recordings; a local centre and thresholds are "
        "learned from normal audio at the installation. The detector uses 96 "
        "logarithmic spectral bands and squared Mahalanobis distance. Developmental"
        " AUC is 0.856 with ten calibration windows; a separate twenty-window "
        "reference reaches 0.867. Two final physical trials pass commissioning and "
        "telemetry checks. The added-tone trial produces alarm and sustained-"
        "deviation events, while the paper-strip trial detects one of three change "
        "blocks and fails its acceptance criteria. Feature and score computation "
        "takes about 716 ms per 10 s window. No dropped samples are reported, but "
        "long-term reliability and detection of confirmed faults remain "
        "unestablished."
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
             "9 chapters / {{PAGES}} pages / 12 references / 20 tables / "
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
    r.prazan(2)
    r.pasus("[TODO] Ovdje se umeće zvanična izjava o akademskoj čestitosti "
            "usaglašena sa mentorom prije predaje rada.", uvlaka=False)


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


# 1. UVOD
def _uvod(r) -> None:
    r.naslov("Uvod")
    r.pasus(
        "Promjene u radu rotacionih mašina mogu se odraziti na njihov zvučni "
        "spektar. Akustička detekcija anomalija koristi ta odstupanja kao razlog za"
        " dodatnu provjeru mašine [2], [3]. Mikrofon omogućava beskontaktno "
        "mjerenje, ali istovremeno prima zvuk okoline. Zbog toga promjena zvuka "
        "sama po sebi ne potvrđuje kvar niti određuje njegov uzrok.")
    r.pasus(
        "Istraživačka zajednica ovaj problem obrađuje pod nazivom detekcija "
        "anomalija zvuka mašina, a od 2020. godine postoji i standardizovan "
        "zadatak u okviru takmičenja DCASE [1]. Postavka je namjerno teška i "
        "realistična: za obuku su dostupni samo snimci ispravnog rada, "
        "anomalije se ne vide unaprijed, a ocjena se radi na drugom fizičkom "
        "primjerku iste vrste mašine. Taj pomak domena čini da rješenja koja "
        "dobro rade na jednoj mašini često podbace na drugoj.")
    r.pasus(
        "Referentni postupci DCASE prvenstveno porede modele na označenim skupovima"
        " snimaka [1], [2]. Prenos na mikrokontroler zahtijeva i provjeru vremena "
        "obrade, memorije i postupka odlučivanja. Uređaj mora da postavi prag, "
        "prepozna nepouzdano mjerenje i zadrži naučeni profil tokom nadzora. U ovom"
        " radu te funkcije razmatraju se zajedno sa kvalitetom rangiranja.")

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
        "Tema je izabrana zbog interesovanja za obradu signala i realizaciju "
        "statističkih modela na ugrađenim sistemima. Cilj je bio da se provjeri "
        "kako ograničenja memorije, vremena obrade i uslova snimanja utiču na "
        "praktičnu upotrebu detektora.")
    r.pasus(
        "Tokom razvoja pokazalo se da kvalitet rangiranja nije dovoljan za "
        "upotrebljiv alarm. Zato je dio rada posvećen izvođenju praga, provjeri "
        "kalibracije i ponašanju pri nepouzdanim mjerenjima.")

    r.naslov("Cilj i doprinosi rada", 2)
    r.pasus(
        "Postavljeni istraživački cilj bio je AUC od najmanje 0,80 na "
        "ventilatoru koji nije korišćen za obuku, uz protokol mjerenja bez "
        "curenja podataka. Pored toga, rad daje sljedeće doprinose:")
    r.stavke([
        "**Kompletan lanac na mikrokontroleru.** Obilježje, ocjena "
        "odstupanja, kalibracija, izvođenje praga i vremensko pravilo "
        "odlučivanja izvršavaju se na uređaju, bez računara u putanji odluke.",
        "**Provjera prihvatljivosti kalibracije.** Učenje se prekida kada podaci ne"
        " zadovolje zadate uslove. Prag se izvodi iz odvojenog normalnog perioda i "
        "provjerava na kasnijem periodu prije prelaska u nadzor.",
        "**Kapija pouzdanosti.** Interno nestabilan prozor iznad ulaznog praga odbija se "
        "kao nepouzdan umjesto da bude protumačen. Jedan mikrofon ne može "
        "tvrditi šta je izvor smetnje, pa uređaj to i ne tvrdi.",
        "**Poređenje alternativnih postupaka.** Prikazano je sedam kandidata uz "
        "osnovno obilježje, više vremenskih pravila i robusno pravilo praga koje je"
        " odbijeno tokom provjere na pločici.",
        "**Digitalni prilog.** Izvorni kod, konfiguracije, tabele i zapisi fizičkih"
        " mjerenja čuvaju se u verzionisanom spremištu, uz kontrolne sume izvora i "
        "firmvera.",
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


# 2. TEORIJSKE OSNOVE
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
        "Korišćen je razvojni skup DCASE 2026, zadatak 2 [1]. Zvanična postavka "
        "*first-shot* razmatra prenos na prethodno neviđene tipove mašina. Ovaj rad"
        " koristi dostupni razvojni skup za izbor i poređenje postupaka, pa njegovi"
        " rezultati nisu nezavisna ocjena na skrivenom skupu takmičenja. Izvorni i "
        "ciljni domen predstavljaju različite uslove snimanja ili rada [2], [3].")
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
        "Korišćena je razvojna ploča sa ESP32-S3 procesorom na 240 MHz i 16 MB "
        "PSRAM-a. Dobavljačka oznaka N32R16V i podešavanje fleš memorije od 32 MB "
        "opisuju konkretnu ploču. Ta oznaka se ne nalazi u tabeli standardnih "
        "WROOM-1 modula u dokumentu [8], pa se kapacitet ploče ne izvodi iz te "
        "tabele. Razvojno okruženje je ESP-IDF 5.5.5 [9].")
    r.pasus(
        "Kao izvor zvuka koristi se digitalni MEMS mikrofon INMP441 [10]. On daje "
        "24-bitni podatak preko sabirnice I2S, pa nisu potrebni spoljni analogno-"
        "digitalni pretvarač i analogni pojačavač. Digitalna veza pojednostavljuje "
        "povezivanje, ali ne uklanja šum mikrofona, uticaj napajanja ili akustike "
        "prostorije. Karakteristike platforme date su u Tabeli 2.1.")
    r.tabela(
        "Karakteristike korišćene platforme",
        ["Stavka", "Vrijednost"],
        [
            ["Ploča", "ESP32-S3, oznaka dobavljača N32R16V"],
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


# 3. KONCEPT RJEŠENJA
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


# 4. RAZVOJ MODELA
def _model(r) -> None:
    r.naslov("Razvoj modela — svi izmjereni pokušaji")
    r.pasus(
        "Ovo poglavlje prikazuje put od prvog pokušaja do konačnog rješenja, "
        "sa svim međurezultatima. Neuspjeli pokušaji nisu izostavljeni, iz dva "
        "razloga. Prvo, oni objašnjavaju zašto konačno rješenje izgleda baš "
        "tako. Drugo, negativan rezultat koji nije zapisan vraća se kasnije "
        "kao „nova ideja“ i troši vrijeme po drugi put.")
    r.pasus(
        "U ovom poglavlju dati su razvojni rezultati na DCASE skupu. Raniji "
        "eksperimenti razlikuju se po podjelama i protokolu; njihove najbolje "
        "vrijednosti opisuju tok istraživanja i nisu jedinstveno kontrolisano "
        "poređenje. Uparene runde koriste iste kalibracione podjele za sve "
        "kandidate. Oznake anomalija ne ulaze u fit, ali je raniji uvid u rezultate"
        " uticao na izbor pristupa, pa ostaje pristrasnost izbora modela.")

    r.naslov("Protokol poređenja", 2)
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
        "U isprobanoj konfiguraciji greška rekonstrukcije nije dovoljno razdvajala "
        "klase. U jednom poređenju dobijeno je 2,53 za normalan i 2,57 za anomalni "
        "snimak, što je razlika od oko 1,6 %. To je nalaz za ovu arhitekturu i "
        "protokol; ne isključuje primjenu drugih autoenkodera.", uvlaka=False)
    r.pasus(
        "Naučena reprezentacija takođe nije dala dobro rangiranje. Jedno moguće "
        "objašnjenje je nepodudaranje zadatka obuke, koji razlikuje tipove mašina i"
        " režime, sa promjenama unutar jedne mašine. Ovaj mehanizam nije izdvojen "
        "posebnim eksperimentom, pa se navodi kao tumačenje.")

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
        "Medijana centra, koja je pomagala u ranijem mel prostoru, u ovoj rundi ne "
        "nadmašuje srednju vrijednost. Različita raspodjela obilježja je moguće "
        "objašnjenje, ali nije posebno izolovana. Tabela 4.5 prikazuje zavisnost "
        "rangiranja od broja kalibracionih isječaka.")
    r.tabela(
        "Zavisnost AUC od trajanja kalibracije (konačno obilježje)",
        ["Trajanje kalibracije", "50 s", "100 s", "200 s", "300 s", "400 s"],
        [["AUC", "0,834", "0,853", "0,864", "0,866", "0,875"]],
        desno={1, 2, 3, 4, 5})
    r.pasus(
        "Već pet normalnih isječaka daje razvojni AUC iznad 0,80. Ova tabela "
        "opisuje samo učenje lokalnog centra i rangiranje; ne obuhvata vrijeme "
        "izvođenja i provjere alarmnog praga. Povećanje broja isječaka i dalje "
        "donosi određeni dobitak, uz duže učenje.", uvlaka=False)

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
        "Obilježje psd_shape daje veći AUC na dvije od sedam mašina u ovom "
        "protokolu. Na ostalima je bolje najmanje jedno mel obilježje. Različita "
        "spektralna struktura mašina može objasniti dio razlike, ali iz ovih "
        "rezultata nije utvrđen poseban fizički uzrok za svaku mašinu. Tabela nije "
        "zvanični ukupni rezultat DCASE takmičenja.", uvlaka=False)
    r.pasus(
        "Za ovaj rad to znači sljedeće. Uređaj je namijenjen ventilatorima, pa "
        "izbor obilježja ostaje ispravan i tvrdnja o AUC 0,867 **važi za "
        "ventilator**. Tvrdnja da je ovo obilježje opšte poboljšanje detekcije "
        "anomalija zvuka **ne stoji** i tako se i piše. Ako bi se sistem širio "
        "na drugi tip mašine, obilježje bi se biralo po tipu, a takav izbor je "
        "moguće napraviti bez ijedne ciljne oznake, samo iz izvornog domena.")

    r.naslov("Faza 5 — poređenje alternativnih obilježja", 2)
    r.pasus(
        "U narednoj rundi poređeno je sedam kandidata sa osnovnim obilježjem na "
        "istih dvadeset kalibracionih podjela. Lista je fiksirana prije te runde "
        "evaluacije. To obezbjeđuje upareno poređenje unutar runde, ali ne uklanja "
        "raniji uvid u razvojne rezultate. Sve konfiguracije su date u Tabeli 4.7.")
    r.tabela(
        "Sedam alternativa i osnovno obilježje (*k* = 10, 20 podjela)",
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
        "Kombinacija sa tranzijentnim obilježjima daje mali pozitivan pomak od oko "
        "0,0012 AUC. Poređenje tog pomaka sa standardnom devijacijom pojedinačnih "
        "rezultata nije test statističke značajnosti. Za takav zaključak potreban "
        "je interval uparenih razlika i nezavisna provjera; postojeći rezultat nije"
        " dovoljan razlog za složeniji model.", uvlaka=False)
    r.pasus(
        "Procijenjena osnovna frekvencija ostaje oko 34 Hz za tri oznake brzine, a "
        "dominantni vrhovi se poklapaju unutar jedne spektralne tačke. To "
        "ograničava korisnost isprobanog preslikavanja u red obrtanja. Bez "
        "tahometra ili potvrde autora skupa nije dokazano da je stvarna brzina "
        "vratila ista; oznaka i akustički vrh ne moraju predstavljati istu fizičku "
        "veličinu.")
    r.pasus(
        "Dvokanalni pristupi su svi slabiji od bližeg kanala samog. Varijanta "
        "sa maskom pala je ispod slučajnog pogađanja, i razlog je poučan: "
        "maska potiskuje trake u kojima je dalji kanal uporediv sa bližim, a "
        "ventilator je glasan u oba kanala. Maska je zato potiskivala baš "
        "signal. Tranzijentni put mjeri udarnost, a anomalije ovog ventilatora "
        "su tonalne i širokopojasne, pa mjeri nešto što u ovim podacima ne "
        "postoji.")
    r.pasus(
        "U ovoj rundi nije utvrđena prednost koja bi opravdala složeniji ugrađeni "
        "model. Dalji razvoj zato je usmjeren na kalibraciju i alarmnu politiku. "
        "Negativni nalazi ostaju ograničeni na ispitane konfiguracije i ne "
        "isključuju druge dvokanalne ili tranzijentne pristupe.")

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
        "U ovoj ranijoj simulaciji histereza smanjuje broj epizoda na drugoj mašini"
        " sa 11,16 na 5,40 na sat. Poređenje ne mjeri detekciju fizičkih kvarova. "
        "Završni firmware koristi zasebno izvedene apsolutne pragove ulaska i "
        "izlaska; raniji faktor izlaska 0,7 nije njegova konačna postavka.")

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
            ["5. Sedam alternativa", "0,857", "nijedna ne pobjeđuje — prepreka nije obilježje"],
            ["6. Vremensko pravilo", "—", "pravilo alarma; usvojena histereza"],
        ], desno={1})
    r.slika("slike/sl_napredak.png",
            "Najbolji razvojni AUC po fazama; različiti protokoli ograničavaju direktno"
            " poređenje")
    r.pasus(
        "Razvoj pokazuje značaj izbora obilježja, regularizacije i zasebne provjere"
        " praga. Najbolje vrijednosti pojedinih faza potiču iz različitih podjela i"
        " konfiguracija. Zbog toga njihov hronološki rast opisuje istraživački put,"
        " a ne kontrolisani efekat jedne promjene.", uvlaka=False)


# 5. REALIZACIJA
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
        "Preporučene su kratke signalne veze do mikrofona. Predviđen je taster "
        "između GPIO 10 i mase, uz unutrašnji *pull-up*, zelena dioda na GPIO 2 "
        "preko 100 Ω i crvena na GPIO 11 preko 330 Ω. Uređaj ostaje na protobordu "
        "MB-102 prema odluci od 2. septembra. Završno povezivanje tastera i dioda "
        "nije potvrđeno mjerenjem; u sačuvanim testovima korišćen je virtuelni "
        "taster preko iste operaterske logike. Šema je data na Slici 5.1.", uvlaka=False)
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
        "U starijim mjerenjima kumulativni brojač uključivao je uzorke odbačene dok"
        " uređaj čeka operatera. Aktuelni firmver prazni bafer i resetuje brojač na"
        " početku sesije. Za prozore mjerenja provjerava se i razlika brojača, koja"
        " je u dva završna zapisa nula. To je dokaz odsustva prijavljenih gubitaka,"
        " a ne nezavisna provjera svakog I2S uzorka.")

    r.naslov("Izračunavanje obilježja", 2)
    r.pasus(
        "Prozor od 10 s pokriva se sa 38 potpunih preklapajućih segmenata dužine "
        "8192 uzorka, sa korakom 4096. Preostalih 256 uzoraka ne ulazi u novi "
        "potpuni segment. Primjenjuje se periodični Hanov prozor, a usrednjeni "
        "spektar snage sažima se u 96 logaritamskih traka od 10 do 4000 Hz. Koristi"
        " se logaritam osnove deset i oduzima srednja vrijednost vektora.")
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
        "Izmjerenih 716 ms odnosi se na računanje obilježja i ocjene, a ne na "
        "ukupno vrijeme akvizicije, istraživačke telemetrije i donošenja alarma. "
        "Oko 14 puta kraća obrada od trajanja prozora potvrđuje izvodljivost tog "
        "računa, ali nije mjerenje najgoreg vremena izvršavanja cijelog sistema. "
        "Navedena poklapanja sa referencom odnose se na konkretne ispitane ulaze.", uvlaka=False)

    r.pasus("Osam traka ne sadrži nijednu FFT tačku i prije centriranja dobija "
            "fiksnu vrijednost −20. Zbog toga oduzimanje sredine ne uklanja potpuno "
            "uticaj pojačanja. Na sintetičkom širokopojasnom signalu, udvostručavanje "
            "amplitude u neizmijenjenom C kodu pomjera popunjene trake za približno "
            "0,05, a prazne za −0,55 jedinica obilježja. Ova računarska provjera "
            "ne mjeri uticaj na fizičku detekciju.")

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
        "Nedostajuće obavezno polje, neispravna vrijednost ili redoslijed "
        "parsiranih protokolarnih zapisa obaraju validnost mjerenja. Dijagnostički "
        "tekst izvan tog ugovora može ostati neparsiran, kao zapis CALTRIM. Zato "
        "prazan spisak grešaka ne dokazuje provjeru svake linije serijskog izlaza.")
    r.pasus(
        "Ti podaci omogućavaju naknadnu analizu obilježja bez novog snimanja, uz "
        "provjeru potpunosti manifesta. Ne zamjenjuju sirovi zvuk pri izmjeni "
        "frontenda, niti predstavljaju novo fizičko mjerenje.")


# 6. PROTOKOL I POLITIKE
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
        "Kalibracija je obuhvatila 100 s zvuka, a kasniji normalni prozori prelaze "
        "tako izveden prag. Analize bilježe osjetljivost uskih spektralnih traka i "
        "razliku pragova do šesnaest puta između ponavljanja. Promjenljiv zvuk, "
        "položaj postavke i kovarijansa mogu doprinositi toj osjetljivosti; "
        "eksperimenti ne izdvajaju jedinstven fizički uzrok.")
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
        "U analiziranim odbijenim kalibracijama najveći doprinos dolazi iz jednog "
        "isječka i uske trake oko 66–75 Hz. Rasipanje te trake iznosi oko 0,08 "
        "jedinica obilježja u prihvaćenom, a 0,23–0,33 u odbijenim zapisima. "
        "Odstupanje od približno 0,7 prati veliki porast ocjene. Bez tahometra taj "
        "pojas ne treba izjednačiti sa potvrđenom frekvencijom obrtanja, niti "
        "opaženo odstupanje tumačiti kao opšti prag osjetljivosti.")
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
        "Ograničenje izlaznog praga utiče na zadržavanje alarma: niži izlazni prag "
        "otežava izlazak i može produžiti epizodu. Ako medijana DERIVE ocjena "
        "premaši polovinu ulaznog praga, firmver odbija nekompatibilne granice. U "
        "završnom testu tonom oporavak nije izmjeren, pa ovo pravilo nije potvrda "
        "oporavka poslije svake promjene.")
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
        "Prozor od 10 s dijeli se na pet potprozora sa sopstvenim obilježjima. Kada"
        " ukupna ocjena premaši ulazni prag i potprozori se previše razlikuju, "
        "kapija označava prozor kao nepouzdan. HOLD prekida niz uzastopnih "
        "prekoračenja. Za ocjene ispod ili na ulaznom pragu ova kapija ne uvodi "
        "HOLD, pa nije opšti filter svih nestabilnih prozora.")
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
        "Alarm se podiže poslije tri uzastopne pouzdane ocjene strogo veće od "
        "ulaznog praga, a gasi se kada ocjena bude manja ili jednaka izlaznom "
        "pragu. Trajno odstupanje prijavljuje se na dvanaestom mjerenom alarmnom "
        "prozoru, uključujući prozor ulaska. HOLD pauzira brojač, pa dvanaest "
        "prozora nije nužno dva minuta neprekidnog zidnog vremena.")
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
        "Host označava naredni DET zapis poslije svake promjene uslova kao "
        "prelazni. Takvi prozori, nepotvrđeni uslovi i nevalidni protokolarni "
        "zapisi izostavljaju se iz metrika. Ne odbacuju se automatski i prvi i "
        "posljednji prozor svakog bloka. Oznake se vezuju za vrijeme prijema "
        "telemetrije, pa ostaje nesigurnost sinhronizacije sa stvarnom pobudom.")
    r.pasus(
        "Uz svako mjerenje čuva se potpuna evidencija porijekla: identifikator "
        "izmjene izvornog koda, kontrolna suma razlike u odnosu na tu izmjenu, "
        "kontrolna suma svakog izvornog fajla koji učestvuje u odluci, "
        "kontrolna suma binarnog fajla firmvera, sirovi bajtovi sa serijske "
        "veze i izvedene tabele. Time se svako mjerenje može naknadno vezati "
        "za tačno određeno stanje sistema.")


# 7. REZULTATI
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
        "U ovoj razvojnoj evaluaciji fan postiže AUC 0,867 i standardizovani pAUC "
        "0,667, iznad postavljenog cilja AUC 0,80. Konfiguracija sa deset prozora "
        "daje 0,856 ± 0,024 na drugom skupu od 20 podjela. Razlika se ne može "
        "pripisati isključivo broju kalibracionih prozora jer protokoli nisu "
        "identični. Rasipanje preko podjela mjeri osjetljivost na izbor "
        "kalibracije; podjele ponovo koriste iste snimke i nisu nezavisni fizički "
        "eksperimenti.", uvlaka=False)

    r.naslov("Mjerenje na uređaju preko zvučnika", 2)
    r.pasus(
        "Prije mjerenja fizičkog ventilatora izvedene su probe reprodukcijom DCASE "
        "snimaka preko zvučnika. Dobijen je AUC oko 0,716, dok je razvojna "
        "digitalna evaluacija davala oko 0,864. Postavke nisu identične, pa razlika"
        " nije izolovana procjena greške mikrofona ili firmvera. Tabela 7.2 "
        "prikazuje zabilježene ocjene u dva puta signala.")
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
        "Dodatna proba koristila je sintetičku akustičku pobudu različite jačine. U"
        " toj postavci izraženiji alarmni odziv dobijen je približno na −15 dB, "
        "naspram ranijeg poređenja oko −30 dB. To su odnosi jačina u generisanoj "
        "pobudi, a ne fizička jačina kvara ili apsolutna osjetljivost u dB SPL. Bez"
        " kalibrisanog akustičkog izvora ne prenose se na druge mašine.")
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
        thesis_rows("paper"), desno={1, 2, 3, 4})
    r.pasus(
        "Medijane ocjena u tri bloka iznose 30 255, 62 344 i 19 844, naspram 1146 u"
        " normalnoj osnovi, nakon izostavljanja prelaznih prozora. U prva dva bloka"
        " tri od četiri prihvatljiva prozora imaju oznaku HOLD. Alarm je "
        "registrovan u trećem bloku, dok unaprijed zadati kriterij detekcije u sva "
        "tri bloka nije zadovoljen.", uvlaka=False)
    r.pasus(
        "GUIDED25 izvještaj ima ishod FAIL: detekcija je ostvarena u jednom od tri "
        "bloka, a alarm je prenesen u oporavak. Odbacivanje nestabilnih prozora "
        "odgovara implementiranoj logici, ali time nije ispunjen cilj eksperimenta."
        " Držanje papirića rukom je moguće objašnjenje nestabilnosti; bez "
        "nezavisnog mjerenja pobude nije potvrđen jedini uzrok. U skupu "
        "prihvatljivih prozora oporavak sadrži jedan alarmni prozor, uz prijavljenu"
        " medijanu oporavka 10,08 s.")
    r.pasus(
        "U označenim blokovima razgovora i vrata nema alarma. Medijane "
        "prihvatljivih prozora iznose 38 307 i 49 549. Sva četiri prozora razgovora"
        " i jedan od dva prozora vrata imaju HOLD oznaku. Ovi kratki blokovi "
        "pokazuju ponašanje u datoj postavci, ali ne procjenjuju opštu otpornost na"
        " buku. Slika 7.1 prikazuje sve DET prozore radi kontinuiteta, dok Tabela "
        "7.4 izostavlja prelazne i nepotvrđene prozore.")
    r.slika("slike/sl_run_papiric.png",
            "Trasa ocjene tokom mjerenja sa izazvanom promjenom protoka; "
            "označeni su prag ulaska, prag izlaska, nepouzdani prozori i "
            "alarmna epizoda")

    r.naslov("Mjerenje sa konstantnom promjenom", 3)
    r.pasus(
        "Drugo mjerenje koristi reprodukovani ton od 1 kHz. Kalibracija je "
        "prihvaćena bez izbacivanja isječaka, sa koeficijentom varijacije 0,43; "
        "pragovi iznose 21 810 i 10 905. U zapisima je uslov označen kao konstantan"
        " ton, ali postoje bilješke o promjeni jačine tokom probe. Tabela 7.5 zato "
        "opisuje označeni blok, a ne pobudu nezavisno izmjerene i stalne amplitude.")
    r.tabela(
        "Ocjene po označenim uslovima, mjerenje sa konstantnim tonom "
        "(prag ulaska 21 810)",
        ["Uslov", "Prozora", "Nepouzdanih", "Alarmnih", "Medijana", "Opseg"],
        thesis_rows("tone"), desno={1, 2, 3, 4})
    r.pasus(
        "Alarm se podiže kada se ostvare tri uzastopna pouzdana prekoračenja. To "
        "odgovara približno 30 s trajanja tri prozora, ali nije izmjerena latencija"
        " od prvog uključivanja tona. Događaj trajnog odstupanja nastaje na "
        "dvanaestom mjerenom alarmnom prozoru, uključujući prozor ulaska; HOLD "
        "pauzira taj brojač. Nema prijavljenih gubitaka uzoraka. Manifest sadrži "
        "125 istraživačkih prozora, odnosno 10 CAL i 115 DET prozora; ne sadrži "
        "obilježja cijelih DERIVE i VERIFY faza.", uvlaka=False)
    r.pasus(
        "Prvih devet prozora označenih tonom ostaje ispod ulaznog praga. Neki "
        "premašuju raniji opseg normalne osnove, pa se ne mogu opisati kao da su "
        "svi u tom opsegu. Kasnije ocjene rastu. Bez zapisa tačnog trenutka "
        "promjene jačine i kalibrisanog izvora ne može se izdvojiti odnos doze i "
        "odziva. Slika 7.2 prikazuje cijelu trasu, uključujući prelazne prozore.")
    r.slika("slike/sl_run_ton.png",
            "Trasa probe tonom: tri pouzdana prekoračenja za ulaz, dvanaesti mjereni "
            "alarmni prozor za trajno odstupanje")
    r.pasus(
        "Pred kraj zapisa ocjena pada sa približno 40 000 na 12 266–19 561, ispod "
        "ulaznog, ali iznad izlaznog praga. Alarm ostaje aktivan. Iz ovog pada se "
        "ne može odrediti tačno vrijeme gašenja izvora, a vrijeme završnog oporavka"
        " nije izmjereno.")

    r.naslov("Sažetak fizičkih mjerenja", 2)
    r.pasus(
        "Tabela 7.6 sažima oba validna mjerenja na ventilatoru, jedno "
        "pored drugog.", uvlaka=False)
    r.tabela(
        "Sažetak dva validna mjerenja na ventilatoru",
        ["Veličina", "Izazvana promjena protoka", "Ton od 1 kHz"],
        [
            ["Kalibracija", "prihvaćena poslije izbacivanja 2 isječka", "prihvaćena bez izbacivanja"],
            ["Koeficijent varijacije", "0,84 → 0,43", "0,43"],
            ["Prag ulaska / izlaska", "8 084 / 3 707", "21 810 / 10 905"],
            ["DET prozora ukupno / u metrici", "65 / 43", "115 / 99"],
            ["Alarmnih prozora / epizoda", "3 / 2", "64 / 2"],
            ["Medijana oporavka", "10,1 s", "nije izmjerena"],
            ["Izgubljenih uzoraka", "0", "0"],
            ["Trajno odstupanje prijavljeno", "ne", "da"],
        ])
    r.pasus(
        "Oznaka validnog fizičkog rezultata potvrđuje prihvatljivost zapisa za "
        "analizu. Ona nije isto što i prolaz kriterija eksperimenta: GUIDED25 proba"
        " sa papirićem ima ishod FAIL. Sažetak koristi 43 od 65 DET prozora prvog "
        "mjerenja i 99 od 115 drugog. HOLD prozori ostaju u tabeli kao odbijene "
        "odluke, a nisu naknadno uklonjeni radi boljih rezultata.", uvlaka=False)

    r.naslov("Provjere na računaru", 2)
    r.pasus(
        "Prošlo je 478 testova protokola, politika i poređenja sa C kodom, kao i "
        "provjera šeme konfiguracije. Ove provjere ne zamjenjuju fizičku "
        "validaciju uređaja.")


# 8. DISKUSIJA
def _diskusija(r) -> None:
    r.naslov("Diskusija i ograničenja")
    r.pasus(
        "U ovom poglavlju rezultati se tumače, a zatim se navode ograničenja "
        "koja se ne smiju izostaviti pri njihovom čitanju.")

    r.naslov("Šta rezultati pokazuju", 2)
    r.pasus(
        "Mjerenja pokazuju da se statistički detektor sa učenjem lokalnog centra i "
        "praga može izvršavati na ESP32-S3. Postojeći zapisi potvrđuju odluke "
        "uređaja u dvije završne probe. Proba papirićem ipak ne zadovoljava sve "
        "kriterije, a poslije tona oporavak ostaje neizmjeren. Zato rezultat "
        "predstavlja funkcionalni prototip sa dokumentovanim ograničenjima.")
    r.pasus(
        "Prvi fizički test dobro razdvaja ocjene izazvane promjene i normalnog "
        "rada, ali 54 od 60 normalnih prozora prelazi tadašnji prag. Taj primjer "
        "razdvaja rangiranje od odluke pri fiksnom pragu. Kasnije promjene uvode "
        "odvojeno izvođenje i provjeru praga, histerezu, kapiju pouzdanosti i "
        "ograničeno odbacivanje kalibracionih isječaka. Dvije prihvaćene "
        "kalibracije ne potvrđuju da je problem pragova uopšteno riješen.")
    r.pasus(
        "Odbijanje robusnog praga tokom VERIFY faze pokazuje praktičnu ulogu "
        "odvojene provjere. Pravilo koje daje prihvatljiv fit na ranijem normalnom "
        "periodu može podbaciti na kasnijem. Taj rezultat podržava zadržavanje "
        "provjere, ali ne dokazuje da prolaz kratkog VERIFY perioda garantuje "
        "dugoročnu pouzdanost.")

    r.naslov("Poređenje sa postojećim radovima", 2)
    r.pasus(
        "Referentni radovi [1]–[3] daju postavku zadatka, podatke i poređenja "
        "algoritama. Ovaj rad dodaje opis lokalnog učenja i provjere praga na "
        "mikrokontroleru. Brojke nisu direktno uporedive sa službenim rang-listama "
        "zbog drugačijih kalibracionih podjela, izabranog tipa mašine i korišćenja "
        "razvojnog skupa.")
    r.pasus(
        "Praktični doprinos je u povezivanju izračunavanja obilježja sa kontrolom "
        "kvaliteta, kalibracijom i zapisom odluka. Pregled literature u ovom radu "
        "nije sistematski pregled svih ugrađenih ASD sistema i ne uspostavlja "
        "prvenstvo takve arhitekture.")

    r.naslov("Ograničenja", 2)
    r.pasus(
        "Obim izvedenih mjerenja ograničava sljedeće zaključke:")
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
        "**Mali uzorci.** Pojedini blokovi imaju samo dva do pet prihvatljivih "
        "prozora. Njihove deskriptivne statistike predstavljaju kratku funkcionalnu"
        " provjeru. Intervali povjerenja za dugoročnu detekciju nisu procijenjeni.",
        "**Stopa lažnih uzbuna nije procijenjena dugoročno.** Odsustvo alarma "
        "tokom nekoliko desetina minuta normalnog rada nije dokaz male "
        "dugoročne stope; jednostrana gornja granica pri takvom trajanju "
        "mjerenja ostaje visoka.",
        "**Vrijeme oporavka poslije jakog izvora promjene nije izmjereno**, "
        "jer je mjerenje završeno dok je ocjena još bila između praga izlaska "
        "i praga ulaska.",
        "**Osjetljivost provjere kalibracije.** U analiziranim zapisima odstupanje "
        "uske trake za približno 0,7 jedinica logaritamskog obilježja prati veliki "
        "porast ocjene. To nije izmjeren opšti prag osjetljivosti. Odbacivanje "
        "najviše dva isječka ublažava problem u jednoj sesiji, bez dokaza da "
        "uklanja njegov uzrok.",
        "**Razvojni izbor politike.** Pragovi i centri fitovani su iz normalnih "
        "podataka. Ipak, tokom razvoja su pregledani ishodi ranijih anomalnih i "
        "fizičkih proba, pa zabrana anomalija u fitu nije dokaz da je cijeli izbor "
        "politike bio nezavisan od tih ishoda. Politika ostaje DEVELOPMENT i nema "
        "potvrđenu dugoročnu stopu lažnih alarma.",
    ])

    r.naslov("Šta nije provjereno na hardveru", 2)
    r.pasus(
        "Na hardveru nisu potvrđeni potpuno samostalan interfejs sa tasterom i "
        "diodama, kontrolisani prekid I2S veze, ponašanje pri gubitku napajanja i "
        "potrošnja cijelog lanca. NVS modul postoji, ali razvojna politika ne "
        "dozvoljava čuvanje i vraćanje profila: poslije restarta potrebno je novo "
        "učenje. Ove stavke ostaju ograničenja rada, bez pretpostavke da će dodatna"
        " mjerenja biti izvedena.")


# 9. ZAKLJUČAK
def _zakljucak(r) -> None:
    r.naslov("Zaključak")
    r.pasus(
        "Realizovan je prototip detektora akustičkih odstupanja ventilatora na "
        "ESP32-S3 sa jednim MEMS mikrofonom. Globalni statistički model izveden je "
        "iz 990 normalnih snimaka, dok uređaj uči lokalni centar i pragove. Završni"
        " vođeni postupak od komande za početak do nadzora traje oko 13,57 min u "
        "obje zabilježene sesije.")
    r.pasus(
        "Razvojni cilj AUC 0,80 premašen je konfiguracijom sa deset kalibracionih "
        "prozora (0,856), dok odvojena referenca sa dvadeset prozora daje 0,867. "
        "Fizička proba tonom potvrđuje alarm i trajno odstupanje. Proba papirićem "
        "detektuje jedan od tri bloka i ima ishod FAIL. Obrada obilježja i ocjene "
        "traje oko 716 ms po prozoru; u završnim zapisima nema prijavljenih "
        "gubitaka uzoraka. Ovi nalazi ne potvrđuju dijagnozu kvara, ponovljivost "
        "kalibracije ili dugoročnu stopu lažnih alarma.")
    r.pasus(
        "Razvoj je obuhvatio promjene modela i pravila odlučivanja. Bolje "
        "rangiranje ocjena nije bilo dovoljno za upotrebljiv prag na uređaju. "
        "Zasebno izvođenje i provjera praga omogućili su prihvatanje dvije završne "
        "sesije, ali ograničenja kapije pouzdanosti i oporavka i dalje ostaju.")
    r.pasus(
        "Prikazani su i negativni ili nedovoljno uvjerljivi rezultati alternativnih"
        " obilježja i vremenskih pravila. Posebno je značajno odbijanje robusnog "
        "praga tokom zasebnog normalnog VERIFY perioda. Ti nalazi objašnjavaju "
        "izbor konačne konfiguracije, ali ne dokazuju da su odbačeni postupci "
        "neupotrebljivi u drugim postavkama.")

    r.naslov("Pravci daljeg rada", 2)
    r.pasus("Iz izmjerenih ograničenja proizlaze sljedeći pravci:", uvlaka=False)
    r.stavke([
        "**Nezavisne postavke.** Drugi primjerci ventilatora i druga akustička "
        "okruženja potrebni su za procjenu generalizacije izvan postojeće postavke.",
        "**Duže normalno mjerenje.** Stopa lažnih uzbuna traži red veličine "
        "duže mjerenje od dosadašnjih da bi se mogla procijeniti sa smislenim "
        "intervalom.",
        "**Izbor obilježja po tipu mašine.** Izmjereno je da se izbor može "
        "napraviti samo iz izvornog domena, bez ijedne ciljne oznake, i da "
        "takav izbor nadmašuje bilo koji fiksni.",
        "**Spektralne trake i kovarijansa.** Osam najnižih traka ne sadrži FFT "
        "tačku, pa fiksna logaritamska donja granica narušava potpunu nezavisnost "
        "od pojačanja. Vrijedi odvojeno ispitati spajanje praznih traka i "
        "ograničavanje uticaja slabo varijabilnih komponenti. Svaka takva izmjena "
        "traži novi model i novu provjeru.",
        "**Trajno čuvanje naučenog profila.** Modul za upis u trajnu memoriju "
        "je realizovan i provjeren na računaru, ali se u razvojnoj "
        "konfiguraciji namjerno ne koristi dok politika ne bude zamrznuta.",
        "**Mjerenje potrošnje i rad na bateriji**, kao uslov za primjenu na "
        "mjestima bez stalnog napajanja.",
    ])


# literatura, biografija, prilozi
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
        "Espressif Systems, *ESP32-S3-WROOM-1 & ESP32-S3-WROOM-1U Datasheet*, v1.8."
        " Dostupno: "
        "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf"
        " (pristupljeno 6. septembra 2026).",
        "Espressif Systems, *ESP-IDF Programming Guide v5.5, ESP32-S3*. Dostupno: "
        "https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32s3/ (pristupljeno"
        " 6. septembra 2026).",
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
