"""Re-export a GLB as FBX with its textures embedded (Blender, headless). UEFN imports FBX/OBJ only.

    blender -b --factory-startup --python tools/glb_to_fbx.py -- in.glb out.fbx
"""
import bpy, sys
src, dst = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, object_types={'MESH'}, path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE')
print("EXPORTED", dst)
