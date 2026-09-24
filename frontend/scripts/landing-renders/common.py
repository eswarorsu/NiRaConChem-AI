"""Shared helpers for the NiRaConChem landing renders (bpy 5.x, Cycles CPU)."""
import math

import bpy  # must precede bmesh/mathutils when running as a module
import bmesh
from mathutils import Vector


def srgb(hex_or_tuple, alpha=1.0):
    """sRGB hex -> linear RGBA, the space Principled BSDF colours live in."""
    if isinstance(hex_or_tuple, str):
        h = hex_or_tuple.lstrip("#")
        rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    else:
        rgb = list(hex_or_tuple)

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (*[lin(c) for c in rgb], alpha)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 8
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass
    return scene


def principled(name, color, rough=0.6, metallic=0.0, spec=0.5, emission=None, emission_strength=0.0,
               transmission=0.0, alpha=1.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = srgb(emission)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
    return mat


def add_bump(mat, scale=40.0, strength=0.15, detail=6.0, distance=0.02, kind="noise"):
    """Procedural surface relief so large flat faces do not read as CG plastic."""
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "voronoi":
        tex = nt.nodes.new("ShaderNodeTexVoronoi")
        tex.inputs["Scale"].default_value = scale
        out = tex.outputs["Distance"]
    else:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = detail
        out = tex.outputs["Fac"]
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(out, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return tex


def color_variation(mat, color_a, color_b, scale=3.0, detail=4.0, coord_kind="Object"):
    """Low-frequency tonal drift between two colours (weathering, sand patches)."""
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    nt.links.new(coord.outputs[coord_kind], tex.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = srgb(color_a)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = srgb(color_b)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return ramp


def add_fog(mat, fog_color, start=60.0, end=1400.0, power=1.4, strength=1.0, max_fac=0.92):
    """Aerial perspective: blend toward the horizon colour with camera distance."""
    nt = mat.node_tree
    out = nt.nodes.get("Material Output")
    surface_link = out.inputs["Surface"].links[0]
    src = surface_link.from_socket
    nt.links.remove(surface_link)

    cam = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = start
    mr.inputs["From Max"].default_value = end
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = max_fac
    mr.clamp = True
    nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 1.0 / power
    nt.links.new(mr.outputs["Result"], pw.inputs[0])

    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb(fog_color)
    emit.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(pw.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(src, mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_from_bmesh(name, bm, mat=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    if mat is not None:
        obj.data.materials.append(mat)
    link(obj)
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    obj = mesh_from_bmesh(name, bm, mat)
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def rounded_rect_points(x0, x1, y0, y1, r_fl=0.0, r_bl=0.0, r_br=0.0, r_fr=0.0, seg=18):
    """Footprint polygon (counter-clockwise), y0 = front edge facing the camera."""
    pts = []

    def arc(cx, cy, r, a0, a1):
        if r <= 0:
            pts.append((cx, cy))
            return
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    arc(x0 + r_fl, y0 + r_fl, r_fl, math.pi, 1.5 * math.pi) if r_fl else pts.append((x0, y0))
    arc(x1 - r_fr, y0 + r_fr, r_fr, 1.5 * math.pi, 2 * math.pi) if r_fr else pts.append((x1, y0))
    arc(x1 - r_br, y1 - r_br, r_br, 0, 0.5 * math.pi) if r_br else pts.append((x1, y1))
    arc(x0 + r_bl, y1 - r_bl, r_bl, 0.5 * math.pi, math.pi) if r_bl else pts.append((x0, y1))
    return pts


def extrude_polygon(name, pts, z0, z1, mat=None, bevel=0.0):
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z0)) for x, y in pts]
    face = bm.faces.new(verts)
    bm.normal_update()
    if face.normal.z > 0:
        face.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in top:
        v.co.z = z1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = mesh_from_bmesh(name, bm, mat)
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(40)
    return obj


def polyline_samples(pts, spacing, start=0.0, stop=None):
    """Evenly spaced points (with outward normals) along an open polyline."""
    segs = []
    total = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        segs.append((a, b, total, L))
        total += L
    stop = total if stop is None else min(stop, total)
    out = []
    d = start
    while d <= stop + 1e-6:
        for a, b, s0, L in segs:
            if s0 <= d <= s0 + L and L > 0:
                t = (d - s0) / L
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t
                tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                out.append(((x, y), (ty, -tx)))  # outward for CCW footprint
                break
        d += spacing
    return out, total


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
