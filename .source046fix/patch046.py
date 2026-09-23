from pathlib import Path

# Passenger v0.4.6 - inline destination autocomplete in the main ride sheet.

# Version markers.
p = Path('passenger/pubspec.yaml')
x = p.read_text()
if 'version: 0.4.5+9' not in x:
    raise SystemExit('pubspec v0.4.5 contract missing')
p.write_text(x.replace('version: 0.4.5+9', 'version: 0.4.6+10', 1))

p = Path('passenger/lib/config/app_config.dart')
x = p.read_text()
if "static const version = '0.4.5';" not in x:
    raise SystemExit('app config v0.4.5 contract missing')
p.write_text(x.replace("static const version = '0.4.5';", "static const version = '0.4.6';", 1))

p = Path('passenger/lib/screens/home_screen.dart')
x = p.read_text()

# Add inline autocomplete state next to the existing destination coordinates.
old = """  final dropoff = TextEditingController();
  final map = MapController();
  int passengers = 1;
  double? pickupLat, pickupLng, dropoffLat, dropoffLng;
"""
new = """  final dropoff = TextEditingController();
  final map = MapController();
  int passengers = 1;
  double? pickupLat, pickupLng, dropoffLat, dropoffLng;
  List<PlaceSuggestion> destinationSuggestions = <PlaceSuggestion>[];
  bool destinationSearching = false;
  String? destinationSearchError;
  int destinationSearchSerial = 0;
  final String destinationSessionToken = 'gmp_inline_${DateTime.now().microsecondsSinceEpoch}';
"""
if old not in x:
    raise SystemExit('home destination state contract missing')
x = x.replace(old, new, 1)

# Replace the separate-screen destination flow with live inline autocomplete.
old = """  Future<void> chooseDestination() async {
    final selected = await Navigator.of(context).push<PlaceSelection>(MaterialPageRoute(builder: (_) => PlaceSearchScreen(
      session: widget.session,
      title: 'Where to?',
      biasLat: pickupLat ?? center.latitude,
      biasLng: pickupLng ?? center.longitude,
    )));
    if (selected == null) return;
    setState(() {
      dropoff.text = selected.address.isNotEmpty ? selected.address : selected.name;
      dropoffLat = selected.lat;
      dropoffLng = selected.lng;
    });
  }

"""
new = """  void destinationChanged(String value) {
    final query = value.trim();
    final serial = ++destinationSearchSerial;

    setState(() {
      dropoffLat = null;
      dropoffLng = null;
      destinationSearchError = null;
      if (query.length < 2) {
        destinationSuggestions = <PlaceSuggestion>[];
        destinationSearching = false;
      } else {
        destinationSearching = true;
      }
    });

    if (query.length < 2) return;

    Future.delayed(const Duration(milliseconds: 250), () async {
      if (!mounted || serial != destinationSearchSerial) return;
      try {
        final rows = await widget.session.placeAutocomplete(
          query,
          sessionToken: destinationSessionToken,
          lat: pickupLat ?? center.latitude,
          lng: pickupLng ?? center.longitude,
        );
        if (!mounted || serial != destinationSearchSerial) return;
        setState(() {
          destinationSuggestions = rows;
          destinationSearching = false;
          destinationSearchError = null;
        });
      } catch (e) {
        if (!mounted || serial != destinationSearchSerial) return;
        setState(() {
          destinationSuggestions = <PlaceSuggestion>[];
          destinationSearching = false;
          destinationSearchError = '$e';
        });
      }
    });
  }

  Future<void> selectDestinationSuggestion(PlaceSuggestion suggestion) async {
    final serial = ++destinationSearchSerial;
    FocusScope.of(context).unfocus();
    setState(() {
      destinationSearching = true;
      destinationSearchError = null;
    });

    try {
      final PlaceSelection selected;
      if (suggestion.hasCoordinates) {
        selected = PlaceSelection(
          address: suggestion.text.isNotEmpty ? suggestion.text : suggestion.mainText,
          lat: suggestion.lat!,
          lng: suggestion.lng!,
          placeId: suggestion.placeId,
          name: suggestion.mainText,
        );
      } else {
        selected = await widget.session.placeDetails(
          suggestion.placeId,
          sessionToken: destinationSessionToken,
        );
      }

      if (!mounted || serial != destinationSearchSerial) return;
      setState(() {
        dropoff.text = selected.address.isNotEmpty ? selected.address : selected.name;
        dropoffLat = selected.lat;
        dropoffLng = selected.lng;
        destinationSuggestions = <PlaceSuggestion>[];
        destinationSearching = false;
        destinationSearchError = null;
      });
    } catch (e) {
      if (!mounted || serial != destinationSearchSerial) return;
      setState(() {
        destinationSearching = false;
        destinationSearchError = '$e';
      });
    }
  }

"""
if old not in x:
    raise SystemExit('chooseDestination contract missing')
