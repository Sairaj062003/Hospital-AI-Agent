"""Static hospital information - not database-backed, unlike db.py.

This is config-style data (hours, location, policies) that changes rarely,
so it lives as a plain dict rather than a Postgres table.
"""

_HOSPITAL_INFO = {
    "name": "HealthCare AI Assistant Hospital",
    "visiting_hours": "Monday to Saturday, 9:00 AM to 7:00 PM. Closed on Sundays and public holidays.",
    "emergency_contact": "0223567568 (24/7 emergency line)",
    "location": "123 Wellness Avenue, Central District",
    "insurance_policy": "We accept most major health insurance providers. Please bring your insurance "
                         "card and a valid ID at the time of your appointment. Contact our billing desk "
                         "to confirm coverage for a specific provider.",
    "parking": "Free parking is available in the hospital's basement and ground-level lots.",
}


def get_hospital_info() -> dict:
    return dict(_HOSPITAL_INFO)
