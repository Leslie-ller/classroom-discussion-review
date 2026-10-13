"""Ground ratio denominators in literal source spans; no answer/case-specific rules."""
import re
from fractions import Fraction

def normalize(text):return ' '.join(text.lower().split()).strip()
def parse_rate(token):
 value=normalize(token)
 words={'half':0.5,'a half':0.5,'one half':0.5,'quarter':0.25,'a quarter':0.25,'one quarter':0.25,'one third':1/3,'two thirds':2/3}
 if value in words:return words[value]
 factors={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twelve':12,'twice':2,'thrice':3}
 if value in ['twice','thrice']:return factors[value]
 mult=re.fullmatch(r'(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve) times',value)
 if mult:return factors[mult[1]] if mult[1] in factors else float(mult[1])
 if re.fullmatch(r'\d+(?:\.\d+)?',value):return float(value)
 ordinal=re.fullmatch(r'(?:a |one )?(\d{1,2})(?:st|nd|rd|th)',value)
 if ordinal and 1<=int(ordinal[1])<=20:return 1/int(ordinal[1])
 if re.fullmatch(r'\d+(?:\.\d+)?\s*%',value):return float(value[:-1])/100
 if re.fullmatch(r'\d{1,6}/\d{1,6}',value):return float(Fraction(value))
 raise ValueError('rate_text只允许原文百分比、数字分数、half/quarter/third词组')

def normalize_inventory(obj,texts):
 """Normalize literal ratio tokens only; keep changes and omitted plain quantities."""
 kept=[];changes=[];omitted=[]
 words={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twelve':12}
 for row in obj.get('ratios',[]):
  raw=row.get('rate_text','');e=row.get('evidence',{});quote=normalize(e.get('quote',''))
  if not isinstance(raw,str) or normalize(raw) not in quote:raise ValueError('比例原始rate_text须真实出现在证据原文中：'+str(row.get('id')))
  token=normalize(raw);kind=None
  m=re.search(r'\d+(?:\.\d+)?\s*%|\d{1,6}/\d{1,6}|(?:a |one )?\d{1,2}(?:st|nd|rd|th)|(?:one-|a |one )?half|(?:a |one )?quarter',token)
  if m:token=m[0]
  else:
   mult=re.search(r'((?:\d+(?:\.\d+)?)|(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve)) times|twice|thrice',token)
   per=re.search(r'(\d+(?:\.\d+)?)\b.*\b(?:each|per)\b',token)
   if mult:
    token=mult[0];kind='multiplier'
   elif per:token=per[1];kind='per_unit'
   else:
    omitted.append({'id':row.get('id'),'raw_rate_text':raw,'reason':'普通数量或未支持的比例词，留在原始资料中，不加入比例事实表'});continue
  if normalize(raw)!=token:changes.append({'id':row.get('id'),'raw_rate_text':raw,'canonical_rate_text':token})
  row['raw_rate_text']=raw;row['rate_text']=token
  if kind:row['relation']=kind
  tail=quote.split(token,1)[-1].strip()
  if tail.startswith('of '):
   after=tail[3:].strip()
   pronoun=re.match(r'(it|them)\b',after)
   if pronoun and normalize(row.get('base_quote',''))!=pronoun[1]:
    row['antecedent_quote']=row['base_quote'];row['base_quote']=pronoun[1]
    changes.append({'id':row.get('id'),'raw_base_quote':row['antecedent_quote'],'literal_denominator_quote':pronoun[1],'reason':'保留原文代词分母，先前提出的指代单独保存，不改成已确认事实'})
  kept.append(row)
 obj['ratios']=kept;obj['normalizations']=changes;obj['omitted_quantities']=omitted
 return obj

def validate_inventory(obj,texts):
 rows=obj.get('ratios')
 if not isinstance(rows,list) or len(rows)>12:raise ValueError('ratios最多12条')
 ids=[]
 for r in rows:
  if not isinstance(r.get('id'),str) or not r['id']:raise ValueError('比例缺编号')
  ids.append(r['id'])
  for k in ['rate_text','base_quote','part_quote','relation']:
   if not isinstance(r.get(k),str) or not r[k].strip():raise ValueError('比例缺'+k)
  if r['relation'] not in ['share','increase','decrease','per_period','per_unit','multiplier','complement']:raise ValueError('比例关系类型无效')
  evidence=r.get('evidence',{})
  if evidence.get('source_id') not in texts or not isinstance(evidence.get('quote'),str):raise ValueError('比例缺原题证据')
  full=normalize(texts[evidence['source_id']]);quote=normalize(evidence['quote']);token=normalize(r['rate_text']);base=normalize(r['base_quote']);part=normalize(r['part_quote'])
  if len(quote)<4 or quote not in full or token not in quote or base not in full or part not in full:raise ValueError('比例、基数、子群体及证据必须来自真实原文')
  rate=parse_rate(r['rate_text'])
  if not 0<=rate<=100 or (r['relation'] in ['share','complement'] and rate>1):raise ValueError('比例超出本工具范围')
  # For explicit "p of GROUP" and "Half the GROUP", the denominator cannot be renamed as all items.
  index=quote.index(token)+len(token);tail=quote[index:].strip()
  explicit=tail.startswith('of ') or (token in ['half','quarter','a half','one half','a quarter','one quarter'] and tail.startswith('the '))
  if explicit:
   if tail.startswith('of '):tail=tail[3:].strip()
   if tail.startswith('the '):tail=tail[4:]
   base_without_article=base[4:] if base.startswith('the ') else base
   if not tail.startswith(base_without_article):raise ValueError('该比例的显式分母必须锚定of/half后面的原文群体，不可换为总量；原文后续='+tail[:150])
  r['value']=rate;r['explicit_denominator']=explicit
 if len(ids)!=len(set(ids)):raise ValueError('比例编号重复')
 return obj

def numeric_base_bindings(claim,inventory,texts):
 """Surface scoped-rate applications to a stated unqualified population count.
 This is a lexical diagnostic, not a semantic proof or a hardcoded answer.
 """
 result=[]
 for q in claim['quotes']:
  for m in re.finditer(r'(\d+(?:\.\d+)?)\s*%\s+of\s+(\d[\d,]*(?:\.\d+)?)',q['quote'],re.I):
   rate=float(m[1])/100;count=m[2].replace(',','')
   for r in inventory['ratios']:
    if not r.get('explicit_denominator') or abs(rate-r['value'])>1e-8:continue
    base=normalize(r['base_quote']);base=re.sub(r'^the\s+','',base)
    words=base.split()
    if len(words)<2:continue
    head=words[-1];pattern=re.escape(count)+r'\s+'+re.escape(head)+r'\b'
    for sid,text in texts.items():
     normalized=normalize(re.sub(r'(?<=\d),(?=\d)','',text))
     found=re.search(pattern,normalized)
     if not found:continue
     if re.search(re.escape(count)+r'\s+(?:the\s+)?'+re.escape(base)+r'\b',normalized):continue
     result.append({'source_ratio_id':r['id'],'turn_id':q['turn_id'],'actual_application':m[0],
       'applied_count':float(count),'count_group_quote':found[0],'source_id':sid,
       'source_denominator_quote':r['base_quote'],
       'diagnostic':'发言将比例作用于题干无该限定词的群体总数；若称为同一基数，需原题额外的群体相等/已知子群体数量依据。仅数值计算正确不能提供这种依据。'})
 return result
