"""Macro of a concrete slab at dusk: water beads on the coated half, darkens the bare half.

usage: python3 droplets.py <width> <samples> <outdir>
"""
import math
import os
import random
import sys

import bpy  # must precede bmesh/mathutils when running as a module
import bmesh
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
from common import add_bump, link, look_at, mesh_from_bmesh, principled, reset_scene, srgb

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 960
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 24
OUT = sys.argv[3] if len(sys.argv) > 3 else "/root/renders"
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(5)

scene = reset_scene()
scene.render.resolution_x = WIDTH
scene.render.resolution_y = round(WIDTH * 9 / 16)
scene.cycles.samples = SAMPLES
scene.cycles.transmission_bounces = 8
scene.cycles.max_bounces = 10
scene.render.film_transparent = False

world = bpy.data.worlds.new("dusk")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = srgb("#D9CCC6")
bg.inputs["Strength"].default_value = 0.6

# low warm sun raking across the surface + soft sky fill
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 3.6
sun_d.color = srgb("#FFC39A")[:3]
sun_d.angle = math.radians(4)
sun = link(bpy.data.objects.new("sun", sun_d))
sun.rotation_euler = Vector((-0.75, 0.95, -0.2)).normalized().to_track_quat("-Z", "Y").to_euler()

fill_d = bpy.data.lights.new("fill", "AREA")
fill_d.energy = 60
fill_d.size = 1.5
fill_d.color = srgb("#DCD6E4")[:3]
fill = link(bpy.data.objects.new("fill", fill_d))
fill.location = (0.3, -0.8, 0.9)
look_at(fill, (0, 0, 0))

# ---- slab: a subdivided plane with fine relief --------------------------------
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=260, y_segments=160, size=1.0)
for v in bm.verts:
    v.co.x *= 1.3
    v.co.y *= 0.8
    v.co.z = noise.noise(v.co * 9.0) * 0.0025 + noise.noise(v.co * 40.0) * 0.0006
slab = mesh_from_bmesh("slab", bm)
for p in slab.data.polygons:
    p.use_smooth = True

