# Unique-id suffixes of entities that were renamed: old -> new.
RENAMED_UNIQUE_ID_SUFFIXES = {
    # The UPS measures its inverter (output) frequency, not the mains.
    "_input_frequency_sensor": "_output_frequency_sensor",
}


def migrated_unique_id(unique_id):
    """Return the current unique id of a renamed entity, or None if unchanged."""
    for old, new in RENAMED_UNIQUE_ID_SUFFIXES.items():
        if unique_id.endswith(old):
            return unique_id.removesuffix(old) + new
    return None
