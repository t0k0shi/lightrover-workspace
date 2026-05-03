/* global React */
const { useState, useEffect, useRef, useMemo } = React;

// ─── helpers ────────────────────────────────────────────────────────────────
function hexWithAlpha(hex, a) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
  return `rgba(${r},${g},${b},${a})`;
}
function daysAgo(iso) {
  const d = new Date(iso);
  const now = new Date("2026-04-24");
  return Math.floor((now - d) / 86400000);
}
function seedRand(seed) {
  let x = seed | 0 || 1;
  return () => { x = (x * 1664525 + 1013904223) | 0; return ((x >>> 0) % 10000) / 10000; };
}

// Deterministic scattered positions across the hero, avoiding the center copy column.
function useScatter(contributors, density, seed = 42) {
  return useMemo(() => {
    const rand = seedRand(seed);
    const take = Math.floor(contributors.length * density);
    const chosen = contributors.slice(0, take);
    // Divide canvas into a left strip, right strip, and top/bottom thin strips.
    const zones = [
      { xMin: 0.02, xMax: 0.22, yMin: 0.05, yMax: 0.95 },   // left column
      { xMin: 0.78, xMax: 0.98, yMin: 0.05, yMax: 0.95 },   // right column
      { xMin: 0.22, xMax: 0.78, yMin: 0.02, yMax: 0.12 },   // top band
      { xMin: 0.22, xMax: 0.78, yMin: 0.88, yMax: 0.98 },   // bottom band
    ];
    const placed = [];
    chosen.forEach((c, i) => {
      const zone = zones[i % zones.length];
      // Try a few times to avoid overlap
      let best = null;
      for (let t = 0; t < 8; t++) {
        const x = zone.xMin + rand() * (zone.xMax - zone.xMin);
        const y = zone.yMin + rand() * (zone.yMax - zone.yMin);
        const minDist = placed.reduce((m, p) => Math.min(m, Math.hypot(p.x - x, p.y - y)), Infinity);
        if (!best || minDist > best.minDist) best = { x, y, minDist };
        if (minDist > 0.09) break;
      }
      placed.push({
        ...c,
        x: best.x, y: best.y,
        delay: rand() * 4,
        duration: 4 + rand() * 3,
        tilt: (rand() - 0.5) * 10,
        scale: 0.85 + rand() * 0.35,
      });
    });
    return placed;
  }, [contributors, density, seed]);
}

// ─── small primitives ──────────────────────────────────────────────────────
function Bubble({ c, animSpeed, onHover }) {
  const isNew = daysAgo(c.joinedAt) <= 7;
  return (
    <div
      className="bubble"
      style={{
        left: `${c.x * 100}%`,
        top: `${c.y * 100}%`,
        transform: `translate(-50%, -50%) scale(${c.scale}) rotate(${c.tilt}deg)`,
        animationDelay: `-${c.delay}s`,
        animationDuration: `${c.duration / animSpeed}s`,
      }}
      onMouseEnter={(e) => onHover && onHover(c, e)}
      onMouseLeave={() => onHover && onHover(null)}
    >
      <div className="bubble-pill" style={{
        borderColor: c.color,
        boxShadow: `0 6px 22px ${hexWithAlpha(c.color, 0.28)}, 0 0 0 1px ${hexWithAlpha(c.color, 0.12)}`,
        background: `linear-gradient(180deg, #fff, ${hexWithAlpha(c.color, 0.06)})`,
      }}>
        <div className="bubble-emoji" aria-hidden>{c.emoji}</div>
        <img
          className="bubble-avatar"
          src={`https://github.com/${c.github}.png?size=80`}
          alt={c.name}
          style={{ borderColor: c.color }}
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
      </div>
      {isNew && <span className="bubble-new" style={{ background: c.color }}>NEW</span>}
    </div>
  );
}

function Tooltip({ c, x, y }) {
  if (!c) return null;
  return (
    <div className="tooltip" style={{ left: x, top: y, borderColor: c.color }}>
      <div className="tt-head">
        <span className="tt-emoji">{c.emoji}</span>
        <div>
          <div className="tt-name">@{c.github}</div>
          <div className="tt-date">joined {c.joinedAt.replace(/-/g, "/")}</div>
        </div>
      </div>
      <div className="tt-msg" style={{ borderTopColor: hexWithAlpha(c.color, 0.3) }}>
        「{c.message}」
      </div>
    </div>
  );
}

