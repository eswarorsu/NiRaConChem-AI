"""Hero scene: a concrete villa on a UAE desert plain at dusk (Belt of Venus sky).

Renders two aligned layers from one camera so the page can parallax them:
  plate   – sky, mountains, dunes, sand plain (no building)
  cutout  – the villa + its palms, over a shadow catcher, transparent film
Also writes hotspot screen positions (0–1, top-left origin) for the page.

usage: python3 hero.py <plate|cutout|both> <width> <samples> <outdir>
"""
import json
import math
import os
import random
import sys

import bpy  # must precede bmesh/mathutils when running as a module
import bmesh
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
from common import (add_bump, add_fog, box, color_variation, extrude_polygon, link, look_at,
                    mesh_from_bmesh, polyline_samples, principled, reset_scene, rounded_rect_points, srgb)

MODE = sys.argv[1] if len(sys.argv) > 1 else "both"
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 960
SAMPLES = int(sys.argv[3]) if len(sys.argv) > 3 else 24
OUT = sys.argv[4] if len(sys.argv) > 4 else "/root/renders"
os.makedirs(OUT, exist_ok=True)

random.seed(7)
FOG = "#E4D3CA"  # horizon haze the far terrain dissolves into

scene = reset_scene()
scene.render.resolution_x = WIDTH
scene.render.resolution_y = round(WIDTH * 9 / 16)
scene.cycles.samples = SAMPLES

# --------------------------------------------------------------------------- world
world = bpy.data.worlds.new("dusk")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
bg = wn.get("Background")
coord = wn.new("ShaderNodeTexCoord")
sep = wn.new("ShaderNodeSeparateXYZ")
wl.new(coord.outputs["Generated"], sep.inputs["Vector"])
ramp = wn.new("ShaderNodeValToRGB")
stops = [
    (0.0, "#D2B9AC"),
    (0.5, "#F2D0BD"),   # horizon glow
    (0.515, "#F0CABF"), # Belt of Venus – the pink band
    (0.555, "#E9CBC4"),
    (0.6, "#DBC7C8"),
    (0.66, "#BDB8C2"),
    (0.74, "#A4A5B5"),
    (0.88, "#9296A9"),
    (1.0, "#8A8FA3"),
]
cr = ramp.color_ramp
cr.interpolation = "EASE"
cr.elements[0].position, cr.elements[0].color = stops[0][0], srgb(stops[0][1])
cr.elements[1].position, cr.elements[1].color = stops[-1][0], srgb(stops[-1][1])
for pos, col in stops[1:-1]:
    e = cr.elements.new(pos)
    e.color = srgb(col)
# Generated Z runs 0..1 from nadir to zenith; remap so the horizon sits at 0.5.
mz = wn.new("ShaderNodeMapRange")
mz.inputs["From Min"].default_value = -1.0
mz.inputs["From Max"].default_value = 1.0
# Generated coords for the world are the direction vector itself.
wl.new(sep.outputs["Z"], mz.inputs["Value"])
wl.new(mz.outputs["Result"], ramp.inputs["Fac"])

