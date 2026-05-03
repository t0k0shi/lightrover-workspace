# ROS2 ロボット開発リポジトリに Claude API の AI 自動レビューを組み込んだ話

## この記事について

1人で開発している ROS2 リポジトリに、lint + Claude API による自動レビューの仕組みを導入しました。この記事では、導入の動機から実装、実際に運用してわかったことまでをまとめています。

**この記事で扱う内容：**
- pre-commit → lint → AI レビュー → 人間判断、という4段構えの設計
- GitHub Actions + Claude API の実装
- ROS2 特有の落とし穴（YAML・XML 混在、ROS1 API の混入）
- 実際に来た AI コメントとその対応

## きっかけ：OSS で体験した「仕組みの力」

最近、Streamlit（Python だけで動く Web アプリフレームワーク）の本体リポジトリに OSS コントリビューションをしていました。外部リンクの挙動修正、数値入力フィールドのエラー表示改善、といった小さめの PR を何件か出しています。

そのときに気づいたことがあります。Streamlit の CI は lint と型チェックとテストがしっかり整備されていて、push するたびに自動でチェックが走ります。「YAML のインデントが」とか「未使用 import が」みたいな指摘は機械が全部やってくれるので、人間のレビュアーはそういう細かいことを気にしなくていい。

自分のライトローバーリポジトリ（ROS2 + Raspberry Pi 4）を見ると、同じことが何もできていませんでした。1人でコードを書いて1人でマージする。セルフレビューはしているつもりでも、YAML のインデントミスや未使用 import を何度もやらかしていました。

「Streamlit と同じ仕組みを自分のリポジトリにも持ち帰ろう」というのがきっかけです。どうせなら lint だけでなく Claude API も繋いで、セルフレビューの弱点を補う仕組みにしてみました。

<!-- 画像: PR 一覧画面で ai:approved や ai:approved-with-warnings ラベルが付いている様子 -->
![スクリーンショット 2026-04-17 152254.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/fe37eef0-6dea-4b6e-b7d1-ed0b635b244d.png)


## コードがマージされるまでの流れ

仕組みを入れてから、PR がマージされるまでの流れはこうなっています。

![スクリーンショット 2026-04-17 151819.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/864d6696-cd2d-4766-beb4-ec1da24ac13b.png)

ポイントは**4段構え**になっていることです。pre-commit（ローカル）→ lint（CI）→ AI レビュー（CI）→ 人間。各段階で拾えるものが違うので、後段になるほど本質的な問題に集中できます。

<!-- 画像: GitHub Actions の Checks タブで lint と ai-review が両方 Pass している様子 -->
![スクリーンショット 2026-04-17 152514.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/cf8574cc-c7ce-4508-a5c4-d08bc5d7b39f.png)


## まずルールを決める：CONTRIBUTING.md

自動化の前に、「何を守るか」を決めないと lint も AI レビューも基準がブレます。`CONTRIBUTING.md` に 9 つの PR ルールを書きました。OSS なら、PR を出すときはみんなここを読むので、全部思いをのせます。

| # | ルール | 強制方法 |
|---|--------|---------|
| 1 | PR の前に Issue で宣言 | 人間 |
| 2 | 1PR = 1スコープ | AI レビュー / 人間 |
| 3 | 新コード = 新テスト（TDD） | AI レビュー / 人間 |
| 4 | CI グリーン必須 | Branch Protection |
| 5 | push 前に pre-commit を通す | pre-commit フック |
| 6 | コミットメッセージに対象パス | 人間 |
| 7 | レビュー 1週間 SLO | 人間 |
| 8 | カバレッジを下げない | CI |
| 9 | good first issue ラベル活用 | 人間 |

機械で強制できるルールは CI に任せます。判断が必要なものは AI レビューが指摘するか、人間が見ます。このルール表を先に作ったことで、あとの自動化がスムーズに進みました。

<!-- 画像: CONTRIBUTING.md を GitHub 上で表示しているスクリーンショット -->
![スクリーンショット 2026-04-17 152632.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/3bab5d0e-a5f1-4bb8-aadb-ba0bcfcd94e3.png)


