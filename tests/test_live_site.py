import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
p=Path(__file__).resolve().parents[1]/'live/ingest.py'
s=importlib.util.spec_from_file_location('ingest',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
NOW=datetime(2026,10,8,23,0,tzinfo=timezone.utc)
def row(**kw):
 d={'time_tag':'2026-10-08T22:59:00','active':True,'source':'OBSERVED-ID','bz_gsm':-3,'bt':6,'overall_quality':0};d.update(kw);return d
class LiveTests(unittest.TestCase):
 def test_valid_preserves_source_flags(self):
  x,_,_=m.normalize([row()],['bz_gsm','bt'],NOW);self.assertEqual(x[0]['source'],'OBSERVED-ID');self.assertEqual(x[0]['provider_flags'],{'overall_quality':0})
 def test_inactive_not_selected(self):
  with self.assertRaises(ValueError):m.normalize([row(active=False)],['bz_gsm','bt'],NOW)
 def test_malformed(self):
  for x in [None,{},[],[row(active='true')],[row(time_tag='bad')]]:
   with self.assertRaises(ValueError):m.normalize(x,['bz_gsm','bt'],NOW)
 def test_future(self):
  with self.assertRaises(ValueError):m.normalize([row(time_tag='2026-10-09T00:00:00')],['bz_gsm','bt'],NOW)
 def test_sentinels(self):
  for v in [None,-9999,float('nan'),True]:
   with self.assertRaises(ValueError):m.normalize([row(bz_gsm=v)],['bz_gsm','bt'],NOW)
 def test_negative_magnitude(self):
  with self.assertRaises(ValueError):m.normalize([row(bt=-3)],['bt'],NOW)
 def test_duplicates_conflict(self):
  with self.assertRaises(ValueError):m.normalize([row(),row(bz_gsm=4)],['bz_gsm','bt'],NOW)
 def test_identical_duplicate(self):
  x,_,_=m.normalize([row(),row()],['bz_gsm','bt'],NOW);self.assertEqual(len(x),1)
 def test_atomic_failure_preserves(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'snapshot.json';m.publish(p,{'old':True})
   with self.assertRaises(ValueError):m.publish(p,{'v':float('nan')})
   self.assertEqual(json.loads(p.read_text()),{'old':True})
 def test_no_predictions(self):
  def down(url):
   r=row(proton_speed=400,proton_density=5);return json.dumps([r]).encode(),200
  d=m.snapshot(NOW,down);self.assertFalse(d['prediction']['available']);self.assertEqual(d['mode'],'observations_only')
 def test_stale(self):
  def down(url):return json.dumps([row(time_tag='2026-10-08T21:00:00',proton_speed=400,proton_density=5)]).encode(),200
  self.assertTrue(m.snapshot(NOW,down)['feeds']['mag']['stale_at_fetch'])
if __name__=='__main__':unittest.main()
