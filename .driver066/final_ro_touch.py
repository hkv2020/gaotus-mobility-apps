from pathlib import Path
import re

root = Path('driver')
loc = root / 'lib/core/localization.dart'
s = loc.read_text()

# Ensure the final visible strings have Romanian translations.
entries = {
    'Could not accept job.': 'Comanda nu a putut fi acceptată.',
    'Could not decline job.': 'Comanda nu a putut fi refuzată.',
    'You’re online': 'Ești online',
    'You’re offline': 'Ești offline',
    'You’re ready to receive nearby jobs.': 'Ești gata să primești comenzi din apropiere.',
    'Ready to drive? Go online to receive jobs.': 'Ești gata de drum? Intră online pentru a primi comenzi.',
    'Gross': 'Brut',
    'Your share': 'Partea ta',
    'Company': 'Companie',
    'Current period': 'Perioada curentă',
    'Platform': 'Platformă',
    'Push available': 'Push disponibil',
    'Push registered': 'Push înregistrat',
    'Server configured': 'Server configurat',
    'Address unavailable': 'Adresă indisponibilă',
    'Customer fare': 'Tarif client',
}
needle = '\n  };\n  static String t('
missing=[]
for key,value in entries.items():
    if f"'{key}':" not in s and f'"{key}":' not in s:
        escaped_key=key.replace("'", "\\'")
        escaped_val=value.replace("'", "\\'")
        missing.append(f"    '{escaped_key}': '{escaped_val}',")
if missing:
    s=s.replace(needle, '\n'+'\n'.join(missing)+needle, 1)
loc.write_text(s)

# Home/availability status.
p=root/'lib/screens/driver_home_screen.dart'
s=p.read_text()
s=s.replace("widget.session.errorMessage ?? 'Could not accept job.'", "widget.session.errorMessage ?? 'Could not accept job.'.tr")
s=s.replace("widget.session.errorMessage ?? 'Could not decline job.'", "widget.session.errorMessage ?? 'Could not decline job.'.tr")
s=s.replace("online ? 'You’re online' : 'You’re offline'", "online ? 'You’re online'.tr : 'You’re offline'.tr")
s=s.replace("? (currentJob != null ? 'You have an active ${currentJob.isRide ? 'ride' : currentJob.jobTypeLabel.toLowerCase()}.' : 'You’re ready to receive nearby jobs.')\n                : 'Ready to drive? Go online to receive jobs.'", "? (currentJob != null ? (AppLocalization.isRomanian ? 'Ai o comandă activă: ${currentJob.jobTypeLabel.tr.toLowerCase()}.' : 'You have an active ${currentJob.isRide ? 'ride' : currentJob.jobTypeLabel.toLowerCase()}.') : 'You’re ready to receive nearby jobs.'.tr)\n                : 'Ready to drive? Go online to receive jobs.'.tr")
p.write_text(s)

# Earnings labels and empty route fallback.
p=root/'lib/screens/earnings_screen.dart'
s=p.read_text()
s=s.replace("label: 'Gross'", "label: 'Gross'.tr")
s=s.replace("label: 'Your share'", "label: 'Your share'.tr")
s=s.replace("label: 'Company'", "label: 'Company'.tr")
s=s.replace("return 'Current period';", "return 'Current period'.tr;")
s=s.replace("value.isEmpty ? 'Address unavailable' : value", "value.isEmpty ? 'Address unavailable'.tr : value")
p.write_text(s)

# Diagnostics: translate generic labels/statuses while keeping GPS/Realtime product terms.
p=root/'lib/screens/driver_menu_screen.dart'
s=p.read_text()
s=s.replace("_ConnectionLine(label: 'Platform',", "_ConnectionLine(label: 'Platform'.tr,")
s=s.replace("_ConnectionLine(label: 'Push available',", "_ConnectionLine(label: 'Push available'.tr,")
s=s.replace("_ConnectionLine(label: 'Push registered',", "_ConnectionLine(label: 'Push registered'.tr,")
s=s.replace("_ConnectionLine(label: 'Server configured',", "_ConnectionLine(label: 'Server configured'.tr,")
s=s.replace("session.gpsRunning ? 'Active' : 'Stopped'", "session.gpsRunning ? 'Active'.tr : 'Stopped'.tr")
p.write_text(s)

# Offer card: translate type badge and all dynamic counters.
p=root/'lib/widgets/offer_card.dart'
s=p.read_text()
s=s.replace("Text(job.jobTypeLabel.toUpperCase(),", "Text(job.jobTypeLabel.tr.toUpperCase(),")
s=s.replace("Text('$seconds sec',", "Text(AppLocalization.isRomanian ? '$seconds sec' : '$seconds sec',")
s=s.replace("label: '${job.passengers} passenger${job.passengers == 1 ? '' : 's'}'", "label: AppLocalization.isRomanian ? '${job.passengers} ${job.passengers == 1 ? 'pasager' : 'pasageri'}' : '${job.passengers} passenger${job.passengers == 1 ? '' : 's'}'")
s=s.replace("label: '${job.operationsSummary.total} stop${job.operationsSummary.total == 1 ? '' : 's'}'", "label: AppLocalization.isRomanian ? '${job.operationsSummary.total} ${job.operationsSummary.total == 1 ? 'oprire' : 'opriri'}' : '${job.operationsSummary.total} stop${job.operationsSummary.total == 1 ? '' : 's'}'")
s=s.replace("title: job.isRide ? 'Pick-up' : 'Start'.tr", "title: job.isRide ? 'Pick-up'.tr : 'Start'.tr")
s=s.replace("label: '${offer.distanceKm!.toStringAsFixed(1)} km to pick-up'", "label: AppLocalization.isRomanian ? '${offer.distanceKm!.toStringAsFixed(1)} km până la preluare' : '${offer.distanceKm!.toStringAsFixed(1)} km to pick-up'")
p.write_text(s)

# Operations: translate type badges, route summary and parcel counters.
p=root/'lib/screens/operations_job_screen.dart'
s=p.read_text()
s=s.replace("Text(job.jobTypeLabel.toUpperCase(),", "Text(job.jobTypeLabel.tr.toUpperCase(),")
s=s.replace("'${summary.pending + summary.active} remaining · ${summary.failed} failed · ${summary.postponed} postponed'", "AppLocalization.isRomanian ? '${summary.pending + summary.active} rămase · ${summary.failed} eșuate · ${summary.postponed} amânate' : '${summary.pending + summary.active} remaining · ${summary.failed} failed · ${summary.postponed} postponed'")
s=s.replace("_Chip(text: '${stop.packageCount} package${stop.packageCount == 1 ? '' : 's'}')", "_Chip(text: AppLocalization.isRomanian ? '${stop.packageCount} ${stop.packageCount == 1 ? 'colet' : 'colete'}' : '${stop.packageCount} package${stop.packageCount == 1 ? '' : 's'}')")
p.write_text(s)

print('Driver final Romanian dynamic-label touch applied')