// Live-counting number
function LiveCount({ target, start = 0, duration = 1800 }) {
  const [n, setN] = useState(target);
  useEffect(() => {
    setN(start);
    let raf, t0, fallback;
    const step = (t) => {
      if (!t0) t0 = t;
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(start + (target - start) * eased));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    // Safety: if rAF stalls (e.g. background iframe), snap to target.
    fallback = setTimeout(() => setN(target), duration + 200);
    return () => { cancelAnimationFrame(raf); clearTimeout(fallback); };
  }, [target]);
  return <span>{n.toLocaleString("ja-JP")}</span>;
}

// Speech bubble interjection
function Serif({ side, color, children }) {
  return (
    <div className={`serif serif-${side}`}>
      <div className="serif-bubble" style={{ borderColor: color, background: hexWithAlpha(color, 0.08) }}>
        {children}
        <span className="serif-tail" style={{ background: "var(--bg)", borderColor: color }} />
      </div>
    </div>
  );
}

// ─── sections ──────────────────────────────────────────────────────────────
function Hero({ contributors, density, animSpeed, bgMode, accent }) {
  const [hover, setHover] = useState(null);
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const scattered = useScatter(contributors, density);

  const count = contributors.length;
  const recent = contributors.filter(c => daysAgo(c.joinedAt) <= 7).length;

  const onMove = (e) => {
    const r = containerRef.current?.getBoundingClientRect();
    if (!r) return;
    setMouse({ x: e.clientX - r.left, y: e.clientY - r.top });
  };

  return (
    <section
      ref={containerRef}
      className={`hero bg-${bgMode}`}
      onMouseMove={onMove}
      style={{ "--accent": accent }}
    >
      <div className="hero-scatter" aria-hidden>
        {scattered.map((c, i) => (
          <Bubble key={c.name + i} c={c} animSpeed={animSpeed}
                  onHover={(cc, e) => setHover(cc)} />
        ))}
      </div>

      <nav className="nav">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            <svg viewBox="0 0 32 32" width="22" height="22">
              <circle cx="16" cy="16" r="15" fill="var(--ink)"/>
              <path d="M9 16h14M16 9v14" stroke="var(--bg)" strokeWidth="2.4" strokeLinecap="round"/>
              <circle cx="16" cy="16" r="3.2" fill="var(--accent)"/>
            </svg>
          </span>
          <b>git-training-ground</b>
          <span className="brand-sub">/ OSS 練習場</span>
        </div>
        <div className="nav-links">
          <a href="#steps">チュートリアル</a>
          <a href="#contributors">参加者</a>
          <a href="#" className="nav-gh">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.08-2.7-1.08-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82a7.6 7.6 0 014 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
            <span>Repo</span>
          </a>
        </div>
      </nav>

      <div className="hero-inner">
        <div className="eyebrow">
          <span className="eyebrow-dot" style={{ background: accent }} />
          first contribution, first win
        </div>
        <h1 className="hero-title">
          <span>Gitの</span>
          <span>"はじめの一歩"を、</span>
          <span className="hero-accent">ここで<em>踏み出そう</em>。</span>
        </h1>
        <p className="hero-lead">
          <code>contributors.json</code> に名前を書いて、PRを投げるだけ。<br/>
          あなたの絵文字が、このページにぷかぷか浮かびます。
        </p>

        <div className="cta-row">
          <a href="#steps" className="btn btn-primary" style={{ background: "var(--ink)" }}>
            参加する
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </a>
          <a href="#" className="btn btn-ghost">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.08-2.7-1.08-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82a7.6 7.6 0 014 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
            リポジトリを見る
          </a>
          <a href="#" className="btn btn-share" aria-label="share">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5L15.4 17.5M15.4 6.5L8.6 10.5"/></svg>
          </a>
        </div>

        {/* live counter */}
        <div className="counter">
          <div className="counter-card">
            <div className="counter-big">
              <LiveCount target={count} />
              <span className="counter-unit">人</span>
            </div>
            <div className="counter-meta">
              <div>参加中<span className="counter-live"><span className="dot"/>LIVE</span></div>
              <div className="counter-recent">今週 <b>+{recent}</b> 人</div>
            </div>
          </div>
          <div className="counter-ticker" aria-hidden>
            {contributors.slice(0, 6).map((c, i) => (
              <div key={i} className="tick" style={{ borderColor: c.color }}>
                <span>{c.emoji}</span>
                <small>@{c.github}</small>
              </div>
            ))}
            <span className="tick-ellipsis">…</span>
          </div>
        </div>
      </div>

      {/* scroll hint */}
      <div className="scroll-hint" aria-hidden>
        <span>scroll</span>
        <svg width="12" height="18" viewBox="0 0 12 18"><rect x="0.5" y="0.5" width="11" height="17" rx="5.5" fill="none" stroke="currentColor"/><circle cx="6" cy="5" r="1.5" fill="currentColor"/></svg>
      </div>

      {hover && <Tooltip c={hover} x={mouse.x + 18} y={mouse.y - 12} />}
    </section>
  );
}

