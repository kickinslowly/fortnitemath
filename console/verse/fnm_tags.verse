# FNM console runtime -- Verse tags that mark the course's devices (no @editable references needed).
# Each door trigger carries fnm_station_NN + fnm_door_X; each station's entry teleporter carries
# fnm_station_NN + fnm_entry; the finish teleporter carries fnm_finish. The director finds them at
# runtime with FindCreativeObjectsWithTag. Up to 20 stations.

using { /Verse.org/Simulation/Tags }

fnm_entry := class(tag){}
fnm_finish := class(tag){}
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
