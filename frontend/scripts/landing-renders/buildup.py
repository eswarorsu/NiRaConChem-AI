"""Roof build-up, second pass: built for realism.

A stepped cutaway of a Gulf roof — structural slab, primer, liquid-applied
membrane, XPS insulation, sand-cement screed, porcelain tiles on a notched
adhesive bed — lit by a real photographed studio (Poly Haven "Studio Small 03",
fetched from the pmndrs/drei-assets GitHub repository).

Rendered once as the whole stack and once per layer from the same camera, so
the page can pull the layers apart without anything drifting out of register.

usage: python3 buildup.py <width> <samples> <outdir> [stack|layers|all|preview] [hdri]
"""
import json
import math
import os
import random
import sys

import bpy  # must precede bmesh/mathutils when running as a module
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from common import link, look_at, srgb

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 800
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 32
OUT = sys.argv[3] if len(sys.argv) > 3 else "/root/renders/b2"
WHAT = sys.argv[4] if len(sys.argv) > 4 else "preview"
HDRI = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_small_03_1k.hdr")
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(21)

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 4
scene.cycles.glossy_bounces = 4
scene.cycles.transmission_bounces = 6
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.render.film_transparent = True
scene.render.resolution_x = WIDTH
scene.render.resolution_y = round(WIDTH * 0.8)
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "16"
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "AgX - Base Contrast"):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        continue

# ------------------------------------------------------------------ light
world = bpy.data.worlds.new("studio")
scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
bg = wn["Background"]
env = wn.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(HDRI)
mapping = wn.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(200))
tc = wn.new("ShaderNodeTexCoord")
wl.new(tc.outputs["Generated"], mapping.inputs["Vector"])
wl.new(mapping.outputs["Vector"], env.inputs["Vector"])
wl.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.22


def area(name, loc, target, energy, size, kelvin_hex, size_y=None):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    if size_y:
        d.shape = "RECTANGLE"
        d.size = size
        d.size_y = size_y
    else:
        d.size = size
    d.color = srgb(kelvin_hex)[:3]
    o = link(bpy.data.objects.new(name, d))
    o.location = loc
    look_at(o, target)
    return o


# big soft key from upper left-front, like a studio softbox
area("key", (-1.9, -2.2, 2.9), (0.6, 0.35, 0.1), 150, 2.2, "#FFF1E4", size_y=1.4)
# cool fill from the right keeps the shadow side readable
area("fill", (3.0, -1.2, 1.1), (0.6, 0.35, 0.1), 28, 2.4, "#E7ECF4")
# rim from behind to separate the layer edges
area("rim", (0.9, 3.0, 2.0), (0.6, 0.35, 0.1), 110, 1.8, "#FFF4EA")

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 72
cam_d.sensor_width = 36
cam = link(bpy.data.objects.new("cam", cam_d))
cam.location = (-1.6, -3.05, 1.72)
look_at(cam, (0.63, 0.36, 0.1))
scene.camera = cam


# ------------------------------------------------------------------ material helpers
def mat_new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def node(nodes, kind, **inputs):
    n = nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def ramp(nodes, stops):
    r = nodes.new("ShaderNodeValToRGB")
    cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], srgb(stops[0][1])
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], srgb(stops[-1][1])
    for pos, col in stops[1:-1]:
        cr.elements.new(pos).color = srgb(col)
    return r


def value_ramp(nodes, a, b, lo, hi):
    m = nodes.new("ShaderNodeMapRange")
    m.inputs["From Min"].default_value = a
    m.inputs["From Max"].default_value = b
    m.inputs["To Min"].default_value = lo
    m.inputs["To Max"].default_value = hi
    return m


def bump_chain(nodes, links, bsdf, heights):
    """heights: list of (socket, strength, distance) applied in sequence."""
    prev = None
    for sock, strength, dist in heights:
        b = node(nodes, "ShaderNodeBump", Strength=strength, Distance=dist)
        links.new(sock, b.inputs["Height"])
        if prev is not None:
            links.new(prev.outputs["Normal"], b.inputs["Normal"])
        prev = b
    links.new(prev.outputs["Normal"], bsdf.inputs["Normal"])


