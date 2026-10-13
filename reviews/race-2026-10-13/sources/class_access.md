# Class access to a UEFN island: research notes

Researched 2026-10-13. Sources are Epic dev docs read in a real browser (Playwright, page innerText), so quotes are verbatim. Epic doc pages carry no per-page date; "fetched 2026-10-13" is the date. Release-note dates come from the What's New page (42.00 = Aug 20 2026, 42.30 = Oct 1 2026).

## Q1. Who can join a private version code? Playtest groups? Under-13? Unlisted?

**Private version code: owner/team only, unmoderated.**
- "Private version codes can be used to playtest your island on different platforms and consoles. These versions are unmoderated, so only you can use the private version code to access your island."
  https://dev.epicgames.com/documentation/fortnite/visibility-screen-in-fortnite
- "Once the project finishes loading, a Private Version code is created for your project at this time... To use the code, click Copy and send this code to your team members or save in your personal files."
  https://dev.epicgames.com/documentation/fortnite/publishing-projects-in-unreal-editor-for-fortnite
- Team members edit; they are not players-by-invite: "You cannot collaborate on UEFN projects with anyone under the age of 18." (Collaborating in UEFN) https://dev.epicgames.com/documentation/fortnite/collaborating-in-unreal-editor-for-fortnite
- Note: Epic's current docs say the private-version code comes from Project > Publish Project (UEFN) and also from Launch Memory Calculation / Upload Private Version. Either creates one.
  https://www.epicgames.com/help/creative-c-35915197/a21796988 ("How do I create a Playtest or Private Version of my island?")

**Playtest group = the only way to let non-team people into a private version.**
- Creator Portal > Projects > Playtests > Create Playtest > pick the Private Version. "This creates a special code playtesters can use to access the island." "Playtesters do not have a hand in creating the island."
- Add people: Manage Team > Playtest Group tab > Add New Playtesters > Copy URL to Clipboard > email the invite URL. Invitee signs in with an Epic account and clicks Join Playtest group.
- Limit: "The number of playtesters you can have is limited to 50. You'll need to remove previous playtesters from the team if you want to add new playtesters."
- Under-13 / under-18: "You must be an adult to accept a Playtest Invitation. If you haven't done so already, you will need to complete the age verification process. Epic Games has partnered with SuperAwesome to confirm that you are an adult."
  https://dev.epicgames.com/documentation/fortnite/adding-playtesters-in-fortnite-creative
- Result: cabined (under-13) accounts cannot be added to a playtest group. Neither can any minor. Students cannot use a private version or a playtest.
- Switching version: "update the playtest version and create a new playtest code" (Update Playtest). The playtest code changes each time.

**Unlisted publish option: exists.**
- "You can set your island to publish automatically once it passes content review by selecting either the Listed or Unlisted option."
- "Unlisted islands can only be found by their island code. Unlisted islands do not appear in Discover and do not surface in search."
  https://dev.epicgames.com/documentation/fortnite/visibility-screen-in-fortnite
- "Unlisted: This means your project has successfully passed moderation, and it has an island code, but is not available in Discover... the island code associated with an unlisted project can be shared with anyone."
  https://dev.epicgames.com/documentation/fortnite/publishing-page-features-in-fortnite-creative
- Unlisted still requires: passing memory check, passing moderation, IARC questionnaire, and "You must be 18 years or older to publish a project." (Aaron qualifies.)
  https://dev.epicgames.com/documentation/fortnite/publishing-projects-in-unreal-editor-for-fortnite

**Can under-13 (cabined) accounts PLAY a published (unlisted) island?** Partly confirmed.
- "Players with Cabined Accounts can still play Fortnite... but won't be able to access certain features such as voice chat until their parent or guardian provides consent." Disabled in cabined accounts: voice chat and free text chat, real-money purchases, recommendations, custom display names.
  https://safety.epicgames.com/en-US/cabined-accounts and https://safety.epicgames.com/en-US/parental-controls
