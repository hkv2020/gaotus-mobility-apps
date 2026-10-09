from pathlib import Path
import shutil

root = Path('driver')
assets = Path('.driver059')

def replace_one(rel, old, new, label):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {rel}')
    p.write_text(s.replace(old, new, 1))

for src, rel in [
    ('booking.dart', 'lib/models/booking.dart'),
    ('operation_stop.dart', 'lib/models/operation_stop.dart'),
    ('operations_job_screen.dart', 'lib/screens/operations_job_screen.dart'),
]:
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(assets / src, dst)

replace_one('pubspec.yaml', 'version: 0.5.8+13', 'version: 0.5.9+14', 'version')
replace_one('pubspec.yaml', '  latlong2: ^0.9.1\n', '  latlong2: ^0.9.1\n  image_picker: ^1.2.0\n', 'image picker dependency')
replace_one('lib/config/app_config.dart', "static const String version = '0.5.8';", "static const String version = '0.5.9';", 'app version')

replace_one(
    'lib/core/api_client.dart',
    "  Future<Map<String, dynamic>> earnings({String period = 'today'}) =>\n",
    """  Future<Map<String, dynamic>> operationsJob(int bookingId) =>
      _request('GET', '/operations/jobs/$bookingId');

  Future<Map<String, dynamic>> operationStops(int bookingId) =>
      _request('GET', '/operations/jobs/$bookingId/stops');

  Future<Map<String, dynamic>> updateOperationStopStatus(
    int bookingId,
    int stopId,
    String status, {
    Map<String, Object?> proof = const <String, Object?>{},
  }) =>
      _request(
        'POST',
        '/operations/jobs/$bookingId/stops/$stopId/status',
        body: <String, Object?>{'status': status, if (proof.isNotEmpty) 'proof': proof},
      );

  Future<Map<String, dynamic>> earnings({String period = 'today'}) =>
""",
    'operations API methods',
)

replace_one(
    'lib/state/app_session.dart',
    "    } else if (currentJob!.id != previousId || currentJob!.status == 'pob') {\n      unawaited(loadTripExtras(silent: true));\n",
    "    } else if (currentJob!.isRide && (currentJob!.id != previousId || currentJob!.status == 'pob')) {\n      unawaited(loadTripExtras(silent: true));\n",
    'ride extras guard',
)
replace_one(
    'lib/state/app_session.dart',
    "  Future<void> loadTripExtras({bool silent = false}) async {\n",
    """  Future<void> updateOperationStopStatus(
    int stopId,
    String status, {
    Map<String, Object?> proof = const <String, Object?>{},
  }) async {
    final api = _api;
    final job = currentJob;
    if (api == null || job == null || !job.isOperations) return;
    busy = true;
    errorMessage = null;
    notifyListeners();
    try {
      final data = await api.updateOperationStopStatus(job.id, stopId, status, proof: proof);
      final raw = data['job'];
      if (raw is Map) currentJob = Booking.fromJson(Map<String, dynamic>.from(raw));
      HapticFeedback.mediumImpact();
      if (currentJob?.status == 'completed') {
        if (driverState != null) {
          driverState = driverState!.copyWith(availability: 'available', activeBookingId: 0);
        }
        unawaited(refreshOperationalState(silent: true));
        unawaited(loadEarnings('today', silent: true));
      }
    } catch (error) {
      errorMessage = _message(error);
      rethrow;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> refreshOperationsJob({bool silent = true}) async {
    final api = _api;
    final job = currentJob;
    if (api == null || job == null || !job.isOperations) return;
    try {
      final data = await api.operationsJob(job.id);
      final raw = data['job'];
      if (raw is Map) currentJob = Booking.fromJson(Map<String, dynamic>.from(raw));
      notifyListeners();
    } catch (error) {
      if (!silent) {
        errorMessage = _message(error);
        notifyListeners();
        rethrow;
      }
    }
  }

  Future<void> loadTripExtras({bool silent = false}) async {
""",
    'operations session methods',
)

replace_one('lib/screens/job_screen.dart', "import 'chat_screen.dart';\n", "import 'chat_screen.dart';\nimport 'operations_job_screen.dart';\n", 'operations screen import')
replace_one('lib/screens/job_screen.dart', "        final next = _nextStatus(job.status);\n", "        if (job.isOperations) {\n          return OperationsJobScreen(session: session);\n        }\n        final next = _nextStatus(job.status);\n", 'operations screen route')

