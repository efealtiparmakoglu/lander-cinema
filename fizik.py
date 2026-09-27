#!/usr/bin/env python3
"""lander-cinema — Ay'a güçlü iniş fiziği (SAF MATEMATIK, Blender'siz).

Klasik suicide burn problemi: arac yukarıda, asagi iniyor, motoru NE ZAMAN
atesleyecegini bilmek zorundasin. Erken atarsan yakit yere degmeden biter,
gec atarsan arac yerle bir olur.

Model (1B dikey + 1B yatay, Ay g = 1.62):
    itki     : F(throttle), throttle ∈ [0.10, 0.60]  (motor min %10 — kapanmaz)
    kutle    : m(t) = kuru + yukit - mdot(throttle) * t
    dikey    : a = F*cos(tilt)/m - g
    yatay    : a = F*sin(tilt)/m  (tilt yatay hizi iptal edecek yonde)
    rehber   : v_profile(h) = sqrt(v_hedef^2 + 2 * a_net * h)
               v > profile -> gaz max, degilse min (bang-bang)
"""

import math

G_AY = 1.62
M_KURU = 2300.0
M_YAKIT = 2400.0
F_MAX = 35000.0            # N
THROTTLE_MIN = 0.10
THROTTLE_MAX = 0.60
VE = 3050.0                # egzoz hizi (m/s)
H_BASLANGIC = 500.0        # m
V_BASLANGIC = -25.0        # m/s (duserken)
U_BASLANGIC = 15.0         # m/s yatay surat
V_TOUCHDOWN_HEDEF = 1.0    # m/s
TILT_MAX_DEG = 25.0
YAKIT_MARJI = 0.08


def mdot(throttle):
    """Yakit akisi: mdot = F / ve."""
    return (F_MAX * throttle) / VE


def a_maks(throttle_max=THROTTLE_MAX, m=None):
    """Tam gazda dikey ivme (tam yukte)."""
    m = m if m is not None else (M_KURU + M_YAKIT)
    return (F_MAX * throttle_max) / m - G_AY


def durus_yuksekligi(v):
    """v hizini V_TOUCHDOWN_HEDEF'e indirmek icin gereken ideal yukseklik.
    a_net sabit varsayimiyla analitik: (v^2 - vt^2) / (2 * a_net)."""
    a_net = a_maks(m=M_KURU + M_YAKIT)
    return (v * v - V_TOUCHDOWN_HEDEF ** 2) / (2.0 * a_net)


def tilt_icin(u, v_dikey_pay):
    """Yatay hizi killemek icin egim acisi (radyan) — sinirlidir."""
    if v_dikey_pay <= 0:
        return 0.0
    oran = u / (v_dikey_pay * 1.6 + 1e-6)
    return max(-math.radians(TILT_MAX_DEG), min(math.radians(TILT_MAX_DEG), oran))


def inis_sim(dt=0.005, t_max=400.0):
    """Bang-bang rehberli guclu inis.
    Doner: sozluk — zamanlar, yukseklikler, dikey/yatay hizlar, throttle'lar,
    yakit_orani, temasta_dikey, temasta_yatay, yakit_kaldi, yanma_baslangic.
    """
    t = 0.0
    h = H_BASLANGIC
    v = V_BASLANGIC
    u = U_BASLANGIC
    yakit = M_YAKIT
    m = M_KURU + yakit

    T, H, Vz, Uz, THR = [0.0], [h], [v], [u], [0.0]
    yanma = None
    temas = None

    while t < t_max:
        # rehber: profil hizini asiyorsak tam gaz
        profil = math.sqrt(V_TOUCHDOWN_HEDEF ** 2 +
                           2.0 * max(0.4, a_maks(m=m)) * 0.85 * max(0.0, h))
        gerekiyor = v < -profil
        if gerekiyor and yanma is None:
            yanma = t
        throttle = THROTTLE_MAX if gerekiyor else THROTTLE_MIN

        # yakit bitti -> motor ne yaparsa yapsin
        if yakit <= 0.0:
            throttle = 0.0

        F = F_MAX * throttle
        tilt = tilt_icin(u, abs(v)) if throttle > THROTTLE_MIN else 0.0

        a_z = F * math.cos(tilt) / m - G_AY
        a_u = -(F * math.sin(tilt) / m) * (1.0 if u > 0 else -1.0)

        v += a_z * dt
        u += a_u * dt if u != 0.0 else 0.0
        h += v * dt
        yakit -= mdot(throttle) * dt
        m = M_KURU + max(0.0, yakit)
        t += dt

        T.append(t)
        H.append(max(0.0, h))
        Vz.append(v)
        Uz.append(u)
        THR.append(throttle)

        if h <= 0.0:
            temas = t
            break

    i = len(T) - 1
    return {
        "zamanlar": T, "yukseklikler": H, "dikey": Vz, "yatay": Uz,
        "throttle": THR,
        "temas_t": temas if temas is not None else T[-1],
        "temas_dikey": Vz[i], "temas_yatay": Uz[i],
        "yakit_orani": max(0.0, yakit / M_YAKIT),
        "yanma_baslangic": yanma if yanma is not None else -1.0,
        "uygun_yanma_baslangic": H_BASLANGIC and durus_yuksekligi(V_BASLANGIC),
    }


def ideal_yanma_baslangic():
    """Analitik kestirim: durus yuksekligi = irtifa oldugu anda yan."""
    # sabit a_net ile dusus: h(t) = h0 - |v0| t - g t^2 / 2
    # durus_yuksekligi(v(t)) = h(t) denkleminin en kucuk kokunu coz
    v0 = abs(V_BASLANGIC)
    a_net = a_maks(m=M_KURU + M_YAKIT)
    lo, hi = 0.0, 60.0
    for _ in range(80):
        mid = (lo + hi) / 2
        h_t = H_BASLANGIC - v0 * mid - G_AY * mid * mid / 2
        v_t = v0 + G_AY * mid
        durus = durus_yuksekligi(v_t)
        if durus > h_t:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
