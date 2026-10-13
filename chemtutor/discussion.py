"""Select the last mathematical contribution without judging its correctness."""
import re


def is_social_or_process_only(text):
    # Acknowledgment plus an actual answer is still an answer.
    if re.search(r'\d', text):
        return False
    value = re.sub(r"[^a-z\u4e00-\u9fff ]", ' ', text.lower())
    value = ' '.join(value.split())
    phrases = [
        r'yes', r'okay', r'ok', r'thanks', r'thank you', r'well done',
        r'excellent', r'good', r'great', r'that makes sense', r'that s correct', r'thats correct',
        r'i understand(?: now)?', r'i appreciate (?:your|the) (?:help|feedback)',
        r'i understand (?:the )?(?:answer|problem) now',
        r'thank you for (?:your help|clarifying)', r'thanks for (?:your|the) help',
        r'thanks for checking my work', r'thanks for helping me understand (?:the problem better|the problem)',
        r'i m glad i was able to understand the problem and get the right answer',
        r'i will (?:make sure to )?(?:simplify the problem as much as possible and )?only use the information given(?: to me)? to solve the problem',
        r'i will (?:make sure to )?simplify the problem as much as possible',
        r'i will (?:be more careful|pay more attention|check my work)(?: next time)?',
        r'谢谢', r'明白了', r'好的', r'我(?:以后|下次)?会(?:注意|更仔细|认真检查)',
    ]
    return bool(re.fullmatch(r'(?:(?:' + '|'.join(phrases) + r')(?: +|$)){1,6}', value))


def final_contribution_turns(messages):
    positions = [i for i, t in enumerate(messages)
                 if t['role'] == 'student' and not is_social_or_process_only(t['text'])]
    position = positions[-1] if positions else max(0, len(messages) - 1)
    return [t for t in messages[position:] if not is_social_or_process_only(t['text'])]


def validate_updates(ledger, messages, quote_validator):
    """Check transition evidence, never mathematical correctness."""
    turns = {t['id']: t['text'] for t in messages}
    positions = {t['id']: i for i, t in enumerate(messages)}
    claims = {c['id']: c for c in ledger['claims']}
    for c in claims.values():
        if 'facet' in c and c['facet'] not in ['answer', 'reason', 'relation']:
            raise ValueError('facet只可answer/reason/relation')
        for q in c.get('context_quotes', []):
            quote_validator(q, turns, 'turn_id')
            if positions[q['turn_id']] > max(positions[e['turn_id']] for e in c['quotes']):
                raise ValueError('承接解释不能来自观点之后的发言')
    updates = ledger.get('updates', [])
    if not isinstance(updates, list) or len(updates) > 12:
        raise ValueError('观点更新最多12项')
    for u in updates:
        c = claims.get(u.get('claim_id'))
        if not c or u.get('facet') not in ['answer', 'reason', 'relation']:
            raise ValueError('更新需要实际观点编号和facet')
        if u.get('action') not in ['replaced', 'retained', 'answer_only']:
            raise ValueError('更新action只可replaced/retained/answer_only')
        if not u.get('reason') or not u.get('previous_quotes') or not u.get('current_quotes'):
            raise ValueError('更新需要前后引文和替换依据')
        for q in u['previous_quotes'] + u['current_quotes']:
            quote_validator(q, turns, 'turn_id')
        if max(positions[q['turn_id']] for q in u['previous_quotes']) >= min(positions[q['turn_id']] for q in u['current_quotes']):
            raise ValueError('观点更新必须由较晚发言提供依据')
        if not any(q['turn_id'] == a['turn_id'] and (q['quote'] in a['quote'] or a['quote'] in q['quote']) for q in u['current_quotes'] for a in c['quotes']):
            raise ValueError('更新后引文必须锚定该实际当前观点')
        if u['action'] == 'replaced' and any(q in c.get('context_quotes', []) for q in u['previous_quotes']):
            raise ValueError('已替换的旧解释不能作为当前承接依据')


def current_claim_context(claims, messages):
    """Expose current/inherited actual quotes, not superseded discussion."""
    grouped = {}
    for c in claims:
        for q in c['quotes'] + c.get('context_quotes', []):
            grouped.setdefault(q['turn_id'], [])
            if q['quote'] not in grouped[q['turn_id']]:
                grouped[q['turn_id']].append(q['quote'])
    return [{'id': t['id'], 'role': t['role'], 'text': '\n'.join(grouped[t['id']])}
            for t in messages if t['id'] in grouped]


def validate_qualifier_coverage(ledger, final_turns):
    """Protect explicit logical qualifiers from being dropped during extraction."""
    markers=r'\bonly (?:possible|way|solution|combination)\b|\balways\b|\bnever\b|唯一|必然|一定'
    for turn in final_turns:
        if turn['role']!='student':continue
        for match in re.finditer(markers,turn['text'],re.I):
            # Questions and explicitly revised past beliefs are not current universal assertions.
            start=max(turn['text'].rfind(ch,0,match.start()) for ch in '.!?。！？')+1
            rest=turn['text'][match.end():]
            ending=re.search(r'[.!?。！？]',rest)
            segment=turn['text'][start:match.end()]+(rest[:ending.start()] if ending else rest)
            if ending and ending.group() in '?？':continue
            if re.search(r'used to|previously|initially|thought|原以为|曾经|之前',segment,re.I) and re.search(r'but|now|however|现在|但是',segment,re.I):continue
            marker=match.group().lower();covered=False
            for c in ledger['claims']:
                if not any(q['turn_id']==turn['id'] and marker in q['quote'].lower() for q in c['quotes']):continue
                if c['status']=='active':
                    cues=r'only|唯一|只有|仅|always|总是|必然|一定|never|从不|从未|绝不'
                    covered=bool(re.search(cues,c['statement'],re.I))
                else:
                    # A later answer alone cannot retract an earlier uniqueness claim.
                    covered=any(re.search(markers+'|another|other possibilities|其他|还有',q.get('quote',''),re.I) for q in c.get('replaced_by',[]) if isinstance(q,dict))
                if covered:break
            if not covered:raise ValueError('最后实质发言的逻辑限定未保留：'+turn['id']+' / '+match.group()+ '；须单独提取忠实带限定的观点，不能只提取最终数字。')