- Island access is gated by IARC rating vs the parental-control rating limit: "Your Parental Controls PIN will be required to unlock experiences for your child that are rated above your age-rating setting." Parents can also switch off Creative/UEFN for a child.
- IARC range: "ranging from E to a maximum rating of Teen" (search snippet from Epic's parental-controls/rating pages). A math/ELA island should rate E or E10+.
- NOT FOUND: the default rating limit on a fresh cabined account, and any statement that unlisted islands are exempt from rating gates. Treat both as unverified.

## Q2. Verse persistence

Source for everything below: https://dev.epicgames.com/documentation/fortnite/using-persistable-data-in-verse (fetched 2026-10-13). Persistence Best Practices page adds no figures.

- Size: "A single weak_map record has a maximum data size of 256 kilobytes (KB) per player." "If you attempt to save data that is larger than 256 KB for a player record, the save will fail and you will get a Verse runtime error." (FitsInPlayerMap can pre-check.)
- Count: "A single island can have up to four persistent variables, that is, four weak_map variables with player as the key type."
- Discrepancy: a search snippet quoted "128 KB / two persistent variables" from an older copy of the Verse reference. The current page says 256 KB / four. Use the current page.
- Published island: "Once your island is published, a persistable record is created for players when their data is stored in the weak_map. This data will then be stored and loaded on any subsequent visits to your island." New versions merge automatically. Backward-compat check runs on publish; after publishing you may only add fields to persistable classes. "Rolling back your island resets all player persistence data."
- Edit session (Launch Session from UEFN): "persistable data can persist across multiple games within a single session. If you exit the session and relaunch a new session, the persistent data will be reset."
- Playtest/private link: "Playtest Session: Persistence data behavior settings are applied when you set up a playtest in Creator Portal when a playtester joins either through a playtest code or private link code... When the player leaves and rejoins the playtest, their data will persist across sessions... To reset the persistable data, you will need to create a new playtesting link code."
- Island Settings device options for both session types: Import From Live (seeds from live data, needs the island published and the player to have played live) or Simulate New User (empty data).
- So: private version / playtest link keeps data across rejoins until you mint a new code. UEFN edit sessions wipe it. Published keeps it. NOT FOUND: separate wording for a private version opened by its owner outside a playtest group.

## Q3. Does the 2026-10-22 thumbnail rule hit private versions?

- "You need the following thumbnail images to submit your island for review: [Landscape 1920x1080, Portrait 1440x1920, Island Name Logo 1440x608; each landscape/portrait needs art+logo and art-only slots]. These thumbnail types become mandatory as of October 22, 2026."
  https://dev.epicgames.com/documentation/fortnite/making-thumbnails-and-videos-in-fortnite-creative
- Publishing flow: "On the Promotional Media screen, upload your required landscape and portrait thumbnails, your logo... The new fields are required as of October 22."
  https://dev.epicgames.com/documentation/fortnite/publishing-from-the-creator-portal-in-fortnite-creative
- Where it sits: Promotional Media is a step of "Create release" (private version -> release -> moderation). "You cannot submit your island for review until you attach a thumbnail." Creating a private version (memory calc / Publish Project) and creating a playtest have no media step in any doc.
- Answer: public publishing only (every release submitted for review, which includes updates because an update is a new release). Private versions and playtests are not affected. Update-applies is my inference from the release flow; no Epic sentence says "updates" explicitly.
- Not in the release notes 40.40-42.30 (searched). Docs-only announcement.

## Q4. Max players and memory

- Island Settings: "Max Players | 16, 1-100 | Set the maximum number of players that can play at the same time." Also "Matchmaking Max Players Per Session | 32 | Maximum number of players matchmaking allows to join a session." and "Island Matchmaking Privacy | Party Choice, Public, Private: Public games can be joined by anyone. Private games are restricted to groups of players in the same party."
  https://dev.epicgames.com/documentation/fortnite/island-settings-in-unreal-editor-for-fortnite
- Memory: "The bar shows a maximum of 100,000 memory units." "With streaming enabled, memory is calculated based on the player's position on the island rather than the total memory used by all the assets on the island." "Note that if any area in your level exceeds 100,000, you will not be able to publish your island." "The memory calculation system in UEFN runs only at Edit time, and cannot be used to evaluate memory use at Play time... custom runtime logic can lead to high memory use."
  https://dev.epicgames.com/documentation/fortnite/memory-management-in-unreal-editor-for-fortnite
- Answer: NOT FOUND. No Epic page ties the 100,000-unit budget to Max Players; there is no tiered limit for >16 or >50. The only memory-vs-setting notes are Enable Jam emotes and Patchwork Memory Mode. Memory budget is a fixed edit-time number; per-player runtime cost is only measurable with Spatial Profiler / Memory Snapshot (Monitor Performance option).
- Practical: a class of 25-30 needs Max Players >= 30 (default 16). Default Matchmaking Max Players Per Session of 32 already covers 30.
- Unverified: how 28 kids on separate devices reach the SAME server from one code. Fortnite party-size cap and matchmaking behaviour were not found in Epic docs (community listings show "Max Social Party Size" 16-25, unofficial). Test with a few accounts before class day.

## Q5. Education guidance (2025-2026)

- https://dev.epicgames.com/documentation/fortnite/education-in-fortnite-creative: "Free Fortnite lesson plans are available to educators who want to use Creative or Unreal Editor for Fortnite (UEFN) in creative ways in the classroom." Plans cover Hour of Code, humanities/arts/design, science/engineering/math, UN SDGs, LEGO Fortnite, TIME Studios March Through Time. Lesson-plan template PDF linked.
- https://www.unrealengine.com/en-US/educators/accelerator: Epic Educator Accelerator, "Secondary (Grades 6-12) school teachers... will learn how to integrate Epic tools into their classroom... Unreal Engine and Unreal Editor for Fortnite (UEFN)." "The Summer 2026 Epic Educator Accelerator will run from July 27-31." Already past; next session not announced on the page.
- UEFN Student Bootcamp (summer, Europe/North America students): https://www.unrealengine.com/learning/uefn-student-bootcamp-application-is-open-now
- NOT FOUND: any school/classroom account type, class roster tool, teacher-managed playtest groups for minors, or guidance on running a class on a creator island. Epic's only education account-adjacent rules are the cabined-account/parental-control pages above.

## What this means for a class pilot

1. A private version or playtest code cannot serve students: private = "only you", and playtest group members must be adults (50 max). No minor, and so no cabined account, can be added.
2. The workable path is Unlisted publish: code-only, off Discover and search, shareable "with anyone". It needs moderation, an IARC rating, a memory pass, Aaron (18+) as publisher, and from 2026-10-22 landscape + portrait + logo thumbnails.
3. Student access then depends on each child's parental-control rating limit and whether Creative/UEFN is switched off; E/E10+ rating helps, and a parent PIN can unlock a single island. Cabined accounts have no chat, which suits class use. Expect a few kids needing a parent action.
4. Set Max Players to 30+ (default 16); no documented memory penalty for it, but run Spatial Profiler with test players. Persistence on the published island survives sessions (256 KB, four maps); rollbacks and UEFN edit sessions wipe it.
5. Unverified and worth one test before class: all ~28 students landing on one server, which needs a Max Players / party / matchmaking-privacy check, plus how long moderation takes for an unlisted release.
