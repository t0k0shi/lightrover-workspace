# Raspberry Pi のロボットで地図を作って自動走行させた！（SLAM / Nav2）

## チャレンジしたこと

Vstone社製の LiDAR搭載ライトローバー（Raspberry Pi 4 + YDLiDAR X2）で、部屋の通路地図を自動生成して、その地図を使ってロボットを自動走行させました。

ROS2 の SLAM と Nav2 という仕組みを使っています。SLAM は「周囲をレーザーで測定しながら地図を作る技術」、Nav2 は「作った地図の上でロボットが自律的に目的地まで走る仕組み」だ。

以前、[SkyWay × ROS2 で Gazebo シミュレーションをやった記事](https://engineers.ntt-west.co.jp/entry/2026/03/09/093000)を投稿させていただきました。当時、実機がなかったのでシミュレーターで実行していました。「実際に動くか」は実機でやって初めてわかることが、どれだけあるか？これと比較して記事を書きたいと思います。

## シミュレーションと実機の違い

やってみて実感した差異をまとめます。

| | シミュレーション | 実機 |
|--|-------------|------|
| 電源 | 無制限 | バッテリーまたは有線。充電・残量管理が必要 |
| ケーブル | なし | 有線給電の場合、ケーブルが動きを制限する。地図作成中にケーブルに引っ張られてロボットが止まる（見た目も小型犬を操ってる感じになる） |
| センサーノイズ | ほぼなし | LiDAR に CheckSum エラーが断続的に出る |
| 権限設定 | 不要 | I2C・USB デバイスのアクセス権設定が必要 |

特にケーブル問題は盲点で、かなり操作性がダウンする。SLAM で部屋を走り回らせようとしたとき、電源ケーブルの長さが行動範囲を制限してしまうので、モバイルバッテリーを持ちながら操作するという荒業を使いました。

<!-- 画像: ライトローバー実機の外観写真 -->

## 環境

| 項目 | 内容 |
|------|------|
| ロボット | Vstone ライトローバー |
| ボードPC | Raspberry Pi 4 Model B（4GB） |
| OS | Ubuntu MATE 22.04（ヴィストン公式イメージ） |
| ROS | ROS2 Humble |
| LiDAR | YDLiDAR X2（USB接続） |

セットアップ手順やエラーの対処は別記事にまとめます。

## 地図を作る（SLAM）

### 起動手順

ターミナルを3つ開く。`lightrover_ros` パッケージが見つからないといった内容のエラーが出る場合は、先に `source ~/ros2_ws/install/setup.bash` を実行する（`.bashrc` に書いておくと毎回不要になる）。

**ターミナル1（ロボット起動）**
```bash
source ~/ros2_ws/install/setup.bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

**ターミナル2（SLAM 起動）**
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch lightrover_ros lightrover_slam.launch.py
```

**ターミナル3（キーボード操縦）**
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/rover_twist
```

3つ起動したら、別ターミナルで RViz2 を開く。

**ターミナル4（RViz2）**
```bash
rviz2
```

起動したら左の「Add」ボタンから `By topic` → `/scan` と `/map` を追加する。キーボードでロボットを動かしながら部屋を走り回る。

### 動かしてみるとこうなる

RViz2 を見ると、ロボットの周囲にレーザーの点群（白い点）が広がっている。これが LiDAR がリアルタイムで測定した壁や障害物の位置だ。ロボットを動かすたびに、点群が積み重なって地図になっていく。最初は自分の周囲だけしか見えていないが、部屋を一周すると輪郭が出来上がってくる。壁が黒いライン、通れる場所が白、まだ見ていない場所がグレーで表示される。

<!-- 画像: RViz2 で /scan（点群）と /map（地図）を同時表示している様子 -->

ゆっくり動かした方が精度が上がる。急旋回や急加速をすると地図が歪む。

### 地図を保存する

部屋を一通り走り回ったら地図を保存する。

```bash
ros2 run nav2_map_server map_saver_cli -f ~/my_map
```

`my_map.pgm`（地図画像）と `my_map.yaml`（メタデータ）が生成される。pgm ファイルを画像ビューワで開くと白黒の2D地図が見える。白が通れる場所、黒が壁だ。

<!-- 画像: 保存された my_map.pgm を開いた様子（白黒の2D占有格子地図） -->

## 自動走行させる（Nav2）

### 起動手順

**ターミナル1（ロボット起動）**
```bash
source ~/ros2_ws/install/setup.bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

**ターミナル2（Nav2 + RViz2 起動）**
```bash
ros2 launch lightrover_navigation lightrover_navigation.launch.py \
  map:=~/my_map.yaml
```

RViz2 が立ち上がり、さっき作った地図が表示される。

<!-- 画像: RViz2 起動直後、地図が読み込まれた状態 -->

### RViz2 で目的地を指定する

1. 「2D Pose Estimate」をクリックして、地図上のロボットの現在位置をドラッグで指定する
2. 緑のパーティクル（小さな矢印の群れ）が広がればOK。ロボットが「自分はここにいる」と認識した状態だ
3. 「2D Nav Goal」をクリックして、目的地をドラッグで指定する
4. ロボットが自動で走り始める

2D Pose Estimate を省略しても AMCL がスキャンと地図を照合して自動で位置推定するため、ロボットが動くことはある。ただし精度は下がる。電源を入れ直すたびに位置がリセットされるので、毎回 Pose Estimate を入れた方が安定する。

<!-- 画像: 2D Pose Estimate 後にパーティクル（緑の矢印群）が広がっている様子 -->

<!-- 画像: ロボットが自律走行している様子（または動画） -->

### AMCL の精度を上げるには

自動走行の精度は AMCL（自己位置推定）の精度に依存する。精度が低いとロボットが地図上でズレた位置にいると認識し、壁に向かって走ったり途中で止まったりする。

**精度を上げる方法：**

- **2D Pose Estimate を丁寧に置く**：ロボットを部屋の角や壁際など「特徴的な場所」に置いてから Pose Estimate する。矢印の向きを実際のロボットの向きに合わせる（±10度以内が目安）。その後ロボットをその場で少し回転させるとパーティクルが収束する
- **地図の品質を上げる**：SLAM 時はゆっくり動かす。同じ場所を2〜3周すると地図が精緻になる。壁際を意識的に走ると輪郭がはっきりする
- **パーティクル数を増やす**：`nav2_params.yaml` の `max_particles` をデフォルト（2000）から増やすと精度が上がる。ただし Raspberry Pi では CPU 負荷も上がるので 3000 程度が現実的

### RViz2 のツールについて

**経路計画を表示したい場合**：「Add」→「By topic」→ `/plan`（Path）を追加する。2D Nav Goal を投げた直後に青い線が一瞬表示される。Nav2 は走行中に経路を再計画し続けるため、すぐに上書きされて消える。これは仕様どおりの動作だ。

**Publish Point**：ツールバーにあるが自動走行では使わない。地図上でクリックした座標を `/clicked_point` トピックに publish するツールで、「この点の座標を調べたい」ときに使う。

### launch ファイルのデフォルト地図名に注意

`lightrover_navigation.launch.py` のデフォルト地図名は `test.yaml` になっている。`map:=` で上書きしないと地図が読み込めないので注意。

```bash
# map:= で保存した地図を指定する
ros2 launch lightrover_navigation lightrover_navigation.launch.py \
  map:=~/my_map.yaml
```

## まとめ

| やったこと | 結果 |
|-----------|------|
| SLAM で地図生成 | ✅ 動作確認 |
| Nav2 で自動走行 | ✅ 動作確認 |

一番の発見は「LiDAR のエラーが出続けても SLAM は動く」だった。エラーログに惑わされず、`ros2 topic hz` でデータが実際に流れているかを確認するのが大事だとわかった。

## 参考リンク

- [ライトローバー公式 WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [公式 SLAM 手順](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/slam/)
- [公式 Nav2 手順](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/navigation/)
- [lightrover-workspace リポジトリ](https://github.com/t0k0shi/lightrover-workspace)