# Faint horizontal cloud streaks: noise stretched along X, masked to the sky.
streak_vec = wn.new("ShaderNodeMapping")
streak_vec.inputs["Scale"].default_value = (0.9, 6.0, 14.0)
wl.new(coord.outputs["Generated"], streak_vec.inputs["Vector"])
streak = wn.new("ShaderNodeTexNoise")
streak.inputs["Scale"].default_value = 2.2
streak.inputs["Detail"].default_value = 3.0
streak.inputs["Roughness"].default_value = 0.55
wl.new(streak_vec.outputs["Vector"], streak.inputs["Vector"])
sramp = wn.new("ShaderNodeMapRange")
sramp.inputs["From Min"].default_value = 0.55
sramp.inputs["From Max"].default_value = 0.8
sramp.inputs["To Max"].default_value = 0.10
wl.new(streak.outputs["Fac"], sramp.inputs["Value"])
mask = wn.new("ShaderNodeMapRange")  # only between ~5° and ~35° elevation
mask.inputs["From Min"].default_value = 0.05
mask.inputs["From Max"].default_value = 0.2
wl.new(sep.outputs["Z"], mask.inputs["Value"])
mul = wn.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
wl.new(sramp.outputs["Result"], mul.inputs[0])
wl.new(mask.outputs["Result"], mul.inputs[1])
cloudmix = wn.new("ShaderNodeMix")
cloudmix.data_type = "RGBA"
cloudmix.blend_type = "SCREEN"
wl.new(mul.outputs["Value"], cloudmix.inputs["Factor"])
wl.new(ramp.outputs["Color"], cloudmix.inputs[6])
cloudmix.inputs[7].default_value = srgb("#FFF1EA")
wl.new(cloudmix.outputs[2], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

# --------------------------------------------------------------------------- sun
sun_data = bpy.data.lights.new("sun", "SUN")
sun_data.energy = 4.4
sun_data.color = srgb("#FFBE94")[:3]
sun_data.angle = math.radians(2.5)
sun = link(bpy.data.objects.new("sun", sun_data))
sun_dir = Vector((0.62, 1.0, -0.13)).normalized()  # from behind-left of camera
sun.rotation_euler = sun_dir.to_track_quat("-Z", "Y").to_euler()

# --------------------------------------------------------------------------- camera
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 35
cam_data.sensor_width = 36
cam_data.clip_end = 5000
cam = link(bpy.data.objects.new("cam", cam_data))
cam.location = (0.0, 0.0, 1.25)
cam.rotation_euler = (math.radians(90 + 6.6), 0.0, 0.0)
scene.camera = cam

# --------------------------------------------------------------------------- terrain
def heightfield(name, xs, ys, fn, mat):
    X, Y = np.meshgrid(xs, ys)
    Z = np.vectorize(fn)(X, Y)
    nx, ny = len(xs), len(ys)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1).tolist()
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    obj = link(bpy.data.objects.new(name, me))
    obj.data.materials.append(mat)
    return obj


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# Hajar-like rock ridge in the far distance
rock = principled("rock", "#A39A9A", rough=0.9)
color_variation(rock, "#8F8686", "#B7ACAA", scale=0.02, coord_kind="Object")
add_fog(rock, FOG, start=250, end=1500, power=1.2, max_fac=0.7)


def mountain(x, y):
    base = noise.ridged_multi_fractal(Vector((x / 520.0, y / 520.0, 3.1)), 1.0, 2.0, 7, 0.9, 2.1)
    envelope = smoothstep(-1500, -300, x) * (1.0 - 0.55 * smoothstep(300, 1400, x))
    return max(0.0, base - 0.35) * 95.0 * envelope + (y - 900) * 0.04


mountains = heightfield(
    "mountains",
    np.linspace(-1700, 1700, 360),
    np.linspace(820, 1400, 60),
    mountain,
    rock,
)

# Sand: one surface from the camera's feet out to the dune sea.
sand = principled("sand", "#C6AE98", rough=0.96, spec=0.25)
color_variation(sand, "#B89F88", "#D1BBA5", scale=0.015, coord_kind="Object")
add_bump(sand, scale=180.0, strength=0.25, distance=0.05)
# wind ripples: banded relief layered on top of the grain
_nt = sand.node_tree
_b = _nt.nodes.get("Principled BSDF")
_prev_bump = _b.inputs["Normal"].links[0].from_node
_tc = _nt.nodes.new("ShaderNodeTexCoord")
_wave = _nt.nodes.new("ShaderNodeTexWave")
_wave.wave_type = "BANDS"
_wave.bands_direction = "Y"
_wave.inputs["Scale"].default_value = 0.9
_wave.inputs["Distortion"].default_value = 7.0
_wave.inputs["Detail"].default_value = 3.0
_wave.inputs["Detail Scale"].default_value = 0.6
_nt.links.new(_tc.outputs["Object"], _wave.inputs["Vector"])
_rb = _nt.nodes.new("ShaderNodeBump")
_rb.inputs["Strength"].default_value = 0.35
_rb.inputs["Distance"].default_value = 0.03
_nt.links.new(_wave.outputs["Fac"], _rb.inputs["Height"])
_nt.links.new(_prev_bump.outputs["Normal"], _rb.inputs["Normal"])
_nt.links.new(_rb.outputs["Normal"], _b.inputs["Normal"])
add_fog(sand, FOG, start=70, end=1100, power=1.35, max_fac=0.85)


