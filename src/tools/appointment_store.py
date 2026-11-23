from pydantic import BaseModel


class AppointmentSlot(BaseModel):
    slot_id: str
    datetime_label: str
    is_booked: bool = False


_MOCK_SLOTS: list[AppointmentSlot] = [
    AppointmentSlot(slot_id="S1", datetime_label="Today 14:00"),
    AppointmentSlot(slot_id="S2", datetime_label="Today 16:30"),
    AppointmentSlot(slot_id="S3", datetime_label="Tomorrow 09:00"),
    AppointmentSlot(slot_id="S4", datetime_label="Tomorrow 11:30"),
]


def get_available_slots() -> list[AppointmentSlot]:
    return [slot for slot in _MOCK_SLOTS if not slot.is_booked]


def book_slot(slot_id: str) -> AppointmentSlot:
    for slot in _MOCK_SLOTS:
        if slot.slot_id == slot_id:
            if slot.is_booked:
                raise ValueError(f"Slot {slot_id} is already booked.")
            slot.is_booked = True
            return slot
    raise ValueError(f"Slot {slot_id} does not exist.")
