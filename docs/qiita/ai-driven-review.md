# ROS2 ロボット開発リポジトリに Claude API の AI 自動レビューを組み込んだ話

## きっかけ

最近、Streamlit（Pythonだけで動くWebアプリフレームワーク）の本体リポジトリにOSSコントリビューションをしていた。外部リンクの挙動修正、数値入力フィールドのエラー表示改善、といった小さめのPRを何件か出した。

そのときに気づいたことがある。Streamlit の CI は lint と型チェックとテストがしっかり整備されていて、push するたびに自動でチェックが走る。「YAML のインデントが」とか「未使用 import が」みたいな指摘は機械が全部やってくれて、人間のレビュアーはそういう細かいことを気にしなくていい。

自分のライトローバーリポジトリ（ROS2 + Raspberry Pi 4）を見ると、同じことが何もできていなかった。1人でコードを書いて1人でマージする。セルフレビューはしているつもりでも、YAML のインデントミスや未使用 import を何度もやらかしていた。

「Streamlit と同じ仕組みを自分のリポジトリにも入れよう」というのがきっかけだ。どうせなら lint だけでなく Claude API も繋いでみようと思った。

<!-- 画像: PR 一覧画面で ai:approved や ai:approved-with-warnings ラベルが付いている様子 -->

---

## コードがマージされるまでの流れ

仕組みを入れてから、PR がマージされるまでこういう流れになった。

```
コードを書く
    ↓
git commit
    └─ pre-commit が起動して lint チェック
       違反があればコミット中断
    ↓
git push → PR 作成
    ↓
GitHub Actions が走る
    ├── lint.yml  ... yamllint / ruff / xmllint
    └── ai-review.yml ... Claude API でコードレビュー
                              ↓
                         PR にコメント投稿
                         ラベル自動付与
                              ├── ai:approved
                              ├── ai:approved-with-warnings
                              └── ai:changes-requested
    ↓
ラベルを見て人間がマージ判断
```

<!-- 画像: GitHub Actions の Checks タブで lint と ai-review が両方 Pass している様子 -->

---

## まずルールを決める：CONTRIBUTING.md

自動化の前に、「何を守るか」を決めないと lint も AI レビューも基準がブレる。`CONTRIBUTING.md` に9つの PR ルールを書いた。

| # | ルール |
|---|--------|
| 1 | PR の前に Issue で宣言 |
| 2 | 1PR = 1スコープ |
| 3 | 新コード = 新テスト（TDD） |
| 4 | CI グリーン必須 |
| 5 | push 前に pre-commit を通す |
| 6 | コミットメッセージに対象パス |
| 7 | レビュー 1週間 SLO |
| 8 | カバレッジを下げない |
| 9 | good first issue ラベル活用 |

機械で強制できるルールは CI に任せる、という分担が大事だと思っている。ルール4（CI グリーン必須）は Branch Protection で強制、ルール5（pre-commit）はフックで強制する。ルール2（1PR = 1スコープ）のように判断が必要なものは AI レビューが指摘するか、人間が見る。

<!-- 画像: CONTRIBUTING.md を GitHub 上で表示しているスクリーンショット -->

---

## テストを先に書く：TDD

ルール3「新コード = 新テスト」を守るため、TDD（テスト駆動開発）で実装している。Red → Green → Refactor のサイクルだ。

Streamlit の OSS コントリビューションでこれを痛感した。テストを先に書かずに実装して push すると、「この分岐にテストがない」「エッジケースが抜けている」とAIレビューに毎回指摘される。修正 → push → 指摘 → 修正のループが続いて、そもそも最初からテストを先に書いていれば自分で気づけた問題だった。

```python
"""TelemetryBridge ノードのユニットテスト

TDD: Red → Green → Refactor

テスト方針:
  - 純粋ロジック関数（quaternion_to_yaw 等）は ROS2 なしで直接テストする
  - TelemetryBridge クラスのコールバックは rclpy と InfluxDBClient を
    モックして検証する
"""
```

