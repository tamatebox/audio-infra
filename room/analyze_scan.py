#!/usr/bin/env python3
"""
3DスキャンデータのOBJファイルから座標情報を分析し、JSONで出力する。

使用方法:
    uv run python room/analyze_scan.py

出力:
    room/scan_analysis.json
"""

import json
import numpy as np


def load_obj_vertices(filepath: str) -> np.ndarray:
    """OBJファイルから頂点座標を読み込む"""
    vertices = []
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(vertices)


def find_clusters(vertices: np.ndarray, axis: int, threshold: float = 0.1) -> list:
    """指定軸で頂点の密集領域を見つける"""
    values = vertices[:, axis]
    hist, edges = np.histogram(values, bins=50)

    clusters = []
    for i, count in enumerate(hist):
        if count > len(vertices) * 0.01:  # 全体の1%以上
            center = (edges[i] + edges[i + 1]) / 2
            clusters.append({"center": float(center), "count": int(count)})
    return clusters


def analyze_region(vertices: np.ndarray, name: str) -> dict:
    """領域の統計情報を計算"""
    if len(vertices) == 0:
        return {"name": name, "vertex_count": 0}

    return {
        "name": name,
        "vertex_count": int(len(vertices)),
        "centroid": {
            "x_m": float(vertices[:, 0].mean()),
            "y_m": float(vertices[:, 1].mean()),
            "z_m": float(vertices[:, 2].mean()),
        },
        "bounds": {
            "x_min_m": float(vertices[:, 0].min()),
            "x_max_m": float(vertices[:, 0].max()),
            "y_min_m": float(vertices[:, 1].min()),
            "y_max_m": float(vertices[:, 1].max()),
            "z_min_m": float(vertices[:, 2].min()),
            "z_max_m": float(vertices[:, 2].max()),
        },
        "size": {
            "x_mm": int((vertices[:, 0].max() - vertices[:, 0].min()) * 1000),
            "y_mm": int((vertices[:, 1].max() - vertices[:, 1].min()) * 1000),
            "z_mm": int((vertices[:, 2].max() - vertices[:, 2].min()) * 1000),
        },
    }


