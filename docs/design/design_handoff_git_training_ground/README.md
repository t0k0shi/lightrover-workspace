# Handoff: git-training-ground トップページ

## Overview

`git-training-ground` は、Git/GitHub の初心者が **フォーク → 編集 → PR → レビュー** という一連の OSS 貢献フローを、安全に練習できる「練習場」リポジトリ。このハンドオフは、そのトップページ（ランディング / 参加者一覧 / チュートリアル）のデザイン一式です。

参加者は `contributors.json` に自分のエントリを追加する PR を出すことで参加し、そのエントリ（絵文字・GitHub アバター・好きな色・メッセージ）がトップページに反映されます。

---

## About the Design Files

`design/` フォルダに入っている HTML / CSS / JSX は **デザインの参考実装（プロトタイプ）** です。ピクセル・コピー・配置・アニメーション・インタラクションの意図を示すためのもので、そのままプロダクションに投入するコードではありません。

タスクは、このデザインを **ターゲットのコードベース（Next.js 15 + TypeScript + TailwindCSS）** のパターン・ライブラリ・ディレクトリ構造に合わせて作り直すことです。

- プロトタイプは 1 ファイル内に Babel + インライン React で動作しており、コンポーネント分割・State 管理・アセット取り扱いは意図的にラフです。Next.js 側では適切な `app/` ルーター構成 / Server Component / Client Component 分離に落とし込んでください。
- スタイルはプレーン CSS で書いてありますが、本番では Tailwind クラスに翻訳してください（値は後述の Design Tokens を参照）。

---

## Fidelity

**High-fidelity (hifi)**。色・タイポ・スペーシング・角丸・影・アニメーション速度など、指定値どおりに再現してください。オリジナルデザインなので、既存のどのサイトの模倣でもありません。

---

## Tech Target

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS（必要に応じて CSS Modules / 独自 `globals.css` 拡張）
- **Deploy**: GitHub Pages or Vercel
- **Fonts**: Google Fonts の `next/font` 経由で読み込み（Noto Sans JP, Inter, JetBrains Mono）

---

## Page Structure

トップページは縦1カラムのスクロールページで、以下の 6 セクションから構成されます。

### 1. Hero
- **目的**: プロジェクトの 1 行価値と、即時参加 CTA を提示
- **レイアウト**: 画面幅いっぱいの背景に、センター揃え 780px の copy column。背景には参加者の「浮遊バブル」が散らばる
- **要素**:
  - ナビ（左: brand `git-training-ground`、右: チュートリアル / 参加者 / Repo リンク）
  - エイブロウ: ドット + `first contribution, first win`
  - 見出し 3 行 / H1（うち 1 行は黄色下線のハイライト装飾）
  - リード文（`contributors.json` を `<code>` で強調）
  - CTA 3 つ: 「参加する →」(primary) / 「リポジトリを見る」(ghost) / share (icon)
  - **ライブカウンターカード**（中央）
    - 左: 大きな数字 `{count}` + 「人」+ `参加中 LIVE ● 今週 +N 人`
    - 右: 最新 6 名のバブル + 「…」
    - 外枠: 4px オフセットの hard shadow（`box-shadow: 4px 4px 0 var(--ink)`）
  - フロート `scroll` インジケータ（下部中央）
- **浮遊バブル配置ロジック**: 決定論的（seed = 42）。hero 領域を 4 ゾーン（左帯・右帯・上帯・下帯）に分け、中央の copy column を避ける。バブル 1 個あたりランダム tilt/scale/animation-delay/duration（3.5〜7s）

### 2. Concept
- セクションキッカー「concept」＋見出し「共同作業を実践して、Git に "カラダ" で慣れる。」
- 説明段落 1 つ
- 3 列タイル（`01 失敗OK` / `02 小さく` / `03 みんなで`）— 各タイルは 3px hard shadow 付きカード

### 3. Help Wanted (code block)
- 2 カラム（左: コピー + 3 つのチェックリスト、右: `contributors.json` の差分風コードブロック）
- コードブロックはダークテーマ（`#0F1419` 背景）、macOS 風 traffic light + `main` ブランチ pill
- 差分の緑ハイライト（line 30–37 が追加行）
- 末尾に右寄せ serif バブル `面白そう🌈… でも、なんだか難しそう…？🤔`

### 4. Steps Timeline
- 縦タイムライン、8 ステップがジグザグに左右交互配置
- 中央に **波打った破線 SVG**（path `M20 0 C 32 200, 8 360, 20 560 S 32 900, 20 1100 S 8 1500, 20 1800`、`stroke-dasharray:2 6`, opacity .35）
- 各ステップは `step-node`（72px 丸、アクセントボーダー、絵文字 36px、3px hard shadow）＋ `step-body`
  - `STEP 01` (mono, muted) / hint pill（`Fork` など）
  - 見出し（20px bold）
  - コマンド `$ git clone ...`（ダーク bg の inline code）
