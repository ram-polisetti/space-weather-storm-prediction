import unittest,json,pathlib,datetime as dt,base64,re,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
class EvidenceTests(unittest.TestCase):
 def setUp(self): self.e=json.loads((ROOT/'web/evidence.json').read_text())
 def test_schema_cases(self): self.assertEqual(set(self.e['cases']),{'2015','2017','2024'})
 def test_no_raw_dst(self): self.assertNotRegex((ROOT/'web/evidence.json').read_text().lower(),r'"(?:observed|predicted|dst|dst1800|dst_kyoto)"\s*:')
 def test_ground_real_intervals(self):
  for c in self.e['cases'].values():
   for r in c['ground']:
    a,b=map(dt.datetime.fromisoformat,[r['start'],r['end']]);self.assertEqual(b-a,dt.timedelta(hours=3));self.assertEqual(a.minute,0);self.assertEqual(a.hour%3,0);self.assertEqual(r['status'],'def');self.assertTrue(0<=r['kp']<=9);self.assertTrue(0<=r['ap']<=400)
 def test_wind_missing_not_fill(self):
  for c in self.e['cases'].values():
   times=[dt.datetime.fromisoformat(r['time']) for r in c['wind']];self.assertEqual(times,sorted(set(times)))
   for r in c['wind']:
    self.assertEqual(dt.datetime.fromisoformat(r['time']).minute,30)
    self.assertTrue(r['bz'] is None or abs(r['bz'])<999);self.assertTrue(r['speed'] is None or 0<r['speed']<9999)
 def test_same_utc_bounds(self):
  for c in self.e['cases'].values():
   a,b=map(dt.datetime.fromisoformat,[c['start'],c['end']]);self.assertTrue(all(a<=dt.datetime.fromisoformat(r['time'])<=b for r in c['wind']))
 def test_images_hash_and_no_build_artifacts(self):
  s=(ROOT/'web/index.html').read_text();images=re.findall('data:image/webp;base64,([A-Za-z0-9+/=]+)',s);self.assertEqual(len(images),3);self.assertEqual({hashlib.sha256(base64.b64decode(i)).hexdigest() for i in images},{c['image_sha256'] for c in self.e['cases'].values()})
 def test_labels_and_fault_path(self):
  s=(ROOT/'web/index.html').read_text();self.assertIn('CC BY 4.0',s);self.assertIn('not independent validation',s);self.assertIn('Historical measurement details unavailable',s);self.assertIn('No live forecast',s);self.assertIn('value="2024"',s)
if __name__=='__main__':unittest.main()
