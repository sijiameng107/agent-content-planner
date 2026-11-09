"""Cost-aware content planner. Synthetic business tools; real or mock model decisions."""
import argparse
import copy
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()

def validate(request):
    missing = [k for k in ('theme', 'budget', 'start_time', 'deadline') if k not in request or request[k] is None or request[k] == '']
    if missing:
        return {'error': 'missing_input', 'missing': missing}
    if not isinstance(request['theme'], str) or not request['theme'].strip():
        return {'error': 'invalid_theme'}
    budget = request['budget']
    if type(budget) is not int or budget < 0:
        return {'error': 'budget_must_be_nonnegative_integer_simulated_units'}
    try:
        start, end = [datetime.fromisoformat(request[k]) for k in ('start_time', 'deadline')]
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError()
    except (ValueError, TypeError):
        return {'error': 'invalid_deadline', 'message': 'Use timezone-aware ISO times; deadline must be after start_time.'}
    return None

class BusinessTools:
    def __init__(self, request, fixture, db, failure='none'):
        self.request, self.fixture, self.failure = request, fixture, failure
        self.key = fingerprint({'request': request, 'fixture': fixture})
        self.db = sqlite3.connect(db, timeout=5)
        self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, plan TEXT NOT NULL)')
        row = self.db.execute('SELECT state FROM runs WHERE id=?', (self.key,)).fetchone()
        self.state = json.loads(row[0]) if row else {'spent': 0, 'elapsed_minutes': 0, 'steps': {}, 'results': {}, 'estimates': [], 'events': [], 'failures_used': [], 'saved_plan': None}
        self.initial_state = copy.deepcopy(self.state)

    def close(self):
        self.db.close()

    def persist(self):
        self.db.execute('INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state', (self.key, encode(self.state)))

    def remaining_minutes(self):
        start, end = [datetime.fromisoformat(self.request[k]) for k in ('start_time', 'deadline')]
        return (end-start).total_seconds()/60 - self.state['elapsed_minutes']

    def gate(self, cost, minutes):
        money = max(0, self.state['spent'] + cost - self.request['budget'])
        time = max(0, minutes - self.remaining_minutes())
        if money or time:
            return {'error': 'constraint_exceeded', 'budget_gap': money, 'deadline_gap_minutes': time, 'spent': self.state['spent']}
        return None

    def charge(self, name, cost, minutes):
        self.state['spent'] += cost
        self.state['elapsed_minutes'] += minutes
        self.state['steps'][name] = 'succeeded'
        self.state['events'].append({'step': name, 'status': 'succeeded', 'cost': cost, 'minutes': minutes})

    def search_materials(self):
        if 'materials' in self.state['results']:
            return {'cached': True, 'materials': self.state['results']['materials'], 'additional_cost': 0}
        spec = self.fixture['tools']['search'];problem = self.gate(spec['cost'], spec['minutes'])
        if problem:return problem
        matches = [m for m in self.fixture['materials'] if any(t.lower() in self.request['theme'].lower() for t in m['keywords'])]
        self.charge('search_materials', spec['cost'], spec['minutes'])
        self.state['results']['materials'] = matches
        return {'materials': matches, 'additional_cost': spec['cost'], 'available_variants': self.fixture['variants']}

    def estimate_cost(self, variant):
        if variant not in self.fixture['variants']:return {'error': 'unknown_variant'}
        spec = self.fixture['variants'][variant]
        cached = 'script:'+variant in self.state['results']
        search_needed = 'materials' not in self.state['results']
        remaining_cost = (0 if cached else spec['cost']) + (self.fixture['tools']['search']['cost'] if search_needed else 0)
        remaining_time = (0 if cached else spec['minutes']) + (self.fixture['tools']['search']['minutes'] if search_needed else 0)
        result = {'variant': variant, 'spent': self.state['spent'], 'remaining_cost': remaining_cost, 'total_cost': self.state['spent']+remaining_cost, 'remaining_minutes': remaining_time, 'total_minutes': self.state['elapsed_minutes']+remaining_time, 'budget_gap': max(0,self.state['spent']+remaining_cost-self.request['budget']), 'deadline_gap_minutes': max(0,remaining_time-self.remaining_minutes())}
        result['feasible'] = not result['budget_gap'] and not result['deadline_gap_minutes']
        self.state['estimates'].append(result)
        return result

    def generate_script(self, variant):
        if variant not in self.fixture['variants']:return {'error': 'unknown_variant'}
        cache = 'script:'+variant
        if cache in self.state['results']:return {'cached':True,'script':self.state['results'][cache],'additional_cost':0}
        materials = self.state['results'].get('materials')
        if not materials:return {'error':'materials_required','message':'Search and obtain supporting material before generating.'}
        estimates = [e for e in self.state['estimates'] if e['variant']==variant]
        if not estimates:return {'error':'estimate_required'}
        spec = self.fixture['variants'][variant];problem = self.gate(spec['cost'], spec['minutes'])
        if problem:return problem
        name = 'generate_script:'+variant
        fail = self.failure == 'generate_always' or (self.failure == 'generate_once' and 'generate_once' not in self.state['failures_used'])
        if fail:
            self.state['failures_used'].append('generate_once')
            self.state['steps'][name]='failed'
            # Model assumption: failed generation has zero monetary charge but costs one simulated minute.
            self.state['elapsed_minutes'] += 1
            self.state['events'].append({'step':name,'status':'failed','cost':0,'minutes':1})
            return {'error':'generation_failed','retryable':self.failure=='generate_once','retained_results':['materials'],'additional_cost':0,'elapsed_minutes':self.state['elapsed_minutes']}
        script = {'title':self.request['theme'],'variant':variant,'source_ids':[m['id'] for m in materials], 'scenes':[{'visual':m['visual'],'narration':m['fact']} for m in materials], 'format':spec['format']}
        self.charge(name,spec['cost'],spec['minutes']);self.state['results'][cache]=script
        return {'script':script,'additional_cost':spec['cost'],'spent':self.state['spent']}

    def save_plan(self, variant):
        if self.state['saved_plan']:
            return {'saved':True,'save_status':'duplicate','plan':self.state['saved_plan']}
        script = self.state['results'].get('script:'+variant)
        if not script:return {'error':'successful_script_required'}
        problem = self.gate(0,0)
        if problem:return problem
        if self.failure=='save_always':
            self.state['steps']['save_plan']='failed'
            self.state['events'].append({'step':'save_plan','status':'failed','cost':0,'minutes':0})
            return {'error':'save_failed','retryable':False,'saved':False,'retained_results':list(self.state['results'])}
        plan = {'plan_id':self.key,'theme':self.request['theme'],'variant':variant,'budget':self.request['budget'],'total_cost':self.state['spent'],'elapsed_minutes':self.state['elapsed_minutes'],'projected_completion':(datetime.fromisoformat(self.request['start_time'])+timedelta(minutes=self.state['elapsed_minutes'])).isoformat(),'deadline':self.request['deadline'],'task_plan':['search_materials','estimate_cost:'+variant,'generate_script:'+variant,'save_plan'],'script':script,'status':'saved'}
        self.db.execute('INSERT INTO plans VALUES (?,?)',(self.key,encode(plan)))
        self.state['saved_plan']=plan;self.state['steps']['save_plan']='succeeded'
        self.state['events'].append({'step':'save_plan','status':'succeeded','cost':0,'minutes':0})
        return {'saved':True,'save_status':'saved','plan':plan}

    def call(self, action, args):
        schemas={'search_materials':set(),'estimate_cost':{'variant'},'generate_script':{'variant'},'save_plan':{'variant'}}
        if action not in schemas or not isinstance(args,dict) or set(args)!=schemas[action] or any(not isinstance(v,str) for v in args.values()):
            return {'error':'invalid_tool_or_arguments','allowed_tools':list(schemas)}
        before=copy.deepcopy(self.state)
        try:
            self.db.execute('BEGIN IMMEDIATE')
            # Reload under transaction so concurrent duplicate invocations cannot charge twice.
            row=self.db.execute('SELECT state FROM runs WHERE id=?',(self.key,)).fetchone()
            if row:self.state=json.loads(row[0])
            result=getattr(self,action)(**args)
            self.persist();self.db.commit();return result
        except sqlite3.Error:
            self.db.rollback();self.state=before
            return {'error':'storage_failed','saved':False,'retryable':False}

    def finish(self):
        if self.state['saved_plan']:return {'finished':True,'status':'completed','reason':'plan_saved'}
        if self.state['results'].get('materials')==[]:return {'finished':True,'status':'incomplete','reason':'no_materials'}
        if any(e['status']=='failed' for e in self.state['events']):return {'finished':True,'status':'incomplete','reason':'tool_failure','retained_results':list(self.state['results'])}
        if any(e['budget_gap'] or e['deadline_gap_minutes'] for e in self.state['estimates']):return {'finished':True,'status':'incomplete','reason':'constraints_unresolved','gaps':self.state['estimates'][-1]}
        return {'error':'unfinished_plan','message':'A plan is not saved. Continue required work or obtain evidence explaining why it cannot complete.'}

