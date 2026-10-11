/// Optional clinical context (design-v1 Section 7.3). In memory only.
class ClinicalContext {
  int? age;
  String? sex; // male | female | other
  final Set<String> complaints = {};
  String? complaintOther;
  bool? chestPainOngoing;
  int? sbp;
  int? dbp;
  int? heartRate;
  int? spo2;
  final Set<String> conditions = {};

  static const complaintOptions = {
    'chest_pain': 'Chest pain',
    'breathlessness': 'Breathlessness',
    'syncope': 'Syncope / near-syncope',
    'palpitations': 'Palpitations',
    'dizziness': 'Dizziness',
    'other': 'Other',
  };

  static const conditionOptions = {
    'hypertension': 'Hypertension',
    'diabetes': 'Diabetes',
    'known_heart_disease': 'Known heart disease',
    'ckd': 'CKD',
  };

  Map<String, dynamic> toJson() => {
        'age': age,
        'sex': sex,
        'complaints': complaints.toList(),
        'complaint_other': (complaintOther?.trim().isEmpty ?? true) ? null : complaintOther!.trim(),
        'chest_pain_ongoing': complaints.contains('chest_pain') ? chestPainOngoing : null,
        'sbp': sbp,
        'dbp': dbp,
        'heart_rate': heartRate,
        'spo2': spo2,
        'conditions': conditions.toList(),
      };
}