replace_one('lib/widgets/offer_card.dart', """              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(99)),
                child: Text('$seconds sec', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
              ),
""", """              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(99)),
                child: Text(job.jobTypeLabel.toUpperCase(), style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(width: 8),
              Text('$seconds sec', style: const TextStyle(fontWeight: FontWeight.w900)),
""", 'offer type badge')
replace_one('lib/widgets/offer_card.dart', "const Text('trip total', style: TextStyle(color: Color(0xFF666666), fontSize: 12)),", "Text(job.isRide ? 'trip total' : 'job value', style: const TextStyle(color: Color(0xFF666666), fontSize: 12)),", 'offer value label')
replace_one('lib/widgets/offer_card.dart', "_RouteLine(icon: Icons.radio_button_checked, title: 'Pick-up', label: job.pickup),", "_RouteLine(icon: Icons.radio_button_checked, title: job.isRide ? 'Pick-up' : 'Start', label: job.pickup),", 'offer start label')
replace_one('lib/widgets/offer_card.dart', "_RouteLine(icon: Icons.stop_rounded, title: 'Destination', label: job.dropoff),", "_RouteLine(icon: Icons.stop_rounded, title: job.isRide ? 'Destination' : 'Finish', label: job.dropoff),", 'offer finish label')
replace_one('lib/widgets/offer_card.dart', """              if (job.passengers > 0) _InfoChip(icon: Icons.person_outline, label: '${job.passengers} passenger${job.passengers == 1 ? '' : 's'}'),
              if (job.pickupTime.isNotEmpty) _InfoChip(icon: Icons.schedule, label: job.pickupTime),
""", """              if (job.isRide && job.passengers > 0) _InfoChip(icon: Icons.person_outline, label: '${job.passengers} passenger${job.passengers == 1 ? '' : 's'}'),
              if (job.isOperations && job.operationsSummary.total > 0) _InfoChip(icon: Icons.route_rounded, label: '${job.operationsSummary.total} stop${job.operationsSummary.total == 1 ? '' : 's'}'),
              if (job.pickupTime.isNotEmpty) _InfoChip(icon: Icons.schedule, label: job.pickupTime),
""", 'offer stop chip')
replace_one('lib/widgets/offer_card.dart', "child: const Text('Accept trip'),", "child: Text(job.isRide ? 'Accept trip' : 'Accept ${job.jobTypeLabel.toLowerCase()}'),", 'offer accept label')

replace_one('lib/screens/nearby_jobs_screen.dart', "const Text('Current job'", "Text(current.isRide ? 'Current ride' : 'Current ${current.jobTypeLabel.toLowerCase()}'", 'current job label')
replace_one('lib/screens/nearby_jobs_screen.dart', "Text(current.status.toUpperCase()", "Text(current.isOperations ? '${current.status.toUpperCase()} · ${current.operationsSummary.completed}/${current.operationsSummary.total} STOPS' : current.status.toUpperCase()", 'current progress')
replace_one('lib/screens/nearby_jobs_screen.dart', "Expanded(child: Text('Nearby trip requests'", "Expanded(child: Text('Nearby jobs'", 'nearby title')
replace_one('lib/screens/nearby_jobs_screen.dart', "'Your active job is shown above. New nearby requests appear here separately.'", "'Your active job is shown above. New nearby jobs appear here separately.'", 'nearby copy 1')
replace_one('lib/screens/nearby_jobs_screen.dart', "'If you close an offer pop-up, the request stays here until it expires or you respond.'", "'If you close an offer pop-up, the job stays here until it expires or you respond.'", 'nearby copy 2')
replace_one('lib/screens/nearby_jobs_screen.dart', "const Text('No new nearby requests'", "const Text('No new nearby jobs'", 'nearby empty title')
replace_one('lib/screens/nearby_jobs_screen.dart', "'You still have an active job. New requests will appear here when available.'", "'You still have an active job. New jobs will appear here when available.'", 'nearby active copy')

replace_one('lib/screens/driver_home_screen.dart', "? (currentJob != null ? 'You have an active trip.' : 'You’re ready to receive nearby trip requests.')", "? (currentJob != null ? 'You have an active ${currentJob.isRide ? 'ride' : currentJob.jobTypeLabel.toLowerCase()}.' : 'You’re ready to receive nearby jobs.')", 'home online copy')
replace_one('lib/screens/driver_home_screen.dart', "'Ready to drive? Go online to receive trip requests.'", "'Ready to drive? Go online to receive jobs.'", 'home offline copy')
replace_one('lib/screens/driver_home_screen.dart', "Text('${session.offers.length} trip request${session.offers.length == 1 ? '' : 's'} waiting'", "Text('${session.offers.length} job request${session.offers.length == 1 ? '' : 's'} waiting'", 'home waiting jobs')
replace_one('lib/screens/driver_home_screen.dart', "Text('Active trip · ${currentJob.status.toString().toUpperCase()}'", "Text('Active ${currentJob.isRide ? 'ride' : currentJob.jobTypeLabel.toLowerCase()} · ${currentJob.status.toString().toUpperCase()}'", 'home active label')
replace_one('lib/screens/driver_home_screen.dart', "const Text('New trip request'", "Text(widget.offer.booking.isRide ? 'New trip request' : 'New ${widget.offer.booking.jobTypeLabel.toLowerCase()} job'", 'offer sheet title')

replace_one('tool/patch_platforms.py', "    'android.permission.POST_NOTIFICATIONS',\n]", "    'android.permission.POST_NOTIFICATIONS',\n    'android.permission.CAMERA',\n]", 'android camera permission')
replace_one('tool/patch_platforms.py', "    data['NSLocationAlwaysAndWhenInUseUsageDescription'] = 'Gaotus Mobility needs background location while you are online as a driver so dispatch and passengers can see your current position.'\n", "    data['NSLocationAlwaysAndWhenInUseUsageDescription'] = 'Gaotus Mobility needs background location while you are online as a driver so dispatch and customers can see your current position.'\n    data['NSCameraUsageDescription'] = 'Gaotus Mobility uses the camera to capture proof-of-delivery photos.'\n    data['NSPhotoLibraryUsageDescription'] = 'Gaotus Mobility may access photos when you attach proof to an operations stop.'\n", 'iOS POD permissions')

print('Applied Driver v0.5.9 Unified Operations patch.')
