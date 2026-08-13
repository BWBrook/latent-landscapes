const slides = [...document.querySelectorAll(".slide")];
const counter = document.querySelector("#slide-counter");
const progress = document.querySelector("#progress-fill");
const notesPanel = document.querySelector("#notes-panel");
const startTime = Date.now();
let current = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));
const revealCounts = new Array(slides.length).fill(0);
const channel = "BroadcastChannel" in window ? new BroadcastChannel("latent-landscapes-team-briefing") : null;

const notes = [
  {
    time: "0:45",
    copy: "Open with the ecological destination. This is not a presentation about building a better optimiser for its own sake. The long-term question is whether we can attribute spatial predator spread and prey decline from imperfect observations. The programme is deliberately staged: first a synthetic paper where truth is known, then a constrained mink–water vole application, and finally the harder Australian murid–cat problem that motivated the grant.",
    sources: ["docs/programme.md", "Project-history discussion, 12 August 2026"],
  },
  {
    time: "1:50",
    copy: "Give only the short history. The Discovery proposal contained a plausible conceptual model, but not yet a tested inferential system. We began with mink and water voles. When estimation failed, we could not tell whether the cause was the biological model, observation process, insufficient data, or inference machinery. That prompted a known-truth synthetic case. The first was useful but too simple. Latent Landscapes is the rebuild: controlled experiments in which each complication has a diagnostic purpose.",
    sources: ["docs/programme.md", "docs/provenance.md", "Project-history discussion, 12 August 2026"],
  },
  {
    time: "1:30",
    copy: "Use the pictures. Habitat was essentially two smooth patches and the predator wave was close to a simple gradient across a small grid. That made it easy to understand, but different mechanisms could produce very similar observable patterns. We learned about response reconstruction and observation support, but the system was too small and geometrically regular to teach us enough about spatial identifiability.",
    sources: ["Legacy SpatExt synth-small suitability and driver-arrival artefacts", "docs/provenance.md"],
  },
  {
    time: "2:00",
    copy: "Orient the group ecologically. This is a deterministic procedural landscape, not an image selected by eye. Explicit geometric rules place aggregated water bodies, six quality patches, five connecting corridors and three western source zones; fixed values make the result exactly reproducible. Blue is impassable water. Grey matrix is poor but passable. Orange corridors are high-conductance movement strips. The light road columns and transect rows form the fixed access network. Sampling centres are selected from that network, balanced across four distance-from-source strata, with eight clusters frozen as holdout. They are deliberately not habitat-targeted, giving us a clear first access-biased design that can later become more realistic.",
    sources: ["artifacts/goal001_deterministic_spread/visuals/landscape_design.svg", "src/latent_landscapes/goal001/design.py", "src/latent_landscapes/goal001/spread.py"],
  },
  {
    time: "2:00",
    copy: "Talk through the encoding explicitly. On the left, background colour is known arrival time; circle size and fill redundantly encode the same total detection count. On the right, circle colour is first detection time; purple, shown as day 120, means never detected; red outlines mark holdout sites. Surveys ran from day 10 to day 110, while the known invasion continued beyond day 200. Of the 27 sites never detected, 25 had not yet been reached when surveying stopped; two were reached but missed. The visible truncation therefore combines the survey window with imperfect detection.",
    sources: ["artifacts/goal001_deterministic_spread/visuals/spread_observations.svg", "src/latent_landscapes/goal001/artifacts.py"],
  },
  {
    time: "2:30",
    copy: "Define the experiment before interpreting it. Resistance is movement cost through passable habitat. Eta controls its contrast: zero makes all passable habitat equivalent; one retains the designed patch, corridor and matrix differences. Each row summarizes 250 independent repeats of the whole synthetic survey at a known generating value. At eta 0.50, only 166 repeats clearly excluded uniform movement; at eta 0.75 and 1.00, all 250 did. In the second panel, p is the chance of detecting a predator during one visit after arrival. Spread rate itself was recovered at all three speeds, but slower waves produced less informative change within the survey window, widening the typical p interval from the accepted 0.20 to 0.24 or 0.26.",
    sources: ["artifacts/goal024_resistance_contrast_transition_benchmark", "artifacts/goal025_spread_detection_transition_benchmark"],
  },
  {
    time: "2:00",
    copy: "Define the prey-effect multiplier as local prey-extirpation risk after predator arrival divided by the background risk; one means no predator effect. With arrival known and prey observed perfectly, a twofold effect remained frequently ambiguous, a threefold effect was reliably detected but slightly imprecise, and a fivefold effect passed every recovery criterion. We then made observation progressively harder: first imperfect prey detection, then hidden arrival dates inferred from imperfect predator detections. The fivefold effect remained recovered. This is a conditional positive control for one strong effect under this design, rather than a general claim that prey responses are easy to infer.",
    sources: ["artifacts/goal028_known_arrival_prey_effect_strength_transition", "artifacts/goal029_known_arrival_known_imperfect_prey_detection", "artifacts/goal031_latent_arrival_prey_effect_positive_control"],
  },
  {
    time: "2:30",
    copy: "Set up the known-truth check plainly. We generated data with spread rate 1.0 and a fivefold prey effect, hid both values, and estimated both from imperfect observations in 1,000 independent repeats. Typical best estimates returned to 1.0 and fivefold. The first uncertainty calculation used one envelope required to cover both parameters simultaneously. Variation among entire invasion waves made that envelope very broad, so only 130 of 1,000 excluded no prey effect. Separate calibrated intervals for spread and prey effect answered a narrower question: all 1,000 prey intervals excluded no effect and their typical width was approximately twofold. This diagnoses an overly blunt joint uncertainty calculation; it does not yet solve simultaneous coverage of both parameters.",
    sources: ["artifacts/goal032_joint_spread_rate_prey_effect_positive_control/summary.json", "artifacts/goal033_parameter_specific_uncertainty_calibration/summary.json"],
  },
  {
    time: "1:45",
    copy: "This is the positive synthesis. We recovered spread rate at all three tested wave speeds, reliably detected resistance from eta 0.75 upward, and recovered a fivefold prey effect despite imperfect detection and hidden arrival dates. The process models also beat fitted neutral baselines on held-out sites. Known truth then let us distinguish genuine weak signal from limitations caused by the survey window or the uncertainty calculation. We now have a working end-to-end laboratory as well as clearly located information boundaries.",
    sources: ["Synthesis of accepted Goal 024–033 evidence", "docs/programme.md"],
  },
  {
    time: "1:45",
    copy: "Paper 1 is a substantive synthetic methodology paper. It should reach the indirect prey-response layer and test whether the lessons generalise across a small set of additional landscapes or generating models. Paper 2 applies the resulting workflow to mink and water voles across Great Britain. Islands may provide useful contrasts, but avoid asserting exact species combinations here. Paper 3 tackles the grant endpoint: Australian murids under cat and perhaps fox invasion. The study systems become more complex as our ability to model and infer from sparse data develops.",
    sources: ["docs/programme.md", "Programme and paper-sequence discussion, 12 August 2026", "American mink image: U.S. Fish and Wildlife Service", "Australian feral-cat image: UNSW Newsroom"],
  },
  {
    time: "1:30",
    copy: "Stop presenting and invite reactions rather than answering the questions yourself. Begin with which result mattered or surprised them, then ask whether the synthetic-only paper feels substantial and what evidence it needs. Use the ecological-credibility and generality questions to expose blind spots without opening an unlimited simulation programme. Finish by asking which constraints from the British and Australian systems should inform the next synthetic design. The discussion can run beyond twenty minutes without adding more presentation content.",
    sources: ["Questions derived from docs/programme.md and the supervisor–research fellow discussion"],
  },
];

