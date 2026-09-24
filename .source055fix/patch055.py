from pathlib import Path

root=Path('passenger')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.4+15','version: 0.5.5+16','version')
replace_one('lib/config/app_config.dart',"static const version = '0.5.4';","static const version = '0.5.5';",'app version')

(root/'lib/widgets/premium_car_marker.dart').write_text(r'''import 'dart:math' as math;

import 'package:flutter/material.dart';

class PremiumCarMarker extends StatelessWidget {
  const PremiumCarMarker({
    super.key,
    required this.headingDegrees,
    this.size = 52,
    this.accent = const Color(0xFF111111),
    this.selected = false,
    this.dimmed = false,
  });

  final double headingDegrees;
  final double size;
  final Color accent;
  final bool selected;
  final bool dimmed;

  @override
  Widget build(BuildContext context) {
    final angle = (headingDegrees.isFinite ? headingDegrees : 0) * math.pi / 180;
    return SizedBox(
      width: size + 14,
      height: size + 14,
      child: Center(
        child: DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: selected
                ? <BoxShadow>[
                    BoxShadow(color: accent.withOpacity(.24), blurRadius: 14, spreadRadius: 4),
                  ]
                : const <BoxShadow>[],
          ),
          child: Transform.rotate(
            angle: angle,
            child: CustomPaint(
              size: Size(size * .70, size),
              painter: _PremiumCarPainter(
                accent: accent,
                selected: selected,
                dimmed: dimmed,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _PremiumCarPainter extends CustomPainter {
  const _PremiumCarPainter({
    required this.accent,
    required this.selected,
    required this.dimmed,
  });

  final Color accent;
  final bool selected;
  final bool dimmed;

  @override
  void paint(Canvas canvas, Size size) {
    final opacity = dimmed ? .58 : 1.0;
    final w = size.width;
    final h = size.height;

    final shadow = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * .17, h * .08, w * .66, h * .84).shift(const Offset(1.8, 3.6)),
      Radius.circular(w * .19),
    );
    canvas.drawRRect(
      shadow,
      Paint()
        ..color = Colors.black.withOpacity(.22 * opacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );

    final wheelPaint = Paint()..color = const Color(0xFF111418).withOpacity(opacity);
    for (final rect in <Rect>[
      Rect.fromLTWH(w * .06, h * .22, w * .16, h * .19),
      Rect.fromLTWH(w * .78, h * .22, w * .16, h * .19),
      Rect.fromLTWH(w * .06, h * .63, w * .16, h * .19),
      Rect.fromLTWH(w * .78, h * .63, w * .16, h * .19),
    ]) {
      canvas.drawRRect(RRect.fromRectAndRadius(rect, Radius.circular(w * .07)), wheelPaint);
    }

    final body = Path()
      ..moveTo(w * .34, h * .04)
      ..quadraticBezierTo(w * .50, h * .00, w * .66, h * .04)
      ..lineTo(w * .82, h * .18)
      ..quadraticBezierTo(w * .90, h * .29, w * .88, h * .47)
      ..lineTo(w * .84, h * .79)
      ..quadraticBezierTo(w * .82, h * .93, w * .68, h * .97)
      ..lineTo(w * .32, h * .97)
      ..quadraticBezierTo(w * .18, h * .93, w * .16, h * .79)
      ..lineTo(w * .12, h * .47)
      ..quadraticBezierTo(w * .10, h * .29, w * .18, h * .18)
      ..close();

    final bodyRect = Rect.fromLTWH(0, 0, w, h);
    canvas.drawPath(
      body,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color.lerp(Colors.white, accent, .05)!.withOpacity(opacity),
            const Color(0xFFF8FAFC).withOpacity(opacity),
            const Color(0xFFD8DEE6).withOpacity(opacity),
          ],
          stops: const <double>[0, .52, 1],
        ).createShader(bodyRect),
    );
    canvas.drawPath(
      body,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.3
        ..color = const Color(0xFF8E98A6).withOpacity(.72 * opacity),
    );

    final frontGlass = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * .24, h * .21, w * .52, h * .22),
      Radius.circular(w * .09),
    );
    canvas.drawRRect(
      frontGlass,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            const Color(0xFF2B3643).withOpacity(.96 * opacity),
            const Color(0xFF607184).withOpacity(.86 * opacity),
          ],
        ).createShader(frontGlass.outerRect),
    );

    final roof = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * .28, h * .39, w * .44, h * .29),
      Radius.circular(w * .11),
    );
    canvas.drawRRect(
      roof,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Colors.white.withOpacity(.98 * opacity),
            const Color(0xFFE7EBF0).withOpacity(.92 * opacity),
          ],
        ).createShader(roof.outerRect),
    );

    final rearGlass = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * .27, h * .66, w * .46, h * .14),
      Radius.circular(w * .07),
    );
    canvas.drawRRect(
      rearGlass,
      Paint()
        ..color = const Color(0xFF3A4653).withOpacity(.82 * opacity),
    );

    final accentPaint = Paint()..color = accent.withOpacity((selected ? .95 : .72) * opacity);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(w * .44, h * .10, w * .12, h * .055),
        Radius.circular(w * .03),
      ),
      accentPaint,
    );

    final lightPaint = Paint()..color = const Color(0xFFFFF7D1).withOpacity(opacity);
    canvas.drawOval(Rect.fromLTWH(w * .20, h * .09, w * .13, h * .055), lightPaint);
    canvas.drawOval(Rect.fromLTWH(w * .67, h * .09, w * .13, h * .055), lightPaint);

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(w * .36, h * .84, w * .28, h * .045),
        Radius.circular(w * .025),
      ),
      Paint()..color = const Color(0xFF20252A).withOpacity(.78 * opacity),
    );

    final highlight = Path()
      ..moveTo(w * .30, h * .13)
      ..quadraticBezierTo(w * .48, h * .07, w * .62, h * .11);
    canvas.drawPath(
      highlight,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.35
        ..strokeCap = StrokeCap.round
        ..color = Colors.white.withOpacity(.88 * opacity),
    );
  }

  @override
  bool shouldRepaint(covariant _PremiumCarPainter oldDelegate) =>
      oldDelegate.accent != accent ||
      oldDelegate.selected != selected ||
      oldDelegate.dimmed != dimmed;
}
''')

