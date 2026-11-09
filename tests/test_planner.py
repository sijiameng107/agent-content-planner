import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from src.planner import BusinessTools,MockModel,ROOT,run,validate
F=json.loads((ROOT/'data/catalog.json').read_text());R=json.loads((ROOT/'data/request.json').read_text())
class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'db')
    def tearDown(self):self.tmp.cleanup()
    def go(self,**kw):return run(kw.pop('request',R),F,MockModel(),self.db,**kw)
    def test_replan(self):
        r=self.go();self.assertEqual(r['status'],'completed');self.assertEqual(r['total_cost'],8);self.assertEqual([e['total_cost'] for e in r['state']['estimates']],[12,8])
    def test_normal(self):self.assertEqual(self.go(request={**R,'budget':15})['total_cost'],12)
    def test_missing_budget(self):self.assertEqual(self.go(request={**R,'budget':None})['reason'],'missing_input')
    def test_missing_deadline(self):self.assertEqual(self.go(request={**R,'deadline':None})['reason'],'missing_input')
    def test_invalid_budget(self):self.assertIsNotNone(validate({**R,'budget':True}));self.assertIsNotNone(validate({**R,'budget':-1}))
    def test_invalid_time(self):self.assertIsNotNone(validate({**R,'deadline':'2026-11-10T09:20:00'}))
    def test_budget_impossible(self):
        r=self.go(request={**R,'budget':7});self.assertEqual(r['status'],'incomplete');self.assertIsNone(r['state']['saved_plan']);self.assertEqual(r['state']['estimates'][-1]['budget_gap'],1)
    def test_deadline(self):
        r=self.go(request={**R,'deadline':'2026-11-10T09:03:00+08:00'});self.assertEqual(r['status'],'incomplete');self.assertGreater(r['state']['estimates'][-1]['deadline_gap_minutes'],0)
    def test_duplicate(self):
        first=self.go();second=self.go();self.assertEqual(first['state'],second['state']);self.assertEqual(second['total_cost'],8)
        with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
    def test_resume(self):
        a=self.go(failure='generate_always');self.assertEqual(a['state']['steps']['generate_script:basic'],'failed');b=self.go();self.assertEqual(b['status'],'completed');self.assertEqual(b['total_cost'],8);self.assertEqual(sum(e['cost'] for e in b['state']['events'] if e['step']=='search_materials'),2);self.assertEqual(b['state']['events'][1]['status'],'failed')
    def test_transient_failure(self):
        r=self.go(failure='generate_once');self.assertEqual(r['status'],'completed');self.assertEqual(r['elapsed_minutes'],6);self.assertEqual(r['total_cost'],8)
    def test_save_failure(self):
        r=self.go(failure='save_always');self.assertEqual(r['reason'],'tool_failure');self.assertIn('script:basic',r['state']['results']);self.assertIsNone(r['state']['saved_plan'])
    def test_step_limit(self):self.assertEqual(self.go(max_steps=1)['reason'],'limit_reached')
    def test_save_without_script(self):
        t=BusinessTools(R,F,self.db);self.assertEqual(t.call('save_plan',{'variant':'basic'})['error'],'successful_script_required');t.close()
    def test_generation_cost_gate(self):
        t=BusinessTools(R,F,self.db);t.call('search_materials',{});t.call('estimate_cost',{'variant':'premium'});self.assertEqual(t.call('generate_script',{'variant':'premium'})['error'],'constraint_exceeded');self.assertEqual(t.state['spent'],2);t.close()
    def test_no_materials(self):self.assertEqual(self.go(request={**R,'theme':'unmatched'})['reason'],'no_materials')
    def test_invalid_tool(self):
        t=BusinessTools(R,F,self.db);self.assertIn('error',t.call('publish',{}));t.close()
    def test_catalog_changes_not_stale_cache(self):
        a=BusinessTools(R,F,self.db);f=copy.deepcopy(F);f['variants']['basic']['cost']=7;b=BusinessTools(R,f,self.db);self.assertNotEqual(a.key,b.key);a.close();b.close()
if __name__=='__main__':unittest.main()
