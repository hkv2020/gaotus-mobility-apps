# Gaotus Mobility Driver v0.6.0 — Connected Driver Hub

Additive upgrade over Driver v0.5.9 Unified Operations.

Connected Platform areas:
- Help: operator phone, WhatsApp, email and help URL from Gaotus Mobility Platform.
- Safety: operator safety contact, configurable emergency number and active job context.
- Settings: Platform-synced navigation provider, haptics, in-app job sound and chat sound.
- Vehicle: assigned vehicle information and compliance status.
- Documents: live driver + vehicle compliance statuses, expiry dates and permitted document links.
- Profile: current driver contact/licence details from Platform.

Unified job behaviour remains intact for Ride, Delivery, Collection and Multi-stop. Existing FCM channel IDs remain unchanged. Notification wording is generalized from passenger-only to unified jobs.

Requires Gaotus Mobility Platform v1.4.2+ for the connected hub endpoints. Older Platform versions keep core ride/delivery jobs working, but connected hub screens will show Platform data unavailable until upgraded.
