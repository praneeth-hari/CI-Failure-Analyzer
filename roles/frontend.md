# Role: Frontend and UI for AI products

Read this for LLM chat interfaces, metrics dashboards, demos (Streamlit, Gradio, React), accessibility, and visual design. Rules in `AGENTS.md` always apply.

## 0. First decision: is there a design system?

1. If the project already has a design system, component library, or style guide: **use it and stop here for visual choices.** Match existing tokens, components and patterns. Consistency beats novelty.
2. If it is a quick internal demo: use the framework defaults (Streamlit, Gradio, shadcn/ui) with minimal changes. Don't over-design.
3. If it is new or branded and design quality matters: use Part B and the extra skills listed in `INSTALL.md`.

The user's brief always wins over the style suggestions below.

---

## Part A. UI patterns for AI products

### Choosing a tool
| Need | Use |
|---|---|
| Fast internal demo, data-science audience | Streamlit or Gradio |
| Product UI, custom interactions | React (Next.js or Vite) with the project's component library |
| Metrics and eval dashboards | Streamlit, Grafana, or a small React page with a charting library |

### Chat interface checklist
- **Streaming:** show tokens as they arrive; render markdown incrementally without layout jumps; auto-scroll only when the user is at the bottom.
- **Stop button:** visible during generation; cancels the request server side.
- **States:** empty (suggested prompts), loading (typing indicator or skeleton), streaming, complete, error (plain message with a retry), offline, rate-limited.
- **Retry / regenerate / edit last message,** copy button on answers and code blocks.
- **RAG citations:** numbered references that open the source passage; show which document, page and date; make it clear when an answer has no source.
- **Uncertainty and honesty:** label that output is AI generated; show when the system could not find an answer; don't present guesses as facts.
- **Feedback:** thumbs up/down with an optional reason, stored with the request id.
- **Long content:** collapse long sources, support wide tables and code with horizontal scroll, keep copy working.
- **Tool/agent activity:** show what the agent is doing ("searching documents...") and ask for approval before irreversible actions, with a clear summary of what will happen.
- **History:** conversations list, rename, delete; make deletion actually delete.
- **Privacy:** don't send or store more than needed; show when data leaves the user's environment.

### Dashboards
- Start with the question each chart answers. Title states the finding or the metric with its unit.
- Show sample sizes and time ranges. Compare against a baseline or target.
- For ML/LLM monitoring show: quality score, latency p50/p95, error rate, cost, drift, and volume.
- Don't use pie charts for many categories or 3D effects. Use consistent colors for the same thing across charts.
- Colorblind-safe palettes; never encode meaning with color alone.

### Accessibility (WCAG 2.2 AA checklist)
- [ ] Text contrast at least 4.5:1 (3:1 for large text and UI components)
- [ ] Everything works with the keyboard; visible focus ring; logical tab order
- [ ] Semantic HTML (buttons are buttons, headings in order); labels on all inputs
- [ ] Alt text for meaningful images; decorative images empty alt
- [ ] Streaming text announced politely to screen readers (`aria-live="polite"`) without flooding
- [ ] Touch targets at least 24x24 CSS px (prefer 44x44 on mobile)
- [ ] Respect `prefers-reduced-motion` and `prefers-color-scheme`
- [ ] Errors explained in text and tied to the field
- [ ] Zoom to 200% and a 320px-wide screen without losing content
- [ ] Test with a screen reader at least once for the main flow

---

## Part B. Design quality (for new or branded work)

### Before coding
1. **Read the brief.** Purpose, audience, tone, constraints (brand, device, language, performance).
2. **Choose one clear direction** (for example calm and clinical, dense and technical, warm and editorial) and commit to it. A distinct direction is better than a blend.
3. **Write design tokens first,** as CSS variables or a theme file:
   - **Color:** 4 to 6 named colors with hex values (background, surface, text, muted text, primary accent, danger), checked for contrast. Add a dark variant if needed.
   - **Type roles:** display, heading, body, small, mono; font families, sizes, weights, line heights. Limit to two families.
   - **Spacing scale:** a base unit (4 or 8 px) and a fixed set of steps.
   - **Radius, borders, shadows,** and a small set of motion durations and easing curves.