slides.forEach((slide, index) => slide.dataset.slideNumber = String(index + 1).padStart(2, "0"));

function revealsFor(index) {
  return [...slides[index].querySelectorAll(".reveal")];
}

function applyRevealState(index) {
  revealsFor(index).forEach((item, itemIndex) => item.classList.toggle("is-shown", itemIndex < revealCounts[index]));
}

function updateNotes() {
  const note = notes[current];
  document.querySelector("#notes-slide-number").textContent = String(current + 1).padStart(2, "0");
  document.querySelector("#notes-title").textContent = slides[current].dataset.title;
  document.querySelector("#target-time").textContent = note.time;
  document.querySelector("#notes-copy").textContent = note.copy;
  const list = document.querySelector("#notes-sources");
  list.replaceChildren(...note.sources.map((source) => Object.assign(document.createElement("li"), { textContent: source })));
}

function showSlide(index, { broadcast = true } = {}) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides.forEach((slide, slideIndex) => slide.classList.toggle("is-active", slideIndex === current));
  applyRevealState(current);
  counter.textContent = `${current + 1} / ${slides.length}`;
  progress.style.width = `${((current + 1) / slides.length) * 100}%`;
  history.replaceState(null, "", `#${current + 1}`);
  updateNotes();
  if (broadcast) channel?.postMessage({ type: "state", current, reveal: revealCounts[current] });
}

