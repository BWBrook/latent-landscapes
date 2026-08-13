# Latent Landscapes Team Briefing

The browser deck is the primary editable presentation. On `wsl-laptop`, run:

```bash
cd /mnt/c/Temp/latent-landscapes-team-briefing-2026-08-13
bash ./start-presentation.sh
```

The launcher serves the folder at `http://localhost:8765/` and opens the
Windows browser. It requires only `python3`, already available in WSL.

Presentation controls:

- use the arrow keys or Space to advance;
- use `F` for full screen, `N` for notes, and `O` for the slide overview;
- the presenter-view button opens a synchronised notes window;
- browser printing produces a 16:9 PDF fallback.

The PowerPoint and pre-rendered PDFs remain as emergency fallbacks and as a
record of the first visual prototype. Presentation content lives in
`index.html`; layout and styling live in `deck.css`; navigation, staged reveals,
notes and timing live in `deck.js`.

The programme-sequence slide uses presentation-local copies of an American mink
image from the U.S. Fish and Wildlife Service and an Australian feral-cat image
from the UNSW Newsroom. They are included for this internal team briefing only.
