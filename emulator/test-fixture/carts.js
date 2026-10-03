// Hand-written test fixture in the PROTOCOL.md §7 emulator format (unicode profile applied).
// Two unrelated cartridges to prove the emulator is topic-agnostic:
//   - "fixture-signed-numbers": 3 tiers, 4-choice items
//   - "fixture-even-odd":       2 tiers, 2-choice items
// Items are built by small loops below; the resulting objects match the §4 item shape.
// Load with: emulator/index.html?carts=test-fixture/carts.js
window.FNM_CARTRIDGES = window.FNM_CARTRIDGES || {};

(function () {
  var M = "−"; // − (minus sign)
  function n(v) { return v < 0 ? M + (-v) : String(v); }
  function pad(i) { return ("00" + i).slice(-3); }

  // Put `correct` at position `pos`, distractors (value, misconception) fill the rest.
  // Distinct-value guard: any collision is bumped and re-tagged ARITH.
  function place(correct, distractors, pos) {
    var used = [correct];
    var ds = distractors.map(function (d) {
      var v = d[0], k = d[1];
      while (used.indexOf(v) !== -1) { v += 1; k = "ARITH"; }
      used.push(v);
      return [v, k];
    });
    var choices = [], mcs = [], di = 0;
    for (var i = 0; i < ds.length + 1; i++) {
      if (i === pos) { choices.push(n(correct)); mcs.push(null); }
      else { choices.push(n(ds[di][0])); mcs.push(ds[di][1]); di++; }
    }
    return { choices: choices, misconceptions: mcs };
  }

  // ---------- Cartridge 1: Signed Numbers (3 tiers, 4 choices) ----------
  var id1 = "fixture-signed-numbers";
  var items1 = [];
  var i, a, b, c, p;
  // Tier 1: a + (−b)
  for (i = 0; i < 24; i++) {
    a = 3 + (i % 8); b = 2 + Math.floor(i / 8) * 4 + (i % 3);
    c = a - b;
    p = place(c, [[a + b, "SIGN_IGNORE"], [b - a, "SUB_BACKWARDS"], [c - 2, "ARITH"]], i % 4);
    items1.push({ id: id1 + "/t1/" + pad(i + 1), tier: 1, prompt: a + " + (" + M + b + ")",
      choices: p.choices, answer: i % 4, misconceptions: p.misconceptions,
      explanation: "Adding " + M + b + " is the same as subtracting " + b + ": " + a + " " + M + " " + b + " = " + n(c) + "." });
  }
  // Tier 2: a − (−b)
  for (i = 0; i < 24; i++) {
    a = -9 + i; if (a >= 0) a += 1; b = 2 + (i * 5) % 9;
    c = a + b;
    p = place(c, [[a - b, "DOUBLE_NEG"], [-(c), "SIGN_IGNORE"], [c + 2, "ARITH"]], (i + 1) % 4);
    items1.push({ id: id1 + "/t2/" + pad(i + 1), tier: 2, prompt: n(a) + " " + M + " (" + M + b + ")",
      choices: p.choices, answer: (i + 1) % 4, misconceptions: p.misconceptions,
      explanation: "Subtracting a negative adds: " + n(a) + " + " + b + " = " + n(c) + "." });
  }
  // Tier 3: (−a)² − b   (prompt uses the unicode-profile superscript ²)
  for (i = 0; i < 24; i++) {
    a = 2 + (i % 8); b = 1 + Math.floor(i / 8) * 3;
    c = a * a - b;
    p = place(c, [[-a * a - b, "NEG_SQUARE"], [-2 * a - b, "EXP_AS_MULT"], [c + 1, "ARITH"]], (i + 2) % 4);
    items1.push({ id: id1 + "/t3/" + pad(i + 1), tier: 3, prompt: "(" + M + a + ")² " + M + " " + b,
      choices: p.choices, answer: (i + 2) % 4, misconceptions: p.misconceptions,
      explanation: "(" + M + a + ")² = (" + M + a + ") × (" + M + a + ") = " + a * a + ", then " + a * a + " " + M + " " + b + " = " + n(c) + "." });
  }

  window.FNM_CARTRIDGES[id1] = {
    protocol: "fnm-cart/1", id: id1, version: "0.1.0",
    title: "Signed Numbers", subtitle: "Fixture: 3 tiers, 4 doors",
    grade: "7", standards: ["CCSS.MATH.CONTENT.7.NS.A.1"],
    seed: 1, items_per_tier: 24, baked_with: "hand-written fixture",
    tiers: [
      { tier: 1, name: "Add a Negative", description: "a + (−b)" },
      { tier: 2, name: "Minus a Negative", description: "a − (−b)" },
      { tier: 3, name: "Negative Squared", description: "(−a)² − b" }
    ],
    misconceptions: {
      SIGN_IGNORE: { student: "Watch the sign. A negative changes the result.", teacher: "Drops the negative sign and combines absolute values." },
      SUB_BACKWARDS: { student: "Order matters: start from the first number.", teacher: "Subtracts the smaller magnitude from the larger regardless of order." },
      DOUBLE_NEG: { student: "Minus a negative is a plus.", teacher: "Treats a − (−b) as a − b." },
      NEG_SQUARE: { student: "A negative times a negative is positive.", teacher: "Treats (−a)² as −a²." },
      EXP_AS_MULT: { student: "² means times itself, not times 2.", teacher: "Treats x² as 2x." }
    },
    items: items1
  };

  // ---------- Cartridge 2: Even or Odd (2 tiers, 2 choices) ----------
  var id2 = "fixture-even-odd";
  var items2 = [];
  var EO = ["Even", "Odd"];
  // Tier 1: is N even or odd?  Alternating parity keeps answer positions balanced.
  for (i = 0; i < 24; i++) {
    var N = 101 + i * 37; // parity alternates: 101 odd, 138 even, ...
    var odd = N % 2;
    items2.push({ id: id2 + "/t1/" + pad(i + 1), tier: 1, prompt: "Is " + N + " even or odd?",
      choices: EO.slice(), answer: odd, misconceptions: odd ? ["FIRST_DIGIT", null] : [null, "FIRST_DIGIT"],
      explanation: "Look at the ones digit: " + (N % 10) + " is " + (odd ? "odd" : "even") + ", so " + N + " is " + (odd ? "odd" : "even") + "." });
  }
  // Tier 2: is a × b even or odd?
  for (i = 0; i < 24; i++) {
    a = 3 + 2 * (i % 6);                 // always odd
    b = 3 + Math.floor(i / 6) * 2 + (i % 2); // alternates odd/even
    var prod = a * b, po = prod % 2;
    items2.push({ id: id2 + "/t2/" + pad(i + 1), tier: 2, prompt: "Is " + a + " × " + b + " even or odd?",
      choices: EO.slice(), answer: po, misconceptions: po ? ["PRODUCT_RULE", null] : [null, "PRODUCT_RULE"],
      explanation: a + " × " + b + " = " + prod + ". A product is odd only when both factors are odd." });
  }

  window.FNM_CARTRIDGES[id2] = {
    protocol: "fnm-cart/1", id: id2, version: "0.1.0",
    title: "Even or Odd", subtitle: "Fixture: 2 tiers, 2 doors",
    grade: "6", standards: ["CCSS.MATH.CONTENT.4.OA.C.5"],
    seed: 2, items_per_tier: 24, baked_with: "hand-written fixture",
    tiers: [
      { tier: 1, name: "Big Numbers", description: "Is N even or odd?" },
      { tier: 2, name: "Products", description: "Is a × b even or odd?" }
    ],
    misconceptions: {
      FIRST_DIGIT: { student: "Only the ones digit decides even or odd.", teacher: "Judges parity from the leading digit." },
      PRODUCT_RULE: { student: "A product is odd only if both numbers are odd.", teacher: "Assumes odd × even is odd." }
    },
    items: items2
  };
})();
