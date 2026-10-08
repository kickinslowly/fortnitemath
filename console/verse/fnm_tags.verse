# FNM console runtime -- Verse tags that mark the course's devices (no @editable references needed).
# Each door trigger carries fnm_station_NN + fnm_door_X; each station's entry teleporter carries
# fnm_station_NN + fnm_entry; the finish teleporter carries fnm_finish. The director finds them at
# runtime with FindCreativeObjectsWithTag. Up to 20 stations.

using { /Verse.org/Simulation/Tags }

fnm_entry := class(tag){}
fnm_finish := class(tag){}
# Penalty props parked out of sight that the director moves onto a punished player (fnm_rig.verse).
fnm_ice := class(tag){}
fnm_spike := class(tag){}
fnm_yeet := class(tag){}
# Per-player effect devices (tools/build_rigs.py): the movement modulator that slows a muddy player, and one
# post-process device per screen effect.
fnm_mud := class(tag){}
fnm_pp_frost := class(tag){}
fnm_pp_mud := class(tag){}
fnm_pp_dizzy := class(tag){}
# The orbit camera a frozen/spiked player watches through.
fnm_penalty_cam := class(tag){}
# Hidden trigger bound to the starting-loadout item granter (tools/build_rigs.py).
fnm_loadout := class(tag){}
# The movement modulator that speeds up a player after a first-try right answer (tools/build_rigs.py).
fnm_boost := class(tag){}
# Hallway obstacles (tools/build_course.py): shipping containers the director slides across the hallway, along
# their own forward axis and back.
fnm_slider := class(tag){}
# Ice hallways (tools/build_course.py ICE_STATIONS): a mutator zone over each icy floor, and the one player movement
# settings device (low friction) the director applies to a player while they are inside such a zone.
fnm_ice_zone := class(tag){}
fnm_ice_floor := class(tag){}
# A station's guard spawner (tools/build_guards.py), also tagged with its fnm_station_NN.
fnm_guards := class(tag){}
# The victory area (tools/build_finish.py): the podium's two button devices, and the giant all-time screen's
# heading billboard and row billboards (rows are ordered by height, top row = rank 1).
fnm_new_race := class(tag){}
fnm_change_skill := class(tag){}
fnm_hall_head := class(tag){}
fnm_hall_row := class(tag){}
# The boss arena (tools/build_course.py arena, maps/starter/LAYOUT.md "Boss arena"): NOT a numbered station. Its entry
# teleporter carries fnm_boss + fnm_entry and its four answer-pad triggers fnm_boss + fnm_door_a..d (so
# FindStationParts(fnm_boss) reads it like a station); the boss's guard spawner, the adds spawner and the exit gate
# barrier have a tag each.
fnm_boss := class(tag){}
fnm_boss_spawner := class(tag){}
fnm_boss_adds := class(tag){}
fnm_boss_gate := class(tag){}
fnm_door_a := class(tag){}
fnm_door_b := class(tag){}
fnm_door_c := class(tag){}
fnm_door_d := class(tag){}
fnm_station_01 := class(tag){}
fnm_station_02 := class(tag){}
fnm_station_03 := class(tag){}
fnm_station_04 := class(tag){}
fnm_station_05 := class(tag){}
fnm_station_06 := class(tag){}
fnm_station_07 := class(tag){}
fnm_station_08 := class(tag){}
fnm_station_09 := class(tag){}
fnm_station_10 := class(tag){}
fnm_station_11 := class(tag){}
fnm_station_12 := class(tag){}
fnm_station_13 := class(tag){}
fnm_station_14 := class(tag){}
fnm_station_15 := class(tag){}
fnm_station_16 := class(tag){}
fnm_station_17 := class(tag){}
fnm_station_18 := class(tag){}
fnm_station_19 := class(tag){}
fnm_station_20 := class(tag){}

