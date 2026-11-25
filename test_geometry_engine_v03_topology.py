import unittest
from engine.geometry_engine_v03 import compute_usable_area, GeometryInputError

class GeometryEngineV03Tests(unittest.TestCase):
    def test_polygon_with_hole(self):
        case = {
            "field": {"type":"Polygon", "coordinates":[
                [[0,0],[20,0],[20,20],[0,20],[0,0]],
                [[8,8],[12,8],[12,12],[8,12],[8,8]],
            ]},
            "obstacles":[],
            "settings":{"boundary_setback_m":1,"obstacle_buffer_m":0,"quad_segs":64,"geometry_tolerance_m":1e-7},
        }
        out=compute_usable_area(case)
        self.assertTrue(out['result']['geometry']['usable_geometry_valid'])
        self.assertGreater(out['result']['areas_m2']['usable_planting_area'],0)
        self.assertEqual(out['result']['geometry']['usable_area_type'],'Polygon')

    def test_disjoint_multipolygon(self):
        case = {
            "field": {"type":"MultiPolygon", "coordinates":[
                [[[0,0],[10,0],[10,10],[0,10],[0,0]]],
                [[[20,0],[30,0],[30,10],[20,10],[20,0]]],
            ]},
            "obstacles":[],
            "settings":{"boundary_setback_m":1,"obstacle_buffer_m":0,"quad_segs":64,"geometry_tolerance_m":1e-7},
        }
        out=compute_usable_area(case)
        self.assertEqual(out['result']['geometry']['usable_area_type'],'MultiPolygon')
        self.assertEqual(out['result']['geometry']['usable_component_count'],2)

    def test_polygonal_obstacle_and_hole(self):
        case = {
            "field": {"type":"Polygon", "coordinates":[[[0,0],[20,0],[20,20],[0,20],[0,0]]]},
            "obstacles":[{"name":"pond","type":"Polygon","coordinates":[[[8,8],[12,8],[12,12],[8,12],[8,8]]]}],
            "settings":{"boundary_setback_m":1,"obstacle_buffer_m":1,"quad_segs":64,"geometry_tolerance_m":1e-7},
        }
        out=compute_usable_area(case)
        self.assertTrue(out['result']['status']['obstacle_clearance_verified'])
        self.assertTrue(out['result']['geometry']['usable_geometry_valid'])

    def test_invalid_multipolygon_rejected(self):
        case = {
            "field": {"type":"MultiPolygon", "coordinates":[
                [[[0,0],[10,0],[10,10],[0,10],[0,0]]],
                [[[5,5],[15,5],[15,15],[5,15],[5,5]]],
            ]}, "obstacles":[], "settings":{}
        }
        with self.assertRaises(GeometryInputError):
            compute_usable_area(case)

if __name__ == '__main__':
    unittest.main(verbosity=2)
