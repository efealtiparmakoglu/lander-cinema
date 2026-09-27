#!/usr/bin/env python3
# Blender icinde: blender --background --python lander_render.py -- --scene scenes/studyo.json [--gif 36]
"""lander-cinema — stüdyo render (uzay: siyah gök + tek sert güneş)."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

import bpy
from mathutils import Vector

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)

import lander  # noqa: E402


def kamera_kur(konum, hedef, lens=50):
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    co = bpy.data.objects.new("kamera", cam)
    bpy.context.collection.objects.link(co)
    co.location = konum
    yon = Vector(hedef) - Vector(konum)
    co.rotation_euler = yon.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co
    return co


def sahne_kur(cfg):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("  [uyari] GPU:", e)
    sc.cycles.samples = cfg["render"].get("samples", 128)
    sc.cycles.use_denoising = True
    sc.render.resolution_x = cfg["render"].get("width", 1600)
    sc.render.resolution_y = cfg["render"].get("height", 900)
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.exposure = cfg["render"].get("exposure", 0.0)
    look = cfg["render"].get("look")
    if look:
        try:
            sc.view_settings.look = look
        except Exception:
            pass

    # UZAY: siyah gök + tek sert güneş (atmosfer yok — yumuşama yok)
    dunya = bpy.data.worlds.new("Uzay")
    sc.world = dunya
    dunya.use_nodes = True
    nt = dunya.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.002, 0.002, 0.003, 1)
    bg.inputs["Strength"].default_value = 1.0
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])

    s = cfg["sun"]
    sd = bpy.data.lights.new("Gunes", "SUN")
    sd.energy = s.get("strength", 6.0)
    sd.angle = math.radians(0.6)      # ayda güneş daha küçük: daha sert
    sd.color = (1.0, 0.97, 0.92)
    so = bpy.data.objects.new("Gunes", sd)
    bpy.context.collection.objects.link(so)
    el = math.radians(s.get("elevation_deg", 30))
    az = math.radians(s.get("azimuth_deg", 160))
    yon = Vector((math.cos(el) * math.sin(az),
                  -math.cos(el) * math.cos(az),
                  math.sin(el)))
    so.rotation_euler = yon.to_track_quat("Z", "Y").to_euler()
    return sc


def zemin_kur(cfg):
    m = bpy.data.materials.new("Regolit")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    z = cfg.get("zemin", {})
    renk = z.get("color", (0.16, 0.155, 0.14))
    b.inputs["Base Color"].default_value = (*renk, 1)
    b.inputs["Roughness"].default_value = z.get("roughness", 0.95)
    bpy.ops.mesh.primitive_plane_add(size=z.get("boyut", 60), location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = "Regolit"
    o.data.materials.append(m)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--gif", type=int, default=0)
    ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args(args)

    cfg = json.load(open(a.scene, encoding="utf-8"))
    if os.environ.get("HIZLI") == "1":
        cfg["render"] = {**cfg.get("render", {}), "width": 800, "height": 450,
                         "samples": 32}
        cfg["output"] = "/tmp/onizleme_lander_" + os.path.basename(a.scene).replace(".json", ".png")
        print("  [HIZLI] onizleme ->", cfg["output"])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = sahne_kur(cfg)
    zemin_kur(cfg)

    refs = lander.kur()
    lander.gimbal_pozu(refs, cfg.get("gimbal", 0.0))
    lander.motor_pozu(refs, cfg.get("throttle", 0.0), 0.0)

    cam_cfg = cfg["camera"]
    cam_obj = kamera_kur(cam_cfg["position"], cam_cfg["look_at"],
                         cam_cfg.get("lens", 50))

    if a.gif:
        cfg["render"] = {**cfg.get("render", {}), "width": 1280, "height": 720,
                         "samples": 48}
        out = os.path.splitext(cfg["output"])[0] + ".gif"
    else:
        out = cfg["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    if not a.gif:
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"== BİTTİ -> {out}")
        return

    tmp = out + ".frames"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for f in range(a.gif):
        t = f / a.fps
        thr = cfg.get("gimbal_throttle", 0.35) * \
            (0.75 + 0.25 * math.sin(t * 2.0))
        lander.gimbal_pozu(refs, cfg.get("gimbal_genlik", 4.0) *
                           math.sin(t * 1.8))
        lander.motor_pozu(refs, thr, t)
        lander.rcs_pozu(refs, t, aktif_araliklar=((1.0, 1.6), (2.6, 3.0)))
        sc.render.filepath = f"{tmp}/f{f:05d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"  kare {f + 1}/{a.gif}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png",
                    "-vf", "palettegen=max_colors=256:stats_mode=diff",
                    f"{tmp}/pal.png"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png", "-i", f"{tmp}/pal.png",
                    "-lavfi", "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                    "-loop", "0", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"== BİTTİ -> {out}")


if __name__ == "__main__":
    main()
