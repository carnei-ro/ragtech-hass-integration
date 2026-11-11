from custom_components.ragtech.utils.migration import migrated_unique_id


def test_frequency_sensor_moves_to_its_output_unique_id():
    assert (
        migrated_unique_id("ragtech_01JABC_input_frequency_sensor")
        == "ragtech_01JABC_output_frequency_sensor"
    )


def test_other_unique_ids_are_left_alone():
    for unique_id in (
        "ragtech_01JABC_output_frequency_sensor",
        "ragtech_01JABC_input_voltage_sensor",
        "ragtech_01JABC_input_current_sensor",
        "ragtech_01JABC_battery_aged_binary_sensor",
    ):
        assert migrated_unique_id(unique_id) is None