function ConceptSection({ accent }) {
  return (
    <section className="concept">
      <div className="sec-kicker">
        <span style={{ background: accent }} />
        concept
      </div>
      <h2>共同作業を実践して、<br/>Gitに"カラダ"で慣れる。</h2>
      <p>
        ドキュメントで読むGitと、手を動かすGitは別の生き物。
        このリポジトリは、フォーク→編集→PR→レビューという OSS の一連の流れを、
        安全にひと通り体験するための <em>練習場</em> です。
      </p>
      <div className="concept-tiles">
        {[
          { k: "01", t: "失敗OK",   d: "rebaseも、force pushも、遠慮なく試していい場所です。" },
          { k: "02", t: "小さく", d: "追加するのは1行。まず「やってみた」を作るのが目的。" },
          { k: "03", t: "みんなで", d: "他の参加者のPRがレビュー例になります。" },
        ].map((x, i) => (
          <div key={i} className="tile">
            <span className="tile-k">{x.k}</span>
            <h3>{x.t}</h3>
            <p>{x.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function HelpWantedSection({ accent }) {
  return (
    <section className="hw">
      <div className="hw-grid">
        <div className="hw-copy">
          <div className="sec-kicker"><span style={{ background: accent }} />help wanted</div>
          <h2>編集するのは、<br/>この <code>JSON</code> 1ファイルだけ。</h2>
          <p>
            難しいコードは書きません。自己紹介、好きな絵文字、好きな色を追加して
            保存するだけ。それが、あなたの "first contribution" になります。
          </p>
          <ul className="hw-check">
            <li>✓ HTMLもCSSもいらない</li>
            <li>✓ テストは CI が自動で走る</li>
            <li>✓ 5分で終わります</li>
          </ul>
        </div>
        <div className="hw-code" role="img" aria-label="contributors.json example">
          <div className="code-chrome">
            <span className="dot r"/><span className="dot y"/><span className="dot g"/>
            <span className="code-file">contributors.json</span>
            <span className="code-branch">main</span>
          </div>
          <pre>
<span className="ln">28</span><span className="p">  </span><span className="c">{`//... 前の参加者たち`}</span>{"\n"}
<span className="ln">29</span><span className="p">  </span><span className="punct">{"},"}</span>{"\n"}
<span className="ln add">30</span><span className="p add">+ </span><span className="punct">{"{"}</span>{"\n"}
<span className="ln add">31</span><span className="p add">+   </span><span className="k">"name"</span>: <span className="s">"yourname"</span>,{"\n"}
<span className="ln add">32</span><span className="p add">+   </span><span className="k">"github"</span>: <span className="s">"your-handle"</span>,{"\n"}
<span className="ln add">33</span><span className="p add">+   </span><span className="k">"favoriteColor"</span>: <span className="s" style={{color: accent}}>"#FF5E5B"</span>,{"\n"}
<span className="ln add">34</span><span className="p add">+   </span><span className="k">"favoriteEmoji"</span>: <span className="s">"🦊"</span>,{"\n"}
<span className="ln add">35</span><span className="p add">+   </span><span className="k">"message"</span>: <span className="s">"よろしくです！"</span>,{"\n"}
<span className="ln add">36</span><span className="p add">+   </span><span className="k">"joinedAt"</span>: <span className="s">"2026-04-24"</span>{"\n"}
<span className="ln add">37</span><span className="p add">+ </span><span className="punct">{"}"}</span>{"\n"}
<span className="ln">38</span><span className="p">  </span><span className="punct">{"]"}</span>
          </pre>
        </div>
      </div>
      <Serif side="right" color={accent}>
        面白そう🌈… <br/>でも、なんだか難しそう…？🤔
      </Serif>
    </section>
  );
}

function StepsSection({ steps, accent }) {
  return (
    <section id="steps" className="steps">
      <div className="sec-kicker"><span style={{ background: accent }} />good first issue</div>
      <h2>はじめてのOSS貢献、<br/>8ステップで <em>体験</em>する。</h2>
      <p className="steps-lead">
        全体像はこんな感じ。詳しい手順・コマンド・スクショは GitHub の README にあります。
      </p>

      <ol className="timeline">
        <svg className="timeline-wiggle" viewBox="0 0 40 1800" preserveAspectRatio="none" aria-hidden>
          <path d="M20 0 C 32 200, 8 360, 20 560 S 32 900, 20 1100 S 8 1500, 20 1800"
                stroke="var(--ink)" strokeWidth="1.2" strokeDasharray="2 6" fill="none"/>
        </svg>
        {steps.map((s, i) => (
          <li key={s.n} className="step" style={{ "--i": i }}>
            <span className="step-node" style={{ borderColor: accent }}>
              <span className="step-emoji">{s.emoji}</span>
            </span>
            <div className="step-body">
              <div className="step-head">
                <span className="step-num">STEP {String(s.n).padStart(2, "0")}</span>
                <span className="step-hint">{s.hint}</span>
              </div>
              <h3>{s.title}</h3>
            </div>
          </li>
        ))}
      </ol>

      <div className="steps-foot">
        <div className="readme-card">
          <div className="readme-card-body">
            <div className="readme-kicker">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden><path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 11-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"/></svg>
              <span>実際の手順はこちら</span>
            </div>
            <h3>コマンド・スクショ・トラブルシュート付き</h3>
            <p>
              上はあくまで全体像です。実際に手を動かすときは、GitHub 上の
              README を開きながら進めてください。スクリーンショット付きで、
              詰まりやすいところも解説しています。
            </p>
          </div>
          <div className="readme-card-ctas">
            <a href="#" className="btn btn-primary readme-btn">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.08-2.7-1.08-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82a7.6 7.6 0 014 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
              <span>READMEで手順を見る</span>
              <svg width="12" height="12" viewBox="0 0 14 14" aria-hidden><path d="M3 11L11 3M5 3h6v6" stroke="currentColor" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </a>
            <span className="readme-meta mono">⏱ 所要時間 5分 · Git さえ入っていればOK</span>
          </div>
        </div>
        <Serif side="left" color={accent}>
          思ったより簡単そう…！✨<br/>READMEを開いて、さっそく PR💨
        </Serif>
      </div>
    </section>
  );
}

function ContributorsSection({ contributors }) {
  const [filter, setFilter] = useState("all");
  const shown = useMemo(() => {
    if (filter === "new") return contributors.filter(c => daysAgo(c.joinedAt) <= 7);
    return contributors;
  }, [contributors, filter]);

  return (
    <section id="contributors" className="contribs">
      <div className="contribs-head">
        <div>
          <div className="sec-kicker"><span />the playground</div>
          <h2>一緒に練習中の <LiveCount target={contributors.length} /> 人</h2>
        </div>
        <div className="seg">
          <button className={filter==="all"?"on":""} onClick={()=>setFilter("all")}>全員</button>
          <button className={filter==="new"?"on":""} onClick={()=>setFilter("new")}>
            今週の新顔 <span className="seg-count">{contributors.filter(c=>daysAgo(c.joinedAt)<=7).length}</span>
          </button>
        </div>
      </div>
      <div className="contrib-grid">
        {shown.map((c, i) => (
          <div key={i} className="contrib-card" style={{ borderColor: c.color, "--c": c.color }}>
            <div className="cc-top">
              <span className="cc-emoji">{c.emoji}</span>
              <img src={`https://github.com/${c.github}.png?size=72`} alt="" onError={(e)=>e.currentTarget.style.display="none"}/>
            </div>
            <div className="cc-name">@{c.github}</div>
            <div className="cc-msg">「{c.message}」</div>
            <div className="cc-date">
              {daysAgo(c.joinedAt) <= 7 && <span className="cc-new" style={{ background: c.color }}>NEW</span>}
              {c.joinedAt.replace(/-/g,"/")}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Footer({ contributors, accent }) {
  return (
    <footer className="footer" style={{ "--accent": accent }}>
      <div className="foot-stamp">
        <span className="stamp-num"><LiveCount target={contributors.length} /></span>
        <span className="stamp-unit">人が参加中</span>
      </div>
      <h2 className="foot-arigato">
        <span>D</span><span>O</span><span>M</span><span>O</span>
        <i>・</i>
        <span>A</span><span>R</span><span>I</span><span>G</span><span>A</span><span>T</span><span>O</span>
        <em>!!</em>
      </h2>
      <p className="foot-msg">
        このページが、あなたが次に <em>自分の</em> OSS を見つけるきっかけになれば、
        私たちもめちゃくちゃ嬉しいです。
      </p>
      <div className="foot-cta">
        <a href="#" className="btn btn-primary">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.08-2.7-1.08-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82a7.6 7.6 0 014 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
          いますぐ参加する
        </a>
        <a href="#" className="btn btn-ghost">このページをシェア</a>
      </div>
      <div className="foot-meta">
        <span>© 2026 git-training-ground</span>
        <span>·</span>
        <span>MIT License</span>
        <span>·</span>
        <span>Made with 🍵 & ☕</span>
      </div>
    </footer>
  );
}

// ─── root ──────────────────────────────────────────────────────────────────
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#E63946",
  "bubbleDensity": 0.8,
  "animSpeed": 1,
  "bgMode": "dots",
  "fakeCount": 0,
  "tightType": false
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const contribs = useMemo(() => {
    const base = window.CONTRIBUTORS;
    if (!t.fakeCount) return base;
    // Pad with duplicates for "what would this look like with N people?"
    const extra = [];
    for (let i = 0; i < t.fakeCount; i++) {
      extra.push({ ...base[i % base.length], name: base[i%base.length].name + "_" + i, joinedAt: "2026-03-01" });
    }
    return [...base, ...extra];
  }, [t.fakeCount]);

  return (
    <div className={`app ${t.tightType ? "tight" : ""}`} style={{ "--accent": t.accent }}>
      <Hero contributors={contribs} density={t.bubbleDensity} animSpeed={t.animSpeed}
            bgMode={t.bgMode} accent={t.accent}/>
      <ConceptSection accent={t.accent}/>
      <HelpWantedSection accent={t.accent}/>
      <StepsSection steps={window.STEPS} accent={t.accent}/>
      <ContributorsSection contributors={contribs}/>
      <Footer contributors={contribs} accent={t.accent}/>

      <TweaksPanel>
        <TweakSection label="テーマ" />
        <TweakColor  label="アクセント"  value={t.accent}        onChange={(v)=>setTweak("accent", v)} />
        <TweakRadio  label="背景"      value={t.bgMode}
                     options={[["dots","ドット"],["noise","ノイズ"],["plain","無地"],["grid","方眼"]]}
                     onChange={(v)=>setTweak("bgMode", v)} />
        <TweakToggle label="見出しをタイトに" value={t.tightType} onChange={(v)=>setTweak("tightType", v)} />
        <TweakSection label="浮遊バブル" />
        <TweakSlider label="密度"      value={t.bubbleDensity} min={0.2} max={1} step={0.05}
                     onChange={(v)=>setTweak("bubbleDensity", v)} />
        <TweakSlider label="アニメ速度" value={t.animSpeed}     min={0.3} max={2.5} step={0.1} unit="×"
                     onChange={(v)=>setTweak("animSpeed", v)} />
        <TweakSection label="デモ" />
        <TweakSlider label="ダミー参加者数" value={t.fakeCount} min={0} max={200} step={10}
                     onChange={(v)=>setTweak("fakeCount", v)} />
      </TweaksPanel>
    </div>
  );
}

window.App = App;
