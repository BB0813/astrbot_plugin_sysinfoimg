# Feature Roadmap

## Positioning

The plugin already covers four main flows: dashboard rendering, AstrBot runtime stats, scheduled delivery, and diagnostics.
The next iterations focus on turning it from a display plugin into a lightweight monitoring plugin.

## Phases

### Phase 1 - Active Alerts (V2.6.x)

Status: first version delivered

- Add `/sysinfo_alert <minutes>` for threshold-based polling.
- Add `/sysinfo_alert status` for the current session.
- Add `/sysinfo_alert off` to disable alerts for the current session.
- Add CPU / memory / disk / swap thresholds.
- Add cooldown, recovery notice, and optional image attachment.
- Reuse the existing scheduler and rendering pipeline instead of adding a second delivery path.

Acceptance criteria:
- Per-session alert enable / disable works.
- Alerts are sent automatically after thresholds are exceeded.
- Recovery messages can be sent when metrics return to normal.
- The feature does not conflict with `/sysinfo_auto`.

### Phase 2 - System History Trends (V2.7.x)

Status: first version delivered

- Add lightweight local history sampling.
- Add 1h / 24h trends for CPU, memory, network, and disk overview.
- Add a history output mode such as `/sysinfo_history` or a dashboard switch.
- Add recent fluctuation context to alert messages.

### Phase 3 - Deep Host Metrics (V2.8.x)

Status: completed in V2.8.1

- Add GPU, temperature, battery, and container metrics where available.
- Detect Linux / Windows capabilities and degrade gracefully.
- Extend alerts to GPU, temperature, battery, and stopped container scenarios.
- Add host probe diagnostics for capability / source troubleshooting.
- Decouple deep host probing from card visibility so alerts and diagnostics stay accurate.

### Phase 4 - Profiles and Layout Presets (V2.9.x)

Status: planned

- Add named profiles for chat, personal, and lightweight views.
- Add horizontal, compact, system-only, and AstrBot-only layouts.
- Add more scene-oriented output modes.

### Phase 5 - Visual Config Page (V3.0.x)

Status: planned

- Add an AstrBot Plugin Page for live preview.
- Preview theme, background, colors, and layout in real time.
- Export a recommended config from the preview page.

## Principles

- Add active monitoring features before visual extras.
- Extend compatibly without breaking the current command system.
- Reuse scheduler, config merge, and rendering paths first.
- Keep new features optional by default.
