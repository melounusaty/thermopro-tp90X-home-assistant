"""TP920 concrete model implementation.

The TP920 has 2 physical probes but advertises and broadcasts using the
TP902 6-channel frame layout (cmd 0x30, payload length 0x0f = 15 bytes).
Physical probes are mapped into non-contiguous broadcast slots:

    physical probe 1  →  broadcast slot 1  (payload offset 7..9)
    physical probe 2  →  broadcast slot 3  (payload offset 11..13)

Empirically verified 2026-05-30 by heating one probe in hand and observing
the BCD value drift only in slot 3. Slots 0, 2, 4, 5 are always 0xFFFF.

Alarm-set and alarm-get use 1-indexed channel numbers (1 and 2) like the
TP902, not the broadcast slot indices.
"""

from .tp90xbase import (
    TP90xBase,
    Temperature,
    TemperatureBroadcast,
    TemperatureActual,
    _decode_temp_bcd,
    _parse_units,
)


class TP920(TP90xBase):
    """ThermoPro TP920 protocol model."""

    NUM_PROBES = 2

    # 0-indexed broadcast slot per physical probe. Index 0 = physical probe 1.
    PROBE_BROADCAST_SLOTS = (1, 3)

    # TP920 uses TP902's 15-byte broadcast payload even though it only has
    # 2 active probes. The base class assumes pkt_len == 3 + NUM_PROBES*2;
    # we override _parse_packet entirely for the broadcast / actual cmds
    # rather than fight the length math.
    _BROADCAST_PAYLOAD_LEN = 0x0F  # = 15, same as TP902
    _ACTUAL_PAYLOAD_LEN = 0x0E     # = 14, same as TP902 (probe_count + alarms + 6*2)

    @classmethod
    def model_name(cls):
        """Model Name - TP920."""
        return "TP920"

    def _parse_packet(self, cmd, data):
        """Parse TP920 packets.

        Broadcast and actual frames carry a 6-channel grid; we extract only
        slots PROBE_BROADCAST_SLOTS into a 2-probe result. All other commands
        delegate to the base parser (alarms, status, firmware, auth) which
        use NUM_PROBES = 2 length checks.
        """
        pkt_len = data[1]

        if (
            cmd == self.RX_TEMP_BROADCAST
            and pkt_len == self._BROADCAST_PAYLOAD_LEN
            and len(data) >= 2 + pkt_len
        ):
            battery = data[2]
            units = _parse_units(data[3])
            alarms = data[4]
            temps = []
            for i, slot in enumerate(self.PROBE_BROADCAST_SLOTS):
                offset = 5 + slot * 2
                val = _decode_temp_bcd(data[offset:offset + 2])
                temps.append(Temperature(i + 1, val))
            return TemperatureBroadcast(battery, units, alarms, temps)

        if (
            cmd == self.RX_TEMP_ACTUAL
            and pkt_len == self._ACTUAL_PAYLOAD_LEN
            and len(data) >= 2 + pkt_len
        ):
            probe_count = data[2]
            alarms = data[3]
            temps = []
            for i, slot in enumerate(self.PROBE_BROADCAST_SLOTS):
                offset = 4 + slot * 2
                val = _decode_temp_bcd(data[offset:offset + 2])
                temps.append(Temperature(i + 1, val))
            return TemperatureActual(probe_count, alarms, temps)

        # Alarm / status / firmware / auth — base parser handles these with
        # length math based on NUM_PROBES = 2, which is correct for the
        # alarm responses (channel 1 or 2).
        return super()._parse_packet(cmd, data)