function forward() {
  const items = revealsFor(current);
  if (revealCounts[current] < items.length) {
    revealCounts[current] += 1;
    applyRevealState(current);
    channel?.postMessage({ type: "state", current, reveal: revealCounts[current] });
    return;
  }
  showSlide(current + 1);
}

function backward() {
  if (revealCounts[current] > 0) {
    revealCounts[current] -= 1;
    applyRevealState(current);
    channel?.postMessage({ type: "state", current, reveal: revealCounts[current] });
    return;
  }
  showSlide(current - 1);
}

function toggleOverview() {
  document.body.classList.toggle("is-overview");
}

function toggleNotes() {
  document.body.classList.toggle("notes-open");
}

document.querySelector("#prev").addEventListener("click", backward);
document.querySelector("#next").addEventListener("click", forward);
document.querySelector("#overview").addEventListener("click", toggleOverview);
document.querySelector("#notes").addEventListener("click", toggleNotes);
document.querySelector("#fullscreen").addEventListener("click", () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen());
document.querySelector("#presenter").addEventListener("click", () => window.open(`${location.pathname}?presenter=1#${current + 1}`, "latent-landscapes-presenter", "width=1500,height=900"));

slides.forEach((slide, index) => slide.addEventListener("click", () => {
  if (!document.body.classList.contains("is-overview")) return;
  document.body.classList.remove("is-overview");
  showSlide(index);
}));

document.addEventListener("keydown", (event) => {
  if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) { event.preventDefault(); forward(); }
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) { event.preventDefault(); backward(); }
  if (event.key.toLowerCase() === "o") toggleOverview();
  if (event.key.toLowerCase() === "n") toggleNotes();
  if (event.key.toLowerCase() === "f") document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  if (event.key === "Home") showSlide(0);
  if (event.key === "End") showSlide(slides.length - 1);
});

window.addEventListener("hashchange", () => {
  const requested = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));
  if (requested !== current) showSlide(requested, { broadcast: false });
});

channel?.addEventListener("message", ({ data }) => {
  if (data?.type !== "state") return;
  revealCounts[data.current] = data.reveal;
  showSlide(data.current, { broadcast: false });
});

if (new URLSearchParams(location.search).get("presenter") === "1") {
  document.body.classList.add("presenter");
  notesPanel.setAttribute("aria-hidden", "false");
}

setInterval(() => {
  const seconds = Math.floor((Date.now() - startTime) / 1000);
  document.querySelector("#elapsed").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}, 1000);

showSlide(current, { broadcast: false });
