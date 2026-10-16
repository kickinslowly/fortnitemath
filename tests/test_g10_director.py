"""G10 race features in the director (briefs/g10/D_director.md): the next-reward line, REDEMPTION at the boss, SHIELD, STRIKE,
medal v2 with the brag grid, the record only against someone, analytics, and the small arena fixes. The project keeps no
Python mirror of the Verse logic, so these read the Verse source (call sites, order, what a branch may not touch); the
behaviour itself is proven by the FNM: log lines of a hooked play session."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"


def src(name):
    return (VERSE / f"{name}.verse").read_text(encoding="utf-8")


def code(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def body(text, head):
    """The body of the method whose header line starts with head (up to the next line at its indent or less)."""
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip().startswith(head))
    indent = len(lines[start]) - len(lines[start].lstrip())
    out = []
    for l in lines[start + 1:]:
        if l.strip() and len(l) - len(l.lstrip()) <= indent:
            break
        out.append(l)
    return "\n".join(out)


D = src("fnm_director")
LOGIC = src("fnm_logic")


def test_ship_values_of_the_new_editables():
    for line in ("    StrikesOn : logic = true\n", "    DebugStrikeSelf : logic = false\n", "    MedalTimeGates : logic = false\n",
                 "    GoldParSeconds : float = 0.0\n", "    SilverParSeconds : float = 0.0\n", '    IslandCode : string = ""\n'):
        assert line in D, line
    # the reward cadence the brief fixes: shield at 3, strikes at 5, 10, 15, 1 s to fire, 1 s warning, 20 s immunity
    for line in ("ShieldStreak : int = 3", "StrikeStreaks : []int = array{5, 10, 15}", "StrikeDelaySeconds : float = 1.0",
                 "StrikeWarnSeconds : float = 1.0", "StrikeImmuneSeconds : float = 20.0", "LeaderBonusSeconds : float = 2.0",
                 "StrikeFreezeSeconds : float = 2.5", "StrikeMudSeconds : float = 4.0", "StrikeBlurSeconds : float = 3.0",
                 "StrikeDarkSeconds : float = 1.5"):
        assert line in D, line


# ---------------------------------------------------------------- C1 next-reward line

def test_streak_line_names_the_next_reward():
    copy = body(D, "StreakCopy(State:fnm_player_state, BoostLeft:int):string =")
    assert "Next := NextRewardCopy(State)" in copy and '"STREAK x{State.Streak}  -  {Next}"' in copy
    nxt = body(D, "NextRewardCopy(State:fnm_player_state)<transacts>:string =")
    assert "if (not State.Shield?, ShieldStreak > State.Streak):" in nxt          # no shield line while one is held
    assert "if (StrikesOn?):" in nxt                                             # strikes off: no strike line
    assert '"{At - State.Streak} more for a {Name}"' in nxt


def mirror_next_reward(streak, shield, strikes_on=True):
    """The rule NextRewardCopy spells, for the cases the brief names."""
    at, name = 0, ""
    if not shield and 3 > streak:
        at, name = 3, "SHIELD"
    if strikes_on:
        for m in (5, 10, 15):
            if m > streak and (at == 0 or m < at):
                at, name = m, "STRIKE"
    return f"{at - streak} more for a {name}" if at else ""


def test_next_reward_cases_from_the_brief():
    assert mirror_next_reward(2, False) == "1 more for a SHIELD"
    assert mirror_next_reward(4, True) == "1 more for a STRIKE"
    assert mirror_next_reward(2, True) == "3 more for a STRIKE"       # a shield already held: the strike is next
    assert mirror_next_reward(15, True) == ""


# ---------------------------------------------------------------- R4 redemption

def test_a_missed_station_is_queued_and_drawn_first_at_the_boss():
    door = body(D, "HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =")
    right = door.split("else if (Choice = Item.Answer):", 1)[1].split("\n            else:", 1)[0]
    # marked before AdvancePlayer moves the stage on (the arena's first draw must already see the queue)
    assert right.index("MarkStation(State, State.Stage, if (State.MissedCurrent?) then FnmMarkMissed else FnmMarkFirstTry)") \
        < right.index("AdvancePlayer(State, Station, DoorIndex, false)")
    mark = body(D, "MarkStation(State:fnm_player_state, Stage:int, Mark:int):void =")
    assert "if (Mark = FnmMarkMissed):\n            set State.RedeemQueue += array{Stage}" in mark
    draw = body(D, "DrawItem(State:fnm_player_state):void =")
    assert "if (State.Mode = fnm_mode.Race, AtArena(State)?, Next := State.RedeemQueue[0]):" in draw
    assert "set Tier = StationTier(State, Next)" in draw
    show = body(D, "ShowCurrent(State:fnm_player_state):void =")
    assert '"REDEMPTION: STATION {State.RedeemStage}  -  {TierName}"' in show


def test_redeemed_only_first_try_and_before_the_hit_lands():
    redeem = body(D, "Redeem(State:fnm_player_state)<transacts>:logic =")
    assert "for (Queued : State.RedeemQueue, Queued <> Stage) { Queued }" in redeem       # off the queue either way
    first_try = redeem.split("if (State.MissedCurrent?):", 1)
    assert "false" in first_try[1].split("else:", 1)[0]                                   # right after a wrong pad: not redeemed
    assert "set State.Redeemed += 1" in first_try[1] and "FnmMarkRedeemed" in first_try[1]
    hit = body(D, "BossHit(State:fnm_player_state, A:fnm_arena):void =")
    assert hit.index("Redeemed := Redeem(State)") < hit.index("Character.Damage(Amount)")   # the killing pad counts too
    assert 'Head := if (Redeemed?) then "REDEEMED!"' in hit


def test_medal_counts_a_redeemed_station_half():
    run = body(D, "FinishRun(State:fnm_player_state, FanfareDelay:float):void =")
    assert "Halves := 2 * State.FirstTryCorrect + State.Redeemed" in run
    assert "Earned := FnmMedalHalves(Halves, Total)" in run and "Medal := GateMedal(Earned, Time)" in run
    medal = LOGIC.split("FnmMedalHalves(Halves:int, Total:int)<transacts>:string =", 1)[1].split("\n\n", 1)[0]
    assert 'if (Halves >= 2 * Total) then "GOLD"' in medal
    assert 'else if (Halves * 10 >= Total * 14) then "SILVER"' in medal                   # today's 70 %, in halves


def medal_halves(halves, total):
    if halves >= 2 * total:
        return "GOLD"
    if halves * 10 >= total * 14:
        return "SILVER"
    return "BRONZE"


def medal_today(first, total):
    """fnm_logic FnmMedal (today's rule, the gates G10 keeps)."""
    if first >= total:
        return "GOLD"
    if first * 10 >= total * 7:
        return "SILVER"
    return "BRONZE"


def test_halves_keep_todays_gates():
    for first in range(11):
        assert medal_halves(2 * first, 10) == medal_today(first, 10)          # no redemption: exactly today's medal
    assert medal_halves(2 * 6 + 2, 10) == "SILVER"                            # 6 first try + 2 redeemed = 7.0
    assert medal_halves(2 * 9 + 1, 10) == "SILVER"                            # 9.5: redemption never buys GOLD


# ---------------------------------------------------------------- C2 shield

def test_shield_takes_the_penalty_but_not_the_lesson():
    door = body(D, "HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =")
    wrong = door.split("            else:\n                set State.MissedCurrent = true", 1)[1]
    # streak and first-try credit go first, then the shield returns before any penalty is picked
    assert wrong.index("set State.Streak = 0") < wrong.index("if (State.Shield?):") < wrong.index("Kind := PickPenalty()")
    assert "ShieldSaved(State, Station, StationIndex + 1, FeedbackFor(Item, Choice))\n                    return" in wrong
    pad = body(D, "HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =")
    assert pad.index("if (State.Shield?):") < pad.index("Kind := PickPenalty()")
    saved = code(body(D, "ShieldSaved(State:fnm_player_state, Station:fnm_station, StationNumber:int, Lesson:string)<suspends>:void ="))
    for banned in ("Punish(", "ChargeWrongDoor(", "PickPenalty(", "AdvancePlayer(", "set State.FirstTryCorrect"):
        assert banned not in saved, banned
    assert 'Retry(State, "SHIELD SAVED YOU  -  still wrong: {Lesson}")' in saved
    assert "set State.Shield = false" in saved and "State.Hud.SetShield(false)" in saved
    earn = body(D, "EarnRewards(State:fnm_player_state):string =")
    assert "if (State.Streak = ShieldStreak, not State.Shield?):" in earn and "State.Hud.SetShield(true)" in earn


# ---------------------------------------------------------------- C3 strike

def test_strike_never_touches_the_targets_run():
    effect = code(body(D, "StrikeEffect(Target:fnm_player_state, Kind:fnm_penalty)<suspends>:void ="))
    land = code(body(D, "StrikeLand(Striker:fnm_player_state, Target:fnm_player_state)<suspends>:void ="))
    for text in (effect, land):
        for banned in ("SendTo", "Retry(", "Reshuffle(", "DrawItem(", "ShowCurrent(", ".Streak", ".FirstTryCorrect",
                       ".MissedCurrent", ".CurrentItem", "ChargeWrongDoor(", "Punish("):
            assert banned not in text, banned
    # the light pool only: Freeze, Mud, Dizzy (blur, no Spin), Lights Out
    assert "Spin(" not in effect and "fnm_penalty.Yeet" not in D.split("PickStrike()", 1)[1].split("\n\n", 1)[0]
    pool = body(D, "PickStrike()<transacts>:fnm_penalty =")
    assert "array{fnm_penalty.Freeze, fnm_penalty.Mud, fnm_penalty.Dizzy, fnm_penalty.Blackout}" in pool


def test_strike_flow_warning_shield_immunity():
    later = body(D, "StrikeLater(State:fnm_player_state, Streak:int)<suspends>:void =")
    assert later.index("Sleep(StrikeDelaySeconds)") < later.index('FlashBig("INCOMING STRIKE!"') \
        < later.index("Sleep(StrikeWarnSeconds)") < later.index("StrikeLand(State, Target)")
    assert "if (DebugStrikeSelf?) then option{State} else StrikeTarget(State)" in later
    assert "LeaderBonus(State, Streak)" in later
    land = body(D, "StrikeLand(Striker:fnm_player_state, Target:fnm_player_state)<suspends>:void =")
    assert land.index("if (Target.Shield?):") < land.index("Kind := PickStrike()") < land.index("set Target.ImmuneUntil = Now + StrikeImmuneSeconds")
    assert "Broadcast(FnmFeedShieldBlock(Target.Player, Striker.Player)" in land
    assert "Broadcast(FnmFeedStrike(Striker.Player, StrikeVerb(Kind), Target.Player)" in land
    open_ = body(D, "StrikeOpen(Target:fnm_player_state, Now:float)<transacts>:logic =")
    for needle in ("not Target.Finished?", "not AtArena(Target)?", "not InVestibule(Target)?", "Now >= Target.ImmuneUntil",
                   "not Target.Struck?", "Target.StartTime >= 0.0"):
        assert needle in open_, needle
    target = body(D, "StrikeTarget(State:fnm_player_state):?fnm_player_state =")
    assert "SortRace(" in target and "K < Mine" in target                                 # only racers ahead, strip order


def test_feed_lines_say_who():
    assert 'FnmFeedStrike<localizes>(Striker:agent, Verb:string, Target:agent):message = "{Striker} {Verb} {Target}!"' in D
    assert '''FnmFeedShieldBlock<localizes>(Target:agent, Striker:agent):message = "{Target}'s shield blocked {Striker}!"''' in D
    assert 'FnmFeedIncoming<localizes>(Striker:agent):message = "INCOMING STRIKE from {Striker}!"' in D


# ---------------------------------------------------------------- medal v2, brag grid, record

def test_brag_grid_follows_the_board():
    run = body(D, "FinishRun(State:fnm_player_state, FanfareDelay:float):void =")
    assert run.index('State.Hud.ShowResults("FINISH!"') < run.index("State.Hud.ShowBragGrid(State.Marks, BossMark, Flawless, NextGoal, IslandCode)")
    goal = body(D, "NextGoalLine(Medal:string, Halves:int, Total:int, Time:float)<transacts>:string =")
    assert '"FLAWLESS needs {Total}/{Total} first try' in goal and '"{Target} needs ' in goal
    gate = body(D, "GateMedal(Medal:string, Time:float)<transacts>:string =")
    assert "if (MedalTimeGates?, Par > 0.0, Time > Par) then FnmMedalDown(Medal) else Medal" in gate


def test_a_lone_first_finish_is_not_a_record():
    run = body(D, "FinishRun(State:fnm_player_state, FanfareDelay:float):void =")
    assert run.index("Rival := HasRival(Skill, State.Player, Time)") < run.index("RecordResult(Skill, State.Player, Time, Splits)")
    assert "Celebrate := if (IslandRecord?, Rival?, not State.Partial?) then true else false" in run
    assert 'RecordTail := if (Celebrate?) then "   NEW!" else ""' in run
    assert "if (Celebrate?):\n            Broadcast(FnmFeedRecord(" in run
    assert "if (NewBest?, HadBest?) then true else false, Celebrate, Medal," in run              # the record sound
    rival = body(D, "HasRival(Skill:int, Who:player, Time:float):logic =")
    assert "Row.Who <> Who" in rival and "Each <> Who" in rival                                # never against yourself


# ---------------------------------------------------------------- analytics, small fixes, compact slate

def test_analytics_seam():
    assert "fnm_analytics := class(tag){}" in src("fnm_tags")
    door = body(D, "HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =")
    assert "Analytics(if (Device := StationAnalytics[StationIndex]) then Device else false, State.Player," in door
    assert 'Analytics(FinishAnalytics, State.Player, "finish")' in D
    assert 'Analytics(BossAnalytics, State.Player, "boss kill")' in body(D, "BossDown():void =")
    assert "Device.Submit(Player)" in body(D, "Analytics(MaybeDevice:?analytics_device, Player:player, What:string):void =")


def test_arena_fixes():
    pad = body(D, "HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =")
    held = pad.split("else if (A.Boss?, not BossAlive?):", 1)[1].split("else if (Choice = Item.Answer):", 1)[0]
    assert "BossHit(" not in held and "Punish(" not in held and "set State.Busy = false" in held   # no answer taken
    hit = code(body(D, "BossHit(State:fnm_player_state, A:fnm_arena):void ="))
    # the killing hit (Left 0) plays no boss_hit: boss_dead + BOSS DOWN carry the kill
    assert "if (Left > 0) then Sound(State.Player, fnm_cue.BossHit)" in hit
    assert hit.count("fnm_cue.BossHit") == 1
    assert 'if (FnmContains(TierName, "Boss")?) then "Final Stretch" else TierName' in D
    assert "Director.MissFeed(State, FnmFeedBmWrong(State.Player, Past)," in src("fnm_bossmode")
    assert "Director.Broadcast(FnmFeedBmWrong(" not in src("fnm_bossmode")


def test_compact_slate_calls():
    calls = re.findall(r"State\.Hud\.SetCompact\((\w+)\)", D)
    assert calls == ["Want"]                                                  # one place tells the HUD
    upd = body(D, "UpdateCompact(State:fnm_player_state):void =")
    assert "(State.RetryHolding? or InArena?)" in upd and "not State.Finished?" in upd and "not State.Picking?" in upd
    assert "UpdateCompact(State)" in body(D, "ArenaArrival(State:fnm_player_state):void =")
    retry = body(D, "Retry(State:fnm_player_state, Lesson:string)<suspends>:void =")
    assert retry.index("set State.RetryHolding = true") < retry.index("ShowCurrent(State)") < retry.index("Sleep(WrongFeedbackSeconds)") \
        < retry.index("EndRetryHold(State)")
