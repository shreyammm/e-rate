"""Regression tests for metadata-backed source identity recovery."""
import unittest
from scripts.build_player_registry import inferred_identity
from scripts.identity_metadata_resolver import institution,personal_name_format

class IdentityMetadataResolutionTest(unittest.TestCase):
    def classify(self,filer,base='unresolved',body='We submit these comments on E-Rate.'):
        return inferred_identity({'filer_raw':filer},base,body)

    def test_source_name_recoveries(self):
        cases=[
            ('Michael McKerley, President of Zayo Education and General Manager of Public Sector & Government Relations for Zayo','telecom_isp'),
            ('SELCO | Michael Flores','library_institution'),
            ('Ateret Torah Center','individual_school'),
            ('Ladacin Network','advocacy_organization'),
            ('Colleston Morgan Jr. | City Forward Collective','advocacy_organization'),
            ('HTTP','advocacy_organization'),
            ('AdvanEdge Solutions | Intelafunds','erate_consultant'),
        ]
        for name,role in cases:
            with self.subTest(name=name):
                found=self.classify(name)
                self.assertEqual(found['role'],role)
                self.assertFalse(found['needs_review'])

    def test_named_remaining_institutions_and_occupational_titles(self):
        cases=[
            ('SentinelOne, Inc.','other_vendor'),
            ('Ohio Information Technology Centers','education_network_consortium'),
            ('Missouri Research and Education Network','education_network_consortium'),
            ('Southwest Kansas Area Cooperative District','school_district'),
            ('Michigan Statewide Educational Network (MiSEN)','education_network_consortium'),
            ('Responsive Education Solutions','school_district'),
            ('Mothers Against Media Addiction','advocacy_organization'),
            ('Family Services of Westchester','advocacy_organization'),
            ('Finkelstein Memorial Library','library_institution'),
            ('Queensborough Community College','higher_education_institution'),
            ('Citizens Against Government Waste','advocacy_organization'),
            ('Alabama Leaders in Educational Technology','trade_association'),
            ('California Emerging Technology Fund','advocacy_organization'),
            ('Methodist Healthcare Ministries of South Texas, Inc.','advocacy_organization'),
            ('Infinity Communications & Compliance','erate_consultant'),
            ('Library Assistant II','library_staff'),
            ('Adult Education & Educational Technology Specialist','school_technology_staff'),
        ]
        for name,role in cases:
            with self.subTest(name=name):
                x=self.classify(name)
                self.assertEqual(x['role'],role)
                self.assertFalse(x['needs_review'])

    def test_repeated_association_metadata_and_parent_language(self):
        cases=[
            ('Kevin Mottus | Outreach Director, CA Brain Tumor Assn','advocacy_organization'),
            ('Chris Warden | K12TechPro','trade_association'),
            ('Maéva Renaud | Kidango','advocacy_organization'),
            ('Liberty Public Schools; Dr. Jennifer Kephart, Superintendent','school_district'),
            ('District of Columbia','government'),
            ('Theodora Scarato | Director of Wireless and EMF Program at Environmental Health Sciences','advocacy_organization'),
        ]
        for name,role in cases:
            with self.subTest(name=name):
                a=self.classify(name)
                self.assertEqual(a['role'],role)
                self.assertFalse(a['needs_review'])
        parent=self.classify('Nicki','unresolved',
            'Where is our say in our child’s safety? We need better screen time limits.')
        self.assertEqual(parent['role'],'parent_guardian')
        self.assertFalse(parent['needs_review'])

    def test_source_only_not_topic(self):
        for commenter in ['Jessica','Cath','Christopher C Netro','E W','Nicki']:
            with self.subTest(name=commenter):
                f=self.classify(commenter,'unresolved',
                    'I oppose E-Rate changes and believe the schools need broadband.')
                self.assertEqual(f['role'],'named_person_capacity_unstated')
                self.assertFalse(f['needs_review'])
                self.assertEqual(f['identity_status'],'capacity_not_stated')

    def test_multi_person_signatories_are_capacity_unstated_not_an_institution(self):
        for raw in ('Sean George | Janine George',
                    'Cheryl Brownstein | Nancy Thompson',
                    'Serena | David | Ralph | Kavion | Camila'):
            with self.subTest(raw=raw):
                x=self.classify(raw)
                self.assertEqual(x['role'],'named_person_capacity_unstated')
                self.assertFalse(x['needs_review'])
                self.assertEqual(x['organization'],'')
        institutional=self.classify('Chris Warden | K12TechPro')
        self.assertEqual(institutional['role'],'trade_association')
        self.assertFalse(institutional['needs_review'])
        self.assertTrue(institutional['attribution_review'])

    def test_dont_invent_professional_authority(self):
        self.assertFalse(personal_name_format('HTTP'))
        self.assertFalse(personal_name_format('26-133 | 13-184'))
        self.assertFalse(personal_name_format('Ateret Torah Center'))
        unknown=self.classify('26-133 | 13-184')
        self.assertEqual(unknown['role'],'unresolved')
        self.assertTrue(unknown['needs_review'])

if __name__=='__main__': unittest.main()
