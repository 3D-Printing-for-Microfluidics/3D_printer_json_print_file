"""Printer hardware compatibility checks for validated print settings."""

import re
from copy import deepcopy


def _get_effective_image_settings(print_settings, layer):
	defaults = print_settings.get("Default layer settings", {}).get("Image settings", {})
	layer_specific_settings = layer.get("Image settings list")

	final_settings = []
	if layer_specific_settings is not None:
		for settings in layer_specific_settings:
			merged = deepcopy(defaults)
			merged.update(settings)
			final_settings.append(merged)
	if not final_settings:
		final_settings.append(deepcopy(defaults))
	return final_settings


def _get_required_light_engine(settings, config_dict):
	if "Light engine" in settings:
		return settings["Light engine"]
	if config_dict.get("light_engines"):
		return config_dict["light_engines"][0]
	return None


def _parse_light_engine_name(light_engine):
	if not light_engine:
		return None, None
	match = re.match(r"^\s*(.+?)\s*\((\d+)\s*nm\)\s*$", str(light_engine))
	if match:
		return match.group(1), int(match.group(2))
	return light_engine, None


def validate_printer_compatibility(print_settings, config_dict):
	"""Validate that the current printer hardware supports the print settings."""
	if not print_settings or "Layers" not in print_settings:
		return

	# Validate vacuum support
	vacuum_settings = (
		print_settings.get("Special print techniques", {})
		.get("Print under vacuum", {})
	)
	if vacuum_settings.get("Enable vacuum"):
		if "mks" not in config_dict:
			raise ValueError("Print job requires vacuum, but this printer has no MKS controller.")

	# Validate light engines, wavelengths, and XY stage usage
	xy_offsets_used = False
	for layer in print_settings.get("Layers", []):
		for settings in _get_effective_image_settings(print_settings, layer):
			light_engine_label = _get_required_light_engine(settings, config_dict)
			if light_engine_label is None:
				raise ValueError("No light engine specified and none configured for this printer.")

			light_engine, legacy_wavelength = _parse_light_engine_name(light_engine_label)

			if light_engine not in config_dict.get("light_engines", []):
				raise ValueError(f"Light engine '{light_engine_label}' is not available on this printer.")

			engine_cfg = config_dict.get(light_engine)
			leds_nm = engine_cfg.get("leds_nm", []) if engine_cfg else []
			wavelength = legacy_wavelength
			led_index = 0

			if "Light engine wavelength (nm)" in settings:
				wavelength = settings["Light engine wavelength (nm)"]
				if not engine_cfg or "leds_nm" not in engine_cfg:
					raise ValueError(
						f"Light engine '{light_engine_label}' has no configured wavelengths."
					)
				if wavelength not in leds_nm:
					raise ValueError(
						f"Light engine '{light_engine_label}' does not support {wavelength} nm."
					)
				led_index = leds_nm.index(wavelength)
			elif wavelength is not None:
				if not engine_cfg or "leds_nm" not in engine_cfg:
					raise ValueError(
						f"Light engine '{light_engine_label}' has no configured wavelengths."
					)
				if wavelength not in leds_nm:
					raise ValueError(
						f"Light engine '{light_engine_label}' does not support {wavelength} nm."
					)
				led_index = leds_nm.index(wavelength)

			corrected = settings.get(
				"Do light grayscale correction",
				settings.get("Do grayscale correction", False),
			)
			if corrected:
				if not leds_nm:
					raise ValueError(
						f"Light engine '{light_engine_label}' has no configured wavelengths for grayscale correction."
					)
				if wavelength is None and len(leds_nm) > 1:
					raise ValueError(
						"Grayscale correction requires an explicit light engine wavelength."
					)
				grayscale_images = engine_cfg.get("grayscale_correction_image") if engine_cfg else None
				if (
					not grayscale_images
					or len(grayscale_images) <= led_index
					or not grayscale_images[led_index]
				):
					wavelength_label = (
						leds_nm[led_index] if led_index < len(leds_nm) else "unknown"
					)
					raise ValueError(
						f"Light engine '{light_engine_label}' has no grayscale correction image for {wavelength_label} nm."
					)

			if settings.get("Image x offset (um)") or settings.get("Image y offset (um)"):
				if settings.get("Image x offset (um)", 0) != 0 or settings.get("Image y offset (um)", 0) != 0:
					xy_offsets_used = True

	if xy_offsets_used:
		stages = config_dict.get("stages", {})
		if not stages.get("xy_stage"):
			raise ValueError("Print job uses X/Y offsets but this printer has no XY stage.")