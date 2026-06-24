import math
import unittest

from geopredict_ml.grid import (
    AnalysisAreaTooLargeError,
    polygon_to_grid_cells,
    suggest_h3_resolution,
    validate_polygon_geometry,
)
from geopredict_ml.osm import build_overpass_query


def circle_geometry(lon: float = 37.62, lat: float = 55.76, radius_m: float = 1_000) -> dict:
    ring = []
    for index in range(64):
        angle = index / 64 * 2 * math.pi
        ring.append(
            [
                lon + (radius_m / (111_320 * math.cos(math.radians(lat)))) * math.sin(angle),
                lat + (radius_m / 111_320) * math.cos(angle),
            ]
        )
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


class StabilityTest(unittest.TestCase):
    def test_circle_overpass_query_is_simplified(self):
        query = build_overpass_query(circle_geometry())

        self.assertLess(len(query), 10_000)
        self.assertLessEqual(query.count("poly:"), 8)

    def test_rejects_non_finite_and_out_of_range_coordinates(self):
        invalid_geometries = [
            {
                "type": "Polygon",
                "coordinates": [[[float("nan"), 55], [38, 55], [38, 56], [float("nan"), 55]]],
            },
            {
                "type": "Polygon",
                "coordinates": [[[200, 95], [201, 95], [201, 96], [200, 95]]],
            },
        ]

        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                with self.assertRaises(ValueError):
                    validate_polygon_geometry(geometry)

    def test_rejects_degenerate_and_self_intersecting_polygons(self):
        invalid_geometries = [
            {"type": "Polygon", "coordinates": [[[37, 55], [37, 55], [37, 55], [37, 55]]]},
            {
                "type": "Polygon",
                "coordinates": [[[37, 55], [38, 56], [38, 55], [37, 56], [37, 55]]],
            },
        ]

        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                with self.assertRaises(ValueError):
                    validate_polygon_geometry(geometry)

    def test_large_area_is_rejected_instead_of_silent_truncation(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[37.0, 55.0], [38.0, 55.0], [38.0, 56.0], [37.0, 56.0], [37.0, 55.0]]],
        }

        with self.assertRaises(AnalysisAreaTooLargeError):
            polygon_to_grid_cells(geometry, resolution=9, max_cells=1_000)

    def test_suggests_coarser_h3_resolution_for_large_area(self):
        self.assertEqual(
            suggest_h3_resolution(estimated_cells=1_521, max_cells=1_000, resolution=9),
            8,
        )

    def test_does_not_suggest_resolution_below_supported_range(self):
        self.assertIsNone(
            suggest_h3_resolution(estimated_cells=9_000, max_cells=1_000, resolution=7)
        )


if __name__ == "__main__":
    unittest.main()
