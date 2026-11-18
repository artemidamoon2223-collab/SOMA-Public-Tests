import json,sys,collections
r=json.load(open(sys.argv[1])); c={'fixed':collections.Counter(),'visible':collections.Counter()}
assert len(r['rows'])==32768
seen=set()
for a,b,mask,truth,lost,name,ch,result in r['rows']:
    k=(tuple(a),tuple(b),mask,truth,lost,name)
    assert k not in seen
    seen.add(k)
    known=lambda h,i: bool(mask & (1 << (h*3+i)))
    choices=[i for i in range(3) if known(0,i) and known(1,i) and a[i]!=b[i]]
    assert ch == (choices[0] if name=='visible' and choices else 0)
    candidates=[h for h,v in enumerate((a,b)) if not known(h,ch) or v[ch]==(a,b)[truth][ch]]
    answer=candidates[0] if not lost and len(candidates)==1 else None
    assert result==answer
    c[name]['abstain' if answer is None else 'correct']+=1
assert dict(c)==r['counts']
print(json.dumps(c))
