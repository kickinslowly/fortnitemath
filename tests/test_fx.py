"""The race's right-answer and boost effects (tools/build_fx.py, console/verse/fnm_fx.verse; G9 spectacle 1a): every system
the Verse spawns is one build_fx builds, the builders bake what the brief asks (counts, lifetimes, the pillar's height, the
gate ring in the barrier plane), the trail stays in its particle budget, and the director's call sites stop the trail with
the boost. The builders run here against a fake MCP that records every call, so nothing touches UEFN."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"
sys.path.insert(0, str(ROOT / "tools"))
import build_fx  # noqa: E402

NEW = ["NS_fnm_gate_burst", "NS_fnm_sky_pillar", "NS_fnm_trail_cyan", "NS_fnm_trail_gold", "NS_fnm_trail_fire"]


def src(name):
    return (VERSE / name).read_text(encoding="utf-8")


def body(text, header):
    """A Verse method's body: from its header line to the next line indented no deeper than the header."""
    start = text.index(header)
    indent = len(header) - len(header.lstrip(" "))
    lines = text[start:].split("\n")
    out = [lines[0]]
    for line in lines[1:]:
        if line.strip() and len(line) - len(line.lstrip(" ")) <= indent:
            break
        out.append(line)
    return "\n".join(out)


class Recorder:
    """Stands in for uefn_mcp.call: answers what build_fx reads back and keeps every write."""

    def __init__(self):
        self.calls = []

    def __call__(self, toolset, tool, args=None, timeout=600, raw=False):
        self.calls.append((tool, args or {}))
        if tool == "exists":
            return {"returnValue": False}
        return {"returnValue": {"emitters": [], "moduleName": "Module"}}

    def inputs(self):
        """{(emitter, module, input path): value} for every SetStackInputData, last write wins."""
        out = {}
        for tool, a in self.calls:
            if tool == "SetStackInputData":
                r = a["stackInputRef"]
                out[(r["emitterName"], r["moduleName"], "/".join(r["inputNameStack"]))] = a["inputData"]["value"]
        return out

    def emitters(self):
        return [a["emitterName"] for tool, a in self.calls if tool == "AddEmitter"]

    def renderer(self, emitter):
        import json
        for tool, a in self.calls:
            if tool == "SetRendererData" and a["renderer"]["emitterName"] == emitter:
                return json.loads(a["rendererData"]["propertyValues"])
        return {}


@pytest.fixture
def build(monkeypatch):
    def run(name):
        rec = Recorder()
        monkeypatch.setattr(build_fx.u, "call", rec)
        build_fx.SYSTEMS[name](name)
        return rec
    return run


def scalar(v):
    return v.get("value") if isinstance(v, dict) else v


def summary(rec):
    """Per emitter: (spawn count, spawn delay, longest lifetime); and the system's loop duration."""
    vals = rec.inputs()
    rows = {}
    for e in rec.emitters():
        count = scalar(vals.get((e, "SpawnBurst_Instantaneous", "Spawn Count"), {"value": 1}))  # a flare spawns 1
        delay = scalar(vals.get((e, "SpawnBurst_Instantaneous", "Spawn Time"), {"value": 0.0}))
        life = max(scalar(vals[(e, "InitializeParticle", k)]) for k in ("Lifetime", "Lifetime Max")
                   if (e, "InitializeParticle", k) in vals)
        rows[e] = (count, delay, life)
    return rows, scalar(vals[("", "SystemState", "Loop Duration")])


def test_every_spawned_system_is_built():
    """A Verse spawn naming a system build_fx does not build would fail the BuildAll (and nobody would know why)."""
    named = set()
    for path in VERSE.glob("*.verse"):
        named |= set(re.findall(r"FNM_FX\.(NS_\w+?)_asset\b", path.read_text(encoding="utf-8")))
    assert set(NEW) <= named, sorted(set(NEW) - named)
    assert named <= set(build_fx.SYSTEMS), sorted(named - set(build_fx.SYSTEMS))


