# Room Documentation Workflow

部屋の3Dスキャンから詳細なレイアウト情報を抽出するワークフロー。

## 概要

1. **3Dスキャン取得** - iPhoneでPolycamを使って部屋をスキャン
2. **レンダリング生成** - Blenderで複数視点の画像を生成
3. **LLM初期分析** - 画像から配置と距離を推定
4. **対話式修正** - 人間が実測値や配置を補正
5. **詳細値抽出** - 頂点データから精密な座標を取得

## ファイル構成

```txt
room/
├── README.md          # このファイル
├── layout.md          # 部屋レイアウトの最終ドキュメント
├── analyze_scan.py    # OBJ頂点データ解析スクリプト
├── render_views.py    # Blenderレンダリングスクリプト
├── scan_analysis.json # analyze_scan.pyの出力
├── scans/
│   ├── room.glb       # Polycamマスターデータ
│   ├── room.obj       # OBJ形式（解析用）
│   └── room.mtl       # マテリアル定義
└── renders/
    └── room_*.png     # 視点別レンダリング画像
```

## 実行手順

### 1. 3Dスキャン取得

iPhoneのPolycamアプリで部屋をスキャン。glb形式でエクスポートして `scans/room.glb` に保存。

```bash
# glbからobjへ変換（assimpを使用）
assimp export room/scans/room.glb room/scans/room.obj
```

### 2. レンダリング生成

Blenderをヘッドレスモードで実行して16視点の画像を生成。

```bash
blender --background --python room/render_views.py
```

生成される視点:

- `room_01_top.png` - 真上（間取り図）
- `room_01_top.png` - 真上（間取り図）
- `room_02-05_corner_*.png` - 4コーナー俯瞰
- `room_06-09_wall_*.png` - 4壁面正面
- `room_10-11_elevation_*.png` - 側面図
- `room_12-15_internal_*.png` - 内部視点
- `room_16_floor.png` - 床面

### 3. LLM初期分析

生成した画像とglbファイルをLLMに渡して初期分析:

- 部屋の形状・寸法
- 家具・機材の配置
- スピーカー位置の推定

### 4. 対話式修正

人間がLLMの認識を確認・補正:

- ASCII配置図の確認
- 実測値の提供（側壁距離、シェルフ高さなど）
- 家具・設備の名称補正

### 5. 詳細値抽出

OBJファイルの頂点データから座標を抽出。

```bash
python room/analyze_scan.py
```

出力:

- コンソール: バウンディングボックス、各領域の座標
- `scan_analysis.json`: 構造化データ

## 注意事項

- 3Dスキャンの精度は±5cm程度
- 精密な値が必要な場合は実測値を使用
- layout.mdの値はスキャン推定値と実測値を併記