x = x.replace(old, new, 1)

# Make the destination field editable and render live suggestions directly below it.
old = """                      TextField(
                        controller: dropoff,
                        readOnly: true,
                        onTap: chooseDestination,
                        decoration: const InputDecoration(fillColor: Colors.transparent, prefixIcon: Icon(Icons.stop_rounded, size: 19), hintText: 'Where are you going?', suffixIcon: Icon(Icons.search_rounded), border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
                      ),
"""
new = """                      TextField(
                        controller: dropoff,
                        onChanged: destinationChanged,
                        onSubmitted: (_) {
                          if (destinationSuggestions.isNotEmpty) {
                            selectDestinationSuggestion(destinationSuggestions.first);
                          }
                        },
                        textInputAction: TextInputAction.search,
                        decoration: InputDecoration(
                          fillColor: Colors.transparent,
                          prefixIcon: const Icon(Icons.stop_rounded, size: 19),
                          hintText: 'Where are you going?',
                          suffixIcon: destinationSearching
                              ? const Padding(
                                  padding: EdgeInsets.all(14),
                                  child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                                )
                              : const Icon(Icons.search_rounded),
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                        ),
                      ),
                      if (destinationSearchError != null && destinationSearchError!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 2, 16, 10),
                          child: Text(
                            destinationSearchError!,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 12, fontWeight: FontWeight.w700),
                          ),
                        ),
                      if (destinationSuggestions.isNotEmpty)
                        Container(
                          constraints: const BoxConstraints(maxHeight: 220),
                          margin: const EdgeInsets.fromLTRB(8, 0, 8, 10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(color: const Color(0xFFE5E5E2)),
                            boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x18000000), blurRadius: 18, offset: Offset(0, 6))],
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: ListView.separated(
                            shrinkWrap: true,
                            padding: EdgeInsets.zero,
                            itemCount: destinationSuggestions.length,
                            separatorBuilder: (_, __) => const Divider(height: 1, indent: 52),
                            itemBuilder: (context, i) {
                              final suggestion = destinationSuggestions[i];
                              return ListTile(
                                dense: true,
                                leading: const Icon(Icons.location_on_outlined, size: 22),
                                title: Text(
                                  suggestion.mainText.isNotEmpty ? suggestion.mainText : suggestion.text,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontWeight: FontWeight.w800),
                                ),
                                subtitle: suggestion.secondaryText.isNotEmpty
                                    ? Text(suggestion.secondaryText, maxLines: 1, overflow: TextOverflow.ellipsis)
                                    : null,
                                onTap: () => selectDestinationSuggestion(suggestion),
                              );
                            },
                          ),
                        ),
"""
if old not in x:
    raise SystemExit('destination TextField contract missing')
x = x.replace(old, new, 1)

# Visible build marker.
x = x.replace('Passenger v0.4.5', 'Passenger v0.4.6')
x = x.replace('Startup recovery + Google fallback + trip markers', 'Inline address suggestions + Google fallback')
p.write_text(x)

# Static contracts.
home = Path('passenger/lib/screens/home_screen.dart').read_text()
assert 'version: 0.4.6+10' in Path('passenger/pubspec.yaml').read_text()
assert "static const version = '0.4.6';" in Path('passenger/lib/config/app_config.dart').read_text()
assert 'destinationChanged' in home
assert 'selectDestinationSuggestion' in home
assert 'destinationSuggestions.isNotEmpty' in home
assert 'destinationSessionToken' in home
assert 'readOnly: true' not in home.split("controller: dropoff", 1)[1].split("),", 1)[0]
assert 'Passenger v0.4.6' in home
print('Passenger v0.4.6 inline destination autocomplete patch applied')
