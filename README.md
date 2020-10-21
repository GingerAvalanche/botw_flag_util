# Breath of the Wild Flag Utilities
Game data and save game data flag utilities for LoZ:BotW

## Dependencies
* A dumped copy of Legend of Zelda: Breath of the Wild (for Wii U or Switch)
* Python 3.7+ (64-bit, added to system PATH)

The following `pip` packages, which will be automatically installed:
* bcml
* oead

## Setup
1. Download and install Python 3.7+, 64-bit. You must choose the "Add to System PATH" option during installation.
2. Open a command line and run `pip install botw_flag_util`

### How to Use

#### Generate flags:
`botw_flag_util generate [path_to_mod_root] [-a] [-r # #] [-b] [-v]`
* `path_to_mod_root` - The path to the root folder of your mod, which contains the `content` folder. Required.
* `-a` - Generate actor flags.
* `-r # #` - Generate revival flags. The first number is the ResetType for MainField actors. The second is the ResetType for CDungeon (shrine) actors. If one of them is set to -1, it will skip flag generation for that field type.
* `-b` - Use big-endian mode. For generating flags for Wii U.
* `-v` - Use verbose mode. Will give more verbose after-action report.

#### Find flags:
`botw_flag_util find [path_to_mod_root] [search_name] [-b] [-v]`
* `path_to_mod_root` - The path to the root folder of your mod, which contains the `content` folder. Required.
* `search_name` - The name of the flag to search for. Will find all flags whose DataName contains `search_name`. For example, `MainField_Npc_HiddenKorok` will find all Korok NPC flags.
* `-b` - Use big-endian mode. For deleting flags for Wii U.
* `-v` - Use verbose mode. Will give more verbose after-action report.

Once the search has been completed, you will be told how many game data and save data flags were found that matched `search_name`. You will then be given three choices:
* `v` - View more detailed information on the flags found: their full names and their types, and then prompt for another choice.
* `d` - Delete all the flags that were found by this search, and then return to the command line.
* `x` - Return to the command line.

##### Quirks
* `botw_flag_util` does not need a Bootup.pack present in your mod to do its thing. If one is not present, it will copy it from your game dump into your mod files and then edit that copy.
* A new copy of gamedata.ssarc and savedataformat.ssarc will always be written to Bootup.pack, even if no changes were made. This is done so that any invalid flags (e.g. duplicate flags) will be deleted from them. Invalid flags will cause BOTW to perform abnormally. This feature was included by request, and should never harm anything, but if you notice that your Bootup.pack's modified date has changed after no changes were made, this is why.
* Knowing which flags to give what properties is a very complicated affair. Rather than try to retrieve all that information from the data files, a stopgap has been developed: inside the `data` folder, where `botw_flag_util` is installed, is a file called `overrides.json`. In this file is a comprehensive set of override conditions. If you have come across any flags that you notice are receiving incorrect values, you may place the flag name inside the dictionary for the correspond flag type/property and give it a value. Any flags with that name as part of their name will receive that value for that property, overriding whatever standard logic applies to that flag during the generation process. For example, inside OVERRIDE_IS_ONE_SAVE is the name/value `"IsGet_": true`. This means that all flags with `IsGet_` in the name will have their `IsSave` property set to `true`. You can modify this file whenever you want, and as long as it is valid JSON and the values are valid for the properties they're being inserted into, the values will be properly overridden. `If you use this feature to create a more comprehensive ruleset for flag generation, please consider opening a PR on GitHub so that others may benefit from it as well.`

## Contributing
* Issues: https://github.com/GingerAvalanche/botw_flag_util/issues
* Source: https://github.com/GingerAvalanche/botw_flag_util

This software is in early, but usable, beta. There are several variable types that are not yet handled, and several cases that are not handled for the variable types that are handled. Feel free to contribute in any way.

## License
This software is licensed under the terms of the GNU Affero General Public License, version 3+. The source is publicly available on Github.
