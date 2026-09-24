from pathlib import Path

root=Path('driver')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.2+7','version: 0.5.3+8','version')
replace_one('lib/config/app_config.dart',"static const String version = '0.5.2';","static const String version = '0.5.3';",'app version')

p=root/'lib/core/api_client.dart'
s=p.read_text()
marker="  Future<Map<String, dynamic>> driverMe() => _request('POST', '/driver/me');\n"
if 'liveSnapshot()' not in s:
    if marker not in s: raise SystemExit('api live snapshot marker missing')
    s=s.replace(marker,marker+"  Future<Map<String, dynamic>> liveSnapshot() => _request('POST', '/driver/live-snapshot');\n",1)
p.write_text(s)

p=root/'lib/state/app_session.dart'
s=p.read_text()
if 'Timer? _wordpressHeartbeatTimer;' not in s:
    s=s.replace('  Timer? _reconcileTimer;\n','  Timer? _reconcileTimer;\n  Timer? _wordpressHeartbeatTimer;\n',1)

start=s.index('  Future<void> initialize() async {')
end=s.index('\n  Future<void> login({',start)
new_init=r'''  Future<void> initialize() async {
    _realtime.onConnectionChanged = (connected) {
      realtimeConnected = connected;
      notifyListeners();
      if (connected && authenticated) unawaited(_pollOperationalSafetyNet());
    };
    _realtime.onEvent = _onRealtimeEvent;
    _push.onToken = (value) {
      pushAvailable = _push.available;
      if (authenticated) unawaited(_registerPushIfPossible());
      notifyListeners();
    };
    _push.onMessage = _onPushMessage;

    try { await _offerNotifications.initialize().timeout(const Duration(seconds: 4)); } catch (_) {}
    try { await _push.initialize().timeout(const Duration(seconds: 5)); } catch (_) {}
    pushAvailable = _push.available;

    try {
      final storedServer = await _store.readServer().timeout(const Duration(seconds: 4));
      final storedToken = await _store.readToken().timeout(const Duration(seconds: 4));
      final storedRealtime = await _store.readRealtimeUrl().timeout(const Duration(seconds: 4));
      if (storedServer != null && storedServer.isNotEmpty) serverUrl = storedServer;
      token = storedToken;
      realtimeUrl = storedRealtime;

      if (serverUrl.isNotEmpty && token != null && token!.isNotEmpty) {
        _api = ApiClient(siteUrl: serverUrl, token: token);
        authenticated = true;
        booting = false;
        notifyListeners();
        unawaited(_restoreSessionInBackground());
        return;
      }
    } catch (error) {
      errorMessage = 'Startup recovery: ${_message(error)}';
    }
    booting = false;
    notifyListeners();
  }

  Future<void> _restoreSessionInBackground() async {
    final api = _api;
    if (api == null || !authenticated) return;
    try {
      final snapshot = await api.liveSnapshot().timeout(const Duration(seconds: 12));
      _applySnapshot(snapshot);
      errorMessage = null;
    } on ApiException catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) {
        await logout(localOnly: true);
        return;
      }
      errorMessage = 'Connected session; live sync is retrying: ${error.message}';
    } catch (error) {
      errorMessage = 'Connected session; live sync is retrying: ${_message(error)}';
    }
    notifyListeners();
    if (!authenticated) return;
    unawaited(_finishRuntimeBootstrap());
  }
'''
s=s[:start]+new_init+s[end:]

start=s.index('  Future<void> _finishLoginBootstrap() async {')
end=s.index('\n  Future<void> _discoverRealtime()',start)
new_finish=r'''  Future<void> _finishLoginBootstrap() async {
    final api = _api;
    if (api == null || !authenticated) return;
    try {
      final snapshot = await api.liveSnapshot().timeout(const Duration(seconds: 12));
      _applySnapshot(snapshot);
      errorMessage = null;
    } on ApiException catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) {
        await logout(localOnly: true);
        return;
      }
      errorMessage = 'Signed in. Driver data sync is retrying: ${error.message}';
    } catch (error) {
      errorMessage = 'Signed in. Driver data sync is retrying: ${_message(error)}';
    }
    notifyListeners();
    if (!authenticated) return;
    unawaited(_finishRuntimeBootstrap());
  }

  Future<void> _finishRuntimeBootstrap() async {
    if (!authenticated) return;
    unawaited(loadEarnings('today', silent: true));
    try { await _discoverRealtime().timeout(const Duration(seconds: 6)); } catch (_) {}
    if (!authenticated) return;
    try { await _registerPushIfPossible().timeout(const Duration(seconds: 6)); } catch (_) {}
    if (!authenticated) return;
    await _startRuntimeServices();
    notifyListeners();
  }
'''
s=s[:start]+new_finish+s[end:]