- 末尾: 「READMEで詳しく見る」outline ボタン + 左寄せ serif バブル `思ったより簡単だった…！✨ さっそく PR 投げてみる💨`

### 5. Contributors Gallery
- セクションキッカー「the playground」＋見出し「一緒に練習中の {count} 人」
- 右にセグメントコントロール `全員 / 今週の新顔 {n}`
- グリッド: `repeat(auto-fill, minmax(180px, 1fr))`、gap 12px
- 各カード: 絵文字（左上）＋ アバター（右上）＋ `@github-handle` ＋ `「message」` ＋ 参加日 `YYYY/MM/DD`
  - favoriteColor を border と外側のソフトグロー（`box-shadow: 0 0 0 4px color-mix(...)`）に使う
  - 7 日以内は `NEW` バッジ

### 6. Footer
- 円形スタンプ（`{count}人が参加中`、3px アクセント色の hard shadow）
- 超特大テキスト `DOMO・ARIGATO !!`（8 vw）
  - 1 文字ずつ順番にバウンスアニメーション（`@keyframes bounce`、3s 間隔、100ms ずつディレイ）
  - 偶数番目とエクスクラメーションがアクセント色
- 感謝メッセージ（2 行）
- CTA 2 つ（「いますぐ参加する」「このページをシェア」）
- メタ行（著作、MIT、Made with 🍵 & ☕）
- 背景: dots パターン + 上から下へ `--bg → --bg-2` グラデ

---

## Design Tokens

```css
/* Colors */
--bg:        #FBF6EE;   /* クリームペーパー */
--bg-2:      #F3ECDE;   /* フッター用 1 段暗いクリーム */
--ink:       #1C1B1A;   /* テキスト / ボーダー */
--ink-2:     #3A3732;   /* 本文 */
--muted:     #78736A;   /* キャプション */
--line:      #E3DAC6;   /* 罫線 */
--paper:     #FFFDF7;   /* カード背景 */
--accent:    #E63946;   /* 既定アクセント（tweakable） */

/* Radius */
sm: 6px, md: 8px, lg: 12px, xl: 14px, 2xl: 18px, pill: 999px

/* Shadows */
card:        3px 3px 0 var(--ink)       /* concept / step-node */
card-lg:     4px 4px 0 var(--ink)       /* counter */
code:        5px 5px 0 var(--ink)       /* code block */
glow(c):     0 0 0 4px color-mix(in srgb, <c> 8%, transparent)  /* 参加者カード */

/* Typography */
body:        "Noto Sans JP" 400, line-height 1.7-1.9, font-feature-settings:"palt" 1
headline:    "Noto Sans JP" 900, letter-spacing -0.025em, line-height 1.05-1.2
mono:        "JetBrains Mono" 400/500/700

/* Scale */
hero H1:     clamp(42px, 6.5vw, 84px)
section H2:  clamp(30px, 3.6vw, 44px)
tile H3:     22px / 800
step H3:     20px / 800
body:        14-15px
caption/mono: 10-12px

/* Spacing (main) */
section pad: 80-120px 上下
container max: 780 / 860 / 1080 px
nav pad: 22px 44px

/* Motion */
float:       5s ease-in-out infinite, Y ±12px
pulse (live dot): 1.4s
bounce (arigato): 3s, stagger 100ms/char
hover bubble: transform: scale(1.08), 200ms
```

---

## Data Shape

`contributors.json` の 1 エントリ:

```ts
type Contributor = {
  name: string;           // 表示名（使わなくても可）
  github: string;         // GitHub handle (URL または username どちらでも。抽出ロジック必要)
  favoriteColor: string;  // "#RRGGBB"
  favoriteEmoji: string;  // 1 絵文字
  message: string;        // 1 行自己紹介
  joinedAt: string;       // "YYYY-MM-DD"
};
```

- アバター URL: `https://github.com/${handle}.png?size=80`（onError 時は非表示にフェイルセーフ）
- `NEW` バッジ判定: `joinedAt` から 7 日以内
- カウンター値: `contributors.length`

---

## Interactions & Behavior

