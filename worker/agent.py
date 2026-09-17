import os,json,subprocess,hashlib,time
from pathlib import Path
ROLE=os.getenv('ROLE','UNKNOWN_ROLE'); MODEL=os.getenv('MODEL','huggingface-projects/llama-3.2-3B-Instruct')
FOCUS=os.getenv('FOCUS','independent replication')
mission=Path('MISSION.md').read_text(encoding='utf-8')
prompt=f'''You are {ROLE} in CEREBRON Omega Farm 35 Replication.\nFocus: {FOCUS}.\n{mission}\nProduce a concise auditable replication report. Separate reproduced facts, derivations, discrepancies, failed replication, unresolved unknowns, and decisive next test.'''

def run(cmd,t=240): return subprocess.run(cmd,text=True,capture_output=True,timeout=t)
def make_payload(spec,p):
    d={}; used=False
    for x in spec.get('parameters',[]):
        n=x.get('parameter_name') or x.get('name'); typ=str(x.get('type','')).lower(); default=x.get('default')
        if not n: continue
        if n in ('message','prompt','text','query','input','instruction','user_message'): d[n]=p; used=True
        elif n in ('history','chat_history','messages'): d[n]=[]
        elif n in ('max_new_tokens','max_tokens','maximum_tokens'): d[n]=600
        elif n=='temperature': d[n]=0.1
        elif n=='top_p': d[n]=0.9
        elif default is not None: d[n]=default
        elif 'str' in typ and not used: d[n]=p; used=True
    return d if used else None

def invoke(space,p):
    info=run(['hf-gradio','info',space],120)
    if info.returncode!=0: return False,None,None,info.stderr.strip()
    try: meta=json.loads(info.stdout)
    except Exception as e: return False,None,None,'info_json:'+repr(e)
    eps=meta.get('named_endpoints') or meta.get('endpoints') or meta.get('api') or {}
    if isinstance(eps,list): pairs=[(e.get('api_name') or e.get('name'),e) for e in eps if isinstance(e,dict)]
    else: pairs=list(eps.items()) if isinstance(eps,dict) else []
    pref=['/generate','/chat','/predict','/respond','/infer','/run']
    pairs.sort(key=lambda z: pref.index(z[0]) if z[0] in pref else 99)
    errors=[]
    for name,spec in pairs:
        if not name: continue
        payload=make_payload(spec if isinstance(spec,dict) else {},p)
        if payload is None: continue
        q=run(['hf-gradio','predict',space,name,json.dumps(payload)],240)
        if q.returncode==0 and q.stdout.strip(): return True,q.stdout.strip(),name,None
        errors.append(f'{name}:{q.stderr.strip()[:500]}')
    return False,None,None,' | '.join(errors[-4:]) or 'no compatible endpoint'

ok,text,endpoint,error=invoke(MODEL,prompt)
out={'farm':35,'role':ROLE,'focus':FOCUS,'model':MODEL,'provider':'huggingface-space-zerogpu','inference_success':ok,'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT' if ok else 'EXTERNAL_INFERENCE_FAILED','api_name':endpoint,'output':text if ok else None,'error':error,'timestamp':int(time.time())}
if ok: out['output_sha256']=hashlib.sha256(text.encode()).hexdigest()
Path('results').mkdir(exist_ok=True); Path(f'results/{ROLE}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:out.get(k) for k in ('role','model','inference_success','status','api_name','error')},ensure_ascii=False))