def dunes(x, y):
    amp = smoothstep(130, 420, y) * 26.0
    warp = noise.noise(Vector((x / 260.0, y / 260.0, 0.3))) * 70.0
    n = noise.noise(Vector(((x + warp) / 150.0, (y + warp * 0.4) / 95.0, 1.7)))
    crest = (1.0 - abs(n)) ** 3
    swell = noise.noise(Vector((x / 40.0, y / 40.0, 5.0))) * 0.12
    return amp * crest + swell - 0.02 * max(0.0, 40 - y)


ys = np.concatenate([np.linspace(-5, 120, 90), np.linspace(122, 900, 170)])
ground = heightfield("sand", np.linspace(-700, 700, 330), ys, dunes, sand)

# Low desert scrub scattered on the plain (gives the plain its scale).
scrub = principled("scrub", "#6C694C", rough=0.85)
color_variation(scrub, "#5B5A3F", "#827A5A", scale=6.0)
add_fog(scrub, FOG, start=70, end=900, power=1.3, max_fac=0.8)


def bush(name, x, y, r):
    """A clump of a few squashed, noisy blobs – reads as dry desert scrub."""
    rnd = random.Random(hash(name) & 0xFFFF)
    bm = bmesh.new()
    for k in range(rnd.randint(3, 6)):
        rr = r * rnd.uniform(0.35, 0.62)
        off = Vector((rnd.uniform(-r, r) * 0.7, rnd.uniform(-r, r) * 0.5, 0))
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=rr)
        for v in tmp.verts:
            d = noise.noise(v.co * (4.0 / rr) + Vector((x + k, y, 0))) * 0.45 * rr
            v.co += v.co.normalized() * d
            v.co.z *= 0.62
            v.co += off + Vector((x, y, rr * 0.3 + dunes(x, y)))
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    obj = mesh_from_bmesh(name, bm, scrub)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


plate_objects = [mountains, ground]
for i in range(46):
    y = random.uniform(14, 130)
    x = random.uniform(-0.62, 0.62) * y + random.uniform(-4, 4)
    if 42 < y < 64 and -3 < x < 25:
        continue
    plate_objects.append(bush(f"bush{i}", x, y, random.uniform(0.22, 0.6)))

# --------------------------------------------------------------------------- villa
# Local coordinates: x 0..19.5 left→right, y 0 = front face, z up. Offset below.
OX, OY = -0.4, 46.0
concrete = principled("concrete", "#DAD5CF", rough=0.86, spec=0.3)
color_variation(concrete, "#CFC9C2", "#E2DDD7", scale=0.9)
add_bump(concrete, scale=55.0, strength=0.12, distance=0.01)
soffit = principled("soffit", "#C9C3BD", rough=0.9, spec=0.2)
fin_mat = principled("fins", "#B5907F", rough=0.62, spec=0.35)
color_variation(fin_mat, "#A98675", "#BE9A89", scale=2.5)
mass_mat = principled("mass", "#7E6358", rough=0.8)
fascia = principled("fascia", "#2E2826", rough=0.42, metallic=0.55)
frame = principled("frame", "#3A322D", rough=0.4, metallic=0.6)

# Lit interior seen through glazing: warm emission that dims toward the floor.
glow = bpy.data.materials.new("glow")
glow.use_nodes = True
gt = glow.node_tree
gb = gt.nodes.get("Principled BSDF")
gb.inputs["Base Color"].default_value = srgb("#2A2521")
gb.inputs["Roughness"].default_value = 0.06
gb.inputs["Specular IOR Level"].default_value = 0.7
gc = gt.nodes.new("ShaderNodeTexCoord")
gsep = gt.nodes.new("ShaderNodeSeparateXYZ")
gt.links.new(gc.outputs["Object"], gsep.inputs["Vector"])
# t = height within the storey (both storeys are 3.4 m, starting at 0.55 m)
gsub = gt.nodes.new("ShaderNodeMath"); gsub.operation = "SUBTRACT"; gsub.inputs[1].default_value = 0.55
gdiv = gt.nodes.new("ShaderNodeMath"); gdiv.operation = "DIVIDE"; gdiv.inputs[1].default_value = 3.4
gfr = gt.nodes.new("ShaderNodeMath"); gfr.operation = "FRACT"
gt.links.new(gsep.outputs["Z"], gsub.inputs[0])
gt.links.new(gsub.outputs[0], gdiv.inputs[0])
gt.links.new(gdiv.outputs[0], gfr.inputs[0])
gr = gt.nodes.new("ShaderNodeValToRGB")
cr_ = gr.color_ramp
cr_.elements[0].position, cr_.elements[0].color = 0.0, srgb("#3A281E")
cr_.elements[1].position, cr_.elements[1].color = 1.0, srgb("#FFE6CC")
for pos, col in ((0.22, "#8A5B40"), (0.34, "#D29467"), (0.75, "#F4C79F")):
    e = cr_.elements.new(pos); e.color = srgb(col)
