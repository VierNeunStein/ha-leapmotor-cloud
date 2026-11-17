"""Base classes shared by all platforms."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import VehicleInfo
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator, VehicleData


class LeapmotorEntity(CoordinatorEntity[LeapmotorCoordinator]):
    """An entity that belongs to one vehicle."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        key: str,
        *,
        right: int | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.vin = vin
        self._attr_unique_id = f"{vin}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = coordinator.device_info(vin)
        if right is not None and coordinator.vehicles[vin].has_right(right) is False:
            # The account was not granted this function: keep it out of the way.
            self._attr_entity_registry_enabled_default = False

    @property
    def vehicle(self) -> VehicleData:
        """Return the current data of the vehicle."""
        return self.coordinator.data[self.vin]

    @property
    def info(self) -> VehicleInfo:
        """Return the static description of the vehicle."""
        return self.coordinator.vehicles[self.vin]

    @property
    def state_data(self) -> dict[str, Any]:
        """Return the parsed vehicle state."""
        return self.vehicle.state

    @property
    def available(self) -> bool:
        """Return whether data for this vehicle exists."""
        return super().available and self.vin in (self.coordinator.data or {})


@callback
def async_add_vehicle_entities[D: EntityDescription](
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    descriptions: Iterable[D],
    create: Callable[[LeapmotorCoordinator, str, D], Entity],
    supported: Callable[[LeapmotorCoordinator, VehicleData, D], bool],
) -> None:
    """Create entities per vehicle, now and whenever new data makes them possible.

    Models differ in what they report.  An entity is created the first time
    its value shows up, so nobody ends up with rows that stay "unknown".
    """
    coordinator = entry.runtime_data
    descriptions = tuple(descriptions)
    known: set[tuple[str, str]] = set()

    @callback
    def _discover() -> None:
        new: list[Entity] = []
        for vin, data in (coordinator.data or {}).items():
            for description in descriptions:
                ident = (vin, description.key)
                if ident in known or not supported(coordinator, data, description):
                    continue
                known.add(ident)
                new.append(create(coordinator, vin, description))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))
