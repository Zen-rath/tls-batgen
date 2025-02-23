TLS Battle Generator - README
=============================

Overview
--------
The Last Starship Battle (TLS) Battle Generator script.

This script takes the savegame.space file, and adds multiple copies of any .ship files it finds in the same folder, to produce a new "savegame_out.space" file containing all those ships.

Ships are repositioned into sensible battle starting positions, facing each other, 2000 distance apart, and are ready for battle!
 
Elements of each .ship filename control how many ships are added, their friendly/hostile faction, and their starting AI-strategy, using the following filename format:

<count>.<ship-name>.<AI-strategy>.<faction>.ship

Count: Number of copies of this ship file to add into the battle. Each ship is given a unique name suffix -1, -2, -3 etc...
Ship-Name: this name will replace the ship's current name.
AI-strategy: one of the allowed AI strategies. This single value will be set for all copies of this ship file.
Faction: FriendlyShip or HostileShip

To use this script, put all above the files into a folder, and execute tls-batgen.py. 


Usage Instructions
------------------

You'll need to install https://www.python.org/downloads/ to execute this python script. Tick the box "Add python.exe to PATH" on the installer.

1. Place the script (tls-batgen.py), your source .space file (a default one is already included), and two or more .ship files in the same directory.
2. Make sure the ship files follow the naming format:
   <count>.<ship-name>.<strategy>.<faction>.ship
   - The <ship-name> can include spaces.
   - <strategy> must be one of the allowed values: StrategyVeryCloseOrbit, CloseRangeAggressive, MediumRangeOrbit, LongRangeSniper, FastMovingJet.
   - <faction> must be either FriendlyShip or HostileShip.
3. Open Windows Command Prompt, and navigate to the directory, then run the script by typing the command: 
   
       tls-batgen.py

4. If there are any validation errors (such as incorrect file naming), the script will exit with an error.
5. On successful completion, the script writes a new output file (savegame-start.space) and prints a summary.
6. Copy the "savegame-start.space" file into the TLS save game folder: C:\Users<your-windows-login-name>\AppData\Local\Introversion\LastStarship\saves\


Summary of modifications the script makes to the same-game / ship files
-----------------------------------------------------------------------

Summary of Changes Applied by the Code

Output Save-Game File (Source .space File):

- File Selection: Loads a source save-game file by scanning all *.space files and ignoring any that end with “-start.space” or “-end.space”.

- Missions Node Clearance: Completely removes all content (attributes and child nodes) from the top-level node tagged “Missions”.
 
- Friendly Newship Removal: Removes any nodes from the source file that represent friendly newships (nodes with Name “NEWSHIP” and Type “FriendlyShip”).

- Header Update: Reads the “NextId” value from the header and later updates it to reflect the next available global ID after processing all appended ships.

- Time and Play Attributes: Sets top-level “TimeIndex” and “PlayTime” attributes to “0”.

- System Orders: Creates or updates a top-level “SystemOrders” node with attributes: Id = 1 Scope = System FleetLogistics = false BattleStations = true

Ship File Parsing & Layer Creation:

- Processes each ship file that follows the naming format <count>.<ship-name>.<strategy>.<faction>, generating the specified number of ship layers.

- ID Assignment (Two-Pass Update):
	- In a first pass, assigns new globally unique IDs to all nodes in the ship layer (except for nodes with tag “Network”, whose Ids remain unchanged).
	- In a second pass, updates all related ID attributes (those ending in “Id” except for excluded keys, and “Carrying”) using a mapping from old to new values.

- Node Removal: Completely removes any “workqueue” node from the ship’s node tree rather than merely clearing its contents.

- Crew Attributes: Clears attributes from nodes representing crew members (removing keys like “JobId” and “State”).

- Entities Removal in Habitation Subtree: In any node with tag “Habitation” (case‑insensitive), recursively removes any attribute named “Entities” from all of its descendant nodes, regardless of their tag.

- Positional Attributes: For each ship layer:
-- For FriendlyShip layers: Sets “Offset.x” to 0, “Rotation” to 0, and “Offset.y” based on a friendly counter (using a calculated offset).
-- For HostileShip layers: Sets “Offset.x” to 2000, “Rotation” to 180, and “Offset.y” based on a hostile counter.

- ShipAI Sub-node
-- Appends a “ShipAI” sub-node to each ship layer with attributes: “Strategy” set from the filename, “Engaged” set to true, “Broadside” set to -1
-- LayerOrders Node: For each appended ship layer, creates or updates a top-level “LayerOrders” node with attributes: Scope = Layer, Salvage = false, Gather = false, Mining = false, ExteriorWork = false, Id = (the new unique ID of the appended ship)
-- Validation: Checks that at least one friendly and one hostile ship have been appended; if not, the script exits with an error.

- Output Filename: Writes the output save-game file with a filename derived from the input save-game file, appended with “-start”.