@pytest.mark.parametrize("name", NEW)
def test_particles_live_inside_the_system(build, name):
    """Every emitter is Once, and its burst plus its longest-lived particle fit in the system's own run."""
    rows, duration = summary(build(name))
    for emitter, (count, delay, life) in rows.items():
        assert delay + life <= duration + 1e-6, (emitter, delay, life, duration)
    vals = build(name).inputs()
    for emitter in rows:
        assert vals[(emitter, "EmitterState", "Loop Behavior")]["displayName"] == "Once", emitter
    assert vals[("", "SystemState", "Loop Behavior")]["displayName"] == "Once"


def test_gate_burst(build):
    rec = build("NS_fnm_gate_burst")
    rows, duration = summary(rec)
    assert rows["Sparks"][0] == build_fx.GATE_SPARKS == 120
    assert rec.renderer("Sparks")["Alignment"] == "VelocityAligned"
    assert 0.5 <= duration <= 1.0                                  # ~0.6 s
    # The shock ring stands in the barrier plane: a ring round local +X (Verse aims +X along the way on).
    vals = rec.inputs()
    assert vals[("Ring", "ShapeLocation", "Rotation Mode")]["displayName"] == "Axis Angle"
    assert vals[("Ring", "ShapeLocation", "Rotation Axis")] == {"x": 0, "y": 1, "z": 0}
    assert sum(r[0] for r in rows.values()) <= 250


def test_sky_pillar(build):
    rec = build("NS_fnm_sky_pillar")
    rows, duration = summary(rec)
    vals = rec.inputs()
    # The beam runs from the floor straight up local +Z (Verse spawns it with no rotation), 40 m: a thin dim thread
    # inside the vestibule's walls (CoreLow, GlowLow from the floor), then the bright core and wide glow above them.
    low, top = build_fx.PILLAR_LOW, build_fx.PILLAR_HEIGHT
    assert (low, top) == (600, 4000.0)
    for lower, upper in (("CoreLow", "Core"), ("GlowLow", "Glow")):
        assert (lower, "BeamEmitterSetup", "Beam Start") not in vals            # from the system origin: the floor
        assert vals[(lower, "BeamEmitterSetup", "Beam End")] == {"x": 0, "y": 0, "z": low}
        assert vals[(upper, "BeamEmitterSetup", "Beam Start")] == {"x": 0, "y": 0, "z": low}
        assert vals[(upper, "BeamEmitterSetup", "Beam End")] == {"x": 0, "y": 0, "z": top - low}   # relative to its start
        assert scalar(vals[(lower, "BeamWidth", "Beam Width")]) * 3 <= scalar(vals[(upper, "BeamWidth", "Beam Width")])
    assert rows["Core"][2] == rows["Glow"][2] == build_fx.PILLAR_LIFE == 1.2
    # Nothing flares at the player's feet (the first cut's 3.8 m base flare whited out their screen).
    for emitter in rows:
        offset = vals.get((emitter, "InitializeParticle", "Position Offset"), {"z": 0})
        size = scalar(vals.get((emitter, "InitializeParticle", "Uniform Sprite Size"), {"value": 0}))
        assert not (size > 100 and offset["z"] < low), emitter


@pytest.mark.parametrize("name", NEW)
def test_seen_up_close_without_a_whiteout(build, name):
    """Seen from 3-6 m in daylight, HDR above ~3 burned gold to white and a 5 m flash filled the screen (session
    2026-10-13): every colour channel stays at 3 or under, and every flare skips particles near the camera."""
    rec = build(name)
    vals = rec.inputs()
    for (emitter, module, path), v in vals.items():
        if isinstance(v, dict) and set(v) >= {"r", "g", "b"}:
            assert max(v["r"], v["g"], v["b"]) <= 3.0, (emitter, module, path, v)
    for emitter in rec.emitters():
        size = vals.get((emitter, "InitializeParticle", "Uniform Sprite Size"))
        if size is not None and scalar(size) < 500:                      # a flare a player can stand next to
            r = rec.renderer(emitter)
            assert r.get("bEnableCameraDistanceCulling") and r["MinCameraDistance"] >= 150, emitter


