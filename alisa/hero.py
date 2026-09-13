"""ALISA heroine: original anime-style character drawn on tkinter Canvas."""


def draw_hero(c, cx, cy, s, blink, speaking, emotion="neutral"):
    """Draw the heroine centered at (cx, cy) with scale s."""
    SKIN = "#ffd9c0"
    HAIR = "#2b2350"
    GOLD_HI = "#eab308"

    def U(dx, dy):
        return (cx + dx * s, cy + dy * s)

    def lw(n):
        return max(1, int(n * s))

    # back hair
    c.create_oval(*U(-95, -115), *U(95, 115), fill=HAIR, outline="#4c3a7a", width=lw(2))
    # body / shoulders
    pts = [U(-112, 225), U(-58, 132), U(58, 132), U(112, 225)]
    c.create_polygon([p for pt in pts for p in pt], fill="#191238", outline="#4c3a7a", width=lw(2))
    # neckline + gem
    c.create_line(*U(-30, 138), *U(0, 172), *U(30, 138), fill=GOLD_HI, width=lw(3))
    gx, gy = U(0, 168)
    gr = 9 * s
    c.create_polygon(gx, gy - gr, gx + gr, gy, gx, gy + gr, gx - gr, gy,
                     fill="#22d3ee", outline="white", width=1)
    c.create_rectangle(*U(-18, 78), *U(18, 122), fill=SKIN, outline="")
    c.create_oval(*U(-70, -75), *U(70, 85), fill=SKIN, outline="")
    # ears
    c.create_oval(*U(-80, 8), *U(-66, 32), fill=SKIN, outline="")
    c.create_oval(*U(66, 8), *U(80, 32), fill=SKIN, outline="")
    # side locks
    c.create_oval(*U(-92, -12), *U(-58, 122), fill=HAIR, outline="#4c3a7a", width=1)
    c.create_oval(*U(58, -12), *U(92, 122), fill=HAIR, outline="#4c3a7a", width=1)
    # bangs
    for lx, tip in ((-72, -18), (-38, 2), (0, -12), (38, 2), (72, -18)):
        c.create_polygon(*U(lx - 24, -72), *U(lx + 24, -72), *U(lx, tip), fill=HAIR, outline="")
    # hair shine
    c.create_arc(*U(-78, -100), *U(-30, -20), start=100, extent=70,
                 outline=GOLD_HI, width=lw(3), style="arc")
    # brows (emotion-aware)
    if emotion == "sad":
        c.create_line(*U(-56, -30), *U(-26, -20), fill="#3a2c5e", width=lw(3))
        c.create_line(*U(56, -30), *U(26, -20), fill="#3a2c5e", width=lw(3))
    elif emotion == "thinking":
        c.create_arc(*U(-56, -44), *U(-24, -24), start=20, extent=140,
                     outline="#3a2c5e", width=lw(3), style="arc")
        c.create_line(*U(26, -34), *U(54, -34), fill="#3a2c5e", width=lw(3))
    elif emotion == "surprised":
        c.create_arc(*U(-56, -46), *U(-24, -26), start=20, extent=140,
                     outline="#3a2c5e", width=lw(3), style="arc")
        c.create_arc(*U(24, -46), *U(56, -26), start=20, extent=140,
                     outline="#3a2c5e", width=lw(3), style="arc")
    else:
        c.create_arc(*U(-56, -38), *U(-24, -18), start=20, extent=140,
                     outline="#3a2c5e", width=lw(3), style="arc")
        c.create_arc(*U(24, -38), *U(56, -18), start=20, extent=140,
                     outline="#3a2c5e", width=lw(3), style="arc")
    # eyes (blink = closed curves)
    for ex in (-38, 38):
        if emotion == "happy" and not blink:
            c.create_arc(*U(ex - 17, -2), *U(ex + 17, 22), start=15, extent=150,
                         outline="#1a1030", width=lw(4), style="arc")
            continue
        if blink:
            c.create_arc(*U(ex - 17, 2), *U(ex + 17, 26), start=200, extent=140,
                         outline="#1a1030", width=lw(4), style="arc")
            continue
        tall = emotion == "surprised"
        top, bot = (-14 if tall else -10), (40 if tall else 36)
        c.create_oval(*U(ex - 17, top), *U(ex + 17, bot), fill="white",
                      outline="#1a1030", width=lw(2))
        shift = 5 if emotion == "thinking" else 0
        c.create_oval(*U(ex - 11 + shift, -2), *U(ex + 11 + shift, 30), fill="#7c3aed", outline="#4c1d95", width=1)
        c.create_oval(*U(ex - 5 + shift, 6), *U(ex + 5 + shift, 22), fill="#120a2e", outline="")
        c.create_oval(*U(ex - 9 + shift, -6), *U(ex - 1 + shift, 2), fill="white", outline="")
        c.create_oval(*U(ex + 3 + shift, 18), *U(ex + 8 + shift, 23), fill="white", outline="")
        c.create_arc(*U(ex - 19, -14), *U(ex + 19, 16), start=15, extent=150,
                     outline="#1a1030", width=lw(4), style="arc")
    # nose + blush
    nx, ny = U(0, 38)
    c.create_oval(nx - 2 * s, ny - 2 * s, nx + 2 * s, ny + 2 * s, fill="#e8a080", outline="")
    for bx in (-58, 58):
        bx0, by0 = U(bx, 42)
        c.create_oval(bx0 - 10 * s, by0 - 6 * s, bx0 + 10 * s, by0 + 6 * s,
                      fill="#f9a8d4", outline="")
    # mouth (moves while speaking; shape follows emotion)
    if speaking:
        mx0, my0 = U(-10, 50)
        mx1, my1 = U(10, 68)
        c.create_oval(mx0, my0, mx1, my1, fill="#7f1d1d", outline="#450a0a", width=1)
        c.create_oval(mx0, my1 - 8 * s, mx1, my1, fill="#f9a8d4", outline="")
    elif emotion == "happy":
        mx0, my0 = U(-16, 46)
        mx1, my1 = U(16, 70)
        c.create_oval(mx0, my0, mx1, my1, fill="#7f1d1d", outline="#450a0a", width=1)
        c.create_oval(mx0, my1 - 9 * s, mx1, my1, fill="#f9a8d4", outline="")
        c.create_line(mx0, my0, mx1, my0, fill="white", width=lw(3))
    elif emotion == "sad":
        c.create_arc(*U(-13, 56), *U(13, 72), start=25, extent=130,
                     outline="#7f1d1d", width=lw(3), style="arc")
    elif emotion == "thinking":
        c.create_line(*U(-9, 58), *U(9, 58), fill="#7f1d1d", width=lw(3))
    elif emotion == "surprised":
        mx, my = U(0, 58)
        c.create_oval(mx - 7 * s, my - 9 * s, mx + 7 * s, my + 9 * s,
                      fill="#7f1d1d", outline="#450a0a", width=1)
    else:
        c.create_arc(*U(-14, 46), *U(14, 66), start=200, extent=140,
                     outline="#7f1d1d", width=lw(3), style="arc")
