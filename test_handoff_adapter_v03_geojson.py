import json
import unittest
from pathlib import Path
from adapter.handoff_adapter_v03 import adapt_project, HandoffError
from engine.geometry_engine_v03 import compute_usable_area

ROOT=Path(__file__).resolve().parents[1]

class AdapterV03GeoJSONTests(unittest.TestCase):
    def test_polygon_with_hole_passes_to_geometry_engine(self):
        app=json.loads((ROOT/'adapter'/'sample_app_project.json').read_text())
        app['boundary'].pop('sourceVertices');app['boundary'].pop('workingVertices')
        shell=[[500000,1000000],[500030,1000000],[500030,1000030],[500000,1000030],[500000,1000000]]
        hole=[[500010,1000010],[500015,1000010],[500015,1000015],[500010,1000015],[500010,1000010]]
        geom={'type':'Polygon','coordinates':[shell,hole]}
        app['boundary']['sourceGeometry']=geom;app['boundary']['workingGeometry']=geom
        profile=json.loads((ROOT/'adapter'/'sample_site_profile.json').read_text())
        case,audit=adapt_project(app,profile,mode='exploratory')
        out=compute_usable_area(case)
        self.assertEqual(case['field']['geometry']['type'],'Polygon')
        self.assertEqual(audit['adapter'],'PROUVE Spatial Handoff Adapter V0.3.1')
        self.assertTrue(out['result']['geometry']['usable_geometry_valid'])

    def test_multipolygon_with_geojson_obstacle(self):
        app=json.loads((ROOT/'adapter'/'sample_app_project.json').read_text())
        app['boundary'].pop('sourceVertices');app['boundary'].pop('workingVertices')
        mp={'type':'MultiPolygon','coordinates':[
            [[[500000,1000000],[500020,1000000],[500020,1000020],[500000,1000020],[500000,1000000]]],
            [[[500030,1000000],[500050,1000000],[500050,1000020],[500030,1000020],[500030,1000000]]],
        ]}
        app['boundary']['sourceGeometry']=mp;app['boundary']['workingGeometry']=mp
        profile=json.loads((ROOT/'adapter'/'sample_site_profile.json').read_text())
        profile['obstacles']=[{'name':'pond','geometry':{'type':'Polygon','coordinates':[
            [[500005,1000005],[500008,1000005],[500008,1000008],[500005,1000008],[500005,1000005]]
        ]}}]
        case,audit=adapt_project(app,profile,mode='exploratory')
        out=compute_usable_area(case)
        self.assertEqual(case['field']['geometry']['type'],'MultiPolygon')
        self.assertIn('geometry',case['obstacles'][0])
        self.assertEqual(out['result']['geometry']['usable_area_type'],'MultiPolygon')

    def test_invalid_coordinate_rejected_by_adapter_gate(self):
        app=json.loads((ROOT/'adapter'/'sample_app_project.json').read_text())
        app['boundary'].pop('sourceVertices');app['boundary'].pop('workingVertices')
        bad={'type':'Polygon','coordinates':[[[0,0],[1,float('nan')],[1,1],[0,1],[0,0]]]}
        app['boundary']['sourceGeometry']=bad;app['boundary']['workingGeometry']=bad
        profile=json.loads((ROOT/'adapter'/'sample_site_profile.json').read_text())
        with self.assertRaises(HandoffError):
            adapt_project(app,profile,mode='exploratory')

if __name__=='__main__': unittest.main(verbosity=2)
