# Goal 034: Latent Landscapes Team Briefing Pack

## Communication Goal

Prepare Barry to brief Natalie Briscoe, Damien Fordham, and Ryo Ogawa on the
Latent Landscapes programme in a 20-minute Teams presentation on 13 August 2026.

By the end, collaborators should understand why the programme moved from a
real-data start to known-truth synthetic experiments, what the current synthetic
laboratory has revealed about identifiability, and how this supports a staged
synthetic, British mink-water vole, and Australian predator-prey paper programme.

## Narrative

Use four acts:

1. the ecological destination and why the project reset;
2. the current synthetic laboratory;
3. what it has taught us about ecological signal, observation, and uncertainty;
4. the paper sequence and questions for collaborators.

Frame the history as progressive diagnosis: a Discovery-proposal concept led to
an initial mink-water vole implementation; real-data failures were difficult to
diagnose because process, observation, model structure, and parameter truth were
all uncertain; the first known-truth synthetic landscape was understandable but
too simple to be sufficiently informative; the richer Python system was built to
separate these problems systematically.

The central take-away is:

> Identifiability depends jointly on ecological signal, observation design, and
> correctly calibrated uncertainty; it is not an intrinsic property of a
> parameter alone.

## Deliverables

Create under `docs/presentations/2026-08-13-team-briefing/`:

- a browser-native, offline-capable presentation as the primary editable
  artefact;
- keyboard navigation, staged reveals, slide overview, full-screen display and
  a synchronised presenter-notes view;
- PowerPoint and PDF fallbacks;
- concise slide-by-slide talk tracks and indicative timing;
- presentation-specific raster assets only where required for reliable display.

Aim for approximately 11 slides and 18-22 minutes. Keep visible slide copy
ecologically legible and avoid goal identifiers, implementation terminology,
and dense statistical tables unless essential to the argument.

## Evidence And Boundaries

Use accepted Latent Landscapes artifacts and repo-local programme documentation.
Read `/Users/bwbrook/papers/spatext` only to select and reproduce one or two
legacy `synth-small` visuals or factual context; do not modify it or create a
runtime dependency on it.

Do not run new simulations, alter scientific claims, add literature-derived
claims requiring a review tranche, or assert exact island mink-water vole
contrasts without verification. Mention islands only as potential natural
contrasts unless their status is verified separately.

## Acceptance

- the deck opens with the ecological destination rather than repository history;
- no more than two slides cover the earlier work and reset;
- the current landscape, sampling design, spread/resistance lessons, prey layer,
  and Goal 032-033 calibration lesson are visually represented;
- observations, inferences, and future proposals remain distinguishable;
- the three-paper trajectory is explicit;
- the close poses three to five useful scientific questions to collaborators;
- all slides render without unintended overlap, clipping, or illegible text;
- speaker notes support an 18-22 minute delivery;
- the browser deck, PowerPoint and PDF fallbacks open successfully.

Perform one focused visual and narrative review pass. Stop for Barry's review
when the first coherent, presentation-ready version is complete; do not pursue
minor stylistic perfection.

Barry approved preparation after the narrative discussion on 12 August 2026.

## Outcome

The first presentation-ready review tranche is complete. The primary artefact
is now an offline-capable 11-slide browser deck under
`docs/presentations/2026-08-13-team-briefing/`, with keyboard navigation,
staged reveals, slide overview, full-screen display, embedded talk tracks and a
synchronised presenter-notes view. The earlier PowerPoint, 11-page PDF and
four-page speaker-notes PDF remain as fallbacks and as a record of the initial
visual prototype.

The deck follows the approved four-part narrative, uses two slides for project
history, makes the current access-constrained landscape and observation process
visible, translates the resistance, spread-detection, prey-effect, and
parameter-specific calibration results into ecological language, states the
remaining limits, and closes with the three-paper sequence and five questions
for collaborators.

Barry's slide-by-slide review on 13 August prompted one consolidated audience-
facing revision. Internal "Act" labels and an engineering mantra were removed;
headlines were made direct; the observation-window message was clarified; the
resistance, prey-effect, and uncertainty slides were rebuilt around explicit
definitions, known generating values, natural denominators, and plain-language
interpretations; the positive scientific achievements were restored to the
synthesis; study-system images now anchor the paper sequence; and the final
discussion questions were replaced. These changes alter presentation and talk
track only, not the accepted scientific evidence.

The browser correction was made after Barry identified that the agreed flexible
delivery medium had been inadvertently superseded by a conventional slide-deck
default. The browser deck uses the accepted PowerPoint as its content and visual
prototype rather than changing the science. No new simulation, scientific
retuning, or island-status claim was introduced. The pack was used successfully
for the collaborator presentation on 13 August 2026. Barry then approved
committing and publishing the accepted briefing pack to the private repository
so that incoming collaborators can inspect it.

For presentation-machine portability, the complete static folder and a ZIP with
the same root name were copied to `wsl-laptop` under `/mnt/c/Temp/`. The ZIP
checksum matched across machines, its contents tested cleanly, and the unpacked
folder passed a local HTTP smoke check in WSL. The included launcher requires
only WSL's existing `python3` and opens the deck through `localhost` in the
Windows browser.

The earlier one-off PowerPoint generator was discarded at closeout because it
contained superseded prototype copy and was not required to run or edit the
accepted browser deck. The browser source, portable launcher, presentation
assets, and binary fallbacks form the durable review surface.