# Station tag types in course order (the director walks these until the first station with no entry).
FnmStationTags()<transacts>:[]castable_subtype(tag) = array{fnm_station_01, fnm_station_02, fnm_station_03, fnm_station_04, fnm_station_05, fnm_station_06, fnm_station_07, fnm_station_08, fnm_station_09, fnm_station_10, fnm_station_11, fnm_station_12, fnm_station_13, fnm_station_14, fnm_station_15, fnm_station_16, fnm_station_17, fnm_station_18, fnm_station_19, fnm_station_20}

# Sound layer (tools/build_audio.py, fnm_audio.verse): one audio player per cue, tagged fnm_cue_<id>, in fnm_cue
# enum order.
fnm_cue_countdown3 := class(tag){}
fnm_cue_countdown2 := class(tag){}
fnm_cue_countdown1 := class(tag){}
fnm_cue_go := class(tag){}
fnm_cue_correct := class(tag){}
fnm_cue_correct_retry := class(tag){}
fnm_cue_wrong := class(tag){}
fnm_cue_door_open := class(tag){}
fnm_cue_boost := class(tag){}
fnm_cue_streak2 := class(tag){}
fnm_cue_streak3 := class(tag){}
fnm_cue_streak4 := class(tag){}
fnm_cue_streak5 := class(tag){}
fnm_cue_streak6 := class(tag){}
fnm_cue_streak7 := class(tag){}
fnm_cue_perfect := class(tag){}
fnm_cue_finish := class(tag){}
fnm_cue_new_best := class(tag){}
fnm_cue_new_record := class(tag){}
fnm_cue_medal_gold := class(tag){}
fnm_cue_medal_silver := class(tag){}
fnm_cue_medal_bronze := class(tag){}
fnm_cue_penalty_freeze := class(tag){}
fnm_cue_penalty_spike := class(tag){}
fnm_cue_penalty_mud := class(tag){}
fnm_cue_penalty_dizzy := class(tag){}
fnm_cue_penalty_blackout := class(tag){}
fnm_cue_penalty_yeet := class(tag){}
fnm_cue_no_skip := class(tag){}
fnm_cue_guards_up := class(tag){}
fnm_cue_welcome := class(tag){}
fnm_cue_choose := class(tag){}
fnm_cue_music_t1 := class(tag){}
fnm_cue_music_t2 := class(tag){}
fnm_cue_music_t3 := class(tag){}
fnm_cue_music_t4 := class(tag){}
fnm_cue_music_t5 := class(tag){}
fnm_cue_boss_fight := class(tag){}
fnm_cue_boss_hit := class(tag){}
fnm_cue_boss_dead := class(tag){}
# Cue tag types in fnm_cue enum order (FnmCues()).
FnmCueTags()<transacts>:[]castable_subtype(tag) = array{fnm_cue_countdown3, fnm_cue_countdown2, fnm_cue_countdown1, fnm_cue_go, fnm_cue_correct, fnm_cue_correct_retry, fnm_cue_wrong, fnm_cue_door_open, fnm_cue_boost, fnm_cue_streak2, fnm_cue_streak3, fnm_cue_streak4, fnm_cue_streak5, fnm_cue_streak6, fnm_cue_streak7, fnm_cue_perfect, fnm_cue_finish, fnm_cue_new_best, fnm_cue_new_record, fnm_cue_medal_gold, fnm_cue_medal_silver, fnm_cue_medal_bronze, fnm_cue_penalty_freeze, fnm_cue_penalty_spike, fnm_cue_penalty_mud, fnm_cue_penalty_dizzy, fnm_cue_penalty_blackout, fnm_cue_penalty_yeet, fnm_cue_no_skip, fnm_cue_guards_up, fnm_cue_welcome, fnm_cue_choose, fnm_cue_music_t1, fnm_cue_music_t2, fnm_cue_music_t3, fnm_cue_music_t4, fnm_cue_music_t5, fnm_cue_boss_fight, fnm_cue_boss_hit, fnm_cue_boss_dead}
