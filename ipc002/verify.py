"""Independent public protocol adversary: checks reason codes AND server liveness."""
import hashlib,json,os,resource,select,signal,socket,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
from system import rpc
ROOT=Path(__file__).resolve().parent
records=[]
def check(name,condition,detail):
 row={'name':name,'status':'PASS' if condition else 'FAIL','detail':detail};records.append(row);print('CASE '+json.dumps(row),flush=True)
 if not condition:raise AssertionError(name)
def line(p):
 assert select.select([p.stdout],[],[],5)[0],'process response timeout'
 raw=p.stdout.readline();assert raw,'unexpected process exit'
 return raw.strip()
def main():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
 children=[]
 with tempfile.TemporaryDirectory(prefix='ipc002-') as d:
  root=Path(d);key=os.urandom(32)
  def spawn(role,crash=False):
   rd,wr=os.pipe();os.write(wr,key if role in ('controller','worker') else b'');os.close(wr)
   p=subprocess.Popen([sys.executable,'-B',str(ROOT/'system.py'),role,d,str(rd)]+(['--crash'] if crash else []),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,pass_fds=(rd,),start_new_session=True)
   os.close(rd);children.append(p);return p
  try:
   inv=spawn('investigator');assert line(inv)=='READY'
   (root/'peers.json').write_text(json.dumps({'investigator':inv.pid}))
   controller=spawn('controller');worker=spawn('worker');assert line(controller)==line(worker)=='READY'
   def ask(obj):inv.stdin.write(json.dumps(obj)+'\n');inv.stdin.flush();return json.loads(line(inv))
   def grant(action='normal',payload='public'):
    return ask({'identity':'SELF','operation':'echo','action':action,'payload':payload})
   def use(g,**extra):return ask(dict(g,target='worker',**extra))
   def reject(name,response,code):
    check(name,response.get('code')==code and inv.poll() is None and controller.poll() is None and worker.poll() is None,{'expected':code,'actual':response.get('code'),'all_servers_alive':True})
   g=grant();check('three_process_authorized',use(g)=={'code':'OK','value':'public'}, {'distinct_pids':len({inv.pid,controller.pid,worker.pid})==3})
   reject('unauthorized_operation',ask({'identity':'SELF','operation':'delete'}),'DENIED_OPERATION')
   reject('forged_identity',ask({'identity':0,'operation':'echo'}),'FORGED_IDENTITY')
   reject('replay',use(g),'REPLAY')
   tampered=grant('tamper');tampered['ticket']['payload']='altered';reject('altered_ticket',use(tampered),'BAD_MAC')
   bad=grant('mac');bad['mac']='00'*32;reject('invalid_mac',use(bad),'BAD_MAC')
   expired=grant('expire');time.sleep(2.2);reject('expired_grant',use(expired),'EXPIRED')
   reject('wrong_peer',rpc(root/'worker.sock',grant('wrong-peer')),'WRONG_PEER')
   probe=spawn('worker_probe');response=json.loads(line(probe));assert probe.wait(timeout=3)==0
   reject('worker_permission_escalation',response,'WRONG_PEER')
   reject('malformed_message',ask({'malformed':True}),'MALFORMED')
   concurrent=use(grant('concurrent'),parallel=True);check('concurrent_one_execution',sorted(r['code'] for r in concurrent)==['OK','REPLAY','REPLAY','REPLAY'],{'codes':[r['code'] for r in concurrent]})
   reject('durable_identity_conflict',grant('normal','different'),'IDENTITY_CONFLICT')
   controller.kill();controller.wait(timeout=3);controller=spawn('controller');assert line(controller)=='READY'
   reject('controller_restart_identity',grant('normal','different'),'IDENTITY_CONFLICT')
   worker.kill();worker.wait(timeout=3);worker=spawn('worker');assert line(worker)=='READY'
   reject('completed_identity_restart',use(grant('normal')),'REPLAY')
   worker.kill();worker.wait(timeout=3);worker=spawn('worker',True);assert line(worker)=='READY'
   crash_grant=grant('uncertain');response=use(crash_grant);rc=worker.wait(timeout=3)
   check('sigkill_exact_outcome',rc==-signal.SIGKILL and response['code']=='DISCONNECTED',{'exit_code':rc,'response':response['code']})
   worker=spawn('worker');assert line(worker)=='READY'
   for n in range(2):reject('unknown_no_replay_'+str(n),use(grant('uncertain')),'UNKNOWN_OUTCOME')
   executions=[json.loads(x)['action'] for x in (root/'executions.jsonl').read_text().splitlines()]
   check('durable_execution_counts',executions.count('uncertain')==1 and executions.count('normal')==1 and executions.count('concurrent')==1,{'executions':executions})
   check('post_attack_legitimate_request',use(grant('after-attacks'))['code']=='OK',{'servers_alive':controller.poll() is None and worker.poll() is None})
   worker.kill();worker.wait(timeout=3)
   with sqlite3.connect(root/'worker.sqlite') as db:db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
   (root/'worker.sqlite').write_bytes(b'CORRUPT PUBLIC FIXTURE')
   worker=spawn('worker');diagnostic=line(worker);rc=worker.wait(timeout=3)
   check('corrupt_state_fail_closed',diagnostic=='CORRUPT_STATE' and rc==42,{'diagnostic':diagnostic,'exit_code':rc})
  finally:
   for p in children:
    if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
    p.communicate(timeout=3)

def report():
 value={'schema':'SOMA_CI002_V1','source_sha':os.environ.get('SOURCE_SHA','local'),'run_id':os.environ.get('GITHUB_RUN_ID'),'records':records,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'system.py',ROOT/'verify.py']},'limitations':{'different_uid':'BLOCKED: no authorized distinct-UID execution mechanism; no sudo/setuid attempted','filesystem_isolation':'NOT_VERIFIED: same UID can access shared filesystem; mode 0600 is not peer isolation','mount_namespace':'BLOCKED in CI-001; no bypass/retry','same_uid_peer_credentials':'Measured PID/UID binding only; hostile same-UID ptrace/filesystem attacker not isolated','authentication':'Fresh synthetic HMAC key in anonymous pipes only; same-UID memory isolation not claimed'},'SCIENTIFICALLY_VALIDATED':'NO','CONFIRMATORY_SET_USED':False,'NEW_LIVE_MODEL_CALLS':0}
 print('REPORT_JSON '+json.dumps(value,sort_keys=True),flush=True)
if __name__=='__main__':
 try:main()
 finally:report()