## テストを先に書く：TDD

ルール 3「新コード = 新テスト」を守るために、TDD（テスト駆動開発）で実装しています。

Streamlit の OSS コントリビューションでこれを痛感しました。テストを先に書かずに実装して push すると、「この分岐にテストがない」「エッジケースが抜けている」と AI レビューに毎回指摘されます。修正 → push → 指摘 → 修正のループが続いて、最初からテストを先に書いていれば自分で気づけた問題でした。

ROS2 ノードのテストで困るのは「rclpy がないと import できない」問題です。テスト環境に ROS2 を毎回インストールするのは現実的でないので、rclpy を MagicMock で差し替えて pytest が走るようにしました。

```python
"""TelemetryBridge ノードのユニットテスト

TDD: Red → Green → Refactor

テスト方針:
  - 純粋ロジック関数（quaternion_to_yaw 等）は ROS2 なしで直接テストする
  - TelemetryBridge クラスのコールバックは rclpy と InfluxDBClient を
    モックして検証する
"""
```

テスト名には要件定義書の番号も入れています。テストが何の要件に対応しているか、あとから追いやすくするためです。

```python
def test_influxdb_error_does_not_crash(self):
    """InfluxDB への書き込みが失敗してもノードがクラッシュしないこと（AC-002-3）"""
```

テストがあると、AI が生成したコードをそのまま入れたときに「既存の動作を壊していないか」が即座にわかります。20 件のテストが 0.36 秒で全件パスする状態を維持しています。

```
$ python3 -m pytest telemetry/bridge/tests/test_telemetry_bridge.py -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-7.4.4
collected 20 items

telemetry/bridge/tests/test_telemetry_bridge.py::TestQuaternionToYaw::test_180_degree_rotation PASSED [  5%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestQuaternionToYaw::test_90_degree_rotation PASSED [ 10%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestQuaternionToYaw::test_identity_quaternion_returns_zero PASSED [ 15%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestQuaternionToYaw::test_negative_rotation PASSED [ 20%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_all_required_fields_exist PASSED [ 25%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_measurement_name_is_robot_telemetry PASSED [ 30%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_pos_x_and_pos_y_fields PASSED [ 35%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_robot_id_tag_is_set PASSED [ 40%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_speed_is_sqrt_of_linear_velocities PASSED [ 45%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_speed_is_zero_when_stationary PASSED [ 50%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestOdomMsgToPoint::test_yaw_is_derived_from_quaternion PASSED [ 55%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestCmdvelMsgToPoint::test_linear_x_and_angular_z_fields PASSED [ 60%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestCmdvelMsgToPoint::test_measurement_name_is_cmd_vel PASSED [ 65%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestCmdvelMsgToPoint::test_only_two_fields_exist PASSED [ 70%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestCmdvelMsgToPoint::test_robot_id_tag_is_set PASSED [ 75%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestTelemetryBridgeCallbacks::test_cmdvel_callback_calls_write PASSED [ 80%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestTelemetryBridgeCallbacks::test_cmdvel_influxdb_error_does_not_crash PASSED [ 85%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestTelemetryBridgeCallbacks::test_influxdb_error_does_not_crash PASSED [ 90%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestTelemetryBridgeCallbacks::test_odom_callback_calls_write PASSED [ 95%]
telemetry/bridge/tests/test_telemetry_bridge.py::TestTelemetryBridgeCallbacks::test_robot_id_from_env PASSED [100%]

============================== 20 passed in 0.36s ==============================
```

## pre-commit：CI に届く前にローカルで弾く

```bash
pip install pre-commit
pre-commit install
```

これだけで `git commit` のたびに自動でチェックが走ります。

```
$ git commit -m "fix: パラメータ修正"
yamllint.................................................Failed
- hook id: yamllint
- exit code: 1
config/nav2_params.yaml:12:3: [error] wrong indentation: expected 4 but found 2
```