# material: bare concrete on the right, satin coat on the left, soft seam
mat = bpy.data.materials.new("concrete")
mat.use_nodes = True
nt = mat.node_tree
nodes, links = nt.nodes, nt.links
out = nodes["Material Output"]
bare = nodes["Principled BSDF"]
bare.inputs["Base Color"].default_value = srgb("#8E857B")
bare.inputs["Roughness"].default_value = 0.92
tc = nodes.new("ShaderNodeTexCoord")
vor = nodes.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 90.0
links.new(tc.outputs["Object"], vor.inputs["Vector"])
agg = nodes.new("ShaderNodeMapRange")
agg.inputs["From Min"].default_value = 0.06
agg.inputs["From Max"].default_value = 0.2
links.new(vor.outputs["Distance"], agg.inputs["Value"])
mix_c = nodes.new("ShaderNodeMix")
mix_c.data_type = "RGBA"
links.new(agg.outputs["Result"], mix_c.inputs["Factor"])
mix_c.inputs[6].default_value = srgb("#766D64")
mix_c.inputs[7].default_value = srgb("#958B81")
# wet patches darken the bare side
wet_n = nodes.new("ShaderNodeTexNoise")
wet_n.inputs["Scale"].default_value = 3.2
wet_n.inputs["Detail"].default_value = 6.0
links.new(tc.outputs["Object"], wet_n.inputs["Vector"])
wet = nodes.new("ShaderNodeMapRange")
wet.inputs["From Min"].default_value = 0.52
wet.inputs["From Max"].default_value = 0.6
links.new(wet_n.outputs["Fac"], wet.inputs["Value"])
dark = nodes.new("ShaderNodeMix")
dark.data_type = "RGBA"
dark.blend_type = "MULTIPLY"
links.new(wet.outputs["Result"], dark.inputs["Factor"])
links.new(mix_c.outputs[2], dark.inputs[6])
dark.inputs[7].default_value = srgb("#5A514B")
links.new(dark.outputs[2], bare.inputs["Base Color"])
bump = nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.35
bump.inputs["Distance"].default_value = 0.002
pore = nodes.new("ShaderNodeTexNoise")
pore.inputs["Scale"].default_value = 420.0
links.new(tc.outputs["Object"], pore.inputs["Vector"])
links.new(pore.outputs["Fac"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bare.inputs["Normal"])

coat = nodes.new("ShaderNodeBsdfPrincipled")
coat.inputs["Base Color"].default_value = srgb("#6F625A")
coat.inputs["Roughness"].default_value = 0.38
coat.inputs["Coat Weight"].default_value = 0.35
coat.inputs["Coat Roughness"].default_value = 0.18
cbump = nodes.new("ShaderNodeBump")
cbump.inputs["Strength"].default_value = 0.08
cbump.inputs["Distance"].default_value = 0.002
links.new(pore.outputs["Fac"], cbump.inputs["Height"])
links.new(cbump.outputs["Normal"], coat.inputs["Normal"])

sep = nodes.new("ShaderNodeSeparateXYZ")
links.new(tc.outputs["Object"], sep.inputs["Vector"])
edge_n = nodes.new("ShaderNodeTexNoise")
edge_n.inputs["Scale"].default_value = 14.0
links.new(tc.outputs["Object"], edge_n.inputs["Vector"])
edge = nodes.new("ShaderNodeMath")
edge.operation = "MULTIPLY_ADD"
edge.inputs[1].default_value = 0.05
links.new(edge_n.outputs["Fac"], edge.inputs[0])
links.new(sep.outputs["X"], edge.inputs[2])
seam = nodes.new("ShaderNodeMapRange")
seam.inputs["From Min"].default_value = 0.035
seam.inputs["From Max"].default_value = 0.05
links.new(edge.outputs["Value"], seam.inputs["Value"])
mixs = nodes.new("ShaderNodeMixShader")
links.new(seam.outputs["Result"], mixs.inputs["Fac"])
links.new(coat.outputs["BSDF"], mixs.inputs[1])
links.new(bare.outputs["BSDF"], mixs.inputs[2])
links.new(mixs.outputs["Shader"], out.inputs["Surface"])
slab.data.materials.append(mat)

# ---- droplets on the coated (x < 0) side ------------------------------------
water = principled("water", "#FFFFFF", rough=0.02, transmission=1.0, spec=0.5)
water.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.333

placed = []
for i in range(520):
    if i < 260:  # denser where the lens is focused
        x = rnd.uniform(-0.55, 0.02)
        y = rnd.uniform(-0.55, 0.25)
    else:
        x = rnd.uniform(-1.3, 0.0)
        y = rnd.uniform(-0.8, 0.8)
    r = rnd.choice([0.006, 0.008, 0.01, 0.013, 0.016, 0.02, 0.026, 0.034]) * rnd.uniform(0.8, 1.2)
    if any((x - px) ** 2 + (y - py) ** 2 < (r + pr) ** 2 * 1.3 for px, py, pr in placed):
        continue
    placed.append((x, y, r))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    squash = 0.62 if r > 0.015 else 0.75
    for v in bm.verts:
        z = v.co.z
        v.co.x *= r * (1.0 + 0.04 * noise.noise(v.co * 3 + Vector((i, 0, 0))))
        v.co.y *= r
        # flatten the base, keep a contact angle above 90° (hydrophobic bead)
        v.co.z = max(z, -0.35) * r * squash
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co += Vector((x, y, -zmin - 0.0004))
    o = mesh_from_bmesh(f"drop{i}", bm, water)
    for p in o.data.polygons:
        p.use_smooth = True

# ---- camera: low, long lens, shallow focus -----------------------------------
cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 100
cam_d.sensor_width = 36
cam_d.dof.use_dof = True
cam_d.dof.aperture_fstop = 2.2
cam = link(bpy.data.objects.new("cam", cam_d))
cam.location = (-0.2, -1.5, 0.42)
look_at(cam, (-0.08, 0.12, 0.0))
focus = link(bpy.data.objects.new("focus", None))
focus.location = (-0.16, -0.18, 0.0)
cam_d.dof.focus_object = focus
scene.camera = cam

scene.render.filepath = os.path.join(OUT, f"droplets-{WIDTH}.png")
bpy.ops.render.render(write_still=True)
