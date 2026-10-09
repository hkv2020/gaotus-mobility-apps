import 'operation_stop.dart';
import 'parsers.dart';

final class Booking {
  const Booking({
    required this.id,
    required this.status,
    required this.pickup,
    required this.dropoff,
    required this.pickupDate,
    required this.pickupTime,
    required this.passengers,
    required this.total,
    required this.paymentMethod,
    required this.customerName,
    required this.customerPhone,
    required this.customerEmail,
    required this.driverNotes,
    required this.additionalNotes,
    required this.flightNumber,
    required this.terminal,
    this.pickupLat,
    this.pickupLng,
    this.dropoffLat,
    this.dropoffLng,
    this.driverId = 0,
    this.vehicleTypeId = 0,
    this.jobType = 'ride',
    this.jobTypeLabel = 'Ride',
    this.operationsEnabled = false,
    this.operationsSummary = const OperationsSummary(),
    this.podSettings = const OperationsPodSettings(),
    this.stops = const <OperationStop>[],
  });

  final int id;
  final String status;
  final String pickup;
  final String dropoff;
  final String pickupDate;
  final String pickupTime;
  final double? pickupLat;
  final double? pickupLng;
  final double? dropoffLat;
  final double? dropoffLng;
  final int driverId;
  final int vehicleTypeId;
  final int passengers;
  final double total;
  final String paymentMethod;
  final String customerName;
  final String customerPhone;
  final String customerEmail;
  final String driverNotes;
  final String additionalNotes;
  final String flightNumber;
  final String terminal;

  final String jobType;
  final String jobTypeLabel;
  final bool operationsEnabled;
  final OperationsSummary operationsSummary;
  final OperationsPodSettings podSettings;
  final List<OperationStop> stops;

  bool get isRide => !operationsEnabled || jobType == 'ride';
  bool get isOperations => !isRide;

  OperationStop? get nextOperationStop {
    for (final stop in stops) {
      if (!stop.isTerminal) return stop;
    }
    return null;
  }

  factory Booking.fromJson(Map<String, dynamic> json) {
    final customer = mapValue(json['customer']);
    final operations = mapValue(json['operations']);
    final rawStops = json['stops'];
    final stops = rawStops is List
        ? rawStops
            .whereType<Map>()
            .map((item) => OperationStop.fromJson(Map<String, dynamic>.from(item)))
            .toList()
        : <OperationStop>[];
    final jobType = (json['job_type'] ?? 'ride').toString();
    final enabledRaw = operations['enabled'];
    final operationsEnabled = enabledRaw is bool
        ? enabledRaw
        : enabledRaw is num
            ? enabledRaw != 0
            : <String>{'1', 'true', 'yes', 'on'}.contains(enabledRaw?.toString().toLowerCase());
    return Booking(
      id: intValue(json['id']),
      status: (json['status'] ?? 'pending').toString(),
      pickup: (json['pickup'] ?? '').toString(),
      dropoff: (json['dropoff'] ?? '').toString(),
      pickupDate: (json['pickup_date'] ?? '').toString(),
      pickupTime: (json['pickup_time'] ?? '').toString(),
      pickupLat: doubleValue(json['pickup_lat']),
      pickupLng: doubleValue(json['pickup_lng']),
      dropoffLat: doubleValue(json['dropoff_lat']),
      dropoffLng: doubleValue(json['dropoff_lng']),
      driverId: intValue(json['driver_id']),
      vehicleTypeId: intValue(json['vehicle_type_id']),
      passengers: intValue(json['passengers']),
      total: doubleValue(json['total']) ?? 0,
      paymentMethod: (json['payment_method'] ?? '').toString(),
      customerName: (customer['name'] ?? '').toString(),
      customerPhone: (customer['phone'] ?? '').toString(),
      customerEmail: (customer['email'] ?? '').toString(),
      driverNotes: (json['driver_notes'] ?? '').toString(),
      additionalNotes: (json['additional_notes'] ?? '').toString(),
      flightNumber: (json['flight_number'] ?? '').toString(),
      terminal: (json['terminal'] ?? '').toString(),
      jobType: jobType,
      jobTypeLabel: (json['job_type_label'] ?? _labelForJobType(jobType)).toString(),
      operationsEnabled: operationsEnabled || jobType != 'ride',
      operationsSummary: OperationsSummary.fromJson(mapValue(operations['summary'])),
      podSettings: OperationsPodSettings.fromJson(mapValue(operations['pod'])),
      stops: stops,
    );
  }

  static String _labelForJobType(String type) => switch (type) {
        'delivery' => 'Delivery',
        'collection' => 'Collection',
        'service' => 'Service',
        'multi_stop' => 'Multi-stop',
        _ => 'Ride',
      };
}
