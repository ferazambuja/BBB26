from pathlib import Path

from votalhada_ocr_batch_validate import select_validation_images


def test_select_validation_images_latest_capture_prefers_latest_timestamp_group():
    images = [
        Path("consolidados_2026-03-09_21-06-01.png"),
        Path("consolidados_2_2026-03-09_21-06-01.png"),
        Path("consolidados_5_2026-03-09_21-06-01.png"),
        Path("consolidados_2026-03-10_21-06-00.png"),
        Path("consolidados_2_2026-03-10_21-06-00.png"),
        Path("consolidados_5_2026-03-10_21-06-00.png"),
        Path("consolidados_final.png"),
    ]

    selected = select_validation_images(images, scope="latest-capture")

    assert [path.name for path in selected] == [
        "consolidados_2026-03-10_21-06-00.png",
        "consolidados_2_2026-03-10_21-06-00.png",
        "consolidados_5_2026-03-10_21-06-00.png",
    ]


def test_select_validation_images_latest_capture_falls_back_to_all_when_no_timestamps():
    images = [
        Path("consolidados.png"),
        Path("consolidados_2.png"),
        Path("consolidados_5.png"),
    ]

    selected = select_validation_images(images, scope="latest-capture")

    assert [path.name for path in selected] == [path.name for path in images]


def test_select_validation_images_full_history_keeps_all_images():
    images = [
        Path("consolidados_2026-03-09_21-06-01.png"),
        Path("consolidados_5_2026-03-10_21-06-00.png"),
        Path("consolidados_final.png"),
    ]

    selected = select_validation_images(images, scope="full-history")

    assert [path.name for path in selected] == [path.name for path in images]
