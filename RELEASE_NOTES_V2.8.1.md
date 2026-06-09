# V2.8.1 Release Notes

## Summary

V2.8.1 completes the second delivery slice of Phase 3.
This release moves deep host metrics from "visible when available" to "monitorable, diagnosable, and explainable" while keeping the existing `/sysinfo`, `/sysinfo_alert`, `/sysinfo_history`, and `/sysinfo_stats_diag` flows compatible.

## Added

- Add `/sysinfo_host_diag` to inspect host probe results, data sources, and active config
- Add `alert_battery_percent` for battery-threshold alerts while discharging
- Add `alert_container_stopped` for stopped-container count alerts
- Add stopped-container counts, state summaries, and stopped-name samples to container metrics
- Mark stopped containers in the container card and `deep_host` detail panel

## Fixed and Improved

- Decouple deep host probing from card visibility so hidden cards no longer break alerts or diagnostics
- Let alert sampling enable the required deep host probes automatically when related thresholds are configured
- Keep history sampling aligned with deep host probe conditions so GPU / temperature alert context remains valid
- Keep host capability summaries accurate even when individual deep host cards are hidden

## Related Config

- `enable_deep_host_metrics`
- `alert_gpu_percent`
- `alert_temperature_c`
- `alert_battery_percent`
- `alert_container_stopped`
- `bottom_right_panel=deep_host`

## Artifacts

- WebUI upload package: `dist/sysinfoimg_V2.8.1_astrbot_upload.zip`
- Manual install package: `dist/sysinfoimg_V2.8.1_manual_folder.zip`

## Suggested Checks

- Run `/sysinfo` and confirm the dashboard still renders correctly
- Run `/sysinfo_host_diag` and confirm probe sources and statuses are returned
- Run `/sysinfo_alert status` and confirm the new thresholds appear in the payload
- Run `/sysinfo_history 24` and confirm GPU / temperature trends still render when available