ROS2 ノードのテストで困るのは「rclpy がないと import できない」問題だ。テスト環境に ROS2 を毎回インストールするのは現実的でないので、rclpy を MagicMock で差し替えて pytest が走るようにしている。テスト名には要件定義書の番号も入れた。

```python
def test_influxdb_error_does_not_crash(self):
    """InfluxDB への書き込みが失敗してもノードがクラッシュしないこと（AC-002-3）"""
```

テストがあると、AI が生成したコードをそのまま入れたときに「既存の動作を壊していないか」が即座にわかる。

<!-- 画像: pytest の実行結果がすべて PASSED になっているターミナルのスクリーンショット -->

---

## pre-commit：CI に届く前にローカルで弾く

```bash
pip install pre-commit
pre-commit install
```

これだけで `git commit` のたびに自動でチェックが走る。

```
$ git commit -m "fix: パラメータ修正"
yamllint.................................................Failed
- hook id: yamllint
- exit code: 1
config/nav2_params.yaml:12:3: [error] wrong indentation: expected 4 but found 2
```

CI で落ちてから気づくより、コミットの瞬間に気づく方がずっと楽だ。push と修正のサイクルを繰り返す手間がなくなる。

<!-- 画像: pre-commit がターミナルで lint 違反を検出してコミットを中断している様子 -->

---

## lint：機械的なミスを CI で自動検出

ROS2 のリポジトリは YAML・Python・XML が混在しているので、手書きだとミスが出やすい。

- **yamllint** ... GitHub Actions の設定ファイルや Nav2 のパラメータ YAML
- **ruff check** ... ROS2 ノードの Python（未使用 import、未定義変数など）
- **ruff format** ... Python のフォーマット統一
- **xmllint** ... launch ファイルの XML 構文チェック

lint に引っかかると PR に `✗` が付いて、diff の該当行に annotation が表示される。

<!-- 画像: GitHub Actions の lint ジョブが失敗して PR に ✗ が付いている様子 -->

<!-- 画像: ruff の lint エラーが PR の diff に annotation として表示されている様子 -->

AI レビューの前に lint で弾いておく理由がある。YAML のインデント指摘を AI にさせると API コストが無駄になるし、本質的なコメントがノイズに埋もれる。機械が見るべきものは機械に任せた方が、AI のコメントの質が上がる。

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

---

## AI レビュー：lint では見えない問題を指摘する

lint が通ったあと、Claude API が diff を読んでレビューする。エラー処理の漏れ、認証情報のハードコード、設計上の問題など、「構文は正しいけど意味的におかしい」部分を指摘してくれる。

README や `docs/` の修正には AI レビューは不要なので、`paths-ignore` でスキップしている。ドキュメントだけ直した PR で API を呼ぶのはもったいない。

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

実装はシンプルで、diff を取って Claude に投げてコメントとラベルを返すだけだ。

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

---

## ラベルで結果を一目で把握する

レビュー結果は3種類のラベルになって PR に付く。

- `ai:approved` ... 問題なし
- `ai:approved-with-warnings` ... 軽微な指摘あり
- `ai:changes-requested` ... 要修正

<!-- 画像: PR に ai:approved-with-warnings ラベルが付いている様子 -->

PR を出してから1〜2分後にはメールが届く。コーヒーを取りに行って戻ってきたら結果が来ているくらいのスピード感だ。

<!-- 画像: GitHub から届いた AI レビュー通知メールのスクリーンショット -->

---

## 実際に来たコメントの例

### 対応した指摘

```
**[Warning]** telemetry_bridge.py L.42
INFLUXDB_TOKEN を環境変数から取得していますが、
未設定時の処理がありません。未設定時に明示的なエラーを出すことを推奨します。
```

確かに未設定時にサイレント失敗していたので修正した。自分では気づいていなかった。

