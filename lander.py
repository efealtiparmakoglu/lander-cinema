#!/usr/bin/env python3
"""lander-cinema — Ay aracı (Blender icinde).

Yerlesim: origin = iniş ayakları zemini, +Z yukarı.
    iniş kademsi : z 0.9 .. 3.6 (sekizgen govde, altin folyo)
    motor        : z 0.25..0.9 (merkez nozul, gimbal)
    iniş ayaklari: 4 adet egik strut + tabla (z 0)
    üst kademe   : z 3.6 .. 5.4 (kabin, pencereler, anten, dokusma portu)

Fonksiyonel: gimbal_pozu + rcs_pozu (kuyruk jetleri) + motor_paleti.
"""

import math

import bpy
from mathutils import Vector

MAT = {}


def mat_yap(ad, renk, rough=0.5, metalik=0.0, emissive=None):
    if ad in MAT:
        return MAT[ad]
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (renk[0], renk[1], renk[2], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metalik
    if emissive is not None:
        nt.nodes.remove(b)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (renk[0], renk[1], renk[2], 1)
        em.inputs["Strength"].default_value = emissive
        outn = nt.nodes.get("Material Output")
        nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    MAT[ad] = m
    return m


def kutu(ad, merkez, boyut, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=merkez)
    o = bpy.context.active_object
    o.name = ad
    o.scale = boyut
    o.rotation_euler = rot
    o.data.materials.append(mat)
    return o


def silindir(ad, merkez, r1, r2, derinlik, mat, vert=8):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=derinlik,
                                    location=merkez, vertices=vert)
    o = bpy.context.active_object
    o.name = ad
    o.data.materials.append(mat)
    return o


def kure(ad, merkez, r, mat, seg=20, halka=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg,
                                         ring_count=halka, location=merkez)
    o = bpy.context.active_object
    o.name = ad
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def cubuk(ad, p0, p1, kalinlik, mat):
    d = Vector(p1) - Vector(p0)
    bpy.ops.mesh.primitive_cylinder_add(radius=kalinlik, depth=1.0,
                                        location=tuple((Vector(p0) + Vector(p1)) / 2),
                                        vertices=12)
    o = bpy.context.active_object
    o.name = ad
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.scale = (1, 1, d.length)
    o.data.materials.append(mat)
    return o