4. **Sketch the layout** as an ASCII wireframe for each main screen and breakpoint:

```
+--------------------------------------------+
| Logo        Search........        [Account]|
+---------+----------------------------------+
| Nav     |  Title                           |
|  - Chat |  +----------------------------+  |
|  - Docs |  | Message stream             |  |
|  - Eval |  +----------------------------+  |
|         |  [ Input ........... ] [Send]    |
+---------+----------------------------------+
```

5. **Review the plan against the brief** before writing code: does each screen serve the purpose, are all states covered, is anything missing or extra? Fix the plan, then build.

### Avoid generic "AI look" defaults
Unless the brief asks for them, avoid: purple-to-blue gradients on white, default system fonts everywhere, identical rounded cards in a grid, glowing orbs, emoji as icons, centered hero with three feature boxes, and placeholder lorem ipsum. Choose type, color and layout on purpose, and make real content.

### Motion (use sparingly, with purpose)
- Motion explains change (where something came from or went) or gives feedback. If it does neither, remove it.
- Prefer spring or ease-out curves for things responding to input; short durations (about 150 to 300 ms) for UI feedback.
- Make animations **interruptible:** a new input mid-animation continues smoothly from the current position and velocity instead of snapping.
- Hand off gesture velocity to the animation (a flicked sheet continues in that direction).
- Animate transform and opacity, not layout properties.
- Honor `prefers-reduced-motion` by replacing movement with simple fades or none.

### Mobile and polish
- Design for narrow screens first; thumb-reachable primary actions; safe-area insets; input fields at 16px or larger to avoid zoom on iOS.
- Handle the on-screen keyboard (chat input stays visible).
- Real hover, active, focus, disabled and loading states for every control.
- Loading skeletons that match final layout; avoid layout shift.
- Empty states that explain what to do next.

### Stress test your UI (break it before users do)
Try: very long words and names, 10,000-character messages, empty and one-item lists, 1,000-item lists, slow network, offline, double-click submit, rapid resize, right-to-left text, emoji, browser zoom, window narrower than 320px, JavaScript error in one component, API returning an unexpected shape. Fix what breaks.

### UI copy
- Say what happens, in plain words: "Couldn't reach the server. Retry" rather than "Error 500".
- Buttons are verbs: "Save changes", "Send".
- No blame, no jokes in error messages, no jargon the audience doesn't use.
- Keep AI disclosures short and honest: "AI-generated. Check important facts."
- Consistent terms: pick one word for each concept and keep it.

---

## Part C. Build quality

- Components small and typed (TypeScript); state close to where it is used; server state through a data-fetching library.
- Never put API keys in frontend code; call your backend.
- Escape or sanitize rendered model output (markdown/HTML) to prevent script injection; render links with `rel="noopener noreferrer"`.
- Test key flows with Playwright; add a few visual checks at mobile and desktop widths.
- Check performance basics: bundle size, image sizes, lazy loading, no blocking requests.
- Verify in a real browser before saying it works: run the app, take a screenshot at desktop and mobile widths, and use the app once with the keyboard only.

## Extra skills (optional, see `INSTALL.md`)
- Emil Kowalski's skills (apple-design for motion, break-ui for stress testing, mobile-native for mobile feel)
- `frontend-design` (creative direction for distinctive UI)
- Addy Osmani's `frontend-ui-engineering`

## Output checklist for a UI task
- [ ] Design system followed, or tokens defined first
- [ ] All states covered (empty, loading, streaming, error, success)
- [ ] Accessibility checklist passed for the main flow
- [ ] Works at mobile and desktop widths
- [ ] Model output sanitized
- [ ] Opened and used in a browser, with evidence (screenshot or test output)
