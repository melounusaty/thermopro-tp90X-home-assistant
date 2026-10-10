from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.helpers.device_registry import format_mac

DOMAIN = "tp90x_multi"

MODEL_OPTIONS = {
    "TP902": "TP902",
    "TP904 (experimental)": "TP904",
    "TP920": "TP920",
}

# Map Bluetooth advertisement names to device models
DEVICE_NAME_MAP = {
    "Thermopro": "TP902",  # Original naming for older devices
    "TP902": "TP902",
    "TP904": "TP904",
    "TP920": "TP920",
}


class TP90XConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ThermoPro TP90X devices."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, str] | None = None):
        if user_input is not None:
            mac = format_mac(user_input["mac"])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            selected_label = user_input["model"]
            model = MODEL_OPTIONS[selected_label]
            title = f"ThermoPro {model}"
            if model == "TP904":
                title = f"{title} (experimental)"

            return self.async_create_entry(
                title=title,
                data={
                    "mac": mac,
                    "name": user_input["name"],
                    "model": model,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("mac"): str,
                    vol.Optional("name", default="ThermoPro Thermometer"): str,
                    vol.Required("model", default="TP902"): vol.In(list(MODEL_OPTIONS)),
                }
            ),
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.FlowResult:
        """Handle Bluetooth discovery of ThermoPro devices."""
        # Get the device name from the advertisement
        device_name = discovery_info.name
        
        # Check if this is a known ThermoPro device
        if device_name not in DEVICE_NAME_MAP:
            return self.async_abort(reason="not_supported")
        
        # Get the model based on the device name
        model = DEVICE_NAME_MAP[device_name]
        
        # Use MAC address as unique ID
        mac = discovery_info.address
        await self.async_set_unique_id(format_mac(mac))
        self._abort_if_unique_id_configured()
        
        # Create entry with discovered model
        title = f"ThermoPro {model}"
        if model == "TP904":
            title = f"{title} (experimental)"
        
        return self.async_create_entry(
            title=title,
            data={
                "mac": format_mac(mac),
                "name": f"ThermoPro {model}",
                "model": model,
            },
        )
        
