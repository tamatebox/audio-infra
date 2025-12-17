#!/usr/bin/env python3
"""
Blenderを使って3Dスキャンデータから複数視点の画像を生成する。

使用方法:
    blender --background --python room/render_views.py
"""

import os

import bpy
from mathutils import Vector


def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_mesh(file_path):
    """メッシュをインポート"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".glb" or ext == ".gltf":
        bpy.ops.import_scene.gltf(filepath=file_path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=file_path)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def get_scene_bounds():
    """シーン全体のバウンディングボックスを取得"""
    min_co = Vector((float("inf"), float("inf"), float("inf")))
    max_co = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for v in obj.bound_box:
                world_v = obj.matrix_world @ Vector(v)
                min_co.x = min(min_co.x, world_v.x)
                min_co.y = min(min_co.y, world_v.y)
                min_co.z = min(min_co.z, world_v.z)
                max_co.x = max(max_co.x, world_v.x)
                max_co.y = max(max_co.y, world_v.y)
                max_co.z = max(max_co.z, world_v.z)

    center = (min_co + max_co) / 2
    extents = max_co - min_co
    return center, extents, min_co, max_co


def setup_camera(location, target, lens=50):
    """カメラを設定"""
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = lens
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)

    cam.location = location
    direction = Vector(target) - Vector(location)
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam.rotation_euler = rot_quat.to_euler()

    bpy.context.scene.camera = cam
    return cam


def setup_lighting():
    """ライティングを設定"""
    # 環境光
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (
        0.8,
        0.8,
        0.8,
        1,
    )

    # サンライト
    light_data = bpy.data.lights.new("Sun", type="SUN")
    light_data.energy = 3
    light = bpy.data.objects.new("Sun", light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = (5, 5, 10)


def render_view(output_path, resolution=(1024, 768)):
    """現在のカメラビューをレンダリング"""
    bpy.context.scene.render.resolution_x = resolution[0]
    bpy.context.scene.render.resolution_y = resolution[1]
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print(f"保存完了: {output_path}")


def delete_camera():
    """現在のカメラを削除"""
    if bpy.context.scene.camera:
        bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)


def render_room_views(file_path, output_prefix):
    """複数視点からレンダリング"""
    # シーン準備
    clear_scene()
    import_mesh(file_path)
    setup_lighting()

    # バウンディングボックス取得
    center, extents, min_co, max_co = get_scene_bounds()
    max_dim = max(extents)

    views = []

    # 1. 真上 (Top View)
    views.append(
        (
            "01_top",
            (center.x, center.y, center.z + max_dim * 2),
            (center.x, center.y, center.z),
            35,
        )
    )

    # 2-5. 4コーナーからの斜め俯瞰
    corners = [
        ("02_corner_pp", (1, 1, 1)),
        ("03_corner_pn", (1, -1, 1)),
        ("04_corner_np", (-1, 1, 1)),
        ("05_corner_nn", (-1, -1, 1)),
    ]
    for name, direction in corners:
        loc = center + Vector(direction) * max_dim * 0.8
        views.append((name, tuple(loc), tuple(center), 50))

    # 6-9. 4壁面の正面ビュー
    walls = [
        ("06_wall_front", (0, -1, 0)),
        ("07_wall_back", (0, 1, 0)),
        ("08_wall_left", (1, 0, 0)),
        ("09_wall_right", (-1, 0, 0)),
    ]
    for name, direction in walls:
        loc = center + Vector(direction) * max_dim * 1.2
        loc.z = center.z
        views.append((name, tuple(loc), tuple(center), 50))

    # 10-11. 側面図
    views.append(
        (
            "10_elevation_x",
            (center.x + max_dim * 2, center.y, center.z),
            tuple(center),
            35,
        )
    )
    views.append(
        (
            "11_elevation_y",
            (center.x, center.y + max_dim * 2, center.z),
            tuple(center),
            35,
        )
    )

    # 12-15. 内部視点
    internal_views = [
        ("12_internal_to_front", (0, 0.3, 0), (0, -1, 0)),
        ("13_internal_to_back", (0, -0.3, 0), (0, 1, 0)),
        ("14_internal_to_left", (0.3, 0, 0), (-1, 0, 0)),
        ("15_internal_to_right", (-0.3, 0, 0), (1, 0, 0)),
    ]
    for name, eye_offset, look_dir in internal_views:
        eye = center + Vector(eye_offset) * Vector(extents)
        eye.z = center.z
        target = eye + Vector(look_dir)
        views.append((name, tuple(eye), tuple(target), 28))  # 広角

    # 16. 床面クローズアップ
    eye = center + Vector((extents.x * 0.3, extents.y * 0.3, extents.z * 0.3))
    target = Vector((center.x, center.y, min_co.z))
    views.append(("16_floor", tuple(eye), tuple(target), 50))

    # レンダリング実行
    for name, location, target, lens in views:
        delete_camera()
        setup_camera(location, target, lens)
        render_view(f"{output_prefix}_{name}.png")

    print(f"\n完了: {len(views)}視点の画像を生成しました")


# 実行
if __name__ == "__main__":
    # Blenderから実行時のパス解決
    # スクリプトのディレクトリを基準にする
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    render_room_views("room/scans/room.glb", output_prefix="room/renders/room")
