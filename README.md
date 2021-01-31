# Production chain calculator

This is a generic production chain calculator.
I made it for calulating production chains in various logistic games, such as
Factorio, Satisfactory, and Dyson Sphere Program.

It is entirely game-agnostic, meaning you can calculate production chains / ratios for any game out there,
you just have to create a file that specifies which recipes exist in the game.

Allow me to demonstrate:
```
Sucessfully loaded dsp.txt
Items to produce/s (amount,item + ...): 2,bluescience + 2,redscience + yellowscience
--- Required products ---
bluescience     :    2/s -   6 matrix
redscience      :    2/s -  12 matrix
yellowscience   :    1/s -   8 matrix

hydrogen        :    4/s -  16 refinery
diamond         :    1/s -   2 smelter
magneticcoil    :    2/s -   1 assembler
circuitboard    :    2/s -   1 assembler
titaniumcrystal :    1/s -   4 assembler

ironingot       :    1/s -   1 smelter
copperingot     :    2/s -   2 smelter
titaniumingot   :    3/s -   6 smelter
magnet          :    2/s -   3 smelter
organiccrystal  :    1/s -   6 chemicalplant

ironore         :    3/s -   6 ironvein
copperore       :    2/s -   4 coppervein
titaniumore     :    6/s -  12 titaniumvein
water           :    1/s -   2 waterpump
plastic         :    2/s -   6 chemicalplant

graphite        :    7/s -  14 smelter
refinedoil      :    5/s -  10 refinery

coal            :   14/s -  28 coalvein
oil             :    8/s -   8 oilwell
--- Needed factories ---
matrix          :  26
refinery        :  26
smelter         :  28
assembler       :   6
chemicalplant   :  12
ironvein        :   6
coppervein      :   4
titaniumvein    :  12
waterpump       :   2
coalvein        :  28
oilwell         :   8
--- Additional products ---
refinedoil      :    3/s
--- Tree View ---
bluescience 2/s - 6 matrix
    magneticcoil 2/s - 1 assembler
        magnet 2/s - 3 smelter
            ironore 2/s - 4 ironvein
        copperingot 1/s - 1 smelter
            copperore 1/s - 2 coppervein
    circuitboard 2/s - 1 assembler
        ironingot 1/s - 1 smelter
            ironore 1/s - 2 ironvein
        copperingot 1/s - 1 smelter
            copperore 1/s - 2 coppervein
redscience 2/s - 12 matrix
    graphite 4/s - 8 smelter
        coal 8/s - 16 coalvein
    hydrogen 4/s - 16 refinery
        oil 8/s - 8 oilwell
yellowscience 1/s - 8 matrix
    diamond 1/s - 2 smelter
        graphite 1/s - 2 smelter
            coal 2/s - 4 coalvein
    titaniumcrystal 1/s - 4 assembler
        organiccrystal 1/s - 6 chemicalplant
            plastic 2/s - 6 chemicalplant
                refinedoil 4/s - 8 refinery
                graphite 2/s - 4 smelter
                    coal 4/s - 8 coalvein
            refinedoil 1/s - 2 refinery
            water 1/s - 2 waterpump
        titaniumingot 3/s - 6 smelter
            titaniumore 6/s - 12 titaniumvein
```

## Features

- Simple command line interface to specify which items to produce
- Calculates needed raw and intermediate items
- Prints a summary of how many items need to be produced per second, and calculates how many production facilities are needed
- Takes into account recipes with multiple outputs and shows surplus production
- Optional recipe support -> select which recipe to use if there are multiple
- Shows total amount of needed production facilities 
- Show a tree view of which items need which subitems and so on
- Display ingredients of each item in summary view, to plan isolated modules
- Customizable output, toggle treeview, summary, total factory count etc

### Wishlist

These features are not implemented yet, but I'd like to add them in the future.
Roughly in order of priority
- Basic graphical interface and binary executable, so its easily usable on windows without a CLI
- Circular dependencies 
    For Oil cracking recipes
- Different time formats (items per min, hour etc)
- Complete resource file for Dyson Sphere Program
- Resource files for other games (factorio, satisfactory)
- Inverse calculator: Given some input resources, how many can I make of the requested products?

## Installation

Clone this repo and copy `calculator.py` and `dsp.txt` wherever you want them to live.
A working python installation is needed. I used python 3.9.1, you need at least python 3.7 (for the yummy dataclasses).

## Usage

```bash
python calculator.py --recipes dsp.txt
```
You will be prompted to enter the items you want to produce.
They follow this format: `<item amount> ,<item name> + <item amount>,<item name> + ...` 
All spaces are optional.

Type `help` to get a list of available commands.
Type `list` or `ls` to show all available items.
Type `exit` or press CTRL-D to quit.

## Recipe file format

The calculator uses a custom file format to define items and recipes.
See `dsp.txt` for an example.

Here is the specification in [Extended Backus-Naur Form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form). (Might not be 100% accurate to that definition, but you get the gist).

```
line        = recipe | whitespace | comment
comment     = '#' [ text ]
recipe      = item-list ';' time ';' factory ';' ingredients
item-list   = item [ '+' item-list ]
ingredients = item [ ';' ingredients ] 
item        = [ number ',' ] text
```

Any leading or trailing whitespace in any token is ignored.
What you specify on the CLI is just an `item-list`.
