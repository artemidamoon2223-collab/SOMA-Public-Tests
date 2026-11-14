"""Independent semantic audit of downloaded public log records."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={'three_process_authorized','unauthorized_operation','forged_identity','replay','altered_ticket','invalid_mac','expired_grant','wrong_peer','worker_permission_escalation','malformed_message','concurrent_one_execution','durable_identity_conflict','controller_restart_identity','completed_identity_restart','sigkill_exact_outcome','unknown_no_replay_0','unknown_no_replay_1','durable_execution_counts','post_attack_legitimate_request','corrupt_state_fail_closed'}
def verify(reports):
 assert len(reports)==2
 for r in reports:
  assert r['source_sha']=='b995d10090760a8fc41a87c5efa7d0548b184b16'
  assert len(r['records'])==20 and {x['name'] for x in r['records']}==EXPECTED
  for row in r['records']:
   assert row['status']=='PASS'
   d=row['detail']
   if 'expected' in d:assert d['actual']==d['expected'] and d['all_servers_alive'] is True
  by={x['name']:x['detail'] for x in r['records']}
  assert by['sigkill_exact_outcome']['exit_code']==-9
  assert by['corrupt_state_fail_closed']=={'diagnostic':'CORRUPT_STATE','exit_code':42}
  assert sorted(by['concurrent_one_execution']['codes'])==['OK','REPLAY','REPLAY','REPLAY']
  assert by['durable_execution_counts']['executions']==['normal','concurrent','uncertain']
  assert by['three_process_authorized']['distinct_pids'] is True
  for n,h in r['source_hashes'].items():assert hashlib.sha256((ROOT/'ipc002'/n).read_bytes()).hexdigest()==h
  assert r['NEW_LIVE_MODEL_CALLS']==0 and r['CONFIRMATORY_SET_USED'] is False
if __name__=='__main__':
 reports=json.loads((Path(__file__).parent/'reports.json').read_text());verify(reports)
 for mutation in ('missing','crash','wrong_reason'):
  v=copy.deepcopy(reports)
  if mutation=='missing':v[0]['records'].pop()
  elif mutation=='crash':next(x for x in v[0]['records'] if x['name']=='corrupt_state_fail_closed')['detail']['exit_code']=-11
  else:next(x for x in v[0]['records'] if x['name']=='replay')['detail']['actual']='MALFORMED'
  try:verify(v)
  except AssertionError:pass
  else:raise AssertionError('accepted '+mutation)
 print('Independent log audit PASS; missing case, unexpected crash, wrong rejection reason all rejected')