def kur():
    """Ay aracini kurar; poz referanslarini dondurur."""
    MAT.clear()
    altin = mat_yap("FolyoAltin", (0.78, 0.55, 0.12), rough=0.35, metalik=1.0)
    gri = mat_yap("GovdeGri", (0.45, 0.45, 0.47), rough=0.45, metalik=0.5)
    koyu = mat_yap("KoyuPanel", (0.10, 0.10, 0.11), rough=0.6)
    siyah = mat_yap("SiyahIzgara", (0.04, 0.04, 0.045), rough=0.7)
    bakir = mat_yap("NozulBakir", (0.40, 0.24, 0.13), rough=0.3, metalik=0.9)
    cam = mat_yap("KabinCam", (0.55, 0.70, 0.85), rough=0.05, metalik=0.2)
    beyaz = mat_yap("BeyazPanel", (0.75, 0.75, 0.76), rough=0.5)

    kok = bpy.data.objects.new("Lander", None)
    bpy.context.collection.objects.link(kok)
    once = set(bpy.data.objects)
    refs = {"kok": kok, "gimbal": None, "alev": None, "isik": None,
            "rcs": [], "ust_kademe": []}

    # ---------------- iniş kademesi (sekizgen, altin folyo)
    silindir("InisGovde", (0, 0, 2.2), 1.75, 1.75, 2.0, altin, vert=8)
    silindir("InisGovde2", (0, 0, 3.2), 1.75, 1.75, 1.0, altin, vert=8)
    # folyo bantlari: farkli ton halkalar
    for i, z in enumerate((1.5, 2.0, 2.9, 3.4)):
        silindir(f"FolyoBand{i}", (0, 0, z), 1.78, 1.78, 0.16,
                 mat_yap(f"Folyo{i}", (0.6 - i * 0.05, 0.42, 0.10),
                         rough=0.4, metalik=1.0), vert=8)
    # yakit tanklari (yan kapsuller)
    for i, (dx, dy) in enumerate(((1.35, 0), (-1.35, 0), (0, 1.35), (0, -1.35))):
        t = kure(f"Tank{i}", (dx, dy, 2.2), 0.62, gri, seg=16, halka=10)
        t.scale = (1.0, 1.0, 1.25)

    # ---------------- motor + gimbal
    pivot = bpy.data.objects.new("GimbalPivot", None)
    pivot.location = (0, 0, 1.0)
    bpy.context.collection.objects.link(pivot)
    nozul = silindir("Nozul", (0, 0, -0.38), 0.52, 0.18, 0.95, bakir, vert=20)
    nozul.parent = pivot
    refs["gimbal"] = pivot

    alev_m = mat_yap("Alev", (1.0, 0.6, 0.2), emissive=1.2)
    alev = silindir("AlevKoni", (0, 0, -0.75), 0.25, 0.5, 1.1, alev_m, vert=20)
    alev.parent = pivot
    refs["alev"] = alev
    isik_d = bpy.data.lights.new("MotorIsik", "POINT")
    isik_d.energy = 1200
    isik_d.color = (1.0, 0.55, 0.2)
    isik = bpy.data.objects.new("MotorIsik", isik_d)
    isik.location = (0, 0, -0.5)
    bpy.context.collection.objects.link(isik)
    isik.parent = pivot
    refs["isik"] = isik

    # ---------------- iniş ayaklari (4 adet)
    for i in range(4):
        aci = math.pi / 4 + i * math.pi / 2
        dx, dy = math.cos(aci) * 1.9, math.sin(aci) * 1.9
        cubuk(f"StrutAna{i}", (math.cos(aci) * 1.1, math.sin(aci) * 1.1, 1.6),
              (dx, dy, 0.12), 0.07, gri)
        cubuk(f"StrutYardimci{i}",
              (math.cos(aci + 0.5) * 1.2, math.sin(aci + 0.5) * 1.2, 1.4),
              (dx, dy, 0.12), 0.05, gri)
        kutu(f"AyakTabla{i}", (dx, dy, 0.06), (0.62, 0.62, 0.12), gri)

    # ---------------- üst kademe (kabin)
    kutu("Kabin", (0, 0, 4.35), (2.2, 2.0, 1.5), koyu)
    kutu("KabinOn", (0.9, 0, 4.35), (0.5, 1.7, 1.3), gri)
    # öne bakan pencere (üçgen hissi: eğik kutu)
    pencere = kutu("Pencere", (1.12, 0.45, 4.6), (0.06, 0.55, 0.5), cam)
    pencere.rotation_euler = (0, math.radians(-16), 0)
    pencere2 = kutu("Pencere2", (1.12, -0.45, 4.6), (0.06, 0.55, 0.5), cam)
    pencere2.rotation_euler = (0, math.radians(-16), 0)
    # dokusma portu (uste)
    silindir("DokusmaPortu", (0, 0, 5.35), 0.5, 0.5, 0.5, koyu, vert=16)
    # anten canaği
    cubuk("AntenDirek", (-0.6, 0, 5.1), (-0.6, 0, 6.0), 0.03, gri)
    kure("AntenCanagi", (-0.6, 0, 6.1), 0.22, beyaz, seg=16, halka=10)
    # RCS kuyruk jetleri (4 köşe, yatay)
    for i in range(4):
        aci = math.pi / 4 + i * math.pi / 2
        dx, dy = math.cos(aci) * 1.15, math.sin(aci) * 1.15
        j = silindir(f"RCS{i}", (dx, dy, 3.95), 0.06, 0.13, 0.22, gri, vert=8)
        j.rotation_euler = (0, math.pi / 2, aci)
        refs["rcs"].append(j)

    # parent
    for o in set(bpy.data.objects) - once:
        if o is not kok and o.parent is None:
            o.parent = kok
    refs["ust_kademe"] = [bpy.data.objects[n] for n in
                          ("Kabin", "KabinOn", "Pencere", "Pencere2",
                           "DokusmaPortu", "AntenDirek", "AntenCanagi")
                          if n in bpy.data.objects]
    return refs


def gimbal_pozu(refs, aci_deg, yon_deg=0.0):
    refs["gimbal"].rotation_euler = (0, math.radians(aci_deg),
                                     math.radians(yon_deg))


def motor_pozu(refs, throttle, t):
    """Palet ve isik throttle'la; hafif titreme."""
    refs["alev"].scale = (1, 1, max(0.05, throttle / 0.6) *
                          (1.0 + 0.1 * math.sin(t * 43.0)))
    refs["isik"].data.energy = 1200 * throttle / 0.6


def rcs_pozu(refs, t, aktif_araliklar=((1.0, 1.35), (5.0, 5.2))):
    """RCS jetleri: aktif araliklarda emissive patlamalar."""
    aktif = any(a <= t <= b for (a, b) in aktif_araliklar)
    m = MAT.get("RcsAlev")
    if m is None:
        m = mat_yap("RcsAlev", (0.8, 0.9, 1.0), emissive=6.0)
    for j in refs["rcs"]:
        j.data.materials.clear()
        j.data.materials.append(m if aktif else MAT["GovdeGri"])