def main():
    obj_path = "room/scans/room.obj"
    output_path = "room/scan_analysis.json"

    print(f"Loading {obj_path}...")
    vertices = load_obj_vertices(obj_path)

    # 基準値
    floor_y = vertices[:, 1].min()
    ceiling_y = vertices[:, 1].max()
    front_z = vertices[:, 2].min()
    back_z = vertices[:, 2].max()
    left_x = vertices[:, 0].min()
    right_x = vertices[:, 0].max()

    result = {
        "_description": "3Dスキャンデータの座標分析結果",
        "_coordinate_system": {
            "X": "幅方向（左がマイナス、右がプラス）",
            "Y": "高さ方向（床がマイナス、天井がプラス）",
            "Z": "奥行方向（前壁がマイナス、後壁がプラス）",
            "unit": "メートル (m)",
        },
        "_reference": {
            "前壁": "スピーカーがある壁（LPから見て前）",
            "後壁": "ソファがある壁（LPから見て後ろ）",
            "左壁": "LPから見て左",
            "右壁": "LPから見て右",
        },
        "room": {
            "total_vertices": int(len(vertices)),
            "bounding_box": {
                "x_range_m": [float(left_x), float(right_x)],
                "y_range_m": [float(floor_y), float(ceiling_y)],
                "z_range_m": [float(front_z), float(back_z)],
            },
            "dimensions_mm": {
                "width_x": int((right_x - left_x) * 1000),
                "height_y": int((ceiling_y - floor_y) * 1000),
                "depth_z": int((back_z - front_z) * 1000),
            },
            "walls": {
                "front_z_m": float(front_z),
                "back_z_m": float(back_z),
                "left_x_m": float(left_x),
                "right_x_m": float(right_x),
                "floor_y_m": float(floor_y),
                "ceiling_y_m": float(ceiling_y),
            },
        },
        "regions": [],
    }

    # 領域別に分析
    # 配置図に基づく構造:
    #   前壁 → [拡散パネル] → [ラック] → [スピーカー] → [シェルフ] → 部屋中央
    #   高さ: シェルフ(床〜約0.5m) → スピーカー本体(約0.5m〜1.2m) → ラック/拡散パネル(1.2m〜)

    # 1. 前壁付近（スピーカーエリア全体）
    front_area = vertices[vertices[:, 2] < front_z + 0.5]
    result["regions"].append(analyze_region(front_area, "front_wall_area"))

    # 2. 後壁付近（ソファエリア）
    back_area = vertices[vertices[:, 2] > back_z - 0.5]
    result["regions"].append(analyze_region(back_area, "back_wall_area"))

    # スピーカー周辺の構造を分離するための高さ閾値
    # TANNOY Greenwich: 380mm(W) x 580mm(H) x 270mm(D)
    # シェルフ高さ: 600mm（実測値）
    shelf_top_y = floor_y + 0.6      # シェルフ上端（スピーカー下端）= 600mm
    speaker_height = 0.58            # スピーカー高さ 580mm
    speaker_top_y = shelf_top_y + speaker_height  # 600 + 580 = 1180mm

    # スピーカー寸法（TANNOY Greenwich）
    speaker_width = 0.38   # 380mm
    speaker_depth = 0.27   # 270mm

    # バッフル面のZ位置（前回の分析から約-1.5m）
    baffle_z = front_z + 0.28  # 前壁から約280mm

    # スピーカー本体のX範囲
    # 側壁からの距離: 左110mm、右150mm（実測値）+ スピーカー幅380mm
    # 左スピーカー: 左壁 + 110mm ~ 左壁 + 110mm + 380mm
    left_spk_x_inner = left_x + 0.11   # 左壁から110mm（実測値）
    left_spk_x_outer = left_spk_x_inner + speaker_width  # 110mm + 380mm = 490mm
    # 右スピーカー: 右壁 - 150mm - 380mm ~ 右壁 - 150mm
    right_spk_x_outer = right_x - 0.15  # 右壁から150mm（実測値）
    right_spk_x_inner = right_spk_x_outer - speaker_width  # 右壁から530mm

    # 3. 左シェルフ（スピーカーの下）
    # シェルフはスピーカーより広い範囲にあると想定
    left_shelf_mask = (
        (vertices[:, 2] < baffle_z + speaker_depth + 0.1) &  # バッフル+奥行+余裕
        (vertices[:, 0] > left_spk_x_inner - 0.05) &  # スピーカー内側端
        (vertices[:, 0] < left_spk_x_outer + 0.1) &   # スピーカー外側端+余裕
        (vertices[:, 1] > floor_y) &
        (vertices[:, 1] < shelf_top_y)
    )
    left_shelf = vertices[left_shelf_mask]
    result["regions"].append(analyze_region(left_shelf, "left_shelf"))

    # 4. 右シェルフ
    right_shelf_mask = (
        (vertices[:, 2] < baffle_z + speaker_depth + 0.1) &
        (vertices[:, 0] > right_spk_x_inner - 0.1) &  # スピーカー内側端-余裕
        (vertices[:, 0] < right_spk_x_outer + 0.05) & # スピーカー外側端
        (vertices[:, 1] > floor_y) &
        (vertices[:, 1] < shelf_top_y)
    )
    right_shelf = vertices[right_shelf_mask]
    result["regions"].append(analyze_region(right_shelf, "right_shelf"))

    # 5. 左スピーカー本体（シェルフ上〜ツイーター）
    # X: 左壁+110mm ～ 左壁+490mm (スピーカー幅380mm)
    # Z: バッフル面 ～ バッフル面+270mm (スピーカー奥行270mm)
    # Y: シェルフ上端 ～ シェルフ+580mm (スピーカー高さ580mm)
    left_speaker_mask = (
        (vertices[:, 2] > baffle_z - 0.02) &  # バッフル面付近（少し余裕）
        (vertices[:, 2] < baffle_z + speaker_depth + 0.02) &  # バッフル+奥行270mm
        (vertices[:, 0] > left_spk_x_inner - 0.02) &  # 左壁から110mm
        (vertices[:, 0] < left_spk_x_outer + 0.02) &  # 左壁から490mm
        (vertices[:, 1] > shelf_top_y - 0.02) &
        (vertices[:, 1] < speaker_top_y + 0.02)
    )
    left_speaker = vertices[left_speaker_mask]
    result["regions"].append(analyze_region(left_speaker, "left_speaker"))

    # 6. 右スピーカー本体
    # X: 右壁-530mm ～ 右壁-150mm (スピーカー幅380mm)
    right_speaker_mask = (
        (vertices[:, 2] > baffle_z - 0.02) &
        (vertices[:, 2] < baffle_z + speaker_depth + 0.02) &
        (vertices[:, 0] > right_spk_x_inner - 0.02) &  # 右壁から530mm
        (vertices[:, 0] < right_spk_x_outer + 0.02) &  # 右壁から150mm
        (vertices[:, 1] > shelf_top_y - 0.02) &
        (vertices[:, 1] < speaker_top_y + 0.02)
    )
    right_speaker = vertices[right_speaker_mask]
    result["regions"].append(analyze_region(right_speaker, "right_speaker"))

    # 7. 左ラック（スピーカー背面、前壁との間）
    # スピーカーと同じX範囲、バッフルより前壁側
    left_rack_mask = (
        (vertices[:, 2] < baffle_z - 0.02) &  # バッフルより前壁側
        (vertices[:, 0] > left_spk_x_inner - 0.05) &
        (vertices[:, 0] < left_spk_x_outer + 0.1) &
        (vertices[:, 1] > shelf_top_y) &
        (vertices[:, 1] < ceiling_y - 0.3)
    )
    left_rack = vertices[left_rack_mask]
    result["regions"].append(analyze_region(left_rack, "left_rack"))

    # 8. 右ラック
    right_rack_mask = (
        (vertices[:, 2] < baffle_z - 0.02) &
        (vertices[:, 0] > right_spk_x_inner - 0.1) &
        (vertices[:, 0] < right_spk_x_outer + 0.05) &
        (vertices[:, 1] > shelf_top_y) &
        (vertices[:, 1] < ceiling_y - 0.3)
    )
    right_rack = vertices[right_rack_mask]
    result["regions"].append(analyze_region(right_rack, "right_rack"))

    # 9. ソファ推定領域
    sofa_mask = (
        (vertices[:, 2] > 0.5) &
        (vertices[:, 1] > floor_y + 0.2) &
        (vertices[:, 1] < floor_y + 0.7)
    )
    sofa = vertices[sofa_mask]
    result["regions"].append(analyze_region(sofa, "sofa_estimated"))

    # 10. 床面
    floor_mask = vertices[:, 1] < floor_y + 0.1
    floor_area = vertices[floor_mask]
    result["regions"].append(analyze_region(floor_area, "floor"))

    # 11. 天井
    ceiling_mask = vertices[:, 1] > ceiling_y - 0.1
    ceiling_area = vertices[ceiling_mask]
    result["regions"].append(analyze_region(ceiling_area, "ceiling"))

    # 測定値の計算（新しい領域名に対応）
    left_spk_data = next((r for r in result["regions"] if r["name"] == "left_speaker"), None)
    right_spk_data = next((r for r in result["regions"] if r["name"] == "right_speaker"), None)
    left_shelf_data = next((r for r in result["regions"] if r["name"] == "left_shelf"), None)
    right_shelf_data = next((r for r in result["regions"] if r["name"] == "right_shelf"), None)
    left_rack_data = next((r for r in result["regions"] if r["name"] == "left_rack"), None)
    right_rack_data = next((r for r in result["regions"] if r["name"] == "right_rack"), None)
    sofa_data = next((r for r in result["regions"] if r["name"] == "sofa_estimated"), None)

    measurements = {}

    # 左スピーカー
    if left_spk_data and left_spk_data["vertex_count"] > 0:
        lb = left_spk_data["bounds"]
        measurements["left_speaker"] = {
            "from_left_wall_mm": int(abs(lb["x_min_m"] - left_x) * 1000),  # スピーカー左端から左壁
            "baffle_z_m": float(lb["z_max_m"]),  # バッフル面のZ座標
            "from_front_wall_mm": int(abs(lb["z_min_m"] - front_z) * 1000),  # 背面から前壁
            "tweeter_height_mm": int((lb["y_max_m"] - floor_y) * 1000),
            "bottom_height_mm": int((lb["y_min_m"] - floor_y) * 1000),
            "width_mm": int((lb["x_max_m"] - lb["x_min_m"]) * 1000),
            "depth_mm": int((lb["z_max_m"] - lb["z_min_m"]) * 1000),
        }

    # 右スピーカー
    if right_spk_data and right_spk_data["vertex_count"] > 0:
        rb = right_spk_data["bounds"]
        measurements["right_speaker"] = {
            "from_right_wall_mm": int(abs(right_x - rb["x_max_m"]) * 1000),  # スピーカー右端から右壁
            "baffle_z_m": float(rb["z_max_m"]),
            "from_front_wall_mm": int(abs(rb["z_min_m"] - front_z) * 1000),
            "tweeter_height_mm": int((rb["y_max_m"] - floor_y) * 1000),
            "bottom_height_mm": int((rb["y_min_m"] - floor_y) * 1000),
            "width_mm": int((rb["x_max_m"] - rb["x_min_m"]) * 1000),
            "depth_mm": int((rb["z_max_m"] - rb["z_min_m"]) * 1000),
        }

    # スピーカー間距離（左スピーカー右端〜右スピーカー左端）
    if left_spk_data and right_spk_data and left_spk_data["vertex_count"] > 0 and right_spk_data["vertex_count"] > 0:
        lb = left_spk_data["bounds"]
        rb = right_spk_data["bounds"]
        measurements["speaker_distance_mm"] = int(abs(rb["x_min_m"] - lb["x_max_m"]) * 1000)
        # センター間距離
        measurements["speaker_center_distance_mm"] = int(abs(right_spk_data["centroid"]["x_m"] - left_spk_data["centroid"]["x_m"]) * 1000)

    # シェルフ情報
    if left_shelf_data and left_shelf_data["vertex_count"] > 0:
        measurements["left_shelf"] = {
            "height_mm": int((left_shelf_data["bounds"]["y_max_m"] - floor_y) * 1000),
            "depth_mm": int((left_shelf_data["bounds"]["z_max_m"] - left_shelf_data["bounds"]["z_min_m"]) * 1000),
        }

    if right_shelf_data and right_shelf_data["vertex_count"] > 0:
        measurements["right_shelf"] = {
            "height_mm": int((right_shelf_data["bounds"]["y_max_m"] - floor_y) * 1000),
            "depth_mm": int((right_shelf_data["bounds"]["z_max_m"] - right_shelf_data["bounds"]["z_min_m"]) * 1000),
        }

    # ラック情報
    if left_rack_data and left_rack_data["vertex_count"] > 0:
        measurements["left_rack"] = {
            "depth_mm": int(abs(left_rack_data["bounds"]["z_max_m"] - front_z) * 1000),
            "top_height_mm": int((left_rack_data["bounds"]["y_max_m"] - floor_y) * 1000),
        }

    if right_rack_data and right_rack_data["vertex_count"] > 0:
        measurements["right_rack"] = {
            "depth_mm": int(abs(right_rack_data["bounds"]["z_max_m"] - front_z) * 1000),
            "top_height_mm": int((right_rack_data["bounds"]["y_max_m"] - floor_y) * 1000),
        }

    # リスニングポイント
    if sofa_data and sofa_data["vertex_count"] > 0:
        sc = sofa_data["centroid"]
        measurements["listening_point"] = {
            "from_front_wall_mm": int(abs(sc["z_m"] - front_z) * 1000),
            "seat_height_mm": int((sc["y_m"] - floor_y) * 1000),
            "ear_height_estimated_mm": int((sc["y_m"] - floor_y + 0.45) * 1000),
        }

        if left_spk_data and right_spk_data and left_spk_data["vertex_count"] > 0 and right_spk_data["vertex_count"] > 0:
            # スピーカー中央からの距離
            spk_center_x = (left_spk_data["centroid"]["x_m"] + right_spk_data["centroid"]["x_m"]) / 2
            spk_center_z = (left_spk_data["centroid"]["z_m"] + right_spk_data["centroid"]["z_m"]) / 2
            dist = np.sqrt((sc["x_m"] - spk_center_x)**2 + (sc["z_m"] - spk_center_z)**2)
            measurements["listening_point"]["from_speaker_center_mm"] = int(dist * 1000)

    result["measurements"] = measurements

    # 検証用コメント
    result["_notes"] = [
        "精度は±50mm程度と推定",
        "スピーカーや家具の領域は頂点密度から推定しており、実際の境界とは異なる可能性あり",
        "内振り角度は頂点データからは判定困難",
    ]

    # 詳細データ
    detailed = {}

    # XZ平面の密度マップ（床から見た配置、10cmグリッド）
    grid_size = 0.1
    x_bins = np.arange(left_x, right_x + grid_size, grid_size)
    z_bins = np.arange(front_z, back_z + grid_size, grid_size)
    density_map = []
    for i in range(len(x_bins) - 1):
        for j in range(len(z_bins) - 1):
            mask = (
                (vertices[:, 0] >= x_bins[i]) & (vertices[:, 0] < x_bins[i + 1]) &
                (vertices[:, 2] >= z_bins[j]) & (vertices[:, 2] < z_bins[j + 1])
            )
            count = mask.sum()
            if count > 0:
                density_map.append({
                    "x_m": float((x_bins[i] + x_bins[i + 1]) / 2),
                    "z_m": float((z_bins[j] + z_bins[j + 1]) / 2),
                    "count": int(count),
                })
    detailed["xz_density_map_10cm_grid"] = density_map

    # X軸ヒストグラム（壁や物体の位置）
    x_hist, x_edges = np.histogram(vertices[:, 0], bins=30)
    detailed["x_histogram"] = [
        {"x_m": float((x_edges[i] + x_edges[i + 1]) / 2), "count": int(x_hist[i])}
        for i in range(len(x_hist))
    ]

    # Z軸ヒストグラム
    z_hist, z_edges = np.histogram(vertices[:, 2], bins=40)
    detailed["z_histogram"] = [
        {"z_m": float((z_edges[i] + z_edges[i + 1]) / 2), "count": int(z_hist[i])}
        for i in range(len(z_hist))
    ]

    # Y軸ヒストグラム（高さ分布）
    y_hist, y_edges = np.histogram(vertices[:, 1], bins=30)
    detailed["y_histogram"] = [
        {"y_m": float((y_edges[i] + y_edges[i + 1]) / 2), "count": int(y_hist[i])}
        for i in range(len(y_hist))
    ]

    # 高さ別スライス（床から0.5m, 1.0m, 1.5mの水平断面）
    slice_heights = [0.5, 1.0, 1.5]
    detailed["horizontal_slices"] = {}
    for h in slice_heights:
        slice_y = floor_y + h
        slice_mask = (vertices[:, 1] > slice_y - 0.05) & (vertices[:, 1] < slice_y + 0.05)
        slice_verts = vertices[slice_mask]
        if len(slice_verts) > 0:
            detailed["horizontal_slices"][f"{h}m_from_floor"] = {
                "vertex_count": int(len(slice_verts)),
                "x_range_m": [float(slice_verts[:, 0].min()), float(slice_verts[:, 0].max())],
                "z_range_m": [float(slice_verts[:, 2].min()), float(slice_verts[:, 2].max())],
                "sample_points": [
                    {"x_m": float(v[0]), "z_m": float(v[2])}
                    for v in slice_verts[::max(1, len(slice_verts) // 50)]  # 最大50点サンプル
                ],
            }

    # 各領域の頂点サンプル
    region_masks = {
        "left_shelf": left_shelf_mask,
        "right_shelf": right_shelf_mask,
        "left_speaker": left_speaker_mask,
        "right_speaker": right_speaker_mask,
        "left_rack": left_rack_mask,
        "right_rack": right_rack_mask,
        "sofa_estimated": sofa_mask,
        "floor": floor_mask,
        "ceiling": ceiling_mask,
    }

    for region in result["regions"]:
        name = region["name"]
        if region["vertex_count"] > 0:
            if name in region_masks:
                mask = region_masks[name]
            elif name == "front_wall_area":
                mask = vertices[:, 2] < front_z + 0.5
            elif name == "back_wall_area":
                mask = vertices[:, 2] > back_z - 0.5
            else:
                continue

            region_verts = vertices[mask]
            sample_count = min(30, len(region_verts))
            indices = np.linspace(0, len(region_verts) - 1, sample_count, dtype=int)
            region["sample_vertices"] = [
                {"x_m": float(region_verts[i, 0]), "y_m": float(region_verts[i, 1]), "z_m": float(region_verts[i, 2])}
                for i in indices
            ]

    result["detailed_data"] = detailed

    # 出力
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Analysis saved to {output_path}")

    # サマリー表示
    print("\n=== Summary ===")
    print(f"Room: {result['room']['dimensions_mm']['width_x']}mm x {result['room']['dimensions_mm']['depth_z']}mm x {result['room']['dimensions_mm']['height_y']}mm")

    if "speaker_center_distance_mm" in measurements:
        print(f"Speaker center distance: {measurements['speaker_center_distance_mm']}mm")

    if "left_speaker" in measurements:
        ls = measurements["left_speaker"]
        print(f"Left speaker: {ls['from_left_wall_mm']}mm from left wall, tweeter at {ls['tweeter_height_mm']}mm")

    if "right_speaker" in measurements:
        rs = measurements["right_speaker"]
        print(f"Right speaker: {rs['from_right_wall_mm']}mm from right wall, tweeter at {rs['tweeter_height_mm']}mm")

    if "left_shelf" in measurements:
        print(f"Left shelf: height {measurements['left_shelf']['height_mm']}mm")

    if "left_rack" in measurements:
        print(f"Left rack: depth {measurements['left_rack']['depth_mm']}mm from front wall")

    if "listening_point" in measurements:
        lp = measurements["listening_point"]
        print(f"Listening point: {lp['from_front_wall_mm']}mm from front wall, ear height {lp['ear_height_estimated_mm']}mm")


if __name__ == "__main__":
    main()
