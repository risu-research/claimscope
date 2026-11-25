#!/usr/bin/env python3
"""Isolate the normalization mechanism on four frozen Next.js negative cases."""
import json,re,hashlib,datetime
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,extract,get,pages,sha
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
MP=extract.__globals__['mp']
CASES=[(80415,2963460503,2963471445),(81994,3111495445,3111513386),(82654,3188922244,3188935214),(86338,3565191987,3565202208)]
BAD='<!-- ## Failing test suites -- >'
GOOD='<!-- ## Failing test suites -->'
SEP='\n'+' '.join(['zzcommentboundary']*32)+'\n'
def det(t):return {'D6':len(extract(t,include_positions=True).get('D6',[])),'normalized_length':len(MP.normalize(t)),'report_title_survives':'stats from current pr' in MP.normalize(t)}
def main():
    out=[]
    for n,aid,bid in CASES:
        cs=pages('/repos/vercel/next.js/issues/'+str(n)+'/comments')
        by={c['id']:c['body'] for c in cs};a,b=by[aid],by[bid]
        assert a.count(BAD)==1
        j=next(i for i,c in enumerate(cs) if c['id']==aid);assert cs[j+1]['id']==bid
        full='\n'.join(c['body'] for c in cs)
        # Exactly the first later closer in the original pre-normalization source, mapped to comment.
        offsets=[];pos=0
        for c in cs:offsets.append((pos,pos+len(c['body']),c['id']));pos+=len(c['body'])+1
        spans=[{'start':m.start(),'end':m.end(),'length':len(m.group()),'start_id':next((i for s,e,i in offsets if s<=m.start()<e),None),'end_id':next((i for s,e,i in offsets if s<m.end()<=e),None),'covers_report':m.start()<=offsets[j+1][0] and m.end()>=offsets[j+1][1]} for m in re.finditer(r'<!--.*?-->',full,re.S) if m.group().startswith(BAD)]
        # Normalize first-step long token substitution separately to check exact original regex span.
        stage=MP._LONG_TOKEN_RE.sub(' ',full)
        normalized_spans=[{'length':len(m.group()),'report_title_inside':'# Stats from current PR' in m.group()} for m in MP._HTML_COMMENT_RE.finditer(stage) if m.group().startswith(BAD)]
        variants={'original':full,'report_alone':b,'malformed_comment_alone':a,'pair_only':a+'\n'+b,
                  'repair_only':full.replace(BAD,GOOD,1),'remove_test_comment':'\n'.join(c['body'] for c in cs if c['id']!=aid),
                  'gap_between_all':SEP.join(c['body'] for c in cs),
                  'remove_opener_only':full.replace(BAD,BAD.replace('<!--',''),1)}
        result={'number':n,'test_comment':aid,'report_comment':bid,'comment_hashes':{str(c['id']):sha(c['body']) for c in cs},'raw_spans':spans,'normalizer_spans':normalized_spans,'conditions':{k:det(v) for k,v in variants.items()}}
        out.append(result)
        print('NEXT_DIAG '+json.dumps(result),flush=True)
    # Ant Design: separate proximity and prospective language, no semantics recoding.
    a=pages('/repos/ant-design/ant-design/issues/55611/comments');d={c['id']:c['body'] for c in a}
    t=d[3486780549];u=d[3486784358]
    row=next(l for l in t.splitlines() if 'dist/antd.min.js' in l)
    sent=next(l for l in u.splitlines() if 'total bundle size' in l)
    ant={'comment_hashes':{str(i):sha(d[i]) for i in (3486780549,3486784358)},'size_limit_row':row,'codecov_sentence':sent,'conditions':{k:det(v) for k,v in {
        'size_limit_original':t,'size_limit_row_original':row,'size_limit_row_with_explicit_cue':'Bundle size '+row,
        'codecov_original':u,'codecov_without_will':u.replace('will increase','increased',1),
        'codecov_sentence_original':sent,'codecov_sentence_without_will':sent.replace('will increase','increased',1),
        'codecov_without_first_sentence':u.replace(sent,'',1),
        'codecov_without_brand_token':re.sub(r'codecov','toolname',u,flags=re.I)}.items()}}
    print('ANT_DIAG '+json.dumps(ant),flush=True)
    OUT.write_text(json.dumps({'pin':PIN,'rows':out,'ant':ant},indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
