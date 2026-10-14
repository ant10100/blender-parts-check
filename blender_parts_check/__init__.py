# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender Parts Check: read-only checks for explicitly paired parts."""


def register():
    from . import ui
    ui.register()


def unregister():
    from . import ui
    ui.unregister()
