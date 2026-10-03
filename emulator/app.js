/* FNM emulator — a browser console for fnm-cart/1 cartridges (PROTOCOL.md §6).
 * Topic-agnostic: everything comes from window.FNM_CARTRIDGES. No cartridge ids,
 * tier counts or item content are assumed here.
 */
(function () {
  "use strict";

  var ARITH_TEXT = "Check your arithmetic.";
  var LETTERS = ["A", "B", "C", "D"];
  var S_MIN = 3, S_MAX = 20, S_DEFAULT = 10;
  var DOOR_OPTIONS = [2, 3, 4];

  // ---------- pure helpers ----------

  // §6: difficulty position p = (s-1)/(S-1), tier = 1 + round_half_up(p * (T-1)).
  // Integer form, identical to the Verse console: 1 + (2(s-1)(T-1) + (S-1)) div (2(S-1)); S = 1 -> tier 1.
  // Every run starts at tier 1 and ends at tier T.
  function tierForStage(s, S, T) {
    if (S <= 1) return 1;
    return 1 + Math.floor((2 * (s - 1) * (T - 1) + (S - 1)) / (2 * (S - 1)));
  }

  // §6a map-profile reduction: when an item has more choices than the map's max_choices, keep the
  // correct choice and drop distractors — ARITH first (last in baked order first), then misconception
  // choices (last first). Survivors keep baked relative order; answer/misconceptions re-indexed.
  function reduceItem(item, maxChoices) {
    var n = item.choices.length;
    if (!maxChoices || n <= maxChoices) return item;
    var keep = item.choices.map(function () { return true; });
    var mcs = item.misconceptions || [];
    var arith = [], other = [];
    for (var i = n - 1; i >= 0; i--) {
      if (i === item.answer) continue;
      (mcs[i] === "ARITH" || mcs[i] == null ? arith : other).push(i);
    }
    var order = arith.concat(other), dropped = 0;
    while (n - dropped > maxChoices) { keep[order[dropped]] = false; dropped++; }
    var out = { choices: [], misconceptions: [], answer: -1 };
    for (var k in item) if (!(k in out)) out[k] = item[k];
    for (var j = 0; j < keep.length; j++) {
      if (!keep[j]) continue;
      if (j === item.answer) out.answer = out.choices.length;
      out.choices.push(item.choices[j]);
      out.misconceptions.push(mcs[j] === undefined ? null : mcs[j]);
    }
    out.baked_choices = n;
    return out;
  }

  // Seeded PRNG (mulberry32). ?seed=<n> makes runs reproducible.
  function makeRng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffled(arr, rng) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  // Without-replacement draw per tier; reshuffles a tier's bag when it runs dry. (§6)
  function makeDrawer(items, rng) {
    var byTier = {};
    items.forEach(function (it) { (byTier[it.tier] = byTier[it.tier] || []).push(it); });
    var bags = {};
    return {
      draw: function (tier) {
        var pool = byTier[tier] || [];
        if (!pool.length) return null;
        if (!bags[tier] || !bags[tier].length) bags[tier] = shuffled(pool, rng);
        return bags[tier].pop();
      }
    };
  }

  var SUP = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
  // Emulator uses the `unicode` render profile (§7). carts.js is normally already rendered;
  // this only catches any leftover digit exponents. Non-digit exponents stay as ^.
  function render(text) {
    return String(text == null ? "" : text).replace(/\^(\d+)/g, function (_, d) {
      return d.split("").map(function (c) { return SUP[c]; }).join("");
    });
  }

  function esc(text) {
    return String(text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function r(text) { return esc(render(text)); }

  function feedbackFor(cart, item, idx) {
    var key = item.misconceptions ? item.misconceptions[idx] : null;
    if (!key || key === "ARITH") return { key: "ARITH", student: ARITH_TEXT, teacher: "" };
    var m = (cart.misconceptions || {})[key];
    if (!m) return { key: key, student: ARITH_TEXT, teacher: "" };
    return { key: key, student: m.student || ARITH_TEXT, teacher: m.teacher || "" };
  }

  function tierName(cart, t) {
    var tiers = cart.tiers || [];
    for (var i = 0; i < tiers.length; i++) if (tiers[i].tier === t) return tiers[i].name;
    return "";
  }

  function tierCount(cart) { return (cart.tiers || []).length; }

  function cartProblem(cart) {
    if (!cart || typeof cart !== "object") return "not an object";
    if (!Array.isArray(cart.tiers) || !cart.tiers.length) return "no tiers";
    if (!Array.isArray(cart.items) || !cart.items.length) return "no items";
    for (var t = 1; t <= cart.tiers.length; t++) {
      if (!cart.items.some(function (it) { return it.tier === t; })) return "tier " + t + " has no items";
    }
    return null;
  }

  // ---------- state ----------

  var params = new URLSearchParams(location.search);
  var state = {
    screen: "select",       // select | inspect | run | end | empty
    selectTab: "play",      // play | inspect
    stages: clampS(parseInt(params.get("stages"), 10) || S_DEFAULT),
    maxDoors: DOOR_OPTIONS.indexOf(parseInt(params.get("doors"), 10)) !== -1 ? parseInt(params.get("doors"), 10) : 4,
    inspectId: null,
    run: null
  };

  function clampS(n) { return Math.max(S_MIN, Math.min(S_MAX, n)); }

  function carts() {
    var c = window.FNM_CARTRIDGES;
    if (!c || typeof c !== "object") return [];
    return Object.keys(c).map(function (k) { return { key: k, cart: c[k] }; });
  }

  function startRun(key) {
    var cart = window.FNM_CARTRIDGES[key];
    var seedParam = params.get("seed");
    var seed = seedParam != null ? (parseInt(seedParam, 10) >>> 0) : (Math.random() * 4294967296) >>> 0;
    var S = state.stages, T = tierCount(cart);
    state.run = {
      key: key, cart: cart, S: S, T: T, seed: seed, maxDoors: state.maxDoors,
      drawer: makeDrawer(cart.items, makeRng(seed)),
      stage: 0, item: null, wrong: [], solved: false,
      log: [] // per stage: {stage, tier, itemId, misses:[keys], firstTry}
    };
    state.screen = "run";
    nextStage();
  }

  function nextStage() {
    var run = state.run;
    run.stage += 1;
    if (run.stage > run.S) { state.screen = "end"; renderApp(); return; }
    var tier = tierForStage(run.stage, run.S, run.T);
    run.tier = tier;
    run.item = reduceItem(run.drawer.draw(tier), run.maxDoors);
    run.wrong = [];
    run.solved = false;
    run.feedback = null;
    run.log.push({ stage: run.stage, tier: tier, itemId: run.item.id, misses: [], firstTry: null });
    renderApp();
  }

  function choose(idx) {
    var run = state.run;
    if (!run || run.solved || !run.item) return;
    if (idx < 0 || idx >= run.item.choices.length) return;
    if (run.wrong.indexOf(idx) !== -1) return;
    var entry = run.log[run.log.length - 1];
    if (idx === run.item.answer) {
      run.solved = true;
      if (entry.firstTry === null) entry.firstTry = true;
      run.feedback = { kind: "correct", text: run.item.explanation };
    } else {
      run.wrong.push(idx);
      if (entry.firstTry === null) entry.firstTry = false;
      var fb = feedbackFor(run.cart, run.item, idx);
      entry.misses.push(fb.key);
      run.feedback = { kind: "wrong", text: fb.student };
    }
    renderApp();
  }

  function summary() {
    var run = state.run;
    var firstTry = run.log.filter(function (e) { return e.firstTry === true; }).length;
    var misses = 0, counts = {}, order = [];
    run.log.forEach(function (e) {
      e.misses.forEach(function (k) {
        misses++;
        if (!counts[k]) { counts[k] = 0; order.push(k); }
        counts[k]++;
      });
    });
    var hit = order.map(function (k) {
      var fb = k === "ARITH" ? { student: ARITH_TEXT, teacher: "" } : (run.cart.misconceptions || {})[k] || { student: ARITH_TEXT, teacher: "" };
      return { key: k, count: counts[k], student: fb.student, teacher: fb.teacher || "" };
    }).sort(function (a, b) { return b.count - a.count; });
    var tiers = [];
    for (var t = 1; t <= run.T; t++) {
      var es = run.log.filter(function (e) { return e.tier === t; });
      tiers.push({ tier: t, name: tierName(run.cart, t), stages: es.length,
        firstTry: es.filter(function (e) { return e.firstTry; }).length });
    }
    return { stages: run.S, firstTry: firstTry, accuracy: Math.round(100 * firstTry / run.S), misses: misses, hit: hit, tiers: tiers };
  }

  // ---------- rendering ----------

  var app;

  function renderApp() {
    app = app || document.getElementById("app");
    var list = carts();
    if (!list.length && state.screen !== "empty") state.screen = "empty";
    app.setAttribute("data-screen", state.screen);
    if (state.screen === "empty") app.innerHTML = viewEmpty();
    else if (state.screen === "select") app.innerHTML = viewSelect(list);
    else if (state.screen === "run") app.innerHTML = viewRun();
    else if (state.screen === "end") app.innerHTML = viewEnd();
    fitDoors();
    var focus = app.querySelector("[data-autofocus]");
    if (focus) focus.focus({ preventScroll: true });
    if (state.screen === "run" && state.run && state.run.feedback) {
      var fbEl = app.querySelector(".feedback");
      if (fbEl && fbEl.scrollIntoView) fbEl.scrollIntoView({ block: "nearest" });
    } else {
      window.scrollTo(0, 0);
    }
  }

  // A choice is a number/expression: never split it across lines. Shrink its font until it fits
  // on one line (down to a floor); only below the floor does it wrap. (§6: no truncation.)
  function fitDoors() {
    var els = app.querySelectorAll(".door-text");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      el.style.fontSize = "";
      el.style.whiteSpace = "nowrap";
      var size = parseFloat(getComputedStyle(el).fontSize);
      var ps = getComputedStyle(el.parentNode);
      var box = el.parentNode.clientWidth - parseFloat(ps.paddingLeft) - parseFloat(ps.paddingRight);
      while (el.scrollWidth > box && size > 14) { size -= 1; el.style.fontSize = size + "px"; }
      if (el.scrollWidth > box) el.style.whiteSpace = "";
    }
  }
  window.addEventListener("resize", function () { if (state.screen === "run") fitDoors(); });

  function brand() {
    return '<div class="brand"><span class="brand-mark">FNM</span><span class="brand-sub">Cartridge Emulator</span></div>';
  }

  function viewEmpty() {
    var src = window.FNM_CARTS_SRC || "carts.js";
    var why = window.FNM_CARTS_STATUS === "missing"
      ? "Couldn't load <code>" + esc(src) + "</code>."
      : "<code>" + esc(src) + "</code> loaded, but it has no cartridges in it.";
    return '<header class="topbar">' + brand() + '</header>' +
      '<main class="screen empty" data-testid="empty">' +
      '<div class="panel">' +
      '<h1 class="big-title">No cartridge inserted</h1>' +
      '<p>' + why + '</p>' +
      '<p>From the repo root, insert one:</p>' +
      '<pre class="cmd">python -m fnm insert &lt;id&gt;</pre>' +
      '<p class="muted">Then reload this page.</p>' +
      '</div></main>';
  }

  function viewSelect(list) {
    var tabs = '<nav class="tabs" role="tablist">' +
      '<button class="tab' + (state.selectTab === "play" ? " on" : "") + '" data-act="tab" data-tab="play" data-testid="tab-play">Play</button>' +
      '<button class="tab' + (state.selectTab === "inspect" ? " on" : "") + '" data-act="tab" data-tab="inspect" data-testid="tab-inspect">Inspector</button>' +
      '</nav>';
    var body = state.selectTab === "play" ? viewPlay(list) : viewInspect(list);
    return '<header class="topbar">' + brand() + tabs + '</header>' + body;
  }

  function viewPlay(list) {
    var stagesCtl = '<div class="stages" data-testid="stages">' +
      '<span class="stages-label">Stages</span>' +
      '<button class="step" data-act="stages" data-delta="-1" aria-label="Fewer stages">−</button>' +
      '<input type="range" min="' + S_MIN + '" max="' + S_MAX + '" value="' + state.stages + '" data-act="stages-range" aria-label="Stage count" data-testid="stages-range">' +
      '<button class="step" data-act="stages" data-delta="1" aria-label="More stages">+</button>' +
      '<span class="stages-val" data-testid="stages-val">' + state.stages + '</span>' +
      '</div>';
    var doorsCtl = '<div class="stages mapshape" data-testid="doors">' +
      '<span class="stages-label" title="Simulates a map profile max_choices (PROTOCOL §6a)">Map doors</span>' +
      '<div class="seg">' + DOOR_OPTIONS.map(function (d) {
        return '<button class="segbtn' + (state.maxDoors === d ? ' on' : '') + '" data-act="doors" data-doors="' + d + '" data-testid="doors-' + d + '">' + d + '</button>';
      }).join("") + '</div>' +
      '<span class="muted small">Items with more choices drop distractors (ARITH first) to fit.</span>' +
      '</div>';
    var cards = list.map(function (e) {
      var c = e.cart, bad = cartProblem(c);
      if (bad) {
        return '<article class="card bad"><h2 class="card-title">' + esc(e.key) + '</h2>' +
          '<p>This cartridge is malformed (' + esc(bad) + ') and can\'t be played.</p></article>';
      }
      var tiers = c.tiers.map(function (t) {
        var n = c.items.filter(function (it) { return it.tier === t.tier; }).length;
        return '<li><span class="tnum">' + t.tier + '</span>' + r(t.name) + '<span class="tcount">' + n + '</span></li>';
      }).join("");
      var stds = (c.standards || []).map(function (s) {
        return '<span class="chip">' + esc(String(s).replace(/^CCSS\.MATH\.CONTENT\./, "")) + '</span>';
      }).join("");
      return '<article class="card" data-testid="cart-card" data-cart="' + esc(e.key) + '">' +
        '<div class="card-head">' +
        (c.grade ? '<span class="grade">Gr ' + esc(c.grade) + '</span>' : '') +
        '<h2 class="card-title">' + r(c.title) + '</h2>' +
        '<p class="card-sub">' + r(c.subtitle || "") + '</p></div>' +
        '<div class="chips">' + stds + '</div>' +
        '<ol class="tierlist">' + tiers + '</ol>' +
        '<div class="card-foot"><span class="muted">' + c.items.length + ' items · ' + c.tiers.length + ' tier' + (c.tiers.length === 1 ? '' : 's') + '</span>' +
        '<button class="btn go" data-act="play" data-cart="' + esc(e.key) + '" data-testid="play">Play</button></div>' +
        '</article>';
    }).join("");
    return '<main class="screen select"><div class="controls">' + stagesCtl + doorsCtl + '</div>' + '<section class="cards">' + cards + '</section></main>';
  }

  function viewInspect(list) {
    var playable = list.filter(function (e) { return !cartProblem(e.cart); });
    if (!playable.length) return '<main class="screen"><p>No playable cartridges.</p></main>';
    if (!state.inspectId || !playable.some(function (e) { return e.key === state.inspectId; })) state.inspectId = playable[0].key;
    var picker = '<div class="inspect-pick">' + playable.map(function (e) {
      return '<button class="pill' + (e.key === state.inspectId ? " on" : "") + '" data-act="inspect-pick" data-cart="' + esc(e.key) + '">' + r(e.cart.title) + '</button>';
    }).join("") + '</div>';
    var c = window.FNM_CARTRIDGES[state.inspectId];
    var groups = c.tiers.map(function (t) {
      var items = c.items.filter(function (it) { return it.tier === t.tier; });
      var rows = items.map(function (it) {
        var ch = it.choices.map(function (txt, i) {
          var ok = i === it.answer;
          var tag = ok ? '<span class="tag ok">correct</span>' : '<span class="tag mc" title="' + esc(feedbackFor(c, it, i).student) + '">' + esc(it.misconceptions[i] || "?") + '</span>';
          return '<li class="ich' + (ok ? " ok" : "") + '"><span class="ilet">' + LETTERS[i] + '</span><span class="itxt math">' + r(txt) + '</span>' + tag + '</li>';
        }).join("");
        return '<article class="iitem" data-testid="inspect-item">' +
          '<div class="iid">' + esc(it.id) + '</div>' +
          '<div class="iprompt math">' + r(it.prompt) + '</div>' +
          '<ol class="ichoices">' + ch + '</ol>' +
          '<div class="iexp"><b>Explanation:</b> ' + r(it.explanation) + '</div>' +
          '</article>';
      }).join("");
      return '<section class="igroup"><h3 class="igroup-h"><span class="tnum">' + t.tier + '</span>' + r(t.name) +
        ' <span class="muted">· ' + items.length + ' items</span></h3>' +
        (t.description ? '<p class="muted idesc">' + r(t.description) + '</p>' : '') +
        '<div class="igrid">' + rows + '</div></section>';
    }).join("");
    var mcs = c.misconceptions || {};
    var legend = Object.keys(mcs).map(function (k) {
      return '<li><span class="tag mc">' + esc(k) + '</span> ' + r(mcs[k].student) +
        (mcs[k].teacher ? '<div class="muted small">' + r(mcs[k].teacher) + '</div>' : '') + '</li>';
    }).join("") + '<li><span class="tag mc">ARITH</span> ' + ARITH_TEXT + '</li>';
    return '<main class="screen inspect" data-testid="inspector">' + picker +
      '<details class="legend" open><summary>Misconception catalog</summary><ul>' + legend + '</ul></details>' +
      groups + '</main>';
  }

  function viewRun() {
    var run = state.run, it = run.item, c = run.cart;
    var pct = Math.round(100 * (run.stage - 1) / run.S);
    var doors = it.choices.map(function (txt, i) {
      var cls = "door d" + i;
      var wrong = run.wrong.indexOf(i) !== -1;
      if (wrong) cls += " wrong";
      if (run.solved && i === it.answer) cls += " right";
      if (run.solved && i !== it.answer) cls += " dim";
      var dis = wrong || run.solved ? " disabled" : "";
      return '<button class="' + cls + '" data-act="choose" data-idx="' + i + '" data-testid="door"' + dis + '>' +
        '<span class="door-letter">' + LETTERS[i] + '</span>' +
        '<span class="door-text math">' + r(txt) + '</span>' +
        (wrong ? '<span class="door-mark" aria-hidden="true">✕</span>' : '') +
        (run.solved && i === it.answer ? '<span class="door-mark" aria-hidden="true">✓</span>' : '') +
        '</button>';
    }).join("");
    var fb = "";
    if (run.feedback) {
      if (run.feedback.kind === "wrong") {
        fb = '<div class="feedback wrong" data-testid="feedback" data-kind="wrong" role="status">' +
          '<div class="fb-head">Not that one</div><div class="fb-text">' + r(run.feedback.text) + '</div>' +
          '<div class="fb-hint">Pick again.</div></div>';
      } else {
        var last = run.stage === run.S;
        fb = '<div class="feedback correct" data-testid="feedback" data-kind="correct" role="status">' +
          '<div class="fb-head">' + (run.wrong.length ? 'Got it!' : 'Nailed it!') + '</div>' +
          '<div class="fb-text math-ish">' + r(run.feedback.text) + '</div>' +
          '<button class="btn go big" data-act="continue" data-testid="continue" data-autofocus>' + (last ? 'See results' : 'Continue') + ' <span class="kbd">Enter</span></button></div>';
      }
    }
    return '<header class="runbar">' +
      '<div class="runbar-row"><div class="run-title"><span class="rt">' + r(c.title) + '</span><span class="rs">' + r(c.subtitle || "") + '</span></div>' +
      '<button class="btn ghost" data-act="quit" data-testid="quit">Quit</button></div>' +
      '<div class="run-stage" data-testid="stage-label" data-stage="' + run.stage + '" data-tier="' + run.tier + '">' +
      'Stage <b>' + run.stage + '</b> / ' + run.S + ' · Tier ' + run.tier + ': ' + r(tierName(c, run.tier)) + '</div>' +
      '<div class="progress"><div class="bar" style="width:' + pct + '%"></div></div>' +
      '</header>' +
      '<main class="screen run">' +
      '<div class="prompt math" data-testid="prompt">' + r(it.prompt) + '</div>' +
      '<div class="doors n' + it.choices.length + '">' + doors + '</div>' +
      fb +
      '<p class="keys muted">Keys: 1–' + it.choices.length + ' or A–' + LETTERS[it.choices.length - 1] + ' · Enter to continue</p>' +
      '</main>';
  }

  function viewEnd() {
    var run = state.run, s = summary();
    var grade = s.accuracy >= 90 ? "Victory Royale!" : s.accuracy >= 70 ? "Top 10!" : s.accuracy >= 40 ? "Good fight" : "Back to the bus";
    var hit = s.hit.length
      ? '<ul class="mc-list" data-testid="mc-list">' + s.hit.map(function (h) {
          return '<li class="mc-row" data-testid="mc-row" data-key="' + esc(h.key) + '" data-count="' + h.count + '">' +
            '<span class="mc-count">×' + h.count + '</span>' +
            '<div class="mc-body"><div class="mc-student">' + r(h.student) + '</div>' +
            (h.teacher ? '<div class="mc-teacher">Teacher note: ' + r(h.teacher) + '</div>' : '') +
            '<div class="mc-key">' + esc(h.key) + '</div></div></li>';
        }).join("") + '</ul>'
      : '<p class="clean" data-testid="mc-none">No misconceptions hit. Clean run.</p>';
    var tiers = '<ol class="tier-break">' + s.tiers.map(function (t) {
      return '<li><span class="tnum">' + t.tier + '</span>' + r(t.name) + '<span class="tb-val">' +
        (t.stages ? t.firstTry + ' / ' + t.stages : '—') + '</span></li>';
    }).join("") + '</ol>';
    return '<header class="runbar"><div class="runbar-row"><div class="run-title"><span class="rt">' + r(run.cart.title) + '</span><span class="rs">' + r(run.cart.subtitle || "") + '</span></div></div></header>' +
      '<main class="screen end" data-testid="end">' +
      '<h1 class="big-title">' + grade + '</h1>' +
      '<div class="stats">' +
      '<div class="stat"><div class="stat-v" data-testid="accuracy" data-first="' + s.firstTry + '" data-stages="' + s.stages + '">' + s.accuracy + '%</div><div class="stat-l">First-try accuracy<br><span class="muted">' + s.firstTry + ' of ' + s.stages + ' stages</span></div></div>' +
      '<div class="stat"><div class="stat-v" data-testid="misses" data-misses="' + s.misses + '">' + s.misses + '</div><div class="stat-l">Total misses</div></div>' +
      '</div>' +
      '<section class="panel"><h2 class="sec-h">Misconceptions you hit</h2>' + hit + '</section>' +
      '<section class="panel"><h2 class="sec-h">First try by tier</h2>' + tiers + '</section>' +
      '<div class="end-actions"><button class="btn go big" data-act="again" data-testid="again" data-autofocus>Play again</button>' +
      '<button class="btn ghost big" data-act="home" data-testid="home">Choose cartridge</button></div>' +
      '</main>';
  }

  // ---------- events ----------

  function onClick(ev) {
    var el = ev.target.closest("[data-act]");
    if (!el || el.disabled) return;
    var act = el.getAttribute("data-act");
    if (act === "tab") { state.selectTab = el.getAttribute("data-tab"); renderApp(); }
    else if (act === "stages") { state.stages = clampS(state.stages + parseInt(el.getAttribute("data-delta"), 10)); renderApp(); }
    else if (act === "doors") { state.maxDoors = parseInt(el.getAttribute("data-doors"), 10); renderApp(); }
    else if (act === "play") startRun(el.getAttribute("data-cart"));
    else if (act === "inspect-pick") { state.inspectId = el.getAttribute("data-cart"); renderApp(); }
    else if (act === "choose") choose(parseInt(el.getAttribute("data-idx"), 10));
    else if (act === "continue") nextStage();
    else if (act === "quit" || act === "home") { state.screen = "select"; state.run = null; renderApp(); }
    else if (act === "again") startRun(state.run.key);
  }

  function onInput(ev) {
    if (ev.target.getAttribute && ev.target.getAttribute("data-act") === "stages-range") {
      state.stages = clampS(parseInt(ev.target.value, 10));
      var v = app.querySelector("[data-testid=stages-val]");
      if (v) v.textContent = state.stages;
    }
  }

  function onKey(ev) {
    if (state.screen !== "run" || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var run = state.run, k = ev.key;
    if (run.solved) {
      if (k === "Enter" || k === " ") { ev.preventDefault(); nextStage(); }
      return;
    }
    var idx = -1;
    if (/^[1-4]$/.test(k)) idx = parseInt(k, 10) - 1;
    else if (/^[a-dA-D]$/.test(k)) idx = k.toUpperCase().charCodeAt(0) - 65;
    if (idx >= 0) { ev.preventDefault(); choose(idx); }
  }

  function boot() {
    if (boot.done) return;
    boot.done = true;
    app = document.getElementById("app");
    document.addEventListener("click", onClick);
    document.addEventListener("input", onInput);
    document.addEventListener("keydown", onKey);
    state.screen = carts().length ? "select" : "empty";
    renderApp();
  }

  // Test/debug handle. Read-only views of state plus the pure helpers.
  window.FNM_EMU = {
    boot: boot,
    tierForStage: tierForStage,
    makeDrawer: makeDrawer,
    reduceItem: reduceItem,
    makeRng: makeRng,
    render: render,
    current: function () {
      var run = state.run;
      if (!run) return null;
      return { screen: state.screen, stage: run.stage, S: run.S, T: run.T, tier: run.tier,
        item: run.item, wrong: run.wrong.slice(), solved: run.solved, seed: run.seed, maxDoors: run.maxDoors };
    },
    summary: function () { return state.run ? summary() : null; }
  };

  if (window.FNM_BOOT_PENDING || window.FNM_CARTS_STATUS) boot();
})();
