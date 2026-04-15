# DDS クロスマシン通信セットアップ

## 概要

Raspberry Pi（ロボット）と PC（rviz2・テレオペ）が同一ネットワーク上で
ROS 2 トピックを共有するための設定手順。

ROS 2 は DDS（Data Distribution Service）をミドルウェアに使用しており、
デフォルトでマルチキャストによりノードを自動探索します。
ただし、Wi-Fi ルーターやネットワーク構成によってはマルチキャストがブロックされるため、
ユニキャスト設定が必要になる場合があります。

---

## 前提条件

- [ ] Raspberry Pi と PC が **同一ネットワーク（同一サブネット）** に接続されている
- [ ] 両機で **同じ `ROS_DOMAIN_ID`** が設定されている（`hardware-checklist.md` セクション6参照）
- [ ] 両機の ROS 2 バージョンが一致している（Humble）

---

## Step 1: ネットワーク疎通確認

```bash
# PC から Raspberry Pi に ping
ping <Raspberry_Pi_IP>

# Raspberry Pi から PC に ping
ping <PC_IP>
```

- [ ] 双方向で ping が通ること

---

## Step 2: ROS_DOMAIN_ID の確認（両機）

```bash
echo $ROS_DOMAIN_ID
```

- [ ] Raspberry Pi と PC で **同じ値**（例: `1`）が表示されること
- [ ] 異なる場合は `.bashrc` を修正して `source ~/.bashrc` を実行

---

## Step 3: マルチキャスト動作確認

### Raspberry Pi 側（ロボット起動）

```bash
ros2 launch lightrover_ros nav_base.launch.py
```

### PC 側（トピック探索）

```bash
ros2 topic list
```

- [ ] `/scan`、`/odom`、`/rover_twist` 等が PC 側に表示されること

**表示されない場合 → Step 4（ユニキャスト設定）へ進む**

---

## Step 4: ユニキャスト設定（マルチキャストがブロックされる場合）

Wi-Fi 環境ではマルチキャストがブロックされることがあります。
その場合、DDS にピア（通信相手）のIPを直接指定します。

### 4-1. Fast DDS の場合（ROS 2 Humble デフォルト）

**両機に設定ファイルを作成:**

```bash
cat > ~/fastdds_unicast.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <participant profile_name="unicast_profile" is_default_prof="true">
    <rtps>
      <builtin>
        <metatrafficUnicastLocatorList>
          <locator/>
        </metatrafficUnicastLocatorList>
        <initialPeersList>
          <locator>
            <udpv4>
              <!-- 通信相手のIPアドレスを記載 -->
              <address>192.168.x.x</address>
            </udpv4>
          </locator>
        </initialPeersList>
      </builtin>
    </rtps>
  </participant>
</profiles>
EOF
```

**`.bashrc` に追記（両機）:**

```bash
echo "export FASTRTPS_DEFAULT_PROFILES_FILE=~/fastdds_unicast.xml" >> ~/.bashrc
source ~/.bashrc
```

- [ ] Raspberry Pi 側の XML に **PC の IP アドレス**を記載
- [ ] PC 側の XML に **Raspberry Pi の IP アドレス**を記載

### 4-2. Cyclone DDS の場合（代替 DDS）

```bash
cat > ~/cyclone_dds.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
      <Interfaces>
        <NetworkInterface name="wlan0" />
      </Interfaces>
    </General>
    <Discovery>
      <Peers>
        <Peer address="192.168.x.x"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
EOF

echo "export CYCLONEDDS_URI=file://$HOME/cyclone_dds.xml" >> ~/.bashrc
echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
```

> Cyclone DDS を使う場合は両機で `sudo apt install ros-humble-rmw-cyclonedds-cpp` が必要

---

## Step 5: 動作確認

### Raspberry Pi 側

```bash
ros2 launch lightrover_ros nav_base.launch.py
```

### PC 側（rviz2 で可視化）

```bash
# LiDAR スキャンデータの確認
ros2 topic echo /scan

# rviz2 で可視化
rviz2
```

- [ ] PC 側で `/scan` データが受信できること
- [ ] rviz2 に LiDAR のスキャン形状が表示されること

### PC 側からロボットを操作（テレオペ確認）

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap cmd_vel:=/rover_twist
```

- [ ] キー入力でロボットが動作すること

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `ros2 topic list` に何も出ない | マルチキャストブロック または DOMAIN_ID 不一致 | Step 2 確認 → Step 4 へ |
| トピックは見えるがデータが届かない | ファイアウォール（UFW 等） | `sudo ufw allow in proto udp` または UFW 無効化 |
| rviz2 で TF エラーが出る | 時刻同期のずれ | `sudo apt install chrony` で NTP 同期 |
| XML ファイルが読み込まれない | パスが通っていない | `echo $FASTRTPS_DEFAULT_PROFILES_FILE` で確認 |

---

## ハマりどころ記録欄

| 症状 | 原因 | 解決方法 |
|------|------|---------|
| | | |

---

## 参考リンク

- [ROS 2 DDS チューニング](https://docs.ros.org/en/humble/How-To-Guides/DDS-tuning.html)
- [Fast DDS ユニキャスト設定](https://fast-dds.docs.eprosima.com/en/latest/fastdds/discovery/simple.html)
- [Cyclone DDS 設定](https://cyclonedds.io/docs/cyclonedds/latest/config/config.html)
