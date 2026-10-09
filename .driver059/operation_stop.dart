import 'parsers.dart';

final class OperationsSummary {
  const OperationsSummary({
    this.total = 0,
    this.pending = 0,
    this.active = 0,
    this.completed = 0,
    this.failed = 0,
    this.postponed = 0,
  });

  final int total;
  final int pending;
  final int active;
  final int completed;
  final int failed;
  final int postponed;

  factory OperationsSummary.fromJson(Map<String, dynamic> json) => OperationsSummary(
        total: intValue(json['total']),
        pending: intValue(json['pending']),
        active: intValue(json['active']),
        completed: intValue(json['completed']),
        failed: intValue(json['failed']),
        postponed: intValue(json['postponed']),
      );
}

final class OperationsPodSettings {
  const OperationsPodSettings({
    this.enablePhoto = true,
    this.requirePhotoDelivery = true,
    this.requirePhotoPickup = true,
    this.enableSignature = true,
    this.requireSignature = false,
    this.enablePin = true,
    this.requirePin = false,
    this.enableBarcode = true,
    this.requireBarcode = false,
    this.enableRecipientName = true,
    this.requireRecipientName = false,
    this.requireFailureReason = true,
  });

  final bool enablePhoto;
  final bool requirePhotoDelivery;
  final bool requirePhotoPickup;
  final bool enableSignature;
  final bool requireSignature;
  final bool enablePin;
  final bool requirePin;
  final bool enableBarcode;
  final bool requireBarcode;
  final bool enableRecipientName;
  final bool requireRecipientName;
  final bool requireFailureReason;

  static bool _bool(Object? value, bool fallback) {
    if (value == null) return fallback;
    if (value is bool) return value;
    if (value is num) return value != 0;
    final text = value.toString().trim().toLowerCase();
    if (<String>{'1', 'true', 'yes', 'on'}.contains(text)) return true;
    if (<String>{'0', 'false', 'no', 'off'}.contains(text)) return false;
    return fallback;
  }

  factory OperationsPodSettings.fromJson(Map<String, dynamic> json) => OperationsPodSettings(
        enablePhoto: _bool(json['enable_photo'], true),
        requirePhotoDelivery: _bool(json['require_photo_delivery'], true),
        requirePhotoPickup: _bool(json['require_photo_pickup'], true),
        enableSignature: _bool(json['enable_signature'], true),
        requireSignature: _bool(json['require_signature'], false),
        enablePin: _bool(json['enable_pin'], true),
        requirePin: _bool(json['require_pin'], false),
        enableBarcode: _bool(json['enable_barcode'], true),
        requireBarcode: _bool(json['require_barcode'], false),
        enableRecipientName: _bool(json['enable_recipient_name'], true),
        requireRecipientName: _bool(json['require_recipient_name'], false),
        requireFailureReason: _bool(json['require_failure_reason'], true),
      );
}

final class OperationStop {
  const OperationStop({
    required this.id,
    required this.bookingId,
    required this.stopKey,
    required this.sequence,
    required this.operationType,
    required this.status,
    required this.name,
    required this.address,
    required this.contactName,
    required this.contactPhone,
    required this.timeWindowStart,
    required this.timeWindowEnd,
    required this.packageRef,
    required this.packageCount,
    required this.packageWeightKg,
    required this.packageSize,
    required this.senderName,
    required this.senderPhone,
    required this.recipientName,
    required this.recipientPhone,
    required this.codAmount,
    required this.driverInstructions,
    required this.notes,
    this.lat,
    this.lng,
    this.completedAt = '',
  });

  final int id;
  final int bookingId;
  final String stopKey;
  final int sequence;
  final String operationType;
  final String status;
  final String name;
  final String address;
  final String contactName;
  final String contactPhone;
  final double? lat;
  final double? lng;
  final String timeWindowStart;
  final String timeWindowEnd;
  final String packageRef;
  final int packageCount;
  final double packageWeightKg;
  final String packageSize;
  final String senderName;
  final String senderPhone;
  final String recipientName;
  final String recipientPhone;
  final double codAmount;
  final String driverInstructions;
  final String notes;
  final String completedAt;

  bool get isTerminal => <String>{'completed', 'failed', 'postponed'}.contains(status);
  bool get isCompleted => status == 'completed';
  bool get isPickup => operationType == 'pickup';
  bool get isDelivery => operationType == 'delivery' || operationType == 'pickup_delivery';

  String get operationLabel => switch (operationType) {
        'pickup' => 'Collection',
        'delivery' => 'Delivery',
        'pickup_delivery' => 'Pickup / delivery',
        'passenger' => 'Passenger',
        _ => 'Service',
      };

  String get primaryContactName {
    if (contactName.trim().isNotEmpty) return contactName;
    if (isPickup && senderName.trim().isNotEmpty) return senderName;
    if (recipientName.trim().isNotEmpty) return recipientName;
    return senderName;
  }

  String get primaryPhone {
    if (contactPhone.trim().isNotEmpty) return contactPhone;
    if (isPickup && senderPhone.trim().isNotEmpty) return senderPhone;
    if (recipientPhone.trim().isNotEmpty) return recipientPhone;
    return senderPhone;
  }

  factory OperationStop.fromJson(Map<String, dynamic> json) => OperationStop(
        id: intValue(json['id']),
        bookingId: intValue(json['booking_id']),
        stopKey: (json['stop_key'] ?? '').toString(),
        sequence: intValue(json['sequence']),
        operationType: (json['operation_type'] ?? 'service').toString(),
        status: (json['status'] ?? 'pending').toString(),
        name: (json['name'] ?? '').toString(),
        address: (json['address'] ?? '').toString(),
        contactName: (json['contact_name'] ?? '').toString(),
        contactPhone: (json['contact_phone'] ?? '').toString(),
        lat: doubleValue(json['lat']),
        lng: doubleValue(json['lng']),
        timeWindowStart: (json['time_window_start'] ?? '').toString(),
        timeWindowEnd: (json['time_window_end'] ?? '').toString(),
        packageRef: (json['package_ref'] ?? '').toString(),
        packageCount: intValue(json['package_count']),
        packageWeightKg: doubleValue(json['package_weight_kg']) ?? 0,
        packageSize: (json['package_size'] ?? '').toString(),
        senderName: (json['sender_name'] ?? '').toString(),
        senderPhone: (json['sender_phone'] ?? '').toString(),
        recipientName: (json['recipient_name'] ?? '').toString(),
        recipientPhone: (json['recipient_phone'] ?? '').toString(),
        codAmount: doubleValue(json['cod_amount']) ?? 0,
        driverInstructions: (json['driver_instructions'] ?? '').toString(),
        notes: (json['notes'] ?? '').toString(),
        completedAt: (json['completed_at'] ?? '').toString(),
      );
}