old=r'''  Future<void> _startRuntimeServices() async {
    final rawToken = token;
    if (realtimeUrl != null && realtimeUrl!.isNotEmpty && rawToken != null) {
      await _realtime.connect(baseUrl: realtimeUrl!, token: rawToken);
    }
    if (isOnline) await _startLocation();
    _fallbackPollTimer?.cancel();
    _fallbackPollTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      unawaited(_pollOperationalSafetyNet());
    });
    _eventPollTimer?.cancel();
    _eventPollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(_pollRealtimeEvents());
    });
    _reconcileTimer?.cancel();
    _reconcileTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      unawaited(refreshAll(silent: true));
    });
    _locationRetryTimer?.cancel();
    _locationRetryTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      if (isOnline && _lastPosition != null) unawaited(_flushLatestLocation(forceHeartbeat: true));
    });
  }
'''
new=r'''  Future<void> _startRuntimeServices() async {
    final rawToken = token;
    if (realtimeUrl != null && realtimeUrl!.isNotEmpty && rawToken != null) {
      unawaited(_realtime.connect(baseUrl: realtimeUrl!, token: rawToken));
    }
    if (isOnline) unawaited(_startLocation());
    _fallbackPollTimer?.cancel();
    _fallbackPollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(_pollOperationalSafetyNet());
    });
    _eventPollTimer?.cancel();
    _eventPollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(_pollRealtimeEvents());
    });
    _reconcileTimer?.cancel();
    _reconcileTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      unawaited(refreshAll(silent: true));
    });
    _locationRetryTimer?.cancel();
    _locationRetryTimer = Timer.periodic(const Duration(seconds: 6), (_) {
      if (isOnline && _lastPosition != null) unawaited(_flushLatestLocation(forceHeartbeat: true));
    });
    _wordpressHeartbeatTimer?.cancel();
    _wordpressHeartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      final position = _lastPosition;
      if (authenticated && isOnline && position != null) unawaited(_sendWordPressFallbackPing(position, force: true));
    });
    if (isOnline) unawaited(primeLocation());
  }
'''
if old not in s: raise SystemExit('runtime services marker missing')
s=s.replace(old,new,1)

old=r'''  Future<void> _pollOperationalSafetyNet() async {
    if (!authenticated || _operationalRefreshInFlight) return;
    _operationalRefreshInFlight = true;
    try {
      await refreshOperationalState(silent: true).timeout(const Duration(seconds: 8));
    } catch (_) {
      // Realtime and the next safety-net tick remain available.
    } finally {
      _operationalRefreshInFlight = false;
    }
  }
'''
new=r'''  Future<void> _pollOperationalSafetyNet() async {
    if (!authenticated || _operationalRefreshInFlight || _api == null) return;
    _operationalRefreshInFlight = true;
    try {
      final snapshot = await _api!.liveSnapshot().timeout(const Duration(seconds: 6));
      _applySnapshot(snapshot);
      notifyListeners();
    } on ApiException catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) await logout(localOnly: true);
    } catch (_) {
      // The next 2-second snapshot tick and realtime mailbox remain available.
    } finally {
      _operationalRefreshInFlight = false;
    }
  }
'''
if old not in s: raise SystemExit('operational safety net marker missing')
s=s.replace(old,new,1)

marker='  Future<void> _loadAll(ApiClient api) async {'
if 'void _applySnapshot(' not in s:
    method=r'''  void _applySnapshot(Map<String, dynamic> data) {
    driverId = intValue(data['driver_id']);
    driverName = (data['name'] ?? driverName).toString();
    final state = mapValue(data['state']);
    if (state.isNotEmpty) driverState = DriverState.fromJson(state);
    _applyCurrentJob(<String,dynamic>{'job': data['job']});
    _applyOffers(<String,dynamic>{'offers': data['offers']});
  }

'''
    if marker not in s: raise SystemExit('load all marker missing')
    s=s.replace(marker,method+marker,1)

old=r'''  Future<void> primeLocation() async {
    try {
      final position = await _location.current();
      _lastPosition = position;
      notifyListeners();
    } catch (error) {
      errorMessage = _message(error);
      notifyListeners();
    }
  }
'''
new=r'''  Future<void> primeLocation() async {
    try {
      final position = await _location.current();
      _onPosition(position);
      if (isOnline) unawaited(_sendWordPressFallbackPing(position, force: true));
    } catch (error) {
      errorMessage = _message(error);
      notifyListeners();
    }
  }
'''
if old not in s: raise SystemExit('prime location marker missing')
s=s.replace(old,new,1)