CI で落ちてから気づくより、コミットの瞬間に気づく方がずっと楽です。push → CI 失敗 → 修正 → push のサイクルを繰り返す手間がなくなります。

## lint：機械的なミスを CI で自動検出

ROS2 のリポジトリは YAML・Python・XML が混在しているので、手書きだとミスが出やすい構成です。以下のツールで検出しています。

- **yamllint** ... GitHub Actions の設定ファイルや Nav2 のパラメータ YAML
- **ruff check** ... ROS2 ノードの Python（未使用 import、未定義変数など）
- **ruff format** ... Python のフォーマット統一
- **xmllint** ... launch ファイルの XML 構文チェック

lint に引っかかると PR に `✗` が付いて、diff の該当行に annotation が表示されます。

<!-- 画像: GitHub Actions の lint ジョブが失敗して PR に ✗ が付いている様子 -->
![スクリーンショット 2026-04-17 153642.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/1ba0f898-8b4b-4d01-bc0f-16e711f5cd55.png)

<!-- 画像: ruff の lint エラーが PR の diff に annotation として表示されている様子 -->
![スクリーンショット 2026-04-17 155221.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/5592dd08-2e1f-4f7e-aa65-afe6fa8a0cff.png)

**AI レビューの前に lint で弾いておく理由があります。** YAML のインデント指摘を AI にさせると API コストが無駄になりますし、本質的なコメントがノイズに埋もれます。機械が見るべきものは機械に任せた方が、AI のコメントの質が上がります。

```yaml
# .github/workflows/lint.yml（抜粋）
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: yamllint
        run: yamllint .
      - name: ruff check
        run: ruff check .
      - name: ruff format
        run: ruff format --check .
      - name: xmllint
        run: xmllint --noout $(find . -name "*.xml" -o -name "*.launch")
```

## AI レビュー：lint では見えない問題を指摘する

lint が通ったあと、Claude API が diff を読んでレビューします。エラー処理の漏れ、認証情報のハードコード、設計上の問題など、「構文は正しいけど意味的におかしい」部分を指摘してくれます。

README や `docs/` の修正には AI レビューは不要なので、`paths-ignore` でスキップしています。

```yaml
on:
  pull_request_target:
    types: [opened, synchronize, reopened]
    paths-ignore:
      - "**.md"
      - "docs/**"
      - "**.rst"
      - "**.txt"
```

実装はシンプルです。diff を取って Claude に投げて、コメントとラベルを返すだけです。

```python
# scripts/review_pr.py（概念）
diff = get_pr_diff(pr_number, github_token)

response = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": REVIEW_PROMPT.format(diff=diff)}]
)

label = determine_label(response.content[0].text)
post_review_comment(pr_number, response.content[0].text, github_token)
add_label(pr_number, label, github_token)
```

### ラベルで結果を一目で把握する

レビュー結果は 3 種類のラベルになって PR に付きます。

| ラベル | 意味 |
|--------|------|
| `ai:approved` | 問題なし |
| `ai:approved-with-warnings` | 軽微な指摘あり |
| `ai:changes-requested` | 要修正 |

PR を出してから 1〜2 分後にはメールが届きます。コーヒーを取りに行って戻ってきたら結果が来ているくらいのスピード感です。

<!-- 画像: PR に ai:approved-with-warnings ラベルが付いている様子 -->
![スクリーンショット 2026-04-17 155407.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/15959/da6caa69-256e-45f1-a311-f259b7ec1f74.png)

### 実際に来たコメントの例

**対応した指摘：**

```
【Warning】write_api の呼び出し箇所を確認してください。
SYNCHRONOUS モードでは書き込みがブロッキングになるため、
ROS2 スピンループでブロッキングが発生しないか確認してください。
```

コールバック内で `write_api` を呼んでいたので、実際にスピンループへの影響を確認しました。InfluxDB への書き込みが詰まった際の挙動を検証して問題ないことを確かめてからマージしています。「非同期から同期に変えるだけ」と思っていましたが、ROS2 のコールバック構造との組み合わせは盲点でした。

<!-- 画像: 上記コメントが PR に投稿されているスクリーンショット -->

