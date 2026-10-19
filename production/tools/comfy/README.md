# Watching and learning ComfyUI

ComfyUI runs on this machine at **http://127.0.0.1:8188** while plates render. Open it in any browser here.

- **See what's rendering:** the queue panel (the list icon on the left) shows every job, including the ones the render
  script sends, with a progress bar and the finished images.
- **See the exact graph behind any plate:** drag any PNG from `media/plates/` onto the canvas. Every image carries the
  graph that made it (box for box, with its seed), and ComfyUI rebuilds it.
- **A guided version:** Workflow → Open → `production/tools/comfy/claudia-plate-annotated.json`. The same graph, with
  each box titled by its job and four notes explaining the flow. Press Run to make the same image again, or change the
  seed in box 7 for a sibling.

Don't press Run while a batch is rendering unless you're happy to wait: jobs queue one at a time on the one GPU.