class MockModel:
    mode='mock'
    model='scripted-test-double'
    def decide(self, context, history):
        state=context['state'];variants=context['catalog']['variants']
        action,args='search_materials',{}
        if state['saved_plan']:action='finish'
        elif 'materials' in state['results']:
            if not state['results']['materials']:action='finish'
            else:
                last=history[-1]['observation'] if history else {}
                if last.get('error') in ('save_failed','storage_failed') or (last.get('error')=='generation_failed' and not last['retryable']):action='finish'
                else:
                    viable=[e for e in state['estimates'] if e['feasible']]
                    if viable:
                        variant=viable[-1]['variant'];args={'variant':variant}
                        action='save_plan' if 'script:'+variant in state['results'] else 'generate_script'
                    else:
                        tried={e['variant'] for e in state['estimates']}
                        remaining=[v for v in variants if v not in tried]
                        if remaining:action,args='estimate_cost',{'variant':remaining[0]}
                        else:action='finish'
        return {'action':action,'arguments':args,'decision_summary':'Offline deterministic test policy; not real model evidence.'}

def run(request,fixture,model,db,max_steps=14,failure='none'):
    problem=validate(request)
    if problem:return {'status':'incomplete','reason':problem['error'],'details':problem,'model_mode':model.mode,'items':{},'trace':[],'total_cost':0}
    if max_steps<1:raise ValueError('max_steps must be positive')
    tools=BusinessTools(request,fixture,db,failure);history=[];status='incomplete';reason='limit_reached'
    try:
        for step in range(1,max_steps+1):
            context={'request':request,'state':copy.deepcopy(tools.state),'catalog':{'variants':fixture['variants'],'tools':fixture['tools']}}
            try:
                decision=model.decide(context,history)
                if not isinstance(decision,dict) or not isinstance(decision.get('action'),str) or not isinstance(decision.get('arguments'),dict) or not isinstance(decision.get('decision_summary'),str) or not decision['decision_summary'].strip():raise ValueError('invalid_decision')
            except Exception as e:
                history.append({'step':step,'action':'model_error','arguments':{},'observation':getattr(e,'details',{'error':type(e).__name__}),'decision_summary':'No valid model action received.'});reason='model_error';break
            action,args=decision['action'],decision['arguments']
            observation=tools.finish() if action=='finish' and args=={} else tools.call(action,args)
            history.append({'step':step,'action':action,'arguments':args,'observation':observation,'decision_summary':decision['decision_summary'][:500],'model_response':getattr(model,'last_meta',{})})
            if observation.get('finished'):
                status,reason=observation['status'],observation['reason'];break
        for i,e in enumerate(history):e['next_action']=history[i+1]['action'] if i+1<len(history) else 'stop:'+reason
        return {'timestamp':datetime.now(timezone.utc).isoformat(),'status':status,'reason':reason,'model_mode':model.mode,'model':model.model,'tool_mode':'local_synthetic','max_steps':max_steps,'steps_used':len(history),'total_cost':tools.state['spent'],'elapsed_minutes':tools.state['elapsed_minutes'],'initial_state':tools.initial_state,'state':tools.state,'trace':history,'time_basis':'Deterministic simulated tool minutes from explicit start_time; not real execution latency.'}
    finally:tools.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--mode',choices=['mock','live'],default='mock');p.add_argument('--data',default=str(ROOT/'data/catalog.json'));p.add_argument('--db',default='planner.sqlite');p.add_argument('--output',default='result.json');p.add_argument('--max-steps',type=int,default=14);p.add_argument('--failure',choices=['none','generate_once','generate_always','save_always'],default='none');a=p.parse_args()
    try:
        from src.model import LiveModel
        model=LiveModel() if a.mode=='live' else MockModel()
        result=run(json.loads(Path(a.input).read_text()),json.loads(Path(a.data).read_text()),model,a.db,a.max_steps,a.failure)
    except Exception as e:
        print(encode(getattr(e,'details',{'error':type(e).__name__})));return 2
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(encode({k:result[k] for k in ('status','reason','model_mode','total_cost')}))
    return 0 if result['status']=='completed' else 2
if __name__=='__main__':sys.exit(main())