gt.links.new(gfr.outputs[0], gr.inputs["Fac"])
gn = gt.nodes.new("ShaderNodeTexNoise")
gn.inputs["Scale"].default_value = 0.35
gt.links.new(gc.outputs["Object"], gn.inputs["Vector"])
gm = gt.nodes.new("ShaderNodeMapRange")
gm.inputs["To Min"].default_value = 0.65
gm.inputs["To Max"].default_value = 1.15
gt.links.new(gn.outputs["Fac"], gm.inputs["Value"])
gt.links.new(gr.outputs["Color"], gb.inputs["Emission Color"])
gt.links.new(gm.outputs["Result"], gb.inputs["Emission Strength"])

balustrade_glass = principled("balustrade", "#DCE3E2", rough=0.04, transmission=1.0, spec=0.6)
downlight = principled("downlight", "#FFFFFF", emission="#FFD9B3", emission_strength=40.0)

villa = []


def V(obj):
    obj.location.x += OX
    obj.location.y += OY
    villa.append(obj)
    return obj


# podium + steps
V(box("podium", -1.8, 21.2, -1.4, 12.5, -0.3, 0.55, concrete, bevel=0.02))
for k in range(3):
    V(box(f"step{k}", 6.0 - k * 0.0, 11.0, -1.4 - (k + 1) * 0.38, -1.4 - k * 0.38, -0.3, 0.55 - (k + 1) * 0.18,
          concrete, bevel=0.01))

# ground floor: glass box set back under the cantilever, one solid wall bay
V(box("gf_glass", 3.2, 17.4, 1.8, 10.5, 0.55, 3.95, glow))
V(box("gf_wall", 0.4, 3.4, 1.4, 11.0, 0.55, 3.95, concrete, bevel=0.015))
for k, x in enumerate(np.arange(3.2, 17.5, 1.78)):
    V(box(f"mullion{k}", x - 0.05, x + 0.05, 1.72, 1.8, 0.55, 3.95, frame))
V(box("gf_transom", 3.2, 17.4, 1.72, 1.8, 3.72, 3.8, frame))
V(box("gf_wall_r", 17.4, 18.2, 1.8, 10.5, 0.55, 3.95, concrete, bevel=0.015))

# upper floor: rounded clad mass on the left, open loggia on the right
UP0, UP1 = 3.95, 7.35
fp = rounded_rect_points(0.0, 12.8, 0.0, 10.0, r_fl=3.0, r_bl=3.0, seg=20)
V(extrude_polygon("up_mass", fp, UP0, UP1, mass_mat))
V(box("up_floor", 0.3, 19.6, 0.0, 10.0, UP0 - 0.28, UP0, soffit))  # slab edge / soffit

# vertical fins following the curved front-left perimeter
front_path = [(12.8, 0.0)]
for a in np.linspace(1.5 * math.pi, math.pi, 21):
    front_path.append((3.0 + 3.0 * math.cos(a), 3.0 + 3.0 * math.sin(a)))
front_path.append((0.0, 7.0))
for a in np.linspace(math.pi, 0.5 * math.pi, 21):
    front_path.append((3.0 + 3.0 * math.cos(a), 7.0 + 3.0 * math.sin(a)))
