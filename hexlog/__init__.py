"""
Hexlog - a solo RPG companion for D&D-style play.

Tracks characters, NPCs, locations and monster statblocks, provides a
searchable journal with @mention highlighting, and a lightweight virtual
tabletop (VTT) for placing image or color tokens on a map.

Data is persisted as JSON under ~/.config/hexlog/ (dev copy for local
development, prod for the packaged AppImage; both hold data.json, maps/, tokens/).

Run the application with:  python -m hexlog
"""

__version__ = "0.6.4"
