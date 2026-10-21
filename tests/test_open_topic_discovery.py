"""Small, dependency-light smoke tests for unseeded full-document topics."""
import unittest
from scripts.discover_open_topics import extract_excerpt, select_fit_indices

class OpenTopicDiscoveryTests(unittest.TestCase):
    def test_exact_text_deduplication_and_prolific_filer_cap(self):
        rows=[
            {"text":"Unique filing text "+str(i),"sha":"h"+str(i),"filer":"Repeated Organization"}
            for i in range(16)
        ]
        rows.append({"text":"Unique filing text 2","sha":"h2","filer":"Different filer"})
        rows.append({"text":"","sha":"empty","filer":"Unknown"})
        selected=select_fit_indices(rows,max_per_filer=4)
        self.assertEqual(len(selected),4)
        self.assertEqual(selected,[0,1,2,3])
    def test_original_quote_is_contiguous_and_semantically_unlabeled(self):
        sentence="Our community has to maintain affordable broadband connectivity for schools and the people who rely on this network."
        body="A brief notice. "+sentence+" Other details."
        quote=extract_excerpt(body,["affordable broadband","network connectivity"])
        self.assertEqual(quote,sentence)
        self.assertIn(quote,body)
        self.assertEqual(extract_excerpt("Not enough evidence.",["broadband","network"]),"")
    def test_no_fcc_policy_or_advocacy_filter_in_source_discovery(self):
        import inspect
        from scripts.discover_open_topics import fit_model,read_corpus
        source=inspect.getsource(fit_model)
        self.assertIn("TfidfVectorizer",source)
        self.assertNotIn("POLICY.search",source)
        self.assertNotIn("ADVOCACY.search",source)
        self.assertIn("NMF",source)
        self.assertIn("manifest",inspect.getsource(read_corpus))
if __name__=="__main__":unittest.main()
