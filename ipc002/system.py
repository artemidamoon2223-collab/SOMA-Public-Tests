"""New public synthetic protocol. Same-UID cooperative fixture, not OS confinement."""
import concurrent.futures, hashlib, hmac, json, os, signal, socket, sqlite3, struct, sys, time
from pathlib import Path

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def rpc(path,obj):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(3);s.connect(str(path));s.sendall(obj if isinstance(obj,bytes) else canonical(obj)+b'\n')
  data=b''
  while not data.endswith(b'\n'):
   part=s.recv(4096)
   if not part:raise RuntimeError('unexpected server disconnect')
   data+=part
  return json.loads(data)
def db_open(path):
 db=sqlite3.connect(path,isolation_level=None);db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA journal_mode=WAL')
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 db.execute('CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL)')
 return db

def server(role,root,key,crash):
 path=root/(role+'.sock')
 try:
  db=db_open(root/(role+'.sqlite'))
  if role=='worker':db.execute("UPDATE actions SET state='UNKNOWN_OUTCOME' WHERE state='RUNNING'")
 except (sqlite3.DatabaseError,AssertionError):
  print('CORRUPT_STATE',flush=True);return 42
 path.unlink(missing_ok=True)
 with socket.socket(socket.AF_UNIX) as server:
  server.bind(str(path));os.chmod(path,0o600);server.listen(8);print('READY',flush=True)
  while True:
   stream,_=server.accept()
   with stream:
    stream.settimeout(2)
    peer=struct.unpack('3i',stream.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    config=json.loads((root/'peers.json').read_text())
    try:
     raw=b''
     while not raw.endswith(b'\n') and len(raw)<=8192:
      part=stream.recv(1024)
      if not part:break
      raw+=part
     if len(raw)>8192:raise ValueError('oversize')
     request=json.loads(raw)
     if not isinstance(request,dict):raise ValueError('not object')
     if peer[0]!=config['investigator'] or peer[1]!=os.getuid():reply={'code':'WRONG_PEER'}
     elif role=='controller':
      if request.get('identity')!=peer[0]:reply={'code':'FORGED_IDENTITY'}
      elif request.get('operation')!='echo':reply={'code':'DENIED_OPERATION'}
      elif not isinstance(request.get('action'),str) or not isinstance(request.get('payload'),str):reply={'code':'MALFORMED'}
      else:
       digest=hashlib.sha256(request['payload'].encode()).hexdigest();old=db.execute('SELECT digest FROM actions WHERE id=?',(request['action'],)).fetchone()
       if old and old[0]!=digest:reply={'code':'IDENTITY_CONFLICT'}
       else:
        db.execute("INSERT OR IGNORE INTO actions VALUES (?,?,'ISSUED')",(request['action'],digest))
        ticket={'action':request['action'],'payload':request['payload'],'operation':'echo','peer':peer[0],'uid':peer[1],'expires':time.time()+2}
        reply={'code':'GRANTED','ticket':ticket,'mac':hmac.new(key,canonical(ticket),hashlib.sha256).hexdigest()}
     else:
      ticket=request.get('ticket');mac=request.get('mac')
      if not isinstance(ticket,dict) or not isinstance(mac,str):reply={'code':'MALFORMED'}
      elif not hmac.compare_digest(hmac.new(key,canonical(ticket),hashlib.sha256).hexdigest(),mac):reply={'code':'BAD_MAC'}
      elif ticket.get('peer')!=peer[0] or ticket.get('uid')!=peer[1]:reply={'code':'TICKET_PEER'}
      elif ticket.get('operation')!='echo':reply={'code':'DENIED_OPERATION'}
      elif ticket.get('expires',0)<time.time():reply={'code':'EXPIRED'}
      else:
       assert rpc(root/'controller.sock',{'identity':os.getpid(),'operation':'delete'})['code']=='WRONG_PEER'
       action=ticket['action'];digest=hashlib.sha256(ticket['payload'].encode()).hexdigest()
       db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT state FROM actions WHERE id=?',(action,)).fetchone()
       if old:
        db.rollback();reply={'code':'UNKNOWN_OUTCOME' if old[0]=='UNKNOWN_OUTCOME' else 'REPLAY'}
       else:
        db.execute("INSERT INTO actions VALUES (?,?,'RUNNING')",(action,digest));db.commit()
        with (root/'executions.jsonl').open('ab') as f:
         f.write(canonical({'action':action})+b'\n');f.flush();os.fsync(f.fileno())
        if crash:os.kill(os.getpid(),signal.SIGKILL)
        db.execute("UPDATE actions SET state='COMPLETED' WHERE id=?",(action,));reply={'code':'OK','value':ticket['payload']}
    except (ValueError,KeyError,TypeError,socket.timeout):reply={'code':'MALFORMED'}
    stream.sendall(canonical(reply)+b'\n')

def investigator(root):
 print('READY',flush=True)
 for line in sys.stdin:
  command=json.loads(line)
  if command.get('identity')=='SELF':command['identity']=os.getpid()
  try:
   if command.pop('parallel',False):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:reply=list(pool.map(lambda _:rpc(root/'worker.sock',command),range(4)))
   elif command.pop('malformed',False):reply=rpc(root/'worker.sock',b'{bad\n')
   else:reply=rpc(root/(command.pop('target','controller')+'.sock'),command)
  except (OSError,RuntimeError) as error:reply={'code':'DISCONNECTED','error_type':type(error).__name__}
  print(json.dumps(reply),flush=True)

if __name__=='__main__':
 role,folder=sys.argv[1:3];root=Path(folder)
 if role=='investigator':investigator(root)
 elif role=='worker_probe':
  print(json.dumps(rpc(root/'controller.sock',{'identity':os.getpid(),'operation':'delete','action':'escalate','payload':'x'})),flush=True)
 else:
  key=os.read(int(sys.argv[3]),32);assert len(key)==32
  raise SystemExit(server(role,root,key,'--crash' in sys.argv))