| 要素 | 動き |
|---|---|
| 浮遊バブル | CSS keyframe で Y ±12px、ホバーで `.bubble-pill { transform: scale(1.08) }` + `filter: brightness(1.05) drop-shadow(...)` |
| バブルホバー | マウス座標追従のツールチップ（`@github` / `joined YYYY/MM/DD` / `「message」`）。ボーダー色は favoriteColor |
| ライブカウンター | マウント時 0 → target へ `requestAnimationFrame` で ease-out-cubic、1800ms。rAF stall 対策で setTimeout フォールバック |
| LIVE ドット | 1.4s パルスアニメ |
| セグメントコントロール | `全員 / 今週の新顔`。後者は `daysAgo(joinedAt) <= 7` でフィルタ |
| 参加者カード | `:hover` で `translateY(-2px)` + 外側グローが濃く |
| DOMO ARIGATO | 文字単位のバウンス、3s 間隔で 100ms ずつディレイ |

### Responsive
- `< 820px`:
  - ナビのテキストリンク非表示（Repo ボタンのみ）
  - Help Wanted と Concept tiles を 1 カラムに
  - タイムラインのジグザグを全ステップ左寄せに統一
  - step-node を 56px / 絵文字 26px に縮小
  - ライブカウンターを縦積み
  - Hero パディングを 60px 20px 100px に

---

## State Management

最小限。App Router でも Client Component はごく一部。

```ts
// (Client) Hero — バブル座標はマウント時に deterministic 計算して useMemo
// (Client) LiveCount — useState + useEffect + rAF
// (Client) ContributorsSection — filter: "all" | "new"
// (Client) Tooltip — hover state
// (Server) 残り全部（静的）
```

`contributors.json` は Server Component でビルド時読み込み → 下流に props として渡す。

---

## Validation / CI 要件

- `contributors.json` の形式チェック（name / github / favoriteColor / favoriteEmoji / message / joinedAt が全て揃っているか、型が正しいか）を GitHub Actions で実行
- `favoriteColor` は `/^#[0-9A-Fa-f]{6}$/` にマッチすること
- `joinedAt` は `YYYY-MM-DD`
- 重複 handle はエラー

---

## Assets

- フォント: Google Fonts（Noto Sans JP / Inter / JetBrains Mono）を `next/font/google` 経由で読み込み
- アバター画像: GitHub の public CDN（`https://github.com/{handle}.png`）。Next Image を使う場合は `next.config.js` の `images.remotePatterns` に `github.com` を追加
- 絵文字: OS ネイティブレンダリング（絵文字フォントを追加しない。iOS/macOS でのカラー絵文字に期待）
- その他のカスタム SVG アイコン: ブランドマーク（十字 + 中心ドット）、矢印、GitHub、シェア — いずれも `app.jsx` 内にインライン SVG で書いてあるので流用可

---

## Files in `design/`

- `index.html` — エントリポイント
- `app.jsx` — React 全コンポーネント（Hero / Concept / HelpWanted / Steps / Contributors / Footer / App）
- `styles.css` — 全スタイル（Tailwind に翻訳する元データ）
- `data.js` — サンプル `CONTRIBUTORS` と `STEPS` 配列
- `tweaks-panel.jsx` — デザイン時の調整 UI（**本番実装には不要**）

### 本番実装に不要な要素
- `tweaks-panel.jsx` と `App` 内の `<TweaksPanel>` / `useTweaks` 関連 — プロトタイプ専用。本番では直接 CSS 変数と JSON データで実装してください
- `data.js` の `CONTRIBUTORS` はダミーデータ。実ファイルは `contributors.json`
- `seedRand` の固定シードはデザイン比較用。本番ではランダム or 日付ベースで OK（ただし hydration mismatch を避けるためサーバー側で座標を決める or useEffect でクライアント計算）

---

## Hydration 注意点

`Math.random()` を SSR/CSR 両方で呼ぶと不一致になります。バブル座標は以下のいずれかで:

1. **Build 時に決定**: `contributors.json` の `sort + seed` で決定論的に座標を付与した配列を ISG で返す
2. **Client だけで計算**: 初回レンダリングは座標なしで出し、`useEffect` 後に配置を流し込む（1 フレーム空く）

現プロトタイプは決定論的 seed を使っていますが、Next.js では (1) のアプローチを推奨。

---

## 実装の進め方（提案）

1. `app/layout.tsx` でフォントと `globals.css` 読み込み
2. `app/page.tsx` で `contributors.json` を読み込み、Hero / Concept / HelpWanted / Steps / Contributors / Footer に props として渡す
3. CSS 変数（`:root` 側）は `globals.css` に直書き、Tailwind の `theme.extend.colors` でも参照できるようブリッジ
4. コンポーネント単位で `components/hero/`, `components/steps/` etc. にファイル分割
5. Bubble / LiveCount / Tooltip / Segment は Client Component としてマーク
6. `contributors.json` のバリデータを `scripts/validate-contributors.ts` に書き、`pre-commit` と GitHub Actions で実行
