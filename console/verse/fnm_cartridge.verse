# FNM Cartridge Protocol v1 — console-side types. See PROTOCOL.md §8.
# Hand-maintained. Changing this file is a protocol bump.

fnm_tier := struct:
    Tier : int
    Name : string
    Description : string

fnm_item := struct:
    Id : string
    Tier : int
    Prompt : string
    Choices : []string
    Answer : int
    # Per choice: student-facing text for a wrong choice, "" at Answer.
    Feedback : []string
    Explanation : string

fnm_cartridge := struct:
    Protocol : string
    Id : string
    Version : string
    Title : string
    Subtitle : string
    Tiers : []fnm_tier
    Items : []fnm_item
