# FNM console runtime -- the one place that speaks /Verse.org/SpatialMath. The rest of the runtime uses
# /UnrealEngine.com/Temporary/SpatialMath (transforms, TeleportTo, MoveTo), and both modules define vector3, so a file
# that imports both cannot name the type. fort_character's impulse functions take the Verse.org vector3; this builds one.

using { /Verse.org/SpatialMath }

# A /Verse.org/SpatialMath vector3 from world X, Y, Z parts (its own fields are Forward = X, Left = -Y, Up = Z), for
# fort_character.ApplyLinearImpulse and friends.
FnmImpulse(X:float, Y:float, Z:float):vector3 = vector3{Forward := X, Left := -Y, Up := Z}