@pytest.mark.parametrize("name", ["NS_fnm_trail_cyan", "NS_fnm_trail_gold", "NS_fnm_trail_fire"])
def test_trail_puff_and_budget(build, name):
    """One puff is ~20 particles living 0.6 s; at the Verse's spawn rate 16 boosting players stay near 1.5k alive."""
    rows, duration = summary(build(name))
    per_puff = sum(r[0] for r in rows.values())
    assert per_puff == 20
    assert duration == build_fx.TRAIL_TIME == 0.6
    every = float(re.search(r"^FnmTrailEvery : float = ([\d.]+)$", src("fnm_fx.verse"), re.M).group(1))
    assert 0.1 <= every <= 0.15                                    # ~8 spawns a second
    alive = 16 * (1 / every) * per_puff * duration
    assert alive <= 1700, alive


def test_trail_tiers_match_the_streak():
    """Streak 1-2 cyan, 3-5 gold, 6+ fire: FnmTrailTier, the names it logs and the asset it spawns agree."""
    fx = src("fnm_fx.verse")
    assert "if (Streak >= 6) then 2 else if (Streak >= 3) then 1 else 0" in fx
    assert 'FnmTrailNames : []string = array{"cyan", "gold", "fire"}' in fx
    spawn = body(fx, "FnmSpawnTrail(Streak:int, At:vector3):void =")
    assert "Tier := FnmTrailTier(Streak)" in spawn
    assert "if (Tier = 2) then SpawnParticleSystem(FNM_FX.NS_fnm_trail_fire_asset, Feet)" in spawn
    assert "else if (Tier = 1) then SpawnParticleSystem(FNM_FX.NS_fnm_trail_gold_asset, Feet)" in spawn
    assert "else SpawnParticleSystem(FNM_FX.NS_fnm_trail_cyan_asset, Feet)" in spawn
    assert list(build_fx.TRAILS) == ["NS_fnm_trail_cyan", "NS_fnm_trail_gold", "NS_fnm_trail_fire"]


def test_director_call_sites():
    d = src("fnm_director.verse")
    # The right answer: AdvancePlayer (the one place a station door is passed) fires the pillar and the burst.
    advance = body(d, "    AdvancePlayer(State:fnm_player_state, Station:fnm_station, DoorIndex:int, ShowNow:logic):void =")
    assert "RightAnswerFx(State, Station, DoorIndex)" in advance
    fx = body(d, "    RightAnswerFx(State:fnm_player_state, Station:fnm_station, DoorIndex:int):void =")
    assert "FnmSpawnPillar(VestibuleFloor(Door))" in fx
    assert "FnmSpawnGateBurst(Passage.GetTransform().Translation," in fx
    # The trail runs with the boost and stops with it: a newer boost or StopBoost bumps BoostGeneration.
    boost = body(d, "    Boost(State:fnm_player_state, Seconds:float)<suspends>:void =")
    assert "spawn{ BoostTrail(State, Generation, Seconds) }" in boost
    trail = body(d, "    BoostTrail(State:fnm_player_state, Generation:int, Seconds:float)<suspends>:void =")
    for guard in ("State.BoostGeneration <> Generation", "State.Finished?", "not PlayerStates[State.Player]",
                  "GetSimulationElapsedTime() - Start >= Seconds", "Character.IsActive[]", "Sleep(FnmTrailEvery)"):
        assert guard in trail, guard
    stop = body(d, "    StopBoost(State:fnm_player_state):void =")
    assert "set State.BoostGeneration += 1" in stop
    # StopBoost on a wrong door, an elimination and the finish (the trail's "penalised, respawns, finishes").
    assert "Print(\"FNM: player eliminated at stage {State.Stage}\")\n                StopBoost(State)" in d
    assert "set State.LastTime = Time\n        StopBoost(State)" in d
    assert "set State.Streak = 0\n                StopBoost(State)" in d


def test_far_pillar_hook_ships_off():
    assert "    DebugFarPillar : int = 0\n" in src("fnm_director.verse")