**スキップした指摘：**

```
Info: コメント言語の統一性を確認してください。
ファイル内の他のコメントが英語の場合、一貫性のため英語への統一を検討してください。
```

このリポジトリは日本語コメントで統一しているので変更不要です。PR コメントで「プロジェクト方針として日本語コメントを採用しているため対応しません」と返答しました。**スキップするときは理由を残しておくのが大事です。** あとで「なんで無視したんだっけ？」となるのを防げます。

<!-- 画像: AI レビューへの返答コメントを書いているスクリーンショット -->

### 実装上のハマりどころ

Claude に「JSON で出力して」と指示しても、モデルやプロンプトによっては従わないことがあります。Markdown で受け取ってキーワードで verdict を判定する方が安定しました。

## AI にコードを書かせること、投げること

2026 年に入って、OSS の世界では AI が生成したコードをそのまま投げる行為が問題になっています。

curl のメンテナーはバグバウンティプログラムを停止しました。理由は、AI が生成した「もっともらしいが実際には誤っている」レポートが大量に届いたためです。Ghostty は低品質な AI 生成コードの提出者を永久 BAN するポリシーを導入しています。ただしこれは AI の利用自体を否定しているのではなく、確認せずに投げる行為への対策です。

Streamlit の OSS コントリビューションをしていても、AI が書いたコードがそのまま投げられた PR を見ることがあります。スタイルは整っているのですが、プロジェクトの設計方針を理解していないコードです。

ROS2 だと特に、学習データに ROS1 のコードが混入して `rospy.loginfo()` が出てくることがあります（ROS2 は `self.get_logger().info()`）。

```python
# AI が生成しがちな問題コード
def publish_velocity(self, linear_x, angular_z):
    msg = Twist()
    msg.linear.x = linear_x
    msg.linear.z = 0.0
    msg.angular.z = angular_z
    self.publisher_.publish(msg)
    rospy.loginfo(f"Published: {linear_x}, {angular_z}")  # ROS1 の API
```

今回の仕組みはこういうコードへの防壁にもなります。pre-commit で import が整理され、lint で構文が弾かれ、AI レビューが「ROS1 の API が混入しています」と指摘します。

AI にコードを書かせること自体は問題ありません。問題は確認せずに投げることです。

## まとめ：仕組みが守るもの、人間が守るもの

導入してみて一番よかったのは、**1人開発でも「複数の目でレビューされた感覚」が得られる**ことです。セルフレビューは自分の思い込みが抜けません。AI が均等に diff 全体を見てくれるのは地味にありがたいです。

ただし、この仕組みで自動化できるのは「コードの品質チェック」までです。`ai:approved` ラベルが付いていても、ライトローバーが実際に動くかどうかは CI にはわかりません。仕様の正しさ、実機での動作確認、チームの設計判断は人間の仕事です。

各段階で拾えるものをまとめると、こうなります。

| 段階 | 拾えるもの | 拾えないもの |
|------|-----------|-------------|
| pre-commit | インデント、フォーマット | — |
| lint（CI） | 未使用 import、構文エラー、型違反 | 意味的な問題 |
| AI レビュー | エラー処理漏れ、認証情報のハードコード、ROS1 API 混入 | プロジェクトの暗黙知、実機での動作 |
| 人間 | 仕様の正しさ、設計判断、実機確認 | （見落とし → 上の3段で補完） |

Streamlit の OSS コントリビューションで学んだのは、「仕組みが整っているリポジトリでは、人間のレビュアーが本質的な議論に集中できる」ということでした。1人開発でも同じことが言えます。機械的なチェックを仕組みに任せた分、実機検証や設計判断に集中できるようになりました。

## リポジトリ

実装はこちらで公開しています。

[t0k0shi/lightrover-workspace](https://github.com/t0k0shi/lightrover-workspace)

- `.github/workflows/ai-review.yml`
- `.github/workflows/lint.yml`
- `scripts/review_pr.py`
- `.pre-commit-config.yaml`
- `CONTRIBUTING.md`
