# Hexlog TODO — solo play features

Priority-ordered feature ideas for solo play, to review and decide on later.

## 1. Oracle / Yes-No (highest priority)
A Mythic-style oracle dialog: type a question, set odds (impossible -> certain),
get a roll plus a twist/flawed-result table. Turns Hexlog from a tracker into a
game engine.

## 2. Built-in dice roller that logs to the journal
Support notation like `2d6+1`, advantage/disadvantage, and "insert result into
note" so rolls stay in the session record.

## 3. Editable random tables
NPC names, encounters, loot, towns, quest hooks, weather. Make rolls able to
output existing data (e.g. encounter roll -> spawn a monster token on the VTT).

## 4. Combat tracker wired into the VTT
Solo combat is the most bookkeeping-heavy part. Turn order + HP/conditions,
seeded from scene tokens and monster statblocks (CR/HP already in the data model).

## 5. Progress clocks / quest tracking
Track goals as ticking clocks (Blades-in-the-Dark style). Visual countdowns
keep sessions directed; fits the autosave model.

## 6. "What do I know about X?" summary
`@mention` references are already tracked per note. Select an entity and see
every note it appears in, compiled into a timeline. Solo players lose track of
threads between sessions.

## 7. Session recap generator
Group today's notes (timestamps already autosave) into a readable recap for
reopening a campaign weeks later.