def coords(nodes, scale=1.0):
    t = nodes.new("ShaderNodeTexCoord")
    if scale == 1.0:
        return t.outputs["Object"]
    m = nodes.new("ShaderNodeMapping")
    m.inputs["Scale"].default_value = (scale, scale, scale)
    nodes.id_data.links.new(t.outputs["Object"], m.inputs["Vector"])
    return m.outputs["Vector"]


def cavity_darken(nodes, links, color_socket, strength=0.35, distance=0.01):
    """Ambient-occlusion grime in corners and joints — real surfaces collect it."""
    ao = nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.inputs["Distance"].default_value = distance
    mr = value_ramp(nodes, 0.0, 1.0, 1.0 - strength, 1.0)
    links.new(ao.outputs["AO"], mr.inputs["Value"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    links.new(color_socket, mix.inputs[6])
    comb = nodes.new("ShaderNodeCombineColor")
    links.new(mr.outputs["Result"], comb.inputs[0])
    links.new(mr.outputs["Result"], comb.inputs[1])
    links.new(mr.outputs["Result"], comb.inputs[2])
    links.new(comb.outputs["Color"], mix.inputs[7])
    return mix.outputs[2]


# ---- concrete: cement paste with aggregate, pores and a trowelled top ----------
def concrete_material():
    m, nodes, links, bsdf = mat_new("concrete")
    co = coords(nodes)
    # slight warp so stones are not perfect voronoi polygons
    warp = node(nodes, "ShaderNodeTexNoise", Scale=45.0, Detail=3.0)
    links.new(co, warp.inputs["Vector"])
    wmix = nodes.new("ShaderNodeMix")
    wmix.data_type = "VECTOR"
    wmix.inputs["Factor"].default_value = 0.018
    links.new(co, wmix.inputs[4])
    links.new(warp.outputs["Color"], wmix.inputs[5])
    wv = wmix.outputs[1]

    def stones(scale, keep_below, edge_lo, edge_hi):
        cell = node(nodes, "ShaderNodeTexVoronoi", Scale=scale, Randomness=1.0)
        links.new(wv, cell.inputs["Vector"])
        edge = node(nodes, "ShaderNodeTexVoronoi", Scale=scale, Randomness=1.0)
        edge.feature = "DISTANCE_TO_EDGE"
        links.new(wv, edge.inputs["Vector"])
        body = value_ramp(nodes, edge_lo, edge_hi, 0.0, 1.0)
        links.new(edge.outputs["Distance"], body.inputs["Value"])
        sep = nodes.new("ShaderNodeSeparateColor")
        links.new(cell.outputs["Color"], sep.inputs["Color"])
        keep = value_ramp(nodes, keep_below, keep_below + 0.01, 1.0, 0.0)
        links.new(sep.outputs[0], keep.inputs["Value"])
        msk = nodes.new("ShaderNodeMath")
        msk.operation = "MULTIPLY"
        links.new(body.outputs["Result"], msk.inputs[0])
        links.new(keep.outputs["Result"], msk.inputs[1])
        return msk.outputs["Value"], sep.outputs[1]

    coarse, coarse_tone = stones(16.0, 0.42, 0.06, 0.1)
    medium, medium_tone = stones(38.0, 0.3, 0.07, 0.12)
    stone_mask = nodes.new("ShaderNodeMath")
    stone_mask.operation = "MAXIMUM"
    links.new(coarse, stone_mask.inputs[0])
    links.new(medium, stone_mask.inputs[1])
    tone = nodes.new("ShaderNodeMix")
    tone.data_type = "FLOAT"
    links.new(coarse, tone.inputs["Factor"])
    links.new(medium_tone, tone.inputs[2])
    links.new(coarse_tone, tone.inputs[3])
    stone_col = ramp(nodes, [(0.0, "#6F6860"), (0.3, "#8E8579"), (0.55, "#A4998B"), (0.8, "#7C736A"), (1.0, "#B2A797")])
    links.new(tone.outputs[0], stone_col.inputs["Fac"])

    # cement paste: warm mid grey with sand
    n1 = node(nodes, "ShaderNodeTexNoise", Scale=8.0, Detail=10.0, Roughness=0.6)
    links.new(co, n1.inputs["Vector"])
    paste = ramp(nodes, [(0.3, "#8F8880"), (0.55, "#9A938A"), (0.75, "#A39C93")])
    links.new(n1.outputs["Fac"], paste.inputs["Fac"])
    sand = node(nodes, "ShaderNodeTexNoise", Scale=900.0, Detail=1.0)
    links.new(co, sand.inputs["Vector"])
    ps = nodes.new("ShaderNodeMix")
    ps.data_type = "RGBA"
    ps.blend_type = "OVERLAY"
    ps.inputs["Factor"].default_value = 0.3
    links.new(paste.outputs["Color"], ps.inputs[6])
    links.new(sand.outputs["Color"], ps.inputs[7])

    # the top face is power-floated: no stones there, a smoother, paler skin
    geo = nodes.new("ShaderNodeNewGeometry")
    sepn = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Normal"], sepn.inputs["Vector"])
    side = value_ramp(nodes, 0.9, 0.99, 1.0, 0.0)
    links.new(sepn.outputs["Z"], side.inputs["Value"])
    mask = nodes.new("ShaderNodeMath")
    mask.operation = "MULTIPLY"
    links.new(stone_mask.outputs["Value"], mask.inputs[0])
    links.new(side.outputs["Result"], mask.inputs[1])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    links.new(mask.outputs["Value"], mix.inputs["Factor"])
    links.new(ps.outputs[2], mix.inputs[6])
    links.new(stone_col.outputs["Color"], mix.inputs[7])
    skin = nodes.new("ShaderNodeMix")
    skin.data_type = "RGBA"
    skin.blend_type = "SCREEN"
    inv = value_ramp(nodes, 0.0, 1.0, 0.18, 0.0)
    links.new(side.outputs["Result"], inv.inputs["Value"])
    links.new(inv.outputs["Result"], skin.inputs["Factor"])
    links.new(mix.outputs[2], skin.inputs[6])
    skin.inputs[7].default_value = srgb("#C9C2B9")

    # pores: small dark pits, clustered
    pv = node(nodes, "ShaderNodeTexVoronoi", Scale=230.0)
    links.new(co, pv.inputs["Vector"])
    pore = value_ramp(nodes, 0.0, 0.1, 1.0, 0.0)
    links.new(pv.outputs["Distance"], pore.inputs["Value"])
    pore_gate = node(nodes, "ShaderNodeTexNoise", Scale=30.0)
    links.new(co, pore_gate.inputs["Vector"])
    pg = value_ramp(nodes, 0.56, 0.64, 0.0, 1.0)
    links.new(pore_gate.outputs["Fac"], pg.inputs["Value"])
    pm = nodes.new("ShaderNodeMath")
    pm.operation = "MULTIPLY"
    links.new(pore.outputs["Result"], pm.inputs[0])
    links.new(pg.outputs["Result"], pm.inputs[1])
    dark = nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.blend_type = "MULTIPLY"
    links.new(pm.outputs["Value"], dark.inputs["Factor"])
    links.new(skin.outputs[2], dark.inputs[6])
    dark.inputs[7].default_value = srgb("#4E4842")
    col = cavity_darken(nodes, links, dark.outputs[2], 0.3, 0.02)
    links.new(col, bsdf.inputs["Base Color"])
    rough = value_ramp(nodes, 0.0, 1.0, 0.8, 0.94)
    links.new(n1.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.32
    bump_chain(nodes, links, bsdf, [
        (mask.outputs["Value"], 0.18, 0.003),
        (pm.outputs["Value"], -0.7, 0.002),
        (sand.outputs["Fac"], 0.15, 0.0008),
    ])
    return m


# ---- primer: thin, wet-looking epoxy, amber and slightly translucent ---------
def primer_material():
    m, nodes, links, bsdf = mat_new("primer")
    co = coords(nodes)
    n = node(nodes, "ShaderNodeTexNoise", Scale=6.0, Detail=4.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.35, "#8E5424"), (0.65, "#A8672F")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    links.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.32
    bsdf.inputs["Coat Weight"].default_value = 0.35
    bsdf.inputs["Coat Roughness"].default_value = 0.2
    bsdf.inputs["Subsurface Weight"].default_value = 0.25
    bsdf.inputs["Subsurface Radius"].default_value = (0.004, 0.002, 0.001)
    brush = node(nodes, "ShaderNodeTexWave", Scale=3.0, Distortion=4.0, Detail=3.0)
    brush.bands_direction = "X"
    links.new(co, brush.inputs["Vector"])
    bump_chain(nodes, links, bsdf, [(brush.outputs["Fac"], 0.05, 0.001)])
    return m


# ---- polyurea membrane: satin elastomer with orange-peel ---------------------
def membrane_material():
    m, nodes, links, bsdf = mat_new("membrane")
    co = coords(nodes)
    n = node(nodes, "ShaderNodeTexNoise", Scale=4.0, Detail=3.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.35, "#5C5F62"), (0.65, "#676A6D")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    col = cavity_darken(nodes, links, c.outputs["Color"], 0.25, 0.01)
    links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.46
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.35
    peel = node(nodes, "ShaderNodeTexVoronoi", Scale=120.0)
    peel.feature = "SMOOTH_F1"
    links.new(co, peel.inputs["Vector"])
    bump_chain(nodes, links, bsdf, [(peel.outputs["Distance"], 0.18, 0.0015)])
    return m


# ---- XPS insulation: closed-cell foam, pale clay pink -------------------------
def xps_material():
    m, nodes, links, bsdf = mat_new("xps")
    co = coords(nodes)
    cells = node(nodes, "ShaderNodeTexVoronoi", Scale=420.0)
    links.new(co, cells.inputs["Vector"])
    n = node(nodes, "ShaderNodeTexNoise", Scale=3.0, Detail=4.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.3, "#CFA893"), (0.7, "#DBB6A2")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    col = cavity_darken(nodes, links, c.outputs["Color"], 0.35, 0.012)
    links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.62
    bsdf.inputs["Subsurface Weight"].default_value = 0.15
    bsdf.inputs["Subsurface Radius"].default_value = (0.01, 0.006, 0.004)
    bump_chain(nodes, links, bsdf, [(cells.outputs["Distance"], 0.22, 0.0012)])
    return m


# ---- sand-cement screed: granular, matte ---------------------------------------
def screed_material():
    m, nodes, links, bsdf = mat_new("screed")
    co = coords(nodes)
    grain = node(nodes, "ShaderNodeTexNoise", Scale=520.0, Detail=2.0)
    links.new(co, grain.inputs["Vector"])
    patches = node(nodes, "ShaderNodeTexNoise", Scale=5.0, Detail=6.0)
    links.new(co, patches.inputs["Vector"])
    c = ramp(nodes, [(0.3, "#A79D91"), (0.55, "#B4AA9E"), (0.75, "#BDB3A7")])
    links.new(patches.outputs["Fac"], c.inputs["Fac"])
    gm = nodes.new("ShaderNodeMix")
    gm.data_type = "RGBA"
    gm.blend_type = "OVERLAY"
    gm.inputs["Factor"].default_value = 0.35
    links.new(c.outputs["Color"], gm.inputs[6])
    links.new(grain.outputs["Color"], gm.inputs[7])
    col = cavity_darken(nodes, links, gm.outputs[2], 0.3, 0.015)
    links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    bump_chain(nodes, links, bsdf, [(grain.outputs["Fac"], 0.35, 0.0015)])
    return m


# ---- tile adhesive: grey, combed into ribs by a notched trowel -----------------
def adhesive_material():
    m, nodes, links, bsdf = mat_new("adhesive")
    co = coords(nodes)
    n = node(nodes, "ShaderNodeTexNoise", Scale=300.0, Detail=2.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.3, "#8F8B86"), (0.7, "#A09C96")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    col = cavity_darken(nodes, links, c.outputs["Color"], 0.4, 0.008)
    links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bump_chain(nodes, links, bsdf, [(n.outputs["Fac"], 0.3, 0.001)])
    return m


# ---- porcelain tile: unglazed terracotta tone, a touch of sheen ---------------
def tile_material():
    m, nodes, links, bsdf = mat_new("tile")
    co = coords(nodes)
    # per-tile tone: object info random drives a small colour shift
    info = nodes.new("ShaderNodeObjectInfo")
    tone = ramp(nodes, [(0.0, "#A8705A"), (0.5, "#B77E66"), (1.0, "#C08A70")])
    links.new(info.outputs["Random"], tone.inputs["Fac"])
    speck = node(nodes, "ShaderNodeTexVoronoi", Scale=220.0)
    links.new(co, speck.inputs["Vector"])
    sp = value_ramp(nodes, 0.0, 0.08, 1.0, 0.0)
    links.new(speck.outputs["Distance"], sp.inputs["Value"])
    cloud = node(nodes, "ShaderNodeTexNoise", Scale=7.0, Detail=5.0)
    links.new(co, cloud.inputs["Vector"])
    cm = nodes.new("ShaderNodeMix")
    cm.data_type = "RGBA"
    cm.blend_type = "SOFT_LIGHT"
    cm.inputs["Factor"].default_value = 0.35
    links.new(tone.outputs["Color"], cm.inputs[6])
    links.new(cloud.outputs["Color"], cm.inputs[7])
    dm = nodes.new("ShaderNodeMix")
    dm.data_type = "RGBA"
    dm.blend_type = "MULTIPLY"
    links.new(sp.outputs["Result"], dm.inputs["Factor"])
    links.new(cm.outputs[2], dm.inputs[6])
    dm.inputs[7].default_value = srgb("#7F5646")
    links.new(dm.outputs[2], bsdf.inputs["Base Color"])
    r = value_ramp(nodes, 0.0, 1.0, 0.34, 0.5)
    links.new(cloud.outputs["Fac"], r.inputs["Value"])
    links.new(r.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.55
    bump_chain(nodes, links, bsdf, [(cloud.outputs["Fac"], 0.05, 0.002), (speck.outputs["Distance"], 0.08, 0.0008)])
    return m


def grout_material():
    m, nodes, links, bsdf = mat_new("grout")
    co = coords(nodes)
    n = node(nodes, "ShaderNodeTexNoise", Scale=400.0, Detail=2.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.3, "#CFC6BA"), (0.7, "#D9D1C6")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    col = cavity_darken(nodes, links, c.outputs["Color"], 0.35, 0.006)
    links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.93
    bump_chain(nodes, links, bsdf, [(n.outputs["Fac"], 0.3, 0.0008)])
    return m


def steel_material():
    m, nodes, links, bsdf = mat_new("rebar")
    co = coords(nodes)
    n = node(nodes, "ShaderNodeTexNoise", Scale=90.0, Detail=6.0)
    links.new(co, n.inputs["Vector"])
    c = ramp(nodes, [(0.3, "#5F5E5C"), (0.62, "#6E6B68"), (0.8, "#7B5A45")])
    links.new(n.outputs["Fac"], c.inputs["Fac"])
    links.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    mr = value_ramp(nodes, 0.4, 0.6, 0.85, 0.25)
    links.new(n.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Metallic"])
    bsdf.inputs["Roughness"].default_value = 0.5
    return m


# ------------------------------------------------------------------ geometry helpers
def slab(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.003, segments=3, subdiv=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.append(mat)
    if bevel > 0:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = segments
        b.limit_method = "ANGLE"
        b.harden_normals = True
    if subdiv:
        s = o.modifiers.new("sub", "SUBSURF")
        s.subdivision_type = "SIMPLE"
        s.levels = subdiv
        s.render_levels = subdiv
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def displace(obj, tex_type, size, strength, mid=0.5):
    tex = bpy.data.textures.new(obj.name + "_d", tex_type)
    if hasattr(tex, "noise_scale"):
        tex.noise_scale = size
    d = obj.modifiers.new("disp", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.mid_level = mid
    d.texture_coords = "OBJECT"
    return d


# ------------------------------------------------------------------ build-up
W, D = 1.25, 0.72
STEP = 0.125
M = {
    "concrete": concrete_material(),
    "primer": primer_material(),
    "membrane": membrane_material(),
    "xps": xps_material(),
    "screed": screed_material(),
    "adhesive": adhesive_material(),
    "tile": tile_material(),
    "grout": grout_material(),
    "steel": steel_material(),
}


def fp(i):
    return i * STEP, W, 0.0, D


layers = []
z = 0.0

# 1. structural slab — chipped arrises, rebar cut flush on the two cut faces
t = 0.17
x0, x1, y0, y1 = fp(0)
s = slab("slab", x0, x1, y0, y1, z, z + t, M["concrete"], bevel=0.004, segments=2, subdiv=5)
displace(s, "STUCCI", 0.02, 0.0025)
objs = [s]
bar_r = 0.011
for k, xb in enumerate([0.12 + 0.19 * i for i in range(6)]):  # bars along y, cut on the front face
    for zb in (0.042, 0.128):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=bar_r, radius2=bar_r, depth=0.03, segments=20)
        for v in bm.verts:
            v.co = Vector((v.co.x, v.co.z, v.co.y)) + Vector((xb, y0 + 0.0135, zb))
        me = bpy.data.meshes.new("bar")
        bm.to_mesh(me)
        bm.free()
        o = link(bpy.data.objects.new(f"barY{k}_{zb}", me))
        o.data.materials.append(M["steel"])
        objs.append(o)
for k, yb in enumerate([0.1 + 0.18 * i for i in range(4)]):  # bars along x, cut on the left face
    for zb in (0.03, 0.14):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=bar_r, radius2=bar_r, depth=0.03, segments=20)
        for v in bm.verts:
            v.co = Vector((v.co.z, v.co.x, v.co.y)) + Vector((x0 + 0.0135, yb, zb))
        me = bpy.data.meshes.new("bar")
        bm.to_mesh(me)
        bm.free()
        o = link(bpy.data.objects.new(f"barX{k}_{zb}", me))
        o.data.materials.append(M["steel"])
        objs.append(o)
layers.append(("slab", objs, z + t))
z += t

# 2. primer — a thin coat, edges softened like a brushed application
t = 0.004
x0, x1, y0, y1 = fp(1)
p = slab("primer", x0, x1, y0, y1, z, z + t, M["primer"], bevel=0.0018, segments=3)
layers.append(("primer", [p], z + t))
z += t

# 3. liquid-applied membrane — cured elastomer, fully rounded edge
t = 0.016
x0, x1, y0, y1 = fp(2)
mb = slab("membrane", x0, x1, y0, y1, z, z + t, M["membrane"], bevel=0.0075, segments=6)
layers.append(("membrane", [mb], z + t))
z += t

# 4. XPS boards with shiplap joints
t = 0.06
x0, x1, y0, y1 = fp(3)
boards = []
nx, ny = 2, 2
gap = 0.0025
bw, bd = (x1 - x0) / nx, (y1 - y0) / ny
for i in range(nx):
    for j in range(ny):
        bx0, bx1 = x0 + i * bw + gap / 2, x0 + (i + 1) * bw - gap / 2
        by0, by1 = y0 + j * bd + gap / 2, y0 + (j + 1) * bd - gap / 2
        o = slab(f"xps{i}{j}", bx0, bx1, by0, by1, z, z + t, M["xps"], bevel=0.0025, segments=2)
        boards.append(o)
layers.append(("insulation", boards, z + t))
z += t

# 5. screed — slightly crumbly arrises
t = 0.045
x0, x1, y0, y1 = fp(4)
sc = slab("screed", x0, x1, y0, y1, z, z + t, M["screed"], bevel=0.003, segments=2, subdiv=5)
displace(sc, "STUCCI", 0.015, 0.0018)
layers.append(("screed", [sc], z + t))
z += t

# 6. tiles on a combed adhesive bed, with grout
x0, x1, y0, y1 = fp(5)
tile_objs = []
bed_t = 0.004
tile_objs.append(slab("bed", x0 + 0.004, x1 - 0.004, y0 + 0.004, y1 - 0.004, z, z + bed_t, M["adhesive"], bevel=0.001))
# trowel ribs, visible along the edges
rib_w, rib_h, rib_gap = 0.006, 0.006, 0.012
yy = y0 + 0.01
while yy < y1 - 0.01:
    tile_objs.append(slab(f"rib{yy:.3f}", x0 + 0.006, x1 - 0.006, yy, yy + rib_w, z + bed_t, z + bed_t + rib_h,
                          M["adhesive"], bevel=0.0028, segments=3))
    yy += rib_w + rib_gap
tz = z + bed_t + rib_h - 0.001
tile_t = 0.018
joint = 0.005
ntx, nty = 3, 3
tw, td = (x1 - x0) / ntx, (y1 - y0) / nty
for i in range(ntx):
    for j in range(nty):
        o = slab(f"tile{i}{j}", x0 + i * tw + joint / 2, x0 + (i + 1) * tw - joint / 2,
                 y0 + j * td + joint / 2, y0 + (j + 1) * td - joint / 2,
                 tz, tz + tile_t + rnd.uniform(-0.0006, 0.0006), M["tile"], bevel=0.0022, segments=3)
        tile_objs.append(o)
tile_objs.append(slab("grout", x0 + 0.002, x1 - 0.002, y0 + 0.002, y1 - 0.002, tz, tz + tile_t * 0.82,
                      M["grout"], bevel=0.0008))
layers.append(("tiles", tile_objs, tz + tile_t))

# soft contact shadow on an invisible floor
floor = slab("catcher", -3, 4, -3, 4, -0.02, 0.0, M["grout"], bevel=0)
floor.is_shadow_catcher = True

# ------------------------------------------------------------------ anchors for the page
bpy.context.view_layer.update()
anchors = {}
for i, (key, _, top) in enumerate(layers):
    x0, x1, y0, y1 = fp(i)
    pl = world_to_camera_view(scene, cam, Vector((x0, y0 + 0.5 * (y1 - y0), top)))
    anchors[key] = {"left": {"x": round(pl.x, 4), "y": round(1 - pl.y, 4)}}
with open(os.path.join(OUT, "buildup-anchors.json"), "w") as fh:
    json.dump(anchors, fh, indent=2)


def show_only(keys, with_floor):
    for key, objs, _ in layers:
        for o in objs:
            o.hide_render = key not in keys
    floor.hide_render = not with_floor


def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


keys = [k for k, _, _ in layers]
if WHAT in ("preview", "stack", "all"):
    show_only(keys, True)
    render(os.path.join(OUT, f"buildup-stack-{WIDTH}.png"))
if WHAT in ("layers", "all") or WHAT.startswith("layers:"):
    wanted = WHAT.split(":", 1)[1].split(",") if ":" in WHAT else keys
    for idx, key in enumerate(keys):
        if key not in wanted:
            continue
        show_only([key], key == "slab")
        render(os.path.join(OUT, f"buildup-{idx + 1}-{key}-{WIDTH}.png"))
