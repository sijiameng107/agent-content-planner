"""Produce actual run outputs and acceptance checks; modes are never mixed."""
import argparse,copy,json,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.planner import run,MockModel,ROOT
from src.model import LiveModel,ModelError

def evaluate(mode,output):
    fixture=json.loads((ROOT/'data/catalog.json').read_text());base=json.loads((ROOT/'data/request.json').read_text())
    model=LiveModel() if mode=='live' else MockModel();out=Path(output);out.mkdir(parents=True,exist_ok=True);records=[]
    cases=[('normal',{},'none'),('missing_budget',{'budget':None},'none'),('missing_deadline',{'deadline':None},'none'),('tool_failure',{},'generate_always'),('budget_replan',{},'none'),('budget_impossible',{'budget':7},'none'),('deadline_impossible',{'deadline':'2026-11-10T09:03:00+08:00'},'none'),('duplicate_first',{},'none'),('duplicate_repeat',{},'none'),('resume_first',{},'generate_always'),('resume_second',{},'none'),('transient_failure',{},'generate_once'),('save_failure',{},'save_always')]
    with tempfile.TemporaryDirectory() as tmp:
        for name,patch,failure in cases:
            request={**base,**patch}
            if name=='normal':request['budget']=15
            if name=='budget_replan':request['initial_variant']='premium'
            group='duplicate' if name.startswith('duplicate') else 'resume' if name.startswith('resume') else name
            db=str(Path(tmp)/group);result=run(request,fixture,model,db,failure=failure)
            state=result.get('state',{});saved=state.get('saved_plan');is_incomplete=name in ('missing_budget','missing_deadline','tool_failure','budget_impossible','deadline_impossible','resume_first','save_failure')
            checks={'expected_status':result['status']==('incomplete' if is_incomplete else 'completed'),'cost_within_budget':request['budget'] is None or result['total_cost']<=request['budget']}
            if not is_incomplete:
                checks['saved']=bool(saved)
                checks['deadline']=bool(saved) and saved['projected_completion']<=request['deadline']
            else:checks['not_saved']=not saved
            if name in ('budget_replan','duplicate_first','duplicate_repeat','resume_second','transient_failure'):
                checks['cost_8']=result['total_cost']==8
            if name=='budget_replan':
                estimates=state.get('estimates',[])
                # This designated evaluation starts from a premium preference; see input instruction below.
                checks['observed_12_then_8']=any(e['total_cost']==12 and not e['feasible'] for e in estimates) and any(e['total_cost']==8 and e['feasible'] for e in estimates)
            if name in ('tool_failure','resume_first','save_failure'):
                checks['failed_step_recorded']=any(e['status']=='failed' for e in state.get('events',[]))
                checks['materials_retained']=bool(state.get('results',{}).get('materials'))
            if name=='duplicate_repeat':
                checks['no_new_charge']=result['total_cost']==result['initial_state']['spent']
                with sqlite3.connect(db) as c:checks['one_plan']=c.execute('SELECT count(*) FROM plans').fetchone()[0]==1
            if name=='resume_second':
                checks['retained_search']=result['initial_state']['steps'].get('search_materials')=='succeeded'
                checks['one_search_charge']=sum(e['cost'] for e in state['events'] if e['step']=='search_materials')==2
            folder=out/name;folder.mkdir(exist_ok=True)
            for filename,value in [('input.json',request),('output.json',result),('assertions.json',checks)]:
                (folder/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
            records.append({'case':name,'passed':all(checks.values()),'checks':checks,'trace':f'{name}/output.json'})
            print(name,'PASS' if all(checks.values()) else 'FAIL',flush=True)
            if result['reason']=='model_error':print(json.dumps(result['trace'][-1]['observation'],ensure_ascii=False));break
    summary={'mode':mode,'expected':len(cases),'executed':len(records),'passed':sum(r['passed'] for r in records),'cases':records,'note':'Mock proves control flow only; live decision evidence requires actual model calls.'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    report=['# '+mode+' 验收结果','',f"通过 {summary['passed']}/{len(cases)}；实际执行 {len(records)}。",'','| 用例 | 通过 | 证据 |','|---|---|---|']+[f"| {r['case']} | {r['passed']} | [输入]({r['case']}/input.json) / [实际输出与 Trace]({r['trace']}) / [断言]({r['case']}/assertions.json) |" for r in records]
    (out/'REPORT.md').write_text('\n'.join(report)+'\n\n'+summary['note']+'\n')
    return 0 if summary['passed']==len(cases) else 2
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['mock','live'],default='mock');p.add_argument('--output',required=True);a=p.parse_args()
    try:sys.exit(evaluate(a.mode,a.output))
    except ModelError as e:print(json.dumps(e.details,ensure_ascii=False));sys.exit(2)