front_path = [(x, y) for x, y in front_path]
front_path = list(reversed(front_path))  # run back-left → front-right
samples, _ = polyline_samples(front_path, 0.36)
fin_bm = bmesh.new()
for (x, y), (nx, ny) in samples:
    # outward normal: straight runs face -y (front) or -x (left); arcs face away from their centre
    if x <= 3.0 and y <= 3.0:
        dx, dy = x - 3.0, y - 3.0
    elif x <= 3.0 and y >= 7.0:
        dx, dy = x - 3.0, y - 7.0
    elif x <= 0.01:
        dx, dy = -1.0, 0.0
    else:
        dx, dy = 0.0, -1.0
    L = math.hypot(dx, dy) or 1
    ox, oy = dx / L, dy / L
    tx, ty = -oy, ox
    w, d = 0.07, 0.24
    corners = []
    for s_t, s_o in ((-w, 0.02), (w, 0.02), (w, d), (-w, d)):
        corners.append((x + tx * s_t + ox * s_o, y + ty * s_t + oy * s_o))
    vb = [fin_bm.verts.new((cx_, cy_, UP0 + 0.05)) for cx_, cy_ in corners]
    vt = [fin_bm.verts.new((cx_, cy_, UP1 - 0.05)) for cx_, cy_ in corners]
    fin_bm.faces.new(vb[::-1])
    fin_bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        fin_bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
bmesh.ops.recalc_face_normals(fin_bm, faces=fin_bm.faces)
V(mesh_from_bmesh("fins", fin_bm, fin_mat))

# loggia
V(box("loggia_glass", 12.8, 19.2, 2.6, 2.7, UP0, UP1, glow))
V(box("loggia_wall_r", 19.2, 19.6, 0.0, 10.0, UP0, UP1, concrete, bevel=0.015))
V(box("loggia_back", 12.8, 19.6, 2.7, 10.0, UP0, UP1, concrete))
for k, x in enumerate(np.arange(12.8, 19.3, 1.6)):
    V(box(f"lmull{k}", x - 0.04, x + 0.04, 2.55, 2.62, UP0, UP1, frame))
V(box("balustrade", 12.9, 19.15, 0.08, 0.14, UP0, UP0 + 1.05, balustrade_glass))
V(box("rail", 12.9, 19.15, 0.06, 0.16, UP0 + 1.03, UP0 + 1.08, frame))

# roof slab with the dark fascia band, following the same rounded footprint
roof_fp = rounded_rect_points(-0.15, 19.75, -0.15, 10.15, r_fl=3.15, r_bl=3.15, seg=24)
V(extrude_polygon("roof", roof_fp, UP1, UP1 + 0.42, fascia, bevel=0.02))
V(extrude_polygon("parapet_cap", rounded_rect_points(-0.1, 19.7, -0.1, 10.1, r_fl=3.1, r_bl=3.1, seg=24),
                  UP1 + 0.42, UP1 + 0.47, concrete))

# soffit downlights under the cantilever
for k, x in enumerate(np.arange(4.4, 17.0, 2.1)):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=0.07, segments=12)
    for v in bm.verts:
        v.co += Vector((x, 0.9, UP0 - 0.285))
    V(mesh_from_bmesh(f"dl{k}", bm, downlight))

# a slim concrete blade wall at the left edge, very Gulf-modern
V(box("blade", -1.4, -1.05, 1.0, 11.5, 0.55, 5.6, concrete, bevel=0.02))

# --------------------------------------------------------------------------- palms
palm_trunk = principled("trunk", "#7C6E63", rough=0.9)
add_bump(palm_trunk, scale=12.0, strength=0.5, distance=0.03)
palm_leaf = principled("frond", "#5F6843", rough=0.7, spec=0.35)
color_variation(palm_leaf, "#4F5A37", "#76784E", scale=1.2)