<!-- 画像: 上記コメントが PR に投稿されているスクリーンショット -->

### スキップした指摘

```
**[Info]** 変数名 x、y は意図が不明です。
```

ROS2 の標準メッセージフィールド（`pose.position.x`）なので変更不要だ。PR コメントで「ROS2 標準フィールド名のため変更しません」と返答した。スキップするときは理由を残しておかないと、あとで「なんで無視したんだっけ？」となる。

<!-- 画像: AI レビューへの返答コメントを書いているスクリーンショット -->

ちなみに「JSON で出力して」と指示すると Haiku は従わないことがある。Markdown で受け取ってキーワードで verdict を判定する方が安定した。

---

## AI Slop の話

2026年に入って、OSS の世界で「AI Slop（AI スロップ）」が大きな問題になっている。

curl は6年続けたバグバウンティプログラムを停止した。最初の21日間で20件のセキュリティレポートが来たが、実際の脆弱性は0件。全部 AI が生成した「もっともらしいが間違っている」内容だった。Ghostty は低品質な AI 生成コードの提出者を永久 BAN するポリシーを導入した。ただし Hashimoto はこう補足している。

> "This is not an anti-AI stance. This is an anti-idiot stance."

Streamlit の OSS コントリビューションをしていると、AI が書いたコードがそのまま投げられた PR を見ることがある。スタイルは整っているが、プロジェクトの設計方針を理解していない「動くけど筋の悪い」コードだ。メンテナーのコメントが「これ AI に書かせたでしょ」で終わる PR も見た。

ROS2 だと特に、学習データに ROS1 のコードが混じって `rospy.loginfo()` が混入することがある（ROS2 は `self.get_logger().info()`）。

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

今回の仕組みはこういうコードへの防壁にもなる。pre-commit で import が整理され、lint で構文が弾かれ、AI レビューが「ROS1 の API が混入しています」と指摘する。

AI にコードを書かせること自体は問題ない。問題は確認せずに投げること。**「AI が書いたから大丈夫」は存在しない。「自分が理解したから大丈夫」だけだ。**

<!-- 画像: AI Slop コードが ai:changes-requested ラベルで差し戻されているスクリーンショット -->

---

## 人間はゲートキーパー

AI と lint で自動化できるのは「コードの品質チェック」だけだ。最終的なマージ判断は人間がする。

`ai:approved` ラベルが付いていても、ライトローバーが実際に動くかどうかは CI にはわからない。仕様の正しさ、実機での動作確認、チームの意思決定は人間の仕事だ。

AI レビューは「自分が見落としているかもしれない部分を指摘してくれるアシスタント」であって、「最終承認者」ではない。Streamlit のメンテナーも AI レビューの結果だけでマージ判断はしていない。人間が見て、文脈を判断して、OKかどうかを決める。

<!-- 画像: ai:approved-with-warnings の PR を確認して人間がマージ判断しているコメントの様子 -->

---

## 何がうれしいか

入れてみて一番よかったのは、**1人開発でも「複数の目でレビューされた感覚」が得られる**ことだ。セルフレビューは自分の思い込みが抜けない。AI が均等に diff 全体を見てくれるのは地味にありがたい。

あとは YAML のインデント直しが人間の仕事じゃなくなったこと。自分のリポジトリなので全部自分でやるのだが、そういう機械的な指摘に時間を使わなくなった分、本質的な問題に集中できている。

ROS2 の開発は実機検証が必要で CI だけで全部カバーはできない。でも「CI を通してから実機で確認する」という習慣が自然に身についた。

---

## リポジトリ

実装はこちらで公開している。

[t0k0shi/lightrover-workspace](https://github.com/t0k0shi/lightrover-workspace)

- `.github/workflows/ai-review.yml`
- `.github/workflows/lint.yml`
- `scripts/review_pr.py`
- `.pre-commit-config.yaml`
- `CONTRIBUTING.md`
