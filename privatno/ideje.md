# Future work — ideje idu OVDJE, ne u kod (pravilo E4 iz plana)

> Otpornost na buku okoline (koraci, razgovor) ima **svoj plan** sa izmjerenim
> polazištem i eksperimentom koji odlučuje šta vrijedi ugraditi:
> [docs/plan-otpornost-na-buku.md](../docs/model/plan-otpornost-na-buku.md).
> Tamo je i nalaz da su DCASE 2026 snimci **dvokanalni**, a da obrada koristi
> samo prvi kanal — pa se dvomikrofonski pristup može isprobati bez novog hardvera.

Već zatvoreno i zato više nije na listi otvorenih ideja: Mahalanobis score i
lokalni centar rade na uređaju, a alarm koristi zaključanu temporalnu politiku
`hysteresis_1.0_0.7_n3`. To ne znači da su stvarni govor, vrata ili fizički
ventilator već testirani.

- [ ] QAT ako PTQ degradira >5 p.p. na nekoj mašini (fallback A3)
- [ ] Depthwise-conv AE na log-mel slici (OutlierNets stil, <10 KB)
- [ ] Dvokanalni noise-aware pristup (DCASE 2026 blizu/daleko parovi)
- [ ] esp-dsp `dsps_fft2r_fc32` umjesto portabilnog FFT-a (uz re-run PC↔C testa)
- [ ] Demo mod: telefon kao mikrofon preko Wi-Fi (S3 SoftAP + HTML stranica sa
      getUserMedia -> WebSocket PCM -> ring buffer). SAMO za demo/odbranu —
      telefonski AGC/NS boji signal, ne valja za eksperimente; Wi-Fi kvari E5.
      ~1 dan posla, raditi u septembru uz pripremu odbrane (fallback za rizik F1)
- [ ] ON-DEVICE LIVE DASHBOARD (za odbranu, septembar) — S3 digne SoftAP
      ("ASD-demo") + HTTP server sa jednom stranicom; WebSocket push ~2x/s:
      {score, prag, normal/anomalija, feat_ms, inf_ms, arena_used, heap,
      zadnjih 128 log-mel vrijednosti za mini-spektrogram}. Stranica: veliki
      status (zeleno/crveno), rolling graf score-a vs prag, spektrogram na
      <canvas>. Sve staticki iz flasha, bez CDN-a. IDF komponente:
      esp_wifi (AP) + esp_http_server (ima ugradjen WebSocket). ~2 dana posla.
      PRAVILO: Wi-Fi ukljucen SAMO u demo modu (taster), nikad tokom E4/E5
      mjerenja — dokumentovati u radu da demo build != mjerni build.
- [ ] Publikacija: ETRAN/TELFOR/MECO poslije odbrane