for rel in ['lib/screens/home_screen.dart','lib/screens/quote_screen.dart']:
    p=root/rel
    s=p.read_text()
    if "import '../widgets/premium_car_marker.dart';" not in s:
        marker="import '../state/passenger_session.dart';\n"
        if marker not in s: raise SystemExit(f'passenger import marker missing in {rel}')
        s=s.replace(marker,marker+"import '../widgets/premium_car_marker.dart';\n",1)
    p.write_text(s)

p=root/'lib/screens/home_screen.dart'
s=p.read_text()
s=s.replace("width:42,height:42,child:_NearbyCarMarker(car:car)","width:58,height:64,child:_NearbyCarMarker(car:car)")
start=s.index('class _NearbyCarMarker extends StatelessWidget {')
end=len(s)
block=s[start:]
old=r'''class _NearbyCarMarker extends StatelessWidget {
  const _NearbyCarMarker({required this.car});
  final NearbyCar car;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFF0A0A0A), width: 2),
          boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 8)],
        ),
        child: const Icon(Icons.local_taxi_rounded, size: 24, color: Color(0xFF0A0A0A)),
      );
}
'''
new=r'''class _NearbyCarMarker extends StatelessWidget {
  const _NearbyCarMarker({required this.car});
  final NearbyCar car;

  @override
  Widget build(BuildContext context) => PremiumCarMarker(
        headingDegrees: car.heading ?? 0,
        size: 48,
        accent: car.signal == 'delayed' ? const Color(0xFF6B7280) : const Color(0xFF15171A),
        dimmed: car.signal == 'lost',
      );
}
'''
if old not in s: raise SystemExit('home nearby marker class missing')
s=s.replace(old,new,1)
s=s.replace('Passenger v0.5.4','Passenger v0.5.5')
p.write_text(s)

p=root/'lib/screens/quote_screen.dart'
s=p.read_text()
s=s.replace("width:42,height:42,child:_QuoteNearbyCar(car:car)","width:58,height:64,child:_QuoteNearbyCar(car:car)")
old=r'''class _QuoteNearbyCar extends StatelessWidget{
  const _QuoteNearbyCar({required this.car});
  final NearbyCar car;
  @override Widget build(BuildContext context)=>Container(
    decoration:BoxDecoration(color:Colors.white,shape:BoxShape.circle,border:Border.all(color:AppTheme.ink,width:2),boxShadow:const <BoxShadow>[BoxShadow(color:Color(0x33000000),blurRadius:8)]),
    child:const Icon(Icons.local_taxi_rounded,size:24,color:AppTheme.ink),
  );
}
'''
new=r'''class _QuoteNearbyCar extends StatelessWidget{
  const _QuoteNearbyCar({required this.car});
  final NearbyCar car;
  @override Widget build(BuildContext context)=>PremiumCarMarker(
    headingDegrees:car.heading??0,
    size:48,
    accent:car.signal=='delayed'?const Color(0xFF6B7280):AppTheme.ink,
    dimmed:car.signal=='lost',
  );
}
'''
if old not in s: raise SystemExit('quote nearby marker class missing')
s=s.replace(old,new,1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.5+16'],
  'lib/config/app_config.dart':["version = '0.5.5'"],
  'lib/widgets/premium_car_marker.dart':['class PremiumCarMarker','LinearGradient','MaskFilter.blur'],
  'lib/screens/home_screen.dart':['PremiumCarMarker(','Passenger v0.5.5','width:58,height:64'],
  'lib/screens/quote_screen.dart':['PremiumCarMarker(','width:58,height:64'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Passenger v0.5.5 premium 3D-look car markers patch applied')
