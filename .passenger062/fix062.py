from pathlib import Path

p = Path('passenger/lib/screens/chat_screen.dart')
s = p.read_text()
anchor = """  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.white,
        appBar: AppBar(
          titleSpacing: 0,
          title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text('Your driver'.tr, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
            Text('Messages update automatically', style: TextStyle(fontWeight: FontWeight.w500, fontSize: 11, color: AppTheme.softInk)),
          ]),
        ),"""
replacement = """  Map<String, dynamic> get _driver {
    final booking = widget.session.activeBooking;
    if (booking != null && booking.id == widget.bookingId && booking.driver != null) return booking.driver!;
    return <String, dynamic>{};
  }

  @override
  Widget build(BuildContext context) {
    final driver = _driver;
    final photo = (driver['photo'] ?? driver['avatar_url'] ?? '').toString();
    final name = (driver['name'] ?? 'Your driver'.tr).toString();
    return Scaffold(
        backgroundColor: Colors.white,
        appBar: AppBar(
          titleSpacing: 0,
          title: Row(children: <Widget>[
            CircleAvatar(radius: 18, backgroundColor: const Color(0xFFF2F2F0), backgroundImage: photo.isNotEmpty ? NetworkImage(photo) : null, child: photo.isEmpty ? const Icon(Icons.person_rounded, size: 20) : null),
            const SizedBox(width: 9),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
              const Text('Messages update automatically', style: TextStyle(fontWeight: FontWeight.w500, fontSize: 11, color: AppTheme.softInk)),
            ])),
          ]),
        ),"""
if anchor not in s:
    raise SystemExit('Passenger chat header anchor not found')
s = s.replace(anchor, replacement, 1)
end = '      );\n}'
pos = s.rfind(end)
if pos < 0:
    raise SystemExit('Passenger chat closing anchor not found')
s = s[:pos] + '      );\n  }\n}' + s[pos + len(end):]
p.write_text(s)
print('Applied Passenger v0.6.2 chat driver-photo fix')
