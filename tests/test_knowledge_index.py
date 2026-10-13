import tempfile
import unittest
from pathlib import Path
from chemtutor.knowledge_index import KnowledgeIndex, split_text

class KnowledgeIndexTests(unittest.TestCase):
    def test_version_filter_updates_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'kb.sqlite3'
            kb = KnowledgeIndex(path)
            old = [{'id':'policy','title':'提交规则','text':'迟交扣分，旧版及格线是60分。'}]
            new = [{'id':'policy','title':'提交规则','text':'迟交扣分，新版及格线是65分。'}]
            kb.ingest('course', 'v1', old)
            kb.ingest('course', 'v2', new)
            kb.ingest('other', 'v1', new)
            self.assertEqual(kb.ingest('course', 'v1', old)['unchanged_documents'], 1)
            hit = KnowledgeIndex(path).search('迟交扣分', 'course', 'v1')[0]
            self.assertIn('60分', hit['text'])
            kb.ingest('course', 'v1', [{'id':'policy','text':'新的规则：免扣分适用条件。'}])
            self.assertEqual(kb.search('迟交', 'course', 'v1'), [])
            self.assertIn('65分', kb.search('迟交', 'course', 'v2')[0]['text'])

    def test_chunks_preserve_source_and_full_coverage(self):
        text = ('条件与例外，不能只引用半句。\n\n'*200)
        pieces = list(split_text(text))
        self.assertEqual(pieces[0][0], 0)
        self.assertEqual(pieces[-1][1], len(text))
        for start, end, body in pieces:
            self.assertEqual(body, text[start:end])
            self.assertLessEqual(len(body), 1400)
        for left, right in zip(pieces, pieces[1:]):
            self.assertLessEqual(right[0], left[1])

    def test_unknown_query_and_exact_citation(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = KnowledgeIndex(Path(tmp)/'kb.sqlite3')
            kb.ingest('cs', '17', [{'id':'doc','text':'Sequence nextval is not rolled back.', 'url':'https://example.test/source'}])
            hit = kb.search('nextval rollback', 'cs', '17')[0]
            source = kb.read(hit['id'])
            self.assertEqual(source['text'], source['document_text'][source['start']:source['end']])
            self.assertEqual(kb.search('xyzunknown', 'cs', '17'), [])
            with self.assertRaises(ValueError):
                kb.read('made-up')

    def test_header_suppression_and_same_page_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = KnowledgeIndex(Path(tmp)/'kb.sqlite3')
            records = [
                {'id':'header','title':'barshadow','text':'jwst.barshadow.BarShadowStep\nbarshadow','url':'page'},
                {'id':'rule','text':'The barshadow correction applies to extended sources only.','url':'page'},
                {'id':'exception','text':'The point source is not corrected in this step.','url':'page'},
                {'id':'other','text':'Unrelated rules from another original source document.','url':'other-page'}]
            kb.ingest('c','v',records)
            kb.ingest('c','old',records)
            hits=kb.search('barshadow','c','v')
            self.assertEqual([h['source_id'] for h in hits],['rule'])
            context=kb.read(hits[0]['id'])
            self.assertEqual([r['source_id'] for r in context['adjacent_sources']],['header','exception'])
            # Updating a record does not move it out of original document order.
            kb.ingest('c','v',[{**records[1], 'text':'The barshadow correction applies to extended sources with conditions.'}])
            updated=kb.read(kb.search('barshadow','c','v')[0]['id'])
            self.assertEqual([r['source_id'] for r in updated['adjacent_sources']],['header','exception'])

    def test_rewrite_preserves_original_and_falls_back_on_failure(self):
        class Model:
            model='fake'
            def completion(self, messages, tools):
                return {'content':'{"queries":["sequence nextval rolled back"]}'}
        class BadModel(Model):
            def completion(self, messages, tools):
                raise ValueError('unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            kb=KnowledgeIndex(Path(tmp)/'kb.sqlite3')
            kb.ingest('cs','17',[{'id':'rule','text':'The sequence nextval value is not rolled back.'}])
            result=kb.retrieve('序列值回滚吗','cs','17',Model())
            self.assertEqual(result['hits'][0]['source_id'],'rule')
            self.assertEqual(result['trace']['searches'][0]['query'],'序列值回滚吗')
            fallback=kb.retrieve('nextval','cs','17',BadModel())
            self.assertEqual(fallback['hits'][0]['source_id'],'rule')
            self.assertEqual(fallback['trace']['rewrite_error'],'ValueError')
