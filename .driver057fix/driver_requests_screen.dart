import 'package:flutter/material.dart';

import '../models/job_offer.dart';
import '../state/app_session.dart';
import '../widgets/offer_card.dart';
import 'job_screen.dart';

class DriverRequestsScreen extends StatelessWidget {
  const DriverRequestsScreen({super.key, required this.session});
  final AppSession session;

  @override
  Widget build(BuildContext context) {
    final active = session.offers.where((x) => !x.expired && x.status == 'offered').toList();
    final activeIds = active.map((e) => e.id).toSet();
    final recent = session.recentOffers.where((x) => !activeIds.contains(x.id)).take(30).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Nearby requests'), automaticallyImplyLeading: false),
      body: RefreshIndicator(
        onRefresh: () => session.refreshAll(silent: true),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
          children: <Widget>[
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(24)),
              child: Row(
                children: <Widget>[
                  const CircleAvatar(backgroundColor: Colors.white, child: Icon(Icons.radar_rounded, color: Colors.black)),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          active.isEmpty ? 'Listening for trips' : '${active.length} request${active.length == 1 ? '' : 's'} waiting',
                          style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 3),
                        const Text('Requests stay here until accepted, declined or expired.', style: TextStyle(color: Color(0xFFCCCCCC))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            const Text('Available now', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const SizedBox(height: 10),
            if (active.isEmpty)
              _empty(Icons.radar_rounded, 'No nearby requests right now', 'Stay online. New requests will appear here even if you dismiss the pop-up.'),
            for (final offer in active) ...<Widget>[
              OfferCard(offer: offer, onAccept: () => _accept(context, offer), onDecline: () => _decline(context, offer)),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 22),
            const Text('Recent requests', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const SizedBox(height: 10),
            if (recent.isEmpty) _empty(Icons.history_rounded, 'No recent requests', 'Expired or answered requests will stay here for reference.'),
            for (final offer in recent) ...<Widget>[
              _RecentOfferCard(offer: offer),
              const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }

  Widget _empty(IconData icon, String title, String body) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: const Color(0xFFF5F6F8), borderRadius: BorderRadius.circular(22)),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, size: 28),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 5),
                  Text(body, style: const TextStyle(color: Color(0xFF666666), height: 1.35)),
                ],
              ),
            ),
          ],
        ),
      );

  Future<void> _accept(BuildContext context, JobOffer offer) async {
    try {
      await session.acceptOffer(offer);
      if (context.mounted) {
        await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => JobScreen(session: session)));
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(session.errorMessage ?? 'Could not accept trip.')));
      }
    }
  }

  Future<void> _decline(BuildContext context, JobOffer offer) async {
    try {
      await session.declineOffer(offer);
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(session.errorMessage ?? 'Could not decline trip.')));
      }
    }
  }
}

class _RecentOfferCard extends StatelessWidget {
  const _RecentOfferCard({required this.offer});
  final JobOffer offer;

  @override
  Widget build(BuildContext context) {
    final job = offer.booking;
    final label = offer.status == 'offered' ? (offer.expired ? 'Missed' : 'Closed') : offer.status.toUpperCase();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE4E4E4))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: const Color(0xFFF1F1F1), borderRadius: BorderRadius.circular(99)),
                child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
              ),
              const Spacer(),
              Text('£${job.total.toStringAsFixed(2)}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
            ],
          ),
          const SizedBox(height: 12),
          Text(job.pickup.isEmpty ? 'Pickup unavailable' : job.pickup, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
          const Padding(padding: EdgeInsets.symmetric(vertical: 5), child: Icon(Icons.more_vert_rounded, size: 15, color: Color(0xFF999999))),
          Text(job.dropoff.isEmpty ? 'Destination unavailable' : job.dropoff, maxLines: 1, overflow: TextOverflow.ellipsis),
          if (offer.distanceKm != null) ...<Widget>[
            const SizedBox(height: 10),
            Text('${offer.distanceKm!.toStringAsFixed(1)} km to pickup', style: const TextStyle(color: Color(0xFF666666), fontSize: 12)),
          ],
        ],
      ),
    );
  }
}
