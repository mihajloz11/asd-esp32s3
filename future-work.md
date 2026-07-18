# Future work — ideje idu OVDJE, ne u kod (pravilo E4 iz plana)

- [ ] QAT ako PTQ degradira >5 p.p. na nekoj mašini (fallback A3)
- [ ] Depthwise-conv AE na log-mel slici (OutlierNets stil, <10 KB)
- [ ] Dvokanalni noise-aware pristup (DCASE 2026 blizu/daleko parovi)
- [ ] Majority-vote preko N klipova (ubija pitanje F3 na odbrani)
- [ ] esp-dsp `dsps_fft2r_fc32` umjesto portabilnog FFT-a (uz re-run PC↔C testa)
- [ ] On-device Mahalanobis (Welford, dijagonalna kovarijansa)
- [ ] Demo mod: telefon kao mikrofon preko Wi-Fi (S3 SoftAP + HTML stranica sa
      getUserMedia -> WebSocket PCM -> ring buffer). SAMO za demo/odbranu —
      telefonski AGC/NS boji signal, ne valja za eksperimente; Wi-Fi kvari E5.
      ~1 dan posla, raditi u septembru uz pripremu odbrane (fallback za rizik F1)
- [ ] Publikacija: ETRAN/TELFOR/MECO poslije odbrane
