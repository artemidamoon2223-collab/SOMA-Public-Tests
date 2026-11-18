import itertools, json, collections
def run():
    counts = {p: collections.Counter() for p in ('fixed', 'visible')}
    mismatches = 0
    rows = []
    for a, b in itertools.product(itertools.product(range(2), repeat=3), repeat=2):
        for mask in range(64):
            visible = [[(v if mask & (1 << (h*3+i)) else None) for i,v in enumerate(m)] for h,m in enumerate((a,b))]
            sep = [i for i in range(3) if visible[0][i] is not None and visible[1][i] is not None and visible[0][i] != visible[1][i]]
            for truth, lost in itertools.product(range(2), repeat=2):
                for name, channel in [('fixed',0),('visible',sep[0] if sep else 0)]:
                    result = None
                    if not lost:
                        obs = (a,b)[truth][channel]
                        possible = [h for h in range(2) if visible[h][channel] is None or visible[h][channel] == obs]
                        if len(possible) == 1:
                            result = possible[0]
                    outcome = 'abstain' if result is None else 'correct' if result == truth else 'wrong'
                    counts[name][outcome] += 1
                    expected = (not lost and sum(visible[h][channel] is None or visible[h][channel] == (a,b)[truth][channel] for h in range(2)) == 1)
                    mismatches += (result is not None) != expected
                    rows.append([list(a),list(b),mask,truth,lost,name,channel,result])
    assert not mismatches and not counts['visible']['wrong'] and not counts['fixed']['wrong']
    print(json.dumps({'counts':counts,'rows':rows},separators=(',',':')))
run()
