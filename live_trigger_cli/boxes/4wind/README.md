# BOX 4wind (Deprecated Local Copy)

`4wind` profile ownership has moved to shared `live_trigger/boxes/4wind/`.

This directory is no longer the active source of truth for the `4wind_base_415` profile.

Current rule:

- update the profile in `live_trigger/boxes/4wind/`
- let `live_trigger_cli` consume the shared profile
- keep this directory only as a migration marker until it can be removed cleanly