old=r'''  void _onPosition(Position position) {
    _lastPosition = position;
    _pendingPosition = position;
    notifyListeners();
    unawaited(_flushLatestLocation());
  }
'''
new=r'''  void _onPosition(Position position) {
    _lastPosition = position;
    _pendingPosition = position;
    notifyListeners();
    unawaited(_flushLatestLocation());
    final now = DateTime.now();
    if (_lastWordPressFallbackPing == null || now.difference(_lastWordPressFallbackPing!) >= const Duration(seconds: 5)) {
      unawaited(_sendWordPressFallbackPing(position));
    }
  }
'''
if old not in s: raise SystemExit('on position marker missing')
s=s.replace(old,new,1)

start=s.index('  Future<void> _flushLatestLocation({bool forceHeartbeat=false}) async {')
end=s.index('\n  Future<void> _sendWordPressFallbackPing',start)
new_flush=r'''  Future<void> _flushLatestLocation({bool forceHeartbeat=false}) async {
    if (_locationSendInFlight || availability == 'offline') return;
    final position = _pendingPosition ?? (forceHeartbeat ? _lastPosition : null);
    if (position == null) return;
    final now = DateTime.now();
    if (!forceHeartbeat) {
      final last = _lastRealtimeHttpPing;
      if (last != null && now.difference(last) < const Duration(seconds: 2)) return;
    }
    _locationSendInFlight = true;
    final sequence = ++_locationSequence;
    try {
      final sentRealtime = _realtime.sendLocation(
        lat: position.latitude, lng: position.longitude, accuracy: position.accuracy,
        heading: position.heading, speed: position.speed,
        availability: availability == 'offline' ? 'online' : availability,
        sequence: sequence, capturedAt: position.timestamp.toUtc().toIso8601String(),
      );
      var delivered = sentRealtime;
      if (!sentRealtime) {
        _lastRealtimeHttpPing = now;
        delivered = await _realtime.sendLocationHttp(
          lat: position.latitude, lng: position.longitude, accuracy: position.accuracy,
          heading: position.heading, speed: position.speed,
          availability: availability == 'offline' ? 'online' : availability,
          sequence: sequence, capturedAt: position.timestamp.toUtc().toIso8601String(),
        );
      }
      if (delivered) _pendingPosition = null;
      if (_lastWordPressFallbackPing == null || now.difference(_lastWordPressFallbackPing!) >= const Duration(seconds: 5)) {
        unawaited(_sendWordPressFallbackPing(position));
      }
    } finally {
      _locationSendInFlight = false;
    }
  }
'''
s=s[:start]+new_flush+s[end:]

start=s.index('  Future<void> _sendWordPressFallbackPing(Position position) async {')
end=s.index('\n  Future<List<ChatMessage>>',start)
new_wp=r'''  Future<void> _sendWordPressFallbackPing(Position position, {bool force = false}) async {
    final api = _api;
    if (api == null || !authenticated || availability == 'offline') return;
    final now = DateTime.now();
    if (!force && _lastWordPressFallbackPing != null && now.difference(_lastWordPressFallbackPing!) < const Duration(seconds: 5)) return;
    _lastWordPressFallbackPing = now;
    try {
      final data = await api.ping(
        lat: position.latitude, lng: position.longitude, accuracy: position.accuracy,
        heading: position.heading, speed: position.speed,
        availability: availability == 'offline' ? 'online' : availability,
      ).timeout(const Duration(seconds: 6));
      final state = mapValue(data['state']);
      if (state.isNotEmpty) driverState = DriverState.fromJson(state);
      final discovered = data['realtime_url']?.toString();
      if (discovered != null && discovered.isNotEmpty && token != null) {
        realtimeUrl = discovered;
        unawaited(_store.writeRealtimeUrl(discovered));
      }
      notifyListeners();
    } catch (_) {}
  }
'''
s=s[:start]+new_wp+s[end:]

old="""      if (value == 'offline') {
        await _stopLocation();
      } else {
        await _startLocation();
      }
"""
new="""      if (value == 'offline') {
        await _stopLocation();
      } else {
        await _startLocation();
        unawaited(primeLocation());
      }
"""
if old not in s: raise SystemExit('availability location marker missing')
s=s.replace(old,new,1)

s=s.replace('      _reconcileTimer?.cancel();\n      _reconcileTimer = null;\n','      _reconcileTimer?.cancel();\n      _reconcileTimer = null;\n      _wordpressHeartbeatTimer?.cancel();\n      _wordpressHeartbeatTimer = null;\n',1)
s=s.replace('    _reconcileTimer?.cancel();\n    _locationRetryTimer?.cancel();','    _reconcileTimer?.cancel();\n    _wordpressHeartbeatTimer?.cancel();\n    _locationRetryTimer?.cancel();',1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.3+8'],
  'lib/config/app_config.dart':["version = '0.5.3'"],
  'lib/core/api_client.dart':['/driver/live-snapshot'],
  'lib/state/app_session.dart':['_restoreSessionInBackground','_wordpressHeartbeatTimer','Duration(seconds: 2)','force: true','liveSnapshot'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Driver v0.5.3 dispatch self-heal patch applied')