def palm(name, x, y, h, lean=0.0, seed=0):
    rnd = random.Random(seed)
    objs = []
    bm = bmesh.new()
    rings = 24
    prev = None
    for i in range(rings + 1):
        t = i / rings
        cx = x + lean * t * t * h
        z = t * h
        r = 0.21 * (1.0 - 0.3 * t) * (1.0 + 0.06 * math.sin(i * 2.7))
        ring = [bm.verts.new((cx + r * math.cos(a), y + r * math.sin(a), z))
                for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
        if prev:
            for k in range(12):
                bm.faces.new((prev[k], prev[(k + 1) % 12], ring[(k + 1) % 12], ring[k]))
        prev = ring
    top = Vector((x + lean * h, y, h))
    t_obj = mesh_from_bmesh(name + "_trunk", bm, palm_trunk)
    for p in t_obj.data.polygons:
        p.use_smooth = True
    objs.append(t_obj)

    fb = bmesh.new()
    n_fronds = 22
    for f in range(n_fronds):
        az = f / n_fronds * 2 * math.pi + rnd.uniform(-0.2, 0.2)
        up = rnd.uniform(0.35, 1.45)
        length = rnd.uniform(3.0, 3.9)
        steps = 30
        spine = []
        for s in range(steps + 1):
            t = s / steps
            horiz = length * t
            z = up * horiz - 1.35 * (horiz ** 2) / length
            spine.append(top + Vector((math.cos(az) * horiz, math.sin(az) * horiz, z)))
        side = Vector((-math.sin(az), math.cos(az), 0))
        # rachis
        for s in range(steps):
            a, b = spine[s], spine[s + 1]
            w = Vector((0, 0, 0.035))
            fb.faces.new((fb.verts.new(a - w), fb.verts.new(b - w), fb.verts.new(b + w), fb.verts.new(a + w)))
        # pinnate leaflets in a shallow V
        for s in range(3, steps):
            t = s / steps
            if s % 1: continue
            base = spine[s]
            fwd = (spine[min(s + 1, steps)] - spine[s - 1]).normalized()
            lf = (0.85 * math.sin(math.pi * min(1.0, t * 1.05)) + 0.15)
            for sgn in (-1, 1):
                d = (side * sgn * 0.8 + fwd * 0.55 + Vector((0, 0, 0.28))).normalized()
                tip = base + d * lf + Vector((0, 0, -0.18 * lf * t))
                n = d.cross(Vector((0, 0, 1))).normalized()
                fb.faces.new((fb.verts.new(base - n * 0.05), fb.verts.new(base + n * 0.05),
                              fb.verts.new(tip + n * 0.03), fb.verts.new(tip - n * 0.03)))
    f_obj = mesh_from_bmesh(name + "_crown", fb, palm_leaf)
    for p in f_obj.data.polygons:
        p.use_smooth = True
    objs.append(f_obj)
    return objs


for o in palm("palm_b", OX + 21.4, OY + 1.2, 6.2, lean=0.12, seed=2):
    villa.append(o)
for o in palm("palm_c", OX + 23.6, OY + 6.8, 7.6, lean=-0.07, seed=3):
    villa.append(o)
for i, (x, y, r) in enumerate([(OX - 2.6, OY - 2.2, 0.55), (OX + 21.8, OY - 1.8, 0.6), (OX + 12.5, OY - 3.4, 0.4),
                                (OX - 5.2, OY - 0.6, 0.45), (OX + 24.8, OY + 0.2, 0.5)]):
    villa.append(bush(f"vbush{i}", x, y, r))

# --------------------------------------------------------------------------- hotspots
hotspots = {
    "roof": (OX + 8.2, OY + 0.0, UP1 + 0.3),
    "facade": (OX + 1.9, OY + 1.35, 2.3),
    "joints": (OX + 17.45, OY + 1.75, 2.1),
    "repair": (OX + 19.4, OY - 1.4, 0.2),
}
bpy.context.view_layer.update()
coords = {}
for key, p in hotspots.items():
    v = world_to_camera_view(scene, cam, Vector(p))
    coords[key] = {"x": round(v.x, 4), "y": round(1 - v.y, 4)}
with open(os.path.join(OUT, "hotspots.json"), "w") as fh:
    json.dump(coords, fh, indent=2)
print("hotspots", coords)


# --------------------------------------------------------------------------- render
def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def set_visible(objs, on):
    for o in objs:
        o.hide_render = not on


if MODE in ("plate", "both"):
    scene.render.film_transparent = False
    set_visible(villa, False)
    set_visible(plate_objects, True)
    render(os.path.join(OUT, f"hero-plate-{WIDTH}.png"))

if MODE in ("cutout", "both"):
    set_visible(villa, True)
    set_visible(plate_objects, False)
    # ground for shadows only
    catcher = box("catcher", -40, 60, 20, 90, -0.2, 0.0, principled("c", "#C8AD98"))
    catcher.is_shadow_catcher = True
    scene.render.film_transparent = True
    render(os.path.join(OUT, f"hero-villa-{WIDTH}.png"))

if MODE == "preview":
    scene.render.film_transparent = False
    set_visible(villa, True)
    set_visible(plate_objects, True)
    render(os.path.join(OUT, f"hero-preview-{WIDTH}.png"))
