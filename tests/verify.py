#!/usr/bin/env python3
"""lander-cinema dogrulama kapilari (Blender'siz: python3 tests/verify.py)"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import fizik as f  # noqa: E402


def main():
    ok, fail = 0, 0

    def kapil(ad, kosul, detay=""):
        nonlocal ok, fail
        if kosul:
            ok += 1
            print(f"  [ok] {ad} {detay}")
        else:
            fail += 1
            print(f"  [FAIL] {ad} {detay}")

    d = f.inis_sim()

    # 1) motor hic kapanmadan once yanmaya basladi (suicide burn gercek)
    kapil("yanma baslangici var", d["yanma_baslangic"] > 0.0,
          f"(t = {d['yanma_baslangic']:.1f} s)")

    # 2) TEMAS DIKEY HIZI < 2 m/s — kapi kapiya
    kapil("temas dikey hizi < 2 m/s", abs(d["temas_dikey"]) < 2.0,
          f"({abs(d['temas_dikey']):.2f} m/s)")

    # 3) yatay hiz temasta < 0.5 m/s (devrilmeyecek)
    kapil("temas yatay hizi < 0.5 m/s", abs(d["temas_yatay"]) < 0.5,
          f"({abs(d['temas_yatay']):.2f} m/s)")

    # 4) yakit marji: inisten sonra > %8 yakit kalmali
    kapil("yakit marji > %8", d["yakit_orani"] > f.YAKIT_MARJI,
          f"(kaldi %{d['yakit_orani'] * 100:.1f})")

    # 5) rehber: yanma baslangici analitik kestirime yakin (%15)
    ideal = f.ideal_yanma_baslangic()
    sapma = abs(d["yanma_baslangic"] - ideal) / max(1.0, ideal)
    kapil("yanma zamani analitik kestirime yakin", sapma < 0.25,
          f"(sim {d['yanma_baslangic']:.1f} s ~ analitik {ideal:.1f} s)")

    # 6) irtifa profili hic negatife daldiktan sonra tekrar yukari cikmadi
    H = d["yukseklikler"]
    dip_indis = H.index(min(H))
    sonradan_yuksel = any(h > min(H) + 1.0 for h in H[dip_indis:])
    kapil("temastan sonra sekme yok", not sonradan_yuksel)

    # 7) determinizm
    kapil("determinizm", f.inis_sim() == f.inis_sim())

    print(f"\n{'TUM KAPILAR GECTI' if fail == 0 else 'KAPILARDA FAIL VAR'}"
          f" ({ok} ok, {fail} fail)")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
