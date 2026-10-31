-- StashOfExile2 window rules for Lua-based Hyprland configs. UNTESTED groundwork - see linux/README.md.
o.window({ class = "^Stashofexile2$" }, { float = true, center = true, size = { 1400, 1000 } })
o.window({ class = "^Toplevel$", xwayland = true }, { float = true })